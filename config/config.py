"""项目配置：路径、被测地址、超时与产物目录。

所有配置集中在此处，业务代码不再出现“魔法值”。
关键项支持环境变量覆盖，便于本地调试与 CI 复用同一套代码。
"""

import os
from pathlib import Path

# ---------- 项目路径 ----------
# config/config.py -> config -> 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# ---------- 产物目录 ----------
REPORT_DIR = BASE_DIR / "reports"
SCREENSHOT_DIR = REPORT_DIR / "screenshots"
LOG_DIR = REPORT_DIR / "logs"
ALLURE_RESULTS_DIR = REPORT_DIR / "allure-results"
ALLURE_REPORT_DIR = REPORT_DIR / "allure-report"


def env_bool(name: str, default: bool = False) -> bool:
    """读取布尔型环境变量，兼容 1/true/yes/on 等写法。"""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def env_int(name: str, default: int) -> int:
    """读取整型环境变量，非法值回退默认值。"""
    value = os.getenv(name)
    if value is None or not value.strip().isdigit():
        return default
    return int(value)


class Config:
    """运行期配置常量。"""

    # ---------- 被测系统 ----------
    BASE_URL = os.getenv("BASE_URL", "https://www.baidu.com")
    KEYWORD = os.getenv("SEARCH_KEYWORD", "软件测试")
    EXPECTED_TITLE_KEYWORD = os.getenv("EXPECTED_TITLE_KEYWORD", "软件测试")

    # ---------- 浏览器 ----------
    # 无头/有界面：容器与 CI 建议 True，本地调试可用 --headed 覆盖
    HEADLESS = env_bool("HEADLESS", True)
    WINDOW_SIZE = (1440, 900)
    MAXIMIZE_WINDOW = env_bool("MAXIMIZE_WINDOW", False)
    # 容器内 Chrome 二进制不在 PATH 时，可通过该变量显式指定路径
    CHROME_BINARY = os.getenv("CHROME_BINARY", "")

    # ---------- 等待策略 ----------
    # 隐式等待固定为 0，全部使用显式等待，避免两者叠加导致超时不可控
    IMPLICIT_WAIT = 0
    EXPLICIT_WAIT = env_int("EXPLICIT_WAIT", 15)
    PAGE_LOAD_TIMEOUT = env_int("PAGE_LOAD_TIMEOUT", 30)
    POLL_FREQUENCY = 0.3

    # ---------- 日志 ----------
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = "test.log"
