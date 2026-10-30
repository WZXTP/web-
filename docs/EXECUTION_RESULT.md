# 测试执行结果说明

> 本文档区分两类记录，请勿混淆：
> - **A. 真实被测站点执行记录**：本机连网运行 `https://www.baidu.com` 的实际结果；
> - **B. 框架链路自检记录**：真实百度被风控拦截时，用本地同结构镜像页验证代码链路是否正确。
>
> 所有结论均来自实际命令输出，未编造通过记录。

---

## 一、执行环境

| 项 | 实际值 |
|----|--------|
| 操作系统 | Linux 5.4.258（x86_64，容器环境） |
| Python | 3.10.18 |
| pytest | 9.1.1 |
| selenium | 4.21.0 |
| webdriver-manager | 4.1.2 |
| allure-pytest | 2.16.2 |
| 浏览器 | Chromium 136.0.7103.25（自动发现，未设置 CHROME_BINARY） |
| 驱动 | chromedriver 136.0.7103.25（webdriver-manager 自动下载，缓存在 `~/.wdm`） |
| Allure CLI | 未安装（本机无 Java，未生成 HTML 页面，仅产出 `allure-results`） |
| 网络 | 可访问 `https://www.baidu.com`（HTTP 200） |

---

## 二、A. 真实被测站点执行记录

### 执行命令（零手动配置：未设置 CHROME_BINARY）

```bash
cd /workspace/ui-autotest-demo
BASE_URL=https://www.baidu.com pytest -q -k test_search_title_contains_keyword
```

> 实测前已清空 `~/.wdm` 驱动缓存（迁移旧缓存），确保是「从零自动下载」的真实路径。
> 注：本沙箱预置了 `BASE_URL=http://inner.mgx.dev`，会覆盖默认百度地址，
> 因此这里显式指定被测地址；浏览器路径无需任何配置。

### 驱动自动管理真实日志

```text
INFO  tool.driver  自动发现浏览器（Playwright 缓存）：/opt/ms-playwright/chromium-1169/chrome-linux/chrome
INFO  tool.driver  检测到浏览器主版本号：136（完整版本 136.0.7103.25）
INFO  WDM  WebDriver version 137.0.7136.0 selected
INFO  WDM  About to download new driver from .../137.0.7136.0/linux64/chromedriver-linux64.zip
INFO  WDM  Driver downloading response is 200
WARN  tool.driver  驱动来源：webdriver-manager 主版本号 136 匹配 → .../linux64/136/chromedriver-linux64/chromedriver，
                   但驱动主版本为 137，与浏览器主版本 136 不一致，继续降级尝试
INFO  WDM  WebDriver version 136.0.7103.113 selected
INFO  WDM  About to download new driver from .../136.0.7103.113/linux64/chromedriver-linux64.zip
INFO  tool.driver  驱动来源：webdriver-manager 完整版本 136.0.7103.25 匹配 → ...（主版本 136 匹配）
INFO  tool.driver  Chrome 启动成功，浏览器版本：136.0.7103.25
```

关键结论：**未设置 `CHROME_BINARY` 也能自动发现浏览器并自动下载匹配驱动**。
过程中发现一个真实问题——webdriver-manager 传主版本 `136` 时会解析到 `137` 驱动，
导致 `only supports Chrome version 137` 启动失败；已通过「下载后校验驱动主版本 → 不一致继续降级」
修复，最终由完整版本号分支拿到匹配驱动。

### 用例结果（真实，未编造）

```text
FAILED script/test_baidu_search.py::TestBaiduSearch::test_search_title_contains_keyword
base.exceptions.PageInterceptedError: 搜索请求被百度安全验证拦截（标题：百度安全验证），
通常是自动化环境/数据中心 IP 触发风控所致，请在本机常规网络与有界面 Chrome 下复跑。
失败截图：reports/screenshots/FAILED_test_search_title_contains_keyword_20261029_204725.png
```

### 失败原因（已定位根因，非代码缺陷）

浏览器、驱动、元素定位、输入、点击均正常，最终卡在站点风控：

```text
INFO  BaiduPage  打开页面：https://www.baidu.com
WARN  BaiduPage  元素不可见，已通过 JS 恢复容器显示：('id', 'form')
INFO  BaiduPage  定位到元素：('id', 'kw')
INFO  BaiduPage  执行搜索流程，关键词：软件测试
INFO  BaiduPage  输入文本至 ('id', 'kw')：软件测试
INFO  BaiduPage  点击元素：('id', 'su')
ERROR conftest   用例 ... 被安全验证拦截
INFO  tool.driver 浏览器已关闭
```

说明：

1. 浏览器与驱动均正常启动（webdriver-manager 自动匹配 136 版本驱动成功）。
2. 百度首页对自动化环境把表单容器 `#form` 置为 `display:none`，
   BasePage 的兜底逻辑已用 JS 恢复显示，`#kw` 定位、输入、`#su` 点击全部成功。
3. 点击后页面跳转至 `wappass.baidu.com` 的「百度安全验证」人机校验页，
   搜索结果未返回，因此标题断言无法成立。
4. 这是站点风控对数据中心 IP + 自动化环境的限制，**未取得真实站点通过记录**。

复跑建议（本机常规网络）：

