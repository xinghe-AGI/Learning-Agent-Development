"""把 LangChain Agent 返回状态整理成便于记录的调用摘要。"""

# 让类型标注延迟解析，避免运行时因为类型名提前求值带来兼容性问题。
from __future__ import annotations

# Mapping 用来表示 dict 这类键值结构，Sequence 用来表示 list/tuple 这类序列。
from collections.abc import Mapping, Sequence
# asdict 用来把 dataclass 转 dict，is_dataclass 用来判断对象是不是 dataclass。
from dataclasses import asdict, is_dataclass
# Real 用来判断 int/float 这类真实数字，不把字符串误当成数字。
from numbers import Real
# Any 表示这里会接收 LangChain 返回的各种对象，类型比较开放。
from typing import Any
# uuid4 用来给详细调用记录生成一个临时的调用 ID。
from uuid import uuid4

# AIMessage 是模型返回消息，HumanMessage 是用户输入消息。
from langchain_core.messages import AIMessage, HumanMessage


# 这个小工具负责把“可能是字典”的值统一变成 Mapping，减少后面重复判断。
def _as_mapping(value: Any) -> Mapping[str, Any]:
    """值是 Mapping 时直接返回，否则返回空 Mapping。"""

    # 如果 value 本来就是 dict / Mapping，就保留原值；否则返回空字典，避免后续 .get 报错。
    return value if isinstance(value, Mapping) else {}


# 这个函数负责把复杂对象变成适合写日志、写 JSON 的普通 Python 数据。
def _safe_value(value: Any) -> Any:
    """把常见 Python 模型转换为适合日志记录的基础数据。"""

    # None、字符串、数字、布尔值本来就容易序列化，可以原样返回。
    if value is None or isinstance(value, (str, int, float, bool)):
        # 这里直接返回，不做额外转换，避免改变业务含义。
        return value

    # dataclass 实例常用于结构化结果，先转成 dict 再继续递归清洗。
    if is_dataclass(value) and not isinstance(value, type):
        # asdict 会把 dataclass 字段展开成字典。
        return _safe_value(asdict(value))

    # Pydantic v2 模型通常有 model_dump 方法，例如结构化输出的 ResponseFormat。
    model_dump = getattr(value, "model_dump", None)
    # 如果 model_dump 可调用，说明它大概率是 Pydantic 风格的对象。
    if callable(model_dump):
        # mode="json" 会尽量转成 JSON 友好的值，比如 datetime 也会被处理。
        return _safe_value(model_dump(mode="json"))

    # 如果是 dict / Mapping，就逐个字段递归转换。
    if isinstance(value, Mapping):
        # key 统一转字符串，item 继续走 _safe_value，避免嵌套对象不能记录。
        return {
            str(key): _safe_value(item)
            for key, item in value.items()
        }

    # 如果是 list / tuple 这类序列，也需要递归处理内部元素。
    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        # 字符串也是 Sequence，所以前面特意排除了 str/bytes/bytearray。
        return [_safe_value(item) for item in value]

    # 其他未知对象兜底转字符串，保证日志记录不会因为不能序列化而崩。
    return str(value)


# Agent 返回值里通常有 response["messages"]，这个函数专门安全读取它。
def _messages_from_response(response: Mapping[str, Any]) -> list[Any]:
    """读取 Agent state 中的消息列表。"""

    # 如果 messages 不存在或是 None，就按空列表处理。
    messages = response.get("messages") or []
    # LangChain 的 messages 应该是列表/元组这类序列，但不能把字符串当消息列表。
    if isinstance(messages, Sequence) and not isinstance(
        messages,
        (str, bytes, bytearray),
    ):
        # 转成 list，后面可以稳定遍历，不依赖原始对象类型。
        return list(messages)
    # 如果 messages 不是合法序列，就返回空列表，避免调用方报错。
    return []


# 判断一条消息是不是模型返回消息，也兼容 dict 形式的 assistant 消息。
def _is_ai_message(message: Any) -> bool:
    # 第一种情况：LangChain 标准 AIMessage。
    return isinstance(message, AIMessage) or (
        # 第二种情况：有些测试或外部数据可能用 dict 表示消息。
        isinstance(message, Mapping)
        # dict 消息中 role 为 assistant/ai 时，也当作模型消息。
        and message.get("role") in {"assistant", "ai"}
    )


# 判断一条消息是不是用户消息，也兼容 dict 形式的 user 消息。
def _is_human_message(message: Any) -> bool:
    # 第一种情况：LangChain 标准 HumanMessage。
    return isinstance(message, HumanMessage) or (
        # 第二种情况：外部数据可能用 dict 表示消息。
        isinstance(message, Mapping)
        # dict 消息中 role 为 user/human 时，也当作用户消息。
        and message.get("role") in {"user", "human"}
    )


