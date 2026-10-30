"""自定义异常。

把 Selenium 的原生异常包装为带业务语义的异常，日志与 Allure 报告中
可以直接看出“哪一步、什么元素、什么原因”失败。
"""


class ElementOperationError(Exception):
    """元素操作失败（查找/点击/输入/截图/窗口与 frame 切换）。"""

    def __init__(self, action: str, target, reason: str):
        self.action = action
        self.target = target
        self.reason = reason
        super().__init__(f"{action}失败 | 目标：{target} | 原因：{reason}")


class PageInterceptedError(AssertionError):
    """被测站点返回安全验证/人机校验页面，业务断言无法进行。

    继承 AssertionError，使 pytest 视为用例断言失败而非框架错误。
    """
