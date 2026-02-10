# inspect_akshare.py
import akshare as ak

print(f"--- 正在检查 akshare 库 (版本: {ak.__version__}) ---")
print("--- 所有可用函数列表如下 ---")

# 获取 akshare 模块的所有属性
all_attributes = dir(ak)

# 过滤出所有函数，并排除内部属性 (以'_'开头的)
all_functions = [attr for attr in all_attributes if callable(getattr(ak, attr)) and not attr.startswith('_')]

# 打印所有函数名
for func_name in sorted(all_functions):
    print(func_name)

print("\n--- 查找包含 'futures' 或 'global' 的函数 ---")
# 查找可能相关的函数
relevant_functions = [f for f in all_functions if 'futures' in f or 'global' in f]
for func_name in sorted(relevant_functions):
    print(func_name)

print("\n--- 检查完成 ---")
