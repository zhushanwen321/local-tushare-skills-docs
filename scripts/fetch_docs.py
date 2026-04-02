#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 Tushare 官网爬取全部 API 接口文档，按分类目录组织保存。

用法:
    python fetch_docs.py            # 下载全部文档（跳过已存在）
    python fetch_docs.py --force    # 强制重新下载
    python fetch_docs.py --dry-run  # 只打印计划不实际下载
"""

import argparse
import os
import re
import sys
import time
import ssl
import urllib.request
import urllib.error

# macOS Python 经常缺根证书，跳过验证
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# 相对路径计算
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
INDEX_FILE = os.path.join(DOCS_DIR, "remote_index.md")
DOC_URL_TEMPLATE = "https://tushare.pro/wctapi/documents/{}.md"
REQUEST_DELAY = 0
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30

# 解析 Markdown 表格行
ROW_PATTERN = re.compile(
    r"\|\s*\[(?P<name>[^\]]+)\]\((?P<url>[^)]+)\)\s*"
    r"\|\s*(?P<title>[^|]+)\s*"
    r"\|\s*(?P<category>[^|]+)\s*"
    r"\|"
)
DOC_ID_PATTERN = re.compile(r"/(\d+)\.md$")


def parse_index(filepath: str) -> list[dict]:
    """解析 remote_index.md，返回接口列表。"""
    entries = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            m = ROW_PATTERN.search(line)
            if not m:
                continue
            url = m.group("url")
            id_match = DOC_ID_PATTERN.search(url)
            if not id_match:
                continue
            raw_cat = m.group("category").strip()
            categories = [c.strip() for c in raw_cat.split(",") if c.strip()]
            entries.append({
                "name": m.group("name").strip(),
                "doc_id": id_match.group(1),
                "title": m.group("title").strip(),
                "categories": categories,
                "url": url,
            })
    return entries


def fetch_document(doc_id: str) -> str | None:
    """下载单个文档，返回 Markdown 内容。失败返回 None。"""
    url = DOC_URL_TEMPLATE.format(doc_id)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; TushareDocFetcher/1.0)"},
    )
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=SSL_CTX) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            wait = 2 ** attempt
            print(f"  [重试 {attempt}/{MAX_RETRIES}] {e}，{wait}s 后重试...")
            time.sleep(wait)
    return None


def build_output_path(categories: list[str], name: str) -> str:
    """根据分类和接口名构建输出文件路径。"""
    parts = [DOCS_DIR] + categories + [f"{name}.md"]
    return os.path.join(*parts)


def main():
    parser = argparse.ArgumentParser(description="爬取 Tushare API 文档")
    parser.add_argument("--force", action="store_true", help="强制重新下载已存在的文件")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划不实际下载")
    args = parser.parse_args()

    if not os.path.exists(INDEX_FILE):
        print(f"错误: 找不到 {INDEX_FILE}，请先运行 update_docs.sh")
        sys.exit(1)

    entries = parse_index(INDEX_FILE)
    print(f"共解析到 {len(entries)} 个接口文档\n")

    if args.dry_run:
        for i, entry in enumerate(entries, 1):
            path = build_output_path(entry["categories"], entry["name"])
            rel_path = os.path.relpath(path, DOCS_DIR)
            exists = " (已存在)" if os.path.exists(path) else ""
            print(f"  [{i}/{len(entries)}] {entry['name']} -> {rel_path}{exists}")
        return

    failed = []
    skipped = 0

    for i, entry in enumerate(entries, 1):
        out_path = build_output_path(entry["categories"], entry["name"])
        rel_path = os.path.relpath(out_path, DOCS_DIR)

        if not args.force and os.path.exists(out_path):
            skipped += 1
            continue

        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        print(f"  [{i}/{len(entries)}] 正在获取 {entry['name']} -> {rel_path}")
        content = fetch_document(entry["doc_id"])

        if content is None:
            failed.append(entry)
            print(f"  x 获取失败: {entry['name']} ({entry['url']})")
        else:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)

        if i < len(entries):
            time.sleep(REQUEST_DELAY)

    total = len(entries)
    success = total - len(failed) - skipped
    print(f"\n完成: 成功 {success}, 跳过 {skipped}, 失败 {len(failed)}/{total}")

    if failed:
        print("\n失败列表:")
        for entry in failed:
            print(f"  - {entry['name']} ({entry['url']})")
        sys.exit(1)


if __name__ == "__main__":
    main()