# 统一读取消息字段：既支持 LangChain 对象属性，也支持 dict 键。
def _message_attribute(message: Any, name: str, default: Any = None) -> Any:
    # 如果 message 是 dict，就用 .get 读取字段。
    if isinstance(message, Mapping):
        # 字段不存在时返回 default。
        return message.get(name, default)
    # 如果 message 是 LangChain 对象，就用 getattr 读取属性。
    return getattr(message, name, default)


# 统一读取 AIMessage.response_metadata，并确保返回 Mapping。
def _response_metadata(message: Any) -> Mapping[str, Any]:
    # response_metadata 里通常保存 model_name、token_usage、finish_reason 等 Provider 元数据。
    return _as_mapping(_message_attribute(message, "response_metadata", {}))


# 从多次模型调用中提取最终使用的模型名和 Provider。
def _model_info(ai_calls: Sequence[Any]) -> dict[str, Any]:
    """取最后一条包含模型信息的 AIMessage。"""

    # model 用来保存模型名称，例如 qwen3.7-plus。
    model = None
    # provider 用来保存 Provider 名称，例如 openai。
    provider = None

    # 一个 Agent 运行过程可能会多次调用模型，所以这里遍历全部 AIMessage。
    for message in ai_calls:
        # 每条 AIMessage 的模型信息通常放在 response_metadata 里。
        metadata = _response_metadata(message)
        # 不同 Provider 字段名可能略有差异，所以同时兼容 model_name 和 model。
        message_model = metadata.get("model_name") or metadata.get("model")
        # Provider 字段也同时兼容 model_provider 和 provider。
        message_provider = (
            metadata.get("model_provider")
            or metadata.get("provider")
        )
        # 如果当前消息里有模型名，就更新为当前值。
        if message_model is not None:
            # 遍历结束后保留下来的就是最后一次可见模型名。
            model = message_model
        # 如果当前消息里有 Provider，就更新为当前值。
        if message_provider is not None:
            # 遍历结束后保留下来的就是最后一次可见 Provider。
            provider = message_provider

    # 返回统一字段，方便 build_response_record 直接拼装。
    return {"model": model, "provider": provider}


# 把 Token 数量安全转换成 int，避免 Provider 返回字符串或 None 时出错。
def _token_number(value: Any) -> int:
    """把 Provider 返回的 Token 数安全转换为整数。"""

    # None 表示没有这个字段；bool 虽然是 int 子类，但不应该当 Token 数。
    if value is None or isinstance(value, bool):
        # 缺失或非法布尔值统一按 0 处理。
        return 0
    # 尝试把数字字符串、float、int 都转成 int。
    try:
        # int("12")、int(12.0) 都能正常转换。
        return int(value)
    # 如果类型不支持、字符串不是数字、数字溢出，就进入兜底。
    except (TypeError, ValueError, OverflowError):
        # 兜底返回 0，保证调用记录生成过程不中断。
        return 0


# 从一个 mapping 中按顺序寻找第一个存在且不为 None 的字段。
def _first_present(mapping: Mapping[str, Any], *keys: str) -> Any:
    # keys 是候选字段名列表，例如 input_tokens / prompt_tokens / inputTokens。
    for key in keys:
        # 只有字段存在且值不是 None，才认为找到了有效值。
        if key in mapping and mapping[key] is not None:
            # 返回第一个命中的值，体现字段优先级。
            return mapping[key]
    # 全部字段都没有命中时返回 None。
    return None


# 读取单条 AIMessage 的 token usage。
def _usage_for_message(message: Any) -> dict[str, int]:
    """优先读取 LangChain 标准 usage，缺失时回退 Provider usage。"""

    # LangChain 标准化后的 token 用量通常放在 usage_metadata。
    usage = _as_mapping(_message_attribute(message, "usage_metadata", {}))
    # 如果 usage_metadata 没有值，再回退读取 Provider 原始 token_usage。
    if not usage:
        # OpenAI-compatible 响应常把原始用量放在 response_metadata["token_usage"]。
        usage = _as_mapping(_response_metadata(message).get("token_usage"))

    # 输入 token 兼容 LangChain / OpenAI / 驼峰字段三种常见命名。
    input_tokens = _token_number(
        _first_present(
            usage,
            "input_tokens",
            "prompt_tokens",
            "inputTokens",
        )
    )
    # 输出 token 同样兼容不同命名。
    output_tokens = _token_number(
        _first_present(
            usage,
            "output_tokens",
            "completion_tokens",
            "outputTokens",
        )
    )
    # total token 先保留原始值，后面判断是否需要自己相加。
    total_value = _first_present(usage, "total_tokens", "totalTokens")
    # 如果 Provider 提供 total_tokens，就用 Provider 的值；否则用 input + output 兜底。
    total_tokens = (
        _token_number(total_value)
        if total_value is not None
        else input_tokens + output_tokens
    )

    # 对外统一输出驼峰字段，便于日志记录和前端展示。
    return {
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "totalTokens": total_tokens,
    }


