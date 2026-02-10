import baostock as bs
import pandas as pd
import numpy as np
import joblib
import os
from tqdm import tqdm
import warnings
import concurrent.futures

# --- 全局设置 ---
# 模型路径
MODEL_FILE_PATH = 'stock_prediction_model.joblib'
# 计算特征所需的最短历史天数
REQUIRED_HISTORY_DAYS = 50

# 忽略一些pandas的警告
warnings.filterwarnings('ignore', category=FutureWarning)

from feature_generator import generate_features

# --- 特征计算模块 (与训练时完全一致) ---

def calculate_features(df: pd.DataFrame) -> pd.DataFrame:
    """为历史数据计算技术指标作为特征"""
    if df.empty or 'close' not in df.columns or len(df) < REQUIRED_HISTORY_DAYS:
        return pd.DataFrame()
        
    # baostock返回的列名是字符串，需要转换为数值类型
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.dropna(subset=numeric_cols, inplace=True)

    return generate_features(df)

# --- 数据获取与处理模块 (使用 Baostock) ---

def get_all_stock_codes_from_baostock(max_retry_days=7):
    """从 baostock 获取所有A股代码和名称，会尝试最近的交易日"""
    print("正在从 baostock 获取所有A股代码列表...")
    today = pd.to_datetime('today')
    for i in range(max_retry_days):
        date_to_try = (today - pd.Timedelta(days=i)).strftime('%Y-%m-%d')
        print(f"尝试获取 {date_to_try} 的股票列表...")
        stock_rs = bs.query_all_stock(day=date_to_try)
        stock_df = stock_rs.get_data()
        if not stock_df.empty:
            print(f"成功获取到 {date_to_try} 的股票列表。")
            break
    else:
        print(f"错误：在过去 {max_retry_days} 天内都无法从 baostock 获取股票列表。")
        return pd.DataFrame()

    # 筛选
    a_stock_df = stock_df[
        (stock_df['code_name'].str.contains('ST|退') == False) &
        (stock_df['code'].str.match('^(sh|sz)\.[^688|^8|^4]'))
    ]
    a_stock_df.rename(columns={'code': '代码', 'code_name': '名称'}, inplace=True)
    return a_stock_df[['代码', '名称']]

def get_recent_history_from_baostock(stock_code: str, days: int = REQUIRED_HISTORY_DAYS) -> pd.DataFrame:
    """使用 baostock 获取单只股票最近N天的日线数据"""
    try:
        end_date = pd.to_datetime('today').strftime('%Y-%m-%d')
        # 为了确保有足够的数据，我们多获取一些
        start_date = (pd.to_datetime('today') - pd.Timedelta(days=days*2)).strftime('%Y-%m-%d')

        rs = bs.query_history_k_data_plus(
            stock_code,
            "date,code,open,high,low,close,volume",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="2" # 前复权
        )
        if rs.error_code != '0':
            return pd.DataFrame()
        
        data_df = rs.get_data()
        if data_df.empty or len(data_df) < days:
            return pd.DataFrame()
            
        data_df.rename(columns={'close': 'close', 'open': 'open', 'high': 'high', 'low': 'low', 'volume': 'volume'}, inplace=True)
        data_df['date'] = pd.to_datetime(data_df['date'])
        data_df.set_index('date', inplace=True)
        return data_df.tail(days)
    except Exception:
        return pd.DataFrame()

def process_stock_isolated(code):
    """在独立的进程中获取单只股票的特征数据"""
    lg = bs.login()
    if lg.error_code != '0':
        # 如果登录失败，直接返回，不要尝试登出
        return None
    
    try:
        hist_df = get_recent_history_from_baostock(code)
        if hist_df.empty:
            return None
            
        features_df = calculate_features(hist_df)
        if features_df.empty:
            return None

        last_features = features_df.iloc[-1:].copy()
        last_features['代码'] = code.split('.')[1]
        return last_features
    except Exception:
        # 捕获所有可能的异常，确保登出逻辑能执行
        return None
    finally:
        # 确保只要登录成功，就一定会执行登出
        try:
            bs.logout()
        except Exception:
            pass

