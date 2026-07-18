# PromptTemplate 与 ChatPromptTemplate 使用方法

参考代码：

- [agent.py](<../agent.py>)
- [system_prompt_tmpl.md](<../prompt/system_prompt_tmpl.md>)
- [human_prompt_tmpl.md](<../prompt/human_prompt_tmpl.md>)
- [config.py](<../utils/config.py>)
- [llms.py](<../utils/llms.py>)
- [.env.example](<../.env.example>)

## 本项目的学习重点

当前阶段只学习 Prompt Template 在项目里的完整使用路径。

| 学习内容 | 需要理解的问题 |
| --- | --- |
| 系统 Prompt 模板文件定义 | Agent 的角色、工具说明和规则写在哪里？ |
| 用户 Prompt 模板文件定义 | 本轮用户信息和问题怎样组织？ |
| Prompt 模板定义变量 | `{name}`、`{question}` 表示什么？ |
| Prompt 变量动态传参 | Python 如何把真实数据填入模板？ |
| Agent 加载 Prompt 模板使用 | 渲染后的 Prompt 最后怎样进入 Agent？ |

模型厂商接入、工具调用、短期记忆和结构化输出暂时不展开。

## 项目中的 Prompt 处理流程

```text
system_prompt_tmpl.md ──读取──> system_prompt ──传入──> create_agent()

human_prompt_tmpl.md  ──读取──> human_prompt
                                      ↓
system_prompt + human_prompt ──> ChatPromptTemplate
                                      ↓
                         format_messages(name, question)
                                      ↓
                                human_msg.content
                                      ↓
                                  agent.invoke()
```

这个流程里有两个关键方向：

- **系统 Prompt** 负责定义 Agent 长期遵守的角色和规则。
- **用户 Prompt** 负责包装本轮动态输入，再作为用户消息交给 Agent。

## 一、系统 Prompt 模板文件定义

系统 Prompt 保存在：

```text
prompt/system_prompt_tmpl.md
```

当前文件主要包含三类内容：

```text
# 角色：你是一名擅长讲冷笑话的专业天气预报员。

## 你可以使用两个工具：
- get_weather_for_location
- get_user_location

## 规则：
回答天气问题前需要确认地点……
```

系统 Prompt 适合存放相对稳定的信息：

- **角色**：Agent 应该以什么身份工作。
- **能力说明**：Agent 可以使用哪些工具。
- **行为规则**：什么情况下应该调用工具，什么情况下不能直接回答。
- **长期约束**：整个会话都需要遵守的要求。

文件路径在 `utils/config.py` 中统一配置：

```python
class Config:
    SYSTEM_PROMPT_TMPL = "prompt/system_prompt_tmpl.md"
```

`agent.py` 使用 `PromptTemplate.from_file()` 读取文件：

```python
system_prompt = PromptTemplate.from_file(
    template_file=Config.SYSTEM_PROMPT_TMPL,
    encoding="utf-8"
).template
```

这里的返回过程分成两步：

| 表达式 | 得到的结果 |
| --- | --- |
| `PromptTemplate.from_file(...)` | `PromptTemplate` 对象 |
| `.template` | 模板中的原始字符串 |

当前代码最终需要系统 Prompt 字符串，所以在后面使用了 `.template`。

## 二、用户 Prompt 模板文件定义

用户 Prompt 保存在：

```text
prompt/human_prompt_tmpl.md
```

当前模板内容是：

```text
请用搞笑的语气，结合冷笑话，回答用户关于天气的问题。
用户的名字是：{name}。
用户原始问题是：{question}
```

用户 Prompt 由两部分组成：

- **固定内容**：回答语气、任务类型和输入字段说明。
- **动态内容**：运行时才知道的用户姓名和问题。

它同样通过配置路径加载：

```python
class Config:
    HUMAN_PROMPT_TMPL = "prompt/human_prompt_tmpl.md"
```

```python
human_prompt = PromptTemplate.from_file(
    template_file=Config.HUMAN_PROMPT_TMPL,
    encoding="utf-8"
).template
```

**系统 Prompt 描述 Agent 应该怎样工作，用户 Prompt 描述这一轮需要处理什么。**

## 三、Prompt 模板定义变量

Prompt 变量使用花括号定义：

```text
{name}
{question}
```

变量只是占位符。模板文件被读取时，它们还没有具体值；只有程序执行到动态传参时，变量才会被替换。

| 变量 | 当前项目中的含义 | 示例值 |
| --- | --- | --- |
| `{name}` | 当前用户姓名 | `星禾` |
| `{question}` | 当前用户提出的问题 | `外面的天气怎么样？` |

定义变量时需要注意：

- 变量名应该能表达内容含义，不要使用 `{a}`、`{data1}` 这类模糊名称。
- 同一个含义在模板和 Python 中应该使用同一个名称。
- 模板需要哪些变量，动态传参时就必须提供哪些变量。
- Prompt 中不要定义 API Key、密码等敏感变量。

系统 Prompt 当前没有动态变量，因此加载后可以直接作为稳定规则使用。用户 Prompt 包含 `{name}` 和 `{question}`，必须经过渲染才能得到完整内容。

## PromptTemplate 和 ChatPromptTemplate 的关系

| 类 | 管理对象 | 当前项目中的作用 |
| --- | --- | --- |
| `PromptTemplate` | 单段文本模板 | 从 Markdown 文件读取系统和用户 Prompt |
| `ChatPromptTemplate` | 多条角色消息 | 把系统 Prompt 和用户 Prompt 组合起来 |

