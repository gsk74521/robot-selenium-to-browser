#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""convert_robot.py — SeleniumLibrary → Browser 机械转换脚本

处理内容：
- Library 导入行替换（SeleniumLibrary/Selenium2Library → Browser，丢弃不兼容参数并记 TODO）
- A 类/B 类关键字的一对一映射（改名、追加参数、插入断言操作符、参数换位）
- 裸 xpath locator 自动补 xpath= 前缀；简单 id=/name=/class=/tag= 前缀自动转 css
- 无法自动转换的已知 SeleniumLibrary 关键字：保留原行，上方插入 # TODO(s2b) 注释
- 自定义关键字名、参数、文档、注释、目录结构一律不动

用法：
    python convert_robot.py <源目录或文件> --out <输出目录> [--report <报告目录>]
"""
import argparse
import json
import os
import re
import sys

TODO_MARK = "# TODO(s2b)"

# ---------------------------------------------------------------- 映射规则 ----
# 规则元组第一个元素是动作类型：
#   ("rename", 新名)                        直接改名，参数原样传递
#   ("append", 新名, [追加参数...])          改名 + 末尾追加参数
#   ("assert", 新名, 断言操作符)             改名 + 在所有参数前插入操作符
#   ("insert1", 新名, 插入词)                改名 + 在第 1 个参数后插入（如 Select Options By）
#   ("page_assert", 断言操作符)              → Get Text  body  <操作符>  <args...>
#   ("wait_state", state)                   → Wait For Elements State  sel  state  [timeout=]
#   ("radio",)                              Select Radio Button → Check Checkbox + 拼接 css
#   ("elem_screenshot",)                    Capture Element Screenshot 特判
#   ("todo", 原因)                          不转换，插入 TODO 注释行
#   ("rename_todo", 新名, 原因)             改名但仍需人工复核，附 TODO 注释

MAPPING = {
    # ---- A 类：直接改名 ----
    "close browser": ("rename", "Close Browser"),
    "go to": ("rename", "Go To"),
    "go back": ("rename", "Go Back"),
    "reload page": ("rename", "Reload"),
    "get title": ("rename", "Get Title"),
    "get location": ("rename", "Get Url"),
    "click element": ("rename", "Click"),
    "click button": ("rename", "Click"),
    "click link": ("rename", "Click"),
    "click image": ("rename", "Click"),
    "mouse over": ("rename", "Hover"),
    "drag and drop": ("rename", "Drag And Drop"),
    "drag and drop by offset": ("rename", "Drag And Drop By Coordinates"),
    "input text": ("rename", "Fill Text"),
    "clear element text": ("rename", "Clear Text"),
    "focus": ("rename", "Focus"),
    "set focus to element": ("rename", "Focus"),
    "scroll element into view": ("rename", "Scroll To Element"),
    "select checkbox": ("rename", "Check Checkbox"),
    "unselect checkbox": ("rename", "Uncheck Checkbox"),
    "choose file": ("rename", "Upload File By Selector"),
    "get text": ("rename", "Get Text"),
    "get element count": ("rename", "Get Element Count"),
    "set selenium timeout": ("rename", "Set Browser Timeout"),
    "get selenium timeout": ("rename", "Get Timeout"),
    "capture page screenshot": ("rename", "Take Screenshot"),
    "switch browser": ("rename", "Switch Browser"),
    "get window handles": ("rename", "Get Page Ids"),
    "get window titles": ("rename", "Get Page Titles"),
    "get cookie": ("rename", "Get Cookie"),
    "get cookies": ("rename", "Get Cookies"),
    "delete cookie": ("rename", "Delete Cookie"),
    "delete all cookies": ("rename", "Delete Cookies"),
    "register keyword to run on failure": ("rename", "Register Keyword To Run On Failure"),
    "close window": ("rename", "Close Page"),
    # ---- append ----
    "double click element": ("append", "Click", ["clickCount=2"]),
    "open context menu": ("append", "Click", ["button=right"]),
    "close all browsers": ("append", "Close Browser", ["ALL"]),
    "get value": ("append", "Get Property", ["value"]),
    "checkbox should be selected": ("append", "Get Checkbox State", ["==", "True"]),
    "checkbox should not be selected": ("append", "Get Checkbox State", ["==", "False"]),
    "mouse down": ("append", "Mouse Button", ["down"]),
    "mouse up": ("append", "Mouse Button", ["up"]),
    "get selected list label": ("append", "Get Selected Options", ["label"]),
    "get selected list value": ("append", "Get Selected Options", ["value"]),
    # ---- assert 操作符前插 ----
    "title should be": ("assert", "Get Title", "=="),
    "location should be": ("assert", "Get Url", "=="),
    "location should contain": ("assert", "Get Url", "contains"),
    "wait until location is": ("assert", "Get Url", "=="),
    "wait until location contains": ("assert", "Get Url", "contains"),
    "element text should be": ("assert", "Get Text", "=="),
    # ---- insert1 ----
    "element should contain": ("insert1", "Get Text", "contains"),
    "element should not contain": ("insert1", "Get Text", "not contains"),
    "wait until element contains": ("insert1", "Get Text", "contains", "drop_extra"),
    "wait until element does not contain": ("insert1", "Get Text", "not contains", "drop_extra"),
    "select from list by label": ("insert1", "Select Options By", "label"),
    "select from list by value": ("insert1", "Select Options By", "value"),
    "select from list by index": ("insert1", "Select Options By", "index"),
    # ---- page_assert（作用于整页文本）----
    "page should contain": ("page_assert", "contains"),
    "page should not contain": ("page_assert", "not contains"),
    "wait until page contains": ("page_assert", "contains", "drop_extra"),
    "wait until page does not contain": ("page_assert", "not contains", "drop_extra"),
    # ---- wait_state ----
    "wait until element is visible": ("wait_state", "visible"),
    "wait until element is not visible": ("wait_state", "hidden"),
    "wait until element is enabled": ("wait_state", "enabled"),
    "wait until element is disabled": ("wait_state", "disabled"),
    "element should be visible": ("wait_state", "visible"),
    "element should not be visible": ("wait_state", "hidden"),
    "element should be enabled": ("wait_state", "enabled"),
    "element should be disabled": ("wait_state", "disabled"),
    "wait until page contains element": ("wait_state", "attached"),
    "wait until page does not contain element": ("wait_state", "detached"),
    "page should contain element": ("wait_state", "attached"),
    "page should not contain element": ("wait_state", "detached"),
    # ---- Get Element Attribute：官方实现用 Get Property，参数顺序与 Selenium 相同 ----
    "get element attribute": ("rename", "Get Property"),
    # ---- 特判 ----
    "capture element screenshot": ("elem_screenshot",),
    "input password": ("rename", "Fill Secret"),
    # ---- B 类：改名但需人工复核 ----
    "press keys": ("rename_todo", "Press Keys",
                   "按键语法不同：Selenium 的 \\\\13/NULL 等需改为 Browser 的 Enter 等写法"),
    "switch window": ("rename_todo", "Switch Page",
                      "Browser 按 page id 切换；按 title/url 切换需配合 Get Page Ids/Get Page Titles"),
    "set window size": ("rename_todo", "Set Viewport Size", "Browser 设置的是 viewport 而非 OS 窗口"),
    "get window size": ("rename_todo", "Get Viewport Size", "Browser 获取的是 viewport 而非 OS 窗口"),
    "element attribute value should be": ("rename_todo", "Get Attribute",
                                          "参数顺序需调整为 (attribute, selector, ==, expected)"),
    # ---- C 类：无法自动转换 ----
    "open browser": ("todo", "Open Browser 需拆为 New Browser + New Context + New Page，见 migration-guide 第 1 节"),
    "maximize browser window": ("todo", "无对应，改用 Set Viewport Size 或 New Context 的 viewport，见 migration-guide 第 10 节"),
    "set window position": ("todo", "Browser 无窗口位置概念，通常直接删除"),
    "get window position": ("todo", "Browser 无窗口位置概念，通常直接删除"),
    "set selenium speed": ("todo", "改用 New Browser 的 slowMo 参数"),
    "set selenium implicit wait": ("todo", "Browser 自动等待，隐式等待概念不存在，删除本行"),
    "set browser implicit wait": ("todo", "Browser 自动等待，隐式等待概念不存在，删除本行"),
    "handle alert": ("todo", "改为 Handle Future Dialogs 且必须先注册再触发，见 migration-guide 第 4 节"),
    "alert should be present": ("todo", "改为 Handle Future Dialogs，见 migration-guide 第 4 节"),
    "alert should not be present": ("todo", "Browser 弹窗默认未注册会报错，按需用 Handle Future Dialogs，见 migration-guide 第 4 节"),
    "dismiss alert": ("todo", "改为 Handle Future Dialogs  action=dismiss，注意先注册后触发"),
    "input text into alert": ("todo", "改为 Handle Future Dialogs  action=accept  prompt_input=..."),
    "select frame": ("todo", "Browser 无 frame 上下文切换，用 iframe 穿透选择器 iframe >>> css=...，见 migration-guide 第 5 节"),
    "unselect frame": ("todo", "Browser 无 frame 上下文切换，删除本行并检查上方 Select Frame 的改写"),
    "current frame should contain": ("todo", "用 iframe 穿透选择器 + Get Text 组合改写"),
    "frame should contain": ("todo", "用 iframe 穿透选择器 + Get Text 组合改写"),
    "execute javascript": ("todo", "改为 Evaluate JavaScript，参数机制不同（箭头函数），见 migration-guide 第 7 节"),
    "execute async javascript": ("todo", "改为 Evaluate JavaScript，函数返回 Promise 即可自动 await"),
    "get webelement": ("todo", "Browser 无元素句柄复用模式，改为复用 selector 字符串，见 migration-guide 第 8 节"),
    "get webelements": ("todo", "Browser 无元素句柄复用模式，改为 Get Element Count + nth= 或复用 selector，见 migration-guide 第 8 节"),
    "wait for condition": ("todo", "改为 Wait For Function"),
    "simulate event": ("todo", "改用 Evaluate JavaScript dispatchEvent"),
    "simulate": ("todo", "改用 Evaluate JavaScript dispatchEvent"),
    "table cell should contain": ("todo", "无对应，用 css/xpath + Get Text contains 组合改写"),
    "table column should contain": ("todo", "无对应，用 css/xpath + Get Text contains 组合改写"),
    "table row should contain": ("todo", "无对应，用 css/xpath + Get Text contains 组合改写"),
    "table header should contain": ("todo", "无对应，用 css/xpath + Get Text contains 组合改写"),
    "table footer should contain": ("todo", "无对应，用 css/xpath + Get Text contains 组合改写"),
    "table should contain": ("todo", "无对应，用 css/xpath + Get Text contains 组合改写"),
    "get table cell": ("todo", "无对应，用 css 选择器定位单元格 + Get Text 改写"),
    "page should contain button": ("todo", "改为 Wait For Elements State  css=input[type=button],button  attached 等具体选择器"),
    "page should contain link": ("todo", "改为 Wait For Elements State  css=a >> text=...  attached"),
    "page should contain image": ("todo", "改为 Wait For Elements State  css=img[...]  attached"),
    "page should contain textfield": ("todo", "改为 Wait For Elements State  css=input[type=text]  attached"),
    "page should contain checkbox": ("todo", "改为 Wait For Elements State  css=input[type=checkbox]  attached"),
    "page should contain radio button": ("todo", "改为 Wait For Elements State  css=input[type=radio]  attached"),
    "set screenshot directory": ("todo", "Browser 无全局截图目录，Take Screenshot 用绝对/相对路径参数"),
    "add location strategy": ("todo", "Browser 无自定义定位策略扩展点"),
    "assign id to element": ("todo", "无对应，改用其他定位方式"),
    "element should be focused": ("todo", "用 Get Element States 查 focused 或 Evaluate JavaScript 判断 activeElement"),
    "element should not be focused": ("todo", "用 Get Element States 查 focused 或 Evaluate JavaScript 判断 activeElement"),
    "get element size": ("todo", "改为 Get BoundingBox 取 width/height 字段"),
    "get element position": ("todo", "改为 Get BoundingBox 取 x/y 字段"),
    "get horizontal position": ("todo", "改为 Get BoundingBox 取 x 字段"),
    "get vertical position": ("todo", "改为 Get BoundingBox 取 y 字段"),
    "submit form": ("todo", "改为直接 Click 提交按钮或 Press Keys  Enter"),
    "mouse down on image": ("todo", "改为 Hover + Mouse Button  down 组合"),
    "mouse down on link": ("todo", "改为 Hover + Mouse Button  down 组合"),
    "mouse up on image": ("todo", "改为 Hover + Mouse Button  up 组合"),
    "mouse up on link": ("todo", "改为 Hover + Mouse Button  up 组合"),
    "click element at coordinates": ("todo", "改为 Click  position={'x': ..., 'y': ...}"),
    "get list items": ("todo", "改为 Get Select Options（返回 dict 列表，字段访问方式需调整）"),
    "add cookie": ("todo", "Browser 的 Add Cookie 需要 url= 或 domain=/path= 参数，需人工补充"),
    "select radio button": ("radio",),
    "select window": ("todo", "Browser 用 Switch Page(id)；按 title 切换需组合 Get Page Ids/Get Page Titles"),
}

# 需要修正第一个位置参数（locator）的目标关键字（转换后的 Browser 名）
LOCATOR_FIRST_ARG = {
    "Click", "Hover", "Fill Text", "Fill Secret", "Clear Text", "Focus",
    "Scroll To Element", "Check Checkbox", "Uncheck Checkbox",
    "Upload File By Selector", "Get Text", "Get Element Count",
    "Get Property", "Get Checkbox State",
    "Wait For Elements State", "Select Options By", "Get Selected Options",
    "Press Keys", "Drag And Drop", "Type Text",
}
# 注意：Get Attribute(attribute, selector)、Mouse Button(button, selector) 首位不是 locator，不能列入

# locator 前缀 → Browser 写法（依据 SeleniumLibraryToBrowser 的实测实现）
# Selenium 的定位策略分隔符 `=` 和 `:` 等价，官方实现用 " ?[:=] ?"，这里保持一致
# 顺序敏感：partial link 必须在 link 之前匹配
PREFIX_AUTO = [
    # id= Browser 原生支持，但 id: 不行，统一归一化为 id=
    (re.compile(r"^id ?[:=] ?([^\s]+)$", re.I), lambda m: "id=" + m.group(1)),
    (re.compile(r"^partial link ?[:=] ?(.+)$", re.I), lambda m: "css=a >> text=%s" % m.group(1)),
    (re.compile(r"^link ?[:=] ?(.+)$", re.I), lambda m: 'css=a >> text="%s"' % m.group(1)),
    (re.compile(r"^identifier ?[:=] ?([^\s]+)$", re.I), lambda m: "css=[id=%s], [name=%s]" % (m.group(1), m.group(1))),
    (re.compile(r"^name ?[:=] ?([^\s]+)$", re.I), lambda m: "css=[name=%s]" % m.group(1)),
    (re.compile(r"^class ?[:=] ?([^\s]+)$", re.I), lambda m: "css=." + m.group(1)),
    (re.compile(r"^tag ?[:=] ?([^\s]+)$", re.I), lambda m: "css=" + m.group(1)),
    (re.compile(r"^data ?[:=] ?([^:\s]+):([^\s]+)$", re.I), lambda m: 'xpath=//*[@data-%s="%s"]' % (m.group(1), m.group(2))),
    (re.compile(r"^(?:jquery|sizzle) ?[:=] ?(.+)$", re.I), lambda m: "css=" + m.group(1)),
]
# id= 前缀 Browser 原生支持，保留不动，不在此表
# dom= 官方直接拒绝，只能人工改写
PREFIX_TODO = re.compile(r"^dom ?[:=]", re.I)
# 裸 locator（无前缀的简单标识符）→ Selenium 的 id/name 默认语义
BARE_LOCATOR = re.compile(r"^[A-Za-z_][\w.\-]*$")

SECTION_RE = re.compile(r"^\*\*\*\s*(.+?)\s*\*\*\*")
KW_SETTING_CELLS = {
    "suite setup", "suite teardown", "test setup", "test teardown",
    "task setup", "task teardown", "test template", "task template",
}
BRACKET_TAGS = {"[setup]", "[teardown]", "[template]", "[timeout]"}
ASSIGN_RE = re.compile(r"^[@$&]\{[^}]*\}\s*=\s*$")


def is_assign(cell):
    """判断 cell 是否为 RF 赋值前缀，如 ${var}= / @{list}= / &{dict}=。"""
    return ASSIGN_RE.match(cell.strip()) is not None


def _resolve_kw_idx(cells, first_idx):
    """定位关键字 cell 下标：若行首是赋值前缀（${var}=），关键字在其后。"""
    if is_assign(cells[first_idx]):
        for j in range(first_idx + 1, len(cells)):
            if not is_blank(cells[j]):
                return j
    return first_idx

BROWSER_INCOMPAT_LIB_ARGS = {
    "implicit_wait", "selenium_speed", "run_on_failure",
    "screenshot_root_directory", "event_firing_webdriver",
}


def norm(name):
    return re.sub(r"[\s_]+", " ", name.strip().lower())


def split_cells(line):
    """按 RF 规则切分单元格（2+ 空格或 tab），保留每格原文与分隔符。"""
    parts = re.split(r"(\t| {2,})", line.rstrip("\n"))
    # parts 交替为 [cell, sep, cell, sep, ...]
    return parts


def is_blank(cell):
    return cell.strip() == ""


def fix_locator_arg(arg, todos, lineno, kwname):
    """修正 locator 参数：裸 xpath 补前缀；各前缀按权威表转 css；不支持的前缀记 TODO。"""
    if arg.startswith(("/", "(/")) and "=" not in arg.split("/", 1)[0]:
        return "xpath=" + arg, None
    if arg.startswith("${") or arg.startswith("@{") or arg.startswith("%{"):
        return arg, None  # 变量，运行时才知道，不动
    for rx, fn in PREFIX_AUTO:
        m = rx.match(arg)
        if m:
            return fn(m), None
    if PREFIX_TODO.match(arg):
        return arg, "dom= 前缀 Browser 不支持（官方直接拒绝），需手工改写为 css/xpath：%s" % arg
    # 裸 locator：Selenium 按 id/name 解析，等价 css=[id='x'], [name='x']
    if BARE_LOCATOR.match(arg):
        return "css=[id='%s'], [name='%s']" % (arg, arg), \
            "裸 locator '%s' 按 Selenium 的 id/name 默认语义转换为 css=[id=...], [name=...]，请复核（若两者都匹配会触发 strict mode）" % arg
    return arg, None


def convert_call(cells, kw_idx, rule, todos, lineno):
    """根据规则改写 cells（kw_idx 为关键字所在 cell 下标），返回新增的 TODO 注释原因或 None。"""
    action = rule[0]
    if action == "todo":
        return rule[1]
    # 提取行尾注释，改写后重新附上
    comment = None
    for i in range(len(cells) - 1, kw_idx, -1):
        c = cells[i]
        if is_blank(c):
            continue
        if c.lstrip().startswith("#"):
            comment = c.strip()
        break
    args = [c for i, c in enumerate(cells)
            if i > kw_idx and not is_blank(c) and not c.lstrip().startswith("#")]
    note = None

    if action == "rename":
        new_name, new_args = rule[1], args
        # Input Text 带 clear=False 时是追加输入，Fill Text 会先清空，必须改用 Type Text
        if new_name == "Fill Text" and any(
                re.match(r"^clear\s*=\s*(false|no|off|0)$", a, re.I) for a in args):
            new_name = "Type Text"
    elif action == "append":
        new_name, new_args = rule[1], args + rule[2]
    elif action == "assert":
        new_name, new_args = rule[1], [rule[2]] + args
    elif action == "insert1":
        new_name = rule[1]
        if len(rule) > 3 and rule[3] == "drop_extra" and len(args) > 2:
            note = "原 timeout/error 参数已丢弃（Browser 断言自动重试，超时由 Set Browser Timeout 控制）：%s" % ", ".join(args[2:])
            args = args[:2]
        new_args = args[:1] + [rule[2]] + args[1:]
    elif action == "page_assert":
        new_name = "Get Text"
        if len(rule) > 2 and rule[2] == "drop_extra" and len(args) > 1:
            note = "原 timeout/error 参数已丢弃（Browser 断言自动重试，超时由 Set Browser Timeout 控制）：%s" % ", ".join(args[1:])
            args = args[:1]
        new_args = ["body", rule[1]] + args
    elif action == "wait_state":
        new_name = "Wait For Elements State"
        new_args = args[:1] + [rule[1]]
        if len(args) >= 2:
            new_args.append("timeout=" + args[1])
        if len(args) >= 3:
            note = "原 error 参数无对应，已丢弃：" + args[2]
    elif action == "radio":
        # Select Radio Button  group  value → Check Checkbox  input[type='radio'][name='group'][value='value']
        new_name = "Check Checkbox"
        group = args[0] if args else ""
        value = args[1] if len(args) > 1 else ""
        new_args = ["input[type='radio'][name='%s'][value='%s']" % (group, value)]
        note = "Select Radio Button 已按官方实现拼接为 css 选择器，请确认 group/value 变量在运行时拼接正确"
    elif action == "rename_todo":
        new_name, new_args, note = rule[1], args, rule[2]
    elif action == "elem_screenshot":
        # Capture Element Screenshot  sel  [filename] → Take Screenshot  [filename]  selector=sel
        new_name = "Take Screenshot"
        new_args = args[1:] + ["selector=" + args[0]] if args else args
    else:
        return None

    new_cells = cells[:kw_idx] + [new_name]
    for a in new_args:
        new_cells += ["    ", a]
    if comment:
        new_cells += ["    ", comment]
    cells[:] = new_cells

    # page_assert / radio 的 locator 是本脚本合成的（body、input[type=...]），不能再按 Selenium locator 规则修正
    if action in ("page_assert", "radio"):
        return note
    locator_note = _apply_locator_fix(cells, kw_idx, todos, lineno)
    return note or locator_note


def _apply_locator_fix(cells, kw_idx, todos, lineno):
    """对 locator 类关键字的第一个位置参数做 xpath/前缀修正。"""
    new_name = cells[kw_idx]
    if new_name not in LOCATOR_FIRST_ARG:
        return None
    for i in range(kw_idx + 1, len(cells)):
        c = cells[i]
        if is_blank(c):
            continue
        if c.startswith("#"):
            return None
        fixed, note = fix_locator_arg(c, todos, lineno, new_name)
        cells[i] = fixed
        return note
    return None


def convert_library_line(cells, todos, lineno):
    """处理 Settings 段的 Library 导入行。"""
    lib_idx = None
    for i, c in enumerate(cells):
        if norm(c) == "library":
            lib_idx = i
            break
    if lib_idx is None:
        return False
    name_idx = None
    for i in range(lib_idx + 1, len(cells)):
        if not is_blank(cells[i]):
            name_idx = i
            break
    if name_idx is None:
        return False
    lib_name = cells[name_idx].strip()
    if norm(lib_name) not in ("seleniumlibrary", "selenium2library"):
        return False
    cells[name_idx] = "Browser"
    # 过滤不兼容导入参数
    dropped = []
    for i in range(name_idx + 1, len(cells)):
        c = cells[i]
        if is_blank(c) or c.startswith("#"):
            continue
        key = c.split("=", 1)[0].strip().lower()
        if key in BROWSER_INCOMPAT_LIB_ARGS:
            dropped.append(c)
            cells[i] = ""
    if dropped:
        todos.append({"line": lineno, "keyword": "Library import",
                      "reason": "Browser 不支持的导入参数已移除：%s" % ", ".join(dropped)})
    return True


def convert_file(src_path, dst_path):
    with open(src_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    out = []
    todos = []
    renames = 0
    section = None

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        m = SECTION_RE.match(stripped)
        if m:
            section = norm(m.group(1)).replace(" ", "")
            out.append(line)
            continue
        if not stripped or stripped.startswith("#"):
            out.append(line)
            continue

        cells = split_cells(line)
        first_idx = None
        for i, c in enumerate(cells):
            if not is_blank(c):
                first_idx = i
                break
        if first_idx is None:
            out.append(line)
            continue

        first = cells[first_idx].strip()
        note = None

        if section in ("settings", "setting"):
            if norm(first) == "library":
                convert_library_line(cells, todos, lineno)
            elif norm(first) in KW_SETTING_CELLS:
                # Suite Setup    Open Browser ... → 关键字在下一个非空格
                for j in range(first_idx + 1, len(cells)):
                    if not is_blank(cells[j]):
                        rule = MAPPING.get(norm(cells[j]))
                        if rule:
                            note = convert_call(cells, j, rule, todos, lineno)
                            if rule[0] != "todo":
                                renames += 1
                        break
        elif section in ("testcases", "tasks"):
            if first.startswith("[") and first.lower() in BRACKET_TAGS:
                for j in range(first_idx + 1, len(cells)):
                    if not is_blank(cells[j]):
                        rule = MAPPING.get(norm(cells[j]))
                        if rule:
                            note = convert_call(cells, j, rule, todos, lineno)
                            if rule[0] != "todo":
                                renames += 1
                        break
            elif first_idx > 0:  # 缩进行才是关键字调用；顶格行是用例名
                kw_idx = _resolve_kw_idx(cells, first_idx)
                rule = MAPPING.get(norm(cells[kw_idx]))
                if rule:
                    note = convert_call(cells, kw_idx, rule, todos, lineno)
                    if rule[0] != "todo":
                        renames += 1
        elif section in ("keywords", "keyword"):
            if first_idx > 0:  # 顶格行是关键字定义名，不动
                kw_idx = _resolve_kw_idx(cells, first_idx)
                rule = MAPPING.get(norm(cells[kw_idx]))
                if rule:
                    note = convert_call(cells, kw_idx, rule, todos, lineno)
                    if rule[0] != "todo":
                        renames += 1
        # variables/comments 段及其他段落不动
        elif section == "variables":
            # 变量值是裸 xpath（/ 开头）时提示：Browser 中裸 xpath 会被当 css 解析
            vals = [c for c in cells if not is_blank(c)]
            if len(vals) >= 2 and vals[1].startswith(("/", "(/")):
                todos.append({"line": lineno, "keyword": vals[0],
                              "reason": "变量值是裸 xpath，Browser 会按 css 解析，请加 xpath= 前缀"})
                indent = re.match(r"^[\t ]*", line).group(0)
                out.append(indent + TODO_MARK + " 变量值是裸 xpath，Browser 会按 css 解析，请加 xpath= 前缀\n")

        if note:
            indent = re.match(r"^[\t ]*", line).group(0)
            out.append(indent + TODO_MARK + " " + note + "\n")
            todos.append({"line": lineno, "keyword": first, "reason": note})

        # 重新拼行：cells 中可能有被清空的参数（如 Library 行），压缩连续空分隔
        new_line = rebuild(cells)
        out.append(new_line if new_line.endswith("\n") else new_line + "\n")

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "w", encoding="utf-8", newline="") as f:
        f.writelines(out)
    return {"file": src_path, "renames": renames, "todos": todos}


def rebuild(cells):
    """把 cells 数组重新拼成一行：被清空的参数 cell 连同其后分隔符丢弃，行首缩进保留。"""
    result = []
    i = 0
    n = len(cells)
    while i < n:
        c = cells[i]
        if c == "" and result and i + 1 < n and re.fullmatch(r"(\t| {2,})", cells[i + 1] or ""):
            i += 2
            continue
        result.append(c)
        i += 1
    line = "".join(result)
    return line.rstrip()


def iter_robot_files(path):
    if os.path.isfile(path):
        yield path, os.path.basename(path)
        return
    for root, _dirs, files in os.walk(path):
        for fn in sorted(files):
            if fn.lower().endswith((".robot", ".resource")):
                full = os.path.join(root, fn)
                yield full, os.path.relpath(full, path)


def main():
    ap = argparse.ArgumentParser(description="SeleniumLibrary → Browser 机械转换")
    ap.add_argument("src", help="源目录或单个 .robot/.resource 文件")
    ap.add_argument("--out", required=True, help="输出目录（镜像源目录结构）")
    ap.add_argument("--report", help="报告输出目录（默认 <out>/conversion_report.*）")
    args = ap.parse_args()

    report_dir = args.report or args.out
    os.makedirs(report_dir, exist_ok=True)

    results = []
    for full, rel in iter_robot_files(args.src):
        dst = os.path.join(args.out, rel)
        results.append(convert_file(full, dst))

    total_renames = sum(r["renames"] for r in results)
    total_todos = sum(len(r["todos"]) for r in results)

    json_path = os.path.join(report_dir, "conversion_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": {"files": len(results), "renames": total_renames,
                               "todos": total_todos},
                   "files": results}, f, ensure_ascii=False, indent=2)

    md_path = os.path.join(report_dir, "conversion_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# SeleniumLibrary → Browser 转换报告\n\n")
        f.write("- 转换文件数：%d\n- 自动替换关键字调用：%d 处\n- 待人工处理 TODO：%d 处\n\n"
                % (len(results), total_renames, total_todos))
        f.write("## 处理顺序建议\n\n")
        f.write("先读 references/migration-guide.md，再按下表逐个处理 TODO。\n\n")
        for r in results:
            if not r["todos"]:
                continue
            f.write("### %s（重命名 %d 处，TODO %d 处）\n\n"
                    % (r["file"], r["renames"], len(r["todos"])))
            for t in r["todos"]:
                f.write("- 第 %d 行 `%s`：%s\n" % (t["line"], t["keyword"], t["reason"]))
            f.write("\n")

    print("完成：%d 个文件，自动替换 %d 处，TODO %d 处" % (len(results), total_renames, total_todos))
    print("报告：%s" % md_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
