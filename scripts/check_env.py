#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_env.py — robotframework-browser 环境检查与安装

检查项：
1. Python 版本（Browser 库要求 >= 3.8）
2. robotframework / robotframework-browser 是否安装及版本
3. Node.js 是否安装及版本（Playwright 驱动依赖 Node，要求 >= 18）
4. rfbrowser init 是否执行过（浏览器二进制是否就绪）
5. 可选：SeleniumLibrary 是否仍安装（迁移期共存提示）

用法：
    python check_env.py [项目目录]          # 只检查
    python check_env.py --install          # 检查并自动安装缺失项（联网）
"""
import argparse
import json
import os
import re
import subprocess
import sys


def run(cmd, timeout=120):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return -1, "命令不存在: %s" % cmd[0]
    except subprocess.TimeoutExpired:
        return -2, "命令超时: %s" % " ".join(cmd)


def pip_show(pkg):
    rc, out = run([sys.executable, "-m", "pip", "show", pkg])
    if rc != 0:
        return None
    m = re.search(r"^Version:\s*(\S+)", out, re.M)
    return m.group(1) if m else "unknown"


def check(project_dir="."):
    results = []

    # 1. Python
    v = sys.version_info
    ok = v >= (3, 8)
    results.append({"item": "Python >= 3.8", "ok": ok,
                    "detail": "%d.%d.%d" % (v.major, v.minor, v.micro),
                    "fix": "升级 Python 到 3.8 以上"})

    # 2. pip 包
    rf = pip_show("robotframework")
    results.append({"item": "robotframework 已安装", "ok": rf is not None,
                    "detail": rf or "未安装",
                    "fix": "pip install -U robotframework"})
    rb = pip_show("robotframework-browser")
    results.append({"item": "robotframework-browser 已安装", "ok": rb is not None,
                    "detail": rb or "未安装",
                    "fix": "pip install -U robotframework-browser"})
    sl = pip_show("robotframework-seleniumlibrary")
    results.append({"item": "SeleniumLibrary 状态（迁移期可共存）", "ok": True,
                    "detail": ("已安装 %s，迁移期间保留以便对照运行，全量迁移完成后可卸载" % sl)
                    if sl else "未安装",
                    "fix": None})

    # 3. Node.js
    rc, out = run(["node", "--version"])
    node_ok = False
    node_ver = out.strip().splitlines()[0] if rc == 0 and out.strip() else "未安装"
    if rc == 0:
        m = re.search(r"(\d+)", node_ver)
        node_ok = bool(m and int(m.group(1)) >= 18)
    results.append({"item": "Node.js >= 18", "ok": node_ok, "detail": node_ver,
                    "fix": "安装 Node.js LTS（https://nodejs.org），Browser 库的 Playwright 驱动依赖它"})

    # 4. rfbrowser init 状态：尝试 dry 检查浏览器是否就绪
    rfb_ok = False
    rfb_detail = "未检查（robotframework-browser 未安装）"
    if rb is not None:
        rc, out = run([sys.executable, "-m", "Browser.entry", "--version"], timeout=60)
        if rc != 0:
            # 退而求其次：看 rfbrowser 命令是否存在
            rc2, out2 = run(["rfbrowser", "--version"], timeout=60)
            if rc2 == 0:
                rfb_detail = "rfbrowser CLI 可用（%s）" % out2.strip().splitlines()[0]
                rfb_ok = True
            else:
                rfb_detail = "rfbrowser 命令不可用"
        else:
            rfb_detail = out.strip().splitlines()[0]
            rfb_ok = True
        # 检查浏览器二进制是否下载过
        if rfb_ok:
            rc3, out3 = run(["rfbrowser", "show-trace", "--help"], timeout=30)
            pw_cache = os.path.expanduser(os.environ.get(
                "PLAYWRIGHT_BROWSERS_PATH",
                "~/.cache/ms-playwright" if os.name != "nt"
                else "~/AppData/Local/ms-playwright"))
            has_browsers = os.path.isdir(os.path.expanduser(pw_cache)) and bool(
                os.listdir(os.path.expanduser(pw_cache)))
            rfb_detail += "；浏览器二进制%s就绪" % ("" if has_browsers else "未")
            rfb_ok = rfb_ok and has_browsers
    results.append({"item": "rfbrowser init 已执行（浏览器二进制就绪）", "ok": rfb_ok,
                    "detail": rfb_detail,
                    "fix": "rfbrowser init（需联网下载 Chromium/Firefox/WebKit）"})

    return results


def install(results):
    """对失败项执行安装。返回执行日志。"""
    logs = []
    for r in results:
        if r["ok"] or not r["fix"]:
            continue
        item = r["item"]
        if item.startswith("robotframework-browser"):
            cmd = [sys.executable, "-m", "pip", "install", "-U", "robotframework-browser"]
        elif item.startswith("robotframework 已安装"):
            cmd = [sys.executable, "-m", "pip", "install", "-U", "robotframework"]
        elif item.startswith("rfbrowser"):
            cmd = ["rfbrowser", "init"]
        else:
            logs.append("跳过 %s：需人工处理（%s）" % (item, r["fix"]))
            continue
        logs.append("执行: %s" % " ".join(cmd))
        rc, out = run(cmd, timeout=600)
        logs.append("  返回码 %d\n%s" % (rc, out[-2000:]))
    return logs


def main():
    ap = argparse.ArgumentParser(description="robotframework-browser 环境检查")
    ap.add_argument("project_dir", nargs="?", default=".", help="项目目录（仅用于展示）")
    ap.add_argument("--install", action="store_true", help="自动安装缺失项（联网）")
    args = ap.parse_args()

    print("== robotframework-browser 环境检查 ==")
    results = check(args.project_dir)
    all_ok = True
    for r in results:
        mark = "OK " if r["ok"] else "缺失"
        print("[%s] %s：%s" % (mark, r["item"], r["detail"]))
        if not r["ok"]:
            all_ok = False
            if r["fix"]:
                print("       修复：%s" % r["fix"])

    if args.install and not all_ok:
        print("\n== 自动安装缺失项 ==")
        for line in install(results):
            print(line)
        print("\n== 安装后复查 ==")
        for r in check(args.project_dir):
            print("[%s] %s：%s" % ("OK " if r["ok"] else "缺失", r["item"], r["detail"]))
    elif not all_ok:
        print("\n存在缺失项。加 --install 可自动安装（pip 包与浏览器二进制需联网）。")
    else:
        print("\n环境就绪，可以开始转换与试运行。")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
