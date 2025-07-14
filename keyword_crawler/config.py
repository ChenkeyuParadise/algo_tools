import os
from typing import List, Dict

# 可选导入，避免依赖问题
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

class Config:
    """爬虫配置类"""
    
    # 基础配置
    DEBUG = True
    DATA_DIR = "data"
    LOGS_DIR = "logs"
    RESULTS_DIR = "results"
    
    # 数据库配置
    DATABASE_PATH = os.path.join(DATA_DIR, "crawler_data.db")
    
    # 爬虫配置
    REQUEST_TIMEOUT = 30
    REQUEST_DELAY = 2  # 请求间隔秒数
    MAX_RETRIES = 3
    
    # 默认关键词
    DEFAULT_KEYWORDS = [
        "人工智能",
        "机器学习", 
        "深度学习",
        "Python编程",
        "数据科学",
        "区块链",
        "云计算",
        "物联网"
    ]
    
    # 搜索引擎配置
    SEARCH_ENGINES = {
        "baidu": {
            "name": "百度",
            "search_url": "https://www.baidu.com/s?wd={keyword}&pn={page}",
            "result_selector": ".result",
            "title_selector": "h3 a",
            "link_selector": "h3 a",
            "snippet_selector": ".c-abstract",
            "enabled": True
        },
        "bing": {
            "name": "必应",
            "search_url": "https://cn.bing.com/search?q={keyword}&first={page}",
            "result_selector": ".b_algo",
            "title_selector": "h2 a",
            "link_selector": "h2 a",
            "snippet_selector": ".b_caption p",
            "enabled": True
        },
        "sogou": {
            "name": "搜狗",
            "search_url": "https://www.sogou.com/web?query={keyword}&page={page}",
            "result_selector": ".results .rb",
            "title_selector": "h3 a",
            "link_selector": "h3 a", 
            "snippet_selector": ".ft",
            "enabled": True
        }
    }
    
    # 定时任务配置
    SCHEDULER_CONFIG = {
        "default_interval": 3600,  # 默认1小时执行一次
        "max_workers": 5,
        "timezone": "Asia/Shanghai"
    }
    
    # Web界面配置
    WEB_CONFIG = {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": DEBUG
    }
    
    # 可视化配置
    VISUALIZATION_CONFIG = {
        'style': 'whitegrid',
        'color_palette': 'Set2',
        'figure_size': (12, 8),
        'dpi': 100,
        
        # 性能优化配置
        'enable_cache': True,
        'cache_timeout': 300,  # 5分钟缓存
        'max_workers': 6,  # 最大线程数
        'enable_parallel': True,  # 启用并行生成
        'optimize_plots': True,  # 启用图表优化
        
        # matplotlib性能优化
        'matplotlib_backend': 'Agg',  # 非交互式后端
        'max_open_warning': 50,
        'path_chunksize': 10000,
        
        # 图表质量设置
        'high_quality_mode': False,  # 高质量模式（较慢）
        'enable_antialiasing': True,
        'compress_images': True,
        
        # 仪表板配置
        'dashboard_use_cdn': True,  # 使用CDN减少文件大小
        'dashboard_minimal_mode': True,  # 最小化模式
    }
    
    @classmethod
    def ensure_directories(cls):
        """确保必要的目录存在"""
        for directory in [cls.DATA_DIR, cls.LOGS_DIR, cls.RESULTS_DIR]:
            os.makedirs(directory, exist_ok=True)
    
    @classmethod
    def get_enabled_search_engines(cls) -> Dict:
        """获取启用的搜索引擎"""
        return {k: v for k, v in cls.SEARCH_ENGINES.items() if v.get("enabled", False)}