# ToolStrategy 和 ProviderStrategy 区别

---
参考资料：
- [LangChain：Structured output](https://docs.langchain.com/oss/python/langchain/structured-output)
---

## 它们的核心关系

**ToolStrategy 和 ProviderStrategy 都是 LangChain Agent 的结构化输出策略，区别在于 Schema 约束发生在哪里。**

ToolStrategy 借用工具调用协议承载最终字段；ProviderStrategy 调用模型提供商的原生结构化输出能力。两者在 LangChain Agent 的最终读取方式一致：成功后都从 `response["structured_response"]` 读取结构化对象。

当前项目默认写法是：

```python
response_format=WeatherResponseFormat
```

这属于直接传 Schema，让 LangChain 自动选择策略。如果想固定实验路线，可以显式写成：

```python
response_format=ToolStrategy(WeatherResponseFormat)
```

或：

```python
response_format=ProviderStrategy(WeatherResponseFormat, strict=True)
```

## 主要区别

| 对比项 | ToolStrategy | ProviderStrategy |
| --- | --- | --- |
| 结构承载方式 | 人工结构化输出工具 | Provider 原生 Structured Outputs |
| 主要依赖 | 模型支持工具调用 | Provider、模型、API 和 integration 支持原生结构化输出 |
| Schema 约束位置 | 模型生成工具参数后，由 LangChain 解析和校验 | Provider 在生成阶段施加结构约束，LangChain 再解析 |
| 消息形状 | 通常会看到结构化输出工具调用和确认 `ToolMessage` | 通常不需要人工结构化输出工具消息 |
| 错误修复 | 可通过 `handle_errors` 把验证错误反馈给模型重试 | 更多依赖 Provider 返回错误、拒答或结构化输出失败信息 |
| 兼容性 | 对支持工具调用的模型更通用 | 对 Provider 原生能力要求更高 |
| 适合场景 | OpenAI-compatible 服务、工具调用稳定、需要可控重试 | 原生支持明确、结构可靠性优先、Schema 稳定 |

## 什么时候先用 ToolStrategy

优先考虑 ToolStrategy 的典型场景：

- 当前模型服务是 Qwen、OneAPI、Ollama 网关或其他 OpenAI-compatible 接口。
- 已经确认工具调用可用，但不确定原生 `json_schema` 是否可用。
- Agent 本身需要先调用业务工具，再提交最终结构化结果。
- 希望通过 `handle_errors` 控制字段缺失、类型错误和多结构化输出的修复方式。

对学习项目而言，ToolStrategy 更适合观察 `AIMessage.tool_calls`、`ToolMessage`、`tool_call_id` 和 `structured_response` 之间的关系。

## 什么时候使用 ProviderStrategy

优先考虑 ProviderStrategy 的典型场景：

- 目标 Provider 明确支持原生 Structured Outputs。
- 目标模型的 LangChain integration 能正确声明或识别结构化输出能力。
- 希望结构约束尽量发生在模型生成阶段，而不是只在 LangChain 解析阶段发现错误。
- Schema 已经收敛，字段、类型、枚举、嵌套对象和额外字段策略比较稳定。

ProviderStrategy 更适合生产中对结构稳定性要求较高的场景，但前提是模型和 Provider 能力已经验证。

## 直接传 Schema 时发生什么

在 `create_agent()` 中直接传 Schema：

```python
response_format=WeatherResponseFormat
```

表示把策略选择交给 LangChain。通常规则是：如果模型 profile 显示支持原生结构化输出，则使用 ProviderStrategy；否则使用 ToolStrategy。

这条路线代码最短，但排查兼容性时不够显式。学习时可以按下面顺序实验：

1. 先使用直接 Schema，观察是否能得到 `structured_response`。
2. 如果需要确认工具调用路线，改成 `ToolStrategy(WeatherResponseFormat)`。
3. 如果需要验证 Provider 原生能力，改成 `ProviderStrategy(WeatherResponseFormat, strict=True)`。
4. 比较响应中的 `messages`、`tool_calls`、`ToolMessage`、`finish_reason` 和错误信息。

## 怎样从响应判断大致路线

| 观察点 | 可能说明 |
| --- | --- |
| 最后出现结构化输出工具调用 | 大概率走 ToolStrategy 或工具调用式结构化路线 |
| 有确认性的结构化输出 `ToolMessage` | LangChain 已把工具参数解析成结构化响应 |
| 没有人工结构化工具消息，但有 `structured_response` | 可能走 ProviderStrategy 或 integration 做了更底层的封装 |
| 请求阶段报 Schema 不支持 | 常见于 ProviderStrategy 或 strict Schema 不兼容 |
| 字段缺失、类型错误后出现错误反馈再重试 | 常见于 ToolStrategy 的 `handle_errors` 机制 |

这些判断需要结合模型、Provider、LangChain 版本和具体 integration 一起看，不能只凭一个字段下结论。

## 实用选择顺序

复习和实验时可以按这个顺序判断：

1. **先确认模型是否支持工具调用。** 如果工具调用不稳定，ToolStrategy 和 Agent 工具链都会受影响。
2. **再确认 Provider 原生结构化输出是否可用。** OpenAI-compatible 聊天接口可用，不代表原生 `json_schema` 可用。
3. **学习调试优先 ToolStrategy。** 它能直接看到工具调用链路，适合理解 Agent 内部状态。
4. **生产可靠性优先 ProviderStrategy。** 前提是 Provider 原生能力、Schema 子集和错误处理都验证通过。
5. **保留失败降级方案。** ProviderStrategy 不可用时可改用 ToolStrategy；工具调用不可靠时再退回 JSON Mode 加本地校验。

## 和其他笔记的关系

- [14_ToolStrategy详解](<14_ToolStrategy详解.md>)：理解工具调用路线的参数、消息和错误处理。
- [15_ProviderStrategy详解](<15_ProviderStrategy详解.md>)：理解 Provider 原生结构化输出路线。
- [17_结构化输出失败原因与处理](<17_结构化输出失败原因与处理.md>)：按照失败层级排查两种策略的异常。
- [13_OpenAI API结构化输出](<13_OpenAI API结构化输出.md>)：理解 ProviderStrategy 背后的底层 API 能力。
