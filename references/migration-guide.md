# 复杂场景迁移规则（处理 TODO(s2b) 前必读）

转换脚本留下的每个 `# TODO(s2b)` 都对应本文件中的某一节。处理时保持封装架构：只改关键字体内部，不改自定义关键字的名称、参数签名和文档。

## 目录

1. [Open Browser → 三件套](#1-open-browser--三件套)
2. [locator 语法差异](#2-locator-语法差异)
3. [等待语义与断言引擎](#3-等待语义与断言引擎)
4. [弹窗 / 对话框](#4-弹窗--对话框)
5. [frame 与 iframe](#5-frame-与-iframe)
6. [多窗口 / 多标签](#6-多窗口--多标签)
7. [Execute Javascript](#7-execute-javascript)
8. [WebElement 句柄复用](#8-webelement-句柄复用)
9. [Cookie](#9-cookie)
10. [窗口尺寸 / 最大化](#10-窗口尺寸--最大化)
11. [strict mode 问题](#11-strict-mode-问题)
12. [环境差异提醒](#12-环境差异提醒)

---

## 1. Open Browser → 三件套

Selenium 的一条 `Open Browser` 在 Browser 中对应"开浏览器进程 + 建上下文 + 开页面"三步。有两种写法：

**推荐：`New Persistent Context`（最贴近 Open Browser 语义，官方 SeleniumLibraryToBrowser 就是这么实现的）**

```robot
# Selenium
Open Browser    https://example.com    chrome    options=add_argument("--headless")

# Browser（推荐，一步到位）
New Persistent Context    url=https://example.com    browser=chromium    headless=True
```

**或拆成三件套（需要多上下文/多页面隔离时用）**

```robot
New Browser    chromium    headless=True
New Context    viewport={'width': 1920, 'height': 1080}
New Page       https://example.com
```

要点：

- `Open Browser` 与 `Create Webdriver` 是本库覆盖最弱的地方：官方实现里 `Create Webdriver` **未实现**，并明确建议用 `New Persistent Context` 替代 `Open Browser` 来获得完整功能。遇到这两个关键字，优先考虑改用 Browser 原生的 `New Persistent Context` / `New Browser`，而不是逐参数硬套。
- 浏览器名映射：`chrome`/`gc`/`googlechrome` → `chromium`（用系统装的 Chrome 可加 `channel="chrome"`）；`firefox`/`ff` → `firefox`；`edge` → `chromium` + `channel="msedge"`；`safari` → `webkit`；`headlesschrome` → `chromium` + `headless=True`。IE 无对应，必须提醒用户。
- `remote_url`（Selenium Grid）→ Browser 没有 Grid 概念，远程执行走 `Connect To Browser`（CDP/ws endpoint），架构不同，列为用户决策项。
- `options`（Chrome/FF 的参数）→ `New Persistent Context`/`New Browser` 的 `args=` 参数（如 `args=["--foo"]`）。
- Suite Setup 里开浏览器是常见模式，保持这个模式：只替换关键字体。
- 对应的 `Close All Browsers` → `Close Browser    ALL`。

## 2. locator 语法差异

前缀策略映射（按 SeleniumLibraryToBrowser 的实测实现整理，这是经过验证的换算，不是猜测）：

| Selenium 前缀 | Browser 写法 | 说明 |
|---|---|---|
| `id=foo` | `id=foo` | **保留不动**——Browser 原生支持 `id=` 策略，不需要转 css |
| `name=foo` | `css=[name=foo]` | |
| `identifier=foo` | `css=[id=foo], [name=foo]` | 匹配 id 或 name |
| `class=foo` | `css=.foo` | |
| `tag=div` | `css=div` | |
| `xpath=...` | `xpath=...` | 原样 |
| `css=...` | `css=...` | 原样 |
| `link=foo` | `css=a >> text="foo"` | 精确匹配链接文本 |
| `partial link=foo` | `css=a >> text=foo` | 无引号＝子串匹配 |
| `text=foo` | `text=foo` | Browser 原生 |
| `data=name:value` | `xpath=//*[@data-name="value"]` | Selenium 的 data 策略 |
| `element=foo` | `element=foo` | Browser 原生（如 `element=iframe`） |
| `nth=2` | `nth=2` | Browser 原生 |
| `jquery=...` / `sizzle=...` | `css=...` | 简单选择器可去前缀直接用 css；依赖 jQuery 扩展语法的需人工复核 |
| `dom=...` | **无对应** | 官方实现直接报错拒绝，必须人工改写为 css/xpath |

其他差异：

- **无前缀的裸 locator**：Selenium 按 id 或 name 解析，等价写法是 `css=[id='foo'], [name='foo']`（脚本会自动转换，并在报告中列出供复核）。注意这是逗号选择器列表，若两者都匹配会触发 Browser strict mode 报错——这属于原脚本 locator 不精确，报告里列出即可。
- Selenium 裸 `//div` 开头视为 xpath；Browser 会当 css 解析而失败。检测规则：locator 以 `/` 或 `(` 开头 → 自动补 `xpath=` 前缀（脚本已做）。
- `>>` 链式穿透：从 Selenium 的多层 `Select Frame` 或复合 locator 改写而来，SeleniumLibraryToBrowser 也用 ` >> ` 拼接列表形式的 locator，Browser 原生支持。
- Browser locator 默认穿透 shadow DOM 与 WebComponent，原来需要用 JS 才能点的元素现在可直接定位——报告里提一句即可，不用主动改。
- `iframe` 内容见第 5 节。

## 3. 等待语义与断言引擎

两库的等待哲学完全不同，这是迁移后行为差异最大的地方：

- Selenium：隐式等待（implicit_wait）+ 显式 `Wait Until ...` 关键字。
- Browser：**所有** `Get*` 断言默认自动重试直到通过或超时（assertion engine），另有 `Wait For Elements State` 做显式等待。

规则：

- `Set Selenium Implicit Wait` / `Set Browser Implicit Wait` → 删除，打 TODO 说明「Browser 自动等待，隐式等待概念不存在」。Suite Setup 里设置隐式等待的行要删掉。
- `Wait Until Element Contains    sel    text` → `Get Text    sel    contains    text`（断言引擎自动重试，等价）。脚本已自动处理这类。
- timeout 参数：Selenium 等待关键字 timeout 是位置参数，Browser 的 `Wait For Elements State` timeout 是 `timeout=10s` 命名参数，脚本转换时注意把位置参数改名。
- 原来依赖隐式等待才能通过的脚本（没有显式 Wait、直接 Click 慢加载元素）在 Browser 下通常**反而更稳**，因为 Browser 操作前自动等元素 actionable。不用为这类加等待。
- `Wait For Condition`（JS 轮询）→ `Wait For Function    js_expression`。

## 4. 弹窗 / 对话框

语义反转，最容易踩坑：Selenium 是事后处理（先触发，再 Handle Alert）；Browser 是**先注册动作，再触发**。

```robot
# Selenium
Click Element    id=delete
Handle Alert    accept

# Browser
Handle Future Dialogs    action=accept
Click    id=delete
```

- `Handle Alert    accept/dismiss/leave` → `Handle Future Dialogs    action=accept/dismiss`（leave 无对应，用 `action=dismiss` 或不注册并配 `New Context    acceptDownloads` 无关项——leave 场景极少，按 dismiss 处理并注明）。
- `Alert Should Be Present` → 注册 `Handle Future Dialogs    action=accept` 后触发；若只是验证出现，用 promise 写法：
  ```robot
  ${promise}=    Promise To    Wait For    text=...
  ```
  更简单做法：`Handle Future Dialogs` 返回值可断言。保留原意即可，别过度设计。
- `Input Text Into Alert` → `Handle Future Dialogs    action=accept    prompt_input=文字`。
- 注意注册行必须**移到触发行之前**——脚本只标 TODO，移动由你来做。

## 5. frame 与 iframe

Selenium 用 `Select Frame` 切换上下文；Browser 没有上下文切换，用穿透选择器：

```robot
# Selenium
Select Frame    id=main-frame
Click Element    id=btn
Unselect Frame

# Browser
Click    iframe[id="main-frame"] >>> css=#btn
```

- `Select Frame` + 后续 N 行操作 + `Unselect Frame`：把 frame locator 作为 `>>>` 前缀拼到区间内每个元素 locator 前面。区间内调用的是封装关键字时，给封装关键字加 frame 前缀参数或新增带前缀的 locator 变量——选改动最小的方案。
- 嵌套 frame：`iframe#a >>> iframe#b >>> css=.x`。
- 如果整个套件都在一个 frame 里操作，也可以考虑用 Browser 的 frame 语法集中定义 locator 变量，减少散落的前缀。

## 6. 多窗口 / 多标签

- Selenium 的 window handle ≈ Browser 的 page id。
- `Switch Window    title=xxx` → Browser 的 `Switch Page` 只接受 id；按 title 切：
  ```robot
  ${ids}=      Get Page Ids
  ${titles}=   Get Page Titles
  # 找到 title 对应 id 后 Switch Page
  ```
  这种组合逻辑保留在原封装关键字内部，对外签名不变。
- `Close Window` → `Close Page`（脚本已映射）。
- 新窗口打开链接的场景：Selenium 需要切 handle；Browser 可用 `Wait For New Page` 或 context 事件，遇到时按实际情况改写。

## 7. Execute Javascript

参数机制完全不同：

- Selenium：`Execute Javascript    arguments[0].click()    ${element}`——用 `arguments[N]` 占位。
- Browser：`Evaluate JavaScript    ${selector}    (e, arg) => e.click()    arg=${value}`——第一个位置参数是元素 selector，函数是箭头函数，其余参数用命名参数传。

```robot
# Selenium
${result}=    Execute Javascript    return document.title;

# Browser
${result}=    Evaluate JavaScript    ${None}    () => document.title
```

- 无元素的纯 JS：selector 传 `${None}`。
- 异步：`Execute Async Javascript` → 函数返回 Promise 即可，Browser 自动 await。
- 转换时保留原 JS 逻辑，只改包装形式；JS 里用了 `arguments[0]` 的改成命名箭头参数。

## 8. WebElement 句柄复用

Selenium 允许 `Get WebElement` 存句柄后反复操作；Browser 没有元素句柄（有 ElementHandle 但不推荐作为架构基础），惯用做法是**复用 selector 字符串**。

```robot
# Selenium
${elem}=    Get WebElement    css=.row:nth-child(2)
Click Element    ${elem}

# Browser
${sel}=    Set Variable    css=.row >> nth=2
Click    ${sel}
```

- 自定义关键字参数里接收 `${element}` 句柄的：参数名不动，语义变为 selector 字符串，文档注释里说明。这保持了封装架构不变。
- `Get WebElements` + FOR 循环逐个操作 → `Get Element Count` + 循环里用 `css=xxx >> nth=${i}`，或直接用 `Get Elements`/`Get Element By ...`。逐个评估选最简单的。

## 9. Cookie

- `Add Cookie    name    value    path=/    domain=.x.com` → Browser 的 `Add Cookie` 需要 `url` 或 `domain+path`：
  ```robot
  Add Cookie    name    value    url=https://example.com
  ```
  或 domain/path 命名参数。脚本标 TODO，人工补 url/domain。
- `Get Cookie` 返回值结构两库都是 dict 类，字段名略有差异（expiry vs expires），用到字段的地方逐个核对。

## 10. 窗口尺寸 / 最大化

- Browser 操作的是 viewport 不是 OS 窗口，headless 下无窗口概念。Playwright 无法修改真实浏览器窗口大小或位置。
- `Maximize Browser Window` → 官方实现是设为 Full HD：`Set Viewport Size    1920    1080`（这是经过验证的等价行为，比"跟随窗口"更可预测）。
- `Set Window Size    w    h` → `Set Viewport Size    w    h`（脚本已映射；注意只改 viewport 不改窗口）。
- `Set Window Position` / `Get Window Position` → 无对应（官方未实现），删除并打 TODO 说明。

## 10.5 Press Keys 按键写法

Selenium 的特殊键写法（`\13`、`ARROW_LEFT` 等）要转成 Browser 的键名。官方 Keys 枚举是本表来源：

| Selenium | Browser 键名 |
|---|---|
| `\13` / `RETURN` / `ENTER` | `Enter` |
| `\8` / `BACKSPACE` | `Backspace` |
| `\9` / `TAB` | `Tab` |
| `\27` / `ESC` / `ESCAPE` | `Escape` |
| `\32` / `SPACE` | ` `（空格） |
| `NULL` | `` 空字符串 |
| `ARROW_LEFT` / `LEFT` | `ArrowLeft` |
| `ARROW_UP` / `UP` | `ArrowUp` |
| `ARROW_RIGHT` / `RIGHT` | `ArrowRight` |
| `ARROW_DOWN` / `DOWN` | `ArrowDown` |
| `PAGE_UP` / `PAGE_DOWN` | `PageUp` / `PageDown` |
| `CONTROL` / `CTRL` | `Control` |
| `COMMAND` / `META` | `Meta` |
| `SHIFT` / `ALT` | `Shift` / `Alt` |
| `F1`–`F12` | `F1`–`F12`（同名） |

组合键：Selenium 的 `Press Keys    <sel>    CTRL+A` 在 Browser 中是 `Press Keys    <sel>    Control+A`。注意 Selenium 的按下/抬起语义与 Browser 的 `Keyboard Key` 略有差异，复杂组合键需实跑验证。

## 11. strict mode 问题

Browser 默认 strict：locator 匹配到多个元素时报错；Selenium 静默取第一个。迁移后运行报 strict 错误的处理顺序：

1. 优先精化 locator（加 `:nth-child`、文本条件、`>> nth=0` 是最后手段）。
2. 不要擅自把 strict 关掉（`Set Strict Mode    False` 是全局开关，会掩盖问题）。如用户明确要求行为与 Selenium 完全一致，再加并说明。

## 12. 环境差异提醒

转换完成后给用户的固定提醒：

- Browser 默认 timeout 10s，Selenium 默认 5s；套件行为可能因此变化。
- Browser 需要 Node.js 和 `rfbrowser init` 下载浏览器二进制；CI 镜像要相应调整（`rfbrowser init` 放 CI 缓存层）。
- SeleniumLibrary 和 Browser 可共存于同一环境，迁移期可双跑对照；全量迁移完成后再卸载 SeleniumLibrary。
- Python 侧若有 `get_library_instance('SeleniumLibrary')` 的自定义库代码，脚本未触碰，需要单独改造（Browser 实例获取方式：`BuiltIn().get_library_instance('Browser')`，但内部 API 完全不同，通常要重写）。