```bash
pip install -r requirements.txt
pytest --headed
```

---

## 三、B. 框架链路自检记录

为证明代码工程本身可运行，使用本地临时镜像页（复刻 `#kw` / `#su` / `#content_left h3`
结构、跳转、iframe 与 target=_blank 新窗口，仅用于自检，不随工程交付），
通过 `BASE_URL` 切换被测地址，**运行的是同一套 base / page / script 代码，未修改业务逻辑**。

### B1. 全套用例

```bash
BASE_URL=http://127.0.0.1:8899 pytest -q
```

```text
test_search_title_contains_keyword                        PASSED
test_search_results_not_empty                             PASSED
test_keyword_echoed_in_input[主场景]                       PASSED
test_keyword_echoed_in_input[参数化场景]                   PASSED
============================== 4 passed in 2.93s ==============================
```

### B2. base 层方法自检（切换窗口 / frame / 截图）

```text
FRAME_BY_INDEX:   frame 内部元素
FRAME_BY_NAME:    frame 内部元素
FRAME_BY_ELEMENT: frame 内部元素
WINDOW_BY_LATEST_title: window_test_百度搜索
WINDOW_BY_HANDLE_title: 百度一下，你就知道
WINDOW_BY_INDEX_title:  window_test_百度搜索
SCREENSHOT: selfcheck_base_20261029_072058.png
```

证明以下链路正常：元素定位与显式等待、点击、输入、截图、
`switch_to_frame_by_index/name/element`、`switch_to_default_content`、
`switch_to_window_by_index/handle/latest`。

### B3. 工具与数据自检

```text
phone format ok: True            # 200 个样本全部匹配 1[3-9]\d{9}
id 18 digits: True               # 200 个样本均为 18 位
id checksum valid: True          # 200 个样本校验位全部通过 GB11643 算法
bad id rejected: False           # 非法身份证被正确拒绝
json rows: 2 | type: list        # json_util.load_list 读取 data/search_data.json
missing-file err OK: JSON 文件不存在：.../data/not_exist.json
bad-key err OK: JSON 中不存在 key：'nope'
```

### B4. 驱动离线兜底链实测（模拟断网）

把 `ChromeDriverManager.install()` 替换为必定抛出 `ConnectionError` 的桩，验证降级链：

```text
--- 分支1：模拟断网，应走本地缓存兜底 ---
INFO  tool.driver  驱动来源：webdriver-manager 本地缓存（离线复用） →
                   /root/.wdm/drivers/chromedriver/linux64/136.0.7103.25/chromedriver-linux64/chromedriver（主版本 136 匹配）

--- 分支2：断网 + 无缓存，应走系统 PATH 驱动兜底 ---
INFO  tool.driver  驱动来源：系统 PATH 中的 chromedriver（离线兜底） →
                   /usr/local/bin/chromedriver（主版本 136 匹配）
```

缓存复用分支另经真实调用确认（不清缓存直接再跑），日志直接命中
「本地缓存（离线复用）」，未出现 `About to download`，即**第二次运行不再重复联网下载**。

---

## 四、用例清单与预期结果

| 用例 | 断言内容 | 真实站点预期 | 自检实测 |
|------|----------|--------------|----------|
| `test_search_title_contains_keyword` | 页面标题包含「软件测试」 | 正常网络下通过 | PASSED |
| `test_search_results_not_empty` | 结果区标题条数 > 0 | 正常网络下通过 | PASSED |
| `test_keyword_echoed_in_input[主场景]` | 结果页输入框回显含关键词 | 正常网络下通过 | PASSED |
| `test_keyword_echoed_in_input[参数化场景]` | 结果页输入框回显含关键词 | 正常网络下通过 | PASSED |

> 「真实站点预期」为个人网络 + 有界面 Chrome 下的预期表现，本机未取得该记录。

---

## 五、产物说明

每次运行自动生成（已被 `.gitignore` 忽略）：

| 路径 | 内容 |
|------|------|
| `reports/allure-results/` | Allure 原始结果（JSON + png/txt 附件） |
| `reports/screenshots/` | 成功截图 `search_<关键词>_<时间戳>.png`；失败截图 `FAILED_<用例名>_<时间戳>.png` |
| `reports/logs/test.log` | 完整运行日志（驱动、元素操作、异常、断言） |

生成 HTML 报告：

```bash
allure generate reports/allure-results -o reports/allure-report --clean
allure open reports/allure-report
```

---

## 六、遗留说明

1. 本机未安装 Allure CLI 与 Java，仅验证到 `allure-results` 产出，未渲染 HTML 页面。
2. 本机无标准安装的 Chrome，`tool/driver.py` 已能自动发现容器内 Chromium 136
   （Playwright 缓存路径），**无需设置 `CHROME_BINARY`**；常规桌面环境安装 Chrome 后自动发现同样生效。
3. 真实站点执行受数据中心 IP 风控限制，需在个人网络环境复跑取得通过基线。
4. 站点改版时只需更新 `page/baidu_page.py` 的定位器常量，其余各层不变。
5. 沙箱预置 `BASE_URL=http://inner.mgx.dev`，跑真实百度需显式覆盖该变量；
   普通本机环境不设该变量时默认使用 `https://www.baidu.com`。
