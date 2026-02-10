import pandas as pd
from data_handler import get_any_stock_data
from feature_generator import generate_features

# 测试数据获取和特征生成
ticker = '600519'
start_date = '20230101'
end_date = '20231231'

print(f"获取数据: {ticker}, {start_date} - {end_date}")
raw_data = get_any_stock_data(ticker=ticker, start_date=start_date, end_date=end_date)

if raw_data.empty:
    print("❌ 无法获取数据")
    exit(1)

print(f"\n=== 原始数据结构 ===")
print(f"Shape: {raw_data.shape}")
print(f"Index type: {type(raw_data.index)}")
print(f"Index: {raw_data.index[:3]}")
print(f"Columns: {raw_data.columns.tolist()}")
if 'date' in raw_data.columns:
    print(f"date column type: {raw_data['date'].dtype}")
    print(f"date column sample: {raw_data['date'].head(3).tolist()}")

print(f"\n=== 生成特征 ===")
raw_data['external_event'] = 0
data_with_features, features_list = generate_features(raw_data.copy())

print(f"\n=== 特征生成后的数据结构 ===")
print(f"Shape: {data_with_features.shape}")
print(f"Index type: {type(data_with_features.index)}")
print(f"Index: {data_with_features.index[:3]}")
print(f"Columns (first 10): {data_with_features.columns.tolist()[:10]}")
if 'date' in data_with_features.columns:
    print(f"✅ date column exists")
    print(f"date column type: {data_with_features['date'].dtype}")
    print(f"date column sample:")
    print(data_with_features['date'].head(3))
    
    # 检查是否有重复的日期结构
    print(f"\n=== 检查 date 列的内部结构 ===")
    sample_date = data_with_features['date'].iloc[0]
    print(f"Sample date value: {sample_date}")
    print(f"Sample date type: {type(sample_date)}")
    
    # 尝试转换
    print(f"\n=== 尝试 pd.to_datetime ===")
    try:
        converted = pd.to_datetime(data_with_features['date'])
        print(f"✅ 转换成功")
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        print(f"错误类型: {type(e).__name__}")
else:
    print(f"❌ date column does NOT exist")

print(f"\n=== 检查是否是 DatetimeIndex ===")
print(f"Is DatetimeIndex: {isinstance(data_with_features.index, pd.DatetimeIndex)}")
