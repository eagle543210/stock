import os
import pandas as pd
import argparse

# 导入我们创建的模块
from data_handler import get_stock_data
from feature_generator import generate_features
from model_trainer import create_target_labels, train_model
from backtester import Backtester
from stock_diagnoser import diagnose_stock

def main():
    """
    主工作流程函数，用于执行整个量化交易策略的训练、回测或股票诊断。
    """
    parser = argparse.ArgumentParser(description="量化交易策略工具")
    parser.add_argument('--ticker', type=str, default='600519',
                        help='要操作的股票代码 (例如: 600519)')
    parser.add_argument('--diagnose', type=str,
                        help='对指定股票代码进行诊断 (例如: 600519)')
    parser.add_argument('--train_start', type=str, default='20180101',
                        help='训练数据开始日期 (YYYYMMDD)')
    parser.add_argument('--train_end', type=str, default='20221231',
                        help='训练数据结束日期 (YYYYMMDD)')
    parser.add_argument('--backtest_start', type=str, default='20230101',
                        help='回测数据开始日期 (YYYYMMDD)')
    parser.add_argument('--backtest_end', type=str, default='20231231',
                        help='回测数据结束日期 (YYYYMMDD)')
    parser.add_argument('--initial_capital', type=float, default=100000.0,
                        help='回测初始资金')

    args = parser.parse_args()

    if args.diagnose:
        print(f"\n" + "="*50)
        print(f"开始诊断股票 {args.diagnose}...")
        print("="*50)
        result = diagnose_stock(args.diagnose)
        print(result)
        print("="*50)
        return

    # --- 1. 配置参数 ---
    TICKER = args.ticker
    TRAIN_START_DATE = args.train_start
    TRAIN_END_DATE = args.train_end
    BACKTEST_START_DATE = args.backtest_start
    BACKTEST_END_DATE = args.backtest_end
    MODEL_PATH = f'M:\\stock\\{TICKER}_model.joblib'
    INITIAL_CAPITAL = args.initial_capital

    # --- 2. 训练模型 ---
    print("="*50)
    print(f"开始为股票 {TICKER} 训练模型...")
    print(f"训练数据范围: {TRAIN_START_DATE} - {TRAIN_END_DATE}")
    print("="*50)

    # 获取训练数据
    raw_data_train = get_stock_data(ticker=TICKER, start_date=TRAIN_START_DATE, end_date=TRAIN_END_DATE)
    if raw_data_train.empty:
        print("无法获取训练数据，程序终止。")
        return

    # 生成特征
    data_with_features_train = generate_features(raw_data_train.copy())
    if data_with_features_train.empty:
        print("生成训练特征失败，程序终止。")
        return

    # 创建目标标签
    data_with_target_train = create_target_labels(data_with_features_train.copy())
    if data_with_target_train.empty:
        print("创建目标标签失败，程序终止。")
        return

    # 定义用于训练的特征列
    # 注意：这里需要根据 model_trainer.py 中 calculate_features 的输出进行调整
    # 假设 model_trainer.py 中的特征是 MA5, MA20, RSI, MACD, Signal_Line
    features_to_use = ['MA5', 'MA20', 'RSI', 'MACD', 'Signal_Line']
    target_col = 'future_20d_return'

    # 确保所有特征列都存在于数据中
    if not all(f in data_with_target_train.columns for f in features_to_use):
        missing_features = [f for f in features_to_use if f not in data_with_target_train.columns]
        print(f"训练数据缺少以下特征: {missing_features}，程序终止。")
        return

    print(f"\n将使用 {len(features_to_use)} 个特征进行训练。")

    # 训练并保存模型
    train_model(data_with_target_train.copy(), features=features_to_use, target_col=target_col, model_path=MODEL_PATH)

    if not os.path.exists(MODEL_PATH):
        print(f"模型文件 {MODEL_PATH} 未能成功创建，程序终止。")
        return
    print(f"\n模型训练完成并保存于: {MODEL_PATH}")

    # --- 3. 执行回测 ---
    print("\n" + "="*50)
    print(f"开始在样本外数据上进行回测...")
    print(f"回测数据范围: {BACKTEST_START_DATE} - {BACKTEST_END_DATE}")
    print("="*50)

    # 获取回测数据
    raw_data_backtest = get_stock_data(ticker=TICKER, start_date=BACKTEST_START_DATE, end_date=BACKTEST_END_DATE)
    if raw_data_backtest.empty:
        print("无法获取回测数据，程序终止。")
        return

    # 为回测数据生成特征
    data_for_backtest = generate_features(raw_data_backtest.copy())
    if data_for_backtest.empty:
        print("生成回测特征失败，程序终止。")
        return

    # 确保回测数据中包含所有需要的特征
    if not all(f in data_for_backtest.columns for f in features_to_use):
        missing_features = [f for f in features_to_use if f not in data_for_backtest.columns]
        print(f"回测数据缺少以下在训练时使用的特征: {missing_features}，程序终止。")
        return

    # 实例化回测器
    try:
        backtester = Backtester(
            data=data_for_backtest,
            model_path=MODEL_PATH,
            features=features_to_use,
            initial_capital=INITIAL_CAPITAL
        )
    except Exception as e:
        print(f"初始化回测器失败: {e}，程序终止。")
        return

    # 运行回测
    backtester.run_backtest()

    # 获取并打印性能指标
    metrics = backtester.get_performance_metrics()
    print("\n--- 回测性能指标 ---")
    for key, value in metrics.items():
        print(f"{key}: {value}")
    print("="*50)

if __name__ == '__main__':
    main()