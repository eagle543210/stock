
import datetime
import uuid
import MetaTrader5 as mt5
import time
import pandas as pd
import joblib
from feature_generator import generate_features
from data_downloader import download_us_stock_data
from datetime import datetime, timedelta

class Trader:
    def __init__(self, 
                 stop_loss_pct: float = -0.08, 
                 take_profit_pct: float = 0.16, 
                 trailing_stop_pct: float = -0.12):
        
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.position_peak_prices = {} # 用于跟踪移动止损的最高价

        if mt5.terminal_info():
            print("Trader: MT5 连接成功，准备进行真实交易。")
        else:
            print("Trader: 警告 - MT5 未连接。place_order 将会失败。请确保MT5正在运行并已登录。")

    def place_order(self, ticker: str, order_type: str, price: float, quantity: float) -> str:
        """
        通过MT5发送真实订单。
        order_type: 'BUY' 或 'SELL'
        """
        if not mt5.terminal_info():
            error_msg = "MT5 未连接，无法下单。"
            print(f"Trader Error: {error_msg}")
            return f"ERROR: {error_msg}"

        symbol_info = mt5.symbol_info(ticker)
        if symbol_info is None:
            error_msg = f"交易品种 {ticker} 未找到或不可用。"
            print(f"Trader Error: {error_msg}")
            return f"ERROR: {error_msg}"

        if order_type == 'BUY':
            trade_action = mt5.ORDER_TYPE_BUY
            price_to_use = mt5.symbol_info_tick(ticker).ask
        elif order_type == 'SELL':
            trade_action = mt5.ORDER_TYPE_SELL
            price_to_use = mt5.symbol_info_tick(ticker).bid
        else:
            error_msg = f"未知的订单类型: {order_type}"
            print(f"Trader Error: {error_msg}")
            return f"ERROR: {error_msg}"

        volume = float(quantity)
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": ticker,
            "volume": volume,
            "type": trade_action,
            "price": price_to_use,
            "deviation": 20,
            "magic": 234000,
            "comment": "Python Quant System",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }

        print(f"正在向MT5发送订单: {order_type} {volume} {ticker} @ {price_to_use}")
        result = mt5.order_send(request)

        if result is None:
            error_code = mt5.last_error()
            error_msg = f"order_send 失败, MT5 last_error() = {error_code}"
            print(f"Trader Error: {error_msg}")
            return f"ERROR: {error_msg}"
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = f"订单执行失败, retcode={result.retcode}, comment={result.comment}"
            print(f"Trader Error: {error_msg}")
            return f"ERROR: {error_msg}"
        
        order_id = str(result.order)
        print(f"订单成功发送到MT5! 订单号: {order_id}")
        return order_id

    def _check_positions_for_exit(self, current_positions: dict, exit_threshold: float = 0.0):
        """
        检查当前持仓，根据模型预测和规则决定是否平仓 (内部辅助函数)。
        """
        signals_to_exit = {} # 使用字典来存储平仓原因
        today_str = datetime.now().strftime('%Y%m%d')
        start_date_str = (datetime.now() - timedelta(days=250)).strftime('%Y%m%d')

        for ticker, position_info in current_positions.items():
            print(f"正在评估股票: {ticker}...")
            
            # --- 1. 检查基于规则的止盈止损 ---
            open_price = position_info['price']
            current_tick = mt5.symbol_info_tick(ticker)
            if not current_tick:
                print(f"警告: 无法获取 {ticker} 的最新报价，跳过规则检查。")
                continue
            
            current_price = current_tick.bid # 使用卖价来评估平仓
            
            # 更新移动止损的最高价
            if ticker not in self.position_peak_prices:
                self.position_peak_prices[ticker] = open_price
            self.position_peak_prices[ticker] = max(self.position_peak_prices[ticker], current_price)
            peak_price = self.position_peak_prices[ticker]

            # 计算当前收益和回撤
            current_return = (current_price / open_price) - 1
            drawdown_from_peak = (current_price / peak_price) - 1

            # 检查规则
            if current_return <= self.stop_loss_pct:
                signals_to_exit[ticker] = f"固定止损 (收益率: {current_return:.2%})"
                continue
            if current_return >= self.take_profit_pct:
                signals_to_exit[ticker] = f"固定止盈 (收益率: {current_return:.2%})"
                continue
            if drawdown_from_peak <= self.trailing_stop_pct:
                signals_to_exit[ticker] = f"移动止损 (从最高价 {peak_price:.2f} 回撤: {drawdown_from_peak:.2%})"
                continue

            # --- 2. 如果规则未触发，则检查模型信号 ---
            model_path = f'./{ticker.upper()}_model.joblib'
            try:
                model_payload = joblib.load(model_path)
                model = model_payload['model']
                model_features = model_payload['features']
            except (FileNotFoundError, KeyError):
                print(f"警告: 未找到 {ticker} 的模型文件或特征列表，跳过模型检查。")
                continue

            download_us_stock_data(ticker, start_date_str, today_str)
            
            data_path = f"stock_data_cache/us_{ticker.lower()}_daily.csv"
            try:
                raw_df = pd.read_csv(data_path, skiprows=[1])
                features_df, _ = generate_features(raw_df.copy())
                
                if features_df.empty:
                    print(f"警告: 为 {ticker} 生成特征后数据为空，无法预测。")
                    continue

                missing_features = [f for f in model_features if f not in features_df.columns]
                if missing_features:
                    print(f"警告: {ticker} 的数据缺少模型需要的特征: {missing_features}，无法预测。")
                    continue

                latest_features = features_df.iloc[-1][model_features]
                
                if latest_features.isnull().any():
                    print(f"警告: {ticker} 的最新特征包含 NaN 值，无法进行预测。")
                    continue

            except Exception as e:
                print(f"为 {ticker} 处理最新数据时发生错误: {e}")
                continue

            prediction = model.predict(latest_features.to_frame().T.astype(float))[0]
            print(f"模型对 {ticker} 的最新预测 (未来5日收益率): {prediction:.4f}")

            # --- 3. 添加布林带平仓逻辑 ---
            # 确保布林带特征存在
            bb_middle = features_df['BBL_20_2.0'].iloc[-1] # 中轨
            bb_lower = features_df['BBB_20_2.0'].iloc[-1] # 下轨
            bb_upper = features_df['BBU_20_2.0'].iloc[-1] # 上轨
            current_close = features_df['close'].iloc[-1]

            if pd.isna(bb_middle) or pd.isna(bb_lower) or pd.isna(bb_upper):
                print(f"警告: {ticker} 的布林带数据不���整，跳过布林带检查。")
            else:
                # 做多持仓的平仓条件
                if position_info['type'] == 0: # 0 代表做多
                    if current_close < bb_middle:
                        signals_to_exit[ticker] = f"布林带信号 (收盘价 {current_close:.2f} 跌破中轨 {bb_middle:.2f})"
                    elif current_close < bb_lower:
                        signals_to_exit[ticker] = f"布林带信号 (收盘价 {current_close:.2f} 跌破下轨 {bb_lower:.2f})"
                # 做空持仓的平仓条件 (如果你的系统支持做空)
                # elif position_info['type'] == 1: # 1 代表做空
                #     if current_close > bb_middle:
                #         signals_to_exit[ticker] = f"布林带信号 (收盘价 {current_close:.2f} 突破中轨 {bb_middle:.2f})"
                #     elif current_close > bb_upper:
                #         signals_to_exit[ticker] = f"布林带信号 (收盘价 {current_close:.2f} 突破上轨 {bb_upper:.2f})"

            if ticker not in signals_to_exit: # 如果布林带和规则都没有触发平仓，再检查模型
                if prediction < exit_threshold:
                    signals_to_exit[ticker] = f"模型信号 (预测值: {prediction:.4f} < 阈值 {exit_threshold})"
                else:
                    print(f"决策: 继续持有 {ticker} (规则、布林带和模型均未触发平仓)")
                
        return signals_to_exit

    def check_and_execute_exits(self, exit_threshold: float = 0.0):
        """
        获取当前所有持仓，检查是否需要平仓，并执行平仓操作。
        """
        print("--- 开始执行每日平仓检查与操作 ---")
        positions_info = self.get_positions()
        
        long_positions = {symbol: info for symbol, info in positions_info.items() if info['type'] == 0}
        
        if not long_positions:
            print("当前无任何做多持仓，无需检查。")
            return

        print(f"当前做多持仓: {list(long_positions.keys())}")
        
        stocks_to_sell = self._check_positions_for_exit(long_positions, exit_threshold)

        if not stocks_to_sell:
            print("没有需要平仓的信号。")
            return

        print("检测到平仓信号，准备执行卖出操作:")
        for ticker, reason in stocks_to_sell.items():
            print(f"- {ticker}: {reason}")
            quantity_to_sell = long_positions[ticker]['quantity']
            self.place_order(ticker, 'SELL', 0, quantity_to_sell)
        
        # 清理已平仓股票的最高价记录
        for ticker in stocks_to_sell:
            if ticker in self.position_peak_prices:
                del self.position_peak_prices[ticker]

        print("--- 每日平仓检查与操作执行完毕 ---")

    def get_positions(self) -> dict:
        if mt5.terminal_info():
            positions = mt5.positions_get()
            if positions is None:
                return {}
            return {p.symbol: {'quantity': p.volume, 'type': p.type, 'price': p.price_open} for p in positions}
        print("Trader Info: MT5未连接，无法获取真实持仓。")
        return {}

    def get_account_info(self) -> dict:
        if mt5.terminal_info():
            info = mt5.account_info()
            if info:
                return info._asdict()
        print("Trader Info: MT5未连接，无法获取真实账户信息。")
        return {}

    def get_trade_log(self) -> list:
        print("Trader Info: get_trade_log 当前未对接MT5。")
        return []

if __name__ == '__main__':
    if not mt5.initialize():
        print("MT5 初始化失败, 无法执行测试。")
        mt5.shutdown()
    else:
        # 创建 Trader 实例时，可以传入自定义的止盈止损参数
        trader = Trader(
            stop_loss_pct=-0.08,
            take_profit_pct=0.16,
            trailing_stop_pct=-0.12
        )
        
        print("--- 开始执行平仓检查示例 ---")
        trader.check_and_execute_exits(exit_threshold=0.0)
        print("--- 平仓检查示例执行完毕 ---")

        mt5.shutdown()