# 汇总多次 AIMessage 的 token usage。
def _sum_usage(ai_calls: Sequence[Any]) -> dict[str, int]:
    # 初始化累计器，三个字段都从 0 开始。
    total = {
        "inputTokens": 0,
        "outputTokens": 0,
        "totalTokens": 0,
    }
    # Agent 可能经历“模型 -> 工具 -> 模型 -> 结构化输出”等多次模型调用。
    for message in ai_calls:
        # 先读取当前这一次模型调用的 token 用量。
        usage = _usage_for_message(message)
        # 三个字段逐个累加，避免写三行重复代码。
        for key in total:
            # 把当前调用的 usage 加到总 usage 上。
            total[key] += usage[key]
    # 返回累计后的总 token 用量。
    return total


# 读取单条 AIMessage 上的延迟统计字段。
def _latency_checkpoint(message: Any) -> Mapping[str, Any]:
    # Provider 扩展字段通常在 response_metadata。
    metadata = _response_metadata(message)
    # 优先读取 response_metadata["latency_checkpoint"]。
    checkpoint = _as_mapping(metadata.get("latency_checkpoint"))
    # 如果直接读到了，就立刻返回。
    if checkpoint:
        # checkpoint 里可能包含 total_duration_ms 等字段。
        return checkpoint

    # 少数 OpenAI-compatible 服务会把该字段放在 token_usage 内。
    token_usage = _as_mapping(metadata.get("token_usage"))
    # 从 token_usage 中继续尝试读取 latency_checkpoint。
    return _as_mapping(token_usage.get("latency_checkpoint"))


# 把延迟字段安全转换成 float。
def _duration_number(value: Any) -> float | None:
    # None 表示没有延迟字段；bool 不应该被当作耗时数字。
    if isinstance(value, bool) or value is None:
        # 没有可用耗时时返回 None，而不是返回 0。
        return None
    # 如果已经是数字类型，直接转成 float。
    if isinstance(value, Real):
        # 使用 float 便于后续 sum 统一处理整数和小数。
        return float(value)
    # 有些 Provider 可能返回数字字符串，例如 "120.5"。
    try:
        # 尝试把字符串数字转成 float。
        return float(value)
    # 转换失败时进入兜底。
    except (TypeError, ValueError, OverflowError):
        # 非法耗时字段按缺失处理。
        return None


# 汇总多次 AIMessage 的 Provider 延迟。
def _sum_latency_ms(ai_calls: Sequence[Any]) -> int | float | None:
    # 保存每次模型调用的耗时，单位是毫秒。
    durations: list[float] = []
    # 遍历每一次模型调用。
    for message in ai_calls:
        # 从 latency_checkpoint.total_duration_ms 中读取耗时。
        duration = _duration_number(
            _latency_checkpoint(message).get("total_duration_ms")
        )
        # 只有读取到合法数字时，才加入累计列表。
        if duration is not None:
            # 加入当前模型调用的耗时。
            durations.append(duration)

    # 如果所有 AIMessage 都没有延迟字段，就无法从 response 反推出耗时。
    if not durations:
        # 返回 None 表示 Provider 未提供延迟信息。
        return None

    # 把多次模型调用耗时求和。
    total = sum(durations)
    # 如果总耗时没有小数，就返回 int，让日志更清爽；否则保留 float。
    return int(total) if total.is_integer() else total


# 从消息列表中抽取“请求输入”的可见部分。
def _extract_request_input(messages: Sequence[Any]) -> dict[str, Any]:
    """收集 state 中可见的 HumanMessage。"""

    # 用列表保存所有用户消息，因为同一个 state 可能包含多轮对话。
    human_messages = []
    # 遍历 Agent state 中的全部消息。
    for message in messages:
        # 只收集用户消息，跳过 AIMessage / ToolMessage。
        if not _is_human_message(message):
            # continue 表示当前消息不是用户输入，进入下一条。
            continue
        # 把用户消息转换成类似 OpenAI messages 的结构。
        human_messages.append(
            {
                "role": "user",
                "content": _safe_value(
                    _message_attribute(message, "content", "")
                ),
            }
        )
    # 对外统一返回 {"messages": [...]}，便于你理解请求结构。
    return {"messages": human_messages}


