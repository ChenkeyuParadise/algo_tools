#!/bin/bash

echo "🍎 macOS环境 - 关键词爬虫工具安装脚本"
echo "================================================"

# 检查Python版本
echo "📍 检查Python版本..."
python3 --version

# 检查pip版本
echo "📍 检查pip版本..."
python3 -m pip --version

# 升级pip
echo "📍 升级pip..."
python3 -m pip install --upgrade pip

# 安装核心依赖 (分步安装避免冲突)
echo "📍 安装核心依赖..."

echo "  🔧 安装基础网络库..."
python3 -m pip install requests>=2.25.0
python3 -m pip install beautifulsoup4>=4.9.0

echo "  🔧 安装XML解析库..."
python3 -m pip install lxml>=4.6.0

echo "  🔧 安装数据处理库..."
python3 -m pip install pandas>=1.3.0

echo "  🔧 安装可视化库..."
python3 -m pip install matplotlib>=3.3.0
python3 -m pip install seaborn>=0.11.0
python3 -m pip install plotly>=5.0.0

echo "  🔧 安装任务调度库..."
python3 -m pip install schedule>=1.1.0
python3 -m pip install APScheduler>=3.8.0

echo "  🔧 安装Web框架..."
python3 -m pip install flask>=2.0.0

echo "  🔧 安装工具库..."
python3 -m pip install fake-useragent>=0.1.11

echo "✅ 依赖安装完成!"

# 验证安装
echo "📍 验证安装..."
python3 -c "
try:
    import requests, bs4, pandas, matplotlib, flask, schedule
    print('✅ 核心依赖验证成功!')
except ImportError as e:
    print(f'❌ 依赖验证失败: {e}')
"

# 初始化系统
echo "📍 初始化系统..."
python3 main.py init

echo "🎉 安装完成!"
echo "📋 使用方法:"
echo "  python3 demo.py          # 运行演示"
echo "  python3 main.py web      # 启动Web界面"