#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试 ccxt 实际发送的请求
"""

import os
import sys
import logging
import ccxt
from dotenv import load_dotenv

# 启用 ccxt 调试模式
ccxt.Exchange.enable_debug = True

# 配置日志
logging.basicConfig(level=logging.DEBUG)

load_dotenv(override=True)

binance_api_key = os.getenv('BINANCE_API_KEY', '').strip()
binance_api_secret = os.getenv('BINANCE_SECRET_KEY', '').strip()

print("\n" + "=" * 80)
print("🔧 ccxt 调试模式 - 查看实际发送的请求")
print("=" * 80 + "\n")

exchange = ccxt.binance({
    'apiKey': binance_api_key,
    'secret': binance_api_secret,
    'enableRateLimit': True,
    'verbose': True,  # 启用详细输出
    'urls': {
        'api': {
            'public': 'https://testnet.binancefuture.com',
            'private': 'https://testnet.binancefuture.com',
        }
    }
})

print("尝试调用 fetch_balance()...")
print("-" * 80 + "\n")

try:
    balance = exchange.fetch_balance()
    print("\n✅ 成功！")
except Exception as e:
    print(f"\n❌ 错误: {str(e)}")
