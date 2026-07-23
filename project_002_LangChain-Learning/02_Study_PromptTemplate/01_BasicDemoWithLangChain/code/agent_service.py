"""FastAPI 后端服务：对外提供 V1 Agent 的 JSON 与 SSE 聊天接口。"""

# Author:@星禾

# 启用延迟类型解析，支持异步迭代器类型注解
from __future__ import annotations

# 导入 JSON 模块，用于把 SSE 事件体编码为 JSON 字符串
import json
# 导入正则模块，用于从不完整的工具参数 JSON 中定位 reply 字段。
import re
# 导入异步上下文管理器装饰器，用于定义 FastAPI 生命周期函数
from contextlib import asynccontextmanager
# 导入异步迭代器类型，用于标注 SSE 事件生成器
from typing import AsyncIterator

# 导入 Uvicorn，用于启动 FastAPI 的 ASGI 服务
import uvicorn
# 导入 FastAPI 和 Request，用于定义 HTTP 接口和读取 app.state
from fastapi import FastAPI, HTTPException, Request
# 导入流式响应类型，用于以 SSE 协议向 WebUI 推送事件
from fastapi.responses import StreamingResponse

# 导入 Agent 运行服务，用于创建和调用 create_agent() 生成的 Agent。
from agent_runtime import AgentPackageService
# 导入集中配置，用于读取后端监听地址和端口
from utils.config import Config
# 导入聊天模型工厂，用于在服务启动时创建 ChatOpenAI。
from utils.llms import LLMInitializationError, get_chat_llm
# 导入日志器，用于记录服务启动和请求处理信息。
from utils.logger import get_logger
# 导入前后端请求、响应和 Agent 结构化输出 Schema
from utils.models import ChatRequest, ChatResponse, PackageRecommendation

# 创建当前模块的日志器；同名日志器会被 LoggerManager 复用。
logger = get_logger(__name__)

# 定义 FastAPI 生命周期函数，在服务启动时创建 Agent 服务缓存。
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """初始化按模型厂商和采样温度区分的 Agent 服务缓存。"""

    # 缓存键是 (llm_type, temperature)，相同设置会复用同一个 Agent 与短期记忆。
    app.state.agent_services: dict[tuple[str, float | None], AgentPackageService] = {}
    # 记录后端完成缓存初始化；具体模型在用户首次选择时再创建。
    logger.info("V1 Agent 服务缓存初始化完成")
    # 将控制权交还给 FastAPI，服务开始接收请求
    yield


# 创建 FastAPI 应用，并注册生命周期函数
app = FastAPI(title="LangChain V1 Agent Learning API", lifespan=lifespan)


# 提供轻量健康检查接口，供 WebUI 判断后端是否已成功启动。
@app.get("/health")
async def health() -> dict[str, str]:
    """返回后端服务可用状态；不发送模型请求。"""

    # 返回固定状态，表示 FastAPI 已完成启动阶段。
    return {"status": "ok"}


# 从请求所属的 FastAPI 应用状态中获取或创建匹配设置的 Agent 服务。
def _agent_service(
    request: Request,
    llm_type: str,
    temperature: float | None,
) -> AgentPackageService:
    """按模型厂商和采样温度复用 Agent；首次使用时创建。"""

    # 相同厂商和温度使用同一服务，因此可持续读写同一组 InMemorySaver 记忆。
    cache_key = (llm_type, temperature)
    # 读取 FastAPI 生命周期中创建的服务缓存。
    services: dict[tuple[str, float | None], AgentPackageService] = (
        request.app.state.agent_services
    )
    # 缓存命中时直接返回，无需重新读取 Prompt 或创建 Agent。
    if cache_key in services:
        return services[cache_key]

    try:
        # 依据本次请求的设置创建 ChatOpenAI 实例。
        model = get_chat_llm(llm_type, temperature)
    except LLMInitializationError as error:
        # 将缺失密钥或无效配置转换为客户端可理解的 422 错误。
        raise HTTPException(status_code=422, detail=str(error)) from error

    # 为该设置创建独立 Agent；独立的 checkpointer 避免不同模型混用会话状态。
    service = AgentPackageService(model)
    # 写入缓存，后续相同选择将复用该模型和 Agent。
    services[cache_key] = service
    # 记录本次运行时模型创建，便于通过日志排查配置问题。
    logger.info("已创建 Agent 服务：llm_type=%s，temperature=%s", llm_type, temperature)
    # 返回可执行的 Agent 服务。
    return service


# 将 Pydantic 结构化输出转换为页面可直接展示的文本
def _agent_text(response: PackageRecommendation) -> str:
    """为文本客户端生成 Agent 结构化输出的可读表示。"""

    # 仅在模型已确定套餐时展示套餐行
    plan_line = (
        f"\n\n推荐套餐：{response.recommended_plan}"
        if response.recommended_plan
        else ""
    )
    # 组合主体回复、可选套餐和推荐依据
    return f"{response.reply}{plan_line}\n\n推荐依据：{response.recommendation_basis}"


