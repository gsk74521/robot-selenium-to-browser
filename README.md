# robot-selenium-to-browser

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Robot Framework](https://img.shields.io/badge/Robot%20Framework-SeleniumLibrary%20%E2%86%92%20Browser-blue)](https://robotframework-browser.org/)

一个把 **SeleniumLibrary** 写的 Robot Framework 脚本迁移到 **Browser**（Playwright）库的 Claude Code skill。

A Claude Code skill that migrates Robot Framework scripts from **SeleniumLibrary** to the **Browser** (Playwright) library.

---

## 中文

### 这是什么

一个 Claude Code skill：把 `.robot` / `.resource` 里的 SeleniumLibrary 关键字转换成 robotframework-browser（Browser 库）写法。它不是全靠模型逐行改写，而是**脚本做机械替换 + Claude 处理语义差异**：

- 内置 Python 转换脚本处理库导入和一对一关键字映射（不漏、不破坏格式、不动自定义关键字架构）
- 转换不了的复杂项打 `# TODO(s2b)` 标记，Claude 按内置迁移指南逐条处理（Open Browser 三件套、弹窗顺序反转、iframe 穿透、Evaluate JavaScript、locator 前缀换算等）
- 输出到新目录，绝不覆盖原文件，并生成转换报告

映射数据来自 RF 核心开发者维护的社区权威项目 [Snooz82/robotframework-browser-migration](https://github.com/Snooz82/robotframework-browser-migration) 的实测实现（164/177 个关键字），不是猜测。

### 两条迁移路线

| | 路线 A：源码转换（本 skill 默认） | 路线 B：垫片库 + 渐进迁移 |
|---|---|---|
| 做法 | 把关键字真正改成 Browser 原生写法 | `Library SeleniumLibraryToBrowser`，改 import 就跑到 Playwright 上 |
| 产物 | 纯 Browser 脚本 | 原脚本几乎不动 + 逐步替换 |
| 适合 | 追求长期可维护、代码量可控 | 代码量大、想快速止血 |

skill 会在动手前和你确认走哪条路，也支持混合（先 B 后逐步 A）。

### 安装（Claude Code）

**macOS / Linux**

```bash
git clone https://github.com/gsk74521/robot-selenium-to-browser.git ~/.claude/skills/robot-selenium-to-browser
```

**Windows PowerShell**

```powershell
git clone https://github.com/gsk74521/robot-selenium-to-browser.git "$env:USERPROFILE\.claude\skills\robot-selenium-to-browser"
```

**Windows Git Bash**

```bash
git clone https://github.com/gsk74521/robot-selenium-to-browser.git "$USERPROFILE/.claude/skills/robot-selenium-to-browser"
```

只想在某个项目里用，就 clone 到项目的 `.claude/skills/` 下（项目级，仅该项目生效）。

**更新**

```bash
git -C ~/.claude/skills/robot-selenium-to-browser pull
```

安装后无需额外注册，Claude Code 启动时自动加载 skills 目录。用 `/skills` 可查看已加载的 skill，或直接发起迁移请求触发。

### 前置依赖

skill 的 `scripts/check_env.py` 会检查下面这些，缺什么会提示安装命令：

- Python ≥ 3.8
- `robotframework-browser`（`pip install -U robotframework-browser`）
- Node.js ≥ 18（Browser 库的 Playwright 驱动依赖）
- 浏览器二进制（`rfbrowser init`，需联网）

SeleniumLibrary 不必卸载——迁移期间两库可共存，方便对照运行。

### 使用

安装后直接用自然语言发起即可，例如：

- 「把这个目录下的 SeleniumLibrary 脚本迁移到 Browser 库」
- 「把 login.robot 从 selenium 转成 playwright」
- 「robot 自动化测试库从 SeleniumLibrary 升级到 robotframework-browser」

skill 会依次执行：环境检查 → 盘点（统计关键字用量和调用点）→ 脚本转换 → 处理 TODO → 验证 → 交付报告。

手动跑脚本也可以：

```bash
# 盘点：统计 SeleniumLibrary 关键字用量、调用点、按难度分类
python scripts/inventory.py <项目目录>

# 机械转换：输出到新目录并生成报告
python scripts/convert_robot.py <源目录> --out <输出目录> --report <报告目录>

# 环境检查
python scripts/check_env.py --install
```

> 若系统里 `python` 不可用（如 Windows 商店占位符），改用 `py` 或 `python3`。

### 目录结构

```
robot-selenium-to-browser/
├── SKILL.md                          # skill 主文件：迁移策略 + 五步工作流
├── scripts/
│   ├── check_env.py                  # 环境检查/安装
│   ├── inventory.py                  # 迁移前盘点（关键字用量、调用点、难度分类）
│   └── convert_robot.py              # 机械转换（库导入、一对一映射、TODO 标记、报告）
├── references/
│   ├── keyword-mapping.md            # 关键字映射总表（A/B/C 分类）
│   └── migration-guide.md            # 复杂场景处理规则（locator/等待/弹窗/frame/JS 等）
└── evals/
    ├── evals.json                    # 测试用例定义
    └── files/                        # 测试夹具
```

### 许可

[MIT](./LICENSE)

---

## English

### What it is

A Claude Code skill that converts SeleniumLibrary keywords in `.robot` / `.resource` files into [robotframework-browser](https://robotframework-browser.org/) (Browser library) form. It does not rely on the model rewriting every line: a bundled Python script does the mechanical work (library import swap, 1:1 keyword mapping) while Claude handles the semantic gaps.

- Mechanical conversion preserves formatting, comments, and your custom-keyword architecture
- Anything that cannot be mapped safely is tagged `# TODO(s2b)` and handled by Claude following the bundled migration guide (Open Browser split, alert ordering reversal, iframe piercing, Evaluate JavaScript, locator prefix translation, …)
- Output always goes to a new directory — the originals are never overwritten — with a conversion report

The mapping data is grounded in the community's authoritative implementation, [Snooz82/robotframework-browser-migration](https://github.com/Snooz82/robotframework-browser-migration) (164 of 177 keywords implemented), not guesswork.

### Two migration strategies

| | Route A: source conversion (default) | Route B: compatibility shim |
|---|---|---|
| How | Rewrite keywords into native Browser form | Import `SeleniumLibraryToBrowser`; scripts run on Playwright almost unchanged |
| Result | Pure Browser scripts | Original scripts kept, replaced gradually |
| Best for | Long-term maintainability, manageable codebase | Large codebases, quick wins |

The skill asks you to pick a route before doing anything, and supports a hybrid (start with B, migrate hot paths to A).

### Installation (Claude Code)

**macOS / Linux**

```bash
git clone https://github.com/gsk74521/robot-selenium-to-browser.git ~/.claude/skills/robot-selenium-to-browser
```

**Windows PowerShell**

```powershell
git clone https://github.com/gsk74521/robot-selenium-to-browser.git "$env:USERPROFILE\.claude\skills\robot-selenium-to-browser"
```

**Windows Git Bash**

```bash
git clone https://github.com/gsk74521/robot-selenium-to-browser.git "$USERPROFILE/.claude/skills/robot-selenium-to-browser"
```

For a single project, clone into that project's `.claude/skills/` instead (project-scoped).

**Update**

```bash
git -C ~/.claude/skills/robot-selenium-to-browser pull
```

No extra registration is needed — Claude Code loads skills from that directory on startup. Use `/skills` to confirm it is loaded, or just ask for a migration.

### Prerequisites

`scripts/check_env.py` verifies the following and tells you how to fix anything missing:

- Python ≥ 3.8
- `robotframework-browser` (`pip install -U robotframework-browser`)
- Node.js ≥ 18 (required by the Browser library's Playwright driver)
- Browser binaries (`rfbrowser init`, requires network)

You can keep SeleniumLibrary installed — both libraries coexist during migration, which is handy for side-by-side runs.

### Usage

Just ask in natural language, for example:

- "Migrate the SeleniumLibrary scripts in this directory to the Browser library"
- "Convert login.robot from Selenium to Playwright"
- "Upgrade our robot test library from SeleniumLibrary to robotframework-browser"

The skill then runs: environment check → inventory (keyword usage and call sites) → script conversion → TODO handling → verification → report.

You can also run the scripts directly:

```bash
# Inventory: keyword usage, call sites, difficulty breakdown
python scripts/inventory.py <project_dir>

# Mechanical conversion: writes to a new directory and generates a report
python scripts/convert_robot.py <src_dir> --out <out_dir> --report <report_dir>

# Environment check
python scripts/check_env.py --install
```

> If `python` is unavailable (e.g. the Windows Store stub), use `py` or `python3`.

### Repository layout

```
robot-selenium-to-browser/
├── SKILL.md                          # Migration strategies + 5-step workflow
├── scripts/
│   ├── check_env.py                  # Environment check / install
│   ├── inventory.py                  # Pre-migration inventory
│   └── convert_robot.py              # Mechanical conversion + report
├── references/
│   ├── keyword-mapping.md            # Keyword mapping table (A/B/C classes)
│   └── migration-guide.md            # Rules for complex cases
└── evals/
    ├── evals.json                    # Test case definitions
    └── files/                        # Test fixtures
```

### License

[MIT](./LICENSE)
