# Schema 基础概念

---
参考资料：
- [JSON Schema：What is a schema?](https://json-schema.org/understanding-json-schema/about)
- [JSON Schema：基础](https://json-schema.org/understanding-json-schema/basics)
- [Pydantic：JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/)
---

## Schema 到底是什么

**Schema 是数据的结构说明书和校验契约。** 它描述一份数据应该有哪些字段、字段是什么类型、哪些字段必须出现，以及字段值需要满足哪些约束。

Schema 不是实际数据，也不是负责处理数据的程序。JSON Schema 本身虽然使用 JSON 编写，但它的作用是声明“其他 JSON 数据应该长什么样”。

| 对象     | 作用                    | 当前项目中的例子                                     |
| ------ | --------------------- | -------------------------------------------- |
| Schema | 描述数据应该具有什么结构          | `WeatherResponseFormat` 定义的字段和类型                    |
| 数据实例   | 按照结构填写的一份具体数据         | `WeatherResponseFormat(weather_location="北京", ...)` |
| 校验与解析  | 检查实际数据是否符合约定，并转换成目标对象 | LangChain 对工具参数的解析与校验                        |

可以把 Schema 理解成一张空白表格及其填表规则，数据实例是填好的表格，校验器则负责检查有没有漏填、填错类型或违反限制。

## 一个最小 JSON Schema 示例

下面的 Schema 要求数据是一个对象，必须包含字符串类型的 `city`；`condition` 可以是字符串或 `null`，也可以省略；除此之外不允许出现其他字段。

```json
{
  "type": "object",
  "properties": {
    "city": {
      "type": "string"
    },
    "condition": {
      "type": ["string", "null"]
    }
  },
  "required": ["city"],
  "additionalProperties": false
}
```

符合 Schema 的数据实例：

```json
{
  "city": "北京",
  "condition": "晴天"
}
```

下面的数据不符合 Schema，因为 `city` 应该是字符串，同时 `temperature` 是未被允许的额外字段：

```json
{
  "city": 100,
  "temperature": 25
}
```

## Schema 通常可以约束什么

| 关键字或概念                 | 约束内容         | 示例                                        |
| ---------------------- | ------------ | ----------------------------------------- |
| `type`                 | 数据类型         | `string`、`number`、`object`、`array`、`null` |
| `properties`           | 对象可以包含的字段    | `city`、`condition`                        |
| `required`             | 哪些字段必须出现     | `required: ["city"]`                      |
| `enum`                 | 字段只能从有限值中选择  | `sunny`、`cloudy`、`rainy`                  |
| `minimum` / `maximum`  | 数值范围         | 温度必须在某个范围内                                |
| `pattern` / `format`   | 字符串格式        | 日期、邮箱或正则模式                                |
| `items`                | 数组元素的结构      | 数组中的每一项都必须是字符串                            |
| `additionalProperties` | 是否允许未声明的额外字段 | `false` 表示禁止额外字段                          |

Schema 擅长检查数据的表面结构。跨字段业务关系、事实真实性以及外部数据是否可靠，通常还需要业务代码继续校验。

## 当前项目中的 Schema

当前项目在 `utils/models.py` 中使用 **`@dataclass`** 定义结构化响应：

```python
from dataclasses import dataclass


@dataclass
class WeatherResponseFormat:
    punny_response: str
    weather_location: str
    weather_conditions: str | None = None
```

**`WeatherResponseFormat`** 是 Python 侧的数据模型，也是 LangChain 接收的 Schema 类型；它本身不是一段手写的 JSON Schema。把它传给 `create_agent(response_format=...)` 后，LangChain 会根据字段、类型和默认值生成结构化输出所需的 Schema。

| 字段                   | Python 类型            | 当前模型中的含义               |
| -------------------- | -------------------- | ---------------------- |
| `punny_response`     | `str`                | 必须提供字符串                |
| `weather_location`   | `str`                | 必须提供字符串                |
| `weather_conditions` | `str \| None = None` | 可以是字符串或 `None`，并且具有默认值 |

从概念上看，它接近下面的 JSON Schema。具体生成结果会受到 LangChain、类型转换库和版本影响，因此调试协议时应以实际发送的 Schema 为准。

```json
{
  "type": "object",
  "properties": {
    "punny_response": {
      "type": "string"
    },
    "weather_location": {
      "type": "string"
    },
    "weather_conditions": {
      "anyOf": [
        { "type": "string" },
        { "type": "null" }
      ],
      "default": null
    }
  },
  "required": ["punny_response", "weather_location"]
}
```

模型最终提交并通过解析后，得到的是一份数据实例：

```python
WeatherResponseFormat(
    punny_response="北京的天气好得让人想‘蕉’个朋友！",
    weather_location="北京",
    weather_conditions="晴天",
)
```

所以需要明确区分：`WeatherResponseFormat` 类描述规则，`WeatherResponseFormat(...)` 对象保存某一次实际结果。

## 必填、可空、可省略不是一回事

这三个概念最容易混淆：

| 概念  | JSON Schema 中怎样表达   | 含义                 |
| --- | ------------------- | ------------------ |
| 必填  | 字段名出现在 `required` 中 | 对象里必须出现这个字段        |
| 可空  | 字段类型允许 `null`       | 字段出现时可以把值设为 `null` |
| 可省略 | 字段名不在 `required` 中  | 整个字段可以不出现          |

以 Pydantic v2 的字段声明为例：

| Python 声明                  | 是否必须传入 | 是否允许 `None` |
| -------------------------- | ------ | ----------- |
| `name: str`                | 是      | 否           |
| `note: str \| None`        | 是      | 是           |
| `note: str \| None = None` | 否      | 是           |

在通用 JSON Schema 中，`default` 主要是一条注释信息，并不要求所有校验器自动补上缺失值。Python 模型是否使用默认值，是模型解析层的行为。

部分模型提供商只支持 JSON Schema 的子集，并可能对 `required`、可空类型和额外字段提出更严格要求。因此“本地 Pydantic 校验成功”和“Provider 原生 strict 模式支持这个 Schema”是两件事。

## Python 中可以用什么表示 Schema

| 表示方式                 | 特点                     | 适合场景                  |
| -------------------- | ---------------------- | --------------------- |
| **`@dataclass`**     | 写法简单，能表达字段、类型和默认值      | 当前 Quickstart 这类基础演示  |
| `TypedDict`          | 保留字典形态，适合声明键和值类型       | 已经以字典为中心的代码           |
| Pydantic `BaseModel` | 支持字段描述、枚举、范围、嵌套模型和本地校验 | 结构约束较多的业务输出           |
| 原始 JSON Schema 字典    | 能直接控制协议层 Schema        | 需要精确适配 Provider API 时 |

普通 Python `# 注释` 不会自动成为模型可见的字段说明。需要让模型理解字段语义时，可以使用 Pydantic 的 `Field(description=...)`，并检查最终生成的 JSON Schema。

## Schema 在当前项目中怎样流转

1. `utils/models.py` 定义 `WeatherResponseFormat`，约定最终结果的字段和类型。
2. `agent.py` 把它传给 `create_agent(response_format=...)`。
3. LangChain 根据显式策略或模型能力选择 `ToolStrategy` 或 `ProviderStrategy`。
4. 模型按选定路线提交符合该结构的字段。
5. LangChain 解析和校验结果，并把 `WeatherResponseFormat` 实例放入 `response["structured_response"]`。

这条完整调用链以及它与 `ProviderStrategy`、JSON Mode 的区别，见 [03_结构化输出](<03_结构化输出.md>)。

如果需要把当前 dataclass Schema 升级为生产中更常用的 Pydantic `BaseModel`，可以参考 [18_Pydantic增强Schema与dataclass区别](<18_Pydantic增强Schema与dataclass区别.md>)。

## 常见误区

- **把 Schema 当作 JSON 数据。** 错。Schema 是规则，JSON 对象可以是符合或不符合规则的数据实例。
- **只要返回有效 JSON，就等于符合 Schema。** 错。有效 JSON 仍可能缺字段、字段类型错误或包含多余字段。
- **结构校验成功就代表回答正确。** 错。Schema 不能证明城市、天气或其他事实值真实。
- **可空就等于可以省略。** 错。一个字段可以必须出现，同时允许它的值为 `null`。
- **Pydantic 模型等于 Provider 原生严格输出。** 错。Pydantic 提供 Schema 生成和本地校验，实际生成约束取决于所选策略和模型服务能力。

## 相关学习笔记

- [03_结构化输出](<03_结构化输出.md>)：理解 Schema 怎样被 `ToolStrategy` 或 `ProviderStrategy` 使用。
- [18_Pydantic增强Schema与dataclass区别](<18_Pydantic增强Schema与dataclass区别.md>)：比较 dataclass 与 Pydantic 在 Schema 表达、字段描述和校验能力上的差异。
- [04_Tools与FunctionCalling](<04_Tools与FunctionCalling.md>)：理解工具参数 Schema、工具调用意图与真实函数执行。
- [05_create_agent参数详解](<05_create_agent参数详解.md>)：理解 `response_format` 怎样进入 Agent 装配过程。
- [07_模型请求与响应结构](<07_模型请求与响应结构.md>)：观察 Schema 对应的数据最终出现在哪些响应字段中。

**最终记忆：Schema 定义“数据应该长什么样”，数据实例表示“这一次实际长什么样”，校验负责比较二者；结构正确不等于内容真实。**
