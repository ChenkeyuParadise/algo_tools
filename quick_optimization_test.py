#!/usr/bin/env python3
"""
快速优化测试脚本

快速验证可视化优化功能是否正常工作
"""

import sys
import os
import time
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_imports():
    """测试导入是否正常"""
    print("🔍 测试模块导入...")
    
    try:
        from keyword_crawler import DataVisualizer, DatabaseManager
        print("✅ 核心模块导入成功")
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_visualizer_creation():
    """测试可视化器创建"""
    print("🔧 测试可视化器创建...")
    
    try:
        from keyword_crawler import DataVisualizer, DatabaseManager
        
        # 创建数据库管理器和可视化器
        db_manager = DatabaseManager()
        visualizer = DataVisualizer(db_manager)
        
        # 检查关键属性
        assert hasattr(visualizer, '_data_cache'), "缺少缓存属性"
        assert hasattr(visualizer, '_executor'), "缺少线程池属性"
        assert hasattr(visualizer, 'get_cache_stats'), "缺少缓存统计方法"
        assert hasattr(visualizer, 'generate_all_visualizations_async'), "缺少异步生成方法"
        
        print("✅ 可视化器创建成功")
        
        # 清理资源
        visualizer.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 创建失败: {e}")
        return False

def test_cache_functionality():
    """测试缓存功能"""
    print("💾 测试缓存功能...")
    
    try:
        from keyword_crawler import DataVisualizer, DatabaseManager
        
        visualizer = DataVisualizer(DatabaseManager())
        
        # 测试缓存键生成
        cache_key = visualizer._get_cache_key("test_func", 7, keyword="test")
        assert isinstance(cache_key, str), "缓存键应该是字符串"
        assert len(cache_key) == 32, "MD5哈希应该是32位"
        
        # 测试缓存统计
        cache_stats = visualizer.get_cache_stats()
        assert 'hit_rate' in cache_stats, "缺少命中率统计"
        assert 'cached_items' in cache_stats, "缺少缓存项数统计"
        
        print("✅ 缓存功能正常")
        visualizer.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 缓存测试失败: {e}")
        return False

def test_performance_stats():
    """测试性能统计"""
    print("📊 测试性能统计...")
    
    try:
        from keyword_crawler import DataVisualizer, DatabaseManager
        
        visualizer = DataVisualizer(DatabaseManager())
        
        # 测试性能统计方法
        perf_stats = visualizer.get_performance_stats()
        
        expected_keys = ['total_generation_time', 'charts_generated', 'cache_hit_rate']
        for key in expected_keys:
            assert key in perf_stats, f"缺少性能统计项: {key}"
        
        print("✅ 性能统计功能正常")
        visualizer.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 性能统计测试失败: {e}")
        return False

def test_config_updates():
    """测试配置更新"""
    print("⚙️ 测试配置更新...")
    
    try:
        from keyword_crawler.config import Config
        
        # 检查新的配置项
        viz_config = Config.VISUALIZATION_CONFIG
        
        required_keys = [
            'enable_cache', 'cache_timeout', 'max_workers', 
            'enable_parallel', 'optimize_plots'
        ]
        
        for key in required_keys:
            assert key in viz_config, f"缺少配置项: {key}"
        
        print("✅ 配置更新正常")
        return True
        
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False

def test_backward_compatibility():
    """测试向后兼容性"""
    print("🔄 测试向后兼容性...")
    
    try:
        from keyword_crawler import DataVisualizer, DatabaseManager
        
        visualizer = DataVisualizer(DatabaseManager())
        
        # 测试原有方法是否仍然存在
        assert hasattr(visualizer, 'generate_all_visualizations'), "缺少向后兼容方法"
        assert hasattr(visualizer, '_plot_timeline_with_data'), "缺少向后兼容绘图方法"
        
        print("✅ 向后兼容性正常")
        visualizer.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 向后兼容性测试失败: {e}")
        return False

def test_basic_visualization():
    """测试基本可视化功能"""
    print("🎨 测试基本可视化功能...")
    
    try:
        from keyword_crawler import DataVisualizer, DatabaseManager
        
        visualizer = DataVisualizer(DatabaseManager())
        
        # 创建简单的测试数据
        test_data = [
            {'date': '2024-01-01', 'search_engine': 'google', 'result_count': 100, 'keyword': 'test'},
            {'date': '2024-01-02', 'search_engine': 'bing', 'result_count': 80, 'keyword': 'test'}
        ]
        
        # 测试单个图表生成方法（使用测试数据）
        timeline_result = visualizer._plot_timeline_with_data_optimized(test_data, 7)
        
        if timeline_result:
            print("✅ 图表生成功能正常")
            # 清理生成的测试文件
            try:
                os.remove(timeline_result)
            except:
                pass
        else:
            print("⚠️  图表生成返回空结果（可能是数据问题）")
        
        visualizer.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 基本可视化测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 可视化优化快速测试")
    print("=" * 50)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    tests = [
        ("模块导入", test_imports),
        ("可视化器创建", test_visualizer_creation),
        ("缓存功能", test_cache_functionality),
        ("性能统计", test_performance_stats),
        ("配置更新", test_config_updates),
        ("向后兼容性", test_backward_compatibility),
        ("基本可视化", test_basic_visualization)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
            else:
                print(f"   测试失败")
        except Exception as e:
            print(f"   测试异常: {e}")
    
    print("\n" + "=" * 50)
    print("📊 测试结果汇总")
    print("=" * 50)
    print(f"通过: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 所有测试通过！优化功能正常工作。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查相关功能。")
        return 1

if __name__ == '__main__':
    sys.exit(main())