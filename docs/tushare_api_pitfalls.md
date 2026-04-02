# Tushare API 使用经验与踩坑记录

**最后更新**: 2026-04-02
**适用范围**: 所有使用 Tushare API 的开发场景

本文档汇总了项目开发过程中遇到的 Tushare API 问题及解决方案，帮助后续开发避免同类陷阱。

---

## 1. 字段名问题

Tushare API 的字段命名存在**跨接口不一致**的情况，这是最常见的数据丢失原因。

### 1.1 同一概念在不同接口中使用不同字段名

| 概念 | 接口 A | 字段名 A | 接口 B | 字段名 B |
|------|--------|---------|--------|---------|
| 涨跌幅 | `daily` | `pct_chg` | `top_list` | `pct_change` |
| 股票代码 | 大多数接口 | `ts_code` | `top_list` | `ts_code` |
| 股票名称 | 大多数接口 | `name` | 部分接口 | `name` |

**规则**: 添加新接口时，必须查阅该接口的官方文档确认字段名，不要从其他接口推断。

### 1.2 `fields` 参数的严格行为

Tushare 的 `fields` 参数行为严格：

- **只返回 `fields` 中指定的列**，未指定的列不会出现在 DataFrame 中
- **不会报错**：如果 `fields` 中包含不存在的字段名，Tushare 静默忽略，不返回该列也不报错
- **大小写敏感**：字段名的大小写必须与文档一致

**典型错误**：`TOP_LIST` 的 `fields` 漏写了 `trade_date`，导致返回数据中没有日期字段，后续处理全部跳过，最终写入 0 条记录。

**调试方法**：当 API 返回数据但写入为 0 时，首先检查 DataFrame 的列名列表是否包含预期字段。

### 1.3 必须包含的关键字段

每个接口都有关键的标识字段，缺少这些字段会导致数据无法关联：

| 接口 | 必须包含的字段 | 用途 |
|------|---------------|------|
| `daily` | `ts_code`, `trade_date` | 股票-日期联合主键 |
| `top_list` | `trade_date`, `ts_code` | 日期 + 股票代码 |
| `moneyflow` | `ts_code`, `trade_date` | 股票-日期联合主键 |
| `balancesheet` | `ts_code`, `end_date` | 股票-报告期 |
| `income` | `ts_code`, `end_date` | 股票-报告期 |

---

## 2. 静默失败模式

Tushare API 最大的陷阱是**静默失败** -- 不报错但返回空数据。

### 2.1 空数据不代表无数据

Tushare 返回空 DataFrame (`df.empty`) 可能有以下原因：

| 原因 | 特征 | 排查方式 |
|------|------|---------|
| **确实无数据** | 日期非交易日、代码不存在 | 检查日期是否为交易日 |
| **字段名错误** | `fields` 中有不存在的字段 | 对比 API 文档检查每个字段 |
| **权限不足** | 日志中有 "权限不足" 关键字 | 检查积分/权限 |
| **频率限制** | 日志中有 "每分钟最多访问" | 检查速率限制配置 |

**关键规则**: 不要假设空数据就是"没有数据"，要排除字段名错误的可能性。

### 2.2 默认输出字段 vs 可选字段

Tushare 文档中的字段分为"默认输出"和"可选输出"：

- **默认输出字段**：不传 `fields` 参数时也会返回
- **可选输出字段**：必须在 `fields` 中明确指定才会返回

**问题**: 如果在 `fields` 中只写了可选字段而漏掉了默认字段，默认字段也不会返回。

**最佳实践**: 在 `_TushareFields` 中定义字段时，始终包含接口文档中的所有默认输出字段，即使它们看起来"理所当然应该有"。

---

## 3. 速率限制与错误处理

### 3.1 跨进程共享限流

项目使用 `SharedRateLimiter` 实现跨进程限流（详见 memory 中的"统一跨进程限流器"条目）。

**关键配置**：

| 原则 | 说明 |
|------|------|
| 80% 安全余量 | 如果 Tushare 限制 300次/分钟，配置为 240次/分钟 |
| 按接口独立限流 | 不同接口有不同的频率限制 |
| 跨进程共享 | 所有子进程 + 主进程共享同一个限流状态 |

### 3.2 可重试 vs 不可重试错误

`TushareClient._retry_on_error()` 区分两类错误：

**可重试（网络错误）**：
```python
_RETRYABLE_NETWORK_ERRORS = frozenset({
    "ConnectionError", "Timeout", "NameResolutionError",
    "MaxRetryError", "HTTPError", "SSLError",
})
```

