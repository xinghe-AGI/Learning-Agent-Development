"""Agent 结构化输出和前后端请求体的 Pydantic 增强 Schema。"""

# Author:@星禾

# 启用延迟类型解析，支持使用 | 编写联合类型
from __future__ import annotations

# 导入 Literal，用于把套餐名限制在固定枚举中
from typing import Literal

# 导入 Pydantic 基类、配置类和字段约束工具
from pydantic import BaseModel, ConfigDict, Field


# 定义 Agent 生成套餐推荐时必须遵守的结构化响应模型
class PackageRecommendation(BaseModel):
    """客服 Agent 返回给 WebUI 的经过校验的套餐建议。"""

    # 拒绝 Schema 之外的字段，防止模型返回的额外字段被静默忽略
    model_config = ConfigDict(extra="forbid")

    # 定义展示给用户的主体回复；必须是至少包含一个字符的字符串
    reply: str = Field(
        # 描述会进入 ToolStrategy 的 JSON Schema，帮助模型理解字段用途
        description="直接给用户展示的中文回复，语气友好、自然。",
        # 限制回复不能是空字符串
        min_length=1,
    )
    # 定义可选套餐名；Literal 把取值限制为四种已定义套餐或 None
    recommended_plan: Literal[
        # 经济套餐是允许的第一个枚举值
        "经济套餐",
        # 畅游套餐是允许的第二个枚举值
        "畅游套餐",
        # 无限套餐是允许的第三个枚举值
        "无限套餐",
        # 校园套餐是允许的第四个枚举值
        "校园套餐",
    ] | None = Field(
        # 默认值为 None，表示信息不足时不强行给出套餐结论
        default=None,
        # 描述会进入 JSON Schema，说明 None 的业务含义
        description="有足够信息时给出套餐名；信息不足时为 null。",
    )
    # 定义推荐依据；必须用非空字符串说明判断理由
    recommendation_basis: str = Field(
        # 描述会进入 JSON Schema，约束模型给出可解释的推荐理由
        description="基于流量、预算或学生身份的简短推荐依据；信息不足时说明需补充的条件。",
        # 限制推荐依据不能是空字符串
        min_length=1,
    )


# 定义 Gradio WebUI 发给 FastAPI 后端的 Agent 聊天请求模型
class ChatRequest(BaseModel):
    """WebUI 调用后端的请求体。"""

    # 拒绝未定义的请求字段，明确前后端接口边界
    model_config = ConfigDict(extra="forbid")

    # 定义用户本轮输入；不能为空字符串
    message: str = Field(min_length=1, description="用户本轮输入。")
    # 定义用户标识；未传入时使用 WebUI 示例用户
    user_id: str = Field(default="webui-user", min_length=1, description="用户标识。")
    # 定义会话标识；用于隔离 Agent 的 thread_id
    conversation_id: str = Field(min_length=1, description="当前会话标识。")
    # 定义是否要求后端通过 SSE 返回 Agent 响应事件
    stream: bool = Field(default=True, description="是否使用 SSE 流式响应。")
    # 定义本次请求使用的 OpenAI-compatible 模型厂商。
    llm_type: Literal["openai", "qwen", "deepseek"] = Field(
        default="qwen",
        description="本次请求使用的模型厂商标识。",
    )
    # 定义本次请求的采样温度；未传入时使用 .env 的默认温度。
    temperature: float | None = Field(
        default=None,
        ge=0,
        le=2,
        description="本次请求的模型采样温度，范围为 0 到 2。",
    )


# 定义后端在非流式模式下返回给客户端的统一响应模型
class ChatResponse(BaseModel):
    """非流式接口的统一返回结构。"""

    # 拒绝未定义的响应字段，保持 API 返回结构稳定
    model_config = ConfigDict(extra="forbid")

    # 定义便于 UI 直接展示的文本内容；不能为空字符串
    content: str = Field(min_length=1, description="可直接展示的文本回答。")
    # 定义 Agent 返回的经过 Pydantic 校验的结构化套餐建议
    structured_response: PackageRecommendation = Field(
        description="Agent 返回的经过 Pydantic 校验的套餐建议。",
    )
