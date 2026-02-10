#!/usr/bin/env python3
"""
币安 API 密钥配置向导
交互式配置你的币安 API 密钥
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def setup_binance_api():
    """交互式配置币安 API"""
    print("\n" + "=" * 70)
    print("🔑 币安 API 密钥配置向导")
    print("=" * 70)
    
    print("\n⚠️  重要提示:")
    print("  • 请确保你已经在币安官方网站创建了新的 API Key")
    print("  • 访问: https://www.binance.com/en/user/settings/api-management")
    print("  • 确保启用了现货交易权限")
    print("  • 这些信息将被保存到 .env 文件中（已在 .gitignore 中）")
    
    # 获取 API Key
    print("\n1️⃣ 输入你的 API Key:")
    print("   (粘贴币安生成的 API Key)")
    api_key = input("   API Key: ").strip()
    
    if not api_key:
        print("   ❌ API Key 不能为空")
        return False
    
    if len(api_key) < 20:
        print(f"   ⚠️  警告: API Key 长度似乎太短 ({len(api_key)} 字符)")
        confirm = input("   是否继续? (y/n): ").strip().lower()
        if confirm != 'y':
            return False
    
    # 获取 Secret Key
    print("\n2️⃣ 输入你的 Secret Key:")
    print("   (粘贴币安生成的 Secret Key，仅显示一次!)")
    secret_key = input("   Secret Key: ").strip()
    
    if not secret_key:
        print("   ❌ Secret Key 不能为空")
        return False
    
    if len(secret_key) < 20:
        print(f"   ⚠️  警告: Secret Key 长度似乎太短 ({len(secret_key)} 字符)")
        confirm = input("   是否继续? (y/n): ").strip().lower()
        if confirm != 'y':
            return False
    
    # 确认
    print("\n3️⃣ 确认信息:")
    print(f"   API Key: {api_key[:8]}...{api_key[-8:]}")
    print(f"   Secret Key: {secret_key[:8]}...{secret_key[-8:]}")
    
    confirm = input("\n   是否确认保存? (y/n): ").strip().lower()
    if confirm != 'y':
        print("   ❌ 已取消")
        return False
    
    # 更新 .env 文件
    print("\n💾 正在保存到 .env 文件...")
    
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换 API Key 和 Secret Key
        import re
        content = re.sub(
            r'BINANCE_API_KEY\s*=\s*"[^"]*"',
            f'BINANCE_API_KEY="{api_key}"',
            content
        )
        content = re.sub(
            r'BINANCE_SECRET_KEY\s*=\s*"[^"]*"',
            f'BINANCE_SECRET_KEY="{secret_key}"',
            content
        )
    else:
        # 创建新的 .env 文件
        content = f'BINANCE_API_KEY="{api_key}"\nBINANCE_SECRET_KEY="{secret_key}"\n'
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("   ✅ 保存成功！")
    
    # 验证
    print("\n🧪 验证配置...")
    load_dotenv()
    
    new_api_key = os.getenv('BINANCE_API_KEY')
    new_secret_key = os.getenv('BINANCE_SECRET_KEY')
    
    if new_api_key == api_key and new_secret_key == secret_key:
        print("   ✅ 配置验证成功！")
        return True
    else:
        print("   ❌ 配置验证失败")
        return False

def main():
    """主函数"""
    try:
        success = setup_binance_api()
        
        if success:
            print("\n" + "=" * 70)
            print("✅ 配置完成！")
            print("\n📝 下一步:")
            print("  1. 运行: python test_binance_api.py")
            print("     (这将测试你的 API 连接)")
            print("  2. 如果测试通过，运行: uvicorn api:app --reload")
            print("     (启动 API 服务)")
            print("=" * 70 + "\n")
        else:
            print("\n❌ 配置已取消")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
