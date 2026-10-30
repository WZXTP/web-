"""百度搜索页页面对象。

约定：本层只做元素定位与操作流程，不写任何断言。
"""

from selenium.webdriver.common.by import By

from base.base_page import BasePage
from base.exceptions import PageInterceptedError
from config.config import Config


class BaiduPage(BasePage):
    """百度首页与搜索结果页。"""

    # ---------- 页面元素定位 ----------
    SEARCH_INPUT = (By.ID, "kw")
    SEARCH_BUTTON = (By.ID, "su")
    RESULT_CONTAINER = (By.CSS_SELECTOR, "#content_left")
    RESULT_TITLES = (By.CSS_SELECTOR, "#content_left h3")

    # 百度对自动化环境会把表单容器置为 display:none，交由 BasePage 兜底恢复
    VISIBILITY_CONTAINER = (By.ID, "form")

    # 安全验证页特征
    INTERCEPT_TITLE_KEYWORD = "安全验证"
    INTERCEPT_URL_KEYWORD = "wappass.baidu.com"

    # ---------- 页面操作流程 ----------
    def open_home(self) -> "BaiduPage":
        """打开百度首页并等待搜索框出现。"""
        self.open(Config.BASE_URL)
        self.find_element(self.SEARCH_INPUT)
        return self

    def input_keyword(self, keyword: str) -> "BaiduPage":
        """在搜索框输入关键词。"""
        self.input_text(self.SEARCH_INPUT, keyword)
        return self

    def click_search(self) -> "BaiduPage":
        """点击“百度一下”按钮。"""
        self.click(self.SEARCH_BUTTON)
        return self

    def search(self, keyword: str) -> "BaiduPage":
        """输入关键词并点击搜索（组合流程）。"""
        self.logger.info("执行搜索流程，关键词：%s", keyword)
        self.input_keyword(keyword)
        self.click_search()
        return self

    def wait_search_outcome(self, timeout: int = None) -> "BaiduPage":
        """等待搜索结果出现，或等待安全验证页接管。

        点击后页面会先短暂停留首页标题再跳转，因此用一次显式等待同时轮询两种状态，
        避免基于 sleep 的竞态误判。

        :raises PageInterceptedError: 页面被安全验证拦截
        """
        timeout = timeout or self.timeout

        def _ready(_driver) -> str:
            if len(self.driver.find_elements(*self.RESULT_TITLES)) > 0:
                return "results"
            if self.is_intercepted():
                return "intercepted"
            return ""

        try:
            outcome = self._make_wait(timeout).until(_ready)
        except Exception:
            raise AssertionError(
                f"等待搜索结果超时（{timeout}s）：标题「{self.title}」，地址 {self.current_url}"
            ) from None

        if outcome == "intercepted":
            self.raise_if_intercepted()

        self.logger.info("搜索结果已加载，标题：%s", self.title)
        return self

    def is_intercepted(self) -> bool:
        """当前页面是否已被安全验证拦截。"""
        return (
            self.INTERCEPT_TITLE_KEYWORD in (self.title or "")
            or self.INTERCEPT_URL_KEYWORD in (self.current_url or "")
        )

    def raise_if_intercepted(self) -> None:
        """命中安全验证时抛出带业务说明的异常。"""
        if self.is_intercepted():
            raise PageInterceptedError(
                f"搜索请求被百度安全验证拦截（标题：{self.title}），"
                "通常是自动化环境/数据中心 IP 触发风控所致，请在本机常规网络与有界面 Chrome 下复跑。"
            )

    def get_result_count(self) -> int:
        """当前结果页的标题条数。"""
        return len(self.find_elements(self.RESULT_TITLES))

    def get_input_value(self) -> str:
        """结果页搜索框的回显内容。"""
        return self.get_attribute(self.SEARCH_INPUT, "value") or ""
