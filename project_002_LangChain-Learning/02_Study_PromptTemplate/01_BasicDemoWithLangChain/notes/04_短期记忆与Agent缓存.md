# 短期记忆与 Agent 缓存

---
参考资料：
- [LangChain Short-term memory](https://docs.langchain.com/oss/python/langchain/short-term-memory)
---

## thread_id 是会话状态的定位键

**短期记忆不是自动按“浏览器页面”保存，而是按 `thread_id` 保存。** 项目把 `user_id` 和 `conversation_id` 组合为唯一会话标识：

```python
thread_id = f"{user_id}:{conversation_id}"
config = {"configurable": {"thread_id": thread_id}}
```

每次调用 `ainvoke()`、`astream_tool_arguments()` 或 `aget_structured_response()` 都使用相同配置。相同 `thread_id` 会读取和写入同一段 Agent 状态，不同值则隔离会话。

## InMemorySaver 保存什么

`InMemorySaver()` 是 Agent 的 checkpointer。它把图运行过程的状态快照保存在 Python 进程内存中，状态包含对话消息和最终的 `structured_response` 等数据。

| 特性 | InMemorySaver 的表现 |
| --- | --- |
| 同一服务进程内连续对话 | 可以恢复历史状态 |
| 重启 `agent_service.py` | 内存清空，会话记忆丢失 |
| 多进程或多实例部署 | 不共享状态 |
| 适合场景 | 学习、原型、单进程本地演示 |

因此它适合本项目理解 `thread_id` 和 Agent 状态，不适合作为生产持久化方案。生产环境通常需要共享、持久化的 checkpointer 或数据库后端，并需要考虑会话过期、并发、访问控制和数据保留策略。

## Agent 缓存为什么和模型设置绑定

服务层以 `(llm_type, temperature)` 作为缓存键：

```python
cache_key = (llm_type, temperature)
```

同一模型接口和温度会复用同一个 `AgentPackageService`，因此它们也复用其中的 `InMemorySaver`。切换模型或温度会得到另一个 Agent 实例和另一块内存状态，避免把不同模型配置下的历史混在同一份 checkpointer 中。

页面中的“新建会话”只生成新的 `conversation_id`，不会清除后端已存在的内存快照；重启后端服务才会全部清空。切换模型或温度后再新建会话，可以让学习过程中的对话边界更清楚。

## 复习重点

- **`conversation_id` 是前端会话标识，`thread_id` 是 Agent 状态定位键。**
- **同一 Agent 实例不等于同一会话。** 会话是否连续取决于调用时传入的 `thread_id`。
- **内存缓存不等于持久化存储。** `InMemorySaver` 的生命周期受后端进程限制。
- **模型设置是状态隔离维度。** 同一 `conversation_id` 在不同模型组合下不应被视为同一段对话。

模型设置如何创建和传递，参考 [[05_运行时模型选择与LLM_TEMPERATURE]]。
