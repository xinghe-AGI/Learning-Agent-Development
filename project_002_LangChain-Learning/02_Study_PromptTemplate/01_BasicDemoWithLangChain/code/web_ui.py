"""Gradio 前端：通过 SSE 调用 V1 Agent，并展示结构化套餐建议。"""

# Author:@星禾

# 启用延迟类型解析，支持使用 | 编写联合类型。
from __future__ import annotations

# Iterator 用于标注同步读取 SSE 时逐条产生的事件序列。
from collections.abc import Iterator
# JSON 模块用于解析后端发送的 SSE 数据帧。
import json
# uuid4 用于为每个新会话生成唯一的 conversation_id。
from uuid import uuid4

# Gradio 用于构建浏览器中的测试页面。
import gradio as gr
# requests 用于访问 FastAPI 后端的健康检查和 SSE 接口。
import requests

# Config 提供后端地址与 WebUI 监听地址，避免页面中硬编码端口。
from utils.config import Config
# 导入默认温度，使页面初始值与 .env 中的模型默认配置保持一致。
from utils.llms import DEFAULT_TEMPERATURE


# 示例用户标识；真实系统应从登录态或认证令牌中取得。
DEFAULT_USER_ID = "webui-user"
# 后端聊天接口地址；该接口返回 SSE 事件或普通 JSON。
CHAT_ENDPOINT = f"{Config.BACKEND_URL}/v1/chat"
# 后端健康检查地址；仅用于判断服务是否可访问。
HEALTH_ENDPOINT = f"{Config.BACKEND_URL}/health"

# 页面初始显示的结构化结果说明。
EMPTY_RESULT = "### 本次结构化结果\n提交问题后，将在此显示套餐建议和推荐依据。"
# 页面初始显示的运行状态说明。
IDLE_STATUS = "🟡 等待提问。"
# 限制页面初始值在 Slider 的合法范围内，避免环境变量配置异常导致页面无法构建。
INITIAL_TEMPERATURE = min(max(DEFAULT_TEMPERATURE, 0), 2)

# 定义简单 CSS，使聊天区和侧边信息面板更容易区分。
PAGE_CSS = """
.gradio-container { max-width: 1280px !important; }
#backend-status-panel, #runtime-status-panel, #result-panel { border: 1px solid #d9e2f0; border-radius: 12px; padding: 12px; }
#backend-status-panel, #runtime-status-panel { background: #f7faff; }
#result-panel { background: #fcfcfd; }
"""


# 如果当前浏览器还没有会话标识，则生成新的 conversation_id。
def _session_id(session_id: str | None) -> str:
    """返回已有会话标识，或为新会话生成 UUID。"""

    # 保留已有会话，避免同一段对话丢失 Agent 短期记忆。
    return session_id or uuid4().hex


# 将完整会话标识压缩为便于页面查看的短标识。
def _session_info(session_id: str) -> str:
    """生成当前会话的简短展示文本。"""

    # 只显示前八位，完整值仍保存在 Gradio State 中。
    return f"当前会话：`{session_id[:8]}...`"


# 将当前模型设置格式化为页面状态文本，便于确认本轮实际使用的配置。
def _model_info(llm_type: str, temperature: float) -> str:
    """生成模型厂商与采样温度的简短说明。"""

    # 保留一位小数，使 Slider 取值与页面显示一致。
    return f"模型接口：`{llm_type}` · temperature：`{temperature:.1f}`"


# 检查 FastAPI 后端是否已经启动，供页面加载和手动检查使用。
def check_backend_status() -> str:
    """调用 /health 并返回适合 Markdown 展示的后端状态。"""

    try:
        # 设置较短超时，避免后端未启动时页面长时间等待。
        response = requests.get(HEALTH_ENDPOINT, timeout=3)
        # 非 2xx 响应直接视为后端不可用。
        response.raise_for_status()
        # 仅当后端返回约定的 ok 状态时显示连接成功。
        if response.json().get("status") == "ok":
            return "🟢 后端服务可访问；模型配置会在首次请求时校验。"
        # 返回格式异常时提示用户检查服务日志。
        return "🟠 后端已响应，但健康检查返回格式不符合预期。"
    except (requests.RequestException, ValueError) as error:
        # 请求失败或 JSON 解析失败时提供可操作的提示。
        return f"🔴 后端未连接：请先启动 `agent_service.py`。\n\n`{error}`"


