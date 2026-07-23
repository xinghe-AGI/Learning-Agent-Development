"""
config.py 定义统一配置类，用于集中管理项目中的路径、日志、模型和服务配置

包含：
    LOG_FILE            日志文件路径
    MAX_BYTES           单个日志文件最大字节数
    BACKUP_COUNT        日志轮转时保留的备份数量
    LLM_TYPE            默认使用的大模型类型
    BACKEND_HOST/PORT   FastAPI 后端服务地址
    WEB_HOST/PORT       Gradio WebUI 服务地址
"""

# Author:@星禾

# 导入操作系统模块，用于读取环境变量
import os
# 从 pathlib 导入 Path，用于根据当前文件稳定定位 code 目录
from pathlib import Path

# 从 python-dotenv 导入 load_dotenv，用于加载 code/.env 中的模型配置
from dotenv import load_dotenv

# 根据当前文件位置定位 code 目录，避免从不同工作目录启动时出现相对路径错误
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 加载 code/.env；项目 .env 中的同名变量会覆盖系统环境变量
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)
# # 加载 code/.env；系统中已存在的同名环境变量优先级更高
# load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)


# 定义统一配置类，用于集中管理项目中的所有常量配置
class Config:

    ######  Prompt  ######
    # 配置 Prompt 文件所在目录
    PROMPT_DIR = PROJECT_ROOT / "prompts"
    # 配置系统 Prompt 与 Human Prompt 文件路径
    SYSTEM_PROMPT_FILE = PROMPT_DIR / "system_prompt.txt"
    HUMAN_PROMPT_FILE = PROMPT_DIR / "human_prompt.txt"

    ######  LOG  ######
    # 配置日志文件所在目录
    LOG_DIR = PROJECT_ROOT / "logfile"
    # 配置日志文件路径
    LOG_FILE = LOG_DIR / "app.log"
    # 配置单个日志文件最大为 5MB；达到上限后会触发日志轮转
    MAX_BYTES = 5 * 1024 * 1024
    # 配置日志轮转时最多保留 3 个历史日志文件
    BACKUP_COUNT = 3
    # 创建日志文件所需的运行目录
    @classmethod
    def ensure_runtime_directories(cls) -> None:
        # 日志目录不存在时自动创建，确保日志写入不会因路径缺失报错
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)

    ######  ENV  ######
    # 配置 .env 文件路径
    ENV_FILE = PROJECT_ROOT / ".env"

    ######  LLM  ######
    # 配置默认大模型类型：openai、qwen、deepseek
    LLM_TYPE = os.getenv("LLM_TYPE", "qwen")

    ######  FastAPI  ######
    # 配置 FastAPI 后端服务的监听地址
    BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
    BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8012"))

    ######  Gradio  ######
    # 配置 Gradio WebUI 的监听地址
    WEB_HOST = os.getenv("WEB_HOST", "127.0.0.1")
    WEB_PORT = int(os.getenv("WEB_PORT", "7860"))
    BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
