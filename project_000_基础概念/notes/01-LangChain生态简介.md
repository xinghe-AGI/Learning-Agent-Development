# LangChain 生态简介

参考资料：

- [LangChain overview](https://docs.langchain.com/oss/python/langchain/overview)
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangSmith documentation](https://docs.langchain.com/langsmith/home)

LangChain 生态常见的三个名字分别解决不同层级的问题：**LangChain 提供较高层的 Agent 与模型集成，LangGraph 提供有状态工作流与运行时，LangSmith 提供追踪、评估和部署相关能力。**

## 三个组件的定位

| 组件 | 核心定位 | 适合解决的问题 |
| --- | --- | --- |
| LangChain | LLM/Agent 应用框架 | 统一模型与工具接口，快速构建常见 Agent 循环 |
| LangGraph | 低层 Agent 编排框架与运行时 | 状态、循环、持久化、人工介入、长时间运行 |
| LangSmith | LLM 应用平台 | Tracing、评估、Prompt 管理、监控与部署 |

![LangChain、LangGraph 与 LangSmith 的关系](<pictures/foundation-05-langchain-ecosystem.png>)

## LangChain

LangChain 适合快速接入模型、工具和 Agent。常见能力包括：

- 模型与消息接口。
- 工具定义与调用。
- Agent 构建。
- 文档加载、检索与 RAG 集成。
- 与 LangSmith 的追踪和评估集成。

当前 LangChain 的 Agent 抽象建立在 LangGraph 能力之上，适合从预构建架构开始；当需要精确控制状态和执行路径时，再直接使用 LangGraph。

## LangGraph

LangGraph 是低层编排框架，重点不是包装 Prompt，而是控制执行：

- **Durable execution**：失败后从检查点恢复。
- **Stateful workflow**：节点之间显式传递状态。
- **Human-in-the-loop**：执行中暂停、检查或修改状态。
- **Memory**：管理短期与长期状态。
- **Streaming**：持续输出节点事件和中间结果。

**LangGraph 可以独立使用，不要求必须使用 LangChain。** 把它称为 LangChain 的“超集”会误导两者关系。

## LangSmith

LangSmith 用于观察和改进 LLM 应用：

| 能力 | 作用 |
| --- | --- |
| Tracing | 记录模型调用、工具调用、状态变化和耗时 |
| Offline Evaluation | 用固定数据集比较 Prompt、模型或工作流版本 |
| Online Evaluation | 在生产流量中抽样评估质量和风险 |
| Monitoring | 观察错误率、延迟、成本和反馈趋势 |
| Prompt 管理 | 保存、测试和协作维护 Prompt 版本 |

LangSmith 可以追踪 LangChain/LangGraph 应用，也支持其他框架或手动埋点。

## 如何选择？

| 当前需求 | 建议起点 |
| --- | --- |
| 只调用一次模型 | 模型官方 SDK，未必需要 LangChain |
| 快速构建带工具的 Agent | LangChain |
| 明确控制状态、循环、恢复和人工审批 | LangGraph |
| 需要追踪、数据集评估和生产监控 | LangSmith |

它们可以组合使用，但不是每个项目都必须全套安装。

## 最小安装

LangChain 当前要求 Python 3.10 或更高版本。集成包按模型提供商独立安装：

```powershell
python -m pip install -U langchain langgraph
python -m pip install -U langchain-openai
```

如果使用其他模型提供商，应安装对应集成包，而不是无条件安装 `langchain-openai`。

## 最小模型调用示例

```python
from langchain_openai import ChatOpenAI

# 把模型名和 API 凭据放在环境配置中，不要写死在仓库。
model = ChatOpenAI(model="你的模型名称")
response = model.invoke("用一句话解释什么是机器学习")

print(response.content)
```

这个示例只说明调用形态。真实项目还需要超时、重试、日志、费用控制和评估。

## 相关笔记

- [开发环境的搭建](<02-开发环境的搭建.md>)
- [conda 常用命令](<conda命令.md>)
- [LLM](<LLM.md>)
- [Prompt](<Prompt.md>)
