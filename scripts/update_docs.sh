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
