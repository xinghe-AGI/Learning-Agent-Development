# LangChain 1.x Quickstart 学习项目

## 示例核心功能

这是一个以天气问答为场景的 LangChain 1.x Agent Quickstart，用来观察模型、消息、工具、结构化输出、短期记忆和调用记录怎样组成一个可以循环决策的 Agent。

示例实现了：

- 使用 `ChatOpenAI` 连接 OpenAI 和多个 OpenAI-compatible 模型服务。
- 使用 system prompt 定义天气预报员角色、地点确认规则和工具使用方式。
- 通过 `@tool` 声明用户定位与天气查询工具。
- 通过 `ToolRuntime[Context]` 向工具注入本次运行的用户上下文。
- 通过 `create_agent()` 组装模型、工具、Prompt、结构化输出与短期记忆。
- 通过 `WeatherResponseFormat` 定义结构化输出，并保留 `ToolStrategy` / `ProviderStrategy` 的对照写法。
- 通过 `InMemorySaver` 和 `thread_id` 保存、恢复线程级对话历史。
- 通过 `call_records.py` 汇总模型信息、Token usage、finish reason 和工具调用记录。

## 项目学习目标

完成这个示例后，需要能够：

1. 说明一个 LangChain Agent 怎样由 Chat Model、system prompt、tools、context schema、response format 和 checkpointer 组成。
2. 区分模型生成工具调用意图与业务系统真正执行工具这两个阶段。
3. 区分 `messages`、Agent state、runtime context、Runnable config 和 `thread_id` 的职责。
4. 理解 OpenAI-compatible 模型服务怎样复用 `ChatOpenAI`，以及它与原生 Provider integration 的区别。
5. 读取 `AIMessage`、`ToolMessage`、`structured_response`、usage 和 finish reason 等关键结果。
6. 解释 `ToolStrategy`、`ProviderStrategy`、JSON Schema 与结构化输出失败修复之间的关系。
7. 使用短期记忆和 LangSmith／本地调用记录观察 Agent 的完整执行过程。

## 学习内容

| 学习主题 | 重点理解的问题 | 对应代码 |
| --- | --- | --- |
| 各厂商 LLM 集成 | 原生 Provider 与 OpenAI-compatible 接入有什么区别？ | `code/utils/llms.py` |
| 模型采样参数 | `temperature`、`top_p`、`top_k`、penalty 和输出长度怎样影响生成？ | `code/utils/llms.py` |
| 结构化输出 | JSON Mode、JSON Schema、Pydantic Schema、ToolStrategy、ProviderStrategy 有什么区别？ | `code/utils/models.py`、`code/agent.py` |
| Tools 与 Function Calling | 模型怎样提出调用意图，Agent runtime 怎样执行并回传结果？ | `code/utils/tools.py`、`code/agent.py` |
| `create_agent()` | 可以传入哪些对象？state、context 与 config 有什么区别？ | `code/agent.py` |
| Agent 短期记忆 | checkpointer 和 `thread_id` 怎样共同维护、隔离历史？ | `code/agent.py` |
| 请求与响应结构 | `model`、`messages/input`、instructions、tools、stream、usage 等字段位于哪一层？ | `code/agent.py`、`code/utils/call_records.py` |
| API 协议模型 | Chat Completions、Responses、Anthropic Messages 怎样表达消息和工具结果？ | `code/agent.py`、LangChain message 对象 |
| LangSmith 与调用记录 | 怎样观察模型调用、工具步骤、Token、延迟和错误？ | `code/agent.py`、`code/utils/call_records.py` |

## 项目结构

```text
01_Study_Quickstart/
├── README.md                             # 示例功能、学习目标、笔记与依赖
├── notes/
│   ├── 00_Quickstart代码导读.md
│   ├── 01_多厂商LLM集成与API协议.md
│   ├── 02_模型采样参数与ChatOpenAI.md
│   ├── 03_结构化输出.md
│   ├── 04_Tools与FunctionCalling.md
│   ├── 05_create_agent参数详解.md
│   ├── 06_Agent短期记忆.md
│   ├── 07_模型请求与响应结构.md
│   ├── 08_LangSmith跟踪与调用记录.md
│   ├── 09_ChatOpenAI与init_chat_model的区别.md
│   ├── 10_ChatOpenAI对象详解.md
│   ├── 11_init_chat_model方法详解.md
│   ├── 12_Schema基础概念.md
│   ├── 13_OpenAI API结构化输出.md
│   ├── 14_ToolStrategy详解.md
│   ├── 15_ProviderStrategy详解.md
│   ├── 16_ToolStrategy和ProviderStrategy区别.md
│   ├── 17_结构化输出失败原因与处理.md
│   └── 18_Pydantic增强Schema与dataclass区别.md
└── code/
    ├── agent.py                          # Agent 创建和运行入口
    ├── .env.example                      # 模型配置示例，不包含真实 Key
    ├── .env                              # 本机配置，不提交
    ├── utils/
    │   ├── config.py                     # 模型类型和日志配置
    │   ├── llms.py                       # 初始化 Chat Model 与 Embedding
    │   ├── tools.py                      # 用户定位和天气查询工具
    │   ├── models.py                     # Runtime Context 和结构化响应模型
    │   ├── call_records.py               # 提取 Token、finish reason 和工具调用记录
    │   └── logger.py                     # 本地日志配置
    └── logfile/                          # 运行日志目录
```

