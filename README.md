# 百度搜索 Web 自动化测试工程

基于 **Python + Selenium + pytest + Allure + webdriver-manager** 的 Web UI 自动化测试示例工程，
采用 **base / tool / config / page / script 五层结构**，覆盖「打开百度 → 输入“软件测试” →
点击搜索 → 断言标题包含关键词 → 截图保存」的完整业务链路。

> 本工程只输出自动化测试代码，不包含任何 Web 页面或后端服务。

---

## 一、项目目录树

```
ui-autotest-demo/
├── base/                           # 公共操作层：所有页面对象的能力基类
│   ├── __init__.py
│   ├── base_page.py                # 元素定位/点击/输入/截图/窗口切换/frame 切换
│   └── exceptions.py               # 自定义异常（元素操作失败、安全验证拦截）
│
├── tool/                           # 工具层：与业务无关的基础设施
│   ├── __init__.py
│   ├── driver.py                   # 启动/退出浏览器，webdriver-manager 自动管理驱动
│   ├── json_util.py                # 读取 JSON 并转换为 dict/list
│   └── logger.py                   # logging 工具类，控制台 + 文件双输出
│
├── config/                         # 配置层
│   ├── __init__.py
│   ├── config.py                   # 项目路径、被测地址、超时、报告/截图目录
│   └── data_generator.py           # 模拟姓名、手机号、身份证号
│
├── page/                           # 页面对象层：元素定位 + 操作流程，不写断言
│   ├── __init__.py
│   └── baidu_page.py               # 百度首页 / 搜索结果页
│
├── script/                         # 测试脚本层
│   ├── __init__.py
│   ├── conftest.py                 # fixture 前后置：启动浏览器 / yield / finally 关闭
│   └── test_baidu_search.py        # 百度搜索测试脚本（test_ 开头）
│
├── data/
│   └── search_data.json            # 参数化测试数据（供 json_util 读取）
│
├── docs/
│   └── EXECUTION_RESULT.md         # 测试执行结果说明（含真实执行记录）
│
├── pytest.ini                      # testpaths=script，含 alluredir
├── requirements.txt                # 依赖清单（含 webdriver-manager）
├── README.md
└── reports/                        # 运行产物（首次运行自动创建）
    ├── screenshots/                #   截图
    ├── logs/test.log               #   运行日志
    ├── allure-results/             #   Allure 原始结果
    └── allure-report/              #   Allure HTML 报告
```

### 分层职责

| 分层 | 职责 | 约束 |
|------|------|------|
| **base** | 元素定位（单个/多个，显式等待）、点击、输入、截图、切换窗口、切换 frame、切回默认 frame | 不依赖 page/script；方法内打日志、捕获异常抛自定义异常 |
| **tool** | 启动/退出浏览器、JSON 读取转换、日志工具类 | 不依赖 page/script |
| **config** | 项目路径、被测地址、超时、数据生成 | 纯配置与工具，无副作用 |
| **page** | 元素定位器类属性 + 页面操作流程 | 不写断言，不引用 script |
| **script** | test_ 脚本、fixture 前后置、断言 | 不出现 `By` 定位，只调用 page 方法 |

依赖方向单向：`script → page → base → config/tool`。

---

## 二、环境前置条件

| 项 | 要求 | 说明 |
|----|------|------|
| Python | 3.8+（实测 3.10.18） | 建议使用虚拟环境 |
| Chrome | 已安装 Chrome / Chromium 浏览器 | 装好后无需任何驱动配置 |
| 网络 | 能访问百度；首次运行需能访问驱动下载源 | 下载一次后缓存在 `~/.wdm`，后续离线可复用 |
| Allure CLI | 生成 HTML 报告时需要 | 需先安装 Java 8+ |

> **零手动配置**：`tool/driver.py` 会自动发现本机浏览器（显式配置 → 常见安装路径 →
> PATH 命令 `google-chrome`/`chromium` → Playwright 缓存），再探测版本并按主版本号
> 交给 webdriver-manager 匹配驱动，全程不需要手动放置或指定 chromedriver。
> 装好 Chrome 后，一条 `pytest` 即可运行。

驱动获取的降级顺序（每级都会校验驱动主版本与浏览器是否一致）：

```
主版本号在线匹配 → 完整版本在线匹配 → 无参自动匹配 → ~/.wdm 本地缓存 → 系统 PATH 中的 chromedriver
```

日志会明确打印走了哪一级、驱动来源路径与版本校验结果。

安装 Allure CLI（仅生成 HTML 报告时需要）：

```bash
brew install allure                  # macOS
scoop install allure                 # Windows (Scoop)
npm install -g allure-commandline    # 通用（需 Node.js）
```

---

## 三、安装与运行

```bash
# 1. 进入工程目录
cd ui-autotest-demo

# 2. 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行全部用例（默认无头模式）
pytest

# 5. 有界面模式运行（可观察浏览器操作，本地调试推荐）
pytest --headed

# 6. 只跑冒烟用例
pytest -m smoke

# 7. 只跑核心用例
pytest script/test_baidu_search.py::TestBaiduSearch::test_search_title_contains_keyword
```

