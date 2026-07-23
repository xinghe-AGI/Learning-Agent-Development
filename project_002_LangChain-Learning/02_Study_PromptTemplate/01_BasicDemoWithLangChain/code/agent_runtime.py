"""V1 Agent 运行层：创建 Agent、维护会话标识并提供同步、异步和流式调用。"""

# Author:@星禾

# 延迟解析类型注解，便于使用现代联合类型写法。
from __future__ import annotations

# AsyncIterator 用于标注异步生成器会逐段产出字符串。
from collections.abc import AsyncIterator

# create_agent 用于创建 LangChain V1 Agent 图。
from langchain.agents import create_agent
# ToolStrategy 用于通过工具调用让模型生成符合 Schema 的结构化结果。
from langchain.agents.structured_output import ToolStrategy
# BaseChatModel 是 Agent 接受的聊天模型抽象类型。
from langchain_core.language_models import BaseChatModel
# AIMessageChunk 表示模型流式返回的一小段增量消息。
from langchain.messages import AIMessageChunk
# PromptTemplate 用于从外部 Prompt 文件加载并填充变量。
from langchain_core.prompts import PromptTemplate
# InMemorySaver 是学习阶段使用的 Agent 短期记忆 checkpointer。
from langgraph.checkpoint.memory import InMemorySaver

# Config 提供 Prompt 文件路径等集中配置，避免在业务代码中硬编码路径。
from utils.config import Config
# PackageRecommendation 规定 Agent 最终返回的 Pydantic 结构。
from utils.models import PackageRecommendation


# 定义 Agent 业务服务；该类不处理 HTTP 或 Gradio 页面逻辑。
class AgentPackageService:
    """使用 Pydantic 结构化输出与 InMemorySaver 的套餐客服 Agent。"""

    # 接收外部创建的聊天模型，体现依赖注入，便于复用或替换模型。
    def __init__(self, model: BaseChatModel) -> None:
        # 从文件读取系统 Prompt；template 是不含变量填充值的原始模板文本。
        system_prompt = PromptTemplate.from_file(
            Config.SYSTEM_PROMPT_FILE,
            encoding="utf-8",
        ).template
        # 从文件读取 Human Prompt；后续用 query 变量填充每轮用户输入。
        self._human_prompt = PromptTemplate.from_file(
            Config.HUMAN_PROMPT_FILE,
            encoding="utf-8",
        )
        # 创建 Agent；本案例没有真实业务工具，因此 tools 为空列表。
        self._agent = create_agent(
            # 传入由应用容器创建的聊天模型。
            model=model,
            # 暂无查询套餐、查询用户用量等业务工具。
            tools=[],
            # 系统 Prompt 规定 Agent 的角色和套餐推荐规则。
            system_prompt=system_prompt,
            # 使用工具调用策略约束最终结果必须符合 Pydantic Schema。
            response_format=ToolStrategy(schema=PackageRecommendation),
            # 按 thread_id 保存本进程内的 Agent 短期状态。
            checkpointer=InMemorySaver(),
        )

    # 根据用户和会话标识构造 LangGraph 所需的运行配置。
    def _config(self, user_id: str, conversation_id: str) -> dict[str, dict[str, str]]:
        """返回包含 thread_id 的配置，用于隔离不同 Agent 会话。"""

        # 同一个 thread_id 会恢复同一段短期记忆；不同会话互不干扰。
        thread_id = f"{user_id}:{conversation_id}"
        # configurable 是 LangGraph 读取线程级配置的固定位置。
        return {"configurable": {"thread_id": thread_id}}

    # 把页面传入的原始问题转换为 Agent 需要的 messages 输入结构。
    def _input(self, query: str) -> dict[str, list[dict[str, str]]]:
        """将 query 填入用户 Prompt，并包装为 LangChain messages 输入。"""

        # 将 query 替换进 human_prompt.txt 中定义的 {query} 占位符。
        user_message = self._human_prompt.format(query=query)
        # Agent 以 role/content 形式接收本轮用户消息。
        return {"messages": [{"role": "user", "content": user_message}]}

    # 提供流式调用入口；产出的是 ToolStrategy 工具参数的增量 JSON 文本。

    async def astream_tool_arguments(
        self,
        query: str,
        user_id: str,
        conversation_id: str,
    ) -> AsyncIterator[str]:
        """流式读取 ToolStrategy 生成的结构化工具参数片段。"""

        # 保存本次会话配置，确保流式调用也读写正确的短期记忆线程。
        config = self._config(user_id, conversation_id)
        # messages 模式会异步返回 (AIMessageChunk, metadata) 元组
        # 使用异步流式调用
        async for message_chunk, _metadata in self._agent.astream(
            self._input(query),
            config=config,
            stream_mode="messages",
        ):
            # 仅处理模型生成的增量消息，跳过其他类型的图事件。
            if not isinstance(message_chunk, AIMessageChunk):
                continue
            # ToolStrategy 把 Schema 结果编码在工具调用的 args 增量中。
            for tool_call_chunk in message_chunk.tool_call_chunks:
                # 没有 args 时只代表工具元数据，不代表新的模型输出文本。
                arguments_delta = tool_call_chunk.get("args")
                # 有参数增量时交给 SSE 服务层继续处理。
                if arguments_delta:
                    yield arguments_delta

    # 提供非流式调用入口，供需要普通 JSON 响应的 FastAPI 路由使用。
    async def ainvoke(
        self,
        query: str,
        user_id: str,
        conversation_id: str,
    ) -> PackageRecommendation:
        """异步执行 Agent，并返回经过 Pydantic 校验的结构化结果。"""

        # await 让等待模型响应时不阻塞 FastAPI 的事件循环。
        result = await self._agent.ainvoke(
            self._input(query),
            config=self._config(user_id, conversation_id),
        )
        # ToolStrategy 会把最终校验结果放入 Agent 状态的 structured_response 字段。
        return result["structured_response"]

    # 在流式调用结束后，读取 Agent 保存到 checkpointer 的最终结构化结果。
    async def aget_structured_response(
        self,
        user_id: str,
        conversation_id: str,
    ) -> PackageRecommendation:
        """从当前 thread 的最终状态读取 Pydantic 结构化结果。"""

        # 流结束后状态已写入 InMemorySaver，因此可以按相同 thread_id 读取快照。
        state_snapshot = await self._agent.aget_state(
            self._config(user_id, conversation_id)
        )
        # ToolStrategy 把最终校验通过的结果放入 structured_response 字段。
        structured_response = state_snapshot.values.get("structured_response")
        # 避免模型中断或结构化校验失败时返回不完整数据。
        if not isinstance(structured_response, PackageRecommendation):
            raise RuntimeError("Agent 流式执行结束后未获得有效的结构化输出")
        # 返回完整、类型安全的 Pydantic 结果。
        return structured_response
