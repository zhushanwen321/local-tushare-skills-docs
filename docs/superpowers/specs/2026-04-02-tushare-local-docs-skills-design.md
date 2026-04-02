# Tushare 本地文档与 Skills 项目设计

## 目标

在 `local-tushare-skills-docs` 仓库中构建三个子系统：

1. **docs/**：完整的 tushare API 本地文档，具备一键自动更新能力
2. **scripts/**：爬取和更新 docs 的脚本
3. **skills/**：Claude Code skill，用于快速查询 tushare 接口文档

## 项目上下文

- 已有爬取成果位于 `/Users/zhushanwen/Documents/api-docs/tushare/`，包含 228 个 API 接口文档（.md）和爬取脚本
- GitHub 数据源：`waditu-tushare/skills` 仓库的 `数据接口.md`，内容与本地 `index.md` 一致
- 已有脚本：`fetch_docs.py`（爬取）、`generate_local_index.py`（索引生成），均为零依赖 Python

## 目录结构

```
local-tushare-skills-docs/
├── README.md
├── docs/
│   ├── remote_index.md                # 在线链接索引（从 GitHub 获取）
│   ├── local_index.md                 # 本地链接索引（脚本生成）
│   ├── ETF专题/
│   │   ├── rt_min.md
│   │   └── ...
│   ├── 债券专题/
│   ├── 股票数据/
│   │   ├── 基础数据/
│   │   ├── 行情数据/
│   │   ├── 财务数据/
│   │   └── ...
│   ├── 宏观经济/
│   ├── 指数专题/
│   ├── 期货数据/
│   ├── 期权数据/
│   ├── 港股数据/
│   ├── 美股数据/
│   ├── 外汇数据/
│   ├── 现货数据/
│   ├── 公募基金/
│   ├── 大模型语料专题数据/
│   ├── 行业经济/
│   └── 财富管理/
├── scripts/
│   ├── fetch_docs.py                  # 爬取文档（从已有脚本适配）
│   ├── generate_index.py              # 生成本地索引（从已有脚本适配）
│   └── update_docs.sh                 # 一键更新入口
└── skills/
    └── tushare-doc-query.md           # Claude Code skill：文档查询
```

## Scripts 设计

### 数据源

- remote_index.md 来源：`https://raw.githubusercontent.com/waditu-tushare/skills/master/tushare-data/references/%E6%95%B0%E6%8D%AE%E6%8E%A5%E5%8F%A3.md`
- 每次 update_docs.sh 运行时从该 URL 覆盖下载

### update_docs.sh — 一键更新流程

```bash
#!/bin/bash
set -euo pipefail

# 步骤 1：下载索引（失败则中止）
curl -fSL "$REMOTE_INDEX_URL" -o docs/remote_index.md || { echo "下载索引失败"; exit 1; }

# 步骤 2：爬取文档（失败继续，汇总报告）
python3 scripts/fetch_docs.py

# 步骤 3：生成 local_index.md
python3 scripts/generate_index.py

# 步骤 4：打印统计
```

错误处理策略：步骤 1 失败则中止（没有索引无法继续）；步骤 2/3 失败不中止，但汇总报告。

### fetch_docs.py — 文档爬取

从已有 `fetch_docs.py` 适配，关键路径修改：

```python
# 路径计算（相对于脚本所在目录）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
INDEX_FILE = os.path.join(DOCS_DIR, "remote_index.md")
```

- 输出路径基于 `DOCS_DIR`：`DOCS_DIR/分类1/分类2/接口名.md`
- 保留原有特性：零依赖、重试机制（3次递增间隔）、幂等性（默认跳过已存在）、`--force`/`--dry-run` 参数

### generate_index.py — 索引生成

从已有 `generate_local_index.py` 适配，关键路径修改：

```python
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")
INDEX_FILE = os.path.join(DOCS_DIR, "remote_index.md")
OUTPUT_FILE = os.path.join(DOCS_DIR, "local_index.md")
```

同名接口处理：`index.md` 中存在同名接口（如 `index_daily`、`trade_cal`、`pro_bar`），原脚本的 flat dict `{文件名: 路径}` 会互相覆盖。适配时改为 `{文件名: [路径列表]}`，替换链接时根据分类字段匹配正确路径。

## Skills 设计

### tushare-doc-query — 文档查询 Skill

**类型**：Claude Code skill

**触发条件**：用户询问 tushare 接口、数据获取方式、API 用法等

**工作流程**：
1. 读取 `docs/local_index.md`，获取完整接口索引表
2. 根据用户问题关键词匹配相关接口（接口名、标题、分类、描述）
3. 读取匹配到的接口文档文件（如 `docs/股票数据/行情数据/daily.md`）
4. 向用户展示：接口说明、入参表、出参表、调用示例

**Skill 文件内容要点**：
- name: tushare-doc-query
- description: 查询 tushare API 接口文档
- 触发词指引：tushare、数据接口、行情、财务、K线等
- 操作步骤：读索引 → 匹配接口 → 读文档 → 展示

## 非目标

- 不做文档内容格式转换（tushare 服务端直接返回 Markdown）
- 不做增量更新检测（全量爬取，默认跳过已存在文件即可）
- 不做并发优化（串行爬取足够，200+ 文档量不大）
- Skills 不做代码生成或 API 调用执行，仅做文档查询
