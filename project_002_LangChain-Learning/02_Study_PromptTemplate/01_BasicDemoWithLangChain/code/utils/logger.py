"""
logger.py 定义日志管理器类，用于集中管理日志配置和提供统一获取接口。

包含：
    LoggerManager  使用单例模式创建并复用日志记录器
    get_logger     保留函数式入口，便于业务代码按模块名获取日志器
"""

# Author:@星禾

# 导入标准库 logging，用于配置和输出日志信息。
import logging

# 从第三方库导入并发安全的轮转日志处理器，避免多进程写日志冲突。
from concurrent_log_handler import ConcurrentRotatingFileHandler

# 从当前包导入 Config，用于获取日志文件路径、大小和备份数量。
from .config import Config


# 定义日志管理器类，提供统一的日志配置和获取接口
class LoggerManager:
    """日志管理器类，提供统一的日志配置和获取接口。"""

    # 类级别单例实例，确保全局只创建一个日志管理器
    _instance = None
    # 缓存按名称创建的 logging.Logger，避免重复添加 Handler
    _loggers: dict[str, logging.Logger] = {}

    def __new__(cls):
        """单例模式，确保全局只有一个日志管理器。"""

        # 尚未创建实例时才调用父类创建新实例
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        # 返回已有或新创建的实例
        return cls._instance

    def _setup_logger(self, name: str) -> logging.Logger:
        """按模块名创建一个文件轮转日志器。"""

        # 确保日志目录已存在
        Config.ensure_runtime_directories()
        # 获取指定模块名对应的日志记录器
        logger = logging.getLogger(name)
        # 设置日志级别为 INFO，记录应用运行和错误信息
        logger.setLevel(logging.INFO)
        # 防止日志向 root logger 重复传播
        logger.propagate = False

        # 若该日志器已经配置过处理器，直接复用
        if logger.handlers:
            return logger

        # 创建支持并发写入且按大小滚动切分的日志处理器
        handler = ConcurrentRotatingFileHandler(
            # 指定日志文件路径
            Config.LOG_FILE,
            # 单个文件达到最大字节数后自动轮转
            maxBytes=Config.MAX_BYTES,
            # 最多保留的历史日志文件数量
            backupCount=Config.BACKUP_COUNT,
            # 指定 UTF-8 编码，确保中文日志正常显示
            encoding="utf-8",
        )
        # 设置日志输出格式：时间、模块、等级和消息
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        # 将处理器添加到当前模块日志器
        logger.addHandler(handler)
        return logger

    @classmethod
    def get_logger(cls, name: str = __name__) -> logging.Logger:
        """按模块名获取日志记录器；同名日志器只初始化一次。"""

        # 获取日志管理器单例
        instance = cls()
        # 已缓存时直接返回
        if name in cls._loggers:
            return cls._loggers[name]
        # 首次使用该名称时完成配置并缓存
        cls._loggers[name] = instance._setup_logger(name)
        return cls._loggers[name]


def get_logger(name: str) -> logging.Logger:
    """保留函数式调用方式，兼容现有业务代码。"""

    # 统一委托给 LoggerManager，避免出现两套日志初始化逻辑
    return LoggerManager.get_logger(name)
