import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
import os

from .config import Config
from .database import DatabaseManager

# 设置matplotlib中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class DataVisualizer:
    """数据可视化类"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager or DatabaseManager()
        self.results_dir = Config.RESULTS_DIR
        Config.ensure_directories()
        
        # 设置seaborn样式
        sns.set_style(Config.VISUALIZATION_CONFIG['style'])
        sns.set_palette(Config.VISUALIZATION_CONFIG['color_palette'])
    
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
    
    def generate_all_visualizations(self, days: int = 7) -> Dict[str, str]:
        """生成所有可视化图表"""
        generated_files = {}
        
        # 生成各种图表
        timeline_path = self.plot_search_results_timeline(days)
        if timeline_path:
            generated_files['timeline'] = timeline_path
        
        comparison_path = self.plot_keyword_comparison(days=days)
        if comparison_path:
            generated_files['keyword_comparison'] = comparison_path
        
        performance_path = self.plot_search_engine_performance(days)
        if performance_path:
            generated_files['engine_performance'] = performance_path
        
        heatmap_path = self.plot_daily_activity_heatmap(days)
        if heatmap_path:
            generated_files['activity_heatmap'] = heatmap_path
        
        dashboard_path = self.generate_interactive_dashboard(days)
        if dashboard_path:
            generated_files['interactive_dashboard'] = dashboard_path
        
        return generated_files