"""
llms.py 用于创建并获取 OpenAI-compatible ChatOpenAI 实例

包含：
    MODEL_CONFIGS           定义不同 LLM 类型对应的环境变量配置
    LLMInitializationError  模型初始化失败时统一抛出的异常
    _extra_body             生成厂商与 ToolStrategy 兼容的额外请求参数
    initialize_llm          按指定模型类型创建 ChatOpenAI 实例
    get_chat_llm            对外按厂商和采样温度获取聊天模型的封装函数
"""

# Author:@星禾

# 导入操作系统模块，用于读取各厂商的环境变量。
import os

# 从 langchain_openai 导入 ChatOpenAI，用于调用 OpenAI 兼容聊天模型接口。
from langchain_openai import ChatOpenAI

# 从当前包导入 Config；导入该模块时会先加载 code/.env 并提供公共配置。
from .config import Config
# 从当前包导入 LoggerManager，用于记录模型初始化结果。
from .logger import LoggerManager

# 默认 LLM 类型来自 Config；未指定时使用 .env 中的 LLM_TYPE 或 qwen
DEFAULT_LLM_TYPE = Config.LLM_TYPE
# 采样温度控制模型输出随机性；0 表示输出更稳定。
DEFAULT_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
# 请求超时以秒为单位，防止模型服务长时间无响应。
DEFAULT_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))
# 最大重试次数用于处理短暂的网络或服务端失败。
DEFAULT_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
# 获取全局日志实例，用于记录模型初始化和配置错误。
logger = LoggerManager.get_logger(__name__)

# 定义各厂商 OpenAI 兼容接口所使用的环境变量名
MODEL_CONFIGS = {
    # OpenAI 或 OpenAI-compatible 服务配置
    "openai": {
        # 读取 OpenAI 服务基础地址
        "base_url": os.getenv("OPENAI_BASE_URL"),
        # 读取 OpenAI API Key
        "api_key": os.getenv("OPENAI_API_KEY"),
        # 读取要调用的 OpenAI 聊天模型名
        "chat_model": os.getenv("OPENAI_CHAT_MODEL"),
    },
    # 阿里千问 OpenAI 兼容模式配置
    "qwen": {
        # 读取千问服务基础地址
        "base_url": os.getenv("QWEN_BASE_URL"),
        # 读取千问 API Key
        "api_key": os.getenv("QWEN_API_KEY"),
        # 读取要调用的千问聊天模型名
        "chat_model": os.getenv("QWEN_CHAT_MODEL"),
    },
    # DeepSeek OpenAI 兼容模式配置
    "deepseek": {
        # 读取 DeepSeek 服务基础地址
        "base_url": os.getenv("DEEPSEEK_BASE_URL"),
        # 读取 DeepSeek API Key
        "api_key": os.getenv("DEEPSEEK_API_KEY"),
        # 读取要调用的 DeepSeek 聊天模型名
        "chat_model": os.getenv("DEEPSEEK_CHAT_MODEL"),
    },
}


# 自定义异常类，在模型初始化失败时统一抛出
class LLMInitializationError(Exception):
    """自定义异常类，用于 LLM 初始化错误。"""


def _extra_body(llm_type: str) -> dict[str, object] | None:
    """返回指定厂商与 ToolStrategy 兼容所需的额外请求参数。"""

    # Qwen 思考模式不能强制指定工具；关闭思考模式以兼容 ToolStrategy。
    if llm_type == "qwen":
        return {"enable_thinking": False}
    # DeepSeek 思考模式会拒绝 ToolStrategy 发送的 tool_choice；显式关闭思考模式。
    if llm_type == "deepseek":
        return {"thinking": {"type": "disabled"}}
    # 其他 OpenAI-compatible 厂商不额外传递思考模式参数。
    return None


def initialize_llm(
    llm_type: str = DEFAULT_LLM_TYPE,
    temperature: float | None = None,
) -> ChatOpenAI:
    """根据模型类型读取配置并创建一个 ChatOpenAI 实例。"""

    try:
        # 统一转换为小写，避免页面或调用方传入 QWEN 这类大小写差异。
        llm_type = llm_type.strip().lower()
        # 检查传入的 llm_type 是否在预定义配置中
        if llm_type not in MODEL_CONFIGS:
            raise ValueError(
                f"不支持的 LLM 类型：{llm_type}。可用类型：{list(MODEL_CONFIGS.keys())}"
            )

        # 获取指定厂商的模型连接配置
        config = MODEL_CONFIGS[llm_type]

        # 根据厂商类型推导环境变量前缀，例如 qwen 推导为 QWEN。
        environment_prefix = llm_type.upper()
        # 逐项检查 ChatOpenAI 创建所需的关键配置。
        missing_variables = []
        # 缺少服务地址时，记录对应厂商的 BASE_URL 环境变量名。
        if not config["base_url"]:
            missing_variables.append(f"{environment_prefix}_BASE_URL")
        # 缺少访问密钥时，记录对应厂商的 API_KEY 环境变量名。
        if not config["api_key"]:
            missing_variables.append(f"{environment_prefix}_API_KEY")
        # 缺少聊天模型名时，记录对应厂商的 CHAT_MODEL 环境变量名。
        if not config["chat_model"]:
            missing_variables.append(f"{environment_prefix}_CHAT_MODEL")
        if missing_variables:
            raise ValueError(f"缺少环境变量：{', '.join(missing_variables)}")

        # 未指定温度时沿用 .env 的默认值；指定时使用本次请求的温度。
        model_temperature = DEFAULT_TEMPERATURE if temperature is None else temperature
        # WebUI 的采样温度限制在 OpenAI-compatible 接口常用的 0 到 2 范围内。
        if not 0 <= model_temperature <= 2:
            raise ValueError("temperature 必须在 0 到 2 之间")

        # 创建对话 LLM 实例
        llm_chat = ChatOpenAI(
            # 指定后端服务地址
            base_url=config["base_url"],
            # 指定访问后端的 API Key
            api_key=config["api_key"],
            # 指定使用的聊天模型名称
            model=config["chat_model"],
            # 控制模型输出的随机性
            temperature=model_temperature,
            # 设置单次调用超时时间，避免长时间阻塞
            timeout=DEFAULT_TIMEOUT,
            # 设置失败时的最大重试次数，提高稳定性
            max_retries=DEFAULT_MAX_RETRIES,
            # 按厂商补充 ToolStrategy 结构化输出所需的思考模式兼容参数。
            extra_body=_extra_body(llm_type),
        )

        # 记录成功初始化的模型类型
        logger.info(
            "成功初始化 %s ChatOpenAI，temperature=%s",
            llm_type,
            model_temperature,
        )
        # 返回对话模型实例
        return llm_chat

    except ValueError as error:
        # 记录模型配置错误并包装为项目统一异常
        logger.error("LLM 配置错误：%s", error)
        raise LLMInitializationError(f"LLM 配置错误：{error}") from error
    except Exception as error:
        # 记录其他初始化失败原因
        logger.error("初始化 LLM 失败：%s", error)
        raise LLMInitializationError(f"初始化 LLM 失败：{error}") from error


def get_chat_llm(
    llm_type: str = DEFAULT_LLM_TYPE,
    temperature: float | None = None,
) -> ChatOpenAI:
    """按指定厂商和采样温度获取 ChatOpenAI 实例。"""

    # 不静默回退到其他厂商，避免页面显示的选择与实际调用模型不一致。
    return initialize_llm(llm_type, temperature)
