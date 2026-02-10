import pandas as pd
import numpy as np
import os
try:
    import pandas_ta as ta
except Exception:
    ta = None

# --- 全局加载因子数据 ---
DATA_CACHE_DIR = 'stock_data_cache'
FACTOR_FILES = {
    'gspc': os.path.join(DATA_CACHE_DIR, 'factor_gspc_daily.csv'),
    'ixic': os.path.join(DATA_CACHE_DIR, 'factor_ixic_daily.csv'),
    'vix': os.path.join(DATA_CACHE_DIR, 'factor_vix_daily.csv'),
    'dxy': os.path.join(DATA_CACHE_DIR, 'factor_dxy_daily.csv'),
    'news_sentiment': os.path.join(DATA_CACHE_DIR, 'factor_news_sentiment_daily.csv'),
}
factor_data = {}

def _load_factor_data():
    """在首次导入时加载所有因子数据到全局变量中"""
    print("正在加载宏观/情绪因子数据...")
    for name, path in FACTOR_FILES.items():
        if os.path.exists(path):
            try:
                df = pd.read_csv(path, skiprows=[1])
                df['date'] = pd.to_datetime(df['date']) # 转换为datetime对象以便合并
                factor_data[name] = df
                print(f"成功加载因子: {name}")
            except Exception as e:
                print(f"加载因子 {name} 失败: {e}")
        else:
            print(f"因子文件不存在: {path}")

# 在模块加载时执行一次
_load_factor_data()

def generate_fibonacci_features(df: pd.DataFrame, lookback: int = 15):
    """
    计算斐波那契回撤水平并生成相关特征。
    
    :param df: 包含 'high' 和 'low' 列的 DataFrame。
    :param lookback: 用于寻找波段高/低点的回顾周期。
    """
    print(f"正在为 {lookback} 周期生成斐波那契特征...")
    
    # 1. 寻找最近的波段高点和低点
    df['swing_high'] = df['high'].rolling(window=lookback*2+1, center=True).max() == df['high']
    df['swing_low'] = df['low'].rolling(window=lookback*2+1, center=True).min() == df['low']

    # 2. 确定当前趋势并计算回撤水平
    last_swing_high_idx = -1
    last_swing_low_idx = -1
    
    ratios = [0.236, 0.382, 0.5, 0.618, 0.786]
    
    fib_level_cols = [f'fib_{r}' for r in ratios]
    for col in fib_level_cols:
        df[col] = np.nan

    for i in range(len(df)):
        if df['swing_high'].iloc[i]:
            last_swing_high_idx = i
        if df['swing_low'].iloc[i]:
            last_swing_low_idx = i

        if last_swing_high_idx != -1 and last_swing_low_idx != -1:
            high_price = df['high'].iloc[last_swing_high_idx]
            low_price = df['low'].iloc[last_swing_low_idx]
            price_range = high_price - low_price

            if price_range > 0:
                if last_swing_high_idx > last_swing_low_idx: # 上涨趋势
                    for r in ratios:
                        df.loc[df.index[i], f'fib_{r}'] = high_price - price_range * r
                else: # 下跌趋势
                    for r in ratios:
                        df.loc[df.index[i], f'fib_{r}'] = low_price + price_range * r

    # 3. 生成特征
    df['fib_zone'] = 0
    for i, r in enumerate(ratios):
        df.loc[df['close'] > df[f'fib_{r}'], 'fib_zone'] = i + 1
        
    def min_dist_to_fib(row):
        distances = [abs(row['close'] - row[col]) for col in fib_level_cols if pd.notna(row[col])]
        return min(distances) if distances else np.nan
        
    df['dist_to_fib'] = df.apply(min_dist_to_fib, axis=1)

    # 清理临时列
    df.drop(columns=['swing_high', 'swing_low'] + fib_level_cols, inplace=True)
    
    print("斐波那契特征生成完毕。")
    return df

