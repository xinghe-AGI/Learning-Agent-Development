# Prompt Template 学习项目

## 示例核心功能

这是一个以天气问答为场景的 LangChain Agent 示例，用来观察 Prompt Template 从文件定义、运行时渲染到进入 Agent 的完整路径。

示例实现了：

- 将系统 Prompt 与用户 Prompt 分别保存为 Markdown 模板文件。
- 使用 `PromptTemplate.from_file()` 读取外部模板。
- 使用 `ChatPromptTemplate` 组合 `system` 与 `human` 消息。
- 使用 `{name}`、`{question}` 定义变量，并通过 `format_messages()` 在运行时填入数据。
- 将系统 Prompt 传入 `create_agent()`，将渲染后的用户 Prompt 传入 `agent.invoke()`。
- 通过 `.env` 管理模型服务地址、API Key 与模型名称，并预留 OpenAI、OneAPI、通义千问和 Ollama 配置。

## 项目学习目标

完成该示例后，应能够：

1. 说明 `PromptTemplate` 与 `ChatPromptTemplate` 分别解决什么问题。
2. 区分系统 Prompt 的长期规则与用户 Prompt 的本轮动态输入。
3. 根据模板变量定义，正确使用 `format_messages()` 传入运行时数据。
4. 说明模板文件、模型配置和 Agent 调用各自的边界。

## 学习内容

| 学习主题 | 重点理解的问题 | 对应代码 |
| --- | --- | --- |
| 系统 Prompt 模板 | 角色、工具说明和长期规则如何外置？ | `code/prompt/system_prompt_tmpl.md` |
| 用户 Prompt 模板 | 本轮用户信息与问题如何组织？ | `code/prompt/human_prompt_tmpl.md` |
| 模板变量 | `{name}`、`{question}` 如何声明和替换？ | `code/agent.py` |
| Prompt 渲染 | `format_messages()` 如何生成角色消息列表？ | `code/agent.py` |
| Prompt 进入 Agent | 系统 Prompt 与用户 Prompt 怎样进入 Agent 调用？ | `code/agent.py` |
| 模板路径与运行目录 | 相对路径为什么应以 `code/` 作为执行边界？ | `code/utils/config.py` |

## 项目结构

```text
02_Study_PromptTemplate/
├── README.md                        # 项目入口与学习导航
├── .gitignore                       # 忽略本地敏感配置与运行产物
├── notes/                           # 项目学习笔记
│   └── ChatPromptTemplate详解.md
└── code/
    ├── agent.py                     # Agent 创建和运行入口
    ├── .env.example                 # 模型配置示例，不包含真实 Key
    ├── .env                         # 本机配置，不提交
    ├── prompt/
    │   ├── system_prompt_tmpl.md    # 系统 Prompt 模板
    │   └── human_prompt_tmpl.md     # 用户 Prompt 模板和变量
    ├── utils/
    │   ├── config.py                # 模型类型、日志和模板路径
    │   ├── llms.py                  # 加载 .env 并初始化模型
    │   ├── tools.py                 # 天气 Agent 工具
    │   ├── models.py                # Context 和结构化响应模型
    │   └── logger.py                # 日志配置
    └── logfile/                     # 本地运行日志
```

## 相关学习笔记

- [PromptTemplate 与 ChatPromptTemplate 使用方法](<notes/ChatPromptTemplate详解.md>)：沿着模板文件、变量渲染和 Agent 调用理解完整使用路径。

## 安装与依赖

### 环境与版本

当前项目按以下版本编写：

| 环境或包 | 版本 | 项目中的作用 |
| --- | --- | --- |
| Python | `3.13.9` | 项目运行环境 |
| `langchain` | `1.2.1` | 创建 Agent 和组织 LangChain 应用 |
| `langchain-openai` | `1.1.6` | 接入 OpenAI 及 OpenAI-compatible 模型 |
| `langgraph` | `1.0.2` | 提供 Agent 短期状态存储 |
| `concurrent-log-handler` | `0.9.28` | 日志文件轮转和并发写入 |
| `python-dotenv` | `1.0.0` | 从 `.env` 加载模型配置 |

安装依赖：

```powershell
pip install langchain==1.2.1 langchain-openai==1.1.6 langgraph==1.0.2 concurrent-log-handler==0.9.28 python-dotenv==1.0.0
```

### 配置模型

1. 参考 [code/.env.example](<code/.env.example>) 创建本机 `code/.env`。
2. 填写模型服务 URL、API Key、Chat Model 与 Embedding Model。
3. 在 `code/utils/config.py` 中选择 `Config.LLM_TYPE`。

`.env` 已加入 `.gitignore`。不要把 API Key、token 或其他凭据写入代码、笔记或提交记录。

### 运行示例

从当前项目目录进入 `code/` 后运行：

```powershell
cd code
python agent.py
```