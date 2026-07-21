# ProviderStrategy 详解

---
参考资料：
- [LangChain：Structured output](https://docs.langchain.com/oss/python/langchain/structured-output)
- [OpenAI：Structured model outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
---

## 什么是 ProviderStrategy

**ProviderStrategy 是 LangChain 在 Agent 层调用模型提供商原生结构化输出能力的策略。**

它不是把目标 Schema 包装成人工工具，而是把 Schema 交给底层 Provider，由 Provider 在生成阶段尽量约束模型输出。成功后，LangChain 仍然把解析结果放入最终状态的 `structured_response`。

因此，ProviderStrategy 的核心前提是：Provider、模型、API 协议和 LangChain integration 都支持原生 Structured Outputs。

## 当前项目中的写法

当前 `agent.py` 默认直接传入 `WeatherResponseFormat`，让 LangChain 自动选择策略：

```python
response_format=WeatherResponseFormat
```

如果要明确测试 Provider 原生结构化输出，可以改成：

```python
from langchain.agents.structured_output import ProviderStrategy


agent = create_agent(
    model=llm_chat,
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
    context_schema=Context,
    response_format=ProviderStrategy(
        schema=WeatherResponseFormat,
        strict=True,
    ),
    checkpointer=checkpointer,
)
```

这段代码表达的是：要求 LangChain 尽量使用模型服务的原生结构化输出能力，而不是把最终结果伪装成一次工具调用。

使用 Qwen、OneAPI 或其他 OpenAI-compatible `base_url` 时，需要单独验证该网关是否完整支持目标 Provider 的 `json_schema`、`strict` 和工具并用能力。**OpenAI-compatible 不等于 Provider 原生 Structured Outputs 一定可用。**

## 主要参数

| 参数 | 作用 | 学习重点 |
| --- | --- | --- |
| `schema` | 定义最终结构化结果的字段、类型和约束 | 可以是 Pydantic、dataclass、TypedDict 或 JSON Schema |
| `strict` | 请求 Provider 严格遵循 Schema | 依赖 LangChain 版本、Provider 能力和模型支持范围 |

最小写法：

```python
response_format=ProviderStrategy(WeatherResponseFormat)
```

更适合结构化输出实验的写法：

```python
response_format=ProviderStrategy(
    schema=WeatherResponseFormat,
    strict=True,
)
```

`strict=True` 的含义不是保证事实正确，而是在 Provider 支持的 Schema 子集内增强结构约束。安全拒答、token 截断、模型能力不足、Schema 不受支持等情况仍然需要业务代码处理。

## ProviderStrategy 的工作机制

ProviderStrategy 的关键路径是：

1. 开发者把 Schema 交给 `ProviderStrategy`。
2. LangChain integration 将 Schema 转成 Provider API 支持的结构化输出参数。
3. Provider 在模型生成阶段施加结构约束。
4. LangChain 接收 Provider 返回结果，解析为 Python 对象，并写入 `structured_response`。

这条路线的优势在于结构约束更靠近模型生成阶段。相比 ToolStrategy，ProviderStrategy 通常不需要人工结构化输出工具消息，响应状态也会更接近普通模型最终回答。

## 适合使用 ProviderStrategy 的场景

- **Provider 原生支持明确**：例如目标模型、API 和 LangChain integration 都确认支持原生结构化输出。
- **结构可靠性优先**：希望减少漏字段、额外字段和类型错误。
- **最终结果不需要表现为工具调用**：结构化输出是最终回答，不是一次业务函数调用。
- **Schema 相对稳定**：字段、枚举、嵌套对象和约束已经清晰。

## 局限性

- **模型和 Provider 绑定更强**：换模型、换网关、换 API 版本后可能需要重新验证。
- **Schema 子集受限制**：不是所有 JSON Schema 特性都能被原生 strict 模式支持。
- **错误通常更靠前暴露**：Schema 不受支持时，请求阶段可能直接失败，而不是进入模型修复循环。
- **与工具并用需要验证**：Agent 同时使用业务工具和原生结构化输出时，模型必须支持两种能力协同工作。

## 和 OpenAI API 的关系

OpenAI 原生结构化输出常见于 `response_format=json_schema` 或 Responses API 的 `text.format`。在 LangChain 中，ProviderStrategy 相当于让 integration 代替业务代码组装这些底层参数。

底层 API 的具体写法可以参考 [13_OpenAI API结构化输出](<13_OpenAI API结构化输出.md>)。ProviderStrategy 的学习重点不在于背诵 API 字段，而在于判断当前模型服务是否真的具备原生结构化输出能力。

## 和其他笔记的关系

- [03_结构化输出](<03_结构化输出.md>)：查看当前项目中 `response_format` 的位置。
- [14_ToolStrategy详解](<14_ToolStrategy详解.md>)：理解工具调用路线如何生成结构化结果。
- [16_ToolStrategy和ProviderStrategy区别](<16_ToolStrategy和ProviderStrategy区别.md>)：比较两种策略的选择条件和失败形态。
- [17_结构化输出失败原因与处理](<17_结构化输出失败原因与处理.md>)：排查 Provider 原生结构化输出不可用、Schema 不兼容和 strict 失败。