def generate_fib_extension_features(df: pd.DataFrame, lookback: int = 15):
    """
    计算斐波那契扩展水平并生成相关特征。
    
    :param df: 包含 'high', 'low', 'close' 列的 DataFrame。
    :param lookback: 用于寻找波段高/低点的回顾周期。
    """
    print(f"正在为 {lookback} 周期生成斐波那契扩展特征...")

    # 1. 识别所有的波段高/低点
    df['is_swing_high'] = df['high'].rolling(window=lookback*2+1, center=True).max() == df['high']
    df['is_swing_low'] = df['low'].rolling(window=lookback*2+1, center=True).min() == df['low']

    swing_points = []
    for i in range(len(df)):
        if df['is_swing_high'].iloc[i]:
            swing_points.append({'idx': i, 'price': df['high'].iloc[i], 'type': 'H'})
        if df['is_swing_low'].iloc[i]:
            swing_points.append({'idx': i, 'price': df['low'].iloc[i], 'type': 'L'})

    # 2. 寻找 A-B-C 结构并计算扩展位
    df['fib_ext_1.618'] = np.nan

    if len(swing_points) >= 3:
        for i in range(2, len(swing_points)):
            p1, p2, p3 = swing_points[i-2], swing_points[i-1], swing_points[i]
            
            start_idx = p3['idx']
            end_idx = swing_points[i+1]['idx'] if i + 1 < len(swing_points) else len(df)

            # 上涨趋势的扩展: Low -> High -> Low (A->B->C)
            if p1['type'] == 'L' and p2['type'] == 'H' and p3['type'] == 'L':
                if p3['price'] > p1['price']:
                    trend_range = p2['price'] - p1['price']
                    target_price = p3['price'] + trend_range * 1.618
                    df.loc[df.index[start_idx:end_idx], 'fib_ext_1.618'] = target_price

            # 下跌趋势的扩展: High -> Low -> High (A->B->C)
            elif p1['type'] == 'H' and p2['type'] == 'L' and p3['type'] == 'H':
                if p3['price'] < p1['price']:
                    trend_range = p1['price'] - p2['price']
                    target_price = p3['price'] - trend_range * 1.618
                    df.loc[df.index[start_idx:end_idx], 'fib_ext_1.618'] = target_price

    # 3. 生成特征
    df['dist_to_ext_1618'] = (df['close'] - df['fib_ext_1.618']) / df['close']
    df['dist_to_ext_1618'] = df['dist_to_ext_1618'].fillna(0)

    # 清理临时列
    df.drop(columns=['is_swing_high', 'is_swing_low', 'fib_ext_1.618'], inplace=True)
    
    print("斐波那契扩展特征生成完毕。")
    return df

def generate_fourier_features(df: pd.DataFrame, n_components: int = 5, lookback: int = 60):
    """
    计算傅里叶级数特征。
    :param df: 包含 'close' 列的 DataFrame。
    :param n_components: 要提取的傅里叶分量数量。
    :param lookback: 用于傅里叶变换的回顾周期。
    """
    print(f"正在为 {lookback} 周期生成傅里叶特征 (前 {n_components} 个分量)...")
    
    # 确保数据有足够的长度
    if len(df) < lookback:
        print(f"警告: 数据长度 ({len(df)}) 小于傅里叶变换所需的回顾周期 ({lookback})，跳过傅里叶特征生成。")
        return df

    # 对收盘价进行傅里叶变换
    close_prices = df['close'].values
    
    # 创建一个空的DataFrame来存储傅里叶特征
    fourier_features = pd.DataFrame(index=df.index)

    for i in range(lookback, len(df) + 1):
        segment = close_prices[i-lookback:i]
        
        # 检查 segment 是否包含 NaN 值
        if np.isnan(segment).any():
            for j in range(n_components):
                fourier_features.loc[df.index[i-1], f'fourier_amplitude_{j+1}'] = np.nan
                fourier_features.loc[df.index[i-1], f'fourier_phase_{j+1}'] = np.nan
            continue

        fft_output = np.fft.fft(segment)
        frequencies = np.fft.fftfreq(lookback)

        # 排除直流分量 (频率为0) 并选择正频率
        positive_frequencies_idx = np.where(frequencies > 0)
        positive_frequencies = frequencies[positive_frequencies_idx]
        positive_fft_output = fft_output[positive_frequencies_idx]

        # 根据幅度排序，选择最重要的分量
        sorted_indices = np.argsort(np.abs(positive_fft_output))[::-1]
        
        for j in range(min(n_components, len(sorted_indices))):
            idx = sorted_indices[j]
            amplitude = np.abs(positive_fft_output[idx])
            phase = np.angle(positive_fft_output[idx])
            
            fourier_features.loc[df.index[i-1], f'fourier_amplitude_{j+1}'] = amplitude
            fourier_features.loc[df.index[i-1], f'fourier_phase_{j+1}'] = phase

    # 将傅里叶特征合并回原始DataFrame
    df = pd.concat([df, fourier_features], axis=1)
    df = df.ffill().bfill() # 填充NaN值

    print("傅里叶特征生成完毕。")
    return df

