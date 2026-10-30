"""BasePage：所有页面对象的公共操作基类。

提供：元素定位（单个/多个，显式等待）、点击、输入、截图、
切换窗口（index / handle）、切换 frame（index / name / element）、
切换回默认 frame。

设计约定：
1. 全部使用显式等待（隐式等待为 0），等待上限取 config.Config.EXPLICIT_WAIT；
2. 每个操作打印步骤日志，成功与失败都可追溯；
3. 捕获 Selenium 异常，统一抛出 ElementOperationError，附明确原因。
"""

from datetime import datetime
from pathlib import Path

from selenium.common.exceptions import (
    NoSuchFrameException,
    NoSuchWindowException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from base.exceptions import ElementOperationError
from config.config import SCREENSHOT_DIR, Config
from tool.logger import get_logger


class BasePage:
    """页面对象基类。"""

    # 兜底容器：部分站点会对自动化环境把表单容器置为 display:none，
    # 子类可按需覆盖为 (By.X, "value")，元素不可见时用 JS 恢复显示。
    VISIBILITY_CONTAINER = None

    def __init__(self, driver):
        self.driver = driver
        self.timeout = Config.EXPLICIT_WAIT
        self.wait = WebDriverWait(driver, self.timeout, poll_frequency=Config.POLL_FREQUENCY)
        self.logger = get_logger(self.__class__.__name__)

    # ==================== 显式等待 ====================
    def _make_wait(self, timeout: int = None) -> WebDriverWait:
        """生成显式等待对象；timeout 缺省使用全局配置。"""
        if timeout is None or timeout == self.timeout:
            return self.wait
        return WebDriverWait(self.driver, timeout, poll_frequency=Config.POLL_FREQUENCY)

    def wait_until_visible(self, locator, timeout: int = None) -> WebElement:
        """等待元素出现且可见，返回元素。"""
        try:
            return self._visibility_wait(locator, timeout)
        except TimeoutException:
            # 首次超时后尝试恢复兜底容器，再重试一次
            if not self._restore_container_visibility():
                raise ElementOperationError(
                    "等待元素可见", locator, f"超时 {timeout or self.timeout}s 仍未出现可见元素"
                ) from None
            try:
                return self._visibility_wait(locator, timeout)
            except TimeoutException:
                raise ElementOperationError(
                    "等待元素可见", locator, f"恢复容器显示后仍不可见（超时 {timeout or self.timeout}s）"
                ) from None

    def _visibility_wait(self, locator, timeout: int = None) -> WebElement:
        self.logger.debug("等待元素可见：%s", locator)
        return self._make_wait(timeout).until(EC.visibility_of_element_located(locator))

    def wait_until_clickable(self, locator, timeout: int = None) -> WebElement:
        """等待元素可点击，返回元素。"""
        try:
            self.logger.debug("等待元素可点击：%s", locator)
            return self._make_wait(timeout).until(EC.element_to_be_clickable(locator))
        except TimeoutException:
            raise ElementOperationError(
                "等待元素可点击", locator, f"超时 {timeout or self.timeout}s 元素仍不可点击"
            ) from None

    def wait_until_present(self, locator, timeout: int = None) -> WebElement:
        """等待元素出现在 DOM 中（不要求可见）。"""
        try:
            return self._make_wait(timeout).until(EC.presence_of_element_located(locator))
        except TimeoutException:
            raise ElementOperationError(
                "等待元素出现", locator, f"超时 {timeout or self.timeout}s 元素未出现在 DOM 中"
            ) from None

    def wait_until_invisible(self, locator, timeout: int = None) -> bool:
        """等待元素从页面消失，返回是否成功（不抛异常）。"""
        try:
            return bool(
                self._make_wait(timeout).until(EC.invisibility_of_element_located(locator))
            )
        except TimeoutException:
            self.logger.warning("元素在 %ss 内未消失：%s", timeout or self.timeout, locator)
            return False

    # ==================== 元素定位 ====================
    def find_element(self, locator, timeout: int = None) -> WebElement:
        """查找单个元素（带显式等待，元素需可见）。"""
        element = self.wait_until_visible(locator, timeout)
        self.logger.info("定位到元素：%s", locator)
        return element

    def find_elements(self, locator, timeout: int = None) -> list:
        """查找多个元素，返回列表（允许为空）。"""
        try:
            elements = self._make_wait(timeout).until(
                EC.presence_of_all_elements_located(locator)
            )
        except TimeoutException:
            self.logger.warning("多个元素定位超时，返回空列表：%s", locator)
            return []
        self.logger.info("定位到 %s 个元素：%s", len(elements), locator)
        return elements

    # ==================== 元素操作 ====================
    def click(self, locator, timeout: int = None) -> "BasePage":
        """点击元素（先等可点击）。"""
        element = self.wait_until_clickable(locator, timeout)
        try:
            element.click()
        except (WebDriverException, StaleElementReferenceException) as exc:
            raise ElementOperationError("点击元素", locator, str(exc)) from exc
        self.logger.info("点击元素：%s", locator)
        return self

    def input_text(self, locator, text: str, timeout: int = None, clear: bool = True) -> "BasePage":
        """向输入框输入文本。"""
        element = self.wait_until_visible(locator, timeout)
        try:
            if clear:
                element.clear()
            element.send_keys(text)
        except WebDriverException as exc:
            raise ElementOperationError("输入文本", locator, str(exc)) from exc
        self.logger.info("输入文本至 %s：%s", locator, text)
        return self

    def get_text(self, locator, timeout: int = None) -> str:
        """获取元素可见文本（去首尾空白）。"""
        text = self.wait_until_visible(locator, timeout).text.strip()
        self.logger.info("获取文本 %s：%s", locator, text)
        return text

    def get_attribute(self, locator, attribute: str, timeout: int = None) -> str:
        """获取元素属性值，例如输入框回显用 value。"""
        value = self.wait_until_visible(locator, timeout).get_attribute(attribute)
        self.logger.info("获取属性 %s[%s]：%s", locator, attribute, value)
        return value

    def is_visible(self, locator, timeout: int = 5) -> bool:
        """判断元素是否可见，不抛异常。"""
        try:
            return self.wait_until_visible(locator, timeout).is_displayed()
        except ElementOperationError:
            return False

    def execute_script(self, script: str, *args):
        """执行 JS 脚本。"""
        return self.driver.execute_script(script, *args)

    # ==================== 截图 ====================
    def screenshot(self, name: str = "screenshot") -> Path:
        """截图并返回文件路径，文件落在 reports/screenshots。"""
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name).strip("_")
        path = SCREENSHOT_DIR / f"{safe_name or 'screenshot'}_{datetime.now():%Y%m%d_%H%M%S}.png"
        try:
            if not self.driver.save_screenshot(str(path)):
                raise ElementOperationError("截图", name, "save_screenshot 返回 False")
        except WebDriverException as exc:
            raise ElementOperationError("截图", name, str(exc)) from exc
        self.logger.info("截图已保存：%s", path)
        return path

    # ==================== 切换窗口 ====================
    def switch_to_window_by_index(self, index: int = -1) -> "BasePage":
        """按索引切换窗口，-1 表示最新打开的窗口。"""
        handles = self.driver.window_handles
        if not handles:
            raise ElementOperationError("切换窗口", f"index={index}", "当前没有任何窗口句柄")
        try:
            handle = handles[index]
        except IndexError:
            raise ElementOperationError(
                "切换窗口", f"index={index}", f"索引越界，当前共 {len(handles)} 个窗口"
            ) from None
        return self.switch_to_window_by_handle(handle)

    def switch_to_window_by_handle(self, handle: str) -> "BasePage":
        """按窗口句柄切换窗口。"""
        if handle not in self.driver.window_handles:
            raise ElementOperationError("切换窗口", handle, "窗口句柄不存在或已关闭")
        try:
            self.driver.switch_to.window(handle)
        except NoSuchWindowException as exc:
            raise ElementOperationError("切换窗口", handle, str(exc)) from exc
        self.logger.info("已切换到窗口：%s（标题：%s）", handle[-8:], self.driver.title)
        return self

    def switch_to_latest_window(self) -> "BasePage":
        """切换到最新打开的窗口。"""
        return self.switch_to_window_by_index(-1)

    # ==================== 切换 frame ====================
    def switch_to_frame_by_index(self, index: int = 0) -> "BasePage":
        """按索引切入 iframe。"""
        try:
            self.driver.switch_to.frame(index)
        except (NoSuchFrameException, WebDriverException) as exc:
            raise ElementOperationError("切换 frame", f"index={index}", str(exc)) from exc
        self.logger.info("已切换到 frame：index=%s", index)
        return self

    def switch_to_frame_by_name(self, name: str) -> "BasePage":
        """按 name / id 切入 iframe。"""
        try:
            self.driver.switch_to.frame(name)
        except (NoSuchFrameException, WebDriverException) as exc:
            raise ElementOperationError("切换 frame", f"name={name}", str(exc)) from exc
        self.logger.info("已切换到 frame：name=%s", name)
        return self

    def switch_to_frame_by_element(self, locator) -> "BasePage":
        """按 iframe 元素切入。"""
        frame = self.wait_until_present(locator)
        try:
            self.driver.switch_to.frame(frame)
        except (NoSuchFrameException, WebDriverException) as exc:
            raise ElementOperationError("切换 frame", locator, str(exc)) from exc
        self.logger.info("已切换到 frame 元素：%s", locator)
        return self

    def switch_to_default_content(self) -> "BasePage":
        """切回主文档（退出所有 iframe）。"""
        try:
            self.driver.switch_to.default_content()
        except WebDriverException as exc:
            raise ElementOperationError("切换回默认 frame", "default_content", str(exc)) from exc
        self.logger.info("已切回默认 frame")
        return self

    # ==================== 浏览器基础信息 ====================
    def open(self, url: str) -> "BasePage":
        """打开指定地址。"""
        self.logger.info("打开页面：%s", url)
        try:
            self.driver.get(url)
        except WebDriverException as exc:
            raise ElementOperationError("打开页面", url, str(exc)) from exc
        return self

    @property
    def title(self) -> str:
        """当前页面标题。"""
        return self.driver.title

    @property
    def current_url(self) -> str:
        """当前页面地址。"""
        return self.driver.current_url

    # ==================== 内部工具 ====================
    def _restore_container_visibility(self) -> bool:
        """元素不可见时，用 JS 强制恢复兜底容器的显示状态。"""
        if not self.VISIBILITY_CONTAINER:
            return False

        elements = self.driver.find_elements(*self.VISIBILITY_CONTAINER)
        if not elements:
            return False

        self.driver.execute_script(
            "arguments[0].style.display='block';"
            "arguments[0].style.visibility='visible';"
            "arguments[0].style.opacity='1';",
            elements[0],
        )
        self.logger.warning(
            "元素不可见，已通过 JS 恢复容器显示：%s（站点可能存在自动化环境适配）",
            self.VISIBILITY_CONTAINER,
        )
        return True
