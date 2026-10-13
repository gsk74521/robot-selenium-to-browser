---
name: robot-selenium-to-browser
description: 将 Robot Framework 的 SeleniumLibrary（robotframework-selenium / Selenium2Library）测试脚本迁移转换为 Browser 库（robotframework-browser，基于 Playwright）脚本。当用户提到 robot 脚本迁移、Selenium 转 Browser、SeleniumLibrary 转 Playwright、robotframework-browser 改造、robot 自动化测试库升级、.robot/.resource 文件转换等场景时，务必使用此 skill，即使用户没有明确说出 skill 名字。
---

# SeleniumLibrary → Browser 迁移

把 SeleniumLibrary 编写的 .robot / .resource 脚本转换为 Browser 库脚本。核心原则：

1. **先脚本后人工**：`scripts/convert_robot.py` 处理机械替换（库导入、一对一关键字映射），转换不了的打 `# TODO(s2b)` 标记，再由你按 `references/migration-guide.md` 逐个处理。不要纯手工逐行改写——机械部分用脚本保证不漏、不破坏格式。
2. **保持封装架构**：用户自定义 `[Keywords]` 段的名称、参数、`[Documentation]`、调用关系一律不动，只改关键字体内的库调用。资源文件的目录结构和 import 关系保持原样。
3. **一对一优先**：能一对一映射的直接映射（见 `references/keyword-mapping.md`）；映射不了的不要硬凑，打 TODO 后按迁移指南处理。
4. **绝不覆盖原文件**：转换结果输出到新目录，并生成转换报告。

## 先决策：迁移策略（务必先和用户确认）

迁移到 Browser 有两条路线，**动手前必须让用户明确选哪条**，因为它们的工作量和最终产物完全不同：

**路线 A：源码转换（本 skill 的默认能力）**——把 .robot 里的关键字真正改成 Browser 原生写法。产物是纯 Browser 脚本，长期最干净、最能吃到 Playwright 红利（strict mode、shadow DOM 穿透、自动等待）。工作量大，需要逐关键字处理。

