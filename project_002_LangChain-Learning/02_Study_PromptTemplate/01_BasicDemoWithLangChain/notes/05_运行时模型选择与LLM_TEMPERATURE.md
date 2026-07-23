# 运行时模型选择与 LLM_TEMPERATURE

---
参考资料：
- [LangChain Overview](https://docs.langchain.com/oss/python/langchain/overview)
- [ChatOpenAI Reference](https://reference.langchain.com/python/integrations/langchain_openai/ChatOpenAI)
---

## 多厂商接入的前提

项目用 `ChatOpenAI` 创建模型对象，因此接入的前提是厂商提供 **OpenAI-compatible 聊天接口**。`openai`、`qwen` 和 `deepseek` 在项目中不是同一个模型，而是三组不同的连接配置：`base_url`、`api_key` 和 `chat_model`。

| 页面选项 | 读取的环境变量前缀 | 额外处理 |
| --- | --- | --- |
| `openai` | `OPENAI_` | 使用 OpenAI-compatible 配置 |
| `qwen` | `QWEN_` | 传入 `enable_thinking=False`，避免思考模式与 ToolStrategy 冲突 |
| `deepseek` | `DEEPSEEK_` | 传入 `thinking={"type": "disabled"}`，避免思考模式拒绝 ToolStrategy 的 `tool_choice` |

模型工厂不会静默回退到其他厂商。用户选择 `deepseek` 但缺少 `DEEPSEEK_*` 配置时，后端返回配置错误，而不是暗中调用默认模型。这样页面选择与实际请求保持一致。

DeepSeek 的思考模式与强制工具选择存在兼容边界。该项目使用 ToolStrategy 生成结构化结果，因此在 DeepSeek 请求中关闭思考模式；如果保留思考模式，需要改用不强制 `tool_choice` 的结构化输出方案，并正确处理多轮 `reasoning_content`。

## 请求参数如何传递

WebUI 的下拉框和 Slider 会进入 `ChatRequest`：

```json
{
  "message": "我是学生，每月预算 160 元，流量要多一些",
  "user_id": "webui-user",
  "conversation_id": "<uuid>",
  "stream": true,
  "llm_type": "qwen",
  "temperature": 0.3
}
```

后端读取 `llm_type` 和 `temperature`，调用：

```python
model = get_chat_llm(llm_type, temperature)
```

模型工厂再把温度传给 `ChatOpenAI(temperature=...)`。Pydantic 将 API 接口中的温度限制为 `0` 到 `2`；如果直接调用 API 时省略 `temperature`，工厂使用 `.env` 的 `LLM_TEMPERATURE` 默认值。

## 温度参数怎样理解

`temperature` 控制采样分布的发散程度。它不是“回答质量”开关，也不能保证完全确定或完全随机。

| 温度范围 | 常见表现 | 本项目中的建议 |
| --- | --- | --- |
| `0.0–0.3` | 输出更稳定、措辞变化较少 | 结构化套餐推荐的默认起点 |
| `0.4–0.8` | 表达变化增加 | 比较不同表达风格时使用 |
| `0.9–2.0` | 随机性较高，结构化字段更可能波动 | 不适合先作为结构化输出基线 |

**先用低温度建立结构化输出基线，再逐步提高温度观察表达变化。** 即使温度为 `0`，服务端实现、模型版本、工具调用策略和上下文差异仍可能导致结果不完全一致。

## 缓存与模型设置的关系

服务层按 `(llm_type, temperature)` 缓存 Agent。相同配置复用 `ChatOpenAI`、Prompt 和 `InMemorySaver`；不同配置创建独立 Agent。这让运行时切换不需要重启服务，也保持不同实验设置的状态隔离。

相关状态细节参考 [[04_短期记忆与Agent缓存]]；`ChatOpenAI` 对象的创建职责参考 [[02_create_agent与Agent运行层]]。
