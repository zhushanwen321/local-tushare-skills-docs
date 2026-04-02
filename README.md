# Tushare 本地文档与 Skill

Tushare Pro API 的完整本地文档库、自动更新脚本，以及 LLM 可用的查询 skill。

## 安装为 Claude Code Skill

```bash
# 克隆仓库
git clone https://github.com/yourname/local-tushare-skills-docs.git

# 安装到 Claude Code skills 目录
cp -r local-tushare-skills-docs ~/.claude/skills/tushare-doc-query

# 验证安装
ls ~/.claude/skills/tushare-doc-query/SKILL.md
```

安装后，在 Claude Code 中即可通过 `/tushare-doc-query` 或直接提问 tushare 相关问题来触发。

## 目录结构

```
local-tushare-skills-docs/
├── SKILL.md                     # Claude Code skill 入口
├── docs/                        # 完整的 tushare API 文档（230+ 个接口）
│   ├── remote_index.md          # 在线链接索引（接口总表）
│   ├── local_index.md           # 本地链接索引
│   └── tushare_api_pitfalls.md  # API 使用经验与踩坑记录
├── scripts/
│   ├── update_docs.sh           # 一键更新入口
│   ├── fetch_docs.py            # 文档爬取
│   └── generate_index.py        # 本地索引生成
└── README.md
```

## 更新文档

```bash
cd ~/.claude/skills/tushare-doc-query

# 一键更新（下载最新索引 → 爬取新增/变更文档 → 生成本地索引）
./scripts/update_docs.sh

# 强制重新下载全部文档
./scripts/update_docs.sh --force

# 仅查看计划，不实际下载
./scripts/update_docs.sh --dry-run
```

也可以在 Claude Code 对话中直接说"更新 tushare 文档"来触发。

## 技术说明

- 所有脚本零外部依赖，仅使用 Python 标准库
- 文档来源：tushare.pro 官方 API 文档
- 索引来源：[waditu-tushare/skills](https://github.com/waditu-tushare/skills) 仓库
