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
        # 确保静态文件和模板目录存在
        self._ensure_directories()
        
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
    
    def _ensure_directories(self):
        """确保必要的目录和文件存在"""
        # 获取当前文件所在目录
        base_dir = os.path.dirname(__file__)
        
        # 创建static和templates目录
        static_dir = os.path.join(base_dir, 'static')
        templates_dir = os.path.join(base_dir, 'templates')
        
        os.makedirs(static_dir, exist_ok=True)
        os.makedirs(templates_dir, exist_ok=True)
        
        # 创建favicon.ico文件（如果不存在）
        favicon_path = os.path.join(static_dir, 'favicon.ico')
        if not os.path.exists(favicon_path):
            try:
                # 创建一个简单的16x16透明favicon
                import base64
                favicon_data = base64.b64decode(
                    b'AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAABILAAASCwAAAAAAAAAAAAD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=='
                )
                with open(favicon_path, 'wb') as f:
                    f.write(favicon_data)
            except Exception as e:
                # If favicon creation fails, just log the error
                print(f"Warning: Could not create favicon.ico: {e}")
    
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
        
        # 添加进度跟踪
        self._chart_progress = {}
        
        @self.app.route('/api/generate_charts')
        def generate_charts():
            """生成图表API（异步优化版本）"""
            days = request.args.get('days', 7, type=int)
            use_optimized = request.args.get('optimized', True, type=bool)
            task_id = f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 进度回调函数
            def progress_callback(step, total, message):
                self._chart_progress[task_id] = {
                    'step': step,
                    'total': total,
                    'message': message,
                    'progress': round(step / total * 100, 1),
                    'timestamp': datetime.now().isoformat()
                }
            
            # 异步执行图表生成
            def generate_charts_async():
                import time
                start_time = time.time()
                
                try:
                    # 使用优化的异步方法
                    generated_files = self.visualizer.generate_all_visualizations_async(
                        days=days, 
                        progress_callback=progress_callback
                    )
                    
                    generation_time = time.time() - start_time
                    
                    # 获取性能统计
                    try:
                        perf_stats = self.visualizer.get_performance_stats()
                    except AttributeError:
                        perf_stats = {}
                    
                    self._chart_progress[task_id].update({
                        'completed': True,
                        'success': True,
                        'files': generated_files,
                        'generation_time': round(generation_time, 2),
                        'performance_stats': perf_stats,
                        'message': f'已生成 {len(generated_files)} 个图表，用时 {generation_time:.2f}秒'
                    })
                    
                except Exception as e:
                    import traceback
                    error_details = {
                        'error': str(e),
                        'traceback': traceback.format_exc()
                    }
                    
                    self._chart_progress[task_id].update({
                        'completed': True,
                        'success': False,
                        'message': f'生成失败: {str(e)}',
                        'error_details': error_details
                    })
            
            # 启动后台线程
            import threading
            thread = threading.Thread(target=generate_charts_async)
            thread.daemon = True
            thread.start()
            
            return jsonify({
                'success': True,
                'task_id': task_id,
                'optimized': use_optimized,
                'message': '图表生成任务已启动（优化模式）' if use_optimized else '图表生成任务已启动'
            })
        
        @self.app.route('/api/generate_charts_progress/<task_id>')
        def get_chart_progress(task_id):
            """获取图表生成进度"""
            progress = self._chart_progress.get(task_id)
            if not progress:
                return jsonify({'success': False, 'message': '任务不存在'})
            
            return jsonify({'success': True, 'progress': progress})
        
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
        
        @self.app.route('/favicon.ico')
        def favicon():
            """网站图标"""
            try:
                favicon_path = os.path.join(self.app.static_folder, 'favicon.ico')
                if os.path.exists(favicon_path):
                    return send_file(favicon_path, mimetype='image/vnd.microsoft.icon')
                else:
                    # Return a 204 No Content response if favicon doesn't exist
                    return '', 204
            except Exception as e:
                # Log error and return empty response to prevent 500 error
                self.app.logger.warning(f"Error serving favicon: {e}")
                return '', 204
        
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
        
        # 任务管理模板
        tasks_template = '''{% extends "base.html" %}

{% block title %}任务管理 - 关键词爬虫工具{% endblock %}

{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
    <h1 class="h2">任务管理</h1>
</div>

<div class="table-responsive">
    <table class="table table-striped">
        <thead>
            <tr>
                <th>任务ID</th>
                <th>状态</th>
                <th>下次执行</th>
                <th>上次执行</th>
                <th>操作</th>
            </tr>
        </thead>
        <tbody>
            {% for job in jobs %}
            <tr>
                <td>{{ job.id }}</td>
                <td>
                    {% if job.paused %}
                        <span class="badge bg-warning">已暂停</span>
                    {% else %}
                        <span class="badge bg-success">运行中</span>
                    {% endif %}
                </td>
                <td>{{ job.next_run_time or '未安排' }}</td>
                <td>{{ job.last_run_time or '从未执行' }}</td>
                <td>
                    <div class="btn-group" role="group">
                        <button class="btn btn-sm btn-primary" onclick="runTask('{{ job.id }}')">立即执行</button>
                        {% if job.paused %}
                            <button class="btn btn-sm btn-success" onclick="resumeTask('{{ job.id }}')">恢复</button>
                        {% else %}
                            <button class="btn btn-sm btn-warning" onclick="pauseTask('{{ job.id }}')">暂停</button>
                        {% endif %}
                    </div>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}

{% block scripts %}
<script>
function runTask(taskId) {
    if (confirm('确定要立即执行任务 ' + taskId + ' 吗？')) {
        axios.post('/api/tasks/' + taskId + '/run')
        .then(response => {
            if (response.data.success) {
                alert(response.data.message);
                location.reload();
            } else {
                alert('操作失败: ' + response.data.message);
            }
        })
        .catch(error => {
            alert('请求失败: ' + error.message);
        });
    }
}

function pauseTask(taskId) {
    if (confirm('确定要暂停任务 ' + taskId + ' 吗？')) {
        axios.post('/api/tasks/' + taskId + '/pause')
        .then(response => {
            if (response.data.success) {
                alert(response.data.message);
                location.reload();
            } else {
                alert('操作失败: ' + response.data.message);
            }
        })
        .catch(error => {
            alert('请求失败: ' + error.message);
        });
    }
}

function resumeTask(taskId) {
    if (confirm('确定要恢复任务 ' + taskId + ' 吗？')) {
        axios.post('/api/tasks/' + taskId + '/resume')
        .then(response => {
            if (response.data.success) {
                alert(response.data.message);
                location.reload();
            } else {
                alert('操作失败: ' + response.data.message);
            }
        })
        .catch(error => {
            alert('请求失败: ' + error.message);
        });
    }
}
</script>
{% endblock %}'''

        # 关键词管理模板
        keywords_template = '''{% extends "base.html" %}

{% block title %}关键词管理 - 关键词爬虫工具{% endblock %}

{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
    <h1 class="h2">关键词管理</h1>
    <div class="btn-toolbar mb-2 mb-md-0">
        <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addKeywordModal">
            <i class="bi bi-plus"></i> 添加关键词
        </button>
    </div>
</div>

<div class="table-responsive">
    <table class="table table-striped">
        <thead>
            <tr>
                <th>关键词</th>
                <th>创建时间</th>
                <th>状态</th>
                <th>操作</th>
            </tr>
        </thead>
        <tbody>
            {% for keyword in keywords %}
            <tr>
                <td>{{ keyword.keyword }}</td>
                <td>{{ keyword.created_at }}</td>
                <td>
                    {% if keyword.is_active %}
                        <span class="badge bg-success">活跃</span>
                    {% else %}
                        <span class="badge bg-secondary">已停用</span>
                    {% endif %}
                </td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="deleteKeyword({{ keyword.id }})">删除</button>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<!-- 添加关键词模态框 -->
<div class="modal fade" id="addKeywordModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">添加关键词</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <form id="addKeywordForm">
                    <div class="mb-3">
                        <label for="keyword" class="form-label">关键词</label>
                        <input type="text" class="form-control" id="keyword" name="keyword" required>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                <button type="button" class="btn btn-primary" onclick="addKeyword()">添加</button>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
function addKeyword() {
    const keyword = document.getElementById('keyword').value.trim();
    if (!keyword) {
        alert('请输入关键词');
        return;
    }
    
    axios.post('/api/keywords', { keyword: keyword })
    .then(response => {
        if (response.data.success) {
            alert(response.data.message);
            location.reload();
        } else {
            alert('添加失败: ' + response.data.message);
        }
    })
    .catch(error => {
        alert('请求失败: ' + error.message);
    });
}
</script>
{% endblock %}'''

        # 统计页面模板
        statistics_template = '''{% extends "base.html" %}

{% block title %}数据统计 - 关键词爬虫工具{% endblock %}

{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
    <h1 class="h2">数据统计</h1>
    <div class="btn-toolbar mb-2 mb-md-0">
        <select class="form-select" onchange="changeDays(this.value)">
            <option value="7" {% if days == 7 %}selected{% endif %}>最近7天</option>
            <option value="30" {% if days == 30 %}selected{% endif %}>最近30天</option>
            <option value="90" {% if days == 90 %}selected{% endif %}>最近90天</option>
        </select>
    </div>
</div>

<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>任务统计</h5>
            </div>
            <div class="card-body">
                <p>总任务数: {{ task_stats.total }}</p>
                <p>成功任务: {{ task_stats.success }}</p>
                <p>失败任务: {{ task_stats.failed }}</p>
                <p>成功率: {{ task_stats.success_rate }}%</p>
            </div>
        </div>
    </div>
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>搜索结果统计</h5>
            </div>
            <div class="card-body">
                <p>总搜索结果: {{ results_stats.total }}</p>
                <p>平均每天: {{ results_stats.daily_average }}</p>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
function changeDays(days) {
    window.location.href = '/statistics?days=' + days;
}
</script>
{% endblock %}'''

        # 可视化页面模板（优化版本）
        visualizations_template = '''{% extends "base.html" %}

{% block title %}数据可视化 - 关键词爬虫工具{% endblock %}

{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
    <h1 class="h2">数据可视化</h1>
    <div class="btn-toolbar mb-2 mb-md-0">
        <div class="input-group" style="width: 200px;">
            <select class="form-select" id="daysSelect">
                <option value="7" {% if days == 7 %}selected{% endif %}>最近7天</option>
                <option value="30" {% if days == 30 %}selected{% endif %}>最近30天</option>
                <option value="90" {% if days == 90 %}selected{% endif %}>最近90天</option>
            </select>
        </div>
        <button type="button" class="btn btn-primary ms-2" id="generateChartsBtn" onclick="generateCharts()">
            <i class="bi bi-graph-up"></i> 生成图表
        </button>
    </div>
</div>

<!-- 进度条 -->
<div id="progressContainer" class="mb-4" style="display: none;">
    <div class="card">
        <div class="card-body">
            <h6 class="card-title">正在生成图表...</h6>
            <div class="progress mb-2">
                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                     id="progressBar" role="progressbar" style="width: 0%"></div>
            </div>
            <p class="text-muted" id="progressMessage">准备中...</p>
        </div>
    </div>
</div>

<!-- 错误信息 -->
<div id="errorContainer" class="mb-4" style="display: none;">
    <div class="alert alert-danger" role="alert">
        <i class="bi bi-exclamation-triangle"></i>
        <span id="errorMessage"></span>
    </div>
</div>

<!-- 图表容器 -->
<div id="chartsContainer">
    <div class="row" id="chartsList">
        <div class="col-12 text-center text-muted py-5">
            <i class="bi bi-bar-chart" style="font-size: 3rem;"></i>
            <p class="mt-3">选择时间范围并点击"生成图表"按钮来创建可视化图表</p>
            <p class="small">支持时间线图、关键词对比、引擎性能、活动热力图等多种图表类型</p>
        </div>
    </div>
</div>

<!-- 图表预览模态框 -->
<div class="modal fade" id="chartModal" tabindex="-1">
    <div class="modal-dialog modal-xl">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="chartModalTitle">图表预览</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body text-center" id="chartModalBody">
                <!-- 图表内容将在这里显示 -->
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                <button type="button" class="btn btn-primary" id="downloadChartBtn">下载图表</button>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
let currentTaskId = null;
let progressInterval = null;

const chartTypeNames = {
    'timeline': '搜索结果时间线',
    'keyword_comparison': '关键词对比图',
    'engine_performance': '搜索引擎性能',
    'activity_heatmap': '每日活动热力图',
    'interactive_dashboard': '交互式仪表板'
};

function generateCharts() {
    const days = document.getElementById('daysSelect').value;
    const generateBtn = document.getElementById('generateChartsBtn');
    const progressContainer = document.getElementById('progressContainer');
    const errorContainer = document.getElementById('errorContainer');
    const chartsList = document.getElementById('chartsList');
    
    // 重置界面
    generateBtn.disabled = true;
    progressContainer.style.display = 'block';
    errorContainer.style.display = 'none';
    chartsList.innerHTML = '<div class="col-12 text-center text-muted py-3"><i class="bi bi-hourglass-split"></i> 正在生成图表...</div>';
    
    // 启动图表生成
    axios.get(`/api/generate_charts?days=${days}`)
    .then(response => {
        if (response.data.success) {
            currentTaskId = response.data.task_id;
            startProgressPolling();
        } else {
            showError(response.data.message);
        }
    })
    .catch(error => {
        showError('请求失败: ' + error.message);
    });
}

function startProgressPolling() {
    if (!currentTaskId) return;
    
    progressInterval = setInterval(() => {
        axios.get(`/api/generate_charts_progress/${currentTaskId}`)
        .then(response => {
            if (response.data.success) {
                const progress = response.data.progress;
                updateProgress(progress);
                
                if (progress.completed) {
                    clearInterval(progressInterval);
                    handleCompletion(progress);
                }
            }
        })
        .catch(error => {
            clearInterval(progressInterval);
            showError('获取进度失败: ' + error.message);
        });
    }, 1000); // 每秒更新一次
}

function updateProgress(progress) {
    const progressBar = document.getElementById('progressBar');
    const progressMessage = document.getElementById('progressMessage');
    
    progressBar.style.width = progress.progress + '%';
    progressBar.textContent = progress.progress + '%';
    progressMessage.textContent = progress.message;
}

function handleCompletion(progress) {
    const generateBtn = document.getElementById('generateChartsBtn');
    const progressContainer = document.getElementById('progressContainer');
    
    generateBtn.disabled = false;
    progressContainer.style.display = 'none';
    
    if (progress.success) {
        displayCharts(progress.files);
    } else {
        showError(progress.message);
    }
}

function displayCharts(files) {
    const chartsList = document.getElementById('chartsList');
    
    if (!files || Object.keys(files).length === 0) {
        chartsList.innerHTML = '<div class="col-12 text-center text-muted py-3">没有生成任何图表，可能是数据不足</div>';
        return;
    }
    
    let chartsHtml = '';
    
    for (const [type, filePath] of Object.entries(files)) {
        const chartName = chartTypeNames[type] || type;
        const fileName = filePath.split('/').pop();
        const isInteractive = type === 'interactive_dashboard';
        
        chartsHtml += `
            <div class="col-md-6 col-lg-4 mb-4">
                <div class="card h-100">
                    <div class="card-body text-center">
                        <i class="bi bi-${getChartIcon(type)}" style="font-size: 2rem; color: #007bff;"></i>
                        <h6 class="card-title mt-2">${chartName}</h6>
                        <p class="card-text text-muted small">文件: ${fileName}</p>
                        <div class="btn-group" role="group">
                            ${isInteractive ? 
                                `<button class="btn btn-sm btn-outline-primary" onclick="openInteractiveChart('${filePath}')">
                                    <i class="bi bi-eye"></i> 查看
                                </button>` :
                                `<button class="btn btn-sm btn-outline-primary" onclick="previewChart('${chartName}', '${filePath}')">
                                    <i class="bi bi-eye"></i> 预览
                                </button>`
                            }
                            <a href="/download/${fileName}" class="btn btn-sm btn-outline-success">
                                <i class="bi bi-download"></i> 下载
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    chartsList.innerHTML = chartsHtml;
}

function getChartIcon(type) {
    const icons = {
        'timeline': 'graph-up',
        'keyword_comparison': 'bar-chart-fill',
        'engine_performance': 'speedometer2',
        'activity_heatmap': 'calendar-heat',
        'interactive_dashboard': 'grid-3x3-gap'
    };
    return icons[type] || 'bar-chart';
}

function previewChart(chartName, filePath) {
    const modal = new bootstrap.Modal(document.getElementById('chartModal'));
    const modalTitle = document.getElementById('chartModalTitle');
    const modalBody = document.getElementById('chartModalBody');
    const downloadBtn = document.getElementById('downloadChartBtn');
    
    modalTitle.textContent = chartName;
    modalBody.innerHTML = `<img src="/download/${filePath.split('/').pop()}" class="img-fluid" alt="${chartName}">`;
    downloadBtn.onclick = () => window.open(`/download/${filePath.split('/').pop()}`, '_blank');
    
    modal.show();
}

function openInteractiveChart(filePath) {
    window.open(`/download/${filePath.split('/').pop()}`, '_blank');
}

function showError(message) {
    const generateBtn = document.getElementById('generateChartsBtn');
    const progressContainer = document.getElementById('progressContainer');
    const errorContainer = document.getElementById('errorContainer');
    const errorMessage = document.getElementById('errorMessage');
    const chartsList = document.getElementById('chartsList');
    
    generateBtn.disabled = false;
    progressContainer.style.display = 'none';
    errorContainer.style.display = 'block';
    errorMessage.textContent = message;
    
    chartsList.innerHTML = '<div class="col-12 text-center text-muted py-3"><i class="bi bi-x-circle"></i> 图表生成失败</div>';
}

// 页面加载时清理之前的进度跟踪
window.addEventListener('beforeunload', () => {
    if (progressInterval) {
        clearInterval(progressInterval);
    }
});
</script>
{% endblock %}'''

        # 配置页面模板
        config_template = '''{% extends "base.html" %}

{% block title %}配置 - 关键词爬虫工具{% endblock %}

{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
    <h1 class="h2">系统配置</h1>
</div>

<div class="row">
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h5>搜索引擎</h5>
            </div>
            <div class="card-body">
                <ul class="list-group list-group-flush">
                    {% for engine in config.search_engines %}
                    <li class="list-group-item">{{ engine }}</li>
                    {% endfor %}
                </ul>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h5>默认关键词</h5>
            </div>
            <div class="card-body">
                <ul class="list-group list-group-flush">
                    {% for keyword in config.default_keywords %}
                    <li class="list-group-item">{{ keyword }}</li>
                    {% endfor %}
                </ul>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h5>调度器配置</h5>
            </div>
            <div class="card-body">
                {% for key, value in config.scheduler_config.items() %}
                <p><strong>{{ key }}:</strong> {{ value }}</p>
                {% endfor %}
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

        # 404错误页面模板
        error_404_template = '''{% extends "base.html" %}

