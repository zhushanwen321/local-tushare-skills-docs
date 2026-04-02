# Tushare 本地文档与 Skills 项目设计

## 目标

在 `local-tushare-skills-docs` 仓库中构建三个子系统：

1. **docs/**：完整的 tushare API 本地文档，具备一键自动更新能力
2. **scripts/**：爬取和更新 docs 的脚本
3. **skills/**：Claude Code skill，用于快速查询 tushare 接口文档

## 项目上下文

- 已有爬取成果位于 `/Users/zhushanwen/Documents/api-docs/tushare/`，包含 228 个 md 文档和爬取脚本
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

### update_docs.sh — 一键更新流程

```
1. curl 下载 GitHub raw URL 的 数据接口.md → docs/remote_index.md
2. python3 scripts/fetch_docs.py
   - 解析 docs/remote_index.md 表格
   - 按分类创建目录，下载文档到 docs/ 下
   - 默认跳过已存在文件，--force 强制覆盖
3. python3 scripts/generate_index.py
   - 扫描 docs/ 下所有 .md（排除 remote_index.md、local_index.md）
   - 读取 remote_index.md，将在线链接替换为本地相对路径
   - 输出 docs/local_index.md
4. 打印统计：新增/跳过/失败
```

### fetch_docs.py — 文档爬取

从已有 `fetch_docs.py` 适配：
- `BASE_DIR` 指向 `docs/` 目录（相对于项目根）
- `INDEX_FILE` 指向 `docs/remote_index.md`
- 保留原有特性：零依赖、重试机制（3次递增间隔）、幂等性（默认跳过已存在）、`--force`/`--dry-run` 参数

### generate_index.py — 索引生成

从已有 `generate_local_index.py` 适配：
- `BASE_DIR` 指向 `docs/` 目录
- 输入：`docs/remote_index.md`
- 输出：`docs/local_index.md`
- 扫描范围限定在 `docs/` 目录下

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
