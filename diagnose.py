#!/usr/bin/env python3
"""
快速诊断脚本 - 检查 API 配置和环境
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def diagnose():
    """运行诊断"""
    print("\n" + "=" * 70)
    print("🔍 量化交易系统 - 快速诊断")
    print("=" * 70)
    
    # 检查工作目录
    print("\n📁 工作目录检查:")
    cwd = Path.cwd()
    print(f"  当前目录: {cwd}")
    
    env_file = cwd / '.env'
    print(f"  .env 文件: {'✅ 存在' if env_file.exists() else '❌ 不存在'}")
    
    if env_file.exists():
        print(f"  .env 大小: {env_file.stat().st_size} 字节")
    
    # 加载 .env 文件
    print("\n🔑 环境变量检查:")
    load_dotenv()
    
    api_key = os.getenv('BINANCE_API_KEY', '')
    secret_key = os.getenv('BINANCE_SECRET_KEY', '')
    
    print(f"  BINANCE_API_KEY: {'✅ 已配置' if api_key else '❌ 未配置'}")
    if api_key:
        # 显示部分 API Key（用星号隐藏）
        masked = api_key[:8] + '*' * (len(api_key) - 16) + api_key[-8:]
        print(f"    内容: {masked}")
        print(f"    长度: {len(api_key)} 字符")
    
    print(f"  BINANCE_SECRET_KEY: {'✅ 已配置' if secret_key else '❌ 未配置'}")
    if secret_key:
        masked = secret_key[:8] + '*' * (len(secret_key) - 16) + secret_key[-8:]
        print(f"    内容: {masked}")
        print(f"    长度: {len(secret_key)} 字符")
    
    # 检查其他关键环境变量
    print("\n📋 其他环境变量:")
    other_vars = [
        'GEMINI_API_KEY',
        'TENCENTCLOUD_SECRET_ID',
        'TENCENTCLOUD_SECRET_KEY',
        'HF_TOKEN'
    ]
    
    for var in other_vars:
        value = os.getenv(var, '')
        status = '✅ 已配置' if value else '❌ 未配置'
        print(f"  {var}: {status}")
    
    # 检查关键文件
    print("\n📂 关键文件检查:")
    files_to_check = [
        'api.py',
        'data_handler.py',
        'feature_generator.py',
        'model_trainer.py',
        'backtester.py',
        'trader.py',
        'requirements.txt',
    ]
    
    for filename in files_to_check:
        filepath = cwd / filename
        status = '✅' if filepath.exists() else '❌'
        print(f"  {status} {filename}")
    
    # 检查虚拟环境
    print("\n🐍 Python 环境:")
    print(f"  Python 可执行文件: {sys.executable}")
    print(f"  Python 版本: {sys.version.split()[0]}")
    
    # 尝试导入关键模块
    print("\n📦 关键模块检查:")
    modules = ['pandas', 'ccxt', 'joblib', 'fastapi', 'sklearn']
    
    for module in modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ❌ {module} (未安装)")
    
    # 诊断建议
    print("\n💡 诊断建议:")
    
    if not api_key or not secret_key:
        print("  ⚠️  币安 API 密钥未配置")
        print("     → 请按照 BINANCE_API_SETUP.md 创建新的 API 密钥")
        print("     → 然后更新 .env 文件中的 BINANCE_API_KEY 和 BINANCE_SECRET_KEY")
    else:
        print("  ✅ 币安 API 密钥已配置")
        print("     → 运行 python test_binance_api.py 测试连接")
    
    print("  ✅ 系统检查完成")
    
    print("\n" + "=" * 70)
    print("📝 下一步:")
    print("  1. 如果 API 密钥未配置，请先创建新的币安 API 密钥")
    print("  2. 运行: python test_binance_api.py 测试连接")
    print("  3. 如果测试通过，启动 API 服务: uvicorn api:app --reload")
    print("=" * 70 + "\n")

if __name__ == '__main__':
    diagnose()
