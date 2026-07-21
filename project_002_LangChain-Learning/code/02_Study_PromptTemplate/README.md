# Prompt Template 学习项目

## 项目做了什么？

这是一个以天气问答为场景的 LangChain Agent 学习项目，主要展示 Prompt Template 从文件定义到进入 Agent 的完整过程。

项目实现了：

- 将系统 Prompt 和用户 Prompt 分别保存在 Markdown 文件中。
- 使用 `PromptTemplate.from_file()` 加载外部模板。
- 使用 `ChatPromptTemplate` 组合 `system` 和 `human` 消息。
- 使用 `{name}`、`{question}` 定义变量并在运行时动态传参。
- 将系统 Prompt 和渲染后的用户 Prompt 分别传给 Agent。
- 通过 `.env` 管理模型服务地址、API Key 和模型名称。
- 预留 OpenAI、OneAPI、通义千问和 Ollama 四类模型配置。

## 重点学习内容

当前阶段只重点学习 Prompt Template：

1. **系统 Prompt 模板文件定义**：角色、能力和长期规则如何外置。
2. **用户 Prompt 模板文件定义**：本轮用户信息和问题如何组织。
3. **Prompt 模板定义变量**：`{name}`、`{question}` 如何声明动态内容。
4. **Prompt 变量动态传参**：`format_messages()` 如何填充真实数据。
5. **Agent 加载 Prompt 模板使用**：系统 Prompt 与用户 Prompt 如何进入 Agent。

模型调用、工具、记忆、结构化输出和流式响应留到后续阶段逐步拆解。

## 环境与依赖版本

当前项目已验证的环境：

| 环境或包 | 版本 | 项目中的作用 |
| --- | --- | --- |
| Python | `3.13.9` | 项目运行环境 |
| `langchain` | `1.2.1` | 创建 Agent 和组织 LangChain 应用 |
| `langchain-openai` | `1.1.6` | 接入 OpenAI 及 OpenAI 兼容模型 |
| `langgraph` | `1.0.2` | 提供 Agent 短期状态存储 |
| `concurrent-log-handler` | `0.9.28` | 日志文件轮转和并发写入 |
| `python-dotenv` | `1.0.0` | 从 `.env` 加载模型配置 |

安装命令：

```powershell
pip install langchain==1.2.1 langchain-openai==1.1.6 langgraph==1.0.2 concurrent-log-handler==0.9.28 python-dotenv==1.0.0
```

## 项目结构

```text
02_Study_PromptTemplate/
├── agent.py                         # Agent 创建和运行入口
├── .env.example                     # 模型配置示例，不包含真实 Key
├── .env                             # 本机配置，不提交
├── prompt/
│   ├── system_prompt_tmpl.md        # 系统 Prompt 模板
│   └── human_prompt_tmpl.md         # 用户 Prompt 模板和变量
├── utils/
│   ├── config.py                    # 模型类型、日志和模板路径
│   ├── llms.py                      # 加载 .env 并初始化模型
│   ├── tools.py                     # 天气 Agent 工具
│   ├── models.py                    # Context 和结构化响应模型
│   └── logger.py                    # 日志配置
└── notes/                           # 项目学习笔记
    └── ChatPromptTemplate详解.md
```

## 运行项目

1. 参考 [.env.example](<.env.example>) 配置本机 `.env`。
2. 在 `utils/config.py` 中选择 `Config.LLM_TYPE`。
3. 从当前项目目录运行：

```powershell
python agent.py
```

`.env` 已加入 `.gitignore`，不要把真实 API Key 写入代码、笔记或提交记录。

## 学习笔记

- [PromptTemplate 与 ChatPromptTemplate 使用方法](<notes/ChatPromptTemplate详解.md>)
