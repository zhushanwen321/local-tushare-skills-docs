# Tushare 本地文档与 Skills 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建完整的 tushare API 本地文档系统、一键更新脚本、以及 Claude Code 文档查询 skill。

**Architecture:** 三个子系统协作：scripts/ 负责从 GitHub 拉取索引并爬取文档到 docs/，skills/ 提供 LLM 可用的文档查询能力。所有脚本零外部依赖，路径通过 `os.path` 相对计算。

**Tech Stack:** Python 3 (标准库 urllib/ssl/os/re/time/argparse), Bash, Markdown

**Spec:** `docs/superpowers/specs/2026-04-02-tushare-local-docs-skills-design.md`

---

## 文件结构

| 操作 | 文件路径 | 职责 |
|------|---------|------|
| 创建 | `scripts/fetch_docs.py` | 解析 remote_index.md，按分类爬取文档到 docs/ |
| 创建 | `scripts/generate_index.py` | 扫描 docs/ 下文档，生成 local_index.md |
| 创建 | `scripts/update_docs.sh` | 一键更新入口：下载索引 → 爬取 → 生成索引 |
| 创建 | `skills/tushare-doc-query.md` | Claude Code skill：文档查询 |
| 复制 | `docs/` 下 228 个 md 文件 | 从 `/Users/zhushanwen/Documents/api-docs/tushare/` 复制已爬取文档 |
| 复制 | `docs/tushare_api_pitfalls.md` | 从 `stock-data-crawler` 项目复制使用经验文档 |
| 修改 | `README.md` | 更新项目说明 |

---

### Task 1: 创建 fetch_docs.py

**Files:**
- 创建: `scripts/fetch_docs.py`
- 参考: `/Users/zhushanwen/Documents/api-docs/tushare/fetch_docs.py`

- [ ] **Step 1: 创建 scripts 目录并编写 fetch_docs.py**

基于已有脚本适配。核心改动是将硬编码的 `BASE_DIR` 改为相对路径计算。

```python
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
```

- [ ] **Step 2: 验证脚本可运行**

```bash
cd /Users/zhushanwen/Code/local-tushare-skills-docs
python3 scripts/fetch_docs.py --help
```

预期：输出帮助信息，无报错。

- [ ] **Step 3: 提交**

```bash
git add scripts/fetch_docs.py
git commit -m "feat: 添加 fetch_docs.py 文档爬取脚本"
```

---

### Task 2: 创建 generate_index.py

**Files:**
- 创建: `scripts/generate_index.py`
- 参考: `/Users/zhushanwen/Documents/api-docs/tushare/generate_local_index.py`

- [ ] **Step 1: 编写 generate_index.py**

基于已有脚本适配，核心改动：相对路径、同名接口处理。

```python
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
    for root, dirs, files in os.walk(DOCS_DIR):
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
        r'\| (?P<before>[^|]*) \[(?P<name>[^\]]+)\]\(https://tushare\.pro/wctapi/documents/\d+\.md\) (?P<after>[^|]*\|[^|]*\|(?P<category>[^|]*))\|'
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
```

- [ ] **Step 2: 提交**

```bash
git add scripts/generate_index.py
git commit -m "feat: 添加 generate_index.py 本地索引生成脚本"
```

---

### Task 3: 创建 update_docs.sh

**Files:**
- 创建: `scripts/update_docs.sh`

- [ ] **Step 1: 编写 update_docs.sh**

```bash
#!/bin/bash
set -uo pipefail
# 注意：不用 -e，因为 fetch_docs.py 失败时仍需继续生成 local_index

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCS_DIR="$PROJECT_ROOT/docs"

REMOTE_INDEX_URL="https://raw.githubusercontent.com/waditu-tushare/skills/master/tushare-data/references/%E6%95%B0%E6%8D%AE%E6%8E%A5%E5%8F%A3.md"

echo "=== Tushare 文档更新 ==="
echo ""

# 步骤 1：下载索引
echo "[1/3] 下载 remote_index.md ..."
mkdir -p "$DOCS_DIR"
if ! curl -fSL "$REMOTE_INDEX_URL" -o "$DOCS_DIR/remote_index.md" 2>/dev/null; then
    echo "错误: 下载索引失败，请检查网络连接"
    exit 1
fi
echo "  完成"
echo ""

# 步骤 2：爬取文档
echo "[2/3] 爬取文档 ..."
FETCH_EXIT=0
python3 "$SCRIPT_DIR/fetch_docs.py" "$@" || FETCH_EXIT=$?
echo ""

# 步骤 3：生成 local_index.md
echo "[3/3] 生成 local_index.md ..."
python3 "$SCRIPT_DIR/generate_index.py"
echo ""

echo "=== 更新完成 ==="
exit $FETCH_EXIT
```

- [ ] **Step 2: 设置可执行权限**

```bash
chmod +x scripts/update_docs.sh
```

