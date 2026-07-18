# LangChain Agent 核心概念详解

## 1. 消息角色系统

### 1.1 支持的消息角色

LangChain 支持以下消息角色：

| 角色 | 描述 | 用途 |
|------|------|------|
| `user` | 用户消息 | 代表用户的输入和问题 |
| `assistant` | 助手消息 | 代表 Agent 的回复和响应 |
| `system` | 系统消息 | 定义 Agent 的角色和行为规则 |
| `tool` | 工具消息 | 代表工具执行的结果 |
| `function` | 函数消息 | 代表函数调用的结果（某些版本） |

### 1.2 各角色详细说明

#### 1.2.1 user 角色
- **用途**：表示用户的输入
- **示例**：
  ```python
  {"role": "user", "content": "北京的天气怎么样？"}
  ```

#### 1.2.2 assistant 角色
- **用途**：表示 Agent 的回复
- **示例**：
  ```python
  {"role": "assistant", "content": "北京今天天气晴朗，温度25度。"}
  ```
- **特殊情况**：当 Agent 调用工具时，会包含 `tool_calls` 字段
  ```python
  {
    "role": "assistant",
    "tool_calls": [
      {
        "id": "call_123",
        "type": "function",
        "function": {
          "name": "get_weather_for_location",
          "arguments": '{"location": "北京"}'
        }
      }
    ]
  }
  ```

#### 1.2.3 system 角色
- **用途**：定义 Agent 的角色、行为规则和背景信息
- **示例**：
  ```python
  {"role": "system", "content": "你是一名专业的天气预报员，擅长用幽默的语言回答问题。"}
  ```
- **特点**：系统消息通常放在消息列表的开头，对 Agent 的行为有重要影响

#### 1.2.4 tool 角色
- **用途**：表示工具执行的结果
- **示例**：
  ```python
  {
    "role": "tool",
    "tool_call_id": "call_123",
    "content": '{"temperature": 25, "condition": "晴朗", "humidity": 45}'
  }
  ```
- **特点**：`tool_call_id` 必须与对应的助手消息中的 `tool_calls.id` 匹配

#### 1.2.5 function 角色
- **用途**：表示函数调用的结果（在某些版本中使用）
- **示例**：
  ```python
  {
    "role": "function",
    "name": "get_weather_for_location",
    "content": '{"temperature": 25, "condition": "晴朗"}'
  }
  ```

### 1.3 实际应用示例

#### 1.3.1 多轮对话示例
```python
messages = [
    # 系统消息
    {"role": "system", "content": "你是一名专业的天气预报员。"},

    # 第一轮对话
    {"role": "user", "content": "北京的天气怎么样？"},
    {"role": "assistant", "content": "北京今天天气晴朗，温度25度。"},

    # 第二轮对话
    {"role": "user", "content": "明天呢？"},
    {"role": "assistant", "content": "明天北京多云，温度22度。"}
]
```

#### 1.3.2 工具调用示例
```python
messages = [
    {"role": "system", "content": "你是一名专业的天气预报员，可使用工具获取天气信息。"},
    {"role": "user", "content": "上海的天气怎么样？"},
    {"role": "assistant", "tool_calls": [
        {
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "get_weather_for_location",
                "arguments": '{"location": "上海"}'
            }
        }
    ]},
    {"role": "tool", "tool_call_id": "call_123", "content": '{"temperature": 28, "condition": "多云", "humidity": 65}'},
    {"role": "assistant", "content": "上海今天多云，温度28度，湿度65%。"}
]
```

### 1.4 消息角色的使用原则

1. **顺序重要性**：消息列表的顺序代表对话的时间顺序，Agent 会根据顺序理解上下文
2. **系统消息优先**：系统消息通常放在最前面，为 Agent 设定角色和规则
3. **工具调用流程**：工具调用需要遵循 assistant → tool → assistant 的流程
4. **多轮对话**：通过交替的 user 和 assistant 消息实现多轮对话
5. **上下文管理**：通过 `config` 中的 `thread_id` 管理不同对话的上下文

## 2. invoke 方法参数详解

### 2.1 核心参数分析