配图统一存放在同级学习项目的 [notes/notes_pictures](<../notes/notes_pictures>) 目录中，笔记通过相对路径引用。

## 相关学习笔记

建议先读代码导读建立执行主线，再进入各专题：

1. [Quickstart 代码导读](<notes/00_Quickstart代码导读.md>)：沿着一次真实执行路径理解整个案例。
2. [多厂商 LLM 集成与 API 协议](<notes/01_多厂商LLM集成与API协议.md>)：理解模型配置、Provider 与 API 协议。
3. [ChatOpenAI 对象详解](<notes/10_ChatOpenAI对象详解.md>)：理解构造参数、调用参数、能力绑定与返回对象。
4. [`init_chat_model` 方法详解](<notes/11_init_chat_model方法详解.md>)：理解工厂参数、Provider 映射、固定模式与运行时配置。
5. [ChatOpenAI 与 init_chat_model 的区别](<notes/09_ChatOpenAI与init_chat_model的区别.md>)：在分别理解两个对象后比较它们的关系、差异和选择方法。
6. [模型采样参数与 ChatOpenAI](<notes/02_模型采样参数与ChatOpenAI.md>)：理解模型初始化参数怎样影响生成。
7. [Schema 基础概念](<notes/12_Schema基础概念.md>)：理解 Schema、数据实例、必填、可空与可省略的区别。
8. [Pydantic 增强 Schema 与 dataclass 区别](<notes/18_Pydantic增强Schema与dataclass区别.md>)：理解生产中为什么更常用 Pydantic 定义结构化输出 Schema。
9. [OpenAI API 结构化输出](<notes/13_OpenAI API结构化输出.md>)：理解 JSON Mode、Function Calling strict 和原生 `json_schema`。
10. [结构化输出](<notes/03_结构化输出.md>)：理解当前项目的 Schema、ToolStrategy 与 ProviderStrategy。
11. [ToolStrategy 详解](<notes/14_ToolStrategy详解.md>)：理解人工结构化工具怎样承载最终结果。
12. [ProviderStrategy 详解](<notes/15_ProviderStrategy详解.md>)：理解 Provider 原生结构化输出怎样接入 Agent。
13. [ToolStrategy 和 ProviderStrategy 区别](<notes/16_ToolStrategy和ProviderStrategy区别.md>)：比较两种结构化输出策略的选择条件和失败形态。
14. [结构化输出失败原因与处理](<notes/17_结构化输出失败原因与处理.md>)：按失败层级排查 Schema、Provider、模型生成和业务校验问题。
15. [Tools 与 Function Calling](<notes/04_Tools与FunctionCalling.md>)：理解工具定义、调用意图、执行与结果回传。
16. [`create_agent` 参数详解](<notes/05_create_agent参数详解.md>)：理解 Agent 装配时可以传入的对象。
17. [Agent 短期记忆](<notes/06_Agent短期记忆.md>)：理解 checkpointer 与线程状态。
18. [模型请求与响应结构](<notes/07_模型请求与响应结构.md>)：在理解结构化输出、工具调用、Agent 装配和短期记忆后，再分析完整消息状态与协议字段。
19. [LangSmith 跟踪与调用记录](<notes/08_LangSmith跟踪与调用记录.md>)：理解调用链观测和本地记录。

### 外部参考资料

- [LangChain Python Overview](https://docs.langchain.com/oss/python/langchain/overview)
- [LangChain Quickstart](https://docs.langchain.com/oss/python/langchain/quickstart)
- [NanGePlus/LangChain_V1_Test](https://github.com/NanGePlus/LangChain_V1_Test)

## 安装与依赖

### 环境与版本

当前源码按以下版本编写：

| 环境或包 | 版本 | 项目中的作用 |
| --- | --- | --- |
| Python | `3.13.9` | 项目运行环境 |
| `langchain` | `1.2.1` | 创建 Agent、组织消息和结构化输出 |
| `langchain-openai` | `1.1.6` | 使用 `ChatOpenAI` 和 `OpenAIEmbeddings` |
| `langgraph` | `1.0.2` | 提供 `InMemorySaver` 和 Agent 状态持久化 |
| `concurrent-log-handler` | `0.9.28` | 日志轮转和并发写入 |
| `python-dotenv` | `1.0.0` | 从 `.env` 加载模型配置 |

安装依赖：

```powershell
pip install langchain==1.2.1 langchain-openai==1.1.6 langgraph==1.0.2 concurrent-log-handler==0.9.28 python-dotenv==1.0.0
```

### 配置模型

1. 参考 [code/.env.example](<code/.env.example>) 创建本机 `code/.env`。
2. 填写准备使用的模型服务 URL、API Key、Chat Model 和 Embedding Model。
3. 在 `code/utils/config.py` 中通过 `Config.LLM_TYPE` 选择 `openai`、`qwen`、`oneapi` 或 `ollama`。

`.env` 只保存本机配置。不要把 API Key、token 或其他凭据写入代码、笔记或提交记录。

### 运行 Agent

从当前项目目录进入 `code/` 后运行：

```powershell
cd code
python agent.py
```
