"""base 层：页面公共操作方法。"""

from base.exceptions import ElementOperationError, PageInterceptedError
from base.base_page import BasePage

__all__ = ["BasePage", "ElementOperationError", "PageInterceptedError"]
