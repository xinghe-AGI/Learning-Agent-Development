# ToolStrategy 详解

---
参考资料：
- [LangChain：Structured output](https://docs.langchain.com/oss/python/langchain/structured-output)
---

## 什么是 ToolStrategy

**ToolStrategy 是 LangChain 在 Agent 层使用工具调用实现结构化输出的策略。**

它会把目标 Schema 转换成一个“结构化输出工具”。模型不是直接在 `content` 中返回 JSON，而是通过工具调用参数提交字段；LangChain 再把工具参数解析、校验，并写入最终状态的 `structured_response`。

这条路线的重点不在于工具是否执行真实业务逻辑，而在于借用工具调用协议承载结构化数据。业务工具会执行 Python 函数；结构化输出工具主要用于接收和校验最终字段。

## 工作机制

ToolStrategy 的一次典型执行可以拆成四步：

1. 开发者把 Python Schema 或 JSON Schema 传给 `ToolStrategy`。
2. LangChain 把该 Schema 表示为模型可调用的结构化输出工具。
3. 模型在合适时机发起工具调用，并把目标字段放入工具参数。
4. LangChain 校验参数，成功后写入 `response["structured_response"]`；失败时按 `handle_errors` 决定是否反馈错误并重试。

因此，ToolStrategy 的稳定性主要取决于两个条件：

- 模型是否能够稳定理解工具描述并生成合法工具参数。
- LangChain 是否能够用目标 Schema 成功解析模型提交的参数。

## 当前项目中的写法

当前 `agent.py` 默认使用直接传 Schema 的写法：

```python
agent = create_agent(
    model=llm_chat,
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
    context_schema=Context,
    response_format=WeatherResponseFormat,
    checkpointer=checkpointer,
)
```

如果要明确固定为工具调用路线，可以改成：

```python
from langchain.agents.structured_output import ToolStrategy


agent = create_agent(
    model=llm_chat,
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
    context_schema=Context,
    response_format=ToolStrategy(WeatherResponseFormat),
    checkpointer=checkpointer,
)
```

这种写法适合验证 OpenAI-compatible 模型服务是否能稳定走工具调用协议。当前项目使用 `ChatOpenAI` 接入 Qwen 兼容接口时，显式使用 ToolStrategy 可以减少“自动策略选择”带来的不确定性。

## 主要参数

| 参数 | 作用 | 学习重点 |
| --- | --- | --- |
| `schema` | 定义最终结构化结果的字段、类型和约束 | 可以是 Pydantic、dataclass、TypedDict 或 JSON Schema |
| `tool_message_content` | 自定义结构化输出工具成功后的 `ToolMessage` 文本 | 影响消息记录可读性，不改变 `structured_response` 的对象形状 |
| `handle_errors` | 控制结构化输出校验失败后的处理方式 | 决定是自动反馈错误并重试，还是直接抛出异常 |

最小写法只需要传 Schema：

```python
response_format=ToolStrategy(WeatherResponseFormat)
```

如果希望工具结果消息更清晰，可以写：

```python
response_format=ToolStrategy(
    schema=WeatherResponseFormat,
    tool_message_content="已生成天气结构化响应。",
)
```

## handle_errors 怎样理解

`handle_errors` 是 ToolStrategy 的重要参数。它决定模型提交的结构化参数不符合 Schema 时，LangChain 是否把错误反馈给模型，让模型尝试修正。

| 写法 | 行为 |
| --- | --- |
| `True` | 默认行为，捕获结构化输出相关错误，并把错误反馈给模型重试 |
| `False` | 不自动修复，错误直接抛出 |
| 字符串 | 使用固定错误消息反馈给模型 |
| 异常类型或异常类型元组 | 只处理指定类型的错误 |
| 回调函数 | 根据异常内容动态生成反馈消息 |

示例：

```python
response_format=ToolStrategy(
    schema=WeatherResponseFormat,
    handle_errors="结构化输出不符合要求，请只返回一个符合 Schema 的结果。",
)
```

更细的错误处理可以交给回调函数：

```python
def handle_structured_error(error: Exception) -> str:
    return f"结构化输出校验失败：{error}。请修正字段后重新提交。"


response_format=ToolStrategy(
    schema=WeatherResponseFormat,
    handle_errors=handle_structured_error,
)
```

错误原因和处理顺序可以参考 [[17_结构化输出失败原因与处理]]。

## 适合使用 ToolStrategy 的场景

- **OpenAI-compatible 服务接入**：模型服务兼容聊天和工具调用，但不确定是否支持原生 `json_schema`。
- **需要和业务工具一起使用**：Agent 先调用业务工具获取数据，最后再通过结构化输出工具提交最终结果。
- **希望错误反馈可控**：字段缺失、类型错误或多次结构化提交时，可以通过 `handle_errors` 控制修复策略。
- **需要支持更多模型**：只要模型工具调用能力可靠，就不一定依赖 Provider 原生结构化输出。

## 局限性

- **它依赖工具调用能力**：模型如果工具调用不稳定，结构化输出也会不稳定。
- **它不是 Provider 原生约束**：结构校验主要发生在 LangChain 侧，而不是 Provider 生成阶段。
- **消息链更长**：结构化结果会表现为一次工具调用和工具结果，调试时需要区分业务工具与结构化输出工具。
- **结构正确不等于事实正确**：即使 Schema 校验通过，仍需要业务校验字段值。

## 和其他笔记的关系

- [[03_结构化输出]]：查看当前项目怎样把 Schema 接入 `create_agent()`。
- [[15_ProviderStrategy详解]]：理解 Provider 原生结构化输出路线。
- [[16_ToolStrategy和ProviderStrategy区别]]：判断何时使用 ToolStrategy，何时使用 ProviderStrategy。
- [[04_Tools与FunctionCalling]]：理解工具调用、工具结果和 `tool_call_id` 的基础协议。