项目通过下面的代码组合两份模板：

```python
chat_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", human_prompt)
])
```

组合后的消息顺序是：

1. `system`：角色、工具和规则。
2. `human`：用户姓名和本轮问题。

**PromptTemplate 解决一段 Prompt 如何复用，ChatPromptTemplate 解决多条角色消息如何组合。**

## 四、Prompt 变量动态传参

当前 `agent.py` 中的真实数据是：

```python
raw_question = "外面的天气怎么样？"
name = "星禾"
```

使用 `format_messages()` 把数据传给模板：

```python
messages = chat_prompt.format_messages(
    question=raw_question,
    name=name
)
```

传参时会发生两次替换：

```text
{name}     -> 星禾
{question} -> 外面的天气怎么样？
```

渲染后的 `messages` 是消息列表：

```text
messages[0]  -> SystemMessage
messages[-1] -> HumanMessage
```

可以读取最后一条用户消息：

```python
human_msg = messages[-1]
print(human_msg.content)
```

`human_msg.content` 的内容类似：

```text
请用搞笑的语气，结合冷笑话，回答用户关于天气的问题。
用户的名字是：星禾。
用户原始问题是：外面的天气怎么样？
```

### 变量名必须完全对应

正确写法：

```python
chat_prompt.format_messages(
    name="星禾",
    question="外面的天气怎么样？"
)
```

错误写法：

```python
chat_prompt.format_messages(
    username="星禾",
    question="外面的天气怎么样？"
)
```

模板需要的是 `{name}`，传入的却是 `username`，两个名称无法对应。

缺少参数也会失败：

```python
chat_prompt.format_messages(
    question="外面的天气怎么样？"
)
```

此时模板中的 `{name}` 没有可以替换的值。

**遇到模板渲染错误时，先检查花括号里的变量名和 `format_messages()` 的参数名。**

## 五、Agent 加载 Prompt 模板使用

当前项目没有把整个 `chat_prompt` 对象直接交给 Agent，而是把系统 Prompt 和用户 Prompt 分别传入。

### 系统 Prompt 进入 Agent

创建 Agent 时，通过 `system_prompt` 参数传入系统模板内容：

```python
agent = create_agent(
    model=llm_chat,
    system_prompt=system_prompt,
    tools=tools,
    context_schema=Context,
    response_format=ToolStrategy(ResponseFormat),
    checkpointer=checkpointer
)
```

这意味着 `system_prompt_tmpl.md` 中的角色和规则会成为 Agent 的系统级约束。

### 用户 Prompt 进入 Agent

用户模板先经过动态传参，再取出 `HumanMessage` 的文本：

```python
messages = chat_prompt.format_messages(
    question=raw_question,
    name=name
)

human_msg = messages[-1]
```

调用 Agent 时，把渲染后的用户内容放入 `messages`：

```python
response = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": human_msg.content
            }
        ]
    },
    config=config,
    context=Context(user_id="1")
)
```

当前项目的两条 Prompt 路径可以概括为：

```text
系统模板文件
→ system_prompt
→ create_agent(system_prompt=system_prompt)

用户模板文件
→ human_prompt
→ ChatPromptTemplate
→ format_messages(name, question)
→ human_msg.content
→ agent.invoke(messages=...)
```

这里暂时只需要理解 Prompt 怎样进入 Agent。`model`、`tools`、`context`、`checkpointer` 和 `response_format` 的具体作用留到后续阶段逐个拆解。

## Prompt 与 `.env` 的边界

API Key 不属于 Prompt，不能写进 Prompt 模板。

| 内容 | 保存位置 |
| --- | --- |
| Agent 角色、行为规则 | `prompt/system_prompt_tmpl.md` |
| 用户消息格式、Prompt 变量 | `prompt/human_prompt_tmpl.md` |
| API Key、Base URL、模型名称 | `.env` |
| Prompt 文件路径、当前模型类型 | `utils/config.py` |

`utils/llms.py` 负责加载 `.env` 并读取模型配置。Prompt Template 只负责组织发给模型的内容。

**Prompt 决定发什么，`.env` 决定连接谁。**

## 常见问题

- **模板文件找不到**：检查运行目录以及 `Config` 中的相对路径。
- **中文读取异常**：模板文件和 `from_file()` 都使用 UTF-8。
- **变量没有替换**：检查变量是否使用 `{变量名}` 格式。
- **动态传参失败**：检查模板变量与函数参数是否同名。
- **系统规则没有生效**：检查 `create_agent()` 是否传入了 `system_prompt`。
- **用户问题还是原始模板**：检查是否先调用了 `format_messages()`。
- **把 API Key 写入模板**：敏感配置应该放在 `.env`，不能进入 Prompt。

## 这一阶段需要记住什么？

本项目中的 Prompt Template 使用方法可以压缩成五句话：

1. 系统 Prompt 文件定义 Agent 的角色和长期规则。
2. 用户 Prompt 文件定义本轮输入的表达结构。
3. `{name}` 和 `{question}` 是等待填充的模板变量。
4. `format_messages()` 负责把真实数据动态传入模板。
5. 系统 Prompt 传给 `create_agent()`，渲染后的用户 Prompt 传给 `agent.invoke()`。

能顺着这两条路径找到每一步对应的代码，就掌握了当前项目要学习的 Prompt Template 内容。
