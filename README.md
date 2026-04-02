# Tushare 本地文档与 Skills

Tushare Pro API 的完整本地文档库、自动更新脚本和 LLM 可用的查询 skill。

## 目录结构

- `docs/` — 完整的 tushare API 文档（230+ 个接口），按分类目录组织
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
