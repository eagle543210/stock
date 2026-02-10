#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键验证币安 API 配置
"""

import os
from binance_http_client import BinanceFuturesHTTP
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_SECRET_KEY')

print("\n" + "=" * 80)
print("✅ 币安 API 配置验证")
print("=" * 80 + "\n")

if not api_key or not api_secret:
    print("❌ API Key 未配置！")
    exit(1)

client = BinanceFuturesHTTP(api_key, api_secret, testnet=True)

try:
    balance = client.fetch_balance()
    print(f"✅ API 认证成功！")
    print(f"\n📊 账户信息:")
    print(f"   USDT 可用: {float(balance.get('availableBalance', 0)):.2f}")
    print(f"   USDT 锁定: {float(balance.get('totalMainteinanceMargin', 0)):.2f}")
    print(f"   总资产: {float(balance.get('totalWalletBalance', 0)):.2f}")
    
    # 检查是否有持仓
    positions = client.get_positions()
    open_positions = [p for p in positions if float(p['positionAmt']) != 0]
    
    if open_positions:
        print(f"\n📈 当前持仓:")
        for pos in open_positions:
            print(f"   {pos['symbol']}: {pos['positionAmt']} (盈亏: {pos['unRealizedProfit']})")
    else:
        print(f"\n📈 当前无持仓")
    
    print(f"\n✅ 系统已准备就绪，可以开始交易！")
    
except Exception as e:
    print(f"❌ 验证失败: {str(e)}")
    exit(1)

print("\n" + "=" * 80)
