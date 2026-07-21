# Agent 短期记忆

---
参考资料：
- [LangChain：Short-term memory](https://docs.langchain.com/oss/python/langchain/short-term-memory)
- [LangChain：Memory overview](https://docs.langchain.com/oss/python/concepts/memory)
- [LangChain：Agents](https://docs.langchain.com/oss/python/langchain/agents)
---

## 短期记忆是什么

**Agent 短期记忆是线程级 Agent state 的持久化，核心作用是在同一段对话线程中保留历史消息和线程内状态。**

LangChain Agent 默认使用 `AgentState` 管理短期记忆，其中最重要的字段是 `messages`。每次 Agent 执行时，会先读取指定线程的 state；模型调用、工具调用或结构化输出完成后，再把更新后的 state 写回 checkpointer。

短期记忆解决的是“同一线程内的连续对话”问题，不是让模型永久记住所有用户信息。跨线程、跨会话、跨用户保留的数据，应放入长期记忆或业务数据库。

## 短期记忆由什么组成

| 组成部分 | 当前项目中的对象 | 作用 |
| --- | --- | --- |
| Agent state | `messages`、`structured_response` 等状态字段 | 保存线程内消息轨迹和运行结果 |
| `checkpointer` | `InMemorySaver()` | 按线程保存和恢复 Agent state |
| `thread_id` | `configurable.thread_id` | 指定读写哪一段线程状态 |
| `context` | `Context(user_id="1")` | 单次调用注入的运行时依赖，不属于记忆本身 |

**短期记忆成立需要两个条件：Agent 配置 checkpointer，并在调用时传入稳定的 `thread_id`。**

## 项目怎样开启短期记忆

[agent.py](<../agent.py>) 中先创建 checkpointer：

```python
checkpointer = InMemorySaver()
```

然后交给 `create_agent()`：

```python
agent = create_agent(
    model=llm_chat,
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
    context_schema=Context,
    response_format=WeatherResponseFormat,
    checkpointer=checkpointer,
)
```

调用 Agent 时通过 `config` 指定线程：

```python
config1 = {"configurable": {"thread_id": "1"}}

response = agent.invoke(
    {"messages": [{"role": "user", "content": "外面的天气怎么样？记住我的暗号是 banana-007"}]},
    config=config1,
    context=Context(user_id="1"),
)
```

同一个 `thread_id` 会延续同一段消息状态。换成不同 `thread_id`，Agent 会进入另一段隔离的线程状态。

## 当前项目怎样验证记忆

项目中准备了三个线程配置：

```python
config1 = {"configurable": {"thread_id": "1"}}
config2 = {"configurable": {"thread_id": "2"}}
config3 = {"configurable": {"thread_id": "3"}}
```

线程 1 的第一轮消息包含“记住我的暗号是 banana-007”。后续继续使用 `config1` 提问“暗号是什么？”，Agent 可以从同一线程的 `messages` 中读取历史信息。

线程 3 使用 `config3` 提问“我上一个问题是什么？我现在在哪里？暗号是什么？”。由于 `config3` 指向另一段线程状态，它不会继承线程 1 中的暗号和历史问题。

这个实验验证的是：

- **相同 `thread_id` 延续消息状态**。
- **不同 `thread_id` 隔离消息状态**。
- **记忆来自 checkpointer 保存的 Agent state，不是模型参数本身发生变化**。

## messages 在短期记忆里的作用

`messages` 是短期记忆中最核心的字段。它保存的不只是用户文本，还包括模型消息、工具调用和工具结果。

一次天气查询后，`messages` 通常包含：

| 消息类型 | 保存内容 | 记忆价值 |
| --- | --- | --- |
| `HumanMessage` | 用户问题和补充信息 | 后续对话可以引用用户说过的话 |
| `AIMessage` | 模型回复、工具调用意图和元数据 | 记录模型做过哪些决策 |
| `ToolMessage` | 工具执行结果 | 后续模型可以读取已查询到的信息 |

同一线程再次调用时，历史 `messages` 会参与下一轮 Agent 执行。模型能够回答“上一个问题是什么”“暗号是什么”，主要依赖这些历史消息仍在当前线程 state 中。

完整消息结构可以参考 [[07_模型请求与响应结构]]，工具调用消息可以参考 [[04_Tools与FunctionCalling]]。

## thread_id 和 user_id 不是一回事

项目调用中同时出现两个看起来相似的值：

```python
config={"configurable": {"thread_id": "1"}}
context=Context(user_id="1")
```

它们属于不同层：

| 字段 | 所在位置 | 作用 |
| --- | --- | --- |
| `thread_id` | Runnable `config` | 指定读写哪段短期记忆 |
| `user_id` | Runtime `context` | 给工具提供当前用户身份 |

`thread_id` 影响历史是否延续，`user_id` 影响工具按哪个用户查询数据。二者可以在示例中使用相同字符串，但生产系统不能把它们混为一谈。

典型情况：

| 操作 | 结果 |
| --- | --- |
| 保持 `user_id`，更换 `thread_id` | 工具仍按同一用户查询，但对话历史隔离 |
| 保持 `thread_id`，更换 `user_id` | 对话历史延续，但工具读取的用户身份变化 |

生产系统需要校验线程归属，避免用户通过伪造 `thread_id` 读取其他人的历史。

## Runtime Context 不是短期记忆

Runtime Context 是单次调用注入的依赖。它不会因为 checkpointer 存在就自动变成长期状态。

项目中的 `get_user_location` 工具通过 `ToolRuntime[Context]` 读取 `user_id`：

```python
@tool("get_user_location", description="根据用户 ID 检索用户信息。")
def get_user_location(runtime: ToolRuntime[Context]) -> str:
    user_id = runtime.context.user_id
```

这类数据适合放在 context 中：

- 用户 ID、租户 ID、权限范围。
- 请求来源、灰度配置、区域信息。
- 数据库连接、业务服务客户端、运行时依赖。

Context 的特点是“本轮有效”。如果需要跨多轮保留，应写入 state；如果需要跨线程保留，应写入 store 或业务数据库。

## 自定义 state：在 messages 之外保存线程内数据

默认 `AgentState` 主要保存 `messages`。如果需要在线程内保存任务阶段、工具调用次数、选中的城市等数据，可以扩展 `state_schema`：

```python
from langchain.agents import AgentState


class CustomState(AgentState):
    tool_call_count: int
    selected_city: str | None
```

创建 Agent 时传入：

```python
agent = create_agent(
    model=llm_chat,
    tools=tools,
    state_schema=CustomState,
    checkpointer=checkpointer,
)
```

工具可以通过 `runtime.state` 读取短期 state。需要从工具更新 state 时，通常使用 `Command` 返回状态更新；如果还要让模型看到工具结果，更新中应包含关联正确 `tool_call_id` 的 `ToolMessage`。

自定义 state 适合保存线程内可变数据，不适合保存跨线程共享资料。

## state、context、config、store 的边界

| 对象 | 生命周期 | 适合保存什么 |
| --- | --- | --- |
| Short-term state | 单个 `thread_id` 内，可由 checkpointer 保存 | `messages`、阶段、计数器、临时选择 |
| Runtime context | 单次调用 | 用户身份、权限范围、请求依赖 |
| Runnable config | 单次图执行配置 | `thread_id`、callbacks、tags、metadata |
| Long-term store | 跨线程、跨会话 | 用户偏好、长期记忆、共享资料 |

**线程内可变数据放 state，本轮依赖放 context，执行控制放 config，跨线程长期数据放 store。**

这条边界能避免把所有数据都塞进 `messages`，也能避免把用户身份这类运行时依赖误当成记忆。

## InMemorySaver 的边界

`InMemorySaver` 适合学习和本地实验，但不适合生产持久化。

它的主要边界：

- 进程退出后数据丢失。
- 多进程、多机器之间不共享。
- 不具备数据库级备份、权限和审计能力。
- 历史消息增长会持续占用内存。
- 不能满足容灾、恢复和长期合规保留要求。

生产环境应使用数据库支持的 checkpointer，例如 PostgreSQL、SQLite 或其他 LangGraph 支持的持久化后端。生产设计还要明确 thread ID 生成规则、用户归属校验、数据保留期、删除策略和加密策略。

## 上下文窗口不是无限记忆

checkpointer 可以保存较长的历史，但模型每次能读取的上下文仍受窗口限制。保存历史不等于模型每次都能有效利用全部历史。

历史持续增长后，常见处理方式包括：

- **裁剪消息**：只保留最近若干轮消息和必要系统消息。
- **删除无关消息**：移除与当前任务无关或过期的消息。
- **摘要历史**：把早期消息压缩成更短的摘要。
- **控制工具结果体积**：避免把大段原始数据全部写回 `ToolMessage`。
- **迁移长期事实**：把跨线程有用的信息写入 store 或业务数据库。

处理消息历史时要遵守 Provider 的消息结构要求。带工具调用的 assistant 消息通常必须跟随对应 tool result；删除消息时不能破坏工具调用与工具结果之间的配对关系。

## 结构化输出和 checkpoint

项目使用 `WeatherResponseFormat` 作为结构化输出 Schema。结构化结果会出现在 Agent 返回状态的 `structured_response` 中，同时相关消息也会进入 `messages`。

如果 checkpointer 保存了自定义 Python 对象，升级 LangGraph 或开启更严格序列化策略时，可能出现未注册类型反序列化警告。生产中应优先使用更稳定的数据模型和持久化策略，并对 checkpoint 中允许反序列化的类型保持明确控制。

结构化输出细节可以参考 [[03_结构化输出]]，Schema 建模可以参考 [[18_Pydantic增强Schema与dataclass区别]]。

## 生产使用经验

- **不要把短期记忆当长期记忆**：同一线程内历史放 state，跨线程用户资料放 store 或数据库。
- **不要把 user_id 当 thread_id**：二者职责不同，生产中要做线程归属校验。
- **不要无限累积 messages**：需要裁剪、删除、摘要和成本监控。
- **不要在工具结果中写入敏感明文**：工具返回会进入模型上下文和线程状态。
- **不要依赖 InMemorySaver 承担生产持久化**：生产应使用数据库 checkpointer。
- **不要破坏工具消息配对**：删除或裁剪消息时保留 `AIMessage.tool_calls` 与对应 `ToolMessage` 的一致性。

## 相关学习笔记

- [[05_create_agent参数详解]]：理解 `checkpointer`、`context_schema`、`state_schema` 和 `store` 的位置。
- [[07_模型请求与响应结构]]：观察 `messages` 中的用户消息、模型消息和工具消息。
- [[04_Tools与FunctionCalling]]：理解工具调用结果怎样写入线程消息状态。
- [[03_结构化输出]]：理解 `structured_response` 与 Agent state 的关系。
- [[18_Pydantic增强Schema与dataclass区别]]：理解结构化对象进入状态后的建模选择。
- [[08_LangSmith跟踪与调用记录]]：观察多轮调用、Token 累计和线程级消息轨迹。

**最终记忆：Agent 短期记忆不是模型永久记住信息，而是 checkpointer 按 `thread_id` 保存 Agent state；`messages` 保存对话和工具轨迹，`context` 注入本轮依赖，跨线程长期事实应进入 store 或业务数据库。**
