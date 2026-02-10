
import asyncio
import os
import aiohttp
import ccxt.async_support as ccxt
from dotenv import load_dotenv
import traceback

load_dotenv(override=True)

async def run_tests():
    output = []
    def log(msg):
        print(msg)
        output.append(str(msg))
    
    proxy = os.getenv('HTTP_PROXY')
    url = "https://testnet.binancefuture.com/dapi/v1/exchangeInfo"
    log(f"Proxy: {proxy}")
    log(f"Target: {url}")
    
    # 1. AIOHTTP
    log("\n[1] AIOHTTP Standard")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=5) as resp:
                log(f"  Status: {resp.status}")
    except Exception as e:
        log(f"  FAILED: {type(e).__name__} - {e}")

    # 2. CCXT
    log("\n[2] CCXT")
    exchange = ccxt.binance({
        'apiKey': 'test', 'secret': 'test',
        'options': {'defaultType': 'future'},
        'timeout': 5000,
        'verbose': True
    })
    exchange.set_sandbox_mode(True)
    if proxy:
        exchange.aiohttp_proxy = proxy
    
    try:
        await exchange.load_markets()
        log("  SUCCESS")
    except Exception as e:
        log(f"  FAILED: {type(e).__name__} - {e}")
    finally:
        await exchange.close()
        
    with open("debug_result_utf8.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    asyncio.run(run_tests())
