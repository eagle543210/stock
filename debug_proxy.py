
import asyncio
import os
import aiohttp
import ccxt.async_support as ccxt
from dotenv import load_dotenv
import traceback

load_dotenv(override=True)

async def test_aiohttp_detailed():
    print("\n=== Testing AIOHTTP ===")
    proxy = os.getenv('HTTP_PROXY')
    url = "https://testnet.binancefuture.com/dapi/v1/exchangeInfo"
    print(f"Target: {url}")
    print(f"Proxy: {proxy}")
    
    # 1. Standard
    try:
        print("\n[Case 1] aiohttp with proxy and default SSL:")
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=5) as resp:
                print(f"  Status: {resp.status}")
                print(f"  Body len: {len(await resp.text())}")
    except Exception:
        print("  FAILED:")
        traceback.print_exc()

    # 2. SSL False
    try:
        print("\n[Case 2] aiohttp with proxy and ssl=False:")
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, ssl=False, timeout=5) as resp:
                print(f"  Status: {resp.status}")
                print(f"  Body len: {len(await resp.text())}")
    except Exception:
        print("  FAILED:")
        traceback.print_exc()

async def test_ccxt_detailed():
    print("\n=== Testing CCXT ===")
    proxy = os.getenv('HTTP_PROXY')
    
    config = {
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'options': {'defaultType': 'future'},
        'timeout': 5000,
        # 'verbose': True 
    }
    
    # Init
    exchange = ccxt.binance(config)
    exchange.set_sandbox_mode(True)
    
    # Set proxy
    if proxy:
        exchange.aiohttp_proxy = proxy
        print(f"Set exchange.aiohttp_proxy = {proxy}")

    try:
        print(f"\nAttempting load_markets with proxy={proxy}...")
        await exchange.load_markets()
        print("  ✅ load_markets SUCCESS")
    except Exception as e:
        print(f"  ❌ load_markets FAILED: {type(e).__name__}: {e}")
        # traceback.print_exc()
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_aiohttp_detailed())
    asyncio.run(test_ccxt_detailed())