- [ ] **Step 3: 提交**

```bash
git add scripts/update_docs.sh
git commit -m "feat: 添加 update_docs.sh 一键更新脚本"
```

---

### Task 4: 复制已有文档到 docs/

**Files:**
- 复制: 从 `/Users/zhushanwen/Documents/api-docs/tushare/` 到 `docs/`

- [ ] **Step 1: 复制所有分类目录和 md 文件**

```bash
# 复制所有分类目录（排除脚本、索引文件、缓存）
cd /Users/zhushanwen/Code/local-tushare-skills-docs
SOURCE="/Users/zhushanwen/Documents/api-docs/tushare"

for dir in ETF专题 债券专题 股票数据 宏观经济 指数专题 期货数据 期权数据 港股数据 美股数据 外汇数据 现货数据 公募基金 大模型语料专题数据 行业经济 财富管理; do
    if [ -d "$SOURCE/$dir" ]; then
        cp -r "$SOURCE/$dir" docs/
        echo "  复制: $dir"
    fi
done
```

- [ ] **Step 2: 下载 remote_index.md**

```bash
curl -fSL "https://raw.githubusercontent.com/waditu-tushare/skills/master/tushare-data/references/%E6%95%B0%E6%8D%AE%E6%8E%A5%E5%8F%A3.md" -o docs/remote_index.md
```

- [ ] **Step 3: 生成 local_index.md**

```bash
python3 scripts/generate_index.py
```

预期：输出替换统计，生成 `docs/local_index.md`。

- [ ] **Step 4: 验证 local_index.md 的本地链接数量**

```bash
# 统计本地链接数（md 文件链接，排除 tushare.pro 在线链接）
python3 -c "
import re
with open('docs/local_index.md', 'r') as f:
    content = f.read()
online = len(re.findall(r'tushare\.pro/wctapi/documents', content))
local = len(re.findall(r'\]\([A-Za-z0-9_%\x20-\x7e\u4e00-\u9fff][^)]*\.md\)', content))
print(f'在线链接: {online}, 本地链接: {local}')
"
```

预期：在线链接接近 0，本地链接接近 200+。

- [ ] **Step 5: 提交**

```bash
git add docs/
git commit -m "docs: 添加 tushare API 完整本地文档和索引"
```

---

### Task 5: 复制 tushare 使用经验文档

**Files:**
- 复制: 从 `/Users/zhushanwen/Code/stock-data-crawler/.claude/worktrees/market-data-expansion/docs/tushare_api_pitfalls.md` 到 `docs/tushare_api_pitfalls.md`

- [ ] **Step 1: 复制并适配踩坑文档**

```bash
cp /Users/zhushanwen/Code/stock-data-crawler/.claude/worktrees/market-data-expansion/docs/tushare_api_pitfalls.md docs/tushare_api_pitfalls.md
```

需要适配的内容：
- 删除与特定项目代码相关的引用路径（如 `backend/app/infra/...`）
- 删除 "相关文档" 章节中指向特定项目文件的链接
- 保留所有通用的 API 使用经验和陷阱知识

- [ ] **Step 2: 提交**

```bash
git add docs/tushare_api_pitfalls.md
git commit -m "docs: 添加 tushare API 使用经验与踩坑记录"
```

---

### Task 6: 创建 tushare-doc-query skill

**Files:**
- 创建: `skills/tushare-doc-query.md`

- [ ] **Step 1: 编写 skill 文件**

