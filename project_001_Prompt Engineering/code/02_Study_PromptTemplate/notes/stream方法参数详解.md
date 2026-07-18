# stream 方法参数详解

## 1. 核心参数分析

### 1.1 消息参数
```python
{"messages": [{"role": "user", "content": human_msg.content}]}
```

**参数结构**：
- **外层字典**：包含 `messages` 键
- **messages 值**：消息列表，每条消息是一个字典
- **消息字典**：
  - `role`：消息角色，如 `"user"`、`"assistant"`、`"system"` 等
  - `content`：消息内容，这里是渲染后的用户提示

**数据类型**：字典
**取值范围**：包含 `messages` 键的有效字典
**默认值**：无（必填参数）
**使用场景**：
- 传递用户输入的消息给 Agent
- 支持多轮对话，可包含历史消息
- 是 Agent 执行的核心输入数据

**注意事项**：
- 消息列表的顺序代表对话的时间顺序
- 系统消息通常放在最前面
- 工具调用需要遵循 assistant → tool → assistant 的流程

### 1.2 配置参数
```python
config=config
```

**参数结构**：
- 通常是一个字典，包含 `configurable` 键
- `configurable` 值是另一个字典，包含 `thread_id` 等配置

**数据类型**：字典
**取值范围**：包含 `configurable` 键的有效字典
**默认值**：无（必填参数）
**使用场景**：
- **线程标识**：通过 `thread_id` 标识对话线程
- **状态隔离**：不同 `thread_id` 之间状态隔离
- **状态共享**：相同 `thread_id` 共享对话上下文
- **执行配置**：可包含其他执行相关的配置参数

**注意事项**：
- 相同的 `thread_id` 会共享对话状态
- 不同的 `thread_id` 会保持状态隔离
- 对于流式调用，`thread_id` 同样重要，确保状态一致性

### 1.3 上下文参数
```python
context=Context(user_id="1")
```

**参数结构**：
- `Context` 是自定义的上下文类实例
- 通常包含 `user_id` 等业务相关信息

**数据类型**：Context 类实例
**取值范围**：有效的 Context 实例
**默认值**：无（必填参数）
**使用场景**：
- 传递业务上下文信息给 Agent
- 在 Agent 执行过程中可访问这些信息
- 支持业务逻辑的个性化处理
- 可用于扩展 Agent 的状态信息

**注意事项**：
- Context 类需要在创建 Agent 时通过 `context_schema` 参数指定
- 确保传入的 Context 实例包含所有必要的业务信息

### 1.4 流式模式参数
```python
stream_mode=["updates", "custom"]
```

**参数结构**：
- 字符串或字符串列表，指定流式输出的模式

**数据类型**：字符串或字符串列表
**取值范围**：
- `"updates"`：按 Agent 步骤推送状态更新
- `"messages"`：按 LLM token 级流式输出
- `"custom"`：自定义数据流
- 列表形式：组合多种流式模式

**默认值**：无（必填参数）
**使用场景**：
- **updates 模式**：适合步骤级进度展示、业务侧进度条、调试与观测
- **messages 模式**：适合聊天 UI 实时打字效果、工具调用 JSON 增量可视化
- **custom 模式**：适合细粒度任务进度、模型外长耗时操作回报
- **组合模式**：适合复杂场景，同时需要多种流式信息

**注意事项**：
- 不同模式返回的数据结构不同
- 组合模式需要分别处理不同类型的数据流
- 流式模式会影响性能和网络带宽使用

## 2. 实际应用分析

### 2.1 单模式调用示例

#### 2.1.1 updates 模式
```python
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": human_msg.content}]},
    config=config,
    context=Context(user_id="1"),
    stream_mode="updates",
):
    for step, data in chunk.items():
        print(f"当前步骤: {step}")
        print(f"当前步骤返回内容: {data['messages'][-1].content_blocks}")
```

**数据结构**：
- `chunk`：字典，key 是步骤名，value 是该步骤的状态数据
- `data['messages'][-1]`：当前步骤的最后一条消息

**使用场景**：
- 多工具/多步骤 Agent 流程可视化
- 业务侧进度条/步骤展示
- 调试与观测复杂 Agent 流程

