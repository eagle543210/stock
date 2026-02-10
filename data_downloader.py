import baostock as bs
import pandas as pd
import os
from tqdm import tqdm
import sys
import time
import yfinance as yf
import akshare as ak
import ccxt # <-- 新增：导入 ccxt 用于加密货币
from datetime import datetime # <-- 新增：导入 datetime

# --- 全局设置 ---
DATA_CACHE_DIR = 'stock_data_cache'
os.makedirs(DATA_CACHE_DIR, exist_ok=True)

# --- 新增：加密货币数据下载函数 ---
def download_crypto_data(ticker: str, start_date: str, end_date: str):
    """
    使用 ccxt 从币安 (Binance) 下载加密货币的历史日线数据。
    ticker 格式应为 'BTC/USDT', 'ETH/USDT' 等。
    """
    print(f"开始为加密货币 {ticker} 下载数据 (源: Binance)...")
    
    # 格式化文件名，例如 BTC/USDT -> btc_usdt
    formatted_ticker = ticker.replace('/', '_').lower()
    filename = f"crypto_{formatted_ticker}_daily.csv"
    filepath = os.path.join(DATA_CACHE_DIR, filename)

    exchange = ccxt.binance({
        'options': {
            'defaultType': 'spot',
        },
        'enableRateLimit': True,
    })

    try:
        # 将开始日期转换为毫秒时间戳
        since = exchange.parse8601(start_date + 'T00:00:00Z')
        end_timestamp = exchange.parse8601(end_date + 'T23:59:59Z')

        all_ohlcv = []
        
        print(f"正在从 {start_date} 下载到 {end_date}...")
        with tqdm(total=(end_timestamp - since) // (1000 * 60 * 60 * 24)) as pbar:
            while since < end_timestamp:
                try:
                    # 每次最多获取500条日线数据
                    ohlcv = exchange.fetch_ohlcv(ticker, '1d', since, limit=500)
                    if not ohlcv:
                        break
                    
                    first = ohlcv[0][0]
                    last = ohlcv[-1][0]
                    
                    all_ohlcv.extend(ohlcv)
                    
                    since = last + (1000 * 60 * 60 * 24) # 更新下一次请求的开始时间
                    
                    pbar.n = (last - exchange.parse8601(start_date + 'T00:00:00Z')) // (1000 * 60 * 60 * 24)
                    pbar.refresh()

                except ccxt.NetworkError as e:
                    print(f"网络错误，暂停10秒后重试... {e}")
                    time.sleep(10)
                except Exception as e:
                    print(f"获取数据分页时发生错误: {e}")
                    break
        
        if not all_ohlcv:
            print(f"未��获取到 {ticker} 的任何数据。")
            return

        # 转换为 DataFrame 并格式化
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.strftime('%Y-%m-%d')
        
        # 筛选出在指定日期范围内的数据
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        
        # 重新排列列顺序以匹配其他数据源
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
        
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"加密货币数据已成功下载并保存到 {filepath}")

    except Exception as e:
        print(f"下载加密货币 {ticker} 数据时发生严重错误: {e}")


