# 从 MT5 启用实际下单的完整步骤

## ✅ 检查清单

### 第一部分：准备环境
- [ ] Python 后端正在运行
  ```
  检查: uvicorn 进程是否活跃
  终端: ps aux | grep uvicorn
  应显示: uvicorn api:app --host 0.0.0.0 --port 8000
  ```

- [ ] 币安 API 密钥已配置
  ```
  文件: .env
  应包含:
    BINANCE_API_KEY=<your_key>
    BINANCE_SECRET_KEY=<your_secret>
    EXECUTION_TOKEN=<your_token>
  ```

- [ ] 测试网络连接
  ```
  终端: curl http://127.0.0.1:8000/get_signal_logs
  应返回: JSON 日志列表
  ```

### 第二部分：更新 MT5 脚本

- [ ] 获取最新的 `BtcSignalTrader.mq5`
  ```
  文件位置: m:\stock\BtcSignalTrader.mq5
  版本: 1.04 或更高
  ```

- [ ] 在 MetaEditor 中打开脚本
  ```
  MT5 → Tools → MetaQuotes Language Editor
  → 打开 BtcSignalTrader.mq5
  ```

- [ ] 编译脚本
  ```
  按 Ctrl+F5 或 Compile
  应显示: 0 errors, 0 warnings
  编译结果: BtcSignalTrader.ex5
  ```

### 第三部分：配置交易参数

- [ ] 在 MT5 中加载 EA
  ```
  1. 打开 BTC/USDT 图表 (5分钟推荐)
  2. 右键图表 → Attach EA
  3. 选择 BtcSignalTrader
  4. 点击 OK
  ```

- [ ] 打开 EA 参数对话框
  ```
  双击图表上的 EA，或右键 → Edit EA
  应显示参数配置面板
  ```

- [ ] 配置关键参数
  ```
  📌 dry_run: 改为 0 (0=实际下单, 1=模拟)
  📌 trade_amount_usdt: 50-100 (建议从小开始)
  signal_check_interval_seconds: 300 (5分钟)
  ```

- [ ] 启用 EA
  ```
  确保开关在 ON 位置 (右上角)
  应显示: "Expert Advisor" 绿色指示
  ```

### 第四部分：验证实际交易

- [ ] 观察 MT5 日志
  ```
  MT5 → View → Logs (Ctrl+L)
  应看到 5 分钟后出现:
    "准备发送GET请求到: http://127.0.0.1:8000/...&dry_run=0"
    "从API获取到信号: [SELL]"
  ```

- [ ] 检查图表信号显示
  ```
  图表左上角应显示:
    当前BTC信号: SELL (或 BUY)
    最后更新: [时间戳]
  ```

- [ ] 查看后端日志
  ```
  后端终端输出应显示:
    [GET /get_btc_signal] DRY RUN 已禁用
    已在币安期货测试网下单
    orderId: 10632732861
  ```

- [ ] 验证币安测试网订单
  ```
  登录: https://testnet.binance.vision
  账户 → Futures → Orders
  应看到新创建的 SELL/BUY 订单
  ```

### 第五部分：审计和监控

- [ ] 查询最近的订单
  ```
  终端或 Postman:
    GET http://127.0.0.1:8000/audit/recent?limit=1
  应返回:
    {
      "count": 1,
      "results": [{audit_id, timestamp, symbol, order, ...}]
    }
  ```

- [ ] 查看特定订单详情
  ```
  从 audit/recent 获取 audit_id，然后:
    GET http://127.0.0.1:8000/audit/{audit_id}
  应返回完整的交易详情
  ```

- [ ] 检查审计日志文件
  ```
  文件: m:\stock\trade_audit.log
  应包含最近的交易记录 (JSON 格式)
  ```

---

## 🔧 故障排除

### 问题 1: EA 无法连接后端
```
症状: 日志显示 "ERROR" 或 "HTTP_ERROR"

检查:
1. 后端是否运行: http://127.0.0.1:8000/get_signal_logs
2. api_url 参数是否正确: "http://127.0.0.1:8000/get_btc_signal"
3. 防火墙是否阻止端口 8000

解决:
1. 确保 uvicorn 在后台运行
2. 检查网络连接
3. 在本地测试 API: curl 命令
```

