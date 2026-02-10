#!/usr/bin/env python3
import subprocess,sys,time,requests,os

# ensure project root on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# start server
proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'api:app', '--host', '127.0.0.1', '--port', '8000'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
try:
    # 等待服务就绪 (最多等待 15 秒)
    for _ in range(15):
        try:
            requests.get('http://127.0.0.1:8000/get_signal_logs', timeout=1)
            break
        except Exception:
            time.sleep(1)
    # call endpoint with small trade_amount_usdt
    r = requests.get('http://127.0.0.1:8000/get_btc_signal', params={'symbol':'BTC/USDT','timeframe':'5m','trade_amount_usdt':'50'}, timeout=15)
    print('status', r.status_code)
    try:
        print('resp:', r.json())
    except Exception:
        print('raw', r.text)
finally:
    proc.terminate()
    proc.wait(timeout=5)
