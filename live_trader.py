from __future__ import print_function, absolute_import, unicode_literals
from gm.api import *
import json
import os
import pandas as pd
import joblib
import sys
from datetime import datetime

# 将项目根目录添加到Python路径
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from feature_generator import generate_features

# --- 1. 配置区 ---
TOKEN = '879fe6f27a8d45f09ed4aa4a60d7761b244ad3d2'
SIGNAL_FILE_PATH = 'signals.json'

class MyTrader:
    """
    本地交易决策 "大脑"。
    通过掘金量化SDK的事件驱动模型运行，以获取实时数据并生成交易决策。
    """
    def __init__(self):
        # 策略参数
        self.stop_loss_pct = -0.08 
        self.take_profit_pct = 0.16
        self.trailing_stop_pct = -0.12
        self.entry_threshold = 0.02
        self.capital_per_trade = 0.2

        # 股票池
        self.stock_pool = ['SHSE.600519', 'SZSE.300750', 'SHSE.601869']
        
        # 运行时变量
        self.position_peak_prices = {}

    def on_init(self, context):
        """
        策略初始化回调。
        """
        print("本地交易大脑初始化...")
        # 订阅股票池的日线数据，这样on_bar才能被触发
        subscribe(symbols=','.join(self.stock_pool), frequency='1d')
        print(f"已订阅股票池: {self.stock_pool}")

    def on_bar(self, context, bars):
        """
        日线数据推送回调，作为我们每日决策的主入口。
        """
        print(f"\n{context.now}: 收到新的Bar数据，开始生成交易信号...")
        self.generate_and_write_signals(context)

    def check_entry_signal(self, context, symbol):
        """
        检查开仓信号。
        """
        ticker = symbol.split('.')[1]
        model_path = f'./{ticker}_model.joblib'
        
        try:
            model_payload = joblib.load(model_path)
            model = model_payload['model']
            model_features = model_payload['features']
        except (FileNotFoundError, KeyError):
            return False

        try:
            raw_df = history_n(symbol=symbol, frequency='1d', count=250, end_time=context.now, fill_missing='last', df=True)
            if raw_df is None or raw_df.empty or len(raw_df) < 50: return False
            features_df, _ = generate_features(raw_df.copy())
            if features_df.empty: return False

            latest_features = features_df.iloc[-1][model_features]
            if latest_features.isnull().any(): return False
        except Exception as e:
            print(f"为 {ticker} 处理开仓数据时发生错误: {e}")
            return False

        prediction = model.predict(latest_features.to_frame().T.astype(float))[0]
        model_signal = prediction > self.entry_threshold

        bb_middle = features_df['BBL_20_2.0'].iloc[-1]
        current_close = features_df['close'].iloc[-1]
        bb_signal = False if pd.isna(bb_middle) else current_close > bb_middle

        if model_signal and bb_signal:
            print(f"  [+] 开仓信号确认: {symbol}. 模型预测 {prediction:.4f}, 收盘价 {current_close:.2f} > 布林中轨 {bb_middle:.2f}")
            return True
        
        return False

    def check_exit_signal(self, context, position):
        """
        检查平仓信号。
        """
        symbol = position.symbol
        open_price = position.vwap
        
        try:
            latest_bar = history_n(symbol=symbol, frequency='1d', count=1, end_time=context.now, fill_missing='last', df=True).iloc[-1]
            current_price = latest_bar['close']
        except Exception as e:
            print(f"获取 {symbol} 最新价格失败: {e}")
            return None

        if symbol not in self.position_peak_prices:
            self.position_peak_prices[symbol] = open_price
        self.position_peak_prices[symbol] = max(self.position_peak_prices.get(symbol, 0), current_price)
        peak_price = self.position_peak_prices[symbol]

        current_return = (current_price / open_price) - 1
        drawdown_from_peak = (current_price / peak_price) - 1

        if current_return <= self.stop_loss_pct: return f"固定止损 (收益率: {current_return:.2%})"
        if current_return >= self.take_profit_pct: return f"固定止盈 (收益率: {current_return:.2%})"
        if drawdown_from_peak <= self.trailing_stop_pct: return f"移动止损 (回撤: {drawdown_from_peak:.2%})"

        try:
            raw_df = history_n(symbol=symbol, frequency='1d', count=250, end_time=context.now, fill_missing='last', df=True)
            if raw_df is None or raw_df.empty: return None
            features_df, _ = generate_features(raw_df.copy())
            if features_df.empty: return None

            bb_middle = features_df['BBL_20_2.0'].iloc[-1]
            if not pd.isna(bb_middle) and current_price < bb_middle:
                return f"布林带信号 (收盘价 {current_price:.2f} 跌破中轨 {bb_middle:.2f})"
        except Exception as e:
            print(f"为 {symbol.split('.')[1]} 处理平仓数据时发生错误: {e}")
            return None

        return None

    def generate_and_write_signals(self, context):
        """
        生成交易信号并写入JSON文件的主函数。
        """
        new_signals = []
        account = context.account() # 从context获取账户对象
        if not account:
            print("错误: 无法获取账户信息。")
            return

        positions = account.positions()
        held_symbols = [p.symbol for p in positions]
        print(f"当前持仓: {held_symbols if held_symbols else '无'}")

        # 检查平仓
        for pos in positions:
            exit_reason = self.check_exit_signal(context, pos)
            if exit_reason:
                print(f"  [-] 平仓信号: {pos.symbol}. 原因: {exit_reason}")
                new_signals.append({"symbol": pos.symbol, "target_percent": 0, "status": "NEW"})
                # 从移动止损记录中移除
                if pos.symbol in self.position_peak_prices:
                    del self.position_peak_prices[pos.symbol]

        # 检查开仓
        for symbol in self.stock_pool:
            if symbol in held_symbols:
                continue
            if self.check_entry_signal(context, symbol):
                new_signals.append({"symbol": symbol, "target_percent": self.capital_per_trade, "status": "NEW"})

        # 写入信号文件
        if new_signals:
            try:
                existing_signals = []
                if os.path.exists(SIGNAL_FILE_PATH):
                    with open(SIGNAL_FILE_PATH, 'r') as f:
                        existing_signals = json.load(f)
                
                processed_signals = [s for s in existing_signals if s.get('status') == 'PROCESSED']
                final_signals = new_signals + processed_signals

                with open(SIGNAL_FILE_PATH, 'w') as f:
                    json.dump(final_signals, f, indent=4)
                print(f"成功生成 {len(new_signals)} 条新信号，并写入到 {SIGNAL_FILE_PATH}")
                print("请将此文件上传到掘金量化平台策略的根目录。")
            except Exception as e:
                print(f"写入信号文件失败: {e}")
        else:
            print("没有生成新的交易信号。")

if __name__ == '__main__':
    # 实例化我们的策略类
    trader = MyTrader()
    
    # 运行策略，注册回调函数
    # mode=MODE_LIVE 表示这是一个实时运行的程序，而不是回测
    run(
        strategy_id='strategy_id_live_trader_brain',
        filename='live_trader.py',
        mode=MODE_LIVE,
        token=TOKEN
    )