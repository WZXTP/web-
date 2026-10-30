"""浏览器驱动工具类：webdriver-manager 全自动驱动管理。

无需手动配置 chromedriver，也无需手动指定 Chrome 路径：
1. 自动发现本机 Chrome/Chromium（显式配置 → 常见安装路径 → PATH → Playwright 缓存）；
2. 探测浏览器版本，优先按主版本号（如 136）交给 webdriver-manager 匹配驱动；
3. 匹配失败回退 webdriver-manager 无参自动匹配；
4. 仍失败则走离线兜底链：wdm 本地缓存 → 系统 PATH 中的 chromedriver；
5. 全部失败才抛带中文排查提示的异常。

退出浏览器时 quit 容错，避免掩盖用例真实失败原因。
"""

import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from config.config import Config
from tool.logger import get_logger

logger = get_logger(__name__)

# 驱动可执行文件名（Windows 带 .exe）
_DRIVER_NAMES = ("chromedriver.exe",) if platform.system() == "Windows" else ("chromedriver",)

# Playwright 浏览器缓存的常见根目录，用于发现其内置 Chromium
_PLAYWRIGHT_ROOTS = (
    Path("/opt/ms-playwright"),
    Path.home() / ".cache" / "ms-playwright",
    Path.home() / "Library" / "Caches" / "ms-playwright",
)


