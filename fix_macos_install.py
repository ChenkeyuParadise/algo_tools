#!/usr/bin/env python3
"""
macOS环境安装问题修复脚本
"""

import sys
import subprocess
import os

def run_command(cmd):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_python_version():
    """检查Python版本"""
    print("🔍 检查Python版本...")
    version = sys.version_info
    print(f"  Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3:
        print("  ❌ 需要Python 3.x版本")
        return False
    elif version.minor < 7:
        print("  ⚠️  建议使用Python 3.7+")
    else:
        print("  ✅ Python版本兼容")
    
    return True

def check_pip():
    """检查pip"""
    print("🔍 检查pip...")
    success, stdout, stderr = run_command("python3 -m pip --version")
    if success:
        print(f"  ✅ pip可用: {stdout.strip()}")
    else:
        print(f"  ❌ pip不可用: {stderr}")
        return False
    return True

def upgrade_pip():
    """升级pip"""
    print("🔧 升级pip...")
    success, stdout, stderr = run_command("python3 -m pip install --upgrade pip")
    if success:
        print("  ✅ pip升级成功")
    else:
        print(f"  ⚠️  pip升级失败: {stderr}")

def install_minimal_deps():
    """安装最小依赖"""
    print("📦 安装最小依赖...")
    
    minimal_packages = [
        "requests>=2.25.0",
        "beautifulsoup4>=4.9.0",
        "fake-useragent>=0.1.11"
    ]
    
    for package in minimal_packages:
        print(f"  📍 安装 {package}...")
        success, stdout, stderr = run_command(f"python3 -m pip install '{package}'")
        if success:
            print(f"    ✅ {package} 安装成功")
        else:
            print(f"    ❌ {package} 安装失败: {stderr}")

def install_optional_deps():
    """安装可选依赖"""
    print("📦 安装可选依赖...")
    
    optional_packages = [
        ("flask>=2.0.0", "Web界面"),
        ("schedule>=1.1.0", "定时任务"),
        ("pandas>=1.3.0", "数据处理")
    ]
    
    for package, desc in optional_packages:
        print(f"  📍 安装 {package} ({desc})...")
        success, stdout, stderr = run_command(f"python3 -m pip install '{package}'")
        if success:
            print(f"    ✅ {package} 安装成功")
        else:
            print(f"    ⚠️  {package} 安装失败，跳过: {stderr.split(':')[0] if ':' in stderr else stderr}")

def verify_installation():
    """验证安装"""
    print("🔍 验证核心功能...")
    
    # 测试核心导入
    test_imports = [
        ("requests", "网络请求"),
        ("bs4", "HTML解析"),
        ("sqlite3", "数据库(内置)"),
        ("json", "JSON处理(内置)"),
        ("datetime", "时间处理(内置)")
    ]
    
    for module, desc in test_imports:
        try:
            __import__(module)
            print(f"  ✅ {module} ({desc})")
        except ImportError:
            print(f"  ❌ {module} ({desc}) - 导入失败")

def test_basic_functionality():
    """测试基本功能"""
    print("🧪 测试基本功能...")
    
    try:
        # 测试HTTP请求
        import requests
        response = requests.get("https://httpbin.org/json", timeout=5)
        if response.status_code == 200:
            print("  ✅ 网络请求功能正常")
        else:
            print("  ⚠️  网络请求测试失败")
    except Exception as e:
        print(f"  ⚠️  网络请求测试失败: {e}")
    
    try:
        # 测试SQLite
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()
        print("  ✅ SQLite功能正常")
    except Exception as e:
        print(f"  ❌ SQLite测试失败: {e}")

def main():
    """主函数"""
    print("🍎 macOS环境问题诊断和修复")
    print("=" * 50)
    
    # 步骤1: 检查Python版本
    if not check_python_version():
        print("❌ Python版本不兼容，请升级Python")
        return
    
    # 步骤2: 检查pip
    if not check_pip():
        print("❌ pip不可用，请安装pip")
        return
    
    # 步骤3: 升级pip
    upgrade_pip()
    
    # 步骤4: 安装最小依赖
    install_minimal_deps()
    
    # 步骤5: 安装可选依赖
    install_optional_deps()
    
    # 步骤6: 验证安装
    verify_installation()
    
    # 步骤7: 测试基本功能
    test_basic_functionality()
    
    print("\n🎉 修复完成!")
    print("📋 下一步:")
    print("  python3 demo.py          # 运行演示")
    print("  python3 test_basic.py    # 运行基础测试")

if __name__ == "__main__":
    main()