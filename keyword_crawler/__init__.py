"""
关键词爬虫工具包

一个完整的定时爬取互联网数据关键词的工具，包含：
- 多搜索引擎爬虫
- 定时任务调度
- 数据存储管理
- 数据可视化
- Web管理界面
"""

__version__ = "1.0.0"
__author__ = "AI Assistant"

from .config import Config
from .database import DatabaseManager
from .crawler import SearchCrawler
from .scheduler import TaskScheduler
from .visualizer import DataVisualizer

__all__ = [
    'Config',
    'DatabaseManager', 
    'SearchCrawler',
    'TaskScheduler',
    'DataVisualizer'
]