# create_agent 与 Agent 运行层

---
参考资料：
- [LangChain Agents](https://docs.langchain.com/oss/python/langchain/overview)
---

## Agent 在本项目中由什么组成

**Agent 不是单独的模型对象，而是模型外加运行约束。** 本项目将聊天模型、系统 Prompt、结构化输出策略和 checkpointer 交给 `create_agent()`，得到一个可执行、可保存会话状态的 Agent 图。

```python
self._agent = create_agent(
    model=model,
    tools=[],
    system_prompt=system_prompt,
    response_format=ToolStrategy(schema=PackageRecommendation),
    checkpointer=InMemorySaver(),
)
```

| 参数 | 本项目传入值 | 作用 |
| --- | --- | --- |
| `model` | `BaseChatModel` 抽象下的 `ChatOpenAI` | 决定模型请求如何发送 |
| `tools` | 空列表 | 本示例不执行外部业务动作 |
| `system_prompt` | 外部文件读取的规则文本 | 约束客服身份和套餐判断 |
| `response_format` | `ToolStrategy(PackageRecommendation)` | 要求最终结果符合 Schema |
| `checkpointer` | `InMemorySaver()` | 按 `thread_id` 保存进程内短期记忆 |

## 为什么构造函数接收 BaseChatModel

`AgentPackageService` 的构造函数标注为 `model: BaseChatModel`，而不是写死 `ChatOpenAI`。`BaseChatModel` 是 Agent 所需的能力边界：它只要求拿到一个可聊天的 LangChain 模型对象。

模型对象仍然由 `utils/llms.py` 创建。这样 Agent 运行层不需要理解 API Key、`base_url`、厂商名或温度设置；替换模型时，只替换注入的依赖。

## 调用入口的职责

| 方法 | 场景 | 返回内容 |
| --- | --- | --- |
| `ainvoke()` | 普通 JSON 接口 | 完整的 `PackageRecommendation` |
| `astream_tool_arguments()` | SSE 接口 | ToolStrategy 参数的增量字符串 |
| `aget_structured_response()` | 流式执行结束后 | checkpointer 中的完整 `PackageRecommendation` |

异步方法使用 `async def`，因为模型请求和流式读取都需要等待网络响应。等待期间，FastAPI 可以继续处理其他请求，而不是阻塞整个服务线程。

## 一个容易混淆的点

`tools=[]` 不代表 `ToolStrategy` 没有作用。这里没有业务工具，例如“查询账单”或“写入订单”；但 `ToolStrategy` 仍会让模型使用工具调用形态提交结构化结果。相关细节参考 [[03_PydanticSchema与ToolStrategy结构化输出]]。

## 复习重点

- **模型负责生成，Agent 负责把模型放进可控的运行框架。**
- **依赖注入降低耦合。** `AgentPackageService` 依赖聊天模型抽象，不依赖某个厂商配置。
- **运行入口应按返回模式区分。** 完整 JSON 与流式增量不应混用同一份前端处理逻辑。
- **状态配置必须在每次调用时传入。** Agent 是否记住历史由 `thread_id` 决定，而不是由 Python 对象名称决定。
