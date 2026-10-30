"""百度搜索场景测试脚本。

场景：打开百度 → 输入「软件测试」→ 点击搜索 → 断言标题包含「软件测试」→ 截图。
本层只写测试步骤与断言，元素定位全部由 page 层提供。
"""

import allure
import pytest

from config.config import Config
from tool.json_util import JsonUtil

SEARCH_DATA = JsonUtil.load_list("data/search_data.json", key="search_cases")


@allure.epic("百度 Web 自动化测试")
@allure.feature("搜索功能")
class TestBaiduSearch:
    """百度搜索功能测试。"""

    @allure.story("关键词搜索")
    @allure.title("搜索「软件测试」后，页面标题应包含关键词")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_search_title_contains_keyword(self, baidu_page):
        """核心场景用例。"""
        keyword = Config.KEYWORD

        with allure.step(f"打开百度首页并搜索关键词：{keyword}"):
            baidu_page.search(keyword)

        with allure.step("等待搜索结果（若命中安全验证则直接失败并说明原因）"):
            baidu_page.wait_search_outcome()

        with allure.step(f"断言页面标题包含「{Config.EXPECTED_TITLE_KEYWORD}」"):
            title = baidu_page.title
            allure.attach(title, name="实际页面标题", attachment_type=allure.attachment_type.TEXT)
            assert Config.EXPECTED_TITLE_KEYWORD in title, (
                f"标题断言失败：期望包含「{Config.EXPECTED_TITLE_KEYWORD}」，实际标题为「{title}」"
            )

        with allure.step("保存搜索结果页截图"):
            path = baidu_page.screenshot(f"search_{keyword}")
            allure.attach.file(
                str(path), name="搜索结果页截图", attachment_type=allure.attachment_type.PNG
            )

    @allure.story("结果列表")
    @allure.title("搜索后结果列表应成功渲染")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_search_results_not_empty(self, baidu_page):
        """验证结果区不只是空壳。"""
        keyword = Config.KEYWORD

        with allure.step(f"执行搜索：{keyword}"):
            baidu_page.search(keyword)
            baidu_page.wait_search_outcome()

        with allure.step("断言结果列表非空"):
            count = baidu_page.get_result_count()
            allure.attach(
                f"结果条数：{count}", name="结果统计", attachment_type=allure.attachment_type.TEXT
            )
            assert count > 0, "搜索结果列表为空，页面可能未加载完成或结构已变更"

    @allure.story("输入框回显")
    @allure.title("搜索后结果页输入框应回显关键词：{case[keyword]}")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("case", SEARCH_DATA, ids=[c["mark"] for c in SEARCH_DATA])
    def test_keyword_echoed_in_input(self, baidu_page, case):
        """读取 JSON 数据参数化，验证结果页输入框回显。"""
        keyword = case["keyword"]

        with allure.step(f"使用 JSON 数据执行搜索：{keyword}（{case['mark']}）"):
            baidu_page.search(keyword)
            baidu_page.wait_search_outcome()

        with allure.step("断言输入框回显内容包含关键词"):
            value = baidu_page.get_input_value()
            allure.attach(
                value, name="输入框实际内容", attachment_type=allure.attachment_type.TEXT
            )
            assert keyword in value, f"输入框未正确回显，期望包含「{keyword}」，实际为「{value}」"
