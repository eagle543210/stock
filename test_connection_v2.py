import asyncio
import os
import ccxt.async_support as ccxt
import aiohttp
from dotenv import load_dotenv

# Force reload
load_dotenv(override=True)

async def test_direct_aiohttp():
    print("\n--- Testing Direct aiohttp Connection ---")
    proxy = os.getenv('HTTP_PROXY')
    url = "https://testnet.binance.vision/api/v3/time"
    try:
        async with aiohttp.ClientSession(trust_env=True) as session: # trust_env=True reads env vars!
            print(f"Connecting to {url} with trust_env=True (Env Proxy: {proxy})")
            async with session.get(url, proxy=proxy if not proxy else None) as resp: # If trust_env=True, we might not need proxy arg if env is set, OR we pass it explicitly.
                # Actually, if proxy is set in env, trust_env=True should handle it.
                # If we pass proxy arg, it overrides.
                # Let's try explicit proxy arg to be sure.
                pass
            
            # Let's try explicit mode as ccxt might not use trust_env
            print(f"Attempt 1: Explicit proxy={proxy}")
            async with session.get(url, proxy=proxy) as resp:
                print(f"Status: {resp.status}")
                print(await resp.text())

    except Exception as e:
        print(f"Direct aiohttp failed: {e}")

async def test_ccxt_proxy():
    print("\n--- Testing CCXT with Proxy Options ---")
    proxy = os.getenv('HTTP_PROXY')
    
    # Method 1: 'aiohttp_proxy' option (Undocumented but sometimes works?)
    # Method 2: 'proxies' dict (Works for requests, maybe ignored by async ccxt)
    # Method 3: 'proxy' option (Often for CORS)
    
    # Try creating custom session? CCXT allows passing 'session'. (Deprecated/Complex)
    
    # Try passing proxy in params?
    
    exchange = ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'aiohttp_proxy': proxy, # Hypothetical
        'proxies': { 'http': proxy, 'https': proxy }, # Common
        'options': {
            'defaultType': 'future', 
        } 
    })
    
    # Crucially, ccxt async might have a property 'aiohttp_proxy' we can set?
    exchange.aiohttp_proxy = proxy
    
    exchange.set_sandbox_mode(True)
    
    try:
        await exchange.load_markets()
        print("✅ CCXT load_markets success!")
    except Exception as e:
        print(f"❌ CCXT load_markets failed: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_direct_aiohttp())
    asyncio.run(test_ccxt_proxy())