def get_latest_features_for_all_stocks():
    """并行获取所有A股的最新特征数据 (使用 Baostock)"""
    codes_and_names = get_all_stock_codes_from_baostock()
    if codes_and_names.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    stock_codes = codes_and_names['代码'].tolist()
    latest_features = []
    
    print(f"开始并行获取 {len(stock_codes)} 只股票的最新特征数据...")
    
    # 折中方案：使用2个并行进程，在速度和稳定性之间取得平衡
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
        future_to_code = {executor.submit(process_stock_isolated, code): code for code in stock_codes}
        
        for future in tqdm(concurrent.futures.as_completed(future_to_code), total=len(stock_codes), desc="获取最新特征"):
            code = future_to_code[future]
            try:
                # 为每个进程设置一个更长的超时，例如60秒
                result = future.result(timeout=60)
                if result is not None:
                    latest_features.append(result)
            except concurrent.futures.TimeoutError:
                print(f"获取 {code} 数据进程超时，已被跳过。")
            except Exception as exc:
                print(f"处理 {code} 数据时发生错误: {exc}")

    print("\n所有并行任务已处理完毕。")

    if not latest_features:
        return pd.DataFrame(), pd.DataFrame()
    
    latest_features = [f for f in latest_features if f is not None]
    if not latest_features:
        return pd.DataFrame(), pd.DataFrame()
        
    codes_and_names['代码'] = codes_and_names['代码'].apply(lambda x: x.split('.')[1])
    all_features_df = pd.concat(latest_features, ignore_index=True)
    return all_features_df, codes_and_names


# --- 主预测流程 ---

def predict_stocks(top_n: int = 50):
    """
    加载模型，获取最新数据，进行预测，并返回Top N结果。
    """
    if not os.path.exists(MODEL_FILE_PATH):
        print(f"错误: 模型文件 '{MODEL_FILE_PATH}' 不存在。请先运行 model_trainer.py。")
        return
    
    print(f"正在加载模型: {MODEL_FILE_PATH}")
    model = joblib.load(MODEL_FILE_PATH)

    # 登录 baostock
    lg = bs.login()
    if lg.error_code != '0':
        print(f"baostock 登录失败: {lg.error_msg}")
        return
    print("baostock 登录成功！")

    features_df, codes_and_names = get_latest_features_for_all_stocks()
    
    # 登出 baostock
    bs.logout()
    print("已登出 baostock。")

    if features_df.empty:
        print("未能获取到任何股票的最新特征数据，预测中止。")
        return

    features_for_prediction = features_df.dropna()
    if features_for_prediction.empty:
        print("数据清洗后为空，无法进行预测。")
        return
        
    feature_names = [
        'SMA_10', 'SMA_20', 'SMA_50',
        'RSI_14',
        'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9',
        'BBL_20_2.0_2.0', 'BBM_20_2.0_2.0', 'BBU_20_2.0_2.0', 'BBB_20_2.0_2.0', 'BBP_20_2.0_2.0',
        'STOCHk_14_3_3', 'STOCHd_14_3_3',
        'ATRr_14',
        'MOM_10',
        'MFI_14',
        'WILLR_14',
        'OBV'
    ]
    X_pred = features_for_prediction[feature_names]

    print("模型正在进行预测...")
    predictions = model.predict(X_pred)
    features_for_prediction['predicted_return'] = predictions

    result_df = pd.merge(features_for_prediction, codes_and_names, on='代码')
    final_df = result_df.sort_values(by='predicted_return', ascending=False)

    print(f"\n--- 模型预测完成，返回预期收益最高的 {top_n} 只股票 ---")
    display_columns = ['代码', '名称', 'predicted_return']
    return final_df.head(top_n)[display_columns]


if __name__ == '__main__':
    top_stocks = predict_stocks(top_n=50)

    if top_stocks is not None and not top_stocks.empty:
        top_stocks['predicted_return(%)'] = (top_stocks['predicted_return'] * 100).round(2)
        # 将结果保存到 JSON 文件，供 API 读取
        output_path = os.path.join(os.path.dirname(__file__), 'predicted_stocks.json')
        top_stocks[['代码', '名称', 'predicted_return(%)']].to_json(output_path, orient='records', force_ascii=False, indent=4)
        print(f"预测结果已保存到 {output_path}")
        # 打印到控制台，方便调试
        print(top_stocks[['代码', '名称', 'predicted_return(%)']].to_string(index=False))
    else:
        print("未能生成选股结果。")