# 将 Pydantic 序列化后的结构化结果格式化为便于复习的 Markdown 卡片。
def _format_structured_result(structured_response: dict[str, object] | None) -> str:
    """将最终套餐建议渲染为结果面板内容。"""

    # 没有结构化结果时保留默认说明，不把空数据展示成卡片。
    if not structured_response:
        return EMPTY_RESULT

    # 读取套餐名；模型信息不足时使用“暂未确定”。
    recommended_plan = structured_response.get("recommended_plan") or "暂未确定"
    # 读取推荐依据；缺失时显示占位文本，避免页面报错。
    recommendation_basis = structured_response.get("recommendation_basis") or "未提供推荐依据"
    # 使用 Markdown 表格让字段和值保持稳定的可读布局。
    return (
        "### 本次结构化结果\n\n"
        "| 字段 | 内容 |\n"
        "| --- | --- |\n"
        f"| 推荐套餐 | {recommended_plan} |\n"
        f"| 推荐依据 | {recommendation_basis} |"
    )


# 建立 SSE 请求并逐条读取后端发送的 token 或 final 事件。
def _stream_response(
    payload: dict[str, object],
) -> Iterator[tuple[str, str, dict[str, object] | None]]:
    """读取 SSE，并产出事件类型、可显示文本和可选结构化结果。"""

    # stream=True 让 requests 不缓冲完整响应，而是逐行读取 SSE 数据。
    with requests.post(
        CHAT_ENDPOINT,
        json=payload,
        stream=True,
        timeout=120,
    ) as response:
        # 后端返回 4xx 或 5xx 时立即抛出异常，由页面显示错误。
        response.raise_for_status()
        # SSE 事件以 data: 开头，并以空行分隔。
        for raw_line in response.iter_lines(decode_unicode=True):
            # 跳过空分隔行和不属于数据帧的内容。
            if not raw_line or not raw_line.startswith("data: "):
                continue
            # 去除 data: 前缀并还原后端发送的 JSON 事件。
            event = json.loads(raw_line.removeprefix("data: "))
            # token 是从 ToolStrategy 参数中提取出的 reply 增量快照。
            if event["type"] == "token":
                yield "token", event["content"], None
            # final 包含经过 Pydantic 校验的完整文本和结构化结果。
            elif event["type"] == "final":
                yield "final", event["content"], event.get("structured_response")


