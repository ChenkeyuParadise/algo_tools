import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端，提高性能
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
import os
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor
import time
import hashlib
import pickle
import weakref

from .config import Config
from .database import DatabaseManager

# 设置matplotlib中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 优化matplotlib性能
plt.rcParams['figure.max_open_warning'] = 50
plt.rcParams['agg.path.chunksize'] = 10000

class DataVisualizer:
    """数据可视化类 - 高性能异步版本"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager or DatabaseManager()
        self.results_dir = Config.RESULTS_DIR
        Config.ensure_directories()
        
        # 设置seaborn样式
        sns.set_style(Config.VISUALIZATION_CONFIG['style'])
        sns.set_palette(Config.VISUALIZATION_CONFIG['color_palette'])
        
        # 优化的缓存系统
        self._data_cache = {}
        self._cache_timeout = 300  # 5分钟缓存
        self._cache_hits = 0
        self._cache_misses = 0
        
        # 线程池配置 - 使用CPU核心数优化
        import multiprocessing
        max_workers = min(multiprocessing.cpu_count(), 6)  # 限制最大线程数
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="chart_gen")
        
        # 进程池用于CPU密集型任务
        self._process_executor = ProcessPoolExecutor(max_workers=2)
        
        # 性能监控
        self._performance_stats = {
            'total_generation_time': 0,
            'cache_hit_rate': 0,
            'charts_generated': 0
        }
    
    def _get_cache_key(self, func_name: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = f"{func_name}_{args}_{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_data(self, cache_key: str, data_func: Callable, *args, **kwargs):
        """智能缓存数据获取"""
        now = datetime.now()
        
        # 检查缓存是否存在且未过期
        if cache_key in self._data_cache:
            cached_data, cached_time = self._data_cache[cache_key]
            if (now - cached_time).total_seconds() < self._cache_timeout:
                self._cache_hits += 1
                return cached_data
        
        # 获取新数据并缓存
        self._cache_misses += 1
        try:
            data = data_func(*args, **kwargs)
            self._data_cache[cache_key] = (data, now)
            
            # 清理过期缓存
            self._cleanup_expired_cache()
            return data
        except Exception as e:
            print(f"缓存数据获取失败: {e}")
            return []
    
    def _cleanup_expired_cache(self):
        """清理过期缓存"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, cached_time) in self._data_cache.items()
            if (now - cached_time).total_seconds() > self._cache_timeout
        ]
        for key in expired_keys:
            del self._data_cache[key]
    
    def _clear_cache(self):
        """清除数据缓存"""
        self._data_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate': round(hit_rate, 2),
            'cached_items': len(self._data_cache)
        }

    def plot_search_results_timeline(self, days: int = 7, save_path: str = None) -> str:
        """绘制搜索结果时间线图"""
        # 获取数据
        results_data = self.db_manager.get_search_results_count(days=days)
        
        if not results_data:
            return None
        
        # 转换为DataFrame
        df = pd.DataFrame(results_data)
        df['date'] = pd.to_datetime(df['date'])
        
        # 创建图表
        fig, ax = plt.subplots(figsize=Config.VISUALIZATION_CONFIG['figure_size'])
        
        # 按搜索引擎分组绘制
        for engine in df['search_engine'].unique():
            engine_data = df[df['search_engine'] == engine]
            ax.plot(engine_data['date'], engine_data['result_count'], 
                   marker='o', label=engine, linewidth=2, markersize=6)
        
        # 设置图表
        ax.set_title(f'搜索结果数量时间线 (最近{days}天)', fontsize=16, fontweight='bold')
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('结果数量', fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 设置日期格式
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # 保存图表
        if save_path is None:
            save_path = os.path.join(self.results_dir, f'search_results_timeline_{days}days.png')
        
        plt.savefig(save_path, dpi=Config.VISUALIZATION_CONFIG['dpi'], bbox_inches='tight')
        plt.close()
        
        return save_path
    
    def plot_keyword_comparison(self, keywords: List[str] = None, days: int = 7, save_path: str = None) -> str:
        """绘制关键词对比图"""
        # 获取数据
        if keywords is None:
            keywords = self.db_manager.get_active_keywords()[:10]  # 限制前10个关键词
        
        keyword_data = []
        for keyword in keywords:
            data = self.db_manager.get_search_results_count(keyword=keyword, days=days)
            if data:
                total_results = sum(item['result_count'] for item in data)
                keyword_data.append({'keyword': keyword, 'total_results': total_results})
        
        if not keyword_data:
            return None
        
        # 转换为DataFrame并排序
        df = pd.DataFrame(keyword_data)
        df = df.sort_values('total_results', ascending=True)
        
        # 创建水平柱状图
        fig, ax = plt.subplots(figsize=(10, max(6, len(df) * 0.5)))
        
        bars = ax.barh(df['keyword'], df['total_results'], color=sns.color_palette("viridis", len(df)))
        
        # 在每个柱子上添加数值标签
        for bar in bars:
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2, 
                   f'{int(width)}', ha='left', va='center', fontsize=10)
        
        ax.set_title(f'关键词搜索结果对比 (最近{days}天)', fontsize=16, fontweight='bold')
        ax.set_xlabel('搜索结果数量', fontsize=12)
        ax.set_ylabel('关键词', fontsize=12)
        ax.grid(True, axis='x', alpha=0.3)
        
        plt.tight_layout()
        
        # 保存图表
        if save_path is None:
            save_path = os.path.join(self.results_dir, f'keyword_comparison_{days}days.png')
        
        plt.savefig(save_path, dpi=Config.VISUALIZATION_CONFIG['dpi'], bbox_inches='tight')
        plt.close()
        
        return save_path
    
    def plot_search_engine_performance(self, days: int = 7, save_path: str = None) -> str:
        """绘制搜索引擎性能对比图"""
        # 获取任务统计数据
        task_data = self.db_manager.get_task_statistics(days=days)
        
        if not task_data:
            return None
        
        # 转换为DataFrame并聚合数据
        df = pd.DataFrame(task_data)
        engine_stats = df.groupby('search_engine').agg({
            'total_tasks': 'sum',
            'completed_tasks': 'sum',
            'failed_tasks': 'sum'
        }).reset_index()
        
        # 计算成功率
        engine_stats['success_rate'] = (engine_stats['completed_tasks'] / 
                                      engine_stats['total_tasks'] * 100).round(2)
        
        # 创建子图
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. 任务总数对比
        ax1.bar(engine_stats['search_engine'], engine_stats['total_tasks'], 
               color=sns.color_palette("Set2", len(engine_stats)))
        ax1.set_title('搜索引擎任务总数对比', fontsize=14, fontweight='bold')
        ax1.set_ylabel('任务数量')
        
        # 2. 成功率对比
        ax2.bar(engine_stats['search_engine'], engine_stats['success_rate'], 
               color=sns.color_palette("Set1", len(engine_stats)))
        ax2.set_title('搜索引擎成功率对比', fontsize=14, fontweight='bold')
        ax2.set_ylabel('成功率 (%)')
        ax2.set_ylim(0, 100)
        
        # 3. 成功vs失败任务堆叠图
        ax3.bar(engine_stats['search_engine'], engine_stats['completed_tasks'], 
               label='成功', color='green', alpha=0.7)
        ax3.bar(engine_stats['search_engine'], engine_stats['failed_tasks'], 
               bottom=engine_stats['completed_tasks'], label='失败', color='red', alpha=0.7)
        ax3.set_title('任务完成情况', fontsize=14, fontweight='bold')
        ax3.set_ylabel('任务数量')
        ax3.legend()
        
        # 4. 饼图显示总体分布
        total_completed = engine_stats['completed_tasks'].sum()
        total_failed = engine_stats['failed_tasks'].sum()
        
        if total_completed + total_failed > 0:
            ax4.pie([total_completed, total_failed], 
                   labels=['成功', '失败'], 
                   colors=['green', 'red'], 
                   autopct='%1.1f%%',
                   startangle=90)
            ax4.set_title('总体任务完成情况', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        # 保存图表
        if save_path is None:
            save_path = os.path.join(self.results_dir, f'search_engine_performance_{days}days.png')
        
        plt.savefig(save_path, dpi=Config.VISUALIZATION_CONFIG['dpi'], bbox_inches='tight')
        plt.close()
        
        return save_path
    
    def plot_daily_activity_heatmap(self, days: int = 30, save_path: str = None) -> str:
        """绘制每日活动热力图"""
        # 获取数据
        task_data = self.db_manager.get_task_statistics(days=days)
        
        if not task_data:
            return None
        
        # 转换为DataFrame
        df = pd.DataFrame(task_data)
        df['date'] = pd.to_datetime(df['date'])
        df['weekday'] = df['date'].dt.day_name()
        df['hour'] = df['date'].dt.hour  # 如果需要按小时分析
        
        # 按日期和搜索引擎聚合
        daily_activity = df.groupby(['date', 'search_engine'])['completed_tasks'].sum().reset_index()
        
        # 创建透视表用于热力图
        pivot_table = daily_activity.pivot(index='search_engine', columns='date', values='completed_tasks')
        pivot_table = pivot_table.fillna(0)
        
        # 创建热力图
        fig, ax = plt.subplots(figsize=(15, 6))
        
        sns.heatmap(pivot_table, 
                   annot=True, 
                   fmt='.0f', 
                   cmap='YlOrRd', 
                   ax=ax,
                   cbar_kws={'label': '完成任务数'})
        
        ax.set_title(f'每日搜索活动热力图 (最近{days}天)', fontsize=16, fontweight='bold')
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('搜索引擎', fontsize=12)
        
        # 旋转日期标签
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # 保存图表
        if save_path is None:
            save_path = os.path.join(self.results_dir, f'daily_activity_heatmap_{days}days.png')
        
        plt.savefig(save_path, dpi=Config.VISUALIZATION_CONFIG['dpi'], bbox_inches='tight')
        plt.close()
        
        return save_path
    
    def generate_interactive_dashboard(self, days: int = 7) -> str:
        """生成交互式仪表板（使用Plotly）"""
        # 获取数据
        results_data = self.db_manager.get_search_results_count(days=days)
        task_data = self.db_manager.get_task_statistics(days=days)
        
        if not results_data and not task_data:
            return None
        
        # 创建子图
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('搜索结果时间趋势', '搜索引擎性能对比', 
                          '关键词热度排行', '任务完成状态'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"type": "pie"}]]
        )
        
        # 1. 搜索结果时间趋势
        if results_data:
            df_results = pd.DataFrame(results_data)
            df_results['date'] = pd.to_datetime(df_results['date'])
            
            for engine in df_results['search_engine'].unique():
                engine_data = df_results[df_results['search_engine'] == engine]
                fig.add_trace(
                    go.Scatter(x=engine_data['date'], y=engine_data['result_count'],
                             mode='lines+markers', name=engine, line=dict(width=3)),
                    row=1, col=1
                )
        
        # 2. 搜索引擎性能对比
        if task_data:
            df_tasks = pd.DataFrame(task_data)
            engine_stats = df_tasks.groupby('search_engine').agg({
                'total_tasks': 'sum',
                'completed_tasks': 'sum'
            }).reset_index()
            engine_stats['success_rate'] = (engine_stats['completed_tasks'] / 
                                          engine_stats['total_tasks'] * 100).round(2)
            
            fig.add_trace(
                go.Bar(x=engine_stats['search_engine'], y=engine_stats['success_rate'],
                      name='成功率', marker_color='lightblue'),
                row=1, col=2
            )
        
        # 3. 关键词热度排行
        if results_data:
            keyword_stats = df_results.groupby('keyword')['result_count'].sum().reset_index()
            keyword_stats = keyword_stats.sort_values('result_count', ascending=False).head(10)
            
            fig.add_trace(
                go.Bar(x=keyword_stats['result_count'], y=keyword_stats['keyword'],
                      orientation='h', name='搜索结果数', marker_color='lightgreen'),
                row=2, col=1
            )
        
        # 4. 任务完成状态饼图
        if task_data:
            total_completed = df_tasks['completed_tasks'].sum()
            total_failed = df_tasks['failed_tasks'].sum()
            
            fig.add_trace(
                go.Pie(labels=['成功', '失败'], values=[total_completed, total_failed],
                      name="任务状态"),
                row=2, col=2
            )
        
        # 更新布局
        fig.update_layout(
            title=f'关键词爬虫数据仪表板 (最近{days}天)',
            title_x=0.5,
            height=800,
            showlegend=True
        )
        
        # 保存HTML文件
        html_path = os.path.join(self.results_dir, f'dashboard_{days}days.html')
        fig.write_html(html_path)
        
        return html_path
    
    def generate_summary_report(self, days: int = 7) -> Dict[str, Any]:
        """生成数据摘要报告"""
        # 获取数据
        results_data = self.db_manager.get_search_results_count(days=days)
        task_data = self.db_manager.get_task_statistics(days=days)
        
        # 计算统计指标
        summary = {
            'period': f'最近{days}天',
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_search_results': 0,
            'total_tasks': 0,
            'success_rate': 0,
            'active_keywords': 0,
            'active_engines': 0,
            'top_keywords': [],
            'engine_performance': {}
        }
        
        if results_data:
            df_results = pd.DataFrame(results_data)
            summary['total_search_results'] = df_results['result_count'].sum()
            summary['active_keywords'] = df_results['keyword'].nunique()
            summary['active_engines'] = df_results['search_engine'].nunique()
            
            # 热门关键词
            keyword_stats = df_results.groupby('keyword')['result_count'].sum().sort_values(ascending=False)
            summary['top_keywords'] = keyword_stats.head(5).to_dict()
        
        if task_data:
            df_tasks = pd.DataFrame(task_data)
            summary['total_tasks'] = df_tasks['total_tasks'].sum()
            
            total_completed = df_tasks['completed_tasks'].sum()
            total_all = df_tasks['total_tasks'].sum()
            summary['success_rate'] = round(total_completed / total_all * 100, 2) if total_all > 0 else 0
            
            # 搜索引擎性能
            engine_stats = df_tasks.groupby('search_engine').agg({
                'total_tasks': 'sum',
                'completed_tasks': 'sum'
            })
            
            for engine, stats in engine_stats.iterrows():
                success_rate = round(stats['completed_tasks'] / stats['total_tasks'] * 100, 2) if stats['total_tasks'] > 0 else 0
                summary['engine_performance'][engine] = {
                    'total_tasks': int(stats['total_tasks']),
                    'completed_tasks': int(stats['completed_tasks']),
                    'success_rate': success_rate
                }
        
        return summary
    
    async def generate_all_visualizations_async_v2(self, days: int = 7, progress_callback: Optional[Callable] = None) -> Dict[str, str]:
        """异步生成所有可视化图表（真正的异步版本）"""
        start_time = time.time()
        
        def update_progress(step: int, total: int, message: str):
            """更新进度"""
            if progress_callback:
                progress_callback(step, total, message)
        
        # 预先获取所有需要的数据（避免重复查询）
        update_progress(1, 8, "正在获取数据...")
        
        # 创建异步任务获取数据
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results_data_task = loop.run_in_executor(
                self._executor,
                self._get_cached_data,
                self._get_cache_key("get_search_results_count", days),
                self.db_manager.get_search_results_count,
                days
            )
            
            task_data_task = loop.run_in_executor(
                self._executor,
                self._get_cached_data,
                self._get_cache_key("get_task_statistics", days), 
                self.db_manager.get_task_statistics,
                days
            )
            
            # 并发获取数据
            results_data, task_data = await asyncio.gather(results_data_task, task_data_task)
            
            update_progress(2, 8, "数据获取完成，开始生成图表...")
            
            # 定义图表生成任务
            chart_tasks = [
                ('timeline', self._plot_timeline_with_data_optimized, results_data, days),
                ('keyword_comparison', self._plot_keyword_comparison_with_data_optimized, results_data, days),
                ('engine_performance', self._plot_engine_performance_with_data_optimized, task_data, days),
                ('activity_heatmap', self._plot_heatmap_with_data_optimized, task_data, days),
                ('interactive_dashboard', self._generate_dashboard_with_data_optimized, results_data, task_data, days)
            ]
            
            generated_files = {}
            
            # 使用异步并发生成图表
            tasks = []
            for name, func, *args in chart_tasks:
                task = loop.run_in_executor(self._executor, func, *args)
                tasks.append((name, task))
            
            completed = 0
            for name, task in tasks:
                try:
                    file_path = await task
                    if file_path:
                        generated_files[name] = file_path
                    completed += 1
                    update_progress(2 + completed, 8, f"已完成 {name} 图表")
                except Exception as e:
                    print(f"生成 {name} 图表时出错: {e}")
                    completed += 1
                    update_progress(2 + completed, 8, f"{name} 图表生成失败")
            
            # 更新性能统计
            generation_time = time.time() - start_time
            self._performance_stats['total_generation_time'] += generation_time
            self._performance_stats['charts_generated'] += len(generated_files)
            cache_stats = self.get_cache_stats()
            self._performance_stats['cache_hit_rate'] = cache_stats['hit_rate']
            
            update_progress(8, 8, f"所有图表生成完成! 用时 {generation_time:.2f}秒")
            
            print(f"生成性能统计: 用时 {generation_time:.2f}秒, 缓存命中率 {cache_stats['hit_rate']}%")
            
            return generated_files
            
        finally:
            loop.close()

    def generate_all_visualizations_async(self, days: int = 7, progress_callback: Optional[Callable] = None) -> Dict[str, str]:
        """异步生成所有可视化图表（优化版本）"""
        start_time = time.time()
        
        def update_progress(step: int, total: int, message: str):
            """更新进度"""
            if progress_callback:
                progress_callback(step, total, message)
        
        # 预先获取所有需要的数据（避免重复查询）
        update_progress(1, 8, "正在获取数据...")
        
        results_cache_key = self._get_cache_key("get_search_results_count", days)
        tasks_cache_key = self._get_cache_key("get_task_statistics", days)
        
        # 并发获取数据
        data_futures = {
            'results': self._executor.submit(
                self._get_cached_data,
                results_cache_key, 
                self.db_manager.get_search_results_count, 
                days=days
            ),
            'tasks': self._executor.submit(
                self._get_cached_data,
                tasks_cache_key,
                self.db_manager.get_task_statistics,
                days=days
            )
        }
        
        # 等待数据获取完成
        results_data = data_futures['results'].result()
        task_data = data_futures['tasks'].result()
        
        update_progress(2, 8, "数据获取完成，开始生成图表...")
        
        # 定义图表生成任务（使用优化版本）
        chart_tasks = [
            ('timeline', self._plot_timeline_with_data_optimized, results_data, days),
            ('keyword_comparison', self._plot_keyword_comparison_with_data_optimized, results_data, days),
            ('engine_performance', self._plot_engine_performance_with_data_optimized, task_data, days),
            ('activity_heatmap', self._plot_heatmap_with_data_optimized, task_data, days),
            ('interactive_dashboard', self._generate_dashboard_with_data_optimized, results_data, task_data, days)
        ]
        
        generated_files = {}
        
        # 使用线程池并行生成图表
        future_to_name = {}
        for name, func, *args in chart_tasks:
            future = self._executor.submit(func, *args)
            future_to_name[future] = name
        
        completed = 0
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                file_path = future.result()
                if file_path:
                    generated_files[name] = file_path
                completed += 1
                update_progress(2 + completed, 8, f"已完成 {name} 图表")
            except Exception as e:
                print(f"生成 {name} 图表时出错: {e}")
                completed += 1
                update_progress(2 + completed, 8, f"{name} 图表生成失败")
        
        # 更新性能统计
        generation_time = time.time() - start_time
        self._performance_stats['total_generation_time'] += generation_time
        self._performance_stats['charts_generated'] += len(generated_files)
        cache_stats = self.get_cache_stats()
        self._performance_stats['cache_hit_rate'] = cache_stats['hit_rate']
        
        update_progress(8, 8, f"所有图表生成完成! 用时 {generation_time:.2f}秒")
        
        print(f"生成性能统计: 用时 {generation_time:.2f}秒, 缓存命中率 {cache_stats['hit_rate']}%")
        
        return generated_files
    
    def _plot_timeline_with_data_optimized(self, results_data: List[Dict], days: int) -> str:
        """优化版本：使用预获取的数据绘制时间线图"""
        if not results_data:
            return None
            
        try:
            # 转换为DataFrame - 更高效的方式
            df = pd.DataFrame(results_data)
            if df.empty:
                return None
                
            df['date'] = pd.to_datetime(df['date'], cache=True)  # 启用缓存
            
            # 创建图表 - 优化性能参数
            fig, ax = plt.subplots(figsize=Config.VISUALIZATION_CONFIG['figure_size'], dpi=80)
            
            # 按搜索引擎分组绘制 - 优化数据处理
            engines = df['search_engine'].unique()
            colors = plt.cm.Set1(np.linspace(0, 1, len(engines)))  # 预计算颜色
            
            for i, engine in enumerate(engines):
                engine_data = df[df['search_engine'] == engine].sort_values('date')
                ax.plot(engine_data['date'], engine_data['result_count'], 
                       marker='o', label=engine, linewidth=2, markersize=4,
                       color=colors[i], markerfacecolor=colors[i])
            
            # 设置图表 - 减少不必要的操作
            ax.set_title(f'搜索结果数量时间线 (最近{days}天)', fontsize=14, fontweight='bold')
            ax.set_xlabel('日期', fontsize=11)
            ax.set_ylabel('结果数量', fontsize=11)
            ax.legend(fontsize=9)
            ax.grid(True, alpha=0.3, linewidth=0.5)
            
            # 优化日期格式设置
            if days <= 7:
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            else:
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days//7)))
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # 保存图表 - 优化保存参数
            save_path = os.path.join(self.results_dir, f'search_results_timeline_{days}days.png')
            plt.savefig(save_path, dpi=Config.VISUALIZATION_CONFIG['dpi'], 
                       bbox_inches='tight', facecolor='white', optimize=True)
            plt.close()
            
            return save_path
            
        except Exception as e:
            print(f"生成时间线图表失败: {e}")
            plt.close('all')  # 确保清理
            return None
    
    def _plot_keyword_comparison_with_data_optimized(self, results_data: List[Dict], days: int) -> str:
        """优化版本：使用预获取的数据绘制关键词对比图"""
        if not results_data:
            return None
            
        try:
            # 转换为DataFrame
            df = pd.DataFrame(results_data)
            if df.empty:
                return None
            
            # 按关键词聚合数据 - 优化聚合操作
            keyword_stats = df.groupby('keyword', as_index=False)['result_count'].agg({
                'total': 'sum',
                'avg': 'mean',
                'count': 'count'
            }).rename(columns={'total': 'result_count'})
            
            keyword_stats = keyword_stats.sort_values('result_count', ascending=True).tail(10)
            
            if keyword_stats.empty:
                return None
            
            # 创建水平柱状图 - 优化图表大小
            fig_height = max(6, len(keyword_stats) * 0.5)
            fig, ax = plt.subplots(figsize=(10, fig_height), dpi=80)
            
            # 使用更高效的颜色映射
            colors = plt.cm.viridis(np.linspace(0, 1, len(keyword_stats)))
            bars = ax.barh(keyword_stats['keyword'], keyword_stats['result_count'], color=colors)
            
            # 优化标签添加
            max_value = keyword_stats['result_count'].max()
            for i, (bar, value) in enumerate(zip(bars, keyword_stats['result_count'])):
                # 只在有足够空间时添加标签
                if value > max_value * 0.1:
                    ax.text(value * 1.02, bar.get_y() + bar.get_height()/2, 
                           f'{int(value)}', ha='left', va='center', fontsize=9)
            
            ax.set_title(f'关键词搜索结果对比 (最近{days}天)', fontsize=14, fontweight='bold')
            ax.set_xlabel('搜索结果数量', fontsize=11)
            ax.set_ylabel('关键词', fontsize=11)
            ax.grid(True, axis='x', alpha=0.3, linewidth=0.5)
            
            plt.tight_layout()
            
            # 保存图表
            save_path = os.path.join(self.results_dir, f'keyword_comparison_{days}days.png')
            plt.savefig(save_path, dpi=Config.VISUALIZATION_CONFIG['dpi'], 
                       bbox_inches='tight', facecolor='white', optimize=True)
            plt.close()
            
            return save_path
            
        except Exception as e:
            print(f"生成关键词对比图表失败: {e}")
            plt.close('all')
            return None
    
    def _plot_engine_performance_with_data_optimized(self, task_data: List[Dict], days: int) -> str:
        """优化版本：使用预获取的数据绘制搜索引擎性能图"""
        if not task_data:
            return None
            
        try:
            # 转换为DataFrame并聚合数据
            df = pd.DataFrame(task_data)
            if df.empty:
                return None
            
            # 更高效的数据聚合
            engine_stats = df.groupby('search_engine').agg({
                'execution_time': ['mean', 'count'],
                'success': lambda x: (x == 'success').sum(),
                'error': lambda x: (x == 'error').sum()
            }).round(2)
            
            engine_stats.columns = ['avg_time', 'total_tasks', 'success_count', 'error_count']
            engine_stats = engine_stats.reset_index()
            engine_stats['success_rate'] = (engine_stats['success_count'] / 
                                           (engine_stats['success_count'] + engine_stats['error_count']) * 100).round(1)
            
            if engine_stats.empty:
                return None
            
            # 创建子图 - 优化布局
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10), dpi=80)
            
            # 使用一致的颜色方案
            colors = plt.cm.Set2(np.linspace(0, 1, len(engine_stats)))
            
            # 1. 平均执行时间
            bars1 = ax1.bar(engine_stats['search_engine'], engine_stats['avg_time'], color=colors)
            ax1.set_title('平均执行时间', fontsize=12, fontweight='bold')
            ax1.set_ylabel('时间 (秒)', fontsize=10)
            for bar, value in zip(bars1, engine_stats['avg_time']):
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                        f'{value:.2f}s', ha='center', va='bottom', fontsize=9)
            
            # 2. 任务数量
            bars2 = ax2.bar(engine_stats['search_engine'], engine_stats['total_tasks'], color=colors)
            ax2.set_title('总任务数量', fontsize=12, fontweight='bold')
            ax2.set_ylabel('任务数', fontsize=10)
            for bar, value in zip(bars2, engine_stats['total_tasks']):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f'{int(value)}', ha='center', va='bottom', fontsize=9)
            
            # 3. 成功率
            bars3 = ax3.bar(engine_stats['search_engine'], engine_stats['success_rate'], color=colors)
            ax3.set_title('成功率', fontsize=12, fontweight='bold')
            ax3.set_ylabel('成功率 (%)', fontsize=10)
            ax3.set_ylim(0, 100)
            for bar, value in zip(bars3, engine_stats['success_rate']):
                ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                        f'{value:.1f}%', ha='center', va='bottom', fontsize=9)
            
            # 4. 成功vs失败对比
            x = np.arange(len(engine_stats))
            width = 0.35
            ax4.bar(x - width/2, engine_stats['success_count'], width, label='成功', color='green', alpha=0.7)
            ax4.bar(x + width/2, engine_stats['error_count'], width, label='失败', color='red', alpha=0.7)
            ax4.set_title('成功失败对比', fontsize=12, fontweight='bold')
            ax4.set_ylabel('任务数', fontsize=10)
            ax4.set_xticks(x)
            ax4.set_xticklabels(engine_stats['search_engine'])
            ax4.legend()
            
            # 优化整体布局
            for ax in [ax1, ax2, ax3, ax4]:
                ax.grid(True, alpha=0.3, linewidth=0.5)
                ax.tick_params(axis='x', rotation=45, labelsize=9)
            
            plt.suptitle(f'搜索引擎性能分析 (最近{days}天)', fontsize=16, fontweight='bold')
            plt.tight_layout()
            
            # 保存图表
            save_path = os.path.join(self.results_dir, f'search_engine_performance_{days}days.png')
            plt.savefig(save_path, dpi=Config.VISUALIZATION_CONFIG['dpi'], 
                       bbox_inches='tight', facecolor='white', optimize=True)
            plt.close()
            
            return save_path
            
        except Exception as e:
            print(f"生成搜索引擎性能图表失败: {e}")
            plt.close('all')
            return None
    
    def _plot_heatmap_with_data_optimized(self, task_data: List[Dict], days: int) -> str:
        """优化版本：使用预获取的数据绘制活动热力图"""
        if not task_data:
            return None
            
        try:
            # 转换为DataFrame
            df = pd.DataFrame(task_data)
            if df.empty:
                return None
            
            df['created_at'] = pd.to_datetime(df['created_at'], cache=True)
            df['hour'] = df['created_at'].dt.hour
            df['day'] = df['created_at'].dt.day_name()
            
            # 创建热力图数据 - 优化数据透视
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            heatmap_data = df.pivot_table(
                values='task_id', 
                index='day', 
                columns='hour', 
                aggfunc='count', 
                fill_value=0
            ).reindex(day_order, fill_value=0)
            
            if heatmap_data.empty:
                return None
            
            # 创建热力图 - 优化参数
            fig, ax = plt.subplots(figsize=(16, 8), dpi=80)
            
            # 使用更高效的热力图绘制
            heatmap = sns.heatmap(
                heatmap_data, 
                annot=True, 
                fmt='d', 
                cmap='YlOrRd',
                ax=ax, 
                cbar_kws={'label': '活动次数'},
                annot_kws={'size': 8},
                linewidths=0.5
            )
            
            ax.set_title(f'每日活动热力图 (最近{days}天)', fontsize=16, fontweight='bold')
            ax.set_xlabel('小时', fontsize=12)
            ax.set_ylabel('星期', fontsize=12)
            
            plt.tight_layout()
            
            # 保存图表
            save_path = os.path.join(self.results_dir, f'daily_activity_heatmap_{days}days.png')
            plt.savefig(save_path, dpi=Config.VISUALIZATION_CONFIG['dpi'], 
                       bbox_inches='tight', facecolor='white', optimize=True)
            plt.close()
            
            return save_path
            
        except Exception as e:
            print(f"生成活动热力图失败: {e}")
            plt.close('all')
            return None
    
    def _generate_dashboard_with_data_optimized(self, results_data: List[Dict], task_data: List[Dict], days: int) -> str:
        """优化版本：使用预获取的数据生成交互式仪表板"""
        try:
            # 准备数据
            results_df = pd.DataFrame(results_data) if results_data else pd.DataFrame()
            task_df = pd.DataFrame(task_data) if task_data else pd.DataFrame()
            
            # 创建子图布局 - 优化性能
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('搜索结果趋势', '关键词分布', '引擎性能', '活动分布'),
                specs=[[{"secondary_y": False}, {"type": "pie"}],
                       [{"type": "bar"}, {"type": "scatter"}]],
                vertical_spacing=0.12,
                horizontal_spacing=0.1
            )
            
            # 1. 搜索结果趋势
            if not results_df.empty:
                results_df['date'] = pd.to_datetime(results_df['date'])
                trend_data = results_df.groupby(['date', 'search_engine'])['result_count'].sum().reset_index()
                
                for engine in trend_data['search_engine'].unique():
                    engine_data = trend_data[trend_data['search_engine'] == engine]
                    fig.add_trace(
                        go.Scatter(
                            x=engine_data['date'],
                            y=engine_data['result_count'],
                            mode='lines+markers',
                            name=engine,
                            line=dict(width=2),
                            marker=dict(size=4)
                        ),
                        row=1, col=1
                    )
            
            # 2. 关键词分布饼图
            if not results_df.empty:
                keyword_dist = results_df.groupby('keyword')['result_count'].sum().head(8)
                fig.add_trace(
                    go.Pie(
                        labels=keyword_dist.index,
                        values=keyword_dist.values,
                        name="关键词分布",
                        textinfo='label+percent',
                        textfont_size=10
                    ),
                    row=1, col=2
                )
            
            # 3. 引擎性能柱状图
            if not task_df.empty:
                engine_perf = task_df.groupby('search_engine').agg({
                    'execution_time': 'mean',
                    'task_id': 'count'
                }).round(2)
                
                fig.add_trace(
                    go.Bar(
                        x=engine_perf.index,
                        y=engine_perf['execution_time'],
                        name="平均执行时间",
                        text=engine_perf['execution_time'],
                        textposition='auto',
                        marker_color='lightblue'
                    ),
                    row=2, col=1
                )
            
            # 4. 时间分布散点图
            if not task_df.empty:
                task_df['created_at'] = pd.to_datetime(task_df['created_at'])
                task_df['hour'] = task_df['created_at'].dt.hour
                hour_dist = task_df['hour'].value_counts().sort_index()
                
                fig.add_trace(
                    go.Scatter(
                        x=hour_dist.index,
                        y=hour_dist.values,
                        mode='markers+lines',
                        name="每小时活动",
                        marker=dict(size=8, color='orange'),
                        line=dict(width=2)
                    ),
                    row=2, col=2
                )
            
            # 更新布局 - 优化性能参数
            fig.update_layout(
                height=800,
                showlegend=True,
                title=dict(
                    text=f'数据分析仪表板 (最近{days}天)',
                    x=0.5,
                    font=dict(size=20)
                ),
                font=dict(size=12),
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            
            # 保存为HTML
            html_path = os.path.join(self.results_dir, f'interactive_dashboard_{days}days.html')
            
            # 优化HTML输出
            fig.write_html(
                html_path,
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']
                },
                include_plotlyjs='cdn'  # 使用CDN减少文件大小
            )
            
            return html_path
            
        except Exception as e:
            print(f"生成交互式仪表板失败: {e}")
            return None
    
    def generate_all_visualizations(self, days: int = 7) -> Dict[str, str]:
        """生成所有可视化图表（保持向后兼容）"""
        return self.generate_all_visualizations_async(days)
    
    def cleanup(self):
        """清理资源"""
        self._clear_cache()
        self._executor.shutdown(wait=True)
        self._process_executor.shutdown(wait=True)
        
        # 清理matplotlib图形
        plt.close('all')
        
        # 打印性能统计
        if self._performance_stats['charts_generated'] > 0:
            avg_time = self._performance_stats['total_generation_time'] / self._performance_stats['charts_generated']
            print(f"性能统计 - 平均生成时间: {avg_time:.2f}秒/图表, 缓存命中率: {self._performance_stats['cache_hit_rate']:.1f}%")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        cache_stats = self.get_cache_stats()
        
        return {
            **self._performance_stats,
            **cache_stats,
            'avg_generation_time': (
                self._performance_stats['total_generation_time'] / 
                max(self._performance_stats['charts_generated'], 1)
            )
        }
    
    # 保持向后兼容的原始方法
    def _plot_timeline_with_data(self, results_data: List[Dict], days: int) -> str:
        """使用预获取的数据绘制时间线图（向后兼容）"""
        return self._plot_timeline_with_data_optimized(results_data, days)
    
    def _plot_keyword_comparison_with_data(self, results_data: List[Dict], days: int) -> str:
        """使用预获取的数据绘制关键词对比图（向后兼容）"""
        return self._plot_keyword_comparison_with_data_optimized(results_data, days)
    
    def _plot_engine_performance_with_data(self, task_data: List[Dict], days: int) -> str:
        """使用预获取的数据绘制搜索引擎性能图（向后兼容）"""
        return self._plot_engine_performance_with_data_optimized(task_data, days)
    
    def _plot_heatmap_with_data(self, task_data: List[Dict], days: int) -> str:
        """使用预获取的数据绘制热力图（向后兼容）"""
        return self._plot_heatmap_with_data_optimized(task_data, days)
    
    def _generate_dashboard_with_data(self, results_data: List[Dict], task_data: List[Dict], days: int) -> str:
        """使用预获取的数据生成交互式仪表板（向后兼容）"""
        return self._generate_dashboard_with_data_optimized(results_data, task_data, days)