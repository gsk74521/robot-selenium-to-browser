#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inventory.py — SeleniumLibrary 关键字使用盘点

迁移前的盘点工具：静态扫描 .robot/.resource 文件，统计每个 SeleniumLibrary 关键字
被调用了多少次、分布在多少个调用点（测试用例/自定义关键字），并按迁移难度分类，
给出工作量预估。

分类依据 convert_robot.py 的映射表（单一数据源）：
  direct  脚本可自动转换（一对一映射）
  review  脚本转换 + 人工复核（参数/语义有差异）
  manual  Browser 无直接对应，必须人工改写
  unshim  manual 中最棘手的一类——连官方垫片库 SeleniumLibraryToBrowser 也没实现

用法：
    py inventory.py <源目录或文件> [--json 输出路径]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from convert_robot import (  # noqa: E402  复用同一份映射表，避免两处维护
    MAPPING, norm, split_cells, is_blank, is_assign, _resolve_kw_idx,
    SECTION_RE, BRACKET_TAGS, KW_SETTING_CELLS,
)

# 官方垫片库 SeleniumLibraryToBrowser 也实现不了的 13 个（Playwright 架构上无法透明等价）
UNSHIMMED = {
    "add location strategy", "remove location strategy",
    "alert should be present", "alert should not be present",
    "handle alert", "input text into alert", "create webdriver",
    "execute async javascript", "get action chain delay", "set action chain delay",
    "get session id", "set browser implicit wait", "set window position",
}


def classify(action):
    if action == "todo":
        return "manual"
    if action == "rename_todo":
        return "review"
    return "direct"


def iter_files(path):
    if os.path.isfile(path):
        yield path
        return
    for root, _dirs, files in os.walk(path):
        for fn in sorted(files):
            if fn.lower().endswith((".robot", ".resource")):
                yield os.path.join(root, fn)


def scan_file(path):
    """返回 (uses_sl, {kwname: {"count": n, "parents": set}}, total_calls)。"""
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    uses_sl = False
    found = {}
    parent = None
    section = None

    for line in lines:
        stripped = line.strip()
        m = SECTION_RE.match(stripped)
        if m:
            section = norm(m.group(1)).replace(" ", "")
            parent = None
            continue
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.lower().startswith("library") and (
                "seleniumlibrary" in stripped.lower() or "selenium2library" in stripped.lower()):
            uses_sl = True

        cells = split_cells(line)
        first_idx = None
        for i, c in enumerate(cells):
            if not is_blank(c):
                first_idx = i
                break
        if first_idx is None:
            continue

        if section in ("testcases", "tasks", "keywords", "keyword"):
            # 顶格行 = 用例/关键字定义名（settings 段除外）
            if first_idx == 0 and section in ("testcases", "tasks", "keywords", "keyword"):
                if not cells[0].strip().startswith("["):
                    parent = cells[0].strip()
                    continue
            kw_idx = _resolve_kw_idx(cells, first_idx)
            name = norm(cells[kw_idx])
            if name in MAPPING:
                entry = found.setdefault(name, {"count": 0, "parents": set()})
                entry["count"] += 1
                entry["parents"].add(parent or "(suite-file)")
        elif section in ("settings", "setting"):
            first = norm(cells[first_idx])
            if first in KW_SETTING_CELLS:
                for j in range(first_idx + 1, len(cells)):
                    if not is_blank(cells[j]):
                        n = norm(cells[j])
                        if n in MAPPING:
                            e = found.setdefault(n, {"count": 0, "parents": set()})
                            e["count"] += 1
                        e["parents"].add("(settings)")
                        break
    return uses_sl, found


def main():
    ap = argparse.ArgumentParser(description="SeleniumLibrary 关键字使用盘点")
    ap.add_argument("src", help="源目录或单个 .robot/.resource 文件")
    ap.add_argument("--json", help="把盘点结果写入 JSON 文件")
    args = ap.parse_args()

    files = list(iter_files(args.src))
    sl_files = []
    agg = {}
    total = 0
    for p in files:
        uses_sl, found = scan_file(p)
        if uses_sl:
            sl_files.append(p)
        for name, e in found.items():
            a = agg.setdefault(name, {"count": 0, "parents": set(), "cat": classify(MAPPING[name][0]),
                                      "files": set()})
            a["count"] += e["count"]
            a["parents"] |= e["parents"]
            a["files"].add(p)
            total += e["count"]

    # 输出
    print("== SeleniumLibrary 使用盘点 ==")
    print("扫描文件：%d 个（其中 %d 个 import 了 SeleniumLibrary）" % (len(files), len(sl_files)))
    print("关键字调用总计：%d 处\n" % total)

    buckets = {"direct": [], "review": [], "manual": []}
    for name, a in agg.items():
        buckets[a["cat"]].append((name, a))

    label = {"direct": "可自动转换（一对一映射）",
             "review": "转换后需人工复核",
             "manual": "需人工改写（无直接对应）"}
    for cat in ("direct", "review", "manual"):
        items = sorted(buckets[cat], key=lambda x: -x[1]["count"])
        n_calls = sum(a["count"] for _, a in items)
        print("── %s：%d 个关键字，%d 处调用 ──" % (label[cat], len(items), n_calls))
        for name, a in items:
            flag = "  [垫片也不支持]" if name in UNSHIMMED else ""
            print("   %-42s 调用 %3d 次 / %d 个调用点%s"
                  % (name.title(), a["count"], len(a["parents"]), flag))
        print()

    manual_calls = sum(a["count"] for _, a in buckets["manual"])
    unshim_calls = sum(a["count"] for name, a in buckets["manual"] if name in UNSHIMMED)
    print("工作量估计：%d 处可自动转换，%d 处需人工（其中 %d 处连垫片也做不了）"
          % (sum(a["count"] for _, a in buckets["direct"]),
             manual_calls + sum(a["count"] for _, a in buckets["review"]), unshim_calls))
    print("注意：调用点(parents)越多，封装改动越分散；优先封装到公共资源文件能大幅降低改动量。")

    if args.json:
        out = {
            "scanned_files": len(files),
            "seleniumlibrary_files": sl_files,
            "total_calls": total,
            "keywords": {
                name: {"count": a["count"], "parents": len(a["parents"]),
                       "category": a["cat"], "unshimmed": name in UNSHIMMED,
                       "files": sorted(a["files"])}
                for name, a in sorted(agg.items())
            },
            "summary": {
                "direct_calls": sum(a["count"] for _, a in buckets["direct"]),
                "review_calls": sum(a["count"] for _, a in buckets["review"]),
                "manual_calls": manual_calls,
                "unshimmed_calls": unshim_calls,
            },
        }
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print("\n盘点 JSON：%s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