# 处理发送事件：更新聊天记录、运行状态和结构化结果面板。
def respond(
    message: str,
    history: list[dict[str, str]] | None,
    session_id: str | None,
    llm_type: str,
    temperature: float,
):
    """将用户问题发送给后端，并持续更新 Gradio 页面。"""

    # 为本次请求确定稳定会话标识，使 Agent 能恢复该 thread 的短期记忆。
    session_id = _session_id(session_id)
    # 清除用户输入首尾空白，避免把空白内容发送给模型。
    cleaned_message = (message or "").strip()
    # 复制历史记录，避免直接修改 Gradio 传入的原始列表。
    current_history = list(history or [])
    # 将 Slider 数值转换为 float，确保传给 Pydantic 请求体的是数值而非组件值。
    model_temperature = float(temperature)
    # 生成本轮模型选择说明，随后写入页面运行状态。
    model_info = _model_info(llm_type, model_temperature)
    # 空输入不调用后端，保留已有页面状态。
    if not cleaned_message:
        yield (
            current_history,
            "",
            session_id,
            f"🟠 请输入套餐需求后再发送。\n\n{model_info}",
            EMPTY_RESULT,
            _session_info(session_id),
        )
        return

    # 先显示用户消息，让页面立即反馈提交动作。
    current_history.append({"role": "user", "content": cleaned_message})
    # 添加空助手消息，后续用 SSE token 逐步覆盖其内容。
    current_history.append({"role": "assistant", "content": ""})
    # 首次刷新页面，告知用户后端请求已经开始。
    yield (
        current_history,
        "",
        session_id,
        f"🔵 已提交请求，模型正在生成套餐建议……\n\n{model_info}",
        "### 本次结构化结果\n正在等待 Agent 完成结构化输出……",
        _session_info(session_id),
    )

    # 构造与 ChatRequest Schema 一致的后端请求体。
    payload = {
        "message": cleaned_message,
        "user_id": DEFAULT_USER_ID,
        "conversation_id": session_id,
        "stream": True,
        # 传递用户在页面中选择的模型厂商。
        "llm_type": llm_type,
        # 传递用户在页面中设置的采样温度。
        "temperature": model_temperature,
    }
    try:
        # 持续消费 SSE；每次 yield 都会让 Gradio 刷新对应组件。
        for event_type, content, structured_response in _stream_response(payload):
            # token 和 final 都使用当前完整文本覆盖助手占位消息，避免重复拼接。
            current_history[-1] = {"role": "assistant", "content": content}
            # token 阶段没有最终结构化结果，因此保留生成中的面板提示。
            result_panel = (
                _format_structured_result(structured_response)
                if event_type == "final"
                else "### 本次结构化结果\n模型正在逐步生成回复……"
            )
            # final 到达时展示完成状态；token 阶段展示持续生成状态。
            runtime_status = (
                f"🟢 Agent 已完成，并返回了经过 Pydantic 校验的结构化结果。\n\n{model_info}"
                if event_type == "final"
                else f"🔵 模型正在逐 token 生成回复……\n\n{model_info}"
            )
            # 更新聊天框、输入框、会话状态、运行状态、结果面板和会话提示。
            yield (
                current_history,
                "",
                session_id,
                runtime_status,
                result_panel,
                _session_info(session_id),
            )
    except (requests.RequestException, json.JSONDecodeError, KeyError, TypeError) as error:
        # 网络、后端或 SSE 格式错误时，把错误信息放在聊天区和状态面板。
        current_history[-1] = {
            "role": "assistant",
            "content": f"后端请求失败：{error}",
        }
        # 让页面保留已发送消息，并给出明确的排查方向。
        yield (
            current_history,
            "",
            session_id,
            f"🔴 请求失败：请确认后端已启动、模型配置有效，并查看后端终端日志。\n\n{model_info}",
            EMPTY_RESULT,
            _session_info(session_id),
        )


# 创建新的 Agent 会话，并清空页面上的聊天和结构化结果。
def new_conversation():
    """生成新的 conversation_id；旧内存会话保留到后端服务重启。"""

    # 为新会话生成唯一标识，后续请求会使用新的 Agent thread_id。
    session_id = uuid4().hex
    # 返回与按钮输出组件顺序一致的初始页面状态。
    return (
        [],
        session_id,
        EMPTY_RESULT,
        IDLE_STATUS,
        _session_info(session_id),
    )


