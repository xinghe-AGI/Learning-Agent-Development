# Basic Demo With LangChain

## 示例核心功能

这是一个套餐客服 Agent 示例。后端使用 `create_agent()` 创建 Agent，通过 Pydantic Schema 约束套餐建议的结构；前端使用 Gradio 提供测试页面，并通过 SSE 调用 FastAPI 后端。

`agent_service.py` 负责按请求设置获取或创建模型和 Agent、处理 HTTP 请求、返回 JSON 或 SSE 事件；`web_ui.py` 只负责收集用户输入并展示后端响应。Agent 使用 `thread_id` 与 `InMemorySaver` 维护进程内短期记忆。

## 项目学习目标

完成这个示例后，应能够：

1. 使用 `PromptTemplate.from_file()` 从外部文件读取系统 Prompt 和用户 Prompt。
2. 使用 `create_agent()` 创建 LangChain Agent。
3. 使用 Pydantic `BaseModel`、`Field`、`Literal` 和 `ConfigDict` 定义结构化响应 Schema。
4. 理解 `ToolStrategy` 如何让 Agent 按 Schema 返回结构化结果。
5. 使用 `InMemorySaver` 与 `thread_id` 维护 Agent 的短期记忆。
6. 区分 WebUI、FastAPI 服务和 Agent 运行逻辑的职责。
7. 使用 `agent.astream(..., stream_mode="messages")` 与 SSE 逐步展示模型生成的结果。
8. 在 WebUI 中选择模型接口并为每次请求设置 `LLM_TEMPERATURE`。

## 学习内容

| 学习主题            | 重点理解的问题                               | 对应代码                                         |
| --------------- | ------------------------------------- | -------------------------------------------- |
| 外部 Prompt 文件    | 系统规则和用户变量怎样从文件加载？                     | `code/prompts/`、`code/agent_runtime.py`      |
| Agent 运行层       | `create_agent()` 怎样创建可运行的 Agent？      | `code/agent_runtime.py`                      |
| Pydantic Schema | 字段约束怎样让 Agent 返回可校验的数据？               | `code/utils/models.py`                       |
| Agent 短期记忆      | `thread_id` 怎样隔离不同会话的进程内状态？           | `code/agent_runtime.py`                      |
| 后端服务            | FastAPI 怎样将 Agent 的模型增量转为 SSE 事件？     | `code/agent_service.py`                      |
| 运行时模型设置         | 怎样按模型接口和温度缓存对应的 Agent？                | `code/agent_service.py`、`code/utils/llms.py` |
| WebUI           | Gradio 怎样选择模型、设置温度并展示 SSE 流式回复和结构化结果？ | `code/web_ui.py`                             |

## 项目结构

```text
01_BasicDemoWithLangChain/
├── README.md
├── .gitignore
├── notes/
│   ├── 00_项目学习总览.md
│   ├── 01_PromptTemplate与外部Prompt文件.md
│   ├── 02_create_agent与Agent运行层.md
│   ├── 03_PydanticSchema与ToolStrategy结构化输出.md
│   ├── 04_短期记忆与Agent缓存.md
│   ├── 05_运行时模型选择与LLM_TEMPERATURE.md
│   ├── 06_FastAPI_SSE与WebUI.md
│   └── notes_pictures/
└── code/
    ├── agent_service.py            # FastAPI 后端入口，提供 JSON/SSE 聊天接口
    ├── web_ui.py                   # Gradio 前端入口，通过 SSE 调用后端
    ├── agent_runtime.py            # create_agent、ToolStrategy 与 InMemorySaver
    ├── prompts/
    │   ├── system_prompt.txt
    │   └── human_prompt.txt
    ├── utils/
    │   ├── config.py
    │   ├── llms.py
    │   ├── logger.py
    │   └── models.py                # Pydantic 请求、响应与结构化输出 Schema
    ├── .env.example
    └── requirements.txt
```

## 相关学习笔记与资料

建议按以下顺序阅读：

1. [项目学习总览](<notes/00_项目学习总览.md>)：先建立代码职责与调用链的整体认识。
2. [PromptTemplate 与外部 Prompt 文件](<notes/01_PromptTemplate与外部Prompt文件.md>)：理解系统提示词与用户提示词的加载和填充方式。
3. [create_agent 与 Agent 运行层](<notes/02_create_agent与Agent运行层.md>)：理解模型、Prompt、结构化输出和 checkpointer 如何组合为 Agent。
4. [Pydantic Schema 与 ToolStrategy 结构化输出](<notes/03_PydanticSchema与ToolStrategy结构化输出.md>)：理解字段约束、工具调用形态与 `structured_response`。
5. [短期记忆与 Agent 缓存](<notes/04_短期记忆与Agent缓存.md>)：理解 `thread_id`、`InMemorySaver` 和模型设置隔离。
6. [运行时模型选择与 LLM_TEMPERATURE](<notes/05_运行时模型选择与LLM_TEMPERATURE.md>)：理解多厂商 OpenAI-compatible 接口与采样温度。
7. [FastAPI、SSE 与 WebUI](<notes/06_FastAPI_SSE与WebUI.md>)：理解请求体、SSE 事件和前端的流式展示。

### 外部参考资料

- [PromptTemplate.from_file](https://reference.langchain.com/python/langchain-core/prompts/prompt/PromptTemplate/from_file)
- [LangChain 短期记忆](https://docs.langchain.com/oss/python/langchain/short-term-memory)
- [LangChain 结构化输出](https://docs.langchain.com/oss/python/langchain/structured-output)

## 安装与依赖

### 安装

进入 `code/` 后安装依赖：

```powershell
cd code
python -m pip install -r requirements.txt
```

代码按 `langchain 1.3.x`、`langchain-openai 1.3.x`、`langgraph 1.2.x`、`Pydantic 2.x` 与 `Gradio 5–6` 的 API 组织。

### 配置模型

1. 复制 `.env.example` 为 `.env`。
2. 设置 `LLM_TYPE`，并填写对应厂商的 `BASE_URL`、`API_KEY` 和 `CHAT_MODEL`。
3. 不要把 `.env` 或日志提交到仓库。

### 启动后端与 WebUI

先启动后端服务：

```powershell
cd code
python agent_service.py
```

再新开一个终端，在同一个 `code/` 目录启动前端页面：

```powershell
python web_ui.py
```

页面右侧可以选择 `qwen`、`openai` 或 `deepseek`，并设置本轮请求的 `LLM_TEMPERATURE`。每一种“模型接口 + 温度”组合会复用独立的 Agent 与进程内短期记忆；切换组合后应点击“新建会话”，避免把不同模型的对话上下文混在同一段学习记录中。

页面设置会覆盖本轮请求的温度；直接调用 API 时若省略 `temperature`，后端会使用 `.env` 中的 `LLM_TEMPERATURE` 默认值。

页面每次请求会使用 SSE 接收 `token`、`final` 和 `done` 事件。`token` 事件逐步展示 `ToolStrategy` 结构化参数中的 `reply` 字段；`final` 事件使用 Pydantic 校验后的完整结果覆盖页面内容。点击“新建会话”会生成新的 `conversation_id`，从而使用新的 Agent `thread_id`。
