# PromptTemplate 与 ChatPromptTemplate 使用方法

## 核心概念

**`PromptTemplate` 用于管理一段可复用的文本模板，`ChatPromptTemplate` 用于把多段模板组织为带角色的消息列表。** 前者解决“文本如何定义与填充变量”，后者解决“system、human 等消息如何组合”。

本项目把天气 Agent 的规则和用户输入拆成两个 Markdown 文件：系统 Prompt 约束 Agent 的长期行为，用户 Prompt 描述本轮问题并包含变量。相关入口可以参考 [agent.py](<../code/agent.py>)、[config.py](<../code/utils/config.py>) 与 [Prompt 模板目录](<../code/prompt>)。

## 项目中的 Prompt 职责划分

| 组成 | 代码或文件 | 职责 | 是否包含运行时变量 |
| --- | --- | --- | --- |
| 系统 Prompt | [system_prompt_tmpl.md](<../code/prompt/system_prompt_tmpl.md>) | 定义角色、可用工具和天气查询规则 | 否 |
| 用户 Prompt | [human_prompt_tmpl.md](<../code/prompt/human_prompt_tmpl.md>) | 规定本轮回答风格，并接收姓名和问题 | 是，`{name}`、`{question}` |
| 路径配置 | [config.py](<../code/utils/config.py>) | 指定两份模板的相对路径 | 否 |
| 文本加载 | [agent.py](<../code/agent.py>) | 通过 `PromptTemplate.from_file()` 读取模板文本 | 否 |
| 消息组合与渲染 | [agent.py](<../code/agent.py>) | 通过 `ChatPromptTemplate` 生成 `SystemMessage` 与 `HumanMessage` | 是 |
| Agent 调用 | [agent.py](<../code/agent.py>) | 把系统规则与渲染后的用户消息分别交给 Agent | 是 |

**系统 Prompt 决定 Agent 应当怎样工作；用户 Prompt 决定本轮请求怎样表达。**

## PromptTemplate：读取并复用单段文本

`PromptTemplate` 的核心是模板字符串与变量占位符。项目使用 `from_file()` 将模板内容从文件读入，再通过 `.template` 获取原始文本：

```python
system_prompt = PromptTemplate.from_file(
    template_file=Config.SYSTEM_PROMPT_TMPL,
    encoding="utf-8",
).template

human_prompt = PromptTemplate.from_file(
    template_file=Config.HUMAN_PROMPT_TMPL,
    encoding="utf-8",
).template
```

这段代码中各对象的含义如下：

| 表达式 | 类型或结果 | 作用 |
| --- | --- | --- |
| `PromptTemplate.from_file(...)` | `PromptTemplate` 对象 | 读取并解析模板文件 |
| `.template` | `str` | 取得尚未填充变量的原始模板文本 |
| `human_prompt` | 包含 `{name}`、`{question}` 的字符串 | 供后续消息模板渲染 |
| `system_prompt` | 规则文本 | 同时作为 Agent 的系统提示词来源 |

### 系统 Prompt 适合放什么

系统 Prompt 应保存相对稳定、跨多轮请求都有效的约束。该项目的系统模板包含：

- **角色**：擅长讲冷笑话的天气预报员。
- **工具边界**：可以查询地点和天气。
- **行为规则**：回答天气前先确认地点；用户询问“我所在的地方”时先查询用户位置。

系统规则不应混入本轮姓名、问题、订单号等临时数据。临时数据应放入用户 Prompt 或运行时上下文。

### 用户 Prompt 中的变量

用户模板包含两个占位符：

```text
用户的名字是：{name}。
用户原始问题是：{question}
```

| 变量 | 传入位置 | 示例值 |
| --- | --- | --- |
| `{name}` | `format_messages(name=...)` | `星禾` |
| `{question}` | `format_messages(question=...)` | `外面的天气怎么样？` |

**模板中的变量名必须与传参名完全一致。** `{name}` 不能通过 `username=...` 填充；缺少任一必填变量时，模板渲染会失败。

## ChatPromptTemplate：将文本组织成消息

`ChatPromptTemplate` 不负责调用模型，而是根据角色和变量生成消息对象。项目中使用两段文本创建聊天模板：

```python
chat_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", human_prompt),
])
```

调用渲染方法后，会得到按角色排列的消息列表：

```python
messages = chat_prompt.format_messages(
    question=raw_question,
    name=name,
)

human_msg = messages[-1]
```

