import pandas as pd
import sys
import traceback

try:
    # 测试 pd.to_datetime 的问题
    print("=== 测试 pd.to_datetime 重复键问题 ===\n")
    
    # 创建一个模拟的 date 列（可能的问题场景）
    dates = pd.date_range('2023-01-01', periods=5, freq='D')
    
    # 场景 1: 正常的 datetime 列
    print("场景 1: 正常的 datetime Series")
    df1 = pd.DataFrame({'date': dates, 'value': range(5)})
    print(f"df1['date'] dtype: {df1['date'].dtype}")
    try:
        result = pd.to_datetime(df1['date'])
        print("✅ 转换成功\n")
    except Exception as e:
        print(f"❌ 失败: {e}\n")
    
    # 场景 2: 已经是 datetime 但尝试再次转换
    print("场景 2: 已经是 datetime64 的列再次转换")
    df2 = pd.DataFrame({'date': pd.to_datetime(dates), 'value': range(5)})
    print(f"df2['date'] dtype: {df2['date'].dtype}")
    try:
        result = pd.to_datetime(df2['date'])
        print("✅ 转换成功\n")
    except Exception as e:
        print(f"❌ 失败: {e}\n")
    
    # 场景 3: 包含字典或复杂结构的列
    print("场景 3: 包含复杂结构的列")
    complex_dates = [{'year': 2023, 'month': 1, 'day': i} for i in range(1, 6)]
    df3 = pd.DataFrame({'date': complex_dates, 'value': range(5)})
    print(f"df3['date'] dtype: {df3['date'].dtype}")
    print(f"df3['date'].iloc[0]: {df3['date'].iloc[0]}")
    try:
        result = pd.to_datetime(df3['date'])
        print("✅ 转换成功\n")
    except Exception as e:
        print(f"❌ 失败: {e}")
        print(f"错误类型: {type(e).__name__}\n")
    
    # 场景 4: Timestamp 对象
    print("场景 4: Timestamp 对象列")
    df4 = pd.DataFrame({'date': [pd.Timestamp(d) for d in dates], 'value': range(5)})
    print(f"df4['date'] dtype: {df4['date'].dtype}")
    print(f"df4['date'].iloc[0]: {df4['date'].iloc[0]}")
    print(f"df4['date'].iloc[0] type: {type(df4['date'].iloc[0])}")
    try:
        result = pd.to_datetime(df4['date'])
        print("✅ 转换成功\n")
    except Exception as e:
        print(f"❌ 失败: {e}\n")

except Exception as e:
    print(f"\n脚本执行出错:")
    traceback.print_exc()
