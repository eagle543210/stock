#!/usr/bin/env python3
import os
import sys
# ensure project root is on sys.path so local modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from binance_http_client import BinanceFuturesHTTP

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_SECRET_KEY')

if not api_key or not api_secret:
    print('No API key configured in .env')
    exit(1)

c = BinanceFuturesHTTP(api_key, api_secret, testnet=True)

symbol = 'BTCUSDT'
print('Fetching symbol info...')
info = c.get_symbol_info(symbol)
print('Symbol filters:')
for f in info.get('filters'):
    print(' ', f)

price = c.fetch_ticker(symbol).get('lastPrice') or c.fetch_klines(symbol, '1m', limit=1)[-1][4]
print('Last price:', price)

for notional in [10, 50, 100, 200, 1000]:
    try:
        qty = c.adjust_quantity_for_notional(symbol, notional, price=float(price))
        print(f'notional {notional} -> qty {qty}')
    except Exception as e:
        print('error', e)

# rounding test
print('round down 0.005 ->', c.round_quantity(symbol, 0.005, rounding='down'))
print('round up 0.005 ->', c.round_quantity(symbol, 0.005, rounding='up'))