# 将 Python 字典编码为一条符合 SSE 规范的数据帧
def _sse(payload: dict[str, object]) -> str:
    """编码一个 Server-Sent Events 数据帧。"""

    # data: 前缀和两个换行符是 SSE 事件的基本格式
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# 从尚未完成的 ToolStrategy 参数 JSON 中尽量提取 reply 字段，用于前端逐 token 显示
def _partial_reply(arguments: str) -> str | None:
    """从不完整 JSON 中提取 reply 的当前文本，不要求 JSON 已闭合。"""

    # 匹配 reply 字段起始位置，并允许 JSON 中存在任意空白
    match = re.search(r'"reply"\s*:\s*"', arguments)
    # 尚未生成 reply 字段时不能展示文本
    if not match:
        return None
    # 从 reply 字符串内容的第一个字符开始扫描
    raw_value = arguments[match.end():]
    # 保存已经生成的 JSON 字符串字符
    characters: list[str] = []
    # 记录当前字符是否被反斜杠转义
    escaped = False
    # 逐字符读取 reply 的不完整 JSON 字符串
    for character in raw_value:
        # 遇到未转义的双引号，说明 reply 字段已经结束
        if character == '"' and not escaped:
            break
        # 保存当前字符，用于组成当前可见文本
        characters.append(character)
        # 反斜杠会转义下一个字符；其他字符取消转义状态
        escaped = character == "\\" and not escaped

    # 组合已经读取到的 JSON 字符串片段
    partial_value = "".join(characters)
    # 尝试借助 json.loads 正确还原转义字符，例如 \n 或 \"。
    try:
        return json.loads(f'"{partial_value}"')
    except json.JSONDecodeError:
        # 字符串还未闭合时做最小转义替换，保证可持续显示中文正文
        return partial_value.replace(r"\\n", "\n").replace(r'\\"', '"')


# 定义 Agent 聊天接口；可根据 stream 字段返回 SSE 或普通 JSON
@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request_body: ChatRequest, request: Request):
    """执行 V1 Agent，并返回 JSON 或 SSE 格式的结构化结果。"""

    # 取得与本次模型选择和采样温度对应的 Agent 运行服务。
    agent_service = _agent_service(
        request,
        request_body.llm_type,
        request_body.temperature,
    )

    # SSE 模式下以事件流形式返回 Agent 结果
    if request_body.stream:
        # 定义异步事件生成器，让 FastAPI 按事件逐条发送数据
        async def event_stream() -> AsyncIterator[str]:
            # 缓存 ToolStrategy 逐步输出的 JSON 参数，便于持续提取 reply 字段
            arguments_buffer = ""
            # 记录上一轮已经推送给前端的 reply，避免重复发送相同文本
            last_reply = ""
            # 逐块读取模型生成的工具调用参数；每块对应真实模型输出增量
            async for arguments_delta in agent_service.astream_tool_arguments(
                request_body.message,
                request_body.user_id,
                request_body.conversation_id,
            ):
                # 将最新 JSON 片段拼接进完整参数缓冲区
                arguments_buffer += arguments_delta
                # 从不完整 JSON 中提取已经生成的 reply 文本
                current_reply = _partial_reply(arguments_buffer)
                # reply 有新增内容时立即作为 token 事件发送给 WebUI
                if current_reply is not None and current_reply != last_reply:
                    last_reply = current_reply
                    yield _sse({"type": "token", "content": current_reply})

            # 流式执行结束后，从 Agent 最终状态读取通过 Pydantic 校验的完整结果
            structured = await agent_service.aget_structured_response(
                request_body.user_id,
                request_body.conversation_id,
            )
            # 发送完整文本和原始结构化结果，用于覆盖流式阶段的不完整展示
            yield _sse(
                {
                    "type": "final",
                    "content": _agent_text(structured),
                    "structured_response": structured.model_dump(),
                }
            )
            # 发送结束事件，通知前端关闭本轮等待状态
            yield _sse({"type": "done"})

        # 返回 SSE 响应；浏览器和 requests 都可逐行读取事件
        return StreamingResponse(event_stream(), media_type="text/event-stream")

    # 非 SSE 模式下直接执行 Agent 并返回普通 JSON 响应
    structured = await agent_service.ainvoke(
        request_body.message,
        request_body.user_id,
        request_body.conversation_id,
    )
    # 使用 ChatResponse 固定普通 JSON 的字段结构
    return ChatResponse(content=_agent_text(structured), structured_response=structured)


# 仅在直接执行本文件时启动 Uvicorn 开发服务器
if __name__ == "__main__":
    # 确保日志目录存在
    Config.ensure_runtime_directories()
    # 使用集中配置中的地址和端口启动后端服务
    uvicorn.run(app, host=Config.BACKEND_HOST, port=Config.BACKEND_PORT)