# 生成单次模型调用的详细记录。
def _llm_call_detail(message: Any) -> dict[str, Any]:
    # 当前 AIMessage 的元数据，里面有模型、Provider、finish_reason 等。
    metadata = _response_metadata(message)
    # 当前 AIMessage 的 token 用量。
    usage = _usage_for_message(message)
    # 返回单次模型调用的结构化详情。
    return {
        "messageId": _message_attribute(message, "id"),
        "modelProvider": (
            metadata.get("model_provider") or metadata.get("provider")
        ),
        "modelName": metadata.get("model_name") or metadata.get("model"),
        "finishReason": (
            metadata.get("finish_reason") or metadata.get("stop_reason")
        ),
        **usage,
        "latencyCheckpoint": _safe_value(
            dict(_latency_checkpoint(message))
        ) or None,
        "toolCalls": _safe_value(
            _message_attribute(message, "tool_calls", []) or []
        ),
    }


# 生成完整消息轨迹，方便你学习 Agent 内部“消息如何流动”。
def _message_trace(messages: Sequence[Any]) -> list[dict[str, Any]]:
    # trace 用来保存每条消息的简化记录。
    trace = []
    # 遍历 state 中的 HumanMessage / AIMessage / ToolMessage 等。
    for message in messages:
        # 先记录消息类型和内容，这是最基础的消息轨迹。
        item = {
            "type": type(message).__name__,
            "content": _safe_value(
                _message_attribute(message, "content", "")
            ),
        }

        # ToolMessage 或部分工具调用消息会带 name 字段。
        name = _message_attribute(message, "name")
        # 只有 name 存在时才写入，避免日志里出现大量 null。
        if name is not None:
            # name 通常是工具名，例如 get_user_location。
            item["name"] = name

        # ToolMessage 会通过 tool_call_id 对应某一次 AIMessage 发起的工具调用。
        tool_call_id = _message_attribute(message, "tool_call_id")
        # 只有 tool_call_id 存在时才写入。
        if tool_call_id is not None:
            # 这个字段能帮助你把 AIMessage.tool_calls 和 ToolMessage 对上。
            item["toolCallId"] = tool_call_id

        # 把当前消息摘要加入轨迹列表。
        trace.append(item)
    # 返回完整消息轨迹。
    return trace


# 对外暴露的主函数：把 agent.invoke(...) 的返回值整理成调用记录。
def build_response_record(
    response: Mapping[str, Any],
    include_details: bool = False,
) -> dict[str, Any]:
    """汇总一次 Agent 返回状态中的模型调用信息。

    ``usage`` 和 ``latencyMs`` 会累计 ``response["messages"]`` 中所有
    ``AIMessage``。复用同一个 ``thread_id`` 时，state 可能包含历史消息，
    因而这里反映的是当前 state 的累计值，不一定只是本轮新增消耗。

    ``latencyMs`` 读取 Provider 返回的
    ``latency_checkpoint.total_duration_ms``。Provider 未返回该字段时，
    结果为 ``None``；仅凭调用完成后的 response 无法反推端到端耗时。
    """

    # 主函数要求 response 是 Mapping，因为 LangChain Agent 返回的是 dict-like state。
    if not isinstance(response, Mapping):
        # 传错类型时尽早报错，避免后面出现更难理解的 AttributeError。
        raise TypeError("response 必须是 LangChain Agent 返回的 Mapping")

    # 从 Agent state 中取出 messages 列表。
    messages = _messages_from_response(response)
    # 只筛选 AIMessage，因为 token、模型名、finish_reason 都记录在模型消息上。
    ai_calls = [message for message in messages if _is_ai_message(message)]
    # 从全部 AIMessage 中提取最终可见的模型名和 Provider。
    model_info = _model_info(ai_calls)

    # 生成基础调用记录；默认只保留最常看的摘要字段。
    record = {
        "model": model_info["model"],
        "provider": model_info["provider"],
        "input": _extract_request_input(messages),
        "output": _safe_value(response.get("structured_response")),
        "usage": _sum_usage(ai_calls),
        "latencyMs": _sum_latency_ms(ai_calls),
    }

    # include_details=True 时，额外输出单次调用详情和完整消息轨迹。
    if include_details:
        # update 会把详细字段合并进基础 record。
        record.update(
            {
                "id": f"call_{uuid4().hex[:12]}",
                "capability": "agent_invoke",
                "status": "success",
                "latencySource": (
                    "sum_ai_message_latency_checkpoint_total_duration_ms"
                    if record["latencyMs"] is not None
                    else None
                ),
                "llmCallCount": len(ai_calls),
                "llmCalls": [
                    _llm_call_detail(message)
                    for message in ai_calls
                ],
                "messageTrace": _message_trace(messages),
            }
        )

    # 返回最终整理好的调用记录。
    return record


# 控制 from utils.call_records import * 时只导出 build_response_record。
__all__ = ["build_response_record"]
