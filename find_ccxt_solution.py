#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 ccxt 的 testnet 正确配置方式
"""

import os
import ccxt
from dotenv import load_dotenv

load_dotenv(override=True)

binance_api_key = os.getenv('BINANCE_API_KEY', '').strip()
binance_api_secret = os.getenv('BINANCE_SECRET_KEY', '').strip()

print("\n" + "=" * 80)
print("🧪 ccxt Binance testnet 配置测试")
print("=" * 80 + "\n")

configs = [
    {
        'name': '方法 1: 使用 sandbox=True',
        'config': {
            'apiKey': binance_api_key,
            'secret': binance_api_secret,
            'enableRateLimit': True,
            'sandbox': True,  # 使用 sandbox 参数
        }
    },
    {
        'name': '方法 2: 直接修改 hostname',
        'config': {
            'apiKey': binance_api_key,
            'secret': binance_api_secret,
            'enableRateLimit': True,
            'hostname': 'testnet.binancefuture.com',
        }
    },
    {
        'name': '方法 3: 修改 urls（当前方法）',
        'config': {
            'apiKey': binance_api_key,
            'secret': binance_api_secret,
            'enableRateLimit': True,
            'urls': {
                'api': {
                    'public': 'https://testnet.binancefuture.com',
                    'private': 'https://testnet.binancefuture.com',
                }
            }
        }
    },
    {
        'name': '方法 4: 使用完整路径',
        'config': {
            'apiKey': binance_api_key,
            'secret': binance_api_secret,
            'enableRateLimit': True,
            'urls': {
                'api': {
                    'public': 'https://testnet.binancefuture.com/fapi/v1',
                    'private': 'https://testnet.binancefuture.com/fapi/v1',
                }
            }
        }
    },
    {
        'name': '方法 5: 使用 options',
        'config': {
            'apiKey': binance_api_key,
            'secret': binance_api_secret,
            'enableRateLimit': True,
            'options': {
                'sandbox': True,
                'testnet': True,
                'defaultType': 'future',
                'test': True,
            }
        }
    },
]

for config_info in configs:
    print(f"🧪 {config_info['name']}")
    print("-" * 80)
    
    try:
        exchange = ccxt.binance(config_info['config'])
        
        # 显示实际使用的 API URL
        if hasattr(exchange, 'urls'):
            print(f"   API URLs:")
            if 'api' in exchange.urls:
                print(f"     - public: {exchange.urls['api'].get('public', 'N/A')}")
                print(f"     - private: {exchange.urls['api'].get('private', 'N/A')}")
        
        # 测试 1: 获取时间
        try:
            server_time = exchange.fetch_time()
            print(f"   ✅ 服务器连接: 正常")
        except Exception as e:
            print(f"   ❌ 服务器连接失败: {str(e)[:60]}")
            print()
            continue
        
        # 测试 2: 获取账户余额
        try:
            balance = exchange.fetch_balance()
            assets = len([b for b in balance['free'].values() if float(b) > 0])
            usdt = float(balance['free'].get('USDT', 0))
            print(f"   ✅ 账户认证: 成功")
            print(f"      持有资产: {assets} | USDT: {usdt:.2f}")
        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ 账户认证失败: {error_msg[:60]}")
            
            if '-2008' in error_msg:
                print(f"      💡 提示: API Key 不被识别")
            elif '-2015' in error_msg:
                print(f"      💡 提示: 权限问题")
        
    except Exception as e:
        print(f"   ❌ 配置错误: {str(e)[:60]}")
    
    print()

print("=" * 80)