```markdown
---
name: tushare-doc-query
description: 查询 tushare API 接口文档，包括入参、出参、调用方式。当用户询问 tushare 相关的数据接口、行情数据、财务数据、K线获取等问题时触发。
---

# Tushare 文档查询

当用户询问 tushare 数据接口、数据获取方式、API 用法时使用此 skill。

## 触发条件

用户问题涉及以下任一：
- 明确提到 "tushare"
- 询问如何获取某类金融数据（股票行情、财务报表、基金净值、期货数据等）
- 询问某个 tushare 接口的用法（如 daily、stock_basic、fina_indicator 等）

## 操作步骤

1. **读取索引**：读取 `docs/local_index.md`，获取完整接口列表（包含接口名、标题、分类、描述、本地文档路径）

2. **匹配接口**：根据用户问题中的关键词，在索引表中匹配相关接口：
   - 优先精确匹配接口名（如用户说 "daily" 则匹配 daily 接口）
   - 其次按标题和描述中的关键词模糊匹配
   - 如果匹配到多个接口，列出所有匹配项让用户选择

3. **读取文档**：读取匹配到的接口文档文件（路径来自 local_index.md 中的链接），提取：
   - 接口说明
   - 输入参数表（参数名、类型、必填、说明）
   - 输出参数表（字段名、类型、说明）
   - 调用示例代码（如有）

4. **返回结果**：以清晰的 Markdown 格式向用户展示接口信息

## API 使用注意事项

在返回接口文档信息时，必须提醒用户以下关键陷阱（详见 `docs/tushare_api_pitfalls.md`）：

### 字段名跨接口不一致
同一概念在不同接口中使用不同字段名（如涨跌幅在 `daily` 中是 `pct_chg`，在 `top_list` 中是 `pct_change`）。使用时必须查阅该接口文档确认字段名，不要从其他接口推断。

### fields 参数的严格行为
- `fields` 中未指定的列不会返回
- 不存在的字段名会被静默忽略，不报错也不返回
- 字段名大小写敏感
- 如果在 fields 中只写了可选字段而漏掉默认字段，默认字段也不会返回

### 静默失败模式
空 DataFrame 不一定代表"无数据"，可能原因：字段名错误、权限不足、频率限制。

### 必须包含的关键字段
每个接口有关键标识字段（如 `ts_code` + `trade_date`），缺少这些字段会导致数据无法关联。

### 速率限制
不同接口有不同的频率限制，建议预留 80% 安全余量（如限制 300次/分钟则配置为 240次/分钟）。

## 接口分类速查

| 分类 | 涵盖内容 |
|------|---------|
| 股票数据 | 基础数据、行情数据、财务数据、资金流向、两融、打板、特色数据 |
| 指数专题 | 指数基本信息、日线行情、成分权重、申万/中信行业分类 |
| 基金 | ETF专题、公募基金 |
| 债券专题 | 可转债、国债收益率、回购、大宗交易 |
| 期货数据 | 合约信息、日线行情、持仓排名、主力合约映射 |
| 期权数据 | 合约信息、日线行情、分钟行情 |
| 港股数据 | 基础信息、日线行情、财务数据 |
| 美股数据 | 基础信息、日线行情、财务数据 |
| 宏观经济 | GDP、CPI、PPI、利率、社融、货币供应量 |
| 其他 | 外汇、现货、行业经济、大模型语料、财富管理 |
```

- [ ] **Step 2: 提交**

```bash
git add skills/tushare-doc-query.md
git commit -m "feat: 添加 tushare-doc-query Claude Code skill"
```

---

### Task 7: 更新 README.md

**Files:**
- 修改: `README.md`

- [ ] **Step 1: 更新 README.md**

```markdown
# Tushare 本地文档与 Skills

Tushare Pro API 的完整本地文档库、自动更新脚本和 LLM 可用的查询 skill。

## 目录结构

- `docs/` — 完整的 tushare API 文档（228+ 个接口），按分类目录组织
  - `remote_index.md` — 在线链接索引
  - `local_index.md` — 本地链接索引
  - `tushare_api_pitfalls.md` — API 使用经验与踩坑记录
- `scripts/` — 文档爬取和更新脚本
  - `update_docs.sh` — 一键更新全部文档
- `skills/` — Claude Code skills
  - `tushare-doc-query.md` — 文档查询 skill

## 更新文档

```bash
# 一键更新（下载最新索引 → 爬取新增/变更文档 → 生成本地索引）
./scripts/update_docs.sh

# 强制重新下载全部文档
./scripts/update_docs.sh --force

# 仅查看计划，不实际下载
./scripts/update_docs.sh --dry-run
```

## 技术说明

- 所有脚本零外部依赖，仅使用 Python 标准库
- 文档来源：tushare.pro 官方 API 文档
- 索引来源：[waditu-tushare/skills](https://github.com/waditu-tushare/skills) 仓库
```

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: 更新项目 README"
```

---

### Task 8: 端到端验证

- [ ] **Step 1: 验证目录结构完整**

```bash
find docs/ -name "*.md" | wc -l
```

预期：230+ 个文件（228 个接口文档 + remote_index.md + local_index.md）。

- [ ] **Step 2: 验证 update_docs.sh 可正常运行**

```bash
./scripts/update_docs.sh
```

预期：下载索引成功，所有文档跳过（已存在），local_index.md 生成成功。

- [ ] **Step 3: 验证 local_index.md 中本地链接可用**

```bash
# 随机抽取 5 个本地链接检查文件是否存在
python3 -c "
import re, os
with open('docs/local_index.md', 'r') as f:
    content = f.read()
links = re.findall(r'\]\(([^)]*\.md)\)', content)
links = [l for l in links if not l.startswith('http')]
ok, missing = 0, 0
for link in links[:5]:
    path = os.path.join('docs', link.replace('%20', ' '))
    if os.path.isfile(path):
        print(f'OK: {link}')
        ok += 1
    else:
        print(f'MISSING: {link}')
        missing += 1
print(f'抽样 {ok+missing}: OK={ok}, MISSING={missing}')
"
```

预期：全部输出 OK。

- [ ] **Step 4: 最终提交（如有未提交的修改）**

```bash
git status
# 如有未提交的文件，提交它们
```
