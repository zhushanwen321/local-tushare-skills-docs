#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 local_index.md，将 remote_index.md 中的在线链接替换为本地路径。"""

import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
INDEX_FILE = os.path.join(DOCS_DIR, "remote_index.md")
OUTPUT_FILE = os.path.join(DOCS_DIR, "local_index.md")


def scan_md_files() -> dict[str, list[str]]:
    """扫描 docs/ 下所有 md 文件，返回 {文件名: [相对路径列表]} 映射。"""
    md_files: dict[str, list[str]] = {}
    for root, _, files in os.walk(DOCS_DIR):
        for file in files:
            if file.endswith(".md") and file not in ("remote_index.md", "local_index.md"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, DOCS_DIR)
                md_files.setdefault(file, []).append(rel_path)
    return md_files


def replace_links(content: str, md_files: dict[str, list[str]]) -> str:
    """逐行处理 remote_index.md，将在线链接替换为本地路径。"""
    # 匹配整行：提取接口名、在线链接、分类
    line_pattern = re.compile(
        r'\|\s*(?P<before>[^|]*?)\s*\[(?P<name>[^\]]+)\]\(https://tushare\.pro/wctapi/documents/\d+\.md\)\s*(?P<after>[^|]*\|[^|]*\|(?P<category>[^|]*))\|'
    )

    original_count = 0
    replaced = 0
    result_lines = []

    for line in content.split("\n"):
        m = line_pattern.search(line)
        if not m:
            result_lines.append(line)
            continue

        name = m.group("name")
        filename = f"{name}.md"
        category = m.group("category").strip()
        categories = [c.strip() for c in category.split(",") if c.strip()]
        original_count += 1

        if filename not in md_files:
            print(f"  警告: 未找到 '{name}' 的本地文件")
            result_lines.append(line)
            continue

        paths = md_files[filename]
        if len(paths) == 1:
            local_path = paths[0].replace(" ", "%20")
        else:
            # 同名接口消歧：根据分类字段匹配正确的本地路径
            matched = None
            for p in paths:
                # 路径中的目录层级应包含分类关键字
                path_cats = [c for c in p.split(os.sep)[:-1]]
                if all(c in path_cats for c in categories):
                    matched = p
                    break
            if matched:
                local_path = matched.replace(" ", "%20")
            else:
                print(f"  警告: '{name}' 无法消歧，使用第一个: {paths[0]}")
                local_path = paths[0].replace(" ", "%20")

        # 只替换链接部分
        new_line = re.sub(
            r'\[([^\]]+)\]\(https://tushare\.pro/wctapi/documents/\d+\.md\)',
            f'[{name}]({local_path})',
            line
        )
        result_lines.append(new_line)
        replaced += 1

    print(f"  替换: {replaced}/{original_count} 个在线链接")
    return "\n".join(result_lines)


def main():
    if not os.path.exists(INDEX_FILE):
        print(f"错误: 找不到 {INDEX_FILE}")
        return

    print("扫描本地 md 文件...")
    md_files = scan_md_files()
    total_files = sum(len(v) for v in md_files.values())
    print(f"  找到 {total_files} 个 md 文件")

    print("读取 remote_index.md...")
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    print("替换链接...")
    new_content = replace_links(content, md_files)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"已生成 {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
