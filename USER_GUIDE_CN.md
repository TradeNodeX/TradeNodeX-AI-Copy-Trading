# TradeNodeX 中文使用指南

本指南面向第一次使用 TradeNodeX 的用户。目标是帮助你完成从添加 API、添加信号、创建跟单路由，到查看日志和执行结果的完整流程。

## 1. 核心对象

- `Signal Source`：主账户信号源。系统监听主账户真实成交、订单或仓位变化，并转换为标准信号。
- `Follower API Account`：子账户 API。子账户不产生信号，只接收执行任务并下单。
- `Copy Trade`：信号源到子账户的跟单路由。这里决定是否启用 1:1 精确复制或按比例复制。
- `Execution Task`：系统为每个 follower 生成的真实执行任务。每个任务都有 attempt、response、error 和时间线。

## 2. 启动系统

启动 API：

```bash
uvicorn copytrading_app.main:app --reload
```

启动 worker、主账户监听和后台执行：

```bash
python -m copytrading_app.workers.runtime
```

打开界面：

- 主界面：[http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- 回退界面：[http://127.0.0.1:8000/legacy](http://127.0.0.1:8000/legacy)

注意：网页只是控制台。自动监听、队列消费和真实执行依赖后台 worker 运行。

## 3. 第一次使用流程

### 第一步：添加主账户信号源

进入 `Signals` 或 `API Registry`，点击 `Add Signal`。

需要填写：

- Name
- Exchange
- Environment
- Pairs Scope
- Default Copy Mode
- Default Leverage
- Margin Mode
- API Key
- API Secret
- API Passphrase（仅部分交易所需要，例如 OKX）

`Pairs Scope` 可以填 `ALL`，表示不限制交易对。也可以填白名单，例如 `BTCUSDT,ETHUSDT`，系统只处理白名单内的交易对。

### 第二步：校验主账户

保存后点击 `Validate`。校验会检查：

- 凭证是否正确
- 权限是否可用
- 网络连接是否正常
- 环境、杠杆、保证金模式、持仓模式是否满足跟单要求

### 第三步：添加子账户 API

进入 `API Registry`，点击 `Add API Account`。

需要填写：

- Name
- Exchange
- Environment
- Leverage
- Margin Mode
- API Key
- API Secret
- API Passphrase（仅部分交易所需要）

保存后点击 `Validate`。

### 第四步：创建跟单路由

进入 `Copy Routing`，创建或编辑路由。

需要配置：

- Signal Source
- Follower
- Copy Mode
- Scale Factor
- Override Leverage
- Execution Template
- Operator Notes
- Enabled

如果你要 1:1 精确复制：

- `Copy Mode = EXACT`
- `Scale Factor = 1`

如果要按比例：

- `Copy Mode = SCALE`
- `Scale Factor = 0.5 / 2 / 3` 等

### 第五步：开始跟单

当以下条件都满足时，系统可以进入自动跟单：

- 主账户信号源为 active
- follower 为 active
- copy trade 已启用
- worker 正在运行
- API 校验通过
- 交易对在白名单范围内，或 Pairs Scope 为 `ALL`

此后你可以在主账户对应交易所下单。系统会自动识别主账户仓位变化，生成 signal，扇出到 follower，并写入审计日志。

## 4. 信号如何生成

系统通过主账户私有流和 REST 对账识别仓位变化。核心判断来自：

- previous position quantity
- current position quantity

系统会自动归类为：

- `OPEN`
- `INCREASE`
- `REDUCE`
- `CLOSE`
- `FLIP`
- `SYNC_TO_TARGET_POSITION`

示例：

- `0 -> 1` 通常是 `OPEN`
- `1 -> 2` 通常是 `INCREASE`
- `2 -> 1` 通常是 `REDUCE`
- `1 -> 0` 通常是 `CLOSE`
- `1 -> -1` 通常是 `FLIP`

## 5. 跟单如何执行

信号生成后：

1. 系统找到该 source 下所有 active copy trades
2. 为每个 follower 生成 execution task
3. 不同账户并行执行
4. 同一账户同一 symbol 串行执行
5. 每次执行都记录 attempt、exchange response、error 和 timeline

所以 200 个账户不是严格一个接一个执行，而是账户间并发、账户内按交易对串行。

## 6. 查看结果

### Audit Logs

查看 signal、execution、warning、error、manual、reconcile 相关日志。

重点字段：

- Timestamp
- Exchange
- Type
- Key
- PnL
- Message

### Live Execution Queue

在 `Studio` 页面查看最近执行任务：

- signal
- follower
- symbol
- status
- exchange stage
- latency

点击任务可以查看执行审计详情。

### Execution Audit Drawer

查看：

- attempt 明细
- exchange response
- error
- signal -> task -> response 链路

### Equity List

查看最近仓位快照和权益分析：

- unrealized pnl
- exposure / notional
- leverage
- margin mode
- freshness

## 7. 多交易所支持

| Exchange | API 校验 | 手动执行/撤单/查仓 | 主账户自动监听 | 说明 |
| --- | --- | --- | --- | --- |
| Binance Futures | 支持 | 支持 | 支持 | 成熟路径 |
| Bybit Linear | 支持 | 支持 | 支持 | 成熟路径 |
| OKX Swap | 支持 | 支持 | 支持 | 需要 passphrase |
| Kraken Futures | 支持 | 支持 | 支持 | 私有流优先，REST 对账兜底 |
| BitMEX | 支持 | 支持 | 支持 | 私有流优先，REST 对账兜底 |
| Gate.io Futures | 支持 | 支持 | 支持 | 私有流优先，REST 对账兜底 |
| Coinbase Advanced | 支持 | 支持 | 支持 | 需要正确密钥格式 |

## 8. 常见问题

### 添加 signal 后为什么没有自动跟单？

常见原因：

- worker 没启动
- 主账户 API 未校验通过
- follower API 未校验通过
- copy trade 未创建或未启用
- 主账户没有发生仓位变化
- 交易对不在 Pairs Scope 白名单内
- 交易所权限、IP 白名单或环境选择不一致

### 交易对可以填 ALL 吗？

可以。`ALL` 表示不限制交易对。但上线前建议确认 follower 对应交易所也支持相同交易对、合约类型、最小下单量和精度。

### 1:1 精确复制为什么仍可能有差异？

即使设置 `EXACT + Scale Factor = 1`，交易所仍可能因为以下限制产生差异：

- 最小下单量
- 最小名义价值
- 精度截断
- 杠杆或保证金模式不一致
- 余额不足
- 交易所拒单

### 只打开网页是否会自动执行？

不会。网页只是控制台。必须启动后台 worker。

## 9. 风险提示

- 不要开启提现权限
- 建议配置 IP 白名单
- 不要一开始就大仓位实盘
- 先用测试网或 demo 环境验证
- 再用主网小仓位验证
- 先接 1 到 2 个 follower，再逐步扩容

推荐上线顺序：

1. 测试网或 demo
2. 主网小仓位
3. 1 到 2 个 follower 灰度
4. 5 到 10 个 follower
5. 30、88、120、200 分批扩容

## 10. 最短操作清单

1. 启动 API
2. 启动 worker
3. 打开网页
4. Add Signal
5. 填主账户 API
6. Validate
7. Add API Account
8. 填 follower API
9. Validate
10. 创建 Copy Trade
11. 设置 `EXACT + Scale Factor = 1`
12. 保存并启用
13. 到主账户交易所下单
14. 在 `Audit Logs` 和 `Studio` 查看执行结果

完成以上步骤，并且日志、执行队列、仓位快照都能对上，说明主链路已经打通。
