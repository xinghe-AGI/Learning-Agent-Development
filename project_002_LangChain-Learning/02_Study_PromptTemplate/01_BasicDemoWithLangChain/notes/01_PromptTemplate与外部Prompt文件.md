# PromptTemplate 与外部 Prompt 文件

---
参考资料：
- [PromptTemplate.from_file](https://reference.langchain.com/python/langchain-core/prompts/prompt/PromptTemplate/from_file)
---

## Prompt 在项目中的分工

项目将 Prompt 分成两个文件：`system_prompt.txt` 保存稳定的角色和套餐规则，`human_prompt.txt` 保存每轮用户问题的模板。这样可以把业务规则从 Python 代码中抽离出来，也避免把每轮变化的输入混入系统规则。

| 文件 | 内容特征 | 在代码中的使用位置 |
| --- | --- | --- |
| `code/prompts/system_prompt.txt` | 客服身份、可推荐套餐、判断规则、表达约束 | 创建 Agent 时传给 `system_prompt` |
| `code/prompts/human_prompt.txt` | 包含 `{query}` 占位符 | 每一轮调用前由 `_input()` 填充 |

## 为什么两处读取方式不同

`AgentPackageService.__init__()` 对系统 Prompt 使用 `.template`：系统提示词在 Agent 创建时作为固定字符串传入，后续不需要再次替换变量。

Human Prompt 则保留为 `self._human_prompt`。`_input(query)` 每次调用 `self._human_prompt.format(query=query)`，因此同一份模板可以针对不同用户输入重复渲染。

```python
system_prompt = PromptTemplate.from_file(
    Config.SYSTEM_PROMPT_FILE,
    encoding="utf-8",
).template

self._human_prompt = PromptTemplate.from_file(
    Config.HUMAN_PROMPT_FILE,
    encoding="utf-8",
)
```

`self._human_prompt` 的前导下划线表示实例内部使用的属性。它不是 Python 的强制私有机制，而是约定：外部调用者不应直接依赖该字段。

## 最终输入给 Agent 的形状

`_input()` 并不直接把原始 `query` 发给模型，而是先填充 Human Prompt，再包装成 LangChain 需要的 messages 结构。

```python
{
    "messages": [
        {
            "role": "user",
            "content": "<human_prompt.txt 填充后的完整文本>",
        }
    ]
}
```

系统 Prompt 由 `create_agent(..., system_prompt=...)` 单独传入，用户消息则进入 `messages`。两者职责不同：系统 Prompt 约束行为，用户消息承载本轮需求。

## 复习重点

- **系统规则与用户输入应分离。** 前者稳定，后者按轮次变化。
- **变量占位符必须与 `.format()` 参数一致。** 文件使用 `{query}` 时，代码必须传入 `query=...`。
- **Prompt 文件是运行时依赖。** 改动文件内容后通常无需修改 Python，但会直接改变 Agent 的行为。
- **不要把密钥、接口地址或用户隐私写进 Prompt 文件。** Prompt 会进入模型请求上下文。

Agent 如何接收这些 Prompt 并运行，参考 [[02_create_agent与Agent运行层]]。