#### 2.1.2 messages 模式
```python
for token, metadata in agent.stream(
    {"messages": [{"role": "user", "content": human_msg.content}]},
    config=config,
    context=Context(user_id="1"),
    stream_mode="messages"
):
    print(f"当前节点: {metadata['langgraph_node']}")
    print(f"当前节点内容: {token.content_blocks}")
```

**数据结构**：
- `token`：消息分片，如 `AIMessageChunk`
- `metadata`：元数据，包含节点名等信息

**使用场景**：
- 聊天 UI 实时打字效果
- 工具调用 JSON 增量可视化
- 多 LLM / 子 Agent token 源区分

#### 2.1.3 custom 模式
```python
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": human_msg.content}]},
    config=config,
    context=Context(user_id="1"),
    stream_mode="custom",
):
    print(f"当前数据块: {chunk}")
```

**数据结构**：
- `chunk`：工具等节点通过 `get_stream_writer` 写出的自定义数据

**使用场景**：
- 细粒度任务进度反馈
- 模型外长耗时操作回报
- 高级 Guardrail / 中间评估结果曝光

### 2.2 组合模式调用示例

#### 2.2.1 updates + custom 组合
```python
for stream_mode, chunk in agent.stream(
    {"messages": [{"role": "user", "content": human_msg.content}]},
    config=config,
    context=Context(user_id="1"),
    stream_mode=["updates", "custom"]
):
    if stream_mode == "custom":
        print(f"当前流式模式返回的内容: {chunk}")
    elif stream_mode == "updates":
        for step, data in chunk.items():
            print(f"当前步骤: {step}")
            print(f"当前步骤返回内容: {data['messages'][-1].content_blocks}")
```

**数据结构**：
- `stream_mode`：当前数据的流式模式
- `chunk`：根据模式不同，数据结构也不同

**使用场景**：
- 同时需要步骤级更新和自定义业务进度
- 复杂业务流程的全面监控

#### 2.2.2 messages + custom 组合
```python
for stream_mode, payload in agent.stream(
    {"messages": [{"role": "user", "content": human_msg.content}]},
    config=config,
    context=Context(user_id="1"),
    stream_mode=["messages", "custom"]
):
    if stream_mode == "custom":
        print(f"当前流式模式返回的内容: {payload}")
    elif stream_mode == "messages":
        token, metadata = payload
        print(f"当前节点: {metadata['langgraph_node']}")
        print(f"当前节点内容: {token.content_blocks}")
```

**数据结构**：
- `stream_mode`：当前数据的流式模式
- `payload`：根据模式不同，数据结构也不同
  - `custom` 模式：自定义数据
  - `messages` 模式：(token, metadata) 二元组

**使用场景**：
- 同时需要实时打字效果和自定义业务进度
- 复杂交互场景的用户体验优化

#### 2.2.3 messages + updates 组合
```python
for stream_mode, payload in agent.stream(
    {"messages": [{"role": "user", "content": human_msg.content}]},
    config=config,
    context=Context(user_id="1"),
    stream_mode=["messages", "updates"]
):
    if stream_mode == "messages":
        token, metadata = payload
        if isinstance(token, AIMessageChunk):
            if token.text:
                print(f"流式文本数据：{token.text} ", end="|")
            if token.tool_call_chunks:
                print(f"流式工具参数数据：{token.tool_call_chunks}")
    elif stream_mode == "updates":
        for source, update in payload.items():
            if source in ("model", "tools"):
                message = update["messages"][-1]
                if isinstance(message, AIMessage) and message.tool_calls:
                    print(f"非流式工具调用完整参数: {message.tool_calls}")
                if isinstance(message, ToolMessage):
                    print(f"非流式工具调用完整返回内容: {message.content_blocks}")
```

**数据结构**：
- `stream_mode`：当前数据的流式模式
- `payload`：根据模式不同，数据结构也不同
  - `messages` 模式：(token, metadata) 二元组
  - `updates` 模式：步骤更新字典

**使用场景**：
- 同时需要实时打字效果和步骤级更新
- 工具调用场景，需要完整的工具调用参数和结果