**路线 B：垫片库 + 渐进迁移（社区方案 [Snooz82/robotframework-browser-migration](https://github.com/Snooz82/robotframework-browser-migration)）**——`pip install robotframework-browser-migration`，把 `Library  SeleniumLibrary` 换成 `Library  SeleniumLibraryToBrowser`（它用 Browser 实现了 177 个 SeleniumLibrary 关键字中的 164 个），**脚本几乎不用改就能跑在 Playwright 上**。然后用下面的共存手法逐步替换：

```robot
*** Settings ***
Library    Browser
Library    SeleniumLibraryToBrowser    prioritize_library=SeleniumLibraryToBrowser
```

优先用垫片保证快速见效，再对热点用例复用本 skill 做源码转换，加 `Browser.` 前缀切到原生关键字；替换完把 `prioritize_library` 改成 `Browser`。

**选择建议**：代码量大、想快速止血、或关键字高度自定义 → 路线 B 起步；追求长期可维护性和 Playwright 完整能力、代码量可控 → 路线 A。混合使用（先 B 后逐步 A）通常最实际。13 个关键字垫片也实现不了（见 `references/keyword-mapping.md` 的 C 类），无论哪条路线都得手工处理。

## 工作流程

按以下顺序执行，每一步完成后再进下一步。

> 环境注意：本机 `python` 可能是 Windows 商店占位符（运行无输出、退出码 49）。运行脚本前先确认 Python 命令可用——优先用 `py` 启动器或 `python3`；不确定就用 `py --version` 探测。下面命令示例统一写 `py`。

### 0. 环境检查与适配

```bash
py <skill_dir>/scripts/check_env.py <项目目录>
```

脚本会检查：Python 版本、`robotframework-browser` 是否安装、Node.js 版本（Browser 库依赖 Playwright，必须有 Node）、`rfbrowser init` 是否执行过。缺什么就加 `--install` 自动装（会联网，先告知用户）。SeleniumLibrary 可以保留不卸载——迁移期间两库可共存，方便对照运行。

### 1. 盘点

转换前先搞清楚规模。跑盘点脚本：

```bash
py <skill_dir>/scripts/inventory.py <源目录>
```

脚本静态扫描 .robot/.resource，统计每个 SeleniumLibrary 关键字被调用了多少次、分布在多少个调用点，并按映射类型（直接映射 / 需复核 / 无法自动转换 / 垫片也不支持）分类，给出工作量估计。

除了脚本输出，还要人工确认：

- 哪些文件只调用了别人封装的关键字（不直接依赖库）？这些文件可能完全不用改。
- 是否有外部变量文件（.py/.yaml）、自定义 Python 库引用了 SeleniumLibrary 的 API（如 `BuiltIn().get_library_instance('SeleniumLibrary')`）？这类代码脚本不会碰，需要在报告中提醒用户。

把盘点结论简要告诉用户，确认转换范围（整个目录还是部分文件）。

### 2. 机械转换

```bash
py <skill_dir>/scripts/convert_robot.py <源目录> --out <输出目录> --report <报告路径>
```

脚本做的事：

- `Library  SeleniumLibrary` → `Library  Browser`，丢弃 Browser 没有的导入参数（implicit_wait、selenium_speed 等）并记 TODO
- `references/keyword-mapping.md` 中「直接映射」表内的关键字名替换，参数原样传递（两库大部分同名关键字参数顺序一致）
- 遇到「无对应/语义不同」的已知 SeleniumLibrary 关键字：保留原行，在上方插入 `# TODO(s2b): <原因>` 注释行
- 目录结构、注释、变量、自定义关键字名原样保留
- 输出 `conversion_report.md`（按文件列出 TODO 项及行号）和 `conversion_report.json`

### 3. 处理 TODO 复杂项

读转换报告，逐个文件处理 TODO。处理规则全部在 `references/migration-guide.md` 中，**动手前先读它**。常见大类：

- `Open Browser` → `New Browser` + `New Context` + `New Page`（三件套，语义完全不同）
- 等待类：Selenium 的显式等待 → Browser 的断言引擎自动等待 / `Wait For Elements State`
- locator 前缀：`id=`、`name=`、`jquery=`、`dom=` 等 Browser 不支持的策略要改写
- 弹窗：`Handle Alert` → `Handle Future Dialogs`（必须先注册再触发，顺序反转）
- frame：`Select Frame` → iframe 穿透选择器 `iframe >>> ...`
- `Execute Javascript` → `Evaluate JavaScript`（参数传递机制不同）
- `Get WebElement` 元素句柄复用 → Browser 用 selector 字符串复用

### 4. 验证

- 语法级：`py -m robot --dryrun <输出目录>` 能跑通（不依赖真实浏览器可达，主要验证库导入和关键字存在性）
- 行为级：挑 1-2 个核心用例真实运行，对比 Selenium 版本的运行结果。提醒用户：Browser 的 strict mode 会在 locator 匹配到多个元素时报错（Selenium 是静默取第一个），这类报错说明原脚本 locator 不精确，需要在报告中列出而不是擅自加 `first=`。

### 5. 交付

向用户汇报：转换文件数、一对一映射条数、人工处理 TODO 数、仍需用户决策的事项（如 strict mode 报错、implicit wait 语义丢失、WebElement 复用点）。

## 参考文件

- `references/keyword-mapping.md` — 关键字映射总表（A/B/C 分类，含 13 个连垫片也实现不了的关键字）
- `references/migration-guide.md` — 复杂场景转换规则（处理 TODO 前必读）
- `scripts/check_env.py` — 环境检查/安装
- `scripts/inventory.py` — 迁移前盘点（统计关键字用量/调用点，按难度分类，估算工作量）
- `scripts/convert_robot.py` — 机械转换（`--help` 查看参数）

映射数据的外部权威来源：[Snooz82/robotframework-browser-migration](https://github.com/Snooz82/robotframework-browser-migration)（RF 核心开发者维护）。本 skill 的 locator 映射、关键字分类、未实现清单都以它的实测实现为准——遇到本 skill 未覆盖的关键字或不确定 locator 写法时，可查该项目的 `src/SeleniumLibraryToBrowser/__init__.py`。

## 注意

- 不要把 SeleniumLibrary 的 timeout 字符串格式问题忽略掉：两库都接受 `10s`、`0:00:10` 这类 Robot 时间格式，但 Browser 默认 timeout 是 10s 而 Selenium 是 5s，迁移后等待行为可能变化，要在报告中提醒。另外 Selenium 的 Implicit Wait 会被折算成 Browser 的通用 timeout，且 Selenium Timeout 与 Implicit Wait 不会累加——这点和 Selenium 的原行为不同。
- Browser 的 locator 默认是 Playwright 引擎且自动穿透 shadow DOM 与 WebComponent；`id=` 前缀两库都支持（不要转成 `css=#foo`）；裸 xpath（`//` 开头）在 Browser 中会被当 css 解析，脚本会自动补 `xpath=` 前缀；裸 locator 按 Selenium 的 id/name 默认语义转成 `css=[id='x'], [name='x']`——这种转换会在报告里列出供复核。
- 迁移前先让用户明确选路线 A（源码转换）还是路线 B（垫片库 + 渐进迁移），两条路的产物完全不同，见开头「先决策」一节。
