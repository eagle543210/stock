#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
币安 API 快速验证工具
在您更新 .env 后运行此脚本验证配置
"""

import os
import sys
import ccxt
from dotenv import load_dotenv

# 重新加载环境变量（确保读取最新的 .env）
load_dotenv(override=True)

binance_api_key = os.getenv('BINANCE_API_KEY', '').strip()
binance_api_secret = os.getenv('BINANCE_SECRET_KEY', '').strip()

print("\n" + "=" * 70)
print("🔐 币安 API 验证工具")
print("=" * 70 + "\n")

# 检查 API Key 是否已配置
if not binance_api_key or not binance_api_secret:
    print("❌ 错误: API Key 或 Secret 未在 .env 中配置")
    print("\n请按以下步骤配置:")
    print("1. 访问: https://testnet.binancefuture.com")
    print("2. 登录或注册账户")
    print("3. Account → API Management")
    print("4. 创建新的 Futures API Key")
    print("5. 复制 Key 和 Secret 到 .env 文件:")
    print("   BINANCE_API_KEY=<your_key>")
    print("   BINANCE_SECRET_KEY=<your_secret>")
    sys.exit(1)

print(f"✅ API Key 已配置 (长度: {len(binance_api_key)} 字符)")
print(f"✅ Secret Key 已配置 (长度: {len(binance_api_secret)} 字符)\n")

# 创建三个不同的交易所实例进行测试
configs = {
    'testnet': {
        'name': '合约 testnet 模拟盘',
        'urls': {
            'api': {
                'public': 'https://testnet.binancefuture.com',
                'private': 'https://testnet.binancefuture.com',
            }
        }
    },
    'mainnet': {
        'name': '合约主网',
        'urls': None  # 使用默认主网
    }
}

print("测试 API 连接....\n")

for config_name, config_info in configs.items():
    exchange_config = {
        'apiKey': binance_api_key,
        'secret': binance_api_secret,
        'enableRateLimit': True,
    }
    
    if config_info['urls']:
        exchange_config['urls'] = config_info['urls']
    
    exchange = ccxt.binance(exchange_config)
    endpoint = config_info['urls']['api']['public'] if config_info['urls'] else 'https://fapi.binance.com'
    
    print(f"🧪 {config_info['name']}")
    print(f"   端点: {endpoint}")
    
    # 测试 1: 服务器时间
    try:
        server_time = exchange.fetch_time()
        print(f"   ✅ 服务器连接: 正常")
    except Exception as e:
        print(f"   ❌ 服务器连接: {str(e)[:60]}")
        continue
    
    # 测试 2: 账户认证
    try:
        balance = exchange.fetch_balance()
        print(f"   ✅ API 认证: 正常")
        
        # 显示主要资产
        total_assets = len([b for b in balance['free'].values() if float(b) > 0])
        print(f"   💰 资产数量: {total_assets}")
        
        # 显示 USDT 余额
        usdt_free = float(balance['free'].get('USDT', 0))
        usdt_used = float(balance['used'].get('USDT', 0))
        usdt_total = usdt_free + usdt_used
        
        if usdt_total > 0:
            print(f"   📊 USDT 余额: {usdt_free:.2f} (冻结: {usdt_used:.2f})")
        else:
            print(f"   📊 USDT 余额: 0 (需要充值)")
        
        # 显示 BTC 余额
        btc_free = float(balance['free'].get('BTC', 0))
        btc_used = float(balance['used'].get('BTC', 0))
        btc_total = btc_free + btc_used
        
        if btc_total > 0:
            print(f"   📊 BTC 余额: {btc_free:.6f} (冻结: {btc_used:.6f})")
        
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ API 认证: 失败")
        
        if '-2008' in error_msg or 'Invalid Api-Key' in error_msg:
            print(f"   👉 原因: API Key 无效或来自不同账户")
        elif '-2015' in error_msg:
            print(f"   👉 原因: 权限问题")
        else:
            print(f"   👉 错误: {error_msg[:60]}")
    
    print()

print("=" * 70)
print("⚠️ 常见问题排查:")
print("-" * 70)
print("Q: 为什么显示 'Invalid Api-Key ID' (-2008)?")
print("A: API Key 无效或来自不同的账户")
print("   解决: 重新在 https://testnet.binancefuture.com 创建新的 API Key\n")

print("Q: 如何创建 testnet API Key?")
print("A: 1. 打开 https://testnet.binancefuture.com")
print("   2. 点击右上角账户图标")
print("   3. 选择 'API Management'")
print("   4. 创建新的 'Futures API' Key")
print("   5. 复制 Key 和 Secret 到 .env 文件\n")

print("Q: 是否需要充值资金到 testnet?")
print("A: 否。testnet 是模拟盘,所有资金都是虚拟的。")
print("   如需初始余额,可联系币安技术支持。\n")

print("=" * 70)
