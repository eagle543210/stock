import pandas as pd
from datetime import datetime
import re
import time
import os
from data_downloader import download_single_a_stock_data, download_us_stock_data, download_crypto_data # 导入下载函数

# 定义缓存目录
CACHE_DIR = 'stock_data_cache'

def _preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    对从CSV加载的DataFrame进行预处理，确保数据类型正确。
    """
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'turnover', 'amplitude', 'change_pct', 'change_amt', 'turnover_rate']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    print("DataFrame 预处理完成，数据类型已强制转换为数值型。")
    return df

def get_stock_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取指定A股股票在给定日期范围内的历史日线数据。
    从本地缓存加载，如果不存在则通过 data_downloader 下载并存入缓存。
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    filename = f"{ticker.replace(".", "_")}_daily.csv"
    cache_path = os.path.join(CACHE_DIR, filename)

    if os.path.exists(cache_path):
        print(f"正在从本地缓存加载A股数据: {cache_path}")
        try:
            df = pd.read_csv(cache_path, encoding='utf-8-sig', engine='python')
            return _preprocess_dataframe(df)
        except Exception as e:
            print(f"读取缓存文件 {cache_path} 失败: {e}。将尝试从 data_downloader 下载。")

    print(f"正在通过 data_downloader 下载A股股票 {ticker} 的数据...")
    download_single_a_stock_data(ticker, start_date, end_date)
    
    if os.path.exists(cache_path):
        try:
            df = pd.read_csv(cache_path, encoding='utf-8-sig', engine='python')
            return _preprocess_dataframe(df)
        except Exception as e:
            print(f"从 data_downloader 下载后读取缓存文件 {cache_path} 失败: {e}。")
            return pd.DataFrame()
    else:
        print(f"警告: data_downloader 未能成功下载A股 {ticker} 的数据。")
        return pd.DataFrame()

def get_us_stock_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取指定美股股票在给定日期范围内的历史日线数据。
    从本地缓存加载，如果不存在则通过 data_downloader 下载并存入缓存。
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    filename = f"us_{ticker}_daily.csv"
    cache_path = os.path.join(CACHE_DIR, filename)

    if os.path.exists(cache_path):
        print(f"正在从本地缓存加载美股数据: {cache_path}")
        try:
            df = pd.read_csv(cache_path, encoding='utf-8-sig', engine='python')
            return _preprocess_dataframe(df)
        except Exception as e:
            print(f"读取缓存文件 {cache_path} 失败: {e}。将尝试从 data_downloader 下载。")

    print(f"正在通过 data_downloader 下载美股股票 {ticker} 的数据...")
    download_us_stock_data(ticker, start_date, end_date)
    
    if os.path.exists(cache_path):
        try:
            df = pd.read_csv(cache_path, encoding='utf-8-sig', engine='python')
            return _preprocess_dataframe(df)
        except Exception as e:
            print(f"从 data_downloader 下载后读取缓存文件 {cache_path} 失败: {e}。")
            return pd.DataFrame()
    else:
        print(f"警告: data_downloader 未能成功下载美股 {ticker} 的数据。")
        return pd.DataFrame()

# --- 新增：获取加密货币数据函数 ---
def get_crypto_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取指定加密货币在给定日期范围内的历史日线数据。
    从本地缓存加载，如果不存在则通过 data_downloader 下载并存入缓存。
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    formatted_ticker = ticker.replace('/', '_').lower()
    filename = f"crypto_{formatted_ticker}_daily.csv"
    cache_path = os.path.join(CACHE_DIR, filename)

    if os.path.exists(cache_path):
        print(f"正在从本地缓存加载加密货币数据: {cache_path}")
        try:
            df = pd.read_csv(cache_path, encoding='utf-8-sig', engine='python')
            return _preprocess_dataframe(df)
        except Exception as e:
            print(f"读取缓存文件 {cache_path} 失败: {e}。将尝试从 data_downloader 下载。")

    print(f"正在通过 data_downloader 下载加密货币 {ticker} 的数据...")
    download_crypto_data(ticker, start_date, end_date)
    
    if os.path.exists(cache_path):
        try:
            df = pd.read_csv(cache_path, encoding='utf-8-sig', engine='python')
            return _preprocess_dataframe(df)
        except Exception as e:
            print(f"从 data_downloader 下载后读取缓存文件 {cache_path} 失败: {e}。")
            return pd.DataFrame()
    else:
        print(f"警告: data_downloader 未能成功下载加密货币 {ticker} 的数据。")
        return pd.DataFrame()

def get_any_stock_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    根据股票代码的格式自动选择数据源获取数据。
    """
    ticker_upper = ticker.upper()
    print(f"DEBUG: get_any_stock_data 接收到的 ticker_upper: {ticker_upper}")
    
    # --- 修改：增加加密货币的判断逻辑 ---
    if '/' in ticker_upper or (len(ticker_upper) > 5 and not (ticker_upper.startswith('SH.') or ticker_upper.startswith('SZ.'))):
        print(f"检测到加密货币或长代码 (按加密货币处理): {ticker_upper}")
        return get_crypto_data(ticker_upper, start_date, end_date)
    elif '.' in ticker_upper:
        print(f"检测到A股代码: {ticker_upper}")
        return get_stock_data(ticker_upper, start_date, end_date)
    else:
        print(f"检测到非A股代码 (按美股处理): {ticker_upper}")
        return get_us_stock_data(ticker_upper, start_date, end_date)

