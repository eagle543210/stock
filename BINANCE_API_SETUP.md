# 币安 API 密钥设置指南

## ⚠️ 重要安全提示

你的旧 API 密钥已经暴露在 GitHub 上，**必须立即删除**。即使删除也可能已被不法分子利用。

## 步骤 1：登录币安账户

1. 访问 https://www.binance.com (国际版) 或 https://www.binancezh.com (中文版)
2. 使用你的邮箱和密码登录
3. 完成 2FA 验证（如果已启用）

## 步骤 2：进入 API 管理页面

### 方式 A：菜单导航
```
账户 → API 管理 → 创建 API
```

### 方式 B：直接链接
```
https://www.binance.com/en/user/settings/api-management
```

## 步骤 3：创建新的 API Key

1. 点击 **"Create API"** 按钮
2. 选择 API 类型：**Spot/Margin Trading**
3. 给 API 取个名字（例如：`QuantTrading_API`）
4. 完成身份验证

## 步骤 4：配置权限

在权限设置中，确保启用以下权限：

```
✅ 启用现货交易读权限 (Enable Reading)
✅ 启用现货交易写权限 (Enable Spot & Margin Trading)
✅ IP 白名单：添加 127.0.0.1 或你的服务器 IP
```

**权限配置示例：**
```
Account Restrictions:
- Restrict creation to IP ______ (留空或输入你的 IP)
- Valid for ______ minutes after API key generation (建议 30-60 分钟)

Permissions:
☑ Enable Reading (读权限)
☑ Enable Spot & Margin Trading (现货交易)
☑ Enable Futures (合约交易 - 可选)
```

## 步骤 5：保存 API 密钥

系统将显示：
- **API Key**: 复制这个值
- **Secret Key**: 复制这个值（仅显示一次！）

**重要**：将这两个值保存到安全的地方。Secret Key 不会再显示。

## 步骤 6：更新项目配置

### 方式 A：更新 `.env` 文件（推荐）

编辑 `m:\stock\.env`：

```env
BINANCE_API_KEY="你的API_KEY"
BINANCE_SECRET_KEY="你的SECRET_KEY"
```

### 方式 B：使用环境变量（Docker/服务器部署）

```bash
export BINANCE_API_KEY="你的API_KEY"
export BINANCE_SECRET_KEY="你的SECRET_KEY"
```

## 步骤 7：测试连接

在 PowerShell 中运行：

```powershell
# 激活虚拟环境
& M:/stock/venv/Scripts/Activate.ps1

# 测试连接
python -c "
import ccxt
exchange = ccxt.binance({
    'apiKey': 'YOUR_API_KEY_HERE',
    'secret': 'YOUR_SECRET_KEY_HERE'
})
try:
    ticker = exchange.fetch_ticker('BTC/USDT')
    print('✅ 连接成功!')
    print(f'BTC/USDT: {ticker[\"last\"]} USDT')
except Exception as e:
    print(f'❌ 错误: {e}')
"
```

## 步骤 8：重启 API 服务

```powershell
# 停止旧服务 (Ctrl+C)

# 重启 API 服务
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

## 步骤 9：测试交易信号 API

```powershell
# 在新的 PowerShell 窗口中
curl "http://127.0.0.1:8000/get_btc_signal?symbol=BTC/USDT&timeframe=5m"
```

**预期输出：**
```json
{
  "symbol": "BTC/USDT",
  "signal": "BUY" 或 "SELL" 或 "HOLD",
  "comment": "模型预测值: 0.0234",
  "order": null
}
```

## 常见问题

### Q: 显示 "Invalid Api-Key ID" 是什么意思？
A: API 密钥格式错误或已失效。检查：
- ✅ 密钥是否正确复制（没有多余空格）
- ✅ 密钥是否已启用
- ✅ IP 白名单是否正确

### Q: 如何撤销泄露的 API 密钥？
A: 
1. 进入 API 管理页面
2. 找到旧的 API Key
3. 点击 "Delete" 删除
4. 创建新的 API Key

### Q: 能否同时创建多个 API Key？
A: 可以。建议为不同的应用创建不同的 API Key，方便管理和权限控制。

### Q: Secret Key 丢失了怎么办？
A: 无法恢复。需要删除该 API 并创建新的。

## 安全最佳实践

```
1. ❌ 不要在代码中硬编码 API 密钥
2. ❌ 不要上传 .env 文件到 GitHub
3. ❌ 不要分享你的 API 密钥给任何人
4. ✅ 使用环境变量管理敏感信息
5. ✅ 定期轮换 API 密钥
6. ✅ 限制 API 权限到最低必需级别
7. ✅ 启用 IP 白名单
```

---

**现在你已经准备好了！按照上面的步骤创建新的 API 密钥并更新配置。**
