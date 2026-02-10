#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
币安 Testnet API 详细诊断工具
帮助您定位 API Key 问题的根本原因
"""

import os
import sys
import time
import json
import requests
import hmac
import hashlib
from dotenv import load_dotenv

# 重新加载环境变量
load_dotenv(override=True)

binance_api_key = os.getenv('BINANCE_API_KEY', '').strip()
binance_api_secret = os.getenv('BINANCE_SECRET_KEY', '').strip()

print("\n" + "=" * 80)
print("🔍 币安 Testnet API 详细诊断工具")
print("=" * 80 + "\n")

# ============================================================================
# 第 1 部分：基本信息检查
# ============================================================================
print("📋 第 1 部分：API 凭证检查")
print("-" * 80)

if not binance_api_key or not binance_api_secret:
    print("❌ 错误：API Key 或 Secret 未配置")
    sys.exit(1)

print(f"✅ API Key: {binance_api_key[:20]}...{binance_api_key[-10:]}")
print(f"   长度: {len(binance_api_key)} 字符")
print(f"✅ Secret Key: {binance_api_secret[:20]}...{binance_api_secret[-10:]}")
print(f"   长度: {len(binance_api_secret)} 字符")

# 验证格式
if not all(c in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-' for c in binance_api_key):
    print("⚠️  警告：API Key 包含不标准字符")

if not all(c in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-' for c in binance_api_secret):
    print("⚠️  警告：Secret Key 包含不标准字符")

print()

# ============================================================================
# 第 2 部分：直接 HTTP 测试（不使用 ccxt）
# ============================================================================
print("📋 第 2 部分：直接 HTTP 请求测试")
print("-" * 80)

endpoints_to_test = [
    {
        'name': 'Testnet 服务器时间',
        'url': 'https://testnet.binancefuture.com/fapi/v1/time',
        'method': 'GET',
        'auth': False
    },
    {
        'name': 'Testnet 账户信息',
        'url': 'https://testnet.binancefuture.com/fapi/v2/account',
        'method': 'GET',
        'auth': True
    },
    {
        'name': 'Mainnet 服务器时间',
        'url': 'https://fapi.binance.com/fapi/v1/time',
        'method': 'GET',
        'auth': False
    },
    {
        'name': 'Mainnet 账户信息',
        'url': 'https://fapi.binance.com/fapi/v2/account',
        'method': 'GET',
        'auth': True
    },
]

def generate_signature(query_string, secret):
    """生成币安 API 签名"""
    return hmac.new(
        secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

for endpoint in endpoints_to_test:
    print(f"\n🧪 {endpoint['name']}")
    print(f"   URL: {endpoint['url']}")
    
    headers = {
        'X-MBX-APIKEY': binance_api_key,
        'User-Agent': 'Python Binance Bot'
    }
    
    try:
        if endpoint['auth']:
            # 生成签名的请求
            timestamp = int(time.time() * 1000)
            query_string = f'timestamp={timestamp}&recvWindow=5000'
            signature = generate_signature(query_string, binance_api_secret)
            
            url = f"{endpoint['url']}?{query_string}&signature={signature}"
            response = requests.get(url, headers=headers, timeout=5)
        else:
            # 无需签名的请求
            response = requests.get(endpoint['url'], headers=headers, timeout=5)
        
        print(f"   HTTP 状态码: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ 请求成功")
            try:
                data = response.json()
                if isinstance(data, dict):
                    if 'serverTime' in data:
                        print(f"   📍 服务器时间: {data['serverTime']}")
                    if 'balances' in data:
                        # 显示有余额的资产
                        assets_with_balance = [
                            b for b in data['balances'] 
                            if float(b['free']) > 0 or float(b['locked']) > 0
                        ]
                        print(f"   💰 持有资产数: {len(assets_with_balance)}")
                        for balance in assets_with_balance[:5]:
                            print(f"      - {balance['asset']}: {balance['free']} (锁定: {balance['locked']})")
            except:
                pass
        
        elif response.status_code == 401 or response.status_code == 403:
            print(f"   ❌ 认证失败 (HTTP {response.status_code})")
            try:
                error = response.json()
                if 'code' in error:
                    print(f"   错误代码: {error['code']}")
                if 'msg' in error:
                    print(f"   错误信息: {error['msg']}")
                    
                    # 分析错误
                    msg = error['msg'].lower()
                    if 'invalid api-key' in msg:
                        print(f"   💡 可能原因: API Key 无效或来自错误账户")
                    elif 'invalid signature' in msg:
                        print(f"   💡 可能原因: Secret Key 错误或签名生成失败")
                    elif 'ip' in msg:
                        print(f"   💡 可能原因: IP 地址不在白名单中")
            except:
                print(f"   响应: {response.text[:100]}")
        
        else:
            print(f"   ❌ 请求失败 (HTTP {response.status_code})")
            print(f"   响应: {response.text[:200]}")
    
    except requests.exceptions.Timeout:
        print(f"   ❌ 请求超时")
    except requests.exceptions.ConnectionError:
        print(f"   ❌ 连接错误 (检查网络)")
    except Exception as e:
        print(f"   ❌ 错误: {str(e)[:100]}")

print("\n")

# ============================================================================
# 第 3 部分：问题排查指南
# ============================================================================
print("=" * 80)
print("🔧 问题排查指南")
print("-" * 80)
print("""
如果 Testnet 账户信息请求失败，请按以下步骤检查：

1️⃣ 验证 API Key 是否在 testnet 上创建
   - 打开 https://testnet.binancefuture.com
   - 登录您的账户
   - 进入 Account → API Management
   - 确认列出了您的 API Key

2️⃣ 检查 API Key 是否仍然有效
   - 如果 API Key 显示 "Restricted"，点击编辑
   - 确保以下权限已启用：
     ✅ Read
     ✅ Enable Trading
     
3️⃣ 检查 IP 白名单设置
   - 在 API Management 页面查看 IP Restriction
   - 如果显示具体 IP，确认您当前 IP 在列表中
   - 获取您当前 IP: https://api.ipify.org
   - 如需从任何地方访问，选择 "Unrestricted"

4️⃣ 重新复制 API Key 和 Secret
   - 可能在复制时有空格或遗漏字符
   - Secret Key 非常敏感，任何差异都会导致失败
   - 建议：
     a) 删除旧的 API Key
     b) 创建新的 API Key
     c) 立即复制（不要切换页面）
     d) 粘贴到 .env 文件

5️⃣ 测试新 API Key
   - 保存 .env 文件后运行此脚本
   - 观察 Testnet 账户信息请求的结果

""")

print("=" * 80)
print("💡 下一步建议:")
print("-" * 80)

# 检测问题
testnet_success = False
try:
    # 简单检测：如果能获取 testnet 时间，说明网络正常
    response = requests.get('https://testnet.binancefuture.com/fapi/v1/time', timeout=5)
    testnet_success = response.status_code == 200
except:
    testnet_success = False

if testnet_success:
    print("""
✅ Testnet 服务器可以连接

👉 建议：
   1. 确认您从 https://testnet.binancefuture.com 创建了 API Key
   2. 检查 IP 白名单是否包含您的 IP
   3. 尝试删除旧 API Key，创建全新的 Key
   4. 确保复制 Key/Secret 时没有多余空格
""")
else:
    print("""
❌ Testnet 服务器无法连接

👉 可能原因：
   1. 网络连接问题
   2. Testnet 服务暂时离线
   3. 防火墙阻止
   
👉 建议：
   1. 检查网络连接
   2. 尝试访问 https://testnet.binancefuture.com
   3. 如果网站无法打开，稍后重试
""")

print("=" * 80)
