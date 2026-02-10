from __future__ import print_function, absolute_import, unicode_literals
from gm.api import *
import json
import os
import time
from typing import List

'''
本策略是一个信号接收与执行器。
它不包含任何交易逻辑，其唯一任务是：
1. 定时读取一个名为 `signals.json` 的外部信号文件。
2. 解析文件中状态为 "NEW" 的新交易指令。
3. 根据指令执行交易（开仓或平仓）。
4. 将已执行的指令状态更新为 "PROCESSED"，防止重复下单。

本地的 "大脑" 程序 (live_trader.py) 负责生成 `signals.json` 文件并上传至本策略的根目录。
'''

# 定义信号文件的路径
SIGNAL_FILE_PATH = 'signals.json'

def init(context):
    # 设置要操作的仿真账户ID
    context.account_id = '23d335f3-e463-11f0-a-0eb-00163e022aa6'
    
    # 设置定时任务，在每个交易日的 09:31:00 启动信号检查循环
    schedule(schedule_func=start_signal_check_loop, date_rule='1d', time_rule='09:31:00')
    print(f"信号接收策略已启动，监控账户ID: {context.account_id}")
    print(f"将在每个交易日 09:31:00 启动信号检查循环。")


def start_signal_check_loop(context):
    # type: (Context) -> None
    """
    启动一个在交易时段内持续运行的信号检查循环。
    """
    print(f"{context.now}: 启动信号检查循环...")
    
    # 循环直到收盘后
    while context.now.hour < 15:
        check_signals_and_trade(context)
        # 等待60秒
        time.sleep(60)
    
    print(f"{context.now}: 今日交易时段结束，信号检查循环停止。")


def check_signals_and_trade(context):
    # type: (Context) -> None
    """
    检查和执行交易信号的核心逻辑。
    """
    print(f"{context.now}: 正在检查信号...")
    
    # 检查信号文件是否存在
    if not os.path.exists(SIGNAL_FILE_PATH):
        return

    # 读取并处理信号
    try:
        with open(SIGNAL_FILE_PATH, 'r+') as f:
            signals = json.load(f)
            
            has_new_signals = False
            for signal in signals:
                # 只处理新信号
                if signal.get('status') == 'NEW':
                    has_new_signals = True
                    print(f"接收到新信号: {signal}")
                    
                    # 执行交易
                    order_target_percent(
                        symbol=signal['symbol'],
                        percent=signal['target_percent'],
                        order_type=OrderType_Market,
                        position_side=PositionSide_Long, # 仅处理做多信号
                        account=context.account_id
                    )
                    
                    # 更新信号状态
                    signal['status'] = 'PROCESSED'
            
            # 如果有新信号被处理，则写回文件
            if has_new_signals:
                f.seek(0)
                f.truncate()
                json.dump(signals, f, indent=4)
                print("信号处理完毕，已更新信号文件。")

    except json.JSONDecodeError:
        print(f"错误: 信号文件 {SIGNAL_FILE_PATH} 格式不正确，无法解析。")
    except Exception as e:
        print(f"处理信号时发生未知错误: {e}")


def on_order_status(context, order):
    # type: (Context, Order) -> NoReturn
    """
    委托状态更新事件，用于确认交易执行情况。
    """
    if order.status == 3: # 3代表委托全部成交
        print(f"交易确认: {order.symbol} 已按指令成交。")


def on_backtest_finished(context, indicator):
    print('*'*50)
    print('策略运行结束。')


if __name__ == '__main__':
    run(strategy_id='strategy_id_signal_receiver',
        filename='signal_receiver_strategy.py',
        mode=MODE_LIVE,
        token='879fe6f27a8d45f09ed4aa4a60d7761b244ad3d2'
    )