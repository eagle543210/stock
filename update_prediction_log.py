

import pandas as pd
import os
from datetime import datetime, timedelta
from data_handler import get_any_stock_data
from tqdm import tqdm

# --- 配置 ---
PREDICTION_LOG_FILE = 'prediction_log.csv'
FUTURE_DAYS = 5  # 这个值必须与 model_trainer.py 中 create_target_labels 的 future_days 一致
TRADING_DAYS_IN_YEAR = 252 # 大约值，用于计算
BUFFER_DAYS = int(FUTURE_DAYS * 1.5) # 为了确保能获取到足够的未来交易日数据，增加一些缓冲

def update_log_file():
    """
    更新 prediction_log.csv 文件，计算其中缺失的 actual_5d_return 和 error。
    """
    if not os.path.exists(PREDICTION_LOG_FILE):
        print(f"错误: 预测日志文件 '{PREDICTION_LOG_FILE}' 不存在。请先运行API以生成预测。")
        return

    try:
        df = pd.read_csv(PREDICTION_LOG_FILE)
    except pd.errors.EmptyDataError:
        print("预测日志文件为空，无需更新。")
        return

    # --- 新增：健壮性检查 ---
    required_columns = ['prediction_date', 'actual_5d_return']
    if not all(col in df.columns for col in required_columns):
        print(f"错误: 预测日志文件 '{PREDICTION_LOG_FILE}' 缺少必要的列。")
        print(f"期望的列: {required_columns}")
        print(f"实际找到的列: {df.columns.tolist()}")
        return
    # --- 检查结束 ---
        
    # 将日期字符串转换为 datetime 对象以便比较
    df['prediction_date_dt'] = pd.to_datetime(df['prediction_date'])

    # 筛选出需要更新的行：
    # 1. actual_5d_return 为空
    # 2. 预测日期距今已超过 FUTURE_DAYS + buffer，确保我们能获取到未来的数据
    cutoff_date = datetime.now() - timedelta(days=FUTURE_DAYS + 2) # 增加2天缓冲
    to_update_df = df[df['actual_5d_return'].isnull() & (df['prediction_date_dt'] < cutoff_date)].copy()

    if to_update_df.empty:
        print("没有需要更新的预测记录。")
        return

    print(f"找到 {len(to_update_df)} 条需要更新的预测记录...")
    
    updated_count = 0
    
    # 使用 tqdm 显示进度条
    for index, row in tqdm(to_update_df.iterrows(), total=to_update_df.shape[0], desc="更新预测日志"):
        try:
            ticker = row['ticker']
            prediction_date = row['prediction_date_dt']
            base_prediction = row['base_prediction']

            # 获取从预测日期开始的一小段时间的行情数据
            start_date_str = prediction_date.strftime('%Y%m%d')
            end_date_str = (prediction_date + timedelta(days=BUFFER_DAYS)).strftime('%Y%m%d')
            
            # 调用 data_handler 获取数据
            market_data = get_any_stock_data(ticker, start_date=start_date_str, end_date=end_date_str)
            
            if market_data is None or market_data.empty or 'close' not in market_data.columns:
                continue

            # 确保 market_data 的索引是 datetime 类型
            if not isinstance(market_data.index, pd.DatetimeIndex):
                 market_data['date'] = pd.to_datetime(market_data['date'])
                 market_data.set_index('date', inplace=True)

            # 找到预测日期的收盘价
            # 使用 asof 查找最接近预测日期的那个交易日
            current_close_series = market_data.asof(prediction_date)
            if pd.isna(current_close_series['close']):
                continue
            current_close = current_close_series['close']

            # 找到 N 个交易日后的收盘价
            future_date_index = market_data.index.searchsorted(prediction_date, side='right') + (FUTURE_DAYS -1)

            if future_date_index < len(market_data):
                future_close = market_data.iloc[future_date_index]['close']
                
                # 计算真实收益率和误差
                actual_return = (future_close / current_close) - 1
                error = actual_return - base_prediction

                # 更新原始 DataFrame 中的值
                df.loc[index, 'actual_5d_return'] = actual_return
                df.loc[index, 'error'] = error
                updated_count += 1

        except Exception as e:
            print(f"\n处理行 {index} (Ticker: {row['ticker']}) 时发生错误: {e}")
            continue
            
    if updated_count > 0:
        # 删除辅助列并保存回CSV
        df.drop(columns=['prediction_date_dt'], inplace=True)
        df.to_csv(PREDICTION_LOG_FILE, index=False)
        print(f"\n成功更新了 {updated_count} 条记录。")
    else:
        print("\n没有记录被成功更新。")


if __name__ == '__main__':
    print("--- 开始更新预测日志文件 ---")
    update_log_file()
    print("--- 更新完成 ---")

