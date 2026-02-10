import asyncio
import os
import ccxt.async_support as ccxt
from dotenv import load_dotenv

# Force reload of .env
load_dotenv(override=True)

async def test_binance():
    api_key = os.getenv('BINANCE_API_KEY')
    secret = os.getenv('BINANCE_SECRET_KEY')
    http_proxy = os.getenv('HTTP_PROXY')
    https_proxy = os.getenv('HTTPS_PROXY')
    
    print(f"--- Configuration Check ---")
    print(f"API Key present: {bool(api_key)}")
    print(f"HTTP_PROXY: {http_proxy}")
    print(f"HTTPS_PROXY: {https_proxy}")
    
    params = {
        'apiKey': api_key,
        'secret': secret,
        'timeout': 10000,
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    }
    
    if http_proxy or https_proxy:
        params['proxies'] = {
            'http': http_proxy,
            'https': https_proxy or http_proxy
        }
        print(f"Using Proxies: {params['proxies']}")
    else:
        print("⚠️ No Proxy configured. Connection may fail in restricted regions.")

    exchange = ccxt.binance(params)
    exchange.set_sandbox_mode(True) # Testnet
    
    print("\n--- Connecting to Binance Testnet ---")
    try:
        await exchange.load_markets()
        print("✅ Success! Markets loaded.")
        print(f"Symbols loaded: {len(exchange.symbols)}")
        
        # Test fetch ticker
        ticker = await exchange.fetch_ticker('BTC/USDT')
        print(f"BTC/USDT Price: {ticker['last']}")
        
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_binance())
