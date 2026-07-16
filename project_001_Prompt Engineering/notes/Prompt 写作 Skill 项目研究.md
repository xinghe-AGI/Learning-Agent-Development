# Prompt 写作 Skill 项目研究
---
参考资料：
- [nidhinjs/prompt-master](https://github.com/nidhinjs/prompt-master)
- [yzfly/structured-prompt-skill](https://github.com/yzfly/structured-prompt-skill)
- [ckelsoe/prompt-architect](https://github.com/ckelsoe/prompt-architect)
- [Principled Instructions Are All You Need for Questioning LLaMA-1/2, GPT-3.5/4](https://arxiv.org/pdf/2312.16171)
- [[26条有效提示词技巧]]
- [[结构化 Prompt 编写指南和最佳实践]]
---

## 这几个资料分别解决什么问题？

这次研究的目标不是再收集一堆 prompt 模板，而是反过来思考：**如果要做一个真正能写 prompt 的 skill，它应该先判断什么、再选择什么、最后检查什么。**

| 资料 | 主要解决的问题 | 最值得迁移到 skill 的部分 |
|---|---|---|
| `prompt-master` | 同一个需求发给不同 AI 工具时，prompt 写法不应该一样 | 目标工具路由、9 个意图维度、最多 3 个澄清问题、token 效率审计 |
| `structured-prompt-skill` | 如何把提示词写成可复用的中文结构化模板 | 简单模式、详细模式、角色 prompt、系统 prompt、任务 prompt 的骨架 |
| `prompt-architect` | 面对不同意图时，应该选择什么提示框架 | CREATE、TRANSFORM、REASON、CRITIQUE、AGENTIC 等意图分类 |
| 26 条提示词原则论文 | 哪些通用提示原则能提升回答质量 | 受众、分隔符、少样本、正向指令、主动澄清、复杂任务拆分等原则 |
| 结构化 Prompt 笔记 | 生产级 Prompt 应该如何保证可解析、可维护、可迭代 | 统一核心骨架和 9 条硬标准 |

我的理解是：这几个资料刚好构成一个完整链路。`prompt-master` 解决“给谁写”，`prompt-architect` 解决“用什么结构写”，论文原则解决“哪些指令习惯更有效”，结构化 Prompt 解决“如何进入真实工作流”，而 `structured-prompt-skill` 提供中文模板表达方式。

## 为什么要分成五层？

如果把所有方法混在一起，很容易变成一个又长又难用的模板库。更好的方式是分层：

| 层级 | 解决的问题 | 对应资料 |
|---|---|---|
| 工具路由层 | 这个 prompt 是给哪个工具用的？ | `prompt-master` |
| 意图框架层 | 用户是要创建、改写、推理、批判，还是让 Agent 行动？ | `prompt-architect` |
| 通用原则层 | prompt 是否足够清晰、具体、有边界？ | 26 条提示词原则 |
| 结构化契约层 | 输出能否稳定解析、维护和迭代？ | 结构化 Prompt 笔记 |
| 诊断自检层 | 这段 prompt 有没有常见坏味道？ | `prompt-master` + 结构化硬标准 |

**这五层的顺序很重要：先判断目标工具，再判断任务意图，然后补充通用原则，最后才决定是否需要完整结构化契约。**  
如果一上来就套完整模板，简单任务会显得笨重；如果完全不套结构，复杂任务又容易变成一次性口头指令。

## 新 skill 的核心工作流

`ai-prompt-writer` 的工作流可以压缩成 8 步：

1. **确认目标工具**：先判断 prompt 是给 Claude、ChatGPT、Cursor、Claude Code、Midjourney、n8n 还是其他工具使用。
2. **抽取意图维度**：任务、目标工具、输入、输出格式、约束、上下文、受众、成功标准、示例。
3. **必要时澄清**：如果关键信息缺失，最多问 3 个问题。
4. **选择框架**：根据 CREATE、TRANSFORM、REASON、CRITIQUE、AGENTIC 等意图选择结构。
5. **选择通用原则**：从 26 条原则中挑最相关的几条，不机械套用。
6. **判断是否需要结构化契约**：如果是生产级、结构化输出、Agent、自动化工作流，就启用统一骨架和 9 条硬标准。
7. **生成可复制 prompt**：输出一个能直接粘贴的 prompt block。
8. **做最终自检**：检查输出形态、字段契约、成功标准、权限边界和 token 冗余。

这里的关键不是“让 skill 变得很聪明”，而是让它每次写 prompt 时都有固定判断顺序。**好的 prompt 写作不是堆技巧，而是减少模型需要猜的地方。**

## 新 skill 的文件结构

| 文件 | 作用 |
|---|---|
| `SKILL.md` | 只放触发条件、核心流程、输出格式和默认规则 |
| `references/tool-routing.md` | 按目标工具决定 prompt 写法 |
| `references/framework-selection.md` | 按任务意图选择提示框架 |
| `references/principled-instructions.md` | 沉淀 26 条提示词原则的实用版本 |
| `references/structured-templates.md` | 放简单模式、详细模式、Agent、图像、工作流模板 |
| `references/structured-prompt-contract.md` | 放统一核心骨架和 9 条硬标准 |
| `references/diagnostics.md` | 放坏 prompt 模式和最终自检清单 |

这样拆分的好处是：平时触发 skill 时只加载 `SKILL.md`，需要某一类知识时再读对应 reference。比如用户要给 Midjourney 写 prompt，就读工具路由和图像模板；用户要做 JSON 抽取，就读结构化契约；用户贴了一段烂 prompt，就读诊断清单。

## 论文 26 条原则在 skill 里的位置

26 条原则不适合变成一个固定模板，更适合变成“可选检查项”。

| 原则类别 | 在 skill 中的用法 |
|---|---|
| 提示结构与清晰度 | 帮助决定是否要加受众、分隔符、输出开头、正向指令 |
| 具体性与信息量 | 帮助决定是否要加示例、解释难度、详细程度、风格模仿 |
| 用户交互与澄清 | 帮助判断是否先问问题，而不是直接生成 |
| 内容与语言风格 | 帮助去掉礼貌废话，保留自然表达和原文风格 |
| 复杂任务与代码 Prompt | 帮助判断是否拆分任务、使用 few-shot、明确多文件处理方式 |

其中有几条要谨慎使用。比如“小费激励”和“错误后果提示”可以作为论文观察，但不适合作为默认 prompt 写法。相比之下，明确受众、写清输出格式、使用分隔符、提供示例、主动澄清需求，这些原则更稳定，也更符合真实工作流。

## 统一核心骨架和 9 条硬标准在 skill 里的位置

统一核心骨架不应该强制套到所有 prompt 上。它更适合以下场景：

- prompt 会长期复用。
- prompt 会交给团队维护。
- prompt 输出要被程序解析。
- prompt 要进入 Agent 或自动化流程。
- prompt 需要处理异常输入、缺失值、字段枚举和来源约束。

9 条硬标准则作为结构化 prompt 的验收线：

| 标准 | 在 skill 里的作用 |
|---|---|
| 简介可追踪版本变化 | 避免长期维护时不知道 prompt 改了什么 |
| 输出形态只能有一个 | 避免下游解析失败 |
| 字段契约全量闭环 | 避免字段在不同章节互相冲突 |
| 缺失值策略统一 | 避免模型用猜测值冒充事实 |
| 枚举值可校验 | 避免分类字段自由发明 |
| 字段来源约束 | 降低幻觉和伪造来源 |
| 条件 + 结果 | 让规则真正可执行 |
| 样例覆盖异常流程 | 让模型知道边界情况怎么处理 |
| 初始化短而可开工 | 让用户第一轮就知道怎么输入 |

**这部分是新 skill 的“工程化底座”。** 没有这一层，skill 可能只能写出看起来漂亮的 prompt；有了这一层，它才更适合写能进入工具链、工作流和 Agent 系统的 prompt。

## 和已有笔记的关系

- [[02_提示词构成要素]]：新 skill 里的角色、上下文、输入、输出格式都来自这些基本要素。
- [[03_设计提示词的通用技巧]]：新 skill 会把通用技巧变成生成前后的检查项。
- [[26条有效提示词技巧]]：新 skill 将 26 条原则沉淀为 `principled-instructions.md`。
- [[结构化 Prompt 编写指南和最佳实践]]：新 skill 将统一核心骨架和 9 条硬标准沉淀为 `structured-prompt-contract.md`。
- [[09_链式提示 Prompt Chaining]]：复杂任务如果不适合一个 prompt 完成，新 skill 应该建议拆成多步，而不是硬塞进一个长 prompt。
- [[10_ReAct 框架]]：Agent 类 prompt 会继承 ReAct 的“行动 + 观察 + 调整”思路，但更强调权限边界和停止条件。

## 我的理解

这个新 skill 的价值不在于“它知道很多提示词模板”，而在于它知道写 prompt 之前要先判断：

- 这个 prompt 是给哪个工具用的？
- 用户到底是要创建、改写、推理、批判，还是让 Agent 行动？
- 这个任务需要简单 prompt，还是生产级结构化 prompt？
- 输出是给人看的，还是给程序解析的？
- 哪些地方不能让模型自由发挥？

**Prompt 写作的核心不是把需求包装得更华丽，而是把目标工具、任务意图、输出契约和执行边界说清楚。**

我会把这套方法记成一句话：

**先路由工具，再判断意图；先锁输出，再补原则；能短则短，需要复用时才上结构化契约。**