def get_fundamental_data(ticker: str) -> pd.DataFrame:
    """
    获取指定A股股票的主要财务指标历史数据。
    注意：此函数仍使用 akshare，因为 data_downloader 中没有对应的财务数据下载逻辑。
    """
    try:
        print(f"正在获取股票代码 {ticker} 的历史财务指标...")
        pure_ticker = ticker.split('.')[-1] if '.' in ticker else ticker
        stock_financial_df = ak.stock_financial_analysis_indicator(symbol=pure_ticker)
        if stock_financial_df.empty:
            print(f"警告: 未能获取到股票 {ticker} 的财务指标数据。")
            return pd.DataFrame()

        fundamental_data = stock_financial_df[['日期', '市盈率(PE, TTM)', '市净率(PB)', '股息率(TTM)']].copy()
        fundamental_data.rename(columns={
            '日期': 'date',
            '市盈率(PE, TTM)': 'pe_ttm',
            '市净率(PB)': 'pb',
            '股息率(TTM)': 'dividend_yield_ttm'
        }, inplace=True)

        fundamental_data['date'] = pd.to_datetime(fundamental_data['date'])
        fundamental_data.set_index('date', inplace=True);
        print(f"成功获取并处理了 {len(fundamental_data)} 条财务指标数据。")
        return fundamental_data
    except Exception as e:
        print(f"获取财务指标时发生错误: {e}")
        return pd.DataFrame()

if __name__ == '__main__':
    print("\n--- 测试A股数据获取 (通过 data_downloader) ---")
    stock_data_a = get_any_stock_data(ticker='sh.688795', start_date='20200101', end_date='20231231')
    if not stock_data_a.empty:
        print(stock_data_a.head())
        print(stock_data_a.info())
    else:
        print("未能获取到A股数据。")

    print("\n--- 测试美股数据获取 (通过 data_downloader) ---")
    stock_data_us = get_any_stock_data(ticker='NVDA', start_date='20230101', end_date='20230201')
    if not stock_data_us.empty:
        print(stock_data_us.head())
        print(stock_data_us.info())

    print("\n--- 测试加密货币数据获取 (通过 data_downloader) ---")
    crypto_data = get_any_stock_data(ticker='BTC/USDT', start_date='20230101', end_date='20230201')
    if not crypto_data.empty:
        print(crypto_data.head())
        print(crypto_data.info())
    else:
        print("未能获取到加密货币数据。")

    print("\n--- 测试长代码 (按加密货币处理) ---")
    long_code_data = get_any_stock_data(ticker='BCTXUSDT', start_date='20230101', end_date='20230201')
    if not long_code_data.empty:
        print(long_code_data.head())
        print(long_code_data.info())
    else:
        print("未能获取到长代码数据。")