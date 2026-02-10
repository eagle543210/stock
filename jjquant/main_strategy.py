from __future__ import print_function, absolute_import, unicode_literals
from gm.api import *

import datetime
import pandas as pd
import joblib
import sys
import os
from typing import List

# 将项目根目录添加到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from feature_generator import generate_features

'''
本策略基于我们自定义的随机森林模型进行交易决策。

开仓逻辑:
1. 模型预测未来5日收益率 > entry_threshold (开仓阈值)
2. 当前收盘价 > 布林带中轨

平仓逻辑:
1. 固定止损: 收益率 <= stop_loss_pct
2. 固定止盈: 收益率 >= take_profit_pct
3. 移动止损: 从持仓期间最高价回撤 >= trailing_stop_pct
4. 布林带信号: 收盘价跌破布林带中轨
'''

def init(context):
    # 策略参数
    context.stop_loss_pct = -0.08 
    context.take_profit_pct = 0.16
    context.trailing_stop_pct = -0.12
    context.entry_threshold = 0.02  # 模型预测的最小收益率
    context.capital_per_trade = 0.2 # 每笔交易使用的资金占总资产的比例

    # 股票池 (请确保有对应的模型文件, e.g., 600519_model.joblib)
    context.stock_pool = ['SHSE.600519', 'SZSE.300750', 'SHSE.601869']
    
    # 运行时变量
    context.position_peak_prices = {} # 用于跟踪移动止损的最高价

    # 订阅股票池中所有股票的日线行情
    subscribe(symbols=','.join(context.stock_pool), frequency='1d')


def on_bar(context, bars):
    # type: (Context, List[Bar]) -> NoReturn
    """
    bar数据推送事件。对于日线，在每个交易日收盘后触发。
    """
    # --- 1. 优先处理平仓逻辑 ---
    positions = get_positions()
    for position in positions:
        latest_bar = next((bar for bar in bars if bar.symbol == position.symbol), None)
        if not latest_bar:
            continue

        exit_reason = check_exit_signal(context, position, latest_bar)
        if exit_reason:
            print(f"{context.now.strftime('%Y-%m-%d')}: 平仓信号 for {position.symbol}. 原因: {exit_reason}")
            order_target_percent(symbol=position.symbol, percent=0, order_type=OrderType_Market, position_side=PositionSide_Long)
            # 清理移动止损记录
            if position.symbol in context.position_peak_prices:
                del context.position_peak_prices[position.symbol]

    # --- 2. 后处理开仓逻辑 ---
    account = get_account()
    if not account:
        print("无法获取账户信息，跳过开仓逻辑。")
        return
        
    # 过滤掉已持仓的股票
    positions = get_positions()
    held_symbols = [p.symbol for p in positions]

    for bar in bars:
        if bar.symbol in held_symbols:
            continue

        if check_entry_signal(context, bar):
            print(f"{context.now.strftime('%Y-%m-%d')}: 开仓信号 for {bar.symbol}.")
            order_value = account.nav * context.capital_per_trade
            
            if order_value > 0:
                order_target_value(symbol=bar.symbol, value=order_value, order_type=OrderType_Market, position_side=PositionSide_Long)


def check_entry_signal(context, bar):
    # type: (Context, Bar) -> bool
    """
    检查单个股票是否满足所有开仓条件。
    """
    symbol = bar.symbol
    ticker = symbol.split('.')[1]
    
    model_path = f'./{ticker}_model.joblib'
    try:
        model_payload = joblib.load(model_path)
        model = model_payload['model']
        model_features = model_payload['features']
    except (FileNotFoundError, KeyError):
        return False

    try:
        raw_df = history_n(symbol=symbol, frequency='1d', count=250, end_time=bar.eob, fill_missing='last', df=True)
        if raw_df is None or raw_df.empty or len(raw_df) < 50:
            return False

        features_df, _ = generate_features(raw_df.copy())
        if features_df.empty:
            return False

        missing_features = [f for f in model_features if f not in features_df.columns]
        if missing_features:
            return False

        latest_features = features_df.iloc[-1][model_features]
        if latest_features.isnull().any():
            return False
    except Exception as e:
        print(f"为 {ticker} 处理开仓数据时发生错误: {e}")
        return False

    prediction = model.predict(latest_features.to_frame().T.astype(float))[0]
    model_signal = prediction > context.entry_threshold

    bb_middle = features_df['BBL_20_2.0'].iloc[-1]
    current_close = features_df['close'].iloc[-1]
    
    if pd.isna(bb_middle):
        bb_signal = False
    else:
        bb_signal = current_close > bb_middle

    if model_signal and bb_signal:
        print(f"开仓信号确认: {symbol}. 模型预测 {prediction:.4f}, 收盘价 {current_close:.2f} > 布林中轨 {bb_middle:.2f}")
        return True
    
    return False


