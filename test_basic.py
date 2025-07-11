#!/usr/bin/env python3
"""
基础功能测试脚本 - 不依赖外部包

用于验证核心模块是否正确创建和初始化
"""

import sys
import os
import sqlite3
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

def test_config_basic():
    """测试配置模块基础功能"""
    print("🔧 测试配置模块...")
    
    try:
        from keyword_crawler.config import Config
        
        # 测试目录创建
        Config.ensure_directories()
        print("  ✅ 目录创建成功")
        
        # 测试配置值
        print(f"  ✅ 数据目录: {Config.DATA_DIR}")
        print(f"  ✅ 日志目录: {Config.LOGS_DIR}")
        print(f"  ✅ 结果目录: {Config.RESULTS_DIR}")
        
        # 测试搜索引擎配置
        engines = Config.get_enabled_search_engines()
        print(f"  ✅ 启用的搜索引擎: {list(engines.keys())}")
        
        # 测试默认关键词
        keywords = Config.DEFAULT_KEYWORDS
        print(f"  ✅ 默认关键词数量: {len(keywords)}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 配置模块测试失败: {e}")
        return False

def test_database_basic():
    """测试数据库模块基础功能"""
    print("🗄️ 测试数据库模块...")
    
    try:
        from keyword_crawler.database import DatabaseManager
        
        # 初始化数据库
        db_manager = DatabaseManager()
        print("  ✅ 数据库初始化成功")
        
        # 检查数据库文件是否创建
        db_path = db_manager.db_path
        if os.path.exists(db_path):
            print(f"  ✅ 数据库文件创建: {db_path}")
        else:
            print(f"  ❌ 数据库文件未找到: {db_path}")
            return False
        
        # 测试基本操作
        success = db_manager.add_keyword("测试关键词")
        print(f"  ✅ 添加关键词: {success}")
        
        keywords = db_manager.get_active_keywords()
        print(f"  ✅ 获取关键词数量: {len(keywords)}")
        
        # 创建测试任务
        task_id = db_manager.create_search_task("测试", "baidu")
        print(f"  ✅ 创建测试任务ID: {task_id}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 数据库模块测试失败: {e}")
        return False

def test_directory_structure():
    """测试目录结构"""
    print("📁 测试目录结构...")
    
    try:
        # 检查主要文件是否存在
        main_files = [
            'main.py',
            'README.md',
            'requirements.txt',
            'keyword_crawler/__init__.py',
            'keyword_crawler/config.py',
            'keyword_crawler/database.py',
            'keyword_crawler/crawler.py',
            'keyword_crawler/scheduler.py',
            'keyword_crawler/visualizer.py',
            'keyword_crawler/web_app.py'
        ]
        
        missing_files = []
        for file_path in main_files:
            if os.path.exists(file_path):
                print(f"  ✅ {file_path}")
            else:
                print(f"  ❌ {file_path} (缺失)")
                missing_files.append(file_path)
        
        if missing_files:
            print(f"  ⚠️  缺失文件: {len(missing_files)}")
            return False
        else:
            print("  ✅ 所有核心文件存在")
            return True
        
    except Exception as e:
        print(f"  ❌ 目录结构测试失败: {e}")
        return False

def test_module_imports():
    """测试模块导入"""
    print("📦 测试模块导入...")
    
    modules_to_test = [
        ('keyword_crawler.config', 'Config'),
        ('keyword_crawler.database', 'DatabaseManager'),
        ('keyword_crawler.crawler', 'SearchCrawler'),
        ('keyword_crawler.scheduler', 'TaskScheduler'),
        ('keyword_crawler.visualizer', 'DataVisualizer'),
    ]
    
    failed_imports = []
    
    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"  ✅ {module_name}.{class_name}")
        except Exception as e:
            print(f"  ❌ {module_name}.{class_name}: {e}")
            failed_imports.append(f"{module_name}.{class_name}")
    
    if failed_imports:
        print(f"  ⚠️  导入失败: {len(failed_imports)}")
        return False
    else:
        print("  ✅ 所有模块导入成功")
        return True

def test_sqlite_functionality():
    """测试SQLite功能"""
    print("🗃️ 测试SQLite功能...")
    
    try:
        # 创建测试数据库
        test_db_path = "test_database.db"
        
        # 连接数据库
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        
        # 创建测试表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 插入测试数据
        cursor.execute("INSERT INTO test_table (name) VALUES (?)", ("测试数据",))
        conn.commit()
        
        # 查询数据
        cursor.execute("SELECT * FROM test_table")
        results = cursor.fetchall()
        
        conn.close()
        
        # 清理测试数据库
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
        
        print(f"  ✅ SQLite操作成功，插入并查询了 {len(results)} 条记录")
        return True
        
    except Exception as e:
        print(f"  ❌ SQLite测试失败: {e}")
        return False

def run_basic_tests():
    """运行基础测试"""
    print("🚀 开始基础功能测试...\n")
    
    tests = [
        ("目录结构", test_directory_structure),
        ("模块导入", test_module_imports),
        ("SQLite功能", test_sqlite_functionality),
        ("配置模块", test_config_basic),
        ("数据库模块", test_database_basic),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"{'='*50}")
        result = test_func()
        results[test_name] = result
        print()
    
    # 输出测试结果摘要
    print(f"{'='*50}")
    print("📋 基础测试结果摘要:")
    print(f"{'='*50}")
    
    passed = 0
    failed = 0
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n📊 总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("🎉 基础测试全部通过！核心功能正常。")
        print("\n📋 下一步:")
        print("  1. 安装依赖: pip install -r requirements.txt")
        print("  2. 初始化系统: python3 main.py init")
        print("  3. 启动Web界面: python3 main.py web")
    else:
        print("⚠️  部分基础测试失败，请检查文件结构和导入。")
    
    return failed == 0

if __name__ == "__main__":
    try:
        success = run_basic_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生意外错误: {e}")
        sys.exit(1)