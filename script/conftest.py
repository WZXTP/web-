"""测试脚本层的前置/后置配置（pytest fixture）。

职责：
1. 浏览器初始化（前置）与关闭（后置）：yield 之后在 finally 中关闭，
   即使用例执行过程中抛出异常也保证浏览器被回收；
2. 提供页面对象 fixture，每个用例开始前回到百度首页；
3. 用例失败自动截图，并附加到 Allure 报告。
"""

import sys
from pathlib import Path

import pytest

# 保证以项目根目录为基准导入 base / config / page / tool
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from base.exceptions import ElementOperationError, PageInterceptedError  # noqa: E402
from config.config import Config  # noqa: E402
from page.baidu_page import BaiduPage  # noqa: E402
from tool.driver import Browser  # noqa: E402
from tool.logger import get_logger  # noqa: E402

logger = get_logger("conftest")


# ---------------- 命令行参数 ----------------
def pytest_addoption(parser):
    """支持 --headed 切换到有界面模式，便于本地观察执行过程。"""
    group = parser.getgroup("ui-autotest")
    group.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="以有界面模式运行 Chrome（默认无头）",
    )


# ---------------- 浏览器 fixture ----------------
@pytest.fixture(scope="session")
def driver_session(request):
    """会话级浏览器：整个测试会话共用一个 driver，结束后统一关闭。"""
    headless = not request.config.getoption("--headed")
    driver = Browser.start(headless=headless)
    logger.info("测试会话开始，浏览器已就绪")

    try:
        yield driver
    finally:
        # 无论用例是否异常，都保证浏览器退出
        Browser.quit(driver)
        logger.info("测试会话结束，浏览器已关闭")


@pytest.fixture(scope="function")
def driver(driver_session):
    """函数级 driver：每条用例开始前清理 cookie 与缓存，避免状态串扰。"""
    try:
        driver_session.delete_all_cookies()
    except Exception as exc:
        logger.warning("清理 cookie 失败（已忽略）：%s", exc)
    yield driver_session


# ---------------- 页面对象 fixture ----------------
@pytest.fixture(scope="function")
def baidu_page(driver):
    """百度搜索页对象，每条用例前先回到首页。"""
    page = BaiduPage(driver)
    page.open_home()
    yield page


# ---------------- 失败自动截图 ----------------
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """用例执行失败时自动截图，并写入 Allure 附件。"""
    outcome = yield
    report = outcome.get_result()

    if report.when != "call" or not report.failed:
        return

    driver = item.funcargs.get("driver") or item.funcargs.get("driver_session")
    if driver is None:
        return

    try:
        path = BaiduPage(driver).screenshot(f"FAILED_{item.name}")
        report.sections.append(("失败截图", str(path)))

        import allure

        allure.attach.file(
            str(path),
            name=f"{item.name} 失败截图",
            attachment_type=allure.attachment_type.PNG,
        )
    except Exception as exc:  # 截图失败不得掩盖原始断言错误
        logger.warning("失败截图处理异常：%s", exc)


# ---------------- 异常兜底日志 ----------------
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    """把框架层异常与业务层异常在日志中区分开，便于快速定位。"""
    outcome = yield
    exc_info = outcome.excinfo
    if exc_info is None:
        return

    exc_type, exc_value = exc_info[0], exc_info[1]
    if isinstance(exc_value, PageInterceptedError):
        logger.error("用例 %s 被安全验证拦截：%s", item.name, exc_value)
    elif isinstance(exc_value, ElementOperationError):
        logger.error("用例 %s 元素操作失败：%s", item.name, exc_value)
