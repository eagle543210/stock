# stock_diagnoser.py

import joblib
import pandas as pd
from sklearn.preprocessing import StandardScaler

from data_handler import get_stock_data
from datetime import datetime, timedelta
from feature_generator import generate_features

def diagnose_stock(stock_code, log_callback=None):
    """
    诊断单只股票，并给出投资建议。
    """
    # 1. 加载模型
    try:
        model_path = f'{stock_code}_model.joblib'
        model = joblib.load(model_path)
        log_message = f"成功加载模型: {model_path}"
        if log_callback: log_callback(log_message)
        else: print(log_message)
    except FileNotFoundError:
        return f"错误：找不到股票代码 {stock_code} 对应的模型文件 {model_path}。请先训练该股票的模型。"

    # 2. 获取最新数据
    #    为了预测下一天，我们需要最近一段时间的数据来生成特征
    try:
        # 获取最近足够天数的数据来生成特征 (例如，200天)
        # 确保 end_date 不会是未来的日期，并获取到最近一个交易日
        today = datetime.now()
        # 如果今天是周末，则将日期调整到最近的周五
        if today.weekday() == 5: # Saturday
            today = today - timedelta(days=1)
        elif today.weekday() == 6: # Sunday
            today = today - timedelta(days=2)
        
        end_date = today.strftime('%Y%m%d')
        start_date = (today - timedelta(days=200)).strftime('%Y%m%d')
        data = get_stock_data(ticker=stock_code, start_date=start_date, end_date=end_date)
        if data.empty:
            return f"错误：无法获取股票 {stock_code} 的最新数据。"
        log_message = f"成功获取 {stock_code} 的最新数据，共 {len(data)} 条。"
        if log_callback: log_callback(log_message)
        else: print(log_message)
    except Exception as e:
        return f"获取股票 {stock_code} 数据时出错: {e}"

    # 3. 生成特征
    data['external_event'] = 0 # 添加 external_event 列
    features_df = generate_features(data.copy())
    
    # 4. 准备用于预测的最新数据
    #    模型通常需要归一化的数据，并且使用最后一天的数据来预测未来
    scaler = StandardScaler()
    
    # 假设模型使用以下特征 (与 feature_generator.py 保持一致)
    feature_columns = [
        '股票代码',
        'external_event',
        'SMA_10', 'SMA_20', 'SMA_50',
        'RSI_14',
        'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9',
        'BBL_20_2.0_2.0', 'BBM_20_2.0_2.0', 'BBU_20_2.0_2.0', 'BBB_20_2.0_2.0', 'BBP_20_2.0_2.0',
        'STOCHk_14_3_3', 'STOCHd_14_3_3',
        'STOCHh_14_3_3',
        'ATRr_14',
        'MOM_10',
        'MFI_14',
        'WILLR_14',
        'OBV',
        'close_to_open',
        'high_to_low',
        'volume_change'
    ]
    
    # 确保所有需要的特征列都存在
    log_message = f"诊断器中，特征生成后DataFrame的列: {features_df.columns.tolist()}"
    if log_callback: log_callback(log_message)
    else: print(log_message)
    for col in feature_columns:
        if col not in features_df.columns:
            return f"错误：数据中缺少必要的特征列 '{col}'。"
            
    features_df.dropna(inplace=True)
    if features_df.empty:
        return f"错误：生成特征后并移除缺失值后，没有足够的数据用于预测。"

    # 归一化特征
    features_scaled = scaler.fit_transform(features_df[feature_columns])
    
    # 获取最后一组特征用于预测
    latest_features = features_scaled[-1].reshape(1, -1)
    
    # 5. 进行预测
    try:
        prediction = model.predict(latest_features)
        log_message = f"模型预测结果: {prediction[0]}"
        if log_callback: log_callback(log_message)
        else: print(log_message)
    except Exception as e:
        return f"使用模型进行预测时出错: {e}"

    # 6. 生成投资建议
    #    这里的逻辑依赖于模型的输出。我们假设：
    #    - 1 表示预测上涨 (买入)
    #    - 0 表示预测平稳 (持有)
    #    - -1 表示预测下跌 (卖出)
    #    这需要根据您模型训练时的目标变量(target)来确定。
    
    latest_close_price = data['close'].iloc[-1]
    
    if prediction[0] == 1:
        advice = "买入"
        reason = f"模型预测下一个交易日上涨。当前收盘价: {latest_close_price:.2f}"
    elif prediction[0] == -1:
        advice = "卖出"
        reason = f"模型预测下一个交易日下跌。当前收盘价: {latest_close_price:.2f}"
    else:
        advice = "持有"
        reason = f"模型预测下一个交易日情可能平稳。当前收盘价: {latest_close_price:.2f}"

    return f"对股票 {stock_code} 的诊断建议：\n- 投资建议: {advice}\n- 分析: {reason}"

if __name__ == '__main__':
    # 用于直接测试该模块
    test_stock_code = '600519' # 使用一个已存在的模型文件进行测试
    advice_result = diagnose_stock(test_stock_code)
    print(advice_result)
