# OpenAI API 结构化输出

---
参考资料：
- [OpenAI：Structured model outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI：Function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [OpenAI：Responses Create API](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [OpenAI：Introducing Structured Outputs in the API](https://openai.com/index/introducing-structured-outputs-in-the-api/)
---

## 这篇笔记解决什么问题

**这篇笔记不是当前 Quickstart 项目的直接实现说明，而是用来理解 LangChain 结构化输出背后的底层 API 能力。**

当前项目默认把 `WeatherResponseFormat` 直接传给 `create_agent(response_format=...)`。如果显式改成 `ToolStrategy(WeatherResponseFormat)`，模型会通过一个人工结构化工具提交字段，然后由 LangChain 解析成 `response["structured_response"]`。

OpenAI API 的结构化输出则是另一层概念：Provider 自己在 API 层提供 JSON Mode、Function Calling、`json_schema`、`strict` 等能力。理解这些能力，是为了判断 LangChain 的 `ToolStrategy` 和 `ProviderStrategy` 到底在依赖什么。

核心结论：

**OpenAI API 讲的是“底层请求怎样约束模型输出”；LangChain 讲的是“框架怎样把 Python Schema 接入 Agent 调用链”。**

## OpenAI API 里有几种结构化方式

| 方式 | 主要配置 | 输出载体 | 结构保证 |
| --- | --- | --- | --- |
| Prompt 要求 JSON | 在 `messages` 或 `instructions` 中写格式要求 | 普通文本 | 不保证有效 JSON，也不保证符合 Schema |
| JSON Mode | `type: "json_object"` | 最终回答 | 通常保证是有效 JSON，但不保证字段符合指定 Schema |
| Function Calling | `tools` + `parameters` | 工具调用参数 | 参数是 JSON 结构，但默认未必严格符合完整 Schema |
| Function Calling + strict | 工具定义里设置 `strict: true` | 工具调用参数 | 在支持范围内约束工具参数符合 Schema |
| Structured Outputs | `type: "json_schema"` + `strict: true` | 最终回答 | 在支持范围内约束最终回答符合 Schema |

这里最容易混淆的是 Function Calling 和 Structured Outputs。

**Function Calling 适合表达“模型要调用哪个工具，以及工具参数是什么”。** 比如模型决定调用 `get_weather(city="北京")`。

**Structured Outputs 适合表达“模型最终回答必须是什么结构”。** 比如最终回答必须包含 `weather_location`、`weather_conditions` 和 `punny_response`。

## Python 代码中怎样直接使用

下面这些示例是**绕过 LangChain，直接使用 OpenAI Python SDK 调底层 Provider API**。这样写的目的不是替代当前项目里的 `ToolStrategy`，而是让自己看清楚底层请求参数到底放在哪里。

先准备客户端：

```python
import json

from openai import OpenAI


client = OpenAI()
MODEL = "你的模型名"
```

如果你连接的是 OpenAI-compatible 网关，客户端通常会多传 `base_url`。但要注意：**能兼容聊天接口，不代表一定兼容 JSON Mode、原生 `json_schema` 或 strict Function Calling。**

```python
client = OpenAI(
    api_key="不要把真实 Key 写进代码或笔记",
    base_url="https://你的-openai-compatible-endpoint/v1",
)
```

真实项目中应该从环境变量或 `.env` 读取 Key，不要硬编码。

### 用 JSON Mode 返回 JSON

JSON Mode 适合先解决“模型不要输出普通自然语言，而要输出 JSON 对象”的问题。

```python
response = client.responses.create(
    model=MODEL,
    input=[
        {
            "role": "system",
            "content": "你必须返回 JSON 对象，不要返回 Markdown。",
        },
        {
            "role": "user",
            "content": "提取这句话的信息：北京今天晴天。",
        },
    ],
    text={
        "format": {
            "type": "json_object",
        }
    },
)

data = json.loads(response.output_text)
print(data)
```

这里关键参数是：

```python
text={
    "format": {
        "type": "json_object",
    }
}
```

它只要求最终文本是 JSON 对象，不知道你真正想要哪些字段。

### 用 `json_schema` 约束最终回答

如果要让最终回答稳定包含指定字段，可以使用 `json_schema`。这是 Provider 原生 Structured Outputs 的典型用法。

```python
weather_schema = {
    "type": "object",
    "properties": {
        "weather_location": {
            "type": "string",
            "description": "天气对应的城市",
        },
        "weather_conditions": {
            "type": ["string", "null"],
            "description": "天气情况；未知时返回 null",
        },
        "punny_response": {
            "type": "string",
            "description": "给用户看的带谐音梗天气回答",
        },
    },
    "required": [
        "weather_location",
        "weather_conditions",
        "punny_response",
    ],
    "additionalProperties": False,
}

response = client.responses.create(
    model=MODEL,
    input=[
        {
            "role": "system",
            "content": "你是天气助手，必须按指定 Schema 返回结果。",
        },
        {
            "role": "user",
            "content": "北京今天晴天，帮我生成一个带谐音梗的回答。",
        },
    ],
    text={
        "format": {
            "type": "json_schema",
            "name": "weather_response",
            "strict": True,
            "schema": weather_schema,
        }
    },
)

data = json.loads(response.output_text)

print(data["weather_location"])
print(data["weather_conditions"])
print(data["punny_response"])
```

这里关键参数是：

```python
text={
    "format": {
        "type": "json_schema",
        "name": "weather_response",
        "strict": True,
        "schema": weather_schema,
    }
}
```

这和 JSON Mode 的区别是：JSON Mode 只要求“像 JSON”，`json_schema` 要求“像这个 Schema 定义的数据”。

### 用 Function Calling 让模型提交工具参数

Function Calling 的目标不是直接拿最终 JSON 回答，而是让模型提交工具调用意图。下面这个例子里，模型会决定是否调用 `get_weather`，并生成符合参数 Schema 的 `city`。

```python
def get_weather(city: str) -> str:
    return f"{city}今天是晴天"


tools = [
    {
        "type": "function",
        "name": "get_weather",
        "description": "查询指定城市的天气",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，例如北京、上海",
                }
            },
            "required": ["city"],
            "additionalProperties": False,
        },
    }
]

input_list = [
    {
        "role": "user",
        "content": "北京天气怎么样？",
    }
]

response = client.responses.create(
    model=MODEL,
    input=input_list,
    tools=tools,
)
```

模型返回工具调用后，Python 代码要自己执行函数，并把结果回传：

```python
input_list += response.output

for item in response.output:
    if item.type != "function_call":
        continue

    if item.name == "get_weather":
        args = json.loads(item.arguments)
        result = get_weather(city=args["city"])

        input_list.append(
            {
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": result,
            }
        )

final_response = client.responses.create(
    model=MODEL,
    input=input_list,
    tools=tools,
)

print(final_response.output_text)
```

这里有三个字段要特别记住：

| 字段 | 出现位置 | 作用 |
| --- | --- | --- |
| `tools` | 第一次和后续请求 | 告诉模型有哪些工具可用 |
| `item.arguments` | 模型返回的 `function_call` | 模型生成的工具参数 JSON 字符串 |
| `call_id` | 工具调用和工具结果之间 | 把某个工具结果对应回某次工具调用 |

**模型只负责生成函数名和参数，真正执行工具的是 Python 业务代码。**

### Chat Completions 写法的位置差异

如果使用 Chat Completions，而不是 Responses API，字段位置会变：

```python
response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "user", "content": "北京今天晴天，提取结构化结果。"}
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "weather_response",
            "strict": True,
            "schema": weather_schema,
        },
    },
)

content = response.choices[0].message.content
data = json.loads(content)
```

Function Calling 在 Chat Completions 里也通常是嵌套形状：

```python
chat_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的天气",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                },
                "required": ["city"],
                "additionalProperties": False,
            },
        },
    }
]
```

因此，复习时不应只记忆“结构化输出参数叫什么”，还要确认当前使用的是哪套 API：

| API | 最终结构化输出位置 | 工具定义形状 |
| --- | --- | --- |
| Responses API | `text.format` | `{"type": "function", "name": ..., "parameters": ...}` |
| Chat Completions | `response_format` | `{"type": "function", "function": {...}}` |

## JSON Mode 只是保证像 JSON

JSON Mode 的目标很窄：让模型最终输出可以被 JSON 解析器读取。

Chat Completions 中常见写法是：

```json
{
  "response_format": {
    "type": "json_object"
  }
}
```

Responses API 中对应的是：

```json
{
  "text": {
    "format": {
      "type": "json_object"
    }
  }
}
```

它的价值是避免模型输出一段普通自然语言，但它不负责校验字段。例如你希望得到：

```json
{
  "weather_location": "北京",
  "weather_conditions": "晴天"
}
```

JSON Mode 只能降低“不是 JSON”的概率，不能保证一定有 `weather_location`，也不能保证 `weather_conditions` 一定是字符串或 `null`。

所以学习时可以这样记：

**JSON Mode 解决“能不能解析”，Schema 解决“字段对不对”。**

## Function Calling 约束的是工具参数

当模型需要调用业务函数时，API 会把工具定义发给模型。工具定义里最重要的是函数名、描述和参数 Schema。

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "查询指定城市的天气",
        "strict": true,
        "parameters": {
          "type": "object",
          "properties": {
            "city": {
              "type": "string"
            }
          },
          "required": ["city"],
          "additionalProperties": false
        }
      }
    }
  ]
}
```

这里的 Schema 约束的是 `get_weather` 的参数，而不是最终回答。

模型不会真的执行 `get_weather`。模型只会生成类似这样的调用意图：

```json
{
  "name": "get_weather",
  "arguments": {
    "city": "北京"
  }
}
```

真正执行函数的是你的业务系统或 Agent runtime。执行完以后，还要把工具结果带着同一个 call id 回传给模型。

这与当前项目里的业务工具关系直接：`get_user_location`、`get_weather_for_location` 这类工具用于让模型先提出调用意图，再由 LangChain 执行 Python 函数。

## Structured Outputs 约束的是最终回答

如果目标不是调用业务工具，而是让模型最终返回固定结构，可以用 `json_schema`。

Chat Completions 里的典型形状是：

```json
{
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "weather_response",
      "strict": true,
      "schema": {
        "type": "object",
        "properties": {
          "weather_location": {
            "type": "string"
          },
          "weather_conditions": {
            "type": ["string", "null"]
          }
        },
        "required": ["weather_location", "weather_conditions"],
        "additionalProperties": false
      }
    }
  }
}
```

Responses API 表达同一个目标时，位置不同：

```json
{
  "text": {
    "format": {
      "type": "json_schema",
      "name": "weather_response",
      "strict": true,
      "schema": {
        "type": "object",
        "properties": {
          "weather_location": {
            "type": "string"
          },
          "weather_conditions": {
            "type": ["string", "null"]
          }
        },
        "required": ["weather_location", "weather_conditions"],
        "additionalProperties": false
      }
    }
  }
}
```

所以复制底层请求示例时，必须先确认自己用的是哪一种 API：

- Chat Completions：通常看 `messages`、`response_format`、`tools`。
- Responses API：通常看 `input`、`text.format`、`tools`。

它们表达的目标类似，但字段位置不是一套。

## strict 的真实含义

`strict: true` 的意思不是“模型一定事实正确”，而是“在支持的 Schema 子集内，模型输出要尽量被生成约束限制到这个结构里”。

这带来两个好处：

- **减少格式修复成本**：少一些多余字段、漏字段、类型错误。
- **更适合业务代码读取**：下游代码可以按字段处理，而不是解析自然语言。

它也有边界：

- Provider 和模型只支持 JSON Schema 的一部分能力。
- strict Schema 往往要求对象明确写 `required` 和 `additionalProperties: false`。
- 可空字段要把 `null` 写进类型，例如 `"type": ["string", "null"]`。
- 安全拒答、token 截断、请求失败不会被强行包装成目标 Schema。
- Schema 正确只代表结构正确，不代表字段值事实正确。

比如 Schema 可以约束 `weather_conditions` 必须是字符串或 `null`，但不能保证“晴天”一定是真实天气。

## 它和 LangChain ToolStrategy 的关系

当前项目写的是：

```python
response_format=ToolStrategy(WeatherResponseFormat)
```

这条路线不是直接调用 OpenAI 的 `response_format=json_schema`。

它更像是 LangChain 在 Agent 层创建了一个人工工具，让模型最后调用这个工具，并把最终字段放进工具参数里：

```json
{
  "name": "WeatherResponseFormat",
  "arguments": {
    "punny_response": "...",
    "weather_location": "北京",
    "weather_conditions": "晴天"
  }
}
```

然后 LangChain 再把这个工具参数解析成：

```python
response["structured_response"]
```

所以它和 OpenAI API 的关系可以这样理解：

| 层次 | 关注点 | 当前项目是否直接使用 |
| --- | --- | --- |
| OpenAI JSON Mode | 最终输出是不是 JSON | 否 |
| OpenAI Function Calling | 模型怎样提交工具调用参数 | 间接相关，因为 `ToolStrategy` 依赖工具调用路线 |
| OpenAI `json_schema` Structured Outputs | Provider 原生约束最终回答结构 | 否 |
| LangChain `ToolStrategy` | 用人工工具承载最终结构化结果 | 是 |
| LangChain `ProviderStrategy` | 让 LangChain 调用 Provider 原生结构化输出 | 当前项目没有使用 |

**当前项目要学的是 ToolStrategy 的消息链路，不是在证明 Qwen OpenAI-compatible 端点支持 OpenAI 原生 `json_schema`。**

## 什么时候这篇笔记有用

这篇笔记主要在三个时候回看：

- **看到 `ProviderStrategy` 时**：知道它背后依赖的是 Provider 原生结构化输出能力。
- **排查结构化输出失败时**：先判断自己失败的是 JSON Mode、Function Calling、`json_schema`，还是 LangChain ToolStrategy。
- **换模型或换 API 协议时**：不要以为 OpenAI-compatible 能聊天，就一定支持原生 Structured Outputs。

## 最终记忆

**JSON Mode 保证“像 JSON”，Structured Outputs + strict 追求“符合 Schema”，Function Calling 约束“工具参数”，LangChain ToolStrategy 则把最终答案伪装成一次人工工具调用再解析成 `structured_response`。**
