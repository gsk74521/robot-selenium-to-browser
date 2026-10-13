# SeleniumLibrary → Browser 关键字映射总表

分三类：

- **A 类（直接映射）**：参数顺序一致或高度兼容，脚本直接改名，参数原样传递。
- **B 类（映射但需人工确认）**：能映射但语义/参数有差异，脚本替换并加 `# TODO(s2b)` 注释，人工复核。
- **C 类（无对应）**：Browser 没有对应物或语义完全不同，脚本只打 TODO，按 migration-guide.md 处理。

匹配规则：不区分大小写、忽略空格和下划线（Robot 关键字标准匹配）。

> 参考基准：社区的 [SeleniumLibraryToBrowser](https://github.com/Snooz82/robotframework-browser-migration) 垫片库实现了 SeleniumLibrary 177 个关键字中的 **164 个**。本表的 A/B/C 分类与它的实现情况对齐。**下面这些是垫片也实现不了的（13 个）**，任何迁移路线都必须手工处理——它们的语义是 Playwright 架构上无法透明等价实现的：
>
> `Add Location Strategy`、`Remove Location Strategy`、`Alert Should Be Present`、`Alert Should Not Be Present`、`Handle Alert`、`Input Text Into Alert`、`Create Webdriver`、`Execute Async Javascript`、`Get Action Chain Delay`、`Set Action Chain Delay`、`Get Session Id`、`Set Browser Implicit Wait`、`Set Window Position`。
>
> 其中 `Handle Alert`/`Set Browser Implicit Wait`/`Set Window Position` 是常见关键字，迁移时优先处理。

## A 类：直接映射（脚本处理）

| SeleniumLibrary | Browser | 备注 |
|---|---|---|
| Close Browser | Close Browser | |
| Close All Browsers | Close Browser    ALL | |
| Close Window | Close Page | |
| Go To | Go To | |
| Go Back | Go Back | |
| Reload Page | Reload | |
| Get Title | Get Title | |
| Title Should Be | Get Title    == | |
| Get Location | Get Url | |
| Location Should Be | Get Url    == | |
| Location Should Contain | Get Url    contains | |
| Click Element | Click | |
| Click Button | Click | |
| Click Link | Click | |
| Click Image | Click | |
| Double Click Element | Click    <sel>    clickCount=2 | 追加参数 |
| Open Context Menu | Click    <sel>    button=right | 追加参数 |
| Mouse Over | Hover | |
| Mouse Down | Mouse Button    down | 无 selector 时用当前位置，需复核 |
| Mouse Up | Mouse Button    up | 同上 |
| Drag And Drop | Drag And Drop | |
| Drag And Drop By Offset | Drag And Drop By Coordinates | 参数含义相同 |
| Input Text | Fill Text | 两者都先清空再填入；`Input Text  sel  text  clear=False` → `Type Text  sel  text  clear=False`（追加输入用 Type Text） |
| Input Password | Fill Secret | |
| Clear Element Text | Clear Text | |
| Press Keys | Press Keys | 按键写法不同（`\\13`→`Enter`），见 B 类说明——脚本仍直接映射并标记 |
| Focus / Set Focus To Element | Focus | |
| Scroll Element Into View | Scroll To Element | |
| Select Checkbox | Check Checkbox | |
| Unselect Checkbox | Uncheck Checkbox | |
| Select Radio Button | Check Checkbox    `input[type='radio'][name='<group>'][value='<value>']` | 官方实现就是拼接出这个 css 再 Check Checkbox；脚本用模板自动拼接 |
| Checkbox Should Be Selected | Get Checkbox State    ==    True | |
| Checkbox Should Not Be Selected | Get Checkbox State    ==    False | |
| Select From List By Label | Select Options By    <sel>    label | Browser 参数为 (selector, attribute, *values)，需插一列→按 B 类对待 |
| Unselect From List By Label | Deselect Options | |
| Choose File | Upload File By Selector | |
| Get Text | Get Text | |
| Get Element Count | Get Element Count | |
| Get Value | Get Property    <sel>    value | 追加属性名 |
| Get Element Attribute | Get Property    <sel>    <attr> | 官方实现用 Get Property（参数顺序与 Selenium 相同，无需换位）；若需严格取 HTML attribute 而非 DOM property，改用 `Get Attribute  <attr>  <sel>`（注意换位） |
| Get Selected List Label | Get Selected Options    <sel>    label | |
| Get Selected List Value | Get Selected Options    <sel>    value | |
| Set Selenium Timeout | Set Browser Timeout | |
| Get Selenium Timeout | Get Timeout | |
| Sleep | Sleep | BuiltIn，不变 |
| Wait Until Keyword Succeeds | Wait Until Keyword Succeeds | BuiltIn，不变 |
| Capture Page Screenshot | Take Screenshot | filename 参数兼容 |
| Capture Element Screenshot | Take Screenshot    selector=<sel> | |
| Switch Browser | Switch Browser | Browser 用实例 id |
| Switch Window | Switch Page | 参数语义不同（title/handle vs id）→按 B 类对待 |
| Get Window Handles | Get Page Ids | |
| Get Window Titles | Get Page Titles | |
| Add Cookie | Add Cookie | 参数结构不同（dict vs 命名参数）→按 B 类对待 |
| Get Cookie | Get Cookie | |
| Get Cookies | Get Cookies | |
| Delete Cookie | Delete Cookie | |
| Delete All Cookies | Delete Cookies | |
| Set Window Size | Set Viewport Size | 语义差异：viewport 非 window，见 B 类 |
| Get Window Size | Get Viewport Size | 同上 |
| Register Keyword To Run On Failure | Register Keyword To Run On Failure | 同名 |

> 上表中「备注」注明参数变化的条目，脚本按 B 类处理：替换 + 追加/调整参数能自动做的自动做，做不了的加 TODO 注释。

## B 类：映射但需人工复核（脚本替换 + TODO 注释）

| SeleniumLibrary | Browser | 差异点 |
|---|---|---|
| Wait Until Element Is Visible | Wait For Elements State    <sel>    visible | timeout 参数名不同（Selenium 是位置参数，Browser 是 `timeout=`） |
| Wait Until Element Is Not Visible | Wait For Elements State    <sel>    hidden | 同上 |
| Wait Until Element Is Enabled | Wait For Elements State    <sel>    enabled | |
| Wait Until Element Is Disabled | Wait For Elements State    <sel>    disabled | |
| Wait Until Page Contains Element | Wait For Elements State    <sel>    attached | |
| Wait Until Page Does Not Contain Element | Wait For Elements State    <sel>    detached | |
| Wait Until Element Contains | Get Text    <sel>    contains    <text> | Browser 断言引擎自动重试，等价于等待；timeout 丢失需在报告注明 |
| Wait Until Element Does Not Contain | Get Text    <sel>    not contains    <text> | 同上 |
| Wait Until Page Contains | Get Text    body    contains    <text> | 同上；原 Selenium 默认等待 timeout 10s 行为由 Browser 默认 timeout 接管 |
| Wait Until Page Does Not Contain | Get Text    body    not contains    <text> | 同上 |
| Element Should Be Visible | Wait For Elements State    <sel>    visible | 断言变等待+断言，行为等价 |
| Element Should Not Be Visible | Wait For Elements State    <sel>    hidden | |
| Element Should Be Enabled | Wait For Elements State    <sel>    enabled | |
| Element Should Be Disabled | Wait For Elements State    <sel>    disabled | |
| Element Should Contain | Get Text    <sel>    contains | |
| Element Should Not Contain | Get Text    <sel>    not contains | |
| Element Text Should Be | Get Text    <sel>    == | |
| Element Attribute Value Should Be | Get Attribute    == | 注意参数顺序 |
| Page Should Contain | Get Text    body    contains | |
| Page Should Not Contain | Get Text    body    not contains | |
| Page Should Contain Element | Wait For Elements State    <sel>    attached | |
| Page Should Not Contain Element | Wait For Elements State    <sel>    detached | |
| Wait Until Location Is | Get Url    == | 断言引擎自动重试 |
| Wait Until Location Contains | Get Url    contains | 同上 |

## C 类：无直接对应（脚本只标 TODO，按 migration-guide.md 人工处理）

| SeleniumLibrary | 去向 |
|---|---|
| Open Browser | New Browser + New Context + New Page 三件套 |
| Maximize Browser Window | New Context 的 viewport / Set Viewport Size |
| Set Window Position / Get Window Position | 无 viewport 位置概念，通常直接删除 |
| Set Selenium Speed | New Browser 的 slowMo 参数 |
| Set Selenium Implicit Wait / Set Browser Implicit Wait | 无对应，Browser 自动等待，删除并说明 |
| Handle Alert / Alert Should Be Present / Alert Should Not Be Present / Dismiss Alert / Input Text Into Alert | Handle Future Dialogs（先注册后触发） |
| Select Frame / Unselect Frame / Current Frame Should Contain | iframe 穿透选择器 `iframe >>> css=...` |
| Execute Javascript / Execute Async Javascript | Evaluate JavaScript（箭头函数 + 参数对象） |
| Get WebElement / Get WebElements | 无元素句柄概念，改为 selector 字符串复用 |
| Wait For Condition | Wait For Function |
| Simulate Event / Simulate | Evaluate JavaScript dispatchEvent |
| Table Cell Should Contain / Get Table Cell 等 Table* 系列 | 无对应，用 css/xpath + Get Text 组合 |
| Page Should Contain Button/Link/Image/TextField/Checkbox/Radio Button | 对应 css 选择器 + Wait For Elements State |
| Set Screenshot Directory | 无全局设置，Take Screenshot 用绝对路径 |
| Add Location Strategy | 无对应（垫片也未实现），Browser 无自定义定位策略扩展点 |
| Remove Location Strategy | 无对应（垫片也未实现） |
| Create Webdriver | 无对应（垫片也未实现），改用 `New Persistent Context` 或 `New Browser`+`New Context` |
| Get Session Id | 无对应（垫片也未实现），Playwright 无 session id 概念 |
| Get Action Chain Delay | 无对应（垫片也未实现），Playwright 无动作链延迟概念，删除或改用 slowMo |
| Set Action Chain Delay | 无对应（垫片也未实现），同上 |
| Assign Id To Element | 无对应，改用其他定位方式 |
| Element Should Be Focused / Element Should Not Be Focused | Evaluate JavaScript 判断 activeElement 或 Get Element States 查 focused |
| Get Element Size / Get Element Position / Get Horizontal Position / Get Vertical Position | Get BoundingBox 取字段 |
| Submit Form | 直接 Click 提交按钮或 Press Keys Enter |
| Element Should (Not) Be Focused、Mouse Down On Image/Link、Click Element At Coordinates | 按具体情况用 Evaluate JavaScript / Click position 参数处理 |

## 不属于 SeleniumLibrary、不要动的

`BuiltIn`、`Collections`、`String`、`OperatingSystem`、`Process`、`DateTime`、`Dialogs`、`Screenshot`（独立库）等关键字不做任何替换。脚本只替换已知 SeleniumLibrary 关键字，未识别的调用原样保留。