def download_us_stock_data(ticker: str, start_date: str, end_date: str, max_retries: int = 3):
    """
    下载单个美股/ETF的历史日线数据，优先使用 yfinance，失败后自动尝试 akshare。
    增加了重试机制。
    """
    filename = f"us_{ticker.lower()}_daily.csv"
    filepath = os.path.join(DATA_CACHE_DIR, filename)

    # --- 尝试方法一：yfinance (首选) ---
    for attempt in range(max_retries):
        try:
            print(f"开始为股票/ETF {ticker} 下载数据 (首选: yfinance, 尝试次数: {attempt + 1}/{max_retries})...")
            start_date_yf = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
            end_date_yf = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
            
            stock_df = yf.download(ticker, start=start_date_yf, end=end_date_yf, auto_adjust=True, progress=False)
            
            if isinstance(stock_df, pd.DataFrame) and not stock_df.empty:
                stock_df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
                stock_df.reset_index(inplace=True)
                stock_df.rename(columns={'Date': 'date'}, inplace=True)
                stock_df.to_csv(filepath, index=False, encoding='utf-8-sig')
                print(f"yfinance 成功下载并保存了 {ticker} 的数据。")
                return # 成功则直接返回
            else:
                print(f"yfinance 未能获取到 {ticker} 的数据，将尝试备用数据源。")
                break # 如果返回空，说明股票代码可能有问题，直接跳到akshare

        except Exception as e:
            print(f"使用 yfinance 获取数据时发生错误: {e}。")
            if attempt < max_retries - 1:
                print("将在10秒后重试...")
                time.sleep(10)
            else:
                print("yfinance 达到最大重试次数，将尝试备用数据源。")

    # --- 尝试方法二：akshare (备用) ---
    for attempt in range(max_retries):
        try:
            print(f"开始为股票/ETF {ticker} 下载数据 (备用: akshare, 尝试次数: {attempt + 1}/{max_retries})...")
            start_date_ak = start_date.replace('-', '')
            end_date_ak = end_date.replace('-', '')

            stock_df = ak.stock_us_hist(symbol=ticker.upper(), start_date=start_date_ak, end_date=end_date_ak, adjust="qfq")
            print(f"akshare 返回的数据: {stock_df}")

            if isinstance(stock_df, pd.DataFrame) and not stock_df.empty:
                stock_df.rename(columns={'日期': 'date', '开盘': 'open', '最高': 'high', '最低': 'low', '收盘': 'close', '成交量': 'volume'}, inplace=True)
                stock_df['date'] = pd.to_datetime(stock_df['date'])
                required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
                final_df = stock_df[required_cols]
                final_df.to_csv(filepath, index=False, encoding='utf-8-sig')
                print(f"akshare 成功下载并保存了 {ticker} 的数据。")
                return # 成功则直接返回
            else:
                print(f"akshare 未能获取到 {ticker} 的数据。")
                if attempt < max_retries - 1:
                    print("将在10秒后重试...")
                    time.sleep(10)
                else:
                    print("akshare 达到最大重试次数。")

        except Exception as e:
            print(f"使用 akshare 获取美股数据时发生错误: {e}")
            if attempt < max_retries - 1:
                print("将在10秒后重试...")
                time.sleep(10)
    
    print(f"警告: 所有数据源都未能成功下载 {ticker} 的数据。")


def download_futures_data(ticker: str, start_date: str, end_date: str):
    """
    使用 akshare 下载单个国际商品期货的历史日线数据并保存到本地。
    """
    print(f"开始为商品期货 {ticker} 下载数据 (使用 akshare)...")
    
    filename = f"us_{ticker.lower()}_daily.csv"
    filepath = os.path.join(DATA_CACHE_DIR, filename)
    
    try:
        start_date_ak = start_date.replace('-', '')
        end_date_ak = end_date.replace('-', '')

        futures_df = ak.futures_foreign_hist(symbol=ticker.upper(), start_date=start_date_ak, end_date=end_date_ak)

        if futures_df is not None and not futures_df.empty:
            futures_df.rename(columns={'日期': 'date', '开盘': 'open', '最高': 'high', '最低': 'low', '收盘': 'close', '成交量': 'volume'}, inplace=True)
            futures_df['date'] = pd.to_datetime(futures_df['date'])
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
            final_df = futures_df[required_cols]
            final_df.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"akshare 成功下载并保存了期货 {ticker} 的数据。")
        else:
            print(f"akshare 未能获取到期货 {ticker} 的数据。")

    except Exception as e:
        print(f"使用 akshare 获取期货数据时发生错误: {e}")