def _system_chrome_candidates() -> list:
    """各平台 Chrome/Chromium 的常见安装路径。"""
    system = platform.system()
    if system == "Darwin":
        return [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    if system == "Windows":
        return [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
    return [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/opt/google/chrome/chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
    ]


def _playwright_chrome_candidates() -> list:
    """扫描 Playwright 缓存中的 Chromium 可执行文件（按版本目录倒序）。"""
    found = []
    for root in _PLAYWRIGHT_ROOTS:
        if not root.is_dir():
            continue
        for pattern in ("chromium-*/chrome-linux/chrome", "chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium"):
            found.extend(sorted(root.glob(pattern), reverse=True))
    return [str(path) for path in found]


def resolve_chrome_binary() -> str:
    """自动发现本机 Chrome/Chromium 可执行文件。

    优先级：CHROME_BINARY 显式配置 → 各平台常见安装路径 → PATH →
    Playwright 缓存。返回空字符串表示未发现（交由 Selenium 默认逻辑处理）。
    """
    # 1. 显式配置优先（可选，非必需）
    if Config.CHROME_BINARY:
        if Path(Config.CHROME_BINARY).exists():
            logger.info("使用 CHROME_BINARY 指定的浏览器：%s", Config.CHROME_BINARY)
            return Config.CHROME_BINARY
        logger.warning("CHROME_BINARY 指向的路径不存在，继续自动发现：%s", Config.CHROME_BINARY)

    # 2. 各平台常见安装路径
    for path in _system_chrome_candidates():
        if Path(path).exists():
            logger.info("自动发现浏览器（常见安装路径）：%s", path)
            return path

    # 3. PATH 中的命令
    for name in ("google-chrome", "google-chrome-stable", "chrome", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            logger.info("自动发现浏览器（PATH 命令 %s）：%s", name, found)
            return found

    # 4. Playwright 缓存（容器常见来源）
    for path in _playwright_chrome_candidates():
        if Path(path).exists():
            logger.info("自动发现浏览器（Playwright 缓存）：%s", path)
            return path

    logger.warning("未自动发现 Chrome/Chromium，将由 Selenium 使用默认查找逻辑")
    return ""


def detect_chrome_version(binary: str) -> str:
    """读取浏览器完整版本号（如 136.0.7103.25），无法识别返回空字符串。"""
    if not binary:
        return ""
    try:
        output = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=15, check=False
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("读取浏览器版本失败：%s", exc)
        return ""

    match = re.search(r"(\d+\.\d+\.\d+\.\d+)", output or "")
    if not match:
        logger.warning("浏览器版本输出无法解析：%s", (output or "").strip()[:120])
        return ""
    return match.group(1)


def detect_major_version(binary: str) -> str:
    """提取主版本号（136.0.7103.25 → 136），用于驱动匹配。"""
    full = detect_chrome_version(binary)
    return full.split(".")[0] if full else ""


def find_cached_driver(major: str = "") -> str:
    """在 webdriver-manager 本地缓存中查找可用的 chromedriver。

    :param major: 主版本号，优先返回该版本；为空则返回最近的任意版本
    :return: 驱动路径；未找到返回空字符串
    """
    cache_root = Path.home() / ".wdm" / "drivers" / "chromedriver"
    if not cache_root.is_dir():
        return ""

    drivers = [p for p in cache_root.rglob("*") if p.is_file() and p.name in _DRIVER_NAMES]
    if not drivers:
        return ""

    if major:
        matched = [
            p for p in drivers if any(part.startswith(f"{major}.") or part == major for part in p.parts)
        ]
        if matched:
            drivers = matched

    return str(max(drivers, key=lambda p: p.stat().st_mtime))


def get_driver_major(driver_path: str) -> str:
    """读取 chromedriver 的主版本号（ChromeDriver 137.0.7136.0 → 137）。

    webdriver-manager 传主版本号时可能解析到相邻的更高版本（例如传 136 得到 137），
    因此下载后必须校验，否则会出现 "only supports Chrome version 137" 的启动失败。
    """
    if not driver_path:
        return ""
    try:
        output = subprocess.run(
            [driver_path, "--version"], capture_output=True, text=True, timeout=15, check=False
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("读取驱动的版本失败（跳过校验）：%s", exc)
        return ""

    match = re.search(r"ChromeDriver\s+(\d+)\.", output or "", re.IGNORECASE)
    return match.group(1) if match else ""


def _accept_driver(driver_path: str, expected_major: str, source: str) -> bool:
    """校验驱动主版本是否与浏览器主版本一致。

    :return: True 表示该驱动可用
    """
    if not expected_major:
        logger.info("驱动来源：%s → %s（无法校验版本，直接使用）", source, driver_path)
        return True

    driver_major = get_driver_major(driver_path)
    if driver_major == expected_major:
        logger.info("驱动来源：%s → %s（主版本 %s 匹配）", source, driver_path, driver_major)
        return True

    logger.warning(
        "驱动来源：%s → %s，但驱动主版本为 %s，与浏览器主版本 %s 不一致，继续降级尝试",
        source,
        driver_path,
        driver_major or "未知",
        expected_major,
    )
    return False


def install_driver(binary: str) -> str:
    """获取 chromedriver 路径，按「主版本匹配 → 完整版本匹配 → 无参匹配 → 本地缓存 → 系统驱动」逐级降级。

    每一级下载后都会校验驱动主版本与浏览器是否一致，避免把不兼容的驱动交给 Selenium。

    :raises RuntimeError: 所有方式都不可用
    """
    major = detect_major_version(binary)
    full_version = detect_chrome_version(binary)
    if major:
        logger.info("检测到浏览器主版本号：%s（完整版本 %s）", major, full_version)
    else:
        logger.warning("未探测到浏览器版本，跳过版本匹配，将使用无参自动匹配")

    # 1. 按主版本号在线匹配（webdriver-manager 官方推荐用法）
    if major:
        try:
            path = ChromeDriverManager(driver_version=major).install()
            if _accept_driver(path, major, f"webdriver-manager 主版本号 {major} 匹配"):
                return path
        except Exception as exc:
            logger.warning("按主版本号 %s 匹配驱动失败，继续降级：%s", major, exc)

    # 2. 按完整版本号匹配（主版本被解析到更高版本时的二次尝试）
    if full_version and full_version != major:
        try:
            path = ChromeDriverManager(driver_version=full_version).install()
            if _accept_driver(path, major, f"webdriver-manager 完整版本 {full_version} 匹配"):
                return path
        except Exception as exc:
            logger.warning("按完整版本 %s 匹配驱动失败，继续降级：%s", full_version, exc)

    # 3. 无参自动匹配（由 webdriver-manager 自行决定版本）
    try:
        path = ChromeDriverManager().install()
        if _accept_driver(path, major, "webdriver-manager 自动匹配"):
            return path
    except Exception as exc:
        logger.warning("webdriver-manager 自动匹配驱动失败，尝试离线兜底：%s", exc)

    # 4. 离线兜底：wdm 本地缓存（无网络时可复用已下载过的驱动）
    cached = find_cached_driver(major)
    if cached and _accept_driver(cached, major, "webdriver-manager 本地缓存（离线复用）"):
        return cached

    # 5. 离线兜底：系统 PATH 中的 chromedriver
    system_driver = shutil.which("chromedriver")
    if system_driver and _accept_driver(system_driver, major, "系统 PATH 中的 chromedriver（离线兜底）"):
        return system_driver

    raise RuntimeError(
        "获取 chromedriver 失败：在线下载与本地兜底均不可用或版本不匹配。"
        "排查建议：1) 确认网络可访问驱动下载源（或配置代理）；"
        "2) 检查 ~/.wdm 缓存目录读写权限；"
        "3) 若已有匹配版本驱动，可将其所在目录加入系统 PATH 作为兜底。"
        f"（浏览器路径：{binary or '未发现'}，主版本：{major or '未知'}）"
    )


def build_chrome_options() -> Options:
    """构造 Chrome 启动参数，未配置 CHROME_BINARY 时自动发现并写入 browser 路径。"""
    options = Options()

    if not Config.MAXIMIZE_WINDOW:
        options.add_argument(f"--window-size={Config.WINDOW_SIZE[0]},{Config.WINDOW_SIZE[1]}")

    options.add_argument("--lang=zh-CN")
    # 容器/CI 环境常用参数
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    # 关闭“Chrome 正受到自动测试软件控制”提示与多余日志
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    if Config.HEADLESS:
        options.add_argument("--headless=new")

    binary = resolve_chrome_binary()
    if binary:
        options.binary_location = binary
    else:
        logger.warning("未设置 browser 路径，依赖 Selenium 默认查找（可能找不到 Chrome）")

    return options


class Browser:
    """浏览器驱动工具类。"""

    @staticmethod
    def start(headless: bool = None) -> webdriver.Chrome:
        """启动 Chrome 并返回驱动实例。

        :param headless: 是否无头运行，缺省取配置值
        :raises RuntimeError: 浏览器或驱动不可用
        """
        if headless is not None and headless != Config.HEADLESS:
            # 用例侧临时覆盖时，同步到 Options 构造逻辑
            Config.HEADLESS = headless

        logger.info("开始启动 Chrome（headless=%s）", Config.HEADLESS)

        options = build_chrome_options()

        try:
            driver_path = install_driver(options.binary_location or "")
            driver = webdriver.Chrome(
                service=webdriver.ChromeService(executable_path=driver_path),
                options=options,
            )
        except (WebDriverException, OSError, ValueError, RuntimeError) as exc:
            logger.error("浏览器启动失败：%s", exc)
            raise RuntimeError(
                "Chrome 启动失败。若本机已安装 Chrome，请检查网络能否访问驱动下载源，"
                "或确认 ~/.wdm 缓存可用；也可通过 CHROME_BINARY 环境变量指定浏览器可执行文件。"
                f"（浏览器路径：{options.binary_location or '未发现'}，原始错误：{exc}）"
            ) from exc

        # 关闭隐式等待，统一使用 base 层显式等待
        driver.implicitly_wait(Config.IMPLICIT_WAIT)
        driver.set_page_load_timeout(Config.PAGE_LOAD_TIMEOUT)

        logger.info(
            "Chrome 启动成功，浏览器版本：%s", driver.capabilities.get("browserVersion")
        )
        return driver

    @staticmethod
    def quit(driver) -> None:
        """关闭浏览器并释放进程，quit 失败仅记录日志。"""
        if driver is None:
            return
        try:
            driver.quit()
            logger.info("浏览器已关闭")
        except Exception as exc:  # 关闭失败不应影响用例结果
            logger.warning("浏览器关闭异常（已忽略）：%s", exc)
