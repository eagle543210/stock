#!/usr/bin/env python3
import os
import json
from dotenv import load_dotenv
import ccxt

load_dotenv()
api = os.getenv('BINANCE_API_KEY')
secret = os.getenv('BINANCE_SECRET_KEY')

print('BINANCE_API_KEY set:', bool(api))
print('BINANCE_SECRET_KEY set:', bool(secret))

exchange = ccxt.binance({
    'apiKey': api,
    'secret': secret,
    'enableRateLimit': True,
})

print('\n--- exchange info ---')
print('id:', exchange.id)
print('urls.api:', json.dumps(exchange.urls.get('api', {}), indent=2))
print('options:', exchange.options)
print('has methods (subset):')
for k in ['fetchBalance','fetchPositions','createOrder','fetchOrder']:
    print(f'  {k}:', exchange.has.get(k))

# Test public fetch
print('\n--- public fetch_ticker ---')
try:
    ticker = exchange.fetch_ticker('BTC/USDT')
    print('fetch_ticker ok, last=', ticker.get('last'))
except Exception as e:
    print('fetch_ticker error:', repr(e))

# Test private spot fetch_balance
print('\n--- private spot fetch_balance ---')
try:
    bal = exchange.fetch_balance()
    print('fetch_balance ok: keys:', list(bal.keys()))
except Exception as e:
    print('fetch_balance error:', repr(e))

# Test futures (set defaultType)
print('\n--- futures check (set defaultType = future) ---')
try:
    exchange.options['defaultType'] = 'future'
    print('options after set:', exchange.options)
    # try fetch positions
    try:
        positions = exchange.fetch_positions([ 'BTC/USDT' ])
        print('fetch_positions ok:', positions)
    except Exception as e:
        print('fetch_positions error:', repr(e))
    # try fetch futures balance
    try:
        bal_f = exchange.fetch_balance()
        print('fetch_balance (futures) ok: keys:', list(bal_f.keys()))
    except Exception as e:
        print('fetch_balance (futures) error:', repr(e))
except Exception as e:
    print('setting defaultType failed:', repr(e))

print('\n--- low-level test: attempt a request that requires trade permission ---')
try:
    # Try to create a small test order on testnet would be safer; here we only check permission by calling private endpoint without creating an order
    # For Binance, request account info for futures
    if 'fapi' in exchange.urls and isinstance(exchange.urls['api'], dict):
        print('fapi available in urls')

    # Try a private GET to account endpoint (may differ by ccxt version)
    try:
        resp = exchange.sapi_get_account() if hasattr(exchange, 'sapi_get_account') else None
        print('sapi_get_account response:', resp if resp else 'not available')
    except Exception as e:
        print('sapi_get_account error:', repr(e))
except Exception as e:
    print('low-level test error:', repr(e))

print('\nDiagnosis complete.')
