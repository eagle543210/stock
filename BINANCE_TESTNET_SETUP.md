# 币安 Futures Testnet API 配置指南

## 问题诊断

您正在收到 `-2008 "Invalid Api-Key ID"` 错误，这意味着您的 API Key 对当前端点无效。

## 根本原因

根据我们的测试结果，您的 API Key：
- ✅ 服务器可以连接
- ❌ 但 API Key 在所有账户 / 端点上都无法认证

**可能的原因：**
1. API Key 从未在 testnet 上创建过
2. API Key 已过期或被删除
3. API Key 来自现货账户而不是合约账户

## 解决步骤

### 第 1 步：访问 Testnet 合约模拟盘
打开浏览器，访问：
```
https://testnet.binancefuture.com
```

### 第 2 步：创建或登录账户
- 如果已有 testnet 账户，直接登录
- 如果没有，点击 "Sign Up" 注册新账户（可使用任意邮箱）

**重要：** testnet 账户独立于主网账户，需要单独注册

### 第 3 步：进入 API 管理页面
在 testnet 网站上：
1. 点击右上角的 **账户图标** 👤
2. 选择 **API Management**

### 第 4 步：创建新的 Futures API Key
1. 点击 **Create API Key**
2. 选择 **Futures API** （不是 Spot）
3. 设置以下权限：
   - ✅ **Read** - 允许读取账户信息
   - ✅ **Enable Trading** - 允许下单
   - ✅ **Enable Margin Trading** - 如需要（可选）

4. **IP 白名单**：
   - 对于测试，可以选择 "Unrestricted" （不推荐）
   - 或添加您的 IP 地址：**您的IP地址**

5. 点击 **Confirm** 创建

### 第 5 步：复制凭证到 .env 文件
创建成功后，您会看到：
- **API Key** （示例：`b7EpqYIf1qpLdbwsEU1Nd...`）
- **Secret Key** （示例：`aDLqMrlgXeXbGKbuqA4x5v...`）

**将这两个值复制到** `M:\stock\.env` 文件：

```dotenv
# 您的其他配置...

# Binance Futures Testnet API（更新这些）
BINANCE_API_KEY=<从 testnet 复制的 API Key>
BINANCE_SECRET_KEY=<从 testnet 复制的 Secret Key>
```

**示例：**
```dotenv
BINANCE_API_KEY="b7EpqYIf1qpLdbwsEU1NduckGlX81JaQJATm5VULueSbieXJEh8F0LZXBTsHRrpM"
BINANCE_SECRET_KEY="aDLqMrlgXeXbGKbuqA4x5vZd9DkP7oICkGQiIXvOrdnPTT0YrcfxFkVmYOQIaBvT"
```

### 第 6 步：验证配置
在 PowerShell 中运行验证脚本：

```powershell
cd M:\stock
python verify_api_key.py
```

### 预期输出（成功）
```
✅ API Key 已配置 (长度: 100 字符)
✅ Secret Key 已配置 (长度: 100 字符)

测试 API 连接....

🧪 合约 testnet 模拟盘
   端点: https://testnet.binancefuture.com
   ✅ 服务器连接: 正常
   ✅ API 认证: 正常
   💰 资产数量: 5
   📊 USDT 余额: 5000.00 (冻结: 0.00)
   📊 BTC 余额: 0.000000 (冻结: 0.000000)
```

## 常见问题

### Q: 为什么显示 "Invalid Api-Key ID" (-2008)?
**A:** API Key 无效或来自错误的账户。
- 确保您从 **testnet.binancefuture.com** 创建的是 **Futures API**
- 检查复制时是否有空格或遗漏

### Q: 现货账户和合约账户有区别吗?
**A:** 是的，完全独立：
- 现货账户用于买卖币种
- 合约账户用于期货交易（杠杆、空头等）
- API Key 需要在对应账户上创建

### Q: testnet 有真实资金吗?
**A:** 否。testnet 是完全虚拟的模拟环境：
- 所有交易都是模拟
- 不涉及真实资金
- 用于测试和学习

### Q: 如何获得 testnet 的初始资金?
**A:** testnet 通常会自动给予一定的虚拟资金。如需追加：
1. 访问 testnet 的 "Faucet" 页面
2. 或联系币安技术支持

### Q: 生成 API Key 后没看到 Secret Key?
**A:** Secret Key 只显示一次！必须复制保存。如果丢失：
1. 删除该 API Key
2. 创建新的 API Key

## 完整工作流

```
1. 访问 https://testnet.binancefuture.com
   ↓
2. 注册/登录账户
   ↓
3. Account → API Management
   ↓
4. Create API Key → Select Futures API
   ↓
5. 复制 Key 和 Secret 到 .env
   ↓
6. 运行 python verify_api_key.py
   ↓
7. 看到 ✅ 成功后，可开始交易！
```

## 验证成功后的下一步

一旦 API 认证成功，您可以：

1. **测试交易信号生成**
   ```bash
   python api.py
   # 访问 http://localhost:8000/get_btc_signal
   ```

2. **测试实际下单**
   ```bash
   curl http://localhost:8000/post_signal -X POST -H "Content-Type: application/json" \
     -d '{"symbol":"BTCUSDT","signal":"BUY"}'
   ```

3. **运行完整系统**
   ```bash
   .\start.ps1
   ```

## 获取帮助

如果仍有问题：

1. **检查错误代码：**
   - `-2008` → API Key 无效
   - `-2015` → 权限不足
   - `-4164` → 账户未激活

2. **查看官方文档：**
   - REST API: https://developers.binance.com/docs/derivatives/
   - Testnet: https://testnet.binancefuture.com

3. **验证端点连接：**
   ```bash
   python test_binance_endpoints.py
   ```

---
**最后更新：** 2024年12月
**作者：** AI Assistant
