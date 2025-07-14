#!/usr/bin/env python3
"""
可视化性能测试脚本

测试可视化系统的性能优化效果，包括：
- 生成时间对比
- 内存使用对比
- 缓存命中率
- 并发性能测试
"""

import time
import sys
import psutil
import os
from typing import Dict, List
import json
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from keyword_crawler import DataVisualizer, DatabaseManager


class VisualizationPerformanceTester:
    """可视化性能测试器"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.visualizer = DataVisualizer(self.db_manager)
        self.test_results = {}
    
    def get_memory_usage(self) -> float:
        """获取当前内存使用量（MB）"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    def test_single_generation(self, days: int = 7, iterations: int = 3) -> Dict:
        """测试单次图表生成性能"""
        print(f"测试单次图表生成性能 (days={days}, iterations={iterations})")
        
        results = []
        
        for i in range(iterations):
            print(f"  第 {i+1}/{iterations} 次测试...")
            
            # 清理缓存确保公平测试
            self.visualizer._clear_cache()
            
            # 记录开始状态
            start_time = time.time()
            start_memory = self.get_memory_usage()
            
            try:
                # 执行图表生成
                generated_files = self.visualizer.generate_all_visualizations_async(days=days)
                
                # 记录结束状态
                end_time = time.time()
                end_memory = self.get_memory_usage()
                
                # 获取性能统计
                perf_stats = self.visualizer.get_performance_stats()
                cache_stats = self.visualizer.get_cache_stats()
                
                result = {
                    'iteration': i + 1,
                    'generation_time': round(end_time - start_time, 2),
                    'memory_usage_mb': round(end_memory - start_memory, 2),
                    'charts_generated': len(generated_files) if generated_files else 0,
                    'cache_hit_rate': cache_stats.get('hit_rate', 0),
                    'success': bool(generated_files)
                }
                
                results.append(result)
                print(f"    用时: {result['generation_time']}秒, 内存: {result['memory_usage_mb']}MB")
                
            except Exception as e:
                result = {
                    'iteration': i + 1,
                    'error': str(e),
                    'success': False
                }
                results.append(result)
                print(f"    测试失败: {e}")
        
        # 计算平均值
        successful_results = [r for r in results if r['success']]
        if successful_results:
            avg_time = sum(r['generation_time'] for r in successful_results) / len(successful_results)
            avg_memory = sum(r['memory_usage_mb'] for r in successful_results) / len(successful_results)
            avg_cache_hit = sum(r['cache_hit_rate'] for r in successful_results) / len(successful_results)
            
            summary = {
                'test_type': 'single_generation',
                'days': days,
                'iterations': iterations,
                'successful_runs': len(successful_results),
                'avg_generation_time': round(avg_time, 2),
                'avg_memory_usage_mb': round(avg_memory, 2),
                'avg_cache_hit_rate': round(avg_cache_hit, 2),
                'results': results
            }
        else:
            summary = {
                'test_type': 'single_generation',
                'days': days,
                'iterations': iterations,
                'successful_runs': 0,
                'error': 'All iterations failed',
                'results': results
            }
        
        return summary
    
    def test_cache_performance(self, days: int = 7) -> Dict:
        """测试缓存性能"""
        print(f"测试缓存性能 (days={days})")
        
        # 第一次生成（冷缓存）
        print("  冷缓存测试...")
        self.visualizer._clear_cache()
        start_time = time.time()
        first_result = self.visualizer.generate_all_visualizations_async(days=days)
        cold_time = time.time() - start_time
        
        # 第二次生成（热缓存）
        print("  热缓存测试...")
        start_time = time.time()
        second_result = self.visualizer.generate_all_visualizations_async(days=days)
        hot_time = time.time() - start_time
        
        # 获取缓存统计
        cache_stats = self.visualizer.get_cache_stats()
        
        cache_improvement = ((cold_time - hot_time) / cold_time * 100) if cold_time > 0 else 0
        
        result = {
            'test_type': 'cache_performance',
            'days': days,
            'cold_cache_time': round(cold_time, 2),
            'hot_cache_time': round(hot_time, 2),
            'cache_improvement_percent': round(cache_improvement, 2),
            'cache_stats': cache_stats,
            'success': bool(first_result and second_result)
        }
        
        print(f"    冷缓存: {cold_time:.2f}秒, 热缓存: {hot_time:.2f}秒")
        print(f"    缓存提升: {cache_improvement:.1f}%")
        
        return result
    
    def test_different_time_ranges(self) -> Dict:
        """测试不同时间范围的性能"""
        print("测试不同时间范围的性能")
        
        time_ranges = [7, 30, 90]
        results = []
        
        for days in time_ranges:
            print(f"  测试 {days} 天数据...")
            
            self.visualizer._clear_cache()
            start_time = time.time()
            start_memory = self.get_memory_usage()
            
            try:
                generated_files = self.visualizer.generate_all_visualizations_async(days=days)
                
                end_time = time.time()
                end_memory = self.get_memory_usage()
                
                result = {
                    'days': days,
                    'generation_time': round(end_time - start_time, 2),
                    'memory_usage_mb': round(end_memory - start_memory, 2),
                    'charts_generated': len(generated_files) if generated_files else 0,
                    'success': bool(generated_files)
                }
                
                results.append(result)
                print(f"    {days}天: {result['generation_time']}秒, {result['memory_usage_mb']}MB")
                
            except Exception as e:
                result = {
                    'days': days,
                    'error': str(e),
                    'success': False
                }
                results.append(result)
                print(f"    {days}天: 测试失败 - {e}")
        
        return {
            'test_type': 'time_range_comparison',
            'results': results
        }
    
    def test_memory_efficiency(self, days: int = 7) -> Dict:
        """测试内存效率"""
        print(f"测试内存效率 (days={days})")
        
        # 记录初始内存
        initial_memory = self.get_memory_usage()
        
        # 生成多次图表，检查内存泄漏
        memory_samples = [initial_memory]
        
        for i in range(5):
            print(f"  第 {i+1}/5 次生成...")
            
            try:
                self.visualizer.generate_all_visualizations_async(days=days)
                current_memory = self.get_memory_usage()
                memory_samples.append(current_memory)
                print(f"    内存使用: {current_memory:.1f}MB")
                
            except Exception as e:
                print(f"    生成失败: {e}")
        
        # 分析内存趋势
        max_memory = max(memory_samples)
        min_memory = min(memory_samples)
        final_memory = memory_samples[-1]
        
        memory_growth = final_memory - initial_memory
        memory_variation = max_memory - min_memory
        
        result = {
            'test_type': 'memory_efficiency',
            'days': days,
            'initial_memory_mb': round(initial_memory, 2),
            'final_memory_mb': round(final_memory, 2),
            'max_memory_mb': round(max_memory, 2),
            'memory_growth_mb': round(memory_growth, 2),
            'memory_variation_mb': round(memory_variation, 2),
            'memory_samples': [round(m, 2) for m in memory_samples],
            'potential_memory_leak': memory_growth > 50  # 超过50MB认为可能有内存泄漏
        }
        
        print(f"    内存增长: {memory_growth:.1f}MB, 变化幅度: {memory_variation:.1f}MB")
        
        return result
    
    def run_comprehensive_test(self) -> Dict:
        """运行综合性能测试"""
        print("=" * 60)
        print("开始可视化性能综合测试")
        print("=" * 60)
        
        test_start_time = time.time()
        
        all_results = {
            'test_timestamp': datetime.now().isoformat(),
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': round(psutil.virtual_memory().total / 1024**3, 2),
                'python_version': sys.version
            }
        }
        
        try:
            # 1. 单次生成性能测试
            all_results['single_generation'] = self.test_single_generation(days=7, iterations=3)
            
            # 2. 缓存性能测试
            all_results['cache_performance'] = self.test_cache_performance(days=7)
            
            # 3. 不同时间范围测试
            all_results['time_range_comparison'] = self.test_different_time_ranges()
            
            # 4. 内存效率测试
            all_results['memory_efficiency'] = self.test_memory_efficiency(days=7)
            
            test_duration = time.time() - test_start_time
            all_results['total_test_time'] = round(test_duration, 2)
            
            print("\n" + "=" * 60)
            print("测试完成！")
            print("=" * 60)
            
            # 生成测试报告
            self.generate_test_report(all_results)
            
        except Exception as e:
            all_results['error'] = str(e)
            print(f"\n测试过程中发生错误: {e}")
        
        finally:
            # 清理资源
            self.visualizer.cleanup()
        
        return all_results
    
    def generate_test_report(self, results: Dict):
        """生成测试报告"""
        print("\n📊 性能测试报告")
        print("-" * 40)
        
        # 单次生成性能
        if 'single_generation' in results:
            single = results['single_generation']
            if single.get('successful_runs', 0) > 0:
                print(f"✅ 平均生成时间: {single['avg_generation_time']}秒")
                print(f"✅ 平均内存使用: {single['avg_memory_usage_mb']}MB")
                print(f"✅ 平均缓存命中率: {single['avg_cache_hit_rate']}%")
            else:
                print("❌ 单次生成测试失败")
        
        # 缓存性能
        if 'cache_performance' in results:
            cache = results['cache_performance']
            if cache.get('success'):
                print(f"🚀 缓存性能提升: {cache['cache_improvement_percent']}%")
                print(f"   冷缓存: {cache['cold_cache_time']}秒 → 热缓存: {cache['hot_cache_time']}秒")
            else:
                print("❌ 缓存性能测试失败")
        
        # 内存效率
        if 'memory_efficiency' in results:
            memory = results['memory_efficiency']
            if memory.get('potential_memory_leak'):
                print(f"⚠️  检测到潜在内存泄漏: +{memory['memory_growth_mb']}MB")
            else:
                print(f"✅ 内存使用稳定: {memory['memory_growth_mb']:+.1f}MB")
        
        # 保存详细报告
        report_filename = f"visualization_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(report_filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\n📄 详细报告已保存: {report_filename}")
        except Exception as e:
            print(f"\n❌ 保存报告失败: {e}")


def main():
    """主函数"""
    print("🔧 可视化性能测试工具")
    print("这个工具将测试可视化系统的性能优化效果\n")
    
    # 检查依赖
    try:
        import matplotlib
        import plotly
        import seaborn
        print("✅ 依赖检查通过")
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        return 1
    
    # 运行测试
    tester = VisualizationPerformanceTester()
    results = tester.run_comprehensive_test()
    
    if 'error' in results:
        print(f"\n❌ 测试失败: {results['error']}")
        return 1
    
    print("\n🎉 所有测试完成！")
    return 0


if __name__ == '__main__':
    sys.exit(main())