import pandas as pd
import lightgbm as lgb
import joblib
import os

# --- 配置 ---
PREDICTION_LOG_FILE = 'prediction_log.csv'
ERROR_MODEL_FILE = 'error_model.joblib'

def train_error_model():
    """
    读取 prediction_log.csv，训练一个用于预测基础模型误差的模型。
    """
    if not os.path.exists(PREDICTION_LOG_FILE):
        print(f"错误: 预测日志文件 '{PREDICTION_LOG_FILE}' 不存在。无法训练误差模型。")
        return

    try:
        df = pd.read_csv(PREDICTION_LOG_FILE)
    except pd.errors.EmptyDataError:
        print("预测日志文件为空，无法训练误差模型。")
        return

    # 1. 数据清洗：只保留有真实结果和误差的行
    df.dropna(subset=['base_prediction', 'error'], inplace=True)
    # 确保 error 列是数值类型
    df['error'] = pd.to_numeric(df['error'], errors='coerce')
    df.dropna(subset=['error'], inplace=True)

    if len(df) < 50:  # 设置一个最小样本量阈值
        print(f"可用于训练的样本量不足 ({len(df)}条)，至少需要50条。请运行更长时间以积累数据。")
        return

    print(f"使用 {len(df)} 条已���成的预测记录来训练误差模型...")

    # 2. 特征工程 (X) 和 目标变量 (y)
    # 基础模型的预测值本身。
    # 未来可以扩展：加入更多描述市场短期状态的特征，如波动率、成交量变化等。
    features = ['base_prediction']
    X = df[features]
    y = df['error']

    # 3. 模型训练
    # 使用一个非常轻量级的 LightGBM 模型
    error_model = lgb.LGBMRegressor(
        objective='regression',
        n_estimators=50,       # 树的数量较少
        learning_rate=0.05,
        num_leaves=10,         # 每棵树的叶子数较少
        max_depth=5,           # 限制树的深度
        random_state=42,
        n_jobs=-1
    )

    print("开始训练误差修正模型...")
    error_model.fit(X, y)
    print("误差修正模型训练完成。")

    # 4. 保存模型
    joblib.dump(error_model, ERROR_MODEL_FILE)
    print(f"误差修正模型已成功保存至 '{ERROR_MODEL_FILE}'。")

if __name__ == '__main__':
    print("--- 开始训练误差修正模型 ---")
    train_error_model()
    print("--- 训练完成 ---")