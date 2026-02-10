
# -*- coding: utf-8 -*-
import yfinance as yf
import os
from datetime import datetime, timedelta

# --- 配置 ---
DATA_CACHE_DIR = 'stock_data_cache'
# 定义我们要下载的宏观/情绪因子及其对应的yfinance代码
FACTOR_TICKERS = {
    'GSPC': '^GSPC',      # S&P 500 Index
    'IXIC': '^IXIC',      # NASDAQ Composite Index
    'VIX': '^VIX',        # CBOE Volatility Index (Fear Index)
    'DXY': 'DX-Y.NYB',    # US Dollar Index
}

def download_factor_data(start_date: str = "2010-01-01", end_date: str = None):
    """
    下载所有定义的宏观/情绪因子数据，并保存到 stock_data_cache 目录。
    """
    if not os.path.exists(DATA_CACHE_DIR):
        print(f"创建数据缓存目录: {DATA_CACHE_DIR}")
        os.makedirs(DATA_CACHE_DIR)

    if end_date is None:
        end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    print(f"开始下载因子数据，时间范围: {start_date} 到 {end_date}")

    for name, ticker in FACTOR_TICKERS.items():
        try:
            print(f"正在下载 {name} ({ticker})...")
            # 使用 yfinance 下载数据
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if data.empty:
                print(f"警告: 未能下载 {name} 的数据。")
                continue

            # 重置索引，使 'Date' 成为一列
            data.reset_index(inplace=True)
            
            # 为了与我们现有的数据格式保持一致，重命名列
            data.rename(columns={
                'Date': 'date',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Adj Close': 'adj_close',
                'Volume': 'volume'
            }, inplace=True)

            # 将 'date' 列转换为 'YYYY-MM-DD' 格式的字符串
            data['date'] = data['date'].dt.strftime('%Y-%m-%d')

            # 构建保存路径
            file_path = os.path.join(DATA_CACHE_DIR, f"factor_{name.lower()}_daily.csv")
            
            # 保存为 CSV 文件
            data.to_csv(file_path, index=False)
            print(f"✅ 成功将 {name} 数据保存至 {file_path}")

        except Exception as e:
            print(f"❌ 下载或处理 {name} ({ticker}) 时发生错误: {e}")

if __name__ == '__main__':
    print("--- 开始���行因子数据下载脚本 ---")
    download_factor_data()
    print("--- 因子数据下载脚本执行完毕 ---")