# 构建并返回 Gradio 页面对象。
def build_demo() -> gr.Blocks:
    """构建 V1 Agent 的聊天、状态和结构化结果展示页面。"""

    # 创建 Blocks 容器；样式以 HTML 注入，兼容 Gradio 6 的参数迁移。
    with gr.Blocks(
        title="LangChain V1 Agent 学习",
    ) as demo:
        # 将页面样式放入 style 标签，避免使用 Gradio 6 已迁移的 Blocks(css=...) 参数。
        gr.HTML(f"<style>{PAGE_CSS}</style>")
        # 展示页面标题和学习场景说明。
        gr.Markdown(
            "# 套餐客服 V1 Agent\n"
            "使用 `create_agent()`、Pydantic Schema、InMemorySaver 和 SSE 构建的学习示例。"
        )
        # 用 State 保存完整 conversation_id；该值不会直接展示在页面中。
        session_id = gr.State(value=None)

        # 左侧放置主要对话操作，右侧放置状态和结构化结果。
        with gr.Row():
            # 主列占更大空间，便于阅读流式聊天内容。
            with gr.Column(scale=3):
                # 创建聊天展示组件；消息采用 role/content 字典结构。
                chatbot = gr.Chatbot(
                    label="套餐咨询",
                    placeholder="输入套餐需求后，Agent 会逐步生成回复。",
                    height=520,
                )
                # 创建用户输入框，并提供可直接尝试的示例。
                message = gr.Textbox(
                    label="你的需求",
                    placeholder="例如：我是学生，每月预算 160 元，流量要多一些。",
                    lines=2,
                )
                # 将主要操作按钮放在同一行。
                with gr.Row():
                    # 发送按钮触发 SSE 聊天请求。
                    send = gr.Button("发送", variant="primary")
                    # 新建会话按钮创建新的 Agent thread_id。
                    reset = gr.Button("新建会话")

            # 侧边列集中展示服务状态和 Agent 结构化结果。
            with gr.Column(scale=2):
                # 下拉框选择本轮调用的 OpenAI-compatible 模型厂商。
                llm_type = gr.Dropdown(
                    choices=["qwen", "openai", "deepseek"],
                    value=Config.LLM_TYPE,
                    label="模型接口",
                    info="需在 code/.env 中配置该厂商的 BASE_URL、API_KEY 和 CHAT_MODEL。",
                )
                # Slider 设置本轮请求的采样温度；数值越高，输出随机性通常越强。
                temperature = gr.Slider(
                    minimum=0,
                    maximum=2,
                    value=INITIAL_TEMPERATURE,
                    step=0.1,
                    label="LLM_TEMPERATURE",
                    info="0 更稳定；数值更高时输出更具随机性。",
                )
                # 显示后端连接状态；页面加载和按钮点击都会刷新它。
                backend_status = gr.Markdown(
                    "⚪ 正在检查后端连接……",
                    elem_id="backend-status-panel",
                )
                # 手动检查按钮用于后端启动后刷新连接状态。
                check_backend = gr.Button("检查后端连接")
                # 显示每一轮 Agent 请求的运行状态。
                runtime_status = gr.Markdown(
                    IDLE_STATUS,
                    elem_id="runtime-status-panel",
                )
                # 显示短会话标识，帮助理解 conversation_id 与 thread_id 的关系。
                session_info = gr.Markdown("当前会话：尚未创建")
                # 用折叠区展示 Pydantic 结构化结果，避免挤占聊天区域。
                with gr.Accordion("套餐建议结构化结果", open=True):
                    result_panel = gr.Markdown(EMPTY_RESULT, elem_id="result-panel")
                # 展示当前页面的运行边界，减少学习过程中的误解。
                with gr.Accordion("当前示例说明", open=False):
                    gr.Markdown(
                        "- 前端通过 SSE 调用 FastAPI 后端。\n"
                        "- Agent 使用 `InMemorySaver` 保存进程内短期记忆。\n"
                        "- 重启后端后，当前 Agent 会话记忆会丢失。"
                    )

        # 定义发送事件所需的输入组件顺序。
        submit_inputs = [message, chatbot, session_id, llm_type, temperature]
        # 定义发送事件每次 yield 对应的输出组件顺序。
        submit_outputs = [
            chatbot,
            message,
            session_id,
            runtime_status,
            result_panel,
            session_info,
        ]
        # 点击发送按钮时处理用户消息。
        send.click(respond, inputs=submit_inputs, outputs=submit_outputs)
        # 在输入框按回车时复用相同的发送逻辑。
        message.submit(respond, inputs=submit_inputs, outputs=submit_outputs)
        # 点击新建会话时清空聊天和结果，并生成新的 conversation_id。
        reset.click(
            new_conversation,
            outputs=[
                chatbot,
                session_id,
                result_panel,
                runtime_status,
                session_info,
            ],
        )
        # 手动刷新后端连接状态，不会触发模型调用。
        check_backend.click(check_backend_status, outputs=backend_status)
        # 页面首次加载时自动检查后端是否可访问。
        demo.load(check_backend_status, outputs=backend_status)

    # 返回构建完成的页面对象，供直接运行或测试导入使用。
    return demo


# 仅在直接执行本文件时启动 Gradio 开发服务器。
if __name__ == "__main__":
    # 使用集中配置中的地址和端口启动 WebUI。
    build_demo().launch(
        server_name=Config.WEB_HOST,
        server_port=Config.WEB_PORT,
    )
