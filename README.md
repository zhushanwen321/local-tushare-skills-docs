# Tushare API 开发指导 Skill

Tushare Pro API 的完整本地文档库 + 开发指导 skill。帮助开发者选对接口、写对代码、避开陷阱。
支持通过脚本自动拉取官网文档更新

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
├── SKILL.md                     # Claude Code skill 入口（API 开发指导）
├── docs/                        # 完整的 tushare API 文档（230+ 个接口）
│   ├── remote_index.md          # 在线链接索引（接口总表）
│   ├── local_index.md           # 本地链接索引
│   ├── tushare_api_pitfalls.md  # API 使用经验与踩坑记录
│   └── */                       # 按分类存放的接口文档（15 个分类目录）
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

## 与官网 Skill 的关系

本项目是**开发指导** skill，帮助你选对接口、写对代码、避开陷阱。

如果你使用 OpenClaw、Trae 等智能体，需要让 AI **直接执行** tushare API 调用获取数据，请安装官网的数据操作 skill：

```bash
npx skills add https://github.com/waditu-tushare/skills.git --skill tushare-data
```

官网 skill 仓库：[waditu-tushare/skills](https://github.com/waditu-tushare/skills)

两个 skill 互补：官网 skill 负责「执行数据获取」，本 skill 负责「指导 API 开发」。

## 技术说明

- 所有脚本零外部依赖，仅使用 Python 标准库
- 文档来源：tushare.pro 官方 API 文档
- 索引来源：[waditu-tushare/skills](https://github.com/waditu-tushare/skills) 仓库