## 3. 与其他功能模块的交互逻辑

### 3.1 与 Prompt 模板的交互
```python
# 加载提示词模板
system_prompt = PromptTemplate.from_file(
    template_file=Config.SYSTEM_PROMPT_TMPL,
    encoding="utf-8"
).template

human_prompt = PromptTemplate.from_file(
    template_file=Config.HUMAN_PROMPT_TMPL,
    encoding="utf-8"
).template

# 构建聊天提示模板
chat_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", human_prompt)
])

# 渲染模板
messages = chat_prompt.format_messages(question=raw_question, name=name)
human_msg = messages[-1]

# 传递渲染后的消息
response = agent.stream(
    {"messages": [{"role": "user", "content": human_msg.content}]},
    # 其他参数...
)
```

**交互逻辑**：
- Prompt 模板用于生成结构化的提示词
- 渲染后的消息作为 stream 方法的输入
- 不同流式模式会影响提示词的处理方式

### 3.2 与工具模块的交互
```python
# 获取工具列表
tools = get_tools()

# 创建 Agent 时传入工具
agent = create_agent(
    model=llm_chat,
    system_prompt=system_prompt,
    tools=tools,
    # 其他参数...
)

# 流式调用
for chunk in agent.stream(
    # 参数...
):
    # 处理工具调用相关的流式数据
```

**交互逻辑**：
- 工具调用会在流式输出中产生特定的消息类型
- updates 模式可以获取工具执行的完整结果
- messages 模式可以实时查看工具调用参数的生成过程
- custom 模式可以从工具中获取自定义进度信息

### 3.3 与上下文管理的交互
```python
# 创建上下文
context = Context(user_id="1")

# 流式调用
for chunk in agent.stream(
    # 其他参数...
    context=context,
):
    # 处理流式数据
```

**交互逻辑**：
- 上下文信息会传递给 Agent 的执行过程
- 工具和节点可以访问上下文中的信息
- 上下文中的信息可能会影响流式输出的内容

## 4. 注意事项与最佳实践

### 4.1 性能优化
- **流式模式选择**：根据实际需求选择合适的流式模式
- **数据处理**：及时处理流式数据，避免内存堆积
- **网络带宽**：考虑流式传输对网络带宽的影响
- **并发控制**：避免同时发起过多的流式调用

### 4.2 错误处理
- **异常捕获**：对流式调用过程中的异常进行捕获
- **重试机制**：实现适当的重试逻辑
- **超时处理**：设置合理的超时时间
- **错误反馈**：及时向用户反馈错误信息

### 4.3 用户体验
- **实时反馈**：利用流式输出提供实时反馈
- **进度展示**：使用 updates 模式展示执行进度
- **打字效果**：使用 messages 模式实现打字机效果
- **错误提示**：及时展示错误信息和处理建议

### 4.4 调试与监控
- **日志记录**：详细记录流式数据，便于调试
- **状态监控**：监控 Agent 的执行状态
- **性能分析**：分析不同流式模式的性能表现
- **问题定位**：利用流式数据快速定位问题

## 5. 总结

`stream` 方法是 LangChain V1.x 中实现流式输出的核心方法，通过不同的流式模式，可以满足各种场景的需求：

| 参数 | 类型 | 作用 | 示例 |
|------|------|------|------|
| 消息参数 | 字典 | 传递用户输入 | `{"messages": [{"role": "user", "content": "天气怎么样？"}]}` |
| config | 字典 | 配置执行环境 | `{"configurable": {"thread_id": "1"}}` |
| context | Context 实例 | 传递业务上下文 | `Context(user_id="1")` |
| stream_mode | 字符串或列表 | 指定流式模式 | `"updates"` 或 `["messages", "custom"]` |

通过合理配置这些参数，可以实现：
- 实时的打字机效果
- 步骤级的执行进度展示
- 自定义的业务进度反馈
- 复杂场景的多模式组合

`stream` 方法的灵活运用，能够显著提升用户体验，特别是在需要实时反馈的场景中。结合实际业务需求，选择合适的流式模式和参数配置，是构建高质量 LangChain 应用的关键。