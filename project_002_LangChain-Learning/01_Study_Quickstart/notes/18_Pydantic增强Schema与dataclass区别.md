# Pydantic 增强 Schema 与 dataclass 区别

---
参考资料：
- [LangChain：Structured output](https://docs.langchain.com/oss/python/langchain/structured-output)
- [Pydantic：Fields](https://docs.pydantic.dev/latest/concepts/fields/)
- [Pydantic：Configuration](https://docs.pydantic.dev/latest/concepts/config/)
---

## 核心结论

**`@dataclass` 适合用最少代码表达字段结构，Pydantic 更适合在生产中表达字段语义、约束、校验和 JSON Schema。**

在 LangChain 结构化输出里，二者都可以作为 `response_format` 的 Schema 来源。差别不在于“能不能用”，而在于 Schema 能表达多少规则、模型能看到多少字段说明、本地解析失败时能得到多少错误信息。

当前项目使用的是 dataclass：

```python
from dataclasses import dataclass


@dataclass
class WeatherResponseFormat:
    punny_response: str
    weather_location: str
    weather_conditions: str | None = None
```

它适合 Quickstart：字段少、结构简单、学习重点在 Agent 调用链。进入真实业务后，通常会改成 Pydantic `BaseModel`。

## 两者的主要区别

| 对比项 | `@dataclass` | Pydantic `BaseModel` |
| --- | --- | --- |
| 主要定位 | Python 数据容器 | 数据建模、解析、校验和 Schema 生成 |
| 字段描述 | 普通 `# 注释` 不会自动进入 Schema | `Field(description=...)` 可以成为 Schema 描述 |
| 类型校验 | 标准 dataclass 本身不主动做运行时类型校验 | 创建或解析对象时执行类型校验 |
| 数值范围 | 需要手写业务校验 | `Field(ge=..., le=...)` 等可声明 |
| 枚举约束 | 可结合 `Enum`，但表达和错误提示较弱 | 可结合 `Enum` / `Literal` 生成更清晰的 Schema |
| 嵌套对象 | 可以嵌套 dataclass，但校验能力有限 | 嵌套 `BaseModel` 是常用写法 |
| 额外字段 | 默认没有统一禁止策略 | `ConfigDict(extra="forbid")` 可禁止额外字段 |
| 错误信息 | 需要自己组织 | `ValidationError` 能指出具体字段和错误原因 |
| 生产适配 | 适合简单结构和演示 | 更适合稳定接口、业务校验和长期维护 |

**学习阶段可以先用 dataclass 理解结构化输出链路，生产阶段优先用 Pydantic 表达更完整的业务契约。**

## 用 Pydantic 改写当前项目 Schema

当前 dataclass 只表达三个字段和一个默认值。如果改成 Pydantic，可以补充字段说明、额外字段策略和更明确的类型约束：

```python
from pydantic import BaseModel, ConfigDict, Field


class WeatherResponseFormat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    punny_response: str = Field(
        description="给用户看的带谐音梗或冷笑话的天气回答"
    )
    weather_location: str = Field(
        description="本次天气信息对应的城市或地点"
    )
    weather_conditions: str | None = Field(
        default=None,
        description="天气情况，例如晴天、多云、下雨；未知时为 null"
    )
```

这段代码和 dataclass 版本表达的是同一类业务结果，但 Pydantic 版本多了三类能力：

- **字段说明**：模型更容易理解每个字段应填什么。
- **额外字段控制**：`extra="forbid"` 可以禁止模型提交未声明字段。
- **本地校验能力**：解析失败时可以得到明确的字段级错误。

接入 LangChain 时，写法不需要大改：

```python
response_format=WeatherResponseFormat
```

如果要固定策略，也可以写：

```python
response_format=ToolStrategy(WeatherResponseFormat)
```

或：

```python
response_format=ProviderStrategy(
    schema=WeatherResponseFormat,
    strict=True,
)
```

Pydantic 负责定义 Schema，`ToolStrategy` / `ProviderStrategy` 负责让模型按这个 Schema 生成结构化结果。

## Pydantic 能增强哪些 Schema 能力

### 字段描述

```python
weather_location: str = Field(
    description="本次天气信息对应的城市或地点"
)
```

字段描述比代码注释更重要。代码注释只给开发者看，`Field(description=...)` 可以进入生成的 Schema，被 LangChain 交给模型或 Provider。

### 枚举约束

```python
from typing import Literal


weather_conditions: Literal["晴天", "多云", "下雨", "未知"] = Field(
    description="天气情况，只能从固定枚举中选择"
)
```

枚举适合业务值集合明确的字段。它可以减少模型自由发挥，但如果真实业务值很多，枚举维护成本也会变高。

### 数值范围

```python
temperature_c: float = Field(
    ge=-100,
    le=100,
    description="摄氏温度"
)
```

数值范围属于结构和基础业务约束。它能阻止明显不合理的格式值，但不能证明温度来源真实。

### 嵌套对象

```python
class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")

    city: str = Field(description="城市名称")
    country: str = Field(description="国家或地区")


class WeatherResponseFormat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    punny_response: str
    location: Location
    weather_conditions: str | None = None
```

嵌套对象适合表达层级清楚的业务数据。例如地址、商品、订单、用户资料，不应全部压成一层字符串字段。

### 自定义校验

```python
from pydantic import BaseModel, Field, field_validator


class WeatherResponseFormat(BaseModel):
    weather_location: str = Field(description="本次天气信息对应的城市或地点")

    @field_validator("weather_location")
    @classmethod
    def location_must_not_be_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("weather_location 不能为空")
        return value
```

自定义校验适合处理 Schema 很难直接表达的规则。需要注意，Provider 原生 strict 模式未必理解 Python 校验函数；这类校验通常发生在本地解析阶段。

## Pydantic 不等于 Provider 原生 strict

Pydantic 可以生成 JSON Schema，也可以执行本地校验，但它不直接决定模型生成阶段是否被严格约束。

需要分清三层：

| 层次 | 负责什么 | 例子 |
| --- | --- | --- |
| Pydantic | 定义字段、约束和本地校验 | `BaseModel`、`Field()`、`ConfigDict(extra="forbid")` |
| LangChain 策略 | 决定怎样让模型产出结构化结果 | `ToolStrategy`、`ProviderStrategy`、直接传 Schema |
| Provider 能力 | 决定底层 API 是否原生支持结构约束 | OpenAI `json_schema`、工具调用、strict 模式 |

因此，`BaseModel` 写得很严格，不代表 Provider 一定支持这些约束。尤其使用 OpenAI-compatible 网关时，需要实际验证 `json_schema`、`strict`、工具调用和 Schema 子集支持情况。

## 什么时候用 dataclass

dataclass 适合：

- Quickstart、教学案例和原型实验。
- 字段数量少，只有类型和默认值。
- 重点是观察 Agent 调用链，而不是建立强 Schema 契约。
- 数据只在内部短链路使用，失败成本较低。

当前项目用 dataclass 是合理的，因为学习重点是 `create_agent()`、工具调用、短期记忆和 `structured_response`。

## 什么时候升级为 Pydantic

Pydantic 更适合：

- 字段含义需要写入 Schema，供模型理解。
- 需要禁止额外字段、限制范围、控制枚举或表达嵌套对象。
- 结构化输出会进入数据库、接口响应、订单流程或其他下游系统。
- 希望拿到清晰的字段级错误，便于重试、日志和排查。
- 多个模块复用同一份数据契约。

生产中推荐组合通常是：

```python
response_format=ToolStrategy(MyPydanticModel)
```

或：

```python
response_format=ProviderStrategy(
    schema=MyPydanticModel,
    strict=True,
)
```

具体选择 ToolStrategy 还是 ProviderStrategy，可以参考 [16_ToolStrategy和ProviderStrategy区别](<16_ToolStrategy和ProviderStrategy区别.md>)。

## 当前项目如果要升级

如果要把当前项目从 dataclass 升级到 Pydantic，优先改 `code/utils/models.py`：

```python
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field


@dataclass
class Context:
    user_id: str


class WeatherResponseFormat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    punny_response: str = Field(
        description="给用户看的带谐音梗或冷笑话的天气回答"
    )
    weather_location: str = Field(
        description="本次天气信息对应的城市或地点"
    )
    weather_conditions: str | None = Field(
        default=None,
        description="天气情况，例如晴天、多云、下雨；未知时为 null"
    )
```

`code/agent.py` 的核心装配可以保持：

```python
response_format=WeatherResponseFormat
```

升级后需要重新观察：

- `response["structured_response"]` 的实际对象类型。
- 日志和 checkpoint 中的序列化表现。
- `ToolStrategy` 与 `ProviderStrategy` 两种显式策略是否都能运行。
- 当前 Qwen 兼容接口是否接受 Pydantic 生成的 Schema。

## 常见误区

- **把 Pydantic 当成结构化输出策略。** Pydantic 是 Schema 定义方式，不是模型调用策略。
- **认为 dataclass 不能用于结构化输出。** dataclass 可以用，只是约束表达能力较弱。
- **认为 Pydantic 校验通过就代表业务正确。** 校验通过只说明字段结构和基础约束通过，事实真实性仍需要业务校验。
- **认为 `Field(description=...)` 等同于强制规则。** 字段描述帮助模型理解字段语义，强制程度取决于 LangChain 策略和 Provider 能力。
- **忽略 Provider Schema 子集。** 本地 Pydantic 能生成的 Schema，不一定全部被 Provider strict 模式支持。

## 和其他笔记的关系

- [12_Schema基础概念](<12_Schema基础概念.md>)：理解 Schema、数据实例、必填、可空和可省略。
- [03_结构化输出](<03_结构化输出.md>)：理解 Schema 怎样进入 `create_agent(response_format=...)`。
- [14_ToolStrategy详解](<14_ToolStrategy详解.md>)：理解 Pydantic Schema 怎样走工具调用路线。
- [15_ProviderStrategy详解](<15_ProviderStrategy详解.md>)：理解 Pydantic Schema 怎样走 Provider 原生路线。
- [17_结构化输出失败原因与处理](<17_结构化输出失败原因与处理.md>)：排查字段校验失败、Provider 不支持和业务校验失败。

**最终记忆：dataclass 适合快速声明结构，Pydantic 适合生产级 Schema 契约；二者都只是 Schema 来源，真正的结构化输出路线仍由 ToolStrategy、ProviderStrategy 或自动策略决定。**