### 问题 2: 订单显示为模拟 (DRY RUN)
```
症状: 日志显示 "DRY RUN - 已模拟..."，无 orderId

原因: dry_run 参数未改为 0

检查:
1. EA 参数中 dry_run 是否为 0
2. 后端日志是否显示 "dry_run=0"

解决:
1. 修改 EA 参数: dry_run = 0
2. 重新加载 EA (右键 → Unload/Load)
3. 再次观察日志
```

### 问题 3: 未收到信号
```
症状: 5 分钟后图表仍无信号显示

原因: 可能是定时器未触发或 API 请求超时

检查:
1. EA 是否真的在运行 (图表右上角绿标)
2. 日志中是否有 "定时器触发" 的消息
3. signal_check_interval_seconds 是否过长

解决:
1. 手动重新加载 EA
2. 缩短检查间隔 (改为 60 秒测试)
3. 检查后端日志是否有错误
```

### 问题 4: 币安测试网未收到订单
```
症状: orderId 显示在日志中，但币安测试网无订单

原因: 可能是账户权限或测试网连接问题

检查:
1. orderId 是否为有效数字 (不是 null/undefined)
2. 币安测试网账户是否有期货权限
3. 后端是否连接到正确的测试网 (testnet=True)

解决:
1. 登录币安测试网: https://testnet.binance.vision
2. 确保账户状态正常
3. 检查币安 API 权限: 需要 TRADE 权限
```

---

## 📊 性能优化建议

### 调整检查间隔
```
当前: signal_check_interval_seconds = 300 (5分钟)

根据需要调整:
- 60 秒: 频繁交易（风险高）
- 300 秒: 稳定交易（推荐）
- 900 秒: 低频交易（风险低）
```

### 调整交易金额
```
当前: trade_amount_usdt = 100.0

建议:
- 测试阶段: 10-50 USDT
- 稳定运行: 100-200 USDT
- 扩大规模: > 200 USDT (需充分验证)
```

---

## ✨ 高级用法

### 使用 /execute_trade 端点
```
场景: 分离信号生成和执行

步骤:
1. 第一步: dry_run=1 获取审计 ID
   GET /get_btc_signal?dry_run=1&...
   → audit_id: abc123...

2. 检查信号后再执行
   POST /execute_trade
   body: {"audit_id": "abc123...", "token": "..."}
   → orderId: 10632732861
```

### 批量查询交易历史
```
查询最近 50 条:
  GET /audit/recent?limit=50

导出为 CSV (自行编写脚本):
  1. 获取 /audit/recent?limit=500
  2. 遍历结果，提取字段
  3. 写入 CSV 文件
```

---

## 🚨 安全提示

⚠️ **重要**: 在启用 `dry_run=0` 前

1. ✅ 在模拟模式下充分测试 (dry_run=1)
2. ✅ 验证信号逻辑正确
3. ✅ 从小金额开始 (10-50 USDT)
4. ✅ 确认后端日志无异常
5. ✅ 监控币安测试网订单执行情况
6. ✅ 设置合理的 max_position_size 和 max_notional

**不要**:
- ❌ 立即使用大金额
- ❌ 跳过模拟测试阶段
- ❌ 在不了解代码的情况下修改参数
- ❌ 忽视后端日志中的警告

---

## 📞 获取帮助

### 信息来源
1. **快速指南**: `MT5_QUICK_START.md`
2. **完整文档**: `MT5_EA_USAGE_GUIDE.md`
3. **系统状态**: `SYSTEM_STATUS.md`

### 调试命令
```bash
# 测试后端健康状态
curl http://127.0.0.1:8000/get_signal_logs

# 测试实际下单功能
python test_mt5_live_trading.py

# 对比模拟 vs 实际
python test_mt5_live_trading.py --compare

# 查询最近订单
curl "http://127.0.0.1:8000/audit/recent?limit=5"
```

---

**准备就绪**: ✅ 是的！  
**风险等级**: 🟡 低（使用测试网）  
**预计设置时间**: 5-10 分钟  
**支持**: 查看上述文档或运行测试脚本

**开始吧！** 🚀
