"""日志工具类：标准库 logging，控制台 + 文件双输出。

特性：
1. 同一 logger 只会挂载一次 handler，避免重复日志；
2. 统一格式与编码，日志文件落在 reports/logs/test.log；
3. 业务侧统一使用 get_logger(__name__) 获取。
"""

import logging
import sys

from config.config import LOG_DIR, Config

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)-22s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 已初始化的 logger 名，用于防重复 handler
_initialized: set = set()


def get_logger(name: str = "ui-autotest") -> logging.Logger:
    """获取带控制台与文件输出的 logger。"""
    logger = logging.getLogger(name)

    if name in _initialized:
        return logger

    logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO))
    logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # 控制台输出
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(LOG_DIR / Config.LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    _initialized.add(name)
    return logger


class Logger:
    """日志工具类封装，便于以类方式调用。"""

    @staticmethod
    def get(name: str = "ui-autotest") -> logging.Logger:
        return get_logger(name)