**不可重试（业务错误）**：
```python
_NON_RETRYABLE_ERRORS = frozenset({
    "抱歉，您每分钟最多访问",  # 频率限制
    "抱歉，您每天最多访问",    # 日限额
    "您的积分不足",            # 积分不足
    "token无效",               # token 过期
    "您的权限不足",            # 权限不足
    "没有访问该接口的权限",    # 接口权限
})
```

**设计原则**: 频率限制错误不应重试（等待不会改变结果），而应通过限流器在请求前排队解决。

---

## 4. 数据源降级策略

### 4.1 DefaultDataSource 模式

项目使用 `DefaultDataSource` 实现 Tushare -> Akshare -> 空列表的降级链：

```python
# 伪代码
async def get_top_list(trade_date: str):
    # 1. 尝试 Tushare
    records = await tushare_client.get_top_list(trade_date)
    if records:
        return records

    # 2. Tushare 返回空，降级到 Akshare
    logger.info("Tushare top list returned empty, falling back to Akshare")
    records = await akshare_client.get_top_list_em(trade_date)
    if records:
        return records

    # 3. 两个源都无数据
    return []
```

### 4.2 降级日志的关键信息

当看到 "falling back to Akshare" 日志时，**不一定代表 Tushare 故障**，可能的原因：

1. Tushare 的 `fields` 参数有问题（字段名错误）
2. 确实该日期无数据（非交易日等）
3. Tushare API 权限不足
4. Akshare 的字段映射有遗漏

**排查顺序**: 先用调试脚本直接调用 Tushare API 确认数据是否存在，再检查字段名和映射逻辑。

---

## 5. 添加新接口的检查清单

当需要在 `TushareClient` 中添加新的 Tushare API 封装时，按以下步骤操作：

### Step 1: 查阅官方文档

- 确认字段名列表（特别注意默认输出 vs 可选输出）
- 确认积分要求和权限要求
- 确认输入参数格式（日期格式、代码格式等）
- 文档位置：`/Users/zhushanwen/Documents/api-docs/tushare/` 或 Tushare 官网

### Step 2: 在 `_TushareFields` 中添加字段常量

```python
class _TushareFields:
    # 必须包含所有默认输出字段 + 需要的可选字段
    NEW_API = "field1,field2,trade_date,ts_code,..."
```

**检查项**:
- [ ] `trade_date` 或日期字段是否包含
- [ ] `ts_code` 或标识字段是否包含
- [ ] 字段名是否与该接口的文档一致（不要从其他接口复制）

### Step 3: 添加方法

```python
async def get_new_api(self, ...) -> list[dict[str, Any]]:
    params = self._build_params(
        {"fields": _TushareFields.NEW_API},
        # 其他参数...
    )
    return await self._call_api(self.pro.new_api, "new_api", **params)
```

### Step 4: 处理字段映射

如果 API 返回的字段名与项目内部命名不同，需要映射：

```python
# ts_code -> stock_code 由 _df_to_records 自动处理
# 其他映射在方法返回前手动处理
records = await self._call_api(...)
return [{**r, "stock_name": r.pop("name", None)} for r in records]
```

### Step 5: 配置速率限制

在 `backend/config/api-rate-limits.yaml` 中添加新接口的限流配置。

### Step 6: 调试验证

编写调试脚本直接调用 Tushare API 验证：

```python
import tushare as ts
ts.set_token("your_token")
pro = ts.pro_api()

# 测试 API 是否正常返回
df = pro.top_list(trade_date="20240301")
print(df.columns.tolist())  # 确认返回的列名
print(len(df))               # 确认有数据
```

---

## 6. 历史问题索引

| 日期 | 问题 | 影响 | 修复 |
|------|------|------|------|
| 2026-04-02 | `top_list` 的 `fields` 缺少 `trade_date`，字段名 `pct_chg` 应为 `pct_change` | 龙虎榜数据全部丢失，任务写入 0 条 | 补充 `trade_date`，修正 `pct_change` |
| 2026-04-02 | Akshare 降级字段映射缺少 `trade_date` | Tushare 失败后 Akshare 数据也无法写入 | 补充字段映射 |
| 2026-04-02 | Akshare `_safe_fetch_lhb` 只捕获 `TypeError` | 其他异常触发无效重试 | 改为捕获 `Exception` |
| 2026-03-25 | 跨进程限流器 `id()` 日志误导 | 误判为多次初始化 | 理解 `id()` 在跨进程中的行为 |
| 2026-03-19 | 速率限制配置无安全余量 | 频繁触发 Tushare 限流 | 采用 80% 安全余量策略 |

