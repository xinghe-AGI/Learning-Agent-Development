# Learning Agent Development

这个仓库用来沉淀 AI 应用开发、Agent 开发和 Prompt Engineering 的学习笔记、方法整理与实践材料。

当前内容分为“AI 应用开发基础概念”“Prompt Engineering”和“LangChain Agent 开发”三条学习路径。建议先理解模型、训练与生成机制，再学习提示词设计，最后进入 Agent、工具调用、结构化输出和状态管理等应用开发内容。

## 学习目录

- [project_000_基础概念](<project_000_基础概念/notes/README.md>)：AI、机器学习、神经网络、LLM、Transformer 与开发环境等基础知识。
- [project_001_Prompt Engineering](<project_001_Prompt Engineering/README.md>)：提示词工程学习笔记，包含基础概念、常见提示技术、技术对比和最佳实践。
- [project_002_LangChain-Learning](<project_002_LangChain-Learning/README.md>)：LangChain Agent 学习笔记与代码示例，包含模型接入、结构化输出、工具调用、短期记忆和 LangSmith 等内容。

## 学习路径

### AI 应用开发基础概念

这部分用于建立后续学习需要的共同底座：

- 区分 AI、AGI、机器学习、深度学习与大语言模型。
- 理解监督学习、无监督学习和强化学习的基本差异。
- 串联 Token、Transformer、自注意力、下一个 Token 预测与自回归生成。
- 准备 Python 开发环境，并认识 LangChain、LangGraph 与 LangSmith 的分工。

入口：

- [基础概念 README](<project_000_基础概念/notes/README.md>)
- [AI、AGI 与 LLM 基础知识总览](<project_000_基础概念/notes/00-AGI知识体系介绍.md>)

### Prompt Engineering

这个子项目已经整理了以下内容：

- 大语言模型设置、提示词构成要素、通用调优技巧。
- 零样本、少样本、CoT、ToT、自我一致性、Prompt Chaining、ReAct、Reflexion 等提示技术。
- 零样本与少样本、CoT 与 ToT、CoT 与 Prompt Chaining、ReAct 与 Reflexion 等技术关系对比。
- 26 条有效提示词技巧、结构化 Prompt 编写指南、Prompt 写作 Skill 项目研究。

入口：

- [Prompt Engineering README](<project_001_Prompt Engineering/README.md>)
- [Prompt Engineering 技术关系总览](<project_001_Prompt Engineering/notes/00_Prompt Engineering技术关系总览.md>)

### LangChain Agent 开发

这部分通过可运行的学习项目理解 LangChain Agent 的基本组成和调用过程：

- 区分 Chatbot、Workflow 与 Agent，理解 Agent 的动态决策和工具调用能力。
- 使用 `ChatOpenAI` 和 `init_chat_model()` 接入不同模型服务。
- 理解模型请求与响应、采样参数、消息角色和常见 API 协议。
- 学习 Schema、结构化输出、ToolStrategy、ProviderStrategy 与失败处理。
- 学习 Tools、Function Calling、`tool_call_id` 和多步工具调用链。
- 学习 `create_agent()`、短期记忆、LangSmith 跟踪和本地调用记录。
- 使用 PromptTemplate 和 ChatPromptTemplate 管理外部提示词模板。

入口：

- [LangChain Learning README](<project_002_LangChain-Learning/README.md>)
- [Agent 基本概念](<project_002_LangChain-Learning/notes/01_Agent 基本概念.md>)
- [Quickstart 代码学习项目](<project_002_LangChain-Learning/code/01_Study_Quickstart/README.md>)

## 目录说明

- `project_000_基础概念/notes/`：AI 应用开发基础概念、知识关系和配图。
- `project_001_Prompt Engineering/notes/`：学习笔记正文和配图。
- `project_002_LangChain-Learning/notes/`：Agent 基础概念与配图。
- `project_002_LangChain-Learning/code/`：LangChain 代码学习项目及其配套笔记。

## 阅读建议

初次学习可以按以下顺序进行：

1. 阅读基础概念总览，理解 AI 应用背后的模型和生成机制。
2. 完成开发环境搭建，尝试一次最小模型调用。
3. 阅读 Prompt Engineering 技术关系总览，再进入单篇技术笔记。
4. 阅读 Agent 基本概念，明确 Chatbot、Workflow 与 Agent 的边界。
5. 运行 LangChain Quickstart，再结合配套笔记理解模型、工具、结构化输出和记忆。
6. 遇到相近概念时，阅读对应的关系对比笔记，重点判断它们分别解决什么问题。