def generate_features(df: pd.DataFrame):
    """
    根据原始股票数据（包含OHLCV），生成多种技术指标以及宏观/情绪因子作为特征。
    现在返回一个包含特征DataFrame和特征列表的元组。
    """
    if df.empty:
        print("输入DataFrame为空，无法生成特征。")
        return pd.DataFrame(), []

    # 记录原始列名
    original_cols = set(df.columns)
    
    # 确保必要的列存在
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    if not all(col in df.columns for col in required_cols):
        print(f"错误: 输入DataFrame缺少必要的列。需要: {required_cols}，当前有: {df.columns.tolist()}")
        return df, []

    # --- 确保date列是datetime类型 ---
    if 'date' not in df.columns:
        if isinstance(df.index, pd.DatetimeIndex):
            df['date'] = df.index
        else:
            print("警告: 无法找到日期信息，将跳过因子数据合并。")
    
    if 'date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])
    
    print("正在生成技术指标特征...")

    if ta is not None:
        df.ta.sma(length=10, append=True)
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        print("正在生成布林带特征...")
        df.ta.bbands(length=20, std=2.0, append=True)
        df.ta.stoch(k=14, d=3, append=True)
        df.ta.atr(length=14, append=True)
        df.ta.mom(length=10, append=True)
        df.ta.mfi(length=14, append=True)
        df.ta.willr(length=14, append=True)
        df.ta.obv(append=True)

        print("正在生成偏离率特征...")
        df['deviation_rate_10_sma'] = ((df['close'] - df['SMA_10']) / df['SMA_10']) * 100
        df['deviation_rate_20_sma'] = ((df['close'] - df['SMA_20']) / df['SMA_20']) * 100
        df['deviation_rate_50_sma'] = ((df['close'] - df['SMA_50']) / df['SMA_50']) * 100
    else:
        df['SMA_10'] = df['close'].rolling(window=10).mean()
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        df['SMA_50'] = df['close'].rolling(window=50).mean()

        print("正在手动生成布林带特征...")
        # 计算20周期SMA作为中轨
        df['BBL_20_2.0'] = df['close'].rolling(window=20).mean()
        # 计算20周期标准差
        std_dev = df['close'].rolling(window=20).std()
        # 计算上轨和下轨
        df['BBU_20_2.0'] = df['BBL_20_2.0'] + (std_dev * 2)
        df['BBB_20_2.0'] = df['BBL_20_2.0'] - (std_dev * 2)
        # 计算带宽
        df['BBP_20_2.0'] = (df['BBU_20_2.0'] - df['BBB_20_2.0']) / df['BBL_20_2.0']
        # 计算 %B
        df['BBP_20_2.0'] = (df['close'] - df['BBB_20_2.0']) / (df['BBU_20_2.0'] - df['BBB_20_2.0'])

        print("正在手动生成偏离率特征...")
        df['deviation_rate_10_sma'] = ((df['close'] - df['SMA_10']) / df['SMA_10']) * 100
        df['deviation_rate_20_sma'] = ((df['close'] - df['SMA_20']) / df['SMA_20']) * 100
        df['deviation_rate_50_sma'] = ((df['close'] - df['SMA_50']) / df['SMA_50']) * 100

    # --- 添加斐波那契特征 ---
    df = generate_fibonacci_features(df, lookback=15)
    df = generate_fib_extension_features(df, lookback=15)
    df = generate_fourier_features(df, n_components=5, lookback=60)

    # --- 合并并处理宏观/情绪因子 ---
    if 'date' in df.columns:
        print("正在合并宏观/情绪因子...")
        df['merge_date'] = df['date'].dt.normalize()
        
        for name, factor_df in factor_data.items():
            temp_factor_df = factor_df.copy()
            
            source_col = 'close'
            if name == 'news_sentiment':
                source_col = 'news_sentiment'
            
            if source_col in temp_factor_df.columns:
                temp_factor_df.rename(columns={source_col: name}, inplace=True)
                
                # 修复：设置 temp_factor_df 的 index 为 date，然后只合并因子列
                # 这样可以避免 date 列变成嵌套 DataFrame
                temp_factor_df['date_normalized'] = temp_factor_df['date'].dt.normalize()
                temp_factor_df = temp_factor_df.set_index('date_normalized')
                
                # 只合并因子列，使用 merge_date 作为左键，index 作为右键
                df = df.join(temp_factor_df[[name]], on='merge_date', how='left')

                if name in df.columns:
                    df[name] = pd.to_numeric(df[name], errors='coerce')
                    df[name] = df[name].ffill().bfill()

        df = df.drop(columns=['merge_date'])
    
    # 从合并后的因子数据创建新特征
    if 'vix' in df.columns:
        df['vix_sma_ratio'] = (df['vix'] / df['vix'].rolling(window=20).mean()).ffill().bfill()
    
    if 'gspc' in df.columns:
        df['gspc_return'] = df['gspc'].pct_change().ffill().bfill()

    if 'dxy' in df.columns:
        df['dxy_return'] = df['dxy'].pct_change().ffill().bfill()

    # --- 添加市场状态/政权转换因子 ---
    print("正在生成市场状态/政权转换因子...")
    if 'gspc' in df.columns:
        gspc_sma_50 = df['gspc'].rolling(window=50).mean()
        gspc_sma_200 = df['gspc'].rolling(window=200).mean()
        df['is_bull_market'] = (gspc_sma_50 > gspc_sma_200).astype(int)
    
    if 'vix' in df.columns:
        df['volatility_regime'] = pd.cut(df['vix'], 
                                         bins=[0, 20, 30, np.inf], 
                                         labels=[0, 1, 2], 
                                         right=False).astype(float).fillna(-1).astype(int)

    df['close_to_open'] = df['close'] - df['open']
    df['high_to_low'] = df['high'] - df['low']
    df['volume_change'] = df['volume'].pct_change().ffill().bfill()

    # --- 自动识别生成的特征列 ---
    exclude_cols = ['open', 'high', 'low', 'close', 'volume', 'date', 'code', 'turnover', 'amplitude', 'change_pct', 'change_amt', 'turnover_rate']
    generated_features = [col for col in df.columns if col not in original_cols and col not in exclude_cols]
    
    print(f"特征生成完成。DataFrame现在包含 {len(df.columns)} 列。")
    print(f"自动识别的特征: {generated_features}")
    
    return df, generated_features

if __name__ == '__main__':
    from data_handler import get_stock_data
    # 确保 __main__ 部分不会因为返回元组而出错
    raw_stock_data = get_stock_data(ticker='600519', start_date='20220101', end_date='20231231')
    if not raw_stock_data.empty:
        features_df, features_list = generate_features(raw_stock_data.copy())
        print("\n--- 带有特征的数据预览 (后5行) ---")
        print(features_df.tail())
        print(f"\n最终DataFrame的列名: {features_df.columns.tolist()}")
        print(f"\n识别出的特征列表: {features_list}")
    else:
        print("未能获取到原始股票数据，无法演示特征生成。")