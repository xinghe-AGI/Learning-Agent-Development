# ChatOpenAI 对象详解

---
参考资料：
- [LangChain：ChatOpenAI 集成](https://docs.langchain.com/oss/python/integrations/chat/openai)
- [LangChain：ChatOpenAI API Reference](https://reference.langchain.com/python/langchain-openai/chat_models/base/ChatOpenAI)
- [LangChain：Models](https://docs.langchain.com/oss/python/langchain/models)
- [OpenAI：Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create)
- [OpenAI：Responses API](https://platform.openai.com/docs/api-reference/responses/create)
---

## ChatOpenAI 是什么

`ChatOpenAI` 是 `langchain-openai` 提供的一个**具体 Chat Model 类**。它负责把 LangChain 的消息对象转换成 OpenAI API 请求，再把模型响应转换成 `AIMessage`。

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="MODEL_NAME")
```

创建 `ChatOpenAI` 对象，主要是在保存模型名、服务地址、鉴权信息和请求默认参数。**实例化对象通常不会立即向模型服务发请求**；调用 `invoke()`、`stream()`、`batch()` 等方法时，才会真正访问后端。

`ChatOpenAI` 原生面向 OpenAI 官方 API 规范，也可以通过 `base_url` 连接 OpenAI-compatible 服务。不过，一个参数最终能否生效，要同时满足三个条件：

> 当前 `langchain-openai` 版本支持、后端接口实现了对应协议、所选模型支持该能力。

所以，“`ChatOpenAI` 接受这个参数”并不等于“任意兼容服务和任意模型都支持这个参数”。

当前项目使用的是 `langchain-openai==1.1.6`。在线 API Reference 可能对应更新版本，新增字段不能直接假定在当前项目中可用。

## 当前项目怎样创建 ChatOpenAI

`utils/llms.py` 当前生效的代码是：

```python
llm_chat = ChatOpenAI(
    base_url=config["base_url"],
    api_key=config["api_key"],
    model=config["chat_model"],
    temperature=DEFAULT_TEMPERATURE,
    timeout=30,
    max_retries=2,
    extra_body=(
        {"enable_thinking": False}
        if llm_type == "qwen"
        else None
    ),
)
```

这段代码为不同的 `llm_type` 复用同一个 `ChatOpenAI` 类，变化的是从 `MODEL_CONFIGS` 中取出的地址、Key 和模型名。因此，这些后端都必须提供 `ChatOpenAI` 能够理解的 OpenAI-compatible 接口。

| 当前参数 | 在项目里的作用 |
| --- | --- |
| `base_url` | 指定当前模型服务的 API 基础地址；它决定请求发往哪里，不决定模型名称 |
| `api_key` | 提供访问该服务所需的凭据；值来自本机 `.env` |
| `model` | 指定后端实际调用的聊天模型 ID |
| `temperature` | 设置默认采样随机性；项目使用统一值，便于比较不同模型 |
| `timeout=30` | 单次请求等待超过 30 秒后按超时处理，避免无限阻塞 |
| `max_retries=2` | API 请求出现可重试异常时，最多执行客户端层重试 |
| `extra_body` | 传递兼容服务的非标准扩展字段；当前仅为 Qwen 关闭思考模式 |

这里的 `extra_body={"enable_thinking": False}` 是 Qwen 服务扩展，不是 OpenAI 标准字段。当前示例这样做，是为了避免思考模式与强制工具调用／`ToolStrategy` 结构化输出之间出现兼容问题。

## 构造参数应该分层理解

不需要每次都把所有参数填满。更实用的理解方式是：先配置连接模型所必需的参数，再按任务需要添加生成控制、可靠性、流式或 Provider 扩展参数。

### 模型、地址与鉴权

| 参数 | 作用 | 使用提示 |
| --- | --- | --- |
| `model` | 后端模型 ID | 它不是 `openai`、`qwen` 这样的项目配置类型，也不是 Runnable 的名字 |
| `api_key` | API 凭据 | 官方 OpenAI 场景可从 `OPENAI_API_KEY` 环境变量自动读取；不要写死在源码中 |
| `base_url` | API 基础地址 | 连接官方 OpenAI 时通常不必传；连接网关、本地服务或兼容接口时传入 |
| `organization` | OpenAI Organization ID | 只有账号与服务确实使用 Organization 时才需要 |
| `name` | 给 Runnable 设置便于调试、追踪的名称 | 只影响运行标识，不会替代 `model` |

`model_provider` 不是 `ChatOpenAI` 的核心构造参数。它主要用于 `init_chat_model()` 选择具体 integration；直接写 `ChatOpenAI(...)` 时，具体类已经选定。

### 生成与采样参数

这些参数会成为该模型实例的默认生成设置：

| 参数 | 作用 | 注意点 |
| --- | --- | --- |
| `temperature` | 调整采样随机性 | 值越低通常越稳定，但不保证事实正确或每次绝对一致 |
| `top_p` | 只从累计概率达到阈值的候选 Token 中采样 | 通常不需要同时大幅调整 `temperature` 与 `top_p` |
| `max_completion_tokens` | 限制一次回答最多生成的 Token 数 | 在本项目依赖版本中会映射到内部字段 `max_tokens`；不要同时传入两种写法 |
| `stop_sequences` | 遇到指定字符串时停止继续生成 | 在本项目依赖版本中会映射到内部字段 `stop`；也可以只为某次调用传 `stop` |
| `n` | 一次请求生成几个候选结果 | 至少为 `1`；流式模式下通常必须为 `1`，增加它也会增加消耗 |
| `presence_penalty` | 更倾向于引入尚未出现的新内容 | 是否支持及有效范围取决于后端 |
| `frequency_penalty` | 降低高频重复内容再次出现的概率 | 不等于事实纠错或重复文本的完整修复方案 |
| `seed` | 请求后端尽量进行可复现采样 | 只提供近似稳定性，仍依赖服务和模型实现 |
| `logprobs` | 请求返回所选 Token 的对数概率 | 会增加响应数据量，兼容服务不一定实现 |
| `top_logprobs` | 返回每个位置概率最高的若干候选 Token | 通常需要同时启用 `logprobs=True` |
| `logit_bias` | 调整指定 Token 被生成的倾向 | 需要了解对应模型的 Token ID，属于高级参数 |
| `reasoning_effort` | 调整支持推理模型的推理投入 | 主要对应支持该字段的 Chat Completions 模型 |
| `reasoning` | 配置 Responses API 的推理选项 | 只在相应 API、服务和模型支持时有效 |
| `verbosity` | 调整支持模型的回答详略程度 | 不是通用模型参数，不能替代 Prompt 中的输出要求 |

采样参数的组合、适用场景和实验方法见 [[02_模型采样参数与ChatOpenAI]]。这篇笔记只说明它们在 `ChatOpenAI` 对象中的位置。

### 超时、重试与请求可靠性

| 参数 | 作用 | 注意点 |
| --- | --- | --- |
| `timeout` | 限制单次 API 请求的等待时间 | 超时只负责结束等待，不会让模型本身变快 |
| `max_retries` | 配置 OpenAI 客户端层的请求重试次数 | 主要处理连接、限流等可重试错误，不能修复回答内容错误 |
| `rate_limiter` | 注入 LangChain 请求限流器 | 适合主动控制并发和请求速率 |
| `cache` | 配置 LangChain 层响应缓存 | 流式 `.stream()` 不使用普通响应缓存 |

Runnable 还可以使用 `.with_retry()`。它属于更外层的 Runnable 重试，可能覆盖解析器或组合链异常；`max_retries` 则主要是模型客户端的 API 请求重试。两层同时设置时，要评估最坏情况下的实际调用次数，避免重试被成倍放大。

### 流式输出与用量

| 参数或方法 | 作用 | 注意点 |
| --- | --- | --- |
| `.stream(input)` / `.astream(input)` | 向调用方逐块返回 `AIMessageChunk` | 这是业务代码消费流式结果的主要入口 |
| `streaming` | 让普通生成内部使用流式路径并聚合结果 | 不等同于调用方一定能逐块收到输出 |
| `stream_usage` | 请求在流式结果中附带 Token usage | 第三方 `base_url` 是否支持，需要实际验证 |
| `disable_streaming` | 强制旁路流式实现 | 设为 `"tool_calling"` 时，可只在传入 tools 的调用中旁路流式 |
| `include_response_headers` | 把响应头放入响应元数据 | 适合排查 request ID、限流信息等；具体字段由服务端决定 |

如果目标是边生成边展示内容，应直接使用 `.stream()` 或 `.astream()`；不要只设置 `streaming=True` 就假定调用方会自动收到分块结果。

### Responses API 相关参数

`ChatOpenAI` 不只可以调用 Chat Completions，也支持在满足条件时调用 Responses API。以下参数需要后端接口与模型共同支持：

| 参数 | 作用 | 注意点 |
| --- | --- | --- |
| `use_responses_api` | 显式选择是否使用 Responses API | 某些 Responses 专属能力也可能让 LangChain自动选择该 API |
| `use_previous_response_id` | 自动使用最近一次响应 ID 延续服务端会话 | 会从发送 payload 中移除该响应之前的消息；不等于 LangGraph checkpointer |
| `output_version` | 控制 Responses API 内容怎样写入 `AIMessage` | 如果业务代码依赖具体内容结构，应该固定并测试版本 |
| `include` | 请求额外返回指定响应内容 | 可用项目取决于 API 与模型能力 |
| `store` | 请求服务端保存响应 | 涉及数据保存策略，使用前要确认隐私和服务端行为 |
| `truncation` | 配置输入超长时的截断行为 | 不应把自动截断当作上下文管理方案 |
| `service_tier` | 请求服务端使用指定服务层级 | 可用值、性能与费用由服务端决定 |

`use_previous_response_id` 是 OpenAI 服务端响应链能力；`InMemorySaver` 则是在 LangGraph 一侧保存 Agent 状态。二者所处层级不同，不能互相替代。

### OpenAI-compatible 服务扩展

这一组参数最容易混淆：

| 参数 | 应该放什么 | 例子 |
| --- | --- | --- |
| `model_kwargs` | OpenAI 标准 API 中存在、但当前类没有显式声明的顶层请求字段 | 某个较新的标准请求参数 |
| `extra_body` | 第三方兼容服务自定义的非 OpenAI 标准字段 | Qwen 的 `{"enable_thinking": False}` |
| `disabled_params` | 标记当前后端不支持、包装器不应自动传递的参数 | 某个兼容服务不支持并行工具调用时禁用对应字段 |

不要把第三方扩展放进 `model_kwargs`，也不要把 OpenAI 标准字段随意塞进 `extra_body`。前者会作为标准请求顶层参数转发，后者会进入扩展请求体；它们在最终 payload 中的位置不同。

其他较少使用的连接参数包括：

- `default_headers`：为每次请求追加默认 HTTP Header。
- `default_query`：为每次请求追加默认查询参数。
- `openai_proxy`：配置访问服务时使用的代理地址。
- `http_client`、`http_async_client`：注入自定义同步／异步 HTTP 客户端。
- `tiktoken_model_name`：指定本地 Token 计数使用的 tokenizer 模型名。
- `custom_get_token_ids`：提供自定义文本到 Token ID 的转换函数。

`client`、`async_client`、`root_client`、`root_async_client` 虽然可能出现在模型字段中，但更接近内部客户端或高级依赖注入，不应作为日常初始化的首选参数。

### 追踪与 Runnable 通用配置

`ChatOpenAI` 还继承了 LangChain Runnable／模型基类的一些通用参数：

| 参数 | 作用 |
| --- | --- |
| `callbacks` | 注册模型调用开始、结束、流式 Token 和错误等回调 |
| `tags` | 为调用添加标签，便于 LangSmith 等观测系统筛选 |
| `metadata` | 为运行记录附加业务元数据 |
| `verbose` | 打开更详细的本地运行输出 |
| `name` | 给模型 Runnable 设置可辨识的运行名称 |
| `profile` | 提供或覆盖模型能力画像，属于高级配置 |

这些字段主要影响 LangChain 运行与观测，不会改变后端实际使用的模型 ID。

## 构造参数、单次调用参数与能力绑定

这是使用 `ChatOpenAI` 时最重要的边界：

| 配置位置 | 作用范围 | 典型内容 |
| --- | --- | --- |
| `ChatOpenAI(...)` | 作为这个实例每次请求的默认值 | `model`、`base_url`、`temperature`、`timeout` |
| `invoke(input, config=..., **kwargs)` | 只影响当前一次调用 | 本次消息、`stop`、本次请求覆盖参数 |
| `bind(**kwargs)` | 返回一个预先绑定请求参数的新 Runnable，不立即调用模型 | 某个任务反复使用的固定请求参数 |
| `bind_tools(...)` | 把工具 Schema 和工具选择策略绑定给模型 | `tools`、`tool_choice`、`parallel_tool_calls`、`strict` |
| `with_structured_output(...)` | 返回负责生成、解析和校验结构化结果的包装器 | `schema`、`method`、`include_raw`、`strict` |

例如：

```python
llm = ChatOpenAI(
    model="MODEL_NAME",
    temperature=0,
    timeout=30,
)

# 只绑定工具定义和工具调用策略，不会在这里执行工具
llm_with_tools = llm.bind_tools(
    tools=[get_weather],
    tool_choice="auto",
)

# invoke 才发送本次消息并获得模型响应
response = llm_with_tools.invoke("深圳今天的天气怎么样？")
```

模型返回的 `tool_calls` 只是工具调用意图，真正执行 Python 函数的是业务代码或 Agent runtime。详见 [[04_Tools与FunctionCalling]]。

`input/messages`、`tools`、`tool_choice` 和结构化输出 Schema 都不应该一股脑写进 `ChatOpenAI` 构造函数：

- `input` 或消息列表交给 `invoke()`、`stream()`。
- `tools`、`tool_choice`、`parallel_tool_calls` 通常交给 `bind_tools()`。
- `schema`、`method`、`include_raw` 通常交给 `with_structured_output()`。
- 在 `create_agent()` 中，工具与 `response_format` 由 Agent 装配层统一处理。
- `invoke(..., config={...})` 中的 `config` 是 Runnable 运行配置，不是发给模型服务的 JSON payload。

## 怎样读取返回结果

`invoke()` 返回的是 LangChain `AIMessage`，而不是直接返回 OpenAI SDK 的原始字典：

```python
response = llm.invoke("你好，请用一句话介绍 LangChain。")

print(response.content)
print(response.tool_calls)
print(response.usage_metadata)
print(response.response_metadata)
```

| 字段 | 常见内容 |
| --- | --- |
| `content` | 模型生成的文本或内容块 |
| `tool_calls` | 模型提出的标准化工具调用意图 |
| `usage_metadata` | 输入、输出和总 Token 用量 |
| `response_metadata` | 模型名、finish reason、Provider 原始元数据等 |

第三方兼容服务的非标准响应字段不一定会被 `ChatOpenAI` 完整保留。请求与响应对象的进一步拆解见 [[07_模型请求与响应结构]]。

## 一套够用的初始化思路

学习和调试阶段，可以先只配置这一组参数：

```python
llm = ChatOpenAI(
    model=config["chat_model"],
    base_url=config["base_url"],
    api_key=config["api_key"],
    temperature=0,
    timeout=30,
    max_retries=2,
)
```

然后按实际需求逐层增加：

1. 需要控制输出长度，再设置 `max_completion_tokens`。
2. 需要工具调用，使用 `bind_tools()` 或把工具交给 `create_agent()`。
3. 需要结构化输出，使用 `with_structured_output()` 或 Agent 的 `response_format`。
4. 需要边生成边展示，改用 `.stream()`，并验证 `stream_usage`。
5. 需要兼容服务扩展，再添加经过后端文档确认的 `extra_body`。

这样出现问题时，可以判断它来自连接配置、模型采样、工具协议、结构化输出，还是 Provider 扩展，而不是让所有参数同时参与排错。

## 常见误区

- **`base_url` 能返回文本，就代表完全兼容。** 实际上 tools、structured output、streaming、usage 和非标准字段都要单独验证。
- **构造函数接受参数，就代表模型一定支持。** 参数还要经过后端协议和具体模型能力两层验证。
- **`max_retries` 可以修复错误答案。** 它主要重试请求异常，不负责语义校验或结构化输出修复。
- **低 `temperature` 等于绝对确定。** 服务端实现、模型版本和并发环境仍可能造成差异。
- **`streaming=True` 等于业务端逐块消费。** 真正逐块迭代应该调用 `.stream()` 或 `.astream()`。
- **`extra_body` 与 `model_kwargs` 可以互换。** 二者承载的字段类型和最终请求位置不同。
- **把 `use_previous_response_id` 理解为 Agent 短期记忆。** 这是不准确的。它是服务端响应链；Agent state 和 checkpointer 属于 LangGraph 层。
- **`ChatOpenAI` 也能生成 Embedding。** Chat Model 与 Embedding 是两种独立接口，项目使用的是另一个 `OpenAIEmbeddings` 对象。

## 怎样检查安装版本支持什么

先确认当前环境版本：

```powershell
pip show langchain-openai
```

再查看运行环境中实际声明的字段及别名：

```python
from langchain_openai import ChatOpenAI

for field_name, field_info in ChatOpenAI.model_fields.items():
    print(field_name, field_info.alias)
```

这个结果适合确认“当前项目代码能传什么”；官方文档适合确认“对应参数表达什么能力”。升级 `langchain-openai` 后，应重新核对字段、默认值和后端兼容性。

## 关联笔记

- [[01_多厂商LLM集成与API协议]]：理解为什么当前项目能用一个 `ChatOpenAI` 连接多组 OpenAI-compatible 地址。
- [[11_init_chat_model方法详解]]：理解统一工厂怎样选择 Provider、创建模型并支持运行时配置。
- [[09_ChatOpenAI与init_chat_model的区别]]：比较直接创建具体类与使用模型工厂。
- [[02_模型采样参数与ChatOpenAI]]：继续学习采样参数怎样影响生成。
- [[07_模型请求与响应结构]]：理解消息输入、`AIMessage` 和响应元数据。
- [[04_Tools与FunctionCalling]]：理解工具定义、工具调用意图和业务执行。
- [[03_结构化输出]]：理解结构化输出策略与失败修复。