| 结果 | 类型 | 内容来源 |
| --- | --- | --- |
| `messages[0]` | `SystemMessage` | `system_prompt_tmpl.md` |
| `messages[-1]` | `HumanMessage` | 填入 `name` 与 `question` 后的用户模板 |
| `human_msg.content` | `str` | 最终发送给 Agent 的用户文本 |

`format_messages()` 的价值在于：它一次完成变量校验、变量替换和角色消息构造。相比手写字符串拼接，模板文件更容易维护，也更容易发现漏传变量的问题。

## 本项目怎样把 Prompt 交给 Agent

项目中的两条 Prompt 路径不同，需要分开理解。

1. `system_prompt_tmpl.md` 被读取为 `system_prompt` 字符串。
2. 创建 Agent 时，`system_prompt` 通过 `create_agent(system_prompt=system_prompt)` 注入，成为 Agent 的系统级规则。
3. `human_prompt_tmpl.md` 被读取为 `human_prompt` 字符串，并与系统文本一起构造成 `ChatPromptTemplate`。
4. `format_messages(question=..., name=...)` 根据变量生成消息列表。
5. 程序取出最后一条 `HumanMessage` 的 `content`，作为本轮用户输入传给 `agent.invoke()`。

对应的关键调用是：

```python
agent = create_agent(
    model=llm_chat,
    system_prompt=system_prompt,
    tools=tools,
    context_schema=Context,
    response_format=ToolStrategy(ResponseFormat),
    checkpointer=checkpointer,
)

response = agent.invoke(
    {"messages": [{"role": "user", "content": human_msg.content}]},
    config=config,
    context=Context(user_id="1"),
)
```

这里有一个重要细节：`ChatPromptTemplate` 会生成一条 system 消息和一条 human 消息，但该调用只取出 `human_msg.content` 传给 `agent.invoke()`；系统规则由 `create_agent(system_prompt=system_prompt)` 单独提供。**同一份系统规则不应同时以 `system_prompt` 参数和请求消息重复注入，否则会造成指令重复。**

## Prompt、配置与运行目录的边界

| 内容 | 应放位置 | 原因 |
| --- | --- | --- |
| 角色、工具说明、行为规则 | `code/prompt/system_prompt_tmpl.md` | 属于模型行为约束 |
| 用户输入结构、回答风格、变量 | `code/prompt/human_prompt_tmpl.md` | 属于本轮请求表达 |
| 模板相对路径、模型类型、日志路径 | `code/utils/config.py` | 属于应用配置 |
| API Key、Base URL、模型名称 | `code/.env` | 属于本机敏感连接配置 |
| 模板加载、消息渲染、Agent 调用 | `code/agent.py` | 属于运行编排 |

`Config.SYSTEM_PROMPT_TMPL` 和 `Config.HUMAN_PROMPT_TMPL` 使用 `prompt/...` 形式的相对路径，因此应从 `code/` 目录运行：

```powershell
cd code
python agent.py
```

`.env` 与 Prompt 的职责不同：**Prompt 决定发送什么内容，`.env` 决定连接哪个模型服务。** API Key、token 和私有地址不应写入 Prompt 模板。

## 常见问题

| 现象 | 优先检查 |
| --- | --- |
| 找不到模板文件 | 是否从 `code/` 目录启动；`Config` 中的相对路径是否正确 |
| 变量未替换或报缺参 | `{name}`、`{question}` 是否与 `format_messages()` 参数同名 |
| 系统规则未生效 | `create_agent()` 是否接收到 `system_prompt` |
| 用户消息仍保留花括号 | 是否调用了 `format_messages()`，并使用渲染后的 `human_msg.content` |
| 指令重复或互相冲突 | 是否把同一系统规则同时传入 `system_prompt` 和请求消息 |
| 敏感信息出现在模板中 | 将 API Key、token、私有地址迁回 `.env` |

## 复习重点

- `PromptTemplate` 管理单段模板文本；`ChatPromptTemplate` 管理带角色的消息组合。
- 系统 Prompt 放长期规则，用户 Prompt 放本轮任务与动态变量。
- `format_messages()` 必须提供模板所需的全部变量，并返回消息对象列表。
- 本项目由 `create_agent(system_prompt=...)` 注入系统规则，由 `agent.invoke(messages=...)` 接收渲染后的用户内容。
- 模板路径以 `code/` 为运行边界；运行目录错误会导致相对路径失效。