### 可选环境变量

| 变量 | 默认值 | 作用 |
|------|--------|------|
| `BASE_URL` | `https://www.baidu.com` | 被测地址 |
| `SEARCH_KEYWORD` | `软件测试` | 搜索关键词 |
| `EXPECTED_TITLE_KEYWORD` | `软件测试` | 标题断言关键词 |
| `HEADLESS` | `true` | 是否无头运行（`--headed` 优先级更高） |
| `CHROME_BINARY` | 自动探测 | Chrome/Chromium 可执行文件绝对路径 |
| `EXPLICIT_WAIT` | `15` | 元素显式等待上限（秒） |
| `PAGE_LOAD_TIMEOUT` | `30` | 页面加载超时（秒） |
| `LOG_LEVEL` | `INFO` | 日志级别 |

示例：

```bash
BASE_URL=https://www.baidu.com SEARCH_KEYWORD=自动化测试 pytest -m smoke --headed
```

---

## 四、Allure 报告

`pytest.ini` 已配置 `--alluredir=reports/allure-results --clean-alluredir`，
运行 pytest 即产出原始结果，无需额外参数。

```bash
# 生成静态 HTML 报告（可归档/分享）
allure generate reports/allure-results -o reports/allure-report --clean

# 生成并立即用本地服务打开（临时预览）
allure serve reports/allure-results
```

报告中可查看：

- `epic / feature / story / title / severity` 五类标记形成的用例层级与重要性；
- 每个 `@allure.step` 的步骤耗时与执行顺序；
- 附加的「实际页面标题」「结果统计」「输入框实际内容」文本附件；
- 成功截图与失败自动截图。

> 未安装 Allure CLI 时，`reports/allure-results/` 中的 JSON 与附件仍然有效，
> 可拷贝到任意装有 Allure 的机器生成报告。

---

## 五、设计要点

1. **驱动零手工管理**：自动发现浏览器 → 探测版本 → 按主版本号匹配驱动，
   下载后校验主版本，不匹配继续降级；离线时复用 `~/.wdm` 缓存或系统 PATH 驱动。
2. **全部显式等待**：`IMPLICIT_WAIT = 0`，隐式与显式等待叠加会导致超时时间不可控。
3. **业务语义异常**：`base/exceptions.py` 的 `ElementOperationError` 携带
   「动作 + 定位器 + 原因」，报告可直接定位问题，而不是原生堆栈。
4. **等待式结果判定**：点击搜索后页面会先停留首页再跳转，
   `wait_search_outcome()` 在一次显式等待中同时轮询「结果出现 / 被拦截」，替代 `sleep`。
5. **数据驱动**：`data/search_data.json` 由 `tool/json_util.py` 读取并直接用于
   `@pytest.mark.parametrize`，新增用例只需改数据文件。
6. **日志可追溯**：统一格式写入 `reports/logs/test.log`，每步操作都有记录，
   handler 防重复挂载。
7. **后置必执行**：conftest 的 `try/yield/finally` 保证用例异常时浏览器也会关闭。

---

## 六、常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| `cannot find Chrome binary` | 本机未安装 Chrome，或安装在非常规路径 | 安装 Chrome/Chromium 即可；自动发现未覆盖的特殊路径才需用 `CHROME_BINARY` 指定 |
| `only supports Chrome version XXX` | 驱动与浏览器主版本不一致 | 本工程下载后会校验主版本并自动降级；若残留旧缓存，清理 `~/.wdm` 后重跑 |
| 驱动下载超时 / 被网络拦截 | 无法访问驱动下载源 | ① 配置代理（`HTTPS_PROXY`）后重跑；② 依赖 `~/.wdm` 缓存复用（日志会标注「本地缓存（离线复用）」）；③ 将已有匹配版本驱动所在目录加入系统 PATH，作为最终兜底 |
| 日志显示「驱动主版本不一致，继续降级尝试」 | webdriver-manager 把主版本解析到了相邻更高版本 | 属正常降级路径，下一级会用完整版本号匹配到正确驱动，无需人工干预 |
| `PageInterceptedError`（百度安全验证） | 数据中心 IP / 自动化环境触发风控 | 在本机常规网络、`--headed` 模式复跑 |
| 元素定位超时 | 站点改版导致定位器失效 | 更新 `page/baidu_page.py` 顶部的定位器常量 |
| Allure 报告为空 | 未带 `--alluredir` 运行 | 直接 `pytest`（配置已内置该参数） |

> 本工程仅用于自动化测试技术演示，请遵守被测站点使用条款，控制执行频率。

---

## 七、执行结果

真实执行记录、通过/失败明细与原因分析见 [docs/EXECUTION_RESULT.md](docs/EXECUTION_RESULT.md)。