def check_exit_signal(context, position, bar):
    # type: (Context, Position, Bar) -> str or None
    """
    检查单个持仓是否满足任何平仓条件。返回平仓原因字符串或None。
    """
    symbol = position.symbol
    ticker = symbol.split('.')[1]
    current_price = bar.close
    open_price = position.vwap

    # --- 规则检查 ---
    if symbol not in context.position_peak_prices:
        context.position_peak_prices[symbol] = open_price
    context.position_peak_prices[symbol] = max(context.position_peak_prices.get(symbol, 0), current_price)
    peak_price = context.position_peak_prices[symbol]

    current_return = (current_price / open_price) - 1
    drawdown_from_peak = (current_price / peak_price) - 1

    if current_return <= context.stop_loss_pct:
        return f"固定止损 (收益率: {current_return:.2%})"
    if current_return >= context.take_profit_pct:
        return f"固定止盈 (收益率: {current_return:.2%})"
    if drawdown_from_peak <= context.trailing_stop_pct:
        return f"移动止损 (从最高价 {peak_price:.2f} 回撤: {drawdown_from_peak:.2%})"

    # --- 技术指标检查 ---
    try:
        raw_df = history_n(symbol=symbol, frequency='1d', count=250, end_time=bar.eob, fill_missing='last', df=True)
        if raw_df is None or raw_df.empty:
            return None

        features_df, _ = generate_features(raw_df.copy())
        if features_df.empty:
            return None

        bb_middle = features_df['BBL_20_2.0'].iloc[-1]
        current_close = features_df['close'].iloc[-1]

        if not pd.isna(bb_middle) and current_close < bb_middle:
            return f"布林带信号 (收盘价 {current_close:.2f} 跌破中轨 {bb_middle:.2f})"
            
    except Exception as e:
        print(f"为 {ticker} 处理平仓数据时发生错误: {e}")
        return None

    return None


def on_order_status(context, order):
    # type: (Context, Order) -> NoReturn
    """
    委托状态更新事件。
    """
    if order.status == 3: # 3代表委托全部成交
        side_effect = '未知操作'
        if order.position_effect == 1: # 1为开仓
            side_effect = '开多仓' if order.side == 1 else '开空仓'
        elif order.position_effect == 2: # 2为平仓
            side_effect = '平空仓' if order.side == 1 else '平多仓'
        
        order_type_word = '限价' if order.order_type==1 else '市价'
        print('{}: {}, 标的: {}, 操作: {}, 价格: {}, 数量: {}'.format(
            context.now, order_type_word, order.symbol, side_effect, order.price, order.volume))


def on_backtest_finished(context, indicator):
    # type: (Context, Indicator) -> NoReturn
    """
    回测结束事件。
    """
    print('*'*50)
    print('回测已完成，请通过右上角“回测历史”功能查询详情。')


if __name__ == '__main__':
    '''
    strategy_id策略ID,由系统生成
    filename文件名,请与本文件名保持一致
    mode实时模式:MODE_LIVE回测模式:MODE_BACKTEST
    token绑定计算机的ID,可在系统设置-密钥管理中生成
    '''
    run(strategy_id='strategy_id',
        filename='main_strategy.py', # 注意：文件名需要与当前文件名一致
        mode=MODE_BACKTEST,
        token='879fe6f27a8d45f09ed4aa4a60d7761b244ad3d2', # 已替换为您的真实TOKEN
        backtest_start_time='2023-01-01 09:00:00',
        backtest_end_time='2023-12-31 15:00:00',
        backtest_adjust=ADJUST_PREV,
        backtest_initial_cash=1000000,
        backtest_commission_ratio=0.0003,
        backtest_slippage_ratio=0.0001,
        backtest_match_mode=1)
