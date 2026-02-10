# -*- coding: utf-8 -*>
import pandas as pd
import numpy as np
# from sklearn.ensemble import RandomForestRegressor # 注释掉 RandomForestRegressor
import lightgbm as lgb # 确保 LightGBM 已导入
import joblib
import os
from tqdm import tqdm
from feature_generator import generate_features # 导入统一的特征生成函数
import argparse # 导入 argparse 用于接收命令行参数

# --- 全局设置 ---
# 数据缓存目录
DATA_CACHE_DIR = 'stock_data_cache'

# --- 1. 数据加载模块 (重构后) ---

def get_stock_file(ticker: str) -> str:
    """从缓存目录获取指定股票的数据文件路径"""
    print(f"正在从本地缓存目录查找 {ticker} 的数据文件...")
    if not os.path.exists(DATA_CACHE_DIR):
        print(f"错误: 数据缓存目录 '{DATA_CACHE_DIR}' 不存在。请先运行 data_downloader.py。")
        return ""
    
    # 根据股票代码格式构建预期的文件名
    formatted_ticker = ticker.replace('.', '_').replace('/', '_').lower()
    
    if '/' in ticker or ('_' in ticker and len(ticker) > 5): # 新增：判断是否为加密货币
        expected_filename = f"crypto_{formatted_ticker}_daily.csv"
    elif '.' in ticker:
        # A股格式, e.g., sh_600519_daily.csv
        expected_filename = f"{formatted_ticker}_daily.csv"
    else:
        # 非A股格式 (按美股处理), e.g., us_wti_daily.csv
        expected_filename = f"us_{formatted_ticker}_daily.csv"
    
    for f in os.listdir(DATA_CACHE_DIR):
        if f.lower() == expected_filename:
            file_path = os.path.join(DATA_CACHE_DIR, f)
            print(f"找到文件: {file_path}")
            return file_path

    print(f"错误: 未找到 {ticker} 的数据文件 (期望文件名: {expected_filename})。")
    return ""

def load_stock_data(file_path: str) -> pd.DataFrame:
    """从本地CSV文件加载股票数据"""
    try:
        # 跳过第二行，因为它包含非数据信息
        df = pd.read_csv(file_path, encoding='utf-8-sig', engine='python', skiprows=[1])
        # 确保关键列为数值类型，并将非数值转换为 NaN
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=numeric_cols, inplace=True) # 删除包含 NaN 的行
        return df
    except Exception as e:
        print(f"加载文件 {file_path} 失败: {e}")
        return pd.DataFrame()

# --- 3. 标签定义模块 (与之前相同) ---

def create_target_labels(df: pd.DataFrame, future_days: int = 5) -> pd.DataFrame:
    """定义标签：未来N日的收益率"""
    if df.empty or 'close' not in df.columns:
        return pd.DataFrame()

    df[f'future_{future_days}d_return'] = df['close'].shift(-future_days) / df['close'] - 1
    return df

# --- 4. 主训练流程 (修改为针对单个股票) ---

def train_single_stock_model(ticker: str):
    """为单个股票训练并保存模型"""
    
    # 步骤1：获取指定股票的数据文件
    stock_file = get_stock_file(ticker)
    if not stock_file:
        print(f"未能找到 {ticker} 的数据文件，训练中止。")
        return

    # 步骤2：从本地加载并处理数据
    daily_df = load_stock_data(stock_file)
    if daily_df.empty:
        print(f"加载 {ticker} 数据失败，训练中止。")
        return
    
    # 检查数据量是否足够进行特征生成和训练
    MIN_ROWS_REQUIRED = 60 # 至少需要60行数据来计算SMA_50和未来收益率
    if len(daily_df) < MIN_ROWS_REQUIRED:
        print(f"错误: {ticker} 的数据量不足 ({len(daily_df)} 行)。至少需要 {MIN_ROWS_REQUIRED} 行才能生成有效特征并训练模型。训练中止。")
        return
    
    print(f"为 {ticker} 生成特征...")
    features_df, features = generate_features(daily_df) # 接收返回的特征列表
    labeled_df = create_target_labels(features_df)

    # 步骤3：数据清洗
    if labeled_df.empty:
        print("数据处理后为空，无法为 {ticker} 训练模型。")
        return

    # 步骤4：准备训练数据
    target = 'future_5d_return'
    
    # --- 新的数据清洗逻辑 ---
    # 只选择包含所有特征和目标值的行
    selected_cols_df = labeled_df[features + [target]]
    print(f"在移除NaN值之前，数据框的形状: {selected_cols_df.shape}")
    train_df = selected_cols_df.dropna()
    print(f"在移除NaN值之后，数据框的形状: {train_df.shape}")

    if train_df.empty:
        print("在移除包含NaN值的行后，没有可用于训练的数据。")
        print("这可能是因为原始数据量太小，或者特征生成过程中产生了太多NaN值。") # Added more context
        return

    X = train_df[features]
    y = train_df[target]

    print(f"数据准备完毕，总样本数: {len(X)}")
    
    # 打印 news_sentiment 列的统计信息以供诊断
    if 'news_sentiment' in X.columns:
        print("\n--- news_sentiment 特征的统计信息 ---")
        print(X['news_sentiment'].describe())
        print("-------------------------------------\n")

    # 步骤5：模型训练 (使用 LightGBM)
    print("开始训练 LightGBM 模型...")
    # LightGBM 回归模型，设置一些常用参数
    model = lgb.LGBMRegressor(objective='regression', # 回归任务
                              n_estimators=200,      # 弱学习器数量，可以比随机森林多
                              learning_rate=0.05,    # 学习率
                              num_leaves=31,         # 每棵树的最大叶子数
                              max_depth=-1,          # 树的最大深度，-1表示无限制，但通常会设置一个值防止过拟合
                              random_state=42,       # 随机种子
                              n_jobs=-1)             # 使用所有可用核心
    model.fit(X, y)

    # 步骤6：打印特征重要性
    feature_importance = pd.DataFrame({'feature': features, 'importance': model.feature_importances_}).sort_values('importance', ascending=False)
    print("\n特征重要性:")
    print(feature_importance)

    # 步骤7：保存模型和特征列表
    safe_ticker = ticker.replace('/', '_').upper()
    model_path = f'./{safe_ticker}_model.joblib'
    print(f"训练完成，正在将模型和特征列表保存至 {model_path} ...")
    
    # 将模型和特征列表保存在一个字典中
    model_payload = {
        'model': model,
        'features': features
    }
    joblib.dump(model_payload, model_path)
    print("模型和特征列表保存成功！")


if __name__ == '__main__':
    # --- 使用 argparse 解析命令行参数 ---
    parser = argparse.ArgumentParser(description='为指定的股票代码训练模型。')
    parser.add_argument('ticker', type=str, help='要训练的股票代码 (例如: USDCHF, AMD, 600519)。')
    args = parser.parse_args()

    print(f"--- 开始为 {args.ticker} 执行模型训练脚本 ---")
    train_single_stock_model(args.ticker)
    print(f"--- {args.ticker} 的模型训练脚本执行完毕 ---")