{% block title %}页面未找到 - 关键词爬虫工具{% endblock %}

{% block content %}
<div class="text-center">
    <h1 class="display-1">404</h1>
    <p class="fs-3"><span class="text-danger">糟糕!</span> 页面未找到。</p>
    <p class="lead">您要查找的页面不存在。</p>
    <a href="{{ url_for('index') }}" class="btn btn-primary">返回首页</a>
</div>
{% endblock %}'''

        # 500错误页面模板
        error_500_template = '''{% extends "base.html" %}

{% block title %}服务器错误 - 关键词爬虫工具{% endblock %}

{% block content %}
<div class="text-center">
    <h1 class="display-1">500</h1>
    <p class="fs-3"><span class="text-danger">糟糕!</span> 服务器内部错误。</p>
    <p class="lead">服务器遇到了一个意外的错误。</p>
    <a href="{{ url_for('index') }}" class="btn btn-primary">返回首页</a>
</div>
{% endblock %}'''

        # 保存所有模板文件
        templates = {
            'base.html': base_template,
            'index.html': index_template,
            'tasks.html': tasks_template,
            'keywords.html': keywords_template,
            'statistics.html': statistics_template,
            'visualizations.html': visualizations_template,
            'config.html': config_template,
            '404.html': error_404_template,
            '500.html': error_500_template
        }
        
        for filename, content in templates.items():
            with open(os.path.join(templates_dir, filename), 'w', encoding='utf-8') as f:
                f.write(content)
    
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