# btc_trader.py
# 这是一个使用移动平均线交叉策略的比特币自动交易脚本示例。

import ccxt
import pandas as pd
import pandas_ta as ta
import os
from dotenv import load_dotenv
import time

# --- 1. 初始化和配置 ---

# 从 .env 文件加载环境变量 (API 密钥)
load_dotenv()
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_SECRET_KEY')

# 检查API密钥是否存在
if not api_key or not api_secret:
    print("错误：请确保在 .env 文件中设置了 BINANCE_API_KEY 和 BINANCE_SECRET_KEY")
    exit()

# 连接到币安交易所
# 'enableRateLimit': True 可以帮助我们避免因请求过于频繁而被API封禁
exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'spot',
    },
})

# --- 如果你想使用测试网，请取消下面的注释 ---
# exchange.set_sandbox_mode(True)
# print("已切换到币安测试网模式")


# --- 2. 交易参数和策略设置 ---

symbol = 'BTC/USDT'      # 交易对
timeframe = '1h'         # K线周期：'1m', '5m', '15m', '1h', '4h', '1d'
fast_ma_period = 20      # 短期移动平均线周期
slow_ma_period = 50      # 长期移动平均线周期
trade_amount_usdt = 15   # 每次交易的USDT金额 (币安现货最低交易额通常是10 USDT)

# --- 3. 核心功能函数 ---

def fetch_data(symbol, timeframe, limit=100):
    """从交易所获取K线数据"""
    try:
        print(f"正在获取 {symbol} 在 {timeframe} 周期上的最新 {limit} 条K线数据...")
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        print(f"获取数据时发生错误: {e}")
        return None

def calculate_indicators(df):
    """计算技术指标"""
    if df is None:
        return None
    print("正在计算移动平均线...")
    # 使用 pandas-ta 库计算SMA
    df.ta.sma(length=fast_ma_period, append=True)
    df.ta.sma(length=slow_ma_period, append=True)
    return df

def check_signals(df):
    """检查交易信号"""
    if df is None or len(df) < slow_ma_period:
        return "HOLD"
        
    print("正在检查交易信号...")
    # 获取最新的两条K线数据来进行判断
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]

    fast_ma_col = f'SMA_{fast_ma_period}'
    slow_ma_col = f'SMA_{slow_ma_period}'

    # 检查列是否存在
    if fast_ma_col not in df.columns or slow_ma_col not in df.columns:
        print("错误：无法找到移动平均线数据列。")
        return "HOLD"

    # --- 核心策略逻辑 ---
    # 金叉：短期线上穿长期线 (上一根K线时短期线在下方，当前K线时短期线在上方)
    if prev_row[fast_ma_col] < prev_row[slow_ma_col] and last_row[fast_ma_col] > last_row[slow_ma_col]:
        print("📈 发现金叉信号！")
        return "BUY"

    # 死叉：短期线下穿长期线 (上一根K线时短期线在上方，当前K线时短期线在下方)
    if prev_row[fast_ma_col] > prev_row[slow_ma_col] and last_row[fast_ma_col] < last_row[slow_ma_col]:
        print("📉 发现死叉信号！")
        return "SELL"

    return "HOLD"

def execute_trade(signal, symbol, amount_usdt):
    """执行交易"""
    try:
        # 获取BTC的当前价格，以计算购买数量
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        if current_price is None or current_price == 0:
            print("无法获取当前价格，跳过交易。")
            return

        # 根据USDT金额计算要交易的BTC数量
        amount_to_trade = amount_usdt / current_price
        
        print(f"当前 {symbol} 价格: {current_price}, 计划交易数量: {amount_to_trade:.6f}")

        if signal == "BUY":
            print(f"正在执行市价买入订单...")
            order = exchange.create_market_buy_order(symbol, amount_to_trade)
            print("买入订单已成功执行！")
            print(order)
        
        elif signal == "SELL":
            # 在卖出前，检查我们是否有足够的BTC余额
            balance = exchange.fetch_balance()
            btc_balance = balance['BTC']['free'] if 'BTC' in balance else 0
            
            if btc_balance < amount_to_trade:
                print(f"BTC余额不足 ({btc_balance:.6f})，无法执行卖出。将卖出所有可用余额。")
                if btc_balance > 0.0001: # 确保有最小可交易量
                   amount_to_trade = btc_balance
                else:
                   print("可用余额过小，取消卖出。")
                   return

            print(f"正在执行市价卖出订单...")
            order = exchange.create_market_sell_order(symbol, amount_to_trade)
            print("卖出订单已成功执行！")
            print(order)

    except ccxt.InsufficientFunds as e:
        print(f"执行交易失败：资金不足。 {e}")
    except Exception as e:
        print(f"执行交易时发生未知错误: {e}")

# --- 4. 主循环 ---

def main_loop():
    """程序的主循环"""
    print("="*50)
    print("比特币交易脚本已启动")
    print(f"交易对: {symbol}, K线周期: {timeframe}")
    print(f"策略: SMA({fast_ma_period}) / SMA({slow_ma_period}) 交叉")
    print("="*50)
    
    while True:
        try:
            # 1. 获取数据
            data = fetch_data(symbol, timeframe)
            
            # 2. 计算指标
            data_with_indicators = calculate_indicators(data)
            
            # 打印最新数据以供观察
            if data_with_indicators is not None:
                print("\n--- 最新市场数据 ---")
                print(data_with_indicators.tail(3))
                print("--------------------\n")

            # 3. 检查信号
            signal = check_signals(data_with_indicators)
            print(f"当前信号: {signal}")

            # 4. 执行交易
            if signal == "BUY" or signal == "SELL":
                execute_trade(signal, symbol, trade_amount_usdt)
            
            # 等待下一个K线周期
            # 注意：这个等待逻辑很简单。在生产环境中，需要更精确的计时器来对准K线开始的时间点。
            print("\n脚本将在60秒后进行下一次检查...")
            time.sleep(60)

        except KeyboardInterrupt:
            print("\n检测到手动中断，程序正在退出...")
            break
        except Exception as e:
            print(f"主循环发生严重错误: {e}")
            print("将在60秒后重试...")
            time.sleep(60)

if __name__ == "__main__":
    main_loop()
