---
name: tushare-doc-query
description: 指导开发者使用 Tushare API 进行开发。当用户需要用 tushare 获取数据、编写调用代码、排查 API 问题、选择合适接口时触发。提供接口选型、参数说明、代码生成、API 陷阱提醒和调试指导。也支持更新本地文档库。
user-invocable: true
---

# Tushare API 开发指导

帮开发者选对接口、写对代码、避开陷阱。

## 触发条件

- 用户说 "tushare"、"tushare-doc-query"、"/tushare-doc-query"
- 用户想用 tushare 获取某类数据（行情、财务、资金流、宏观等）
- 用户需要编写 tushare API 调用代码
- 用户遇到 tushare API 调用问题（空数据、报错、字段对不上等）
- 用户要求更新 tushare 文档

## 操作步骤

### 1. 理解开发需求

先搞清楚用户要做什么：
- 获取什么数据？（行情、财务、资金流、宏观...）
- 用在什么场景？（研究分析、数据管道、策略回测...）
- 使用什么语言/SDK？（Python tushare 包、HTTP REST API）

### 2. 选接口

读取 `docs/local_index.md`，根据需求匹配接口：
- 优先精确匹配接口名
- 其次按标题和描述模糊匹配
- 如果匹配到多个，说明每个接口的适用场景，帮用户选择
- 如果需求复杂，可能需要组合多个接口

**接口推荐思路**（不是硬性规则，具体以文档为准）：

| 需求 | 常用接口 |
|------|---------|
| 股票日线行情 | `daily`、`pro_bar`、`daily_basic` |
| 财务报表 | `income`、`balancesheet`、`cashflow`、`fina_indicator` |
| 资金流向 | `moneyflow`、`moneyflow_hsgt`、`hsgt_top10` |
| 指数数据 | `index_daily`、`index_basic`、`index_weight` |
| 板块/行业 | `sw_daily`、`ths_index`、`index_classify` |
| 宏观经济 | `cn_cpi`、`cn_ppi`、`cn_gdp`、`shibor` |

### 3. 给出接口文档

读取匹配到的接口文档文件（路径来自 local_index.md），整理为：
- **接口说明**：这个接口做什么、返回什么
- **必填参数**：哪些参数必须传
- **关键可选参数**：常用的可选参数
- **输出字段**：返回哪些列（区分默认输出和需 fields 指定的）
- **积分/权限要求**：是否需要高级权限
- **频率限制**：每分钟调用次数限制

### 4. 生成调用代码

根据用户的技术栈，给出可直接运行的代码片段。

Python SDK 示例模板：

```python
import tushare as ts

pro = ts.pro_api('your_token')

# 调用接口
df = pro.接口名(
    # 必填参数
    ts_code='600519.SH',
    # 日期参数
    start_date='20240101',
    end_date='20241231',
    # 指定返回字段（建议显式指定，避免遗漏）
    fields='ts_code,trade_date,open,high,low,close,vol'
)

print(df.shape)
print(df.head())
```

HTTP API 示例模板：

```python
import requests

url = "https://api.tushare.pro"
payload = {
    "api_name": "接口名",
    "token": "your_token",
    "params": {
        "ts_code": "600519.SH",
        "start_date": "20240101",
        "end_date": "20241231"
    },
    "fields": "ts_code,trade_date,open,high,low,close,vol"
}
resp = requests.post(url, json=payload)
data = resp.json()
```

### 5. 提醒 API 陷阱

在给出代码时，必须针对该接口提醒相关陷阱（完整列表见 `docs/tushare_api_pitfalls.md`）：

**字段名跨接口不一致**：同一概念在不同接口中字段名可能不同。必须查阅该接口文档确认字段名，不要从其他接口推断。

**fields 参数行为**：
- 未指定的列不会返回
- 不存在的字段名被静默忽略（不报错不返回）
- 漏掉默认字段时默认字段也不返回
- 字段名大小写敏感

**静默失败**：空 DataFrame 不一定是"无数据"，可能是字段名错误、权限不足、频率限制。

**分段拉取**：长区间数据不要一次全拉。建议日线按年/季度切片，财报按报告期切片，分钟数据按月切片。

**速率限制**：不同接口限制不同，预留 80% 安全余量（如限制 300次/分钟则用 240次/分钟）。

### 6. 帮助调试

当用户遇到 API 调用问题时，按以下顺序排查：

1. **空结果** → 检查字段名是否正确、日期是否为交易日、代码格式是否标准
2. **报错** → 区分是权限问题还是参数问题
3. **数据不完整** → 检查 fields 参数是否包含了需要的字段
4. **频率限制** → 检查是否超频，加入节流控制

调试命令：

```python
# 冒烟测试：确认环境和 token 正常
df = pro.trade_cal(exchange='SSE', start_date='20240101', end_date='20240110')
print(df)

# 确认接口返回的列名（排查字段名问题）
df = pro.接口名(ts_code='600519.SH', trade_date='20240102')
print(df.columns.tolist())  # 查看实际返回了哪些字段
print(df.dtypes)            # 查看字段类型
```

## 更新文档

当用户要求更新 tushare 文档时：

执行 `bash scripts/update_docs.sh`
- 自动：下载最新索引 → 爬取新增/变更文档 → 生成本地索引
- 加 `--force` 强制重新下载全部
- 加 `--dry-run` 仅查看计划

## 前置条件

使用 tushare API 需要：
1. 注册 tushare 账号获取 token：https://tushare.pro/register
2. 安装 Python SDK：`pip install tushare`
3. 设置 token：`ts.set_token('your_token')` 或 `export TUSHARE_TOKEN=your_token`

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