#### 2.1.1 消息参数
```python
{"messages": [{"role": "user", "content": human_msg.content}]}
```

**参数结构**：
- **外层字典**：包含 `messages` 键
- **messages 值**：消息列表，每条消息是一个字典
- **消息字典**：
  - `role`：消息角色，这里是 `"user"`（用户）
  - `content`：消息内容，这里是 `human_msg.content`（渲染后的用户提示）

**作用**：
- 传递用户输入的消息给 Agent
- 支持多轮对话，可包含历史消息
- 是 Agent 执行的核心输入数据

#### 2.1.2 配置参数
```python
config=config
```

**参数结构**：
- 通常是一个字典，包含 `configurable` 键
- `configurable` 值是另一个字典，包含 `thread_id` 等配置

**作用**：
- **线程标识**：通过 `thread_id` 标识对话线程
- **状态隔离**：不同 `thread_id` 之间状态隔离
- **状态共享**：相同 `thread_id` 共享对话上下文
- **执行配置**：可包含其他执行相关的配置参数

#### 2.1.3 上下文参数
```python
context=Context(user_id="1")
```

**参数结构**：
- `Context` 是自定义的上下文类实例
- 通常包含 `user_id` 等业务相关信息

**作用**：
- 传递业务上下文信息给 Agent
- 在 Agent 执行过程中可访问这些信息
- 支持业务逻辑的个性化处理
- 可用于扩展 Agent 的状态信息

### 2.2 参数在 Agent 执行中的作用

#### 2.2.1 消息处理流程
1. Agent 接收消息列表
2. 结合系统提示词理解用户意图
3. 根据需要调用工具获取信息
4. 生成响应并返回

#### 2.2.2 配置的影响
- **对话记忆**：通过 `thread_id` 关联之前的对话状态
- **执行环境**：影响 Agent 的执行行为和资源使用
- **状态管理**：控制对话状态的存储和恢复

#### 2.2.3 上下文的应用
- **用户标识**：通过 `user_id` 识别不同用户
- **业务逻辑**：根据上下文信息执行特定业务逻辑
- **个性化处理**：提供个性化的响应和服务

### 2.3 实际应用示例

#### 2.3.1 多轮对话示例
```python
# 第一轮对话
response1 = agent.invoke(
    {"messages": [{"role": "user", "content": "我叫张三"}]},
    config={"configurable": {"thread_id": "1"}},
    context=Context(user_id="1")
)

# 第二轮对话，Agent 应该记得用户的名字
response2 = agent.invoke(
    {"messages": [
        {"role": "user", "content": "我叫张三"},
        {"role": "assistant", "content": "你好，张三！"},
        {"role": "user", "content": "你知道我叫什么名字吗？"}
    ]},
    config={"configurable": {"thread_id": "1"}},
    context=Context(user_id="1")
)
```

#### 2.3.2 不同线程示例
```python
# 线程 1
response1 = agent.invoke(
    {"messages": [{"role": "user", "content": "北京的天气怎么样？"}]},
    config={"configurable": {"thread_id": "1"}},
    context=Context(user_id="1")
)

# 线程 2（状态隔离）
response2 = agent.invoke(
    {"messages": [{"role": "user", "content": "上海的天气怎么样？"}]},
    config={"configurable": {"thread_id": "2"}},
    context=Context(user_id="2")
)
```

### 2.4 总结

`invoke` 方法的参数设计体现了 LangChain V1.x 的灵活性和扩展性：

| 参数 | 类型 | 作用 | 示例 |
|------|------|------|------|
| 消息参数 | 字典 | 传递用户输入 | `{"messages": [{"role": "user", "content": "天气怎么样？"}]}` |
| config | 字典 | 配置执行环境 | `{"configurable": {"thread_id": "1"}}` |
| context | Context 实例 | 传递业务上下文 | `Context(user_id="1")` |

这些参数共同作用，使得 Agent 能够：
- 理解用户意图
- 维护对话状态
- 执行工具调用
- 生成个性化响应
- 适应不同业务场景

通过合理配置这些参数，可以构建更加智能、灵活的 Agent 应用。
