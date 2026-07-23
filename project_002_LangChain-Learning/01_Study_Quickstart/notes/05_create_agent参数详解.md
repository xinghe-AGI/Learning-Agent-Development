# create_agent 参数详解

---
参考资料：
- [LangChain：Agents](https://docs.langchain.com/oss/python/langchain/agents)
- [LangChain API Reference：create_agent](https://reference.langchain.com/python/langchain/agents/factory/create_agent)
- [LangChain：Structured output](https://docs.langchain.com/oss/python/langchain/structured-output)
---

## create_agent 创建的是什么

**`create_agent()` 创建的是一个基于 LangGraph 的 Agent graph，用来让模型在“调用模型”和“执行工具”之间循环，直到得到最终结果。**

它不是单纯的 Chat Model 包装器。Chat Model 只负责一次模型调用；Agent graph 还负责工具执行、消息状态更新、结构化输出、短期记忆、中断、middleware 和运行配置。

一次典型执行包含这些阶段：

| 阶段 | 发生什么 | 结果写到哪里 |
| --- | --- | --- |
| 输入消息 | 用户消息进入 Agent state | `messages` |
| 调用模型 | 模型基于消息、system prompt 和 tools 做决策 | `AIMessage` |
| 判断工具 | 如果 `AIMessage` 包含 `tool_calls`，进入工具节点 | `AIMessage.tool_calls` |
| 执行工具 | Agent runtime 执行业务工具，并把结果回传 | `ToolMessage` |
| 再次调用模型 | 模型读取工具结果，继续决策或生成最终结果 | 新的 `AIMessage` |
| 返回状态 | 没有更多工具调用，或结构化输出完成 | Agent state |

因此，`create_agent()` 返回对象的重点不是“能不能聊天”，而是**能不能把模型、工具、状态和运行时上下文组织成一个可执行循环**。

## 参数总览

不同 LangChain 小版本的签名可能略有变化，阅读源码时应同时核对本机安装版本和官方 API Reference。LangChain 1.x 中常见参数可以按用途分成五组：

| 参数组   | 参数                                                               | 主要作用                      |
| ----- | ---------------------------------------------------------------- | ------------------------- |
| 核心执行  | `model`、`tools`、`system_prompt`                                  | 定义模型怎样决策、有哪些外部能力、遵守什么基础规则 |
| 输出结构  | `response_format`                                                | 定义最终是否返回结构化结果             |
| 状态与记忆 | `state_schema`、`context_schema`、`checkpointer`、`store`           | 管理线程状态、运行时依赖、短期记忆和长期存储    |
| 扩展与控制 | `middleware`、`interrupt_before`、`interrupt_after`、`transformers` | 扩展 Agent 行为、插入人工确认或转换逻辑   |
| 调试与标识 | `debug`、`name`、`cache`                                           | 观察执行过程、命名子图、配置缓存          |

常见函数形状可以理解为：

```python
create_agent(
    model,
    tools=None,
    *,
    system_prompt=None,
    middleware=(),
    response_format=None,
    state_schema=None,
    context_schema=None,
    checkpointer=None,
    store=None,
    interrupt_before=None,
    interrupt_after=None,
    debug=False,
    name=None,
    cache=None,
    transformers=None,
)
```

**参数不需要一次全部使用。** Quickstart 阶段优先理解 `model`、`tools`、`system_prompt`、`context_schema`、`response_format` 和 `checkpointer`。

## 当前项目怎样调用 create_agent

项目入口在 [agent.py](<../code/agent.py>)：

```python
agent = create_agent(
    model=llm_chat,
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
    context_schema=Context,
    response_format=WeatherResponseFormat,
    # response_format=ToolStrategy(WeatherResponseFormat),
    # response_format=ProviderStrategy(WeatherResponseFormat, strict=True),
    checkpointer=checkpointer,
)
```

这段代码表达了一个天气 Agent 的最小完整结构：

| 参数                | 项目对象                    | 作用                               |
| ----------------- | ----------------------- | -------------------------------- |
| `model`           | `llm_chat`              | 负责理解问题、选择工具、读取工具结果和生成最终响应        |
| `system_prompt`   | `SYSTEM_PROMPT`         | 指定天气预报员角色、地点确认规则和工具使用规则          |
| `tools`           | `get_tools()` 返回的工具列表   | 提供用户定位和天气查询能力                    |
| `context_schema`  | `Context`               | 声明运行时会传入 `user_id` 等上下文数据        |
| `response_format` | `WeatherResponseFormat` | 定义最终 `structured_response` 的字段结构 |
| `checkpointer`    | `InMemorySaver()`       | 按 `thread_id` 保存和恢复线程级消息状态       |

这个 Agent 能完成的事情包括：读取用户问题、调用定位工具、调用天气工具、生成结构化响应，并在相同 `thread_id` 下复用短期消息历史。

## model：Agent 的推理引擎

`model` 可以传模型标识字符串，也可以传已经初始化好的 Chat Model 对象。

| 写法 | 适合场景 |
| --- | --- |
| `model="openai:gpt-5.5"` | 使用默认 Provider 配置，快速创建 Agent |
| `model=ChatOpenAI(...)` | 需要控制 `base_url`、API Key、模型名、采样参数、超时和重试 |

项目中使用第二种方式：

```python
llm_chat, llm_embedding = get_llm(Config.LLM_TYPE)

agent = create_agent(
    model=llm_chat,
    tools=tools,
)
```

这种方式适合多厂商或 OpenAI-compatible 接入，因为模型初始化细节集中在 `code/utils/llms.py`。`create_agent()` 只接收已经配置好的 `llm_chat`，不再关心底层 `base_url` 和 API Key。

需要注意：使用结构化输出时，不应把已经 `bind_tools()` 的模型再交给 `create_agent()`。工具绑定由 Agent runtime 统一处理，否则容易和结构化输出策略冲突。

## tools：Agent 可执行的外部能力

`tools` 用来告诉模型有哪些外部能力可用。它可以是 LangChain Tool、Python callable 或工具定义字典。

项目中工具由 [tools.py](<../code/utils/tools.py>) 提供：

```python
tools = [
    get_weather_for_location,
    get_user_location,
]
```

传入 `create_agent()` 后，模型能在对话中生成工具调用意图：

```python
agent = create_agent(
    model=llm_chat,
    tools=tools,
)
```

`tools=None` 或空列表时，Agent 仍然可以调用模型，但不会进入工具调用循环。带工具的 Agent 能支持顺序调用、并行调用、动态工具选择、工具错误处理和工具结果写回消息状态。

工具定义、`AIMessage.tool_calls`、`ToolMessage.tool_call_id` 的细节可以参考 [04_Tools与FunctionCalling](<04_Tools与FunctionCalling.md>)。

## system_prompt：静态系统规则

`system_prompt` 用来设置 Agent 的基础角色、行为边界和工具使用原则。它可以是字符串，也可以是 `SystemMessage`。

项目中定义为天气预报员角色：

```python
SYSTEM_PROMPT = """你是一名擅长讲冷笑话的专业天气预报员。

你可以使用两个工具：

get_weather_for_location：用于获取某个具体地点的天气

get_user_location：用于获取用户当前所在位置

如果用户向你询问天气，一定要先确认地点。
如果从问题中可以判断出用户指的是“我所在的地方”的天气，就使用 get_user_location 工具来获取用户的位置。"""
```

它决定了模型在天气问题中优先确认地点，再选择合适工具。生产代码中，system prompt 应与工具名、工具描述和业务规则保持一致；如果工具名变化，prompt 中的工具说明也应同步调整。

动态系统提示不适合直接写死在 `system_prompt` 中。需要根据用户角色、权限或任务阶段改变提示词时，更适合使用 `middleware`。

## response_format：最终结构化输出

`response_format` 规定 Agent 最终是否返回结构化结果。它可以传：

| 写法 | 含义 | 适合场景 |
| --- | --- | --- |
| `None` | 不显式要求结构化输出 | 只需要自然语言回答 |
| `WeatherResponseFormat` | 直接传 Schema，让 LangChain 自动选择策略 | 默认学习入口或模型能力明确时 |
| `ToolStrategy(WeatherResponseFormat)` | 使用工具调用路线提交结构化字段 | OpenAI-compatible 服务或想明确调试工具调用路线 |
| `ProviderStrategy(WeatherResponseFormat, strict=True)` | 使用 Provider 原生结构化输出 | Provider 原生 Structured Outputs 能力明确时 |

项目中默认写法是：

```python
response_format=WeatherResponseFormat
```

成功后，结果进入：

```python
response["structured_response"]
```

结构化输出不是普通工具返回值。业务工具负责获取信息，`response_format` 负责定义最终业务对象。相关细节可以参考 [03_结构化输出](<03_结构化输出.md>)、[14_ToolStrategy详解](<14_ToolStrategy详解.md>) 和 [15_ProviderStrategy详解](<15_ProviderStrategy详解.md>)。

## context_schema：本次运行注入的上下文

`context_schema` 声明每次调用时可以注入什么运行时数据。项目中使用 `Context`：

```python
@dataclass
class Context:
    user_id: str
```

调用 Agent 时传入：

```python
response = agent.invoke(
    {"messages": [{"role": "user", "content": "外面的天气怎么样？"}]},
    config=config1,
    context=Context(user_id="1"),
)
```

工具通过 `ToolRuntime[Context]` 读取：

```python
@tool("get_user_location", description="根据用户 ID 检索用户信息。")
def get_user_location(runtime: ToolRuntime[Context]) -> str:
    user_id = runtime.context.user_id
```

**Runtime context 是本次调用注入的业务依赖，不是模型自己生成的消息。** 它适合放用户 ID、租户 ID、权限范围、请求来源、灰度开关等不希望模型编造的数据。

## checkpointer：短期记忆

`checkpointer` 用来保存和恢复单个线程的 Agent state。项目中使用：

```python
checkpointer = InMemorySaver()
```

调用时通过 `thread_id` 选择线程：

```python
config1 = {"configurable": {"thread_id": "1"}}
```

`checkpointer` 和 `thread_id` 需要配合使用：

| 条件 | 结果 |
| --- | --- |
| 有 `checkpointer`，并复用同一个 `thread_id` | 延续同一线程的消息历史 |
| 有 `checkpointer`，但每次使用不同 `thread_id` | 不同线程隔离 |
| 没有 `checkpointer` | 本地运行通常不能跨调用恢复线程状态 |

`InMemorySaver` 适合学习和本地实验。生产环境应使用持久化 checkpointer，并设计用户归属、权限校验、历史清理和数据保留策略。相关细节可以参考 [06_Agent短期记忆](<06_Agent短期记忆.md>)。

## state_schema、context_schema、config 和 store 的区别

这几个概念容易混淆：

| 对象               | 生命周期                    | 保存什么                                  | 项目中是否使用                     |
| ---------------- | ----------------------- | ------------------------------------- | --------------------------- |
| `state_schema`   | 线程内，可被 checkpointer 持久化 | messages 之外的可变状态，例如阶段、计数器、临时选择        | 未扩展                         |
| `context_schema` | 单次调用注入                  | 用户 ID、租户、权限、请求依赖                      | 使用 `Context(user_id=...)`   |
| `config`         | 单次 Runnable 执行配置        | `thread_id`、callbacks、tags、metadata 等 | 使用 `configurable.thread_id` |
| `store`          | 跨线程长期存储                 | 用户偏好、长期记忆、共享资料                        | 未配置                         |

**线程内可变数据放 state，本轮依赖放 context，执行控制放 config，跨线程长期数据放 store。**

项目中 `thread_id` 和 `user_id` 都写成 `"1"` 这类值，但职责完全不同：

- `thread_id` 决定读取和写入哪段对话历史。
- `user_id` 决定工具按哪个用户身份查询业务数据。

生产系统需要校验 thread 是否属于当前用户，不能只凭客户端传入的 `thread_id` 读取历史。

## middleware：扩展 Agent 行为

`middleware` 是生产化 Agent 的主要扩展点。它可以在模型调用、工具调用、prompt 构造、错误处理和安全检查等环节插入逻辑。

常见用途包括：

- **动态 Prompt**：根据用户角色或任务阶段生成 system prompt。
- **动态工具过滤**：根据权限、套餐或任务状态决定暴露哪些工具。
- **模型选择**：根据任务复杂度选择不同模型。
- **错误处理**：对模型调用或工具调用做重试、降级和错误包装。
- **安全守卫**：在工具执行前检查 PII、权限和高风险动作。
- **人工确认**：在写入、删除、付款等动作前暂停等待批准。

学习 Quickstart 时可以先不配置 middleware。进入生产设计时，middleware 往往比继续加长 system prompt 更可控。

## interrupt_before 和 interrupt_after

`interrupt_before` 与 `interrupt_after` 用来在指定图节点执行前或执行后暂停。它们适合做人类确认、调试和高风险动作控制。

| 参数 | 含义 | 适合场景 |
| --- | --- | --- |
| `interrupt_before` | 在某个节点执行前暂停 | 工具执行前人工确认 |
| `interrupt_after` | 在某个节点执行后暂停 | 查看工具结果后再决定是否继续 |

例如涉及转账、删除数据、发送外部消息等动作时，模型生成工具调用后不应直接执行。可以在工具节点前中断，由业务系统或人工审批决定是否继续。

## debug、name、cache 和 transformers

这些参数不是 Quickstart 的主线，但需要知道用途：

| 参数 | 作用 | 使用建议 |
| --- | --- | --- |
| `debug` | 打印图执行细节 | 本地排查 Agent 运行过程时启用 |
| `name` | 给 Agent 图命名 | 多 Agent 或子图组合时使用，推荐 `snake_case` |
| `cache` | 配置图运行缓存 | 需要缓存可重复模型或节点结果时使用 |
| `transformers` | 对图进行转换或增强 | 高级扩展场景使用，优先按官方版本文档确认 |

这些参数更偏框架扩展。学习时优先掌握核心参数，避免把配置项当作必须项。

## 调用 Agent 时传什么

`create_agent()` 只是装配 Agent。真正执行时，需要调用 `invoke()`、`stream()` 或其他 Runnable 方法。

项目中的典型调用是：

```python
response = agent.invoke(
    {"messages": [{"role": "user", "content": "外面的天气怎么样？"}]},
    config={"configurable": {"thread_id": "1"}},
    context=Context(user_id="1"),
)
```

这三个输入分属不同层：

| 输入                                            | 作用                       |
| --------------------------------------------- | ------------------------ |
| `{"messages": [...]}`                         | 给 Agent state 增加本轮用户消息   |
| `config={"configurable": {"thread_id": "1"}}` | 选择本轮要读写的线程状态             |
| `context=Context(user_id="1")`                | 给工具和 middleware 提供本次运行依赖 |
|                                               |                          |

返回结果是 Agent state。项目最常读取：

```python
response["messages"]
response["structured_response"]
```

`messages` 用于观察完整模型调用和工具调用链，`structured_response` 用于业务代码读取最终结构化结果。

## 参数选择顺序

设计一个 Agent 时，可以按下面顺序确定参数：

1. **先确定模型**：用字符串快速开始，或用 Chat Model 对象控制 `base_url`、采样、超时和重试。
2. **再确定工具**：只暴露任务需要的工具，工具名、description 和参数 Schema 要稳定。
3. **补充 system prompt**：写角色、边界和工具使用规则，不要把全部业务逻辑塞进 prompt。
4. **决定是否结构化输出**：需要业务字段时设置 `response_format`。
5. **区分 context 和 state**：本轮依赖放 context，线程内可变数据放 state。
6. **配置短期记忆**：需要多轮记忆时设置 checkpointer，并稳定传入 `thread_id`。
7. **生产化再加 middleware**：权限、错误处理、人工确认、动态模型和工具过滤放到 middleware。

## 相关学习笔记

- [04_Tools与FunctionCalling](<04_Tools与FunctionCalling.md>)：理解 `tools`、工具调用和工具结果回传。
- [03_结构化输出](<03_结构化输出.md>)：理解 `response_format` 和 `structured_response`。
- [14_ToolStrategy详解](<14_ToolStrategy详解.md>)：理解工具调用路线的结构化输出。
- [15_ProviderStrategy详解](<15_ProviderStrategy详解.md>)：理解 Provider 原生结构化输出。
- [06_Agent短期记忆](<06_Agent短期记忆.md>)：理解 `checkpointer`、`thread_id` 和线程状态。
- [07_模型请求与响应结构](<07_模型请求与响应结构.md>)：观察 `create_agent()` 执行后返回的完整 Agent state。
- [10_ChatOpenAI对象详解](<10_ChatOpenAI对象详解.md>)：理解传给 `model` 的 Chat Model 实例。

**最终记忆：`create_agent()` 是 Agent harness 的装配入口；`model` 负责推理，`tools` 提供动作，`system_prompt` 设置规则，`response_format` 约束最终结果，`context_schema` 注入本轮依赖，`checkpointer` 维护线程状态。**