def download_single_a_stock_data(ticker: str, start_date: str, end_date: str):
    """
    使用 baostock 下载单个A股的历史日线数据并保存到本地。
    """
    print(f"开始为A股股票 {ticker} 下载数据...")
    lg = bs.login()
    if lg.error_code != '0':
        print(f"baostock 登录失败: {lg.error_msg}")
        return

    filename = f"{ticker.replace('.', '_')}_daily.csv"
    filepath = os.path.join(DATA_CACHE_DIR, filename)

    start_date_bs = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
    end_date_bs = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

    try:
        rs = bs.query_history_k_data_plus(ticker, "date,code,open,high,low,close,preclose,volume,amount,pctChg", start_date=start_date_bs, end_date=end_date_bs, frequency="d", adjustflag="2")
        if rs.error_code != '0':
            print(f"警告: 获取A股 {ticker} 数据失败: {rs.error_msg}")
            return
        
        data_df = rs.get_data()
        if not data_df.empty:
            data_df.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"A股数据已成功下载并保存到 {filepath}")
        else:
            print(f"警告: baostock 未能获取到A股 {ticker} 的数据。")

    except Exception as e:
        print(f"使用 baostock 获取A股数据时发生错误: {e}")
    finally:
        bs.logout()

def download_all_stock_data(start_date: str = '2020-01-01', end_date: str = '2023-12-31'):
    lg = bs.login()
    if lg.error_code != '0': return
    stock_rs = bs.query_all_stock(day=end_date)
    stock_df = stock_rs.get_data()
    if stock_df.empty:
        print(f"警告: baostock 在 {end_date} 未返回任何股票列表数据。请检查日期或API状态。")
        bs.logout()
        return
    print(f"Baostock 返回的列名: {stock_df.columns.tolist()}")
    # 使用 tradeStatus 列来过滤，'1' 表示正常交易
    a_stock_df = stock_df[(stock_df['tradeStatus'] == '1') & (stock_df['code'].str.match(r'^(sh|sz)\.'))]
    all_codes = a_stock_df['code'].tolist()
    for code in tqdm(all_codes, desc="下载进度"):
        cache_path = os.path.join(DATA_CACHE_DIR, f'{code.replace(".", "_")}_daily.csv')
        if os.path.exists(cache_path): continue
        try:
            rs = bs.query_history_k_data_plus(code, "date,code,open,high,low,close,preclose,volume,amount,pctChg", start_date=start_date, end_date=end_date, frequency="d", adjustflag="2")
            if rs.error_code != '0': continue
            data_df = rs.get_data()
            if not data_df.empty:
                data_df.to_csv(cache_path, index=False, encoding='utf-8-sig')
        except Exception as e:
            print(f"处理 {code} 时发生未知异常: {e}")
            continue
    bs.logout()

if __name__ == '__main__':
    # 增加更灵活的命令行参数处理
    if len(sys.argv) == 2:
        # 只提供 ticker，使用默认日期范围
        ticker = sys.argv[1]
        start_date = '20200101' # 使用 YYYYMMDD 格式
        end_date = datetime.now().strftime('%Y%m%d') # 使用 YYYYMMDD 格式
        
        if '/' in ticker:
            download_crypto_data(ticker, start_date, end_date)
        elif ticker.startswith('sh.') or ticker.startswith('sz.'):
            download_single_a_stock_data(ticker, start_date, end_date)
        elif ticker.upper() in ['WTI', 'CL', 'BRENT', 'BRN']:
            download_futures_data(ticker, start_date, end_date)
        else:
            download_us_stock_data(ticker, start_date, end_date)

    elif len(sys.argv) >= 4:
        # 提供 ticker, start_date, end_date
        ticker = sys.argv[1]
        start_date = sys.argv[2]
        end_date = sys.argv[3]
        
        if '/' in ticker:
            download_crypto_data(ticker, start_date, end_date)
        elif ticker.startswith('sh.') or ticker.startswith('sz.'):
            download_single_a_stock_data(ticker, start_date, end_date)
        elif ticker.upper() in ['WTI', 'CL', 'BRENT', 'BRN']:
            download_futures_data(ticker, start_date, end_date)
        else:
            download_us_stock_data(ticker, start_date, end_date)
    else:
        # 如果没有参数，默认执行A股全量下载
        print("未提供特定股票代码，将执行A股全量数据下载...")
        today = datetime.now().strftime('%Y-%m-%d')
        download_all_stock_data(start_date='2020-01-01', end_date=today)