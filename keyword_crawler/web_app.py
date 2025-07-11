from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import json
import os
from datetime import datetime
from typing import Dict, Any

from .config import Config
from .database import DatabaseManager
from .crawler import SearchCrawler
from .scheduler import TaskScheduler
from .visualizer import DataVisualizer

class WebApp:
    """Web应用类"""
    
    def __init__(self):
        self.app = Flask(__name__, template_folder='templates', static_folder='static')
        self.app.secret_key = 'keyword_crawler_secret_key'
        
        # 初始化组件
        self.db_manager = DatabaseManager()
        self.crawler = SearchCrawler(self.db_manager)
        self.scheduler = TaskScheduler(self.db_manager)
        self.visualizer = DataVisualizer(self.db_manager)
        
        # 注册路由
        self._register_routes()
        
        # 启动调度器
        self.scheduler.setup_default_jobs()
        self.scheduler.start()
    
    def _register_routes(self):
        """注册Flask路由"""
        
        @self.app.route('/')
        def index():
            """主页"""
            # 获取概要统计
            summary = self.visualizer.generate_summary_report(days=7)
            return render_template('index.html', summary=summary)
        
        @self.app.route('/keywords')
        def keywords():
            """关键词管理页面"""
            active_keywords = self.db_manager.get_active_keywords()
            return render_template('keywords.html', keywords=active_keywords)
        
        @self.app.route('/api/keywords', methods=['POST'])
        def add_keyword():
            """添加关键词API"""
            data = request.get_json()
            keyword = data.get('keyword', '').strip()
            
            if not keyword:
                return jsonify({'success': False, 'message': '关键词不能为空'})
            
            success = self.db_manager.add_keyword(keyword)
            if success:
                return jsonify({'success': True, 'message': '关键词添加成功'})
            else:
                return jsonify({'success': False, 'message': '关键词已存在或添加失败'})
        
        @self.app.route('/tasks')
        def tasks():
            """任务管理页面"""
            jobs_info = self.scheduler.get_jobs_info()
            return render_template('tasks.html', jobs=jobs_info)
        
        @self.app.route('/api/tasks/<task_id>/run', methods=['POST'])
        def run_task(task_id):
            """立即执行任务API"""
            try:
                self.scheduler.run_once(task_id)
                return jsonify({'success': True, 'message': f'任务 {task_id} 已开始执行'})
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)})
        
        @self.app.route('/api/tasks/<task_id>/pause', methods=['POST'])
        def pause_task(task_id):
            """暂停任务API"""
            try:
                self.scheduler.pause_job(task_id)
                return jsonify({'success': True, 'message': f'任务 {task_id} 已暂停'})
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)})
        
        @self.app.route('/api/tasks/<task_id>/resume', methods=['POST'])
        def resume_task(task_id):
            """恢复任务API"""
            try:
                self.scheduler.resume_job(task_id)
                return jsonify({'success': True, 'message': f'任务 {task_id} 已恢复'})
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)})
        
        @self.app.route('/statistics')
        def statistics():
            """统计页面"""
            days = request.args.get('days', 7, type=int)
            
            # 获取统计数据
            task_stats = self.db_manager.get_task_statistics(days=days)
            results_stats = self.db_manager.get_search_results_count(days=days)
            summary = self.visualizer.generate_summary_report(days=days)
            
            return render_template('statistics.html', 
                                 task_stats=task_stats,
                                 results_stats=results_stats,
                                 summary=summary,
                                 days=days)
        
        @self.app.route('/visualizations')
        def visualizations():
            """可视化页面"""
            days = request.args.get('days', 7, type=int)
            return render_template('visualizations.html', days=days)
        
        @self.app.route('/api/generate_charts')
        def generate_charts():
            """生成图表API"""
            days = request.args.get('days', 7, type=int)
            
            try:
                generated_files = self.visualizer.generate_all_visualizations(days=days)
                return jsonify({
                    'success': True,
                    'files': generated_files,
                    'message': f'已生成 {len(generated_files)} 个图表'
                })
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)})
        
        @self.app.route('/api/search_now', methods=['POST'])
        def search_now():
            """立即执行搜索API"""
            data = request.get_json()
            keywords = data.get('keywords', [])
            pages = data.get('pages', 1)
            
            if not keywords:
                keywords = self.db_manager.get_active_keywords()
            
            try:
                # 在后台执行搜索
                results = self.crawler.search_all_engines(keywords, pages)
                
                total_results = sum(
                    len(engine_results) 
                    for keyword_results in results.values()
                    for engine_results in keyword_results.values()
                )
                
                return jsonify({
                    'success': True,
                    'message': f'搜索完成，共获取 {total_results} 个结果',
                    'total_results': total_results
                })
                
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)})
        
        @self.app.route('/api/summary')
        def api_summary():
            """获取概要统计API"""
            days = request.args.get('days', 7, type=int)
            summary = self.visualizer.generate_summary_report(days=days)
            return jsonify(summary)
        
        @self.app.route('/download/<path:filename>')
        def download_file(filename):
            """下载文件"""
            file_path = os.path.join(Config.RESULTS_DIR, filename)
            if os.path.exists(file_path):
                return send_file(file_path, as_attachment=True)
            else:
                return "文件不存在", 404
        
        @self.app.route('/config')
        def config():
            """配置页面"""
            config_data = {
                'search_engines': Config.SEARCH_ENGINES,
                'default_keywords': Config.DEFAULT_KEYWORDS,
                'scheduler_config': Config.SCHEDULER_CONFIG
            }
            return render_template('config.html', config=config_data)
        
        @self.app.errorhandler(404)
        def not_found_error(error):
            return render_template('404.html'), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return render_template('500.html'), 500
    
    def create_templates(self):
        """创建HTML模板文件"""
        templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
        os.makedirs(templates_dir, exist_ok=True)
        
        # 基础布局模板
        base_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}关键词爬虫工具{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        .sidebar { min-height: 100vh; }
        .main-content { margin-left: 0; }
        @media (min-width: 768px) {
            .main-content { margin-left: 250px; }
        }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <!-- 侧边栏 -->
            <nav class="col-md-3 col-lg-2 d-md-block bg-light sidebar collapse">
                <div class="position-sticky pt-3">
                    <h5 class="px-3 mb-3">关键词爬虫</h5>
                    <ul class="nav flex-column">
                        <li class="nav-item">
                            <a class="nav-link" href="{{ url_for('index') }}">
                                <i class="bi bi-house"></i> 首页
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="{{ url_for('keywords') }}">
                                <i class="bi bi-tags"></i> 关键词管理
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="{{ url_for('tasks') }}">
                                <i class="bi bi-clock"></i> 任务管理
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="{{ url_for('statistics') }}">
                                <i class="bi bi-graph-up"></i> 数据统计
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="{{ url_for('visualizations') }}">
                                <i class="bi bi-bar-chart"></i> 数据可视化
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="{{ url_for('config') }}">
                                <i class="bi bi-gear"></i> 配置
                            </a>
                        </li>
                    </ul>
                </div>
            </nav>

            <!-- 主内容区 -->
            <main class="col-md-9 ms-sm-auto col-lg-10 px-md-4 main-content">
                <div class="pt-3">
                    {% block content %}{% endblock %}
                </div>
            </main>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>'''
        
        # 主页模板
        index_template = '''{% extends "base.html" %}

{% block title %}首页 - 关键词爬虫工具{% endblock %}

{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
    <h1 class="h2">系统概览</h1>
    <div class="btn-toolbar mb-2 mb-md-0">
        <button type="button" class="btn btn-primary" onclick="searchNow()">
            <i class="bi bi-search"></i> 立即搜索
        </button>
    </div>
</div>

<div class="row">
    <div class="col-md-3">
        <div class="card text-white bg-primary mb-3">
            <div class="card-body">
                <h5 class="card-title">总搜索结果</h5>
                <h2>{{ summary.total_search_results }}</h2>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-white bg-success mb-3">
            <div class="card-body">
                <h5 class="card-title">总任务数</h5>
                <h2>{{ summary.total_tasks }}</h2>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-white bg-info mb-3">
            <div class="card-body">
                <h5 class="card-title">成功率</h5>
                <h2>{{ summary.success_rate }}%</h2>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-white bg-warning mb-3">
            <div class="card-body">
                <h5 class="card-title">活跃关键词</h5>
                <h2>{{ summary.active_keywords }}</h2>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>热门关键词</h5>
            </div>
            <div class="card-body">
                <ul class="list-group list-group-flush">
                    {% for keyword, count in summary.top_keywords.items() %}
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        {{ keyword }}
                        <span class="badge bg-primary rounded-pill">{{ count }}</span>
                    </li>
                    {% endfor %}
                </ul>
            </div>
        </div>
    </div>
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>搜索引擎性能</h5>
            </div>
            <div class="card-body">
                {% for engine, stats in summary.engine_performance.items() %}
                <div class="mb-3">
                    <div class="d-flex justify-content-between">
                        <span>{{ engine }}</span>
                        <span>{{ stats.success_rate }}%</span>
                    </div>
                    <div class="progress">
                        <div class="progress-bar" role="progressbar" style="width: {{ stats.success_rate }}%"></div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
function searchNow() {
    if (confirm('确定要立即执行搜索吗？')) {
        axios.post('/api/search_now', {
            keywords: [],
            pages: 1
        }).then(response => {
            if (response.data.success) {
                alert(response.data.message);
                location.reload();
            } else {
                alert('搜索失败: ' + response.data.message);
            }
        }).catch(error => {
            alert('请求失败: ' + error.message);
        });
    }
}
</script>
{% endblock %}'''
        
        # 保存模板文件
        with open(os.path.join(templates_dir, 'base.html'), 'w', encoding='utf-8') as f:
            f.write(base_template)
        
        with open(os.path.join(templates_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(index_template)
    
    def run(self, host=None, port=None, debug=None):
        """运行Web应用"""
        # 创建模板文件
        self.create_templates()
        
        # 使用配置或默认值
        host = host or Config.WEB_CONFIG['host']
        port = port or Config.WEB_CONFIG['port']
        debug = debug if debug is not None else Config.WEB_CONFIG['debug']
        
        print(f"启动Web应用: http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug)
    
    def stop(self):
        """停止应用"""
        if self.scheduler:
            self.scheduler.stop()

def create_app():
    """创建Flask应用实例"""
    web_app = WebApp()
    return web_app.app