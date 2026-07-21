# 模型采样参数与 ChatOpenAI

---
参考资料：
- [LangChain Models](https://docs.langchain.com/oss/python/langchain/models)
- [LangChain ChatOpenAI](https://docs.langchain.com/oss/python/integrations/chat/openai)
- [vLLM 0.6.4 SamplingParams](https://docs.vllm.ai/en/v0.6.4/dev/sampling_params.html)
---

## 当前项目怎样设置采样基线

当前项目在 `utils/llms.py` 中创建 `ChatOpenAI`。生效代码只显式设置了一个采样参数：`temperature`。

```python
DEFAULT_TEMPERATURE = 0

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

这段配置包含三类不同性质的参数：

| 类型 | 当前参数 | 作用 |
| --- | --- | --- |
| 生成参数 | `temperature=0` | 降低随机性，建立相对稳定的测试基线 |
| 客户端参数 | `timeout=30`、`max_retries=2` | 控制超时和重试，不改变 Token 采样分布 |
| Provider 扩展参数 | `extra_body.enable_thinking=False` | 关闭当前 Qwen 服务的思考模式，不属于采样参数 |

**`temperature=0` 适合先观察工具型 Agent 的基础行为，但不保证事实正确、工具选择正确或结果绝对可复现。**

## 采样与生成参数解决什么问题

狭义的采样参数控制模型怎样从候选 Token 中选择下一个 Token。实际调试模型时，通常还会同时关注重复控制、停止条件、输出长度和随机种子，所以这篇笔记把它们放在一起理解。

这些参数主要影响：

- 输出是稳定还是发散。
- 候选 Token 的选择范围。
- 是否容易出现重复内容。
- 最多生成多少内容以及何时停止。
- 相同输入能否近似复现。

**生成参数只能调整生成行为，不能把不支持工具调用的模型变成支持工具调用，也不能替代 Prompt、Schema 和业务校验。**

## 常用参数与传递位置

| 参数 | 类型 | 直觉 | 在当前 `ChatOpenAI` 中怎样传 | 注意点 |
| --- | --- | --- | --- | --- |
| `temperature` | 概率采样 | 越低越偏向高概率 Token | 直接参数 | 低温不等于事实正确，也不保证绝对可复现 |
| `top_p` | 概率采样 | 只在累计概率达到阈值的候选集合中采样 | 直接参数 | 通常不要和 `temperature` 同时大幅调整 |
| `top_k` | 概率采样 | 每一步只保留概率最高的 K 个候选 | `extra_body` | 不是 OpenAI 标准字段，后端未必支持 |
| `min_p` | 概率采样 | 过滤相对最高概率过低的候选 | `extra_body` | 常见于 vLLM 等后端，不是通用字段 |
| `presence_penalty` | 重复控制 | Token 出现过就施加惩罚，鼓励新内容 | 直接参数 | 与 `frequency_penalty` 的计算方式不同 |
| `frequency_penalty` | 重复控制 | 出现次数越多，惩罚越强 | 直接参数 | 数值范围和效果依赖具体 Provider |
| `repetition_penalty` | 重复控制 | 参考 Prompt 与已生成内容抑制重复 | `extra_body` | vLLM 常见，但不是 OpenAI 标准字段 |
| `seed` | 近似复现 | 固定随机种子，帮助复现实验 | 直接参数 | 后端、模型版本和并发环境变化仍可能改变结果 |
| `stop` / `stop_sequences` | 终止条件 | 生成指定字符串时停止 | 构造时可用 `stop_sequences`，`bind()` / `invoke()` 使用 `stop` | 它匹配字符串停止序列，可能截断 JSON 或工具参数 |
| `max_completion_tokens` | 输出长度 | 限制最多生成多少 Token | 直接参数 | 达到上限可能得到不完整的工具参数或结构化结果 |

当前项目固定的 `langchain-openai==1.1.6` 仍接受 Python 参数名 `max_tokens`，但 `ChatOpenAI` 会把 Chat Completions 请求规范化为 `max_completion_tokens`；使用 Responses API 时又会转换为 `max_output_tokens`。**同一次配置只选一个长度字段，不要同时传递。** OpenAI-compatible 后端是否支持转换后的字段，还需要单独验证。

## `ChatOpenAI` 的三种参数入口

| 入口 | 适合传什么 | 示例 |
| --- | --- | --- |
| 直接构造参数 | `ChatOpenAI` 已显式支持的标准字段 | `temperature`、`top_p`、`seed`、`max_completion_tokens` |
| `model_kwargs` | OpenAI 标准 API 中存在，但当前类没有显式声明的字段 | 某些新增的 OpenAI 请求字段 |
| `extra_body` | OpenAI-compatible Provider 的非标准扩展字段 | `top_k`、`min_p`、`repetition_penalty`、`enable_thinking` |

同一个字段不要同时出现在直接参数、`model_kwargs` 和 `extra_body` 中。自定义 Provider 参数应优先放进 `extra_body`，避免 OpenAI 客户端把它当成标准字段校验。

## 一次性传递本篇常用参数

下面的“全部参数”指本篇涉及的常用生成参数与调用可靠性参数，不代表 `ChatOpenAI` 的所有构造字段。代码重点是展示每类参数应该放在哪里：

```python
from typing import Any

from langchain_openai import ChatOpenAI


def create_chat_model(
    config: dict[str, str],
    llm_type: str,
    *,
    supports_sampling_extensions: bool = False,
) -> ChatOpenAI:
    chat_kwargs: dict[str, Any] = {
        # 模型连接参数
        "base_url": config["base_url"],
        "api_key": config["api_key"],
        "model": config["chat_model"],

        # ChatOpenAI 显式支持的生成参数
        "temperature": 0,
        "top_p": None,  # 例如 0.9；None 表示不发送，让后端使用默认值
        "max_completion_tokens": 800,
        "stop_sequences": None,  # 例如 ["</final>"]；ToolStrategy 下建议不设置
        "frequency_penalty": None,  # 例如 0.2
        "presence_penalty": None,  # 例如 0.1
        "seed": None,  # 例如 42；只有后端支持时才有意义

        # OpenAI 标准但 ChatOpenAI 未显式声明的字段才放这里
        "model_kwargs": {},

        # HTTP 客户端与流式用量配置，不属于采样参数
        "timeout": 30,
        "max_retries": 2,
        "stream_usage": False,
    }

    if llm_type == "qwen":
        qwen_extra_body: dict[str, Any] = {
            # 当前项目使用的 Qwen 扩展参数
            "enable_thinking": False,
        }

        # 只有确认当前 Qwen / vLLM 后端支持时才发送
        if supports_sampling_extensions:
            qwen_extra_body.update(
                {
                    "top_k": 40,
                    "min_p": 0.05,
                    "repetition_penalty": 1.05,
                }
            )

        chat_kwargs["extra_body"] = qwen_extra_body

    return ChatOpenAI(**chat_kwargs)
```

这段代码用于展示传递语法，不是推荐把所有参数同时调离默认值。实际使用时尤其注意：

- `None` 值通常不会进入请求体，表示让后端使用默认值；需要实验时再替换成具体数值。
- `top_k`、`min_p` 和 `repetition_penalty` 只有在 `supports_sampling_extensions=True` 且后端明确支持时才会发送。
- 当前 Agent 使用 Tools 和 `ToolStrategy`，停止序列可能截断工具参数；没有明确格式边界时保持 `None`。
- 建立实验基线时先使用 `temperature=0`，让 `top_p`、penalty 等参数保持默认值。
- 自定义 `base_url` 时，只有验证后端支持流式 usage 后才设置 `stream_usage=True`。

## 构造、绑定和单次调用的区别

### 构造函数：模型实例的默认值

```python
model = ChatOpenAI(
    model="MODEL_NAME",
    api_key="YOUR_API_KEY",
    temperature=0.2,
    top_p=0.9,
    max_completion_tokens=800,
)
```

后续每次直接调用这个 `model`，都会继承这些默认值。当前项目把模型传入 `create_agent()`，因此构造函数中的默认值会作用于 Agent 内部的每次模型调用。

### `bind()`：生成一个带任务级默认参数的新 Runnable

```python
creative_model = model.bind(
    temperature=0.8,
    top_p=0.95,
)

response = creative_model.invoke(
    [{"role": "user", "content": "生成三个产品名称"}]
)
```

`bind()` 不会修改原来的 `model`，而是返回一个绑定了额外参数的新 Runnable。它适合直接模型调用或 LCEL 链；完整的 `ChatOpenAI` 对象与 Agent 装配边界见 [[10_ChatOpenAI对象详解]]。

### `invoke()`：只覆盖本次直接模型调用

```python
response = model.invoke(
    [{"role": "user", "content": "写一个简短的广告标题"}],
    temperature=0.7,
    top_p=0.95,
    max_completion_tokens=300,
    stop=["<END>"],
)
```

单次调用参数会覆盖模型实例中的同名默认值，但不会修改模型对象。这里说的是直接调用 `ChatOpenAI.invoke()`；不要把这些字段直接塞进 `agent.invoke()`，期望它们自动变成底层模型参数。

同名请求参数的一般优先级是：**单次 `invoke()` 参数高于 `bind()` 参数，`bind()` 参数高于构造函数默认值。** 但还要注意两个例外：

- `max_retries` 是客户端级参数，只在构造 `ChatOpenAI` 时设置。
- `extra_body` 在不同层级之间按整个字典替换，不会深度合并。覆盖时要同时保留已有的 `enable_thinking=False` 等字段。

## 调参顺序与常见误区

- 先固定 Prompt、工具、模型版本和测试输入，只改变一个参数。
- `temperature` 与 `top_p` 先选择一个调整，避免无法判断变化来源。
- 工具选择不稳定时，先检查模型能力、工具名、描述和参数 Schema。
- 结构化输出中断时，检查结束原因和输出 Token 上限，进一步排查见 [[03_结构化输出]]。
- `seed` 只能帮助近似复现，不能跨模型版本、Provider 和部署环境保证完全一致。
- 不同模型可能拒绝不支持的参数，OpenAI-compatible 不等于所有扩展字段都兼容。

**参数支持范围始终是“具体模型 + Provider API + LangChain integration 版本”的交集。**

## 相关学习笔记

- [[project_001_Prompt Engineering/notes/01_大预言模型设置|大语言模型设置]]：从 Prompt Engineering 角度理解参数直觉和任务选择。
- [[10_ChatOpenAI对象详解]]：查看 `ChatOpenAI` 的完整构造参数、调用参数和返回对象。
- [[03_结构化输出]]：理解输出长度、截断与 Schema 校验的关系。
- [[04_Tools与FunctionCalling]]：理解工具调用稳定性不只由采样参数决定。
- [[07_模型请求与响应结构]]：观察参数最终怎样进入请求，以及 usage 和结束原因怎样出现在响应中。
