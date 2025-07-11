import time
import schedule
import threading
import logging
from datetime import datetime, timedelta
from typing import List, Callable, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from .config import Config
from .database import DatabaseManager
from .crawler import SearchCrawler

class TaskScheduler:
    """任务调度器类"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager or DatabaseManager()
        self.crawler = SearchCrawler(self.db_manager)
        self.scheduler = BackgroundScheduler(timezone=Config.SCHEDULER_CONFIG['timezone'])
        self.logger = self._setup_logger()
        self.is_running = False
        
        # 存储已注册的任务
        self.registered_jobs = {}
    
    def _setup_logger(self):
        """设置日志记录器"""
        logger = logging.getLogger('TaskScheduler')
        logger.setLevel(logging.INFO)
        
        # 创建文件处理器
        Config.ensure_directories()
        file_handler = logging.FileHandler(f'{Config.LOGS_DIR}/scheduler.log', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 创建格式器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def start(self):
        """启动调度器"""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            self.logger.info("任务调度器已启动")
        else:
            self.logger.warning("任务调度器已经在运行中")
    
    def stop(self):
        """停止调度器"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            self.logger.info("任务调度器已停止")
        else:
            self.logger.warning("任务调度器未在运行")
    
    def add_interval_job(self, job_id: str, func: Callable, interval_seconds: int, 
                        *args, **kwargs) -> bool:
        """添加间隔执行的任务"""
        try:
            if job_id in self.registered_jobs:
                self.logger.warning(f"任务 {job_id} 已存在，将被替换")
                self.remove_job(job_id)
            
            job = self.scheduler.add_job(
                func=func,
                trigger=IntervalTrigger(seconds=interval_seconds),
                id=job_id,
                args=args,
                kwargs=kwargs,
                replace_existing=True
            )
            
            self.registered_jobs[job_id] = {
                'job': job,
                'type': 'interval',
                'interval': interval_seconds,
                'func': func.__name__,
                'created_at': datetime.now()
            }
            
            self.logger.info(f"添加间隔任务: {job_id}, 间隔: {interval_seconds}秒")
            return True
            
        except Exception as e:
            self.logger.error(f"添加间隔任务失败: {e}")
            return False
    
    def add_cron_job(self, job_id: str, func: Callable, cron_expression: str,
                     *args, **kwargs) -> bool:
        """添加定时执行的任务（cron表达式）"""
        try:
            if job_id in self.registered_jobs:
                self.logger.warning(f"任务 {job_id} 已存在，将被替换")
                self.remove_job(job_id)
            
            # 解析cron表达式
            cron_parts = cron_expression.split()
            if len(cron_parts) != 5:
                raise ValueError("Cron表达式格式错误，应为: 分 时 日 月 周")
            
            minute, hour, day, month, day_of_week = cron_parts
            
            job = self.scheduler.add_job(
                func=func,
                trigger=CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week
                ),
                id=job_id,
                args=args,
                kwargs=kwargs,
                replace_existing=True
            )
            
            self.registered_jobs[job_id] = {
                'job': job,
                'type': 'cron',
                'cron': cron_expression,
                'func': func.__name__,
                'created_at': datetime.now()
            }
            
            self.logger.info(f"添加定时任务: {job_id}, Cron: {cron_expression}")
            return True
            
        except Exception as e:
            self.logger.error(f"添加定时任务失败: {e}")
            return False
    
    def remove_job(self, job_id: str) -> bool:
        """移除任务"""
        try:
            if job_id in self.registered_jobs:
                self.scheduler.remove_job(job_id)
                del self.registered_jobs[job_id]
                self.logger.info(f"移除任务: {job_id}")
                return True
            else:
                self.logger.warning(f"任务 {job_id} 不存在")
                return False
                
        except Exception as e:
            self.logger.error(f"移除任务失败: {e}")
            return False
    
    def get_jobs_info(self) -> List[Dict]:
        """获取所有任务信息"""
        jobs_info = []
        for job_id, job_data in self.registered_jobs.items():
            job = job_data['job']
            info = {
                'id': job_id,
                'name': job_data['func'],
                'type': job_data['type'],
                'created_at': job_data['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                'next_run_time': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else 'N/A'
            }
            
            if job_data['type'] == 'interval':
                info['interval'] = f"{job_data['interval']}秒"
            elif job_data['type'] == 'cron':
                info['cron'] = job_data['cron']
            
            jobs_info.append(info)
        
        return jobs_info
    
    def search_keywords_job(self, keywords: List[str] = None, pages: int = 1):
        """执行关键词搜索任务"""
        try:
            if keywords is None:
                # 获取数据库中的活跃关键词
                keywords = self.db_manager.get_active_keywords()
                if not keywords:
                    # 如果数据库中没有关键词，使用默认关键词
                    keywords = Config.DEFAULT_KEYWORDS
                    # 将默认关键词添加到数据库
                    for keyword in keywords:
                        self.db_manager.add_keyword(keyword)
            
            self.logger.info(f"开始执行搜索任务，关键词: {keywords}")
            
            # 执行搜索
            results = self.crawler.search_all_engines(keywords, pages)
            
            # 统计结果
            total_results = 0
            for keyword, engine_results in results.items():
                for engine, result_list in engine_results.items():
                    total_results += len(result_list)
            
            self.logger.info(f"搜索任务完成，共获取 {total_results} 个结果")
            
        except Exception as e:
            self.logger.error(f"执行搜索任务失败: {e}")
    
    def trending_keywords_job(self):
        """获取热门关键词任务"""
        try:
            self.logger.info("开始获取热门关键词")
            
            trending_keywords = self.crawler.search_trending_keywords()
            
            # 将热门关键词添加到数据库
            for keyword in trending_keywords:
                self.db_manager.add_keyword(keyword)
            
            self.logger.info(f"热门关键词获取完成，共 {len(trending_keywords)} 个")
            
        except Exception as e:
            self.logger.error(f"获取热门关键词失败: {e}")
    
    def cleanup_old_data_job(self, days_to_keep: int = 30):
        """清理旧数据任务"""
        try:
            self.logger.info(f"开始清理 {days_to_keep} 天前的旧数据")
            
            # 这里可以添加清理逻辑
            # 例如删除指定天数前的搜索结果和任务记录
            
            self.logger.info("旧数据清理完成")
            
        except Exception as e:
            self.logger.error(f"清理旧数据失败: {e}")
    
    def setup_default_jobs(self):
        """设置默认的定时任务"""
        try:
            # 添加默认的关键词搜索任务（每小时执行一次）
            self.add_interval_job(
                job_id='search_keywords_hourly',
                func=self.search_keywords_job,
                interval_seconds=3600,  # 1小时
                pages=1
            )
            
            # 添加热门关键词获取任务（每天执行一次）
            self.add_cron_job(
                job_id='trending_keywords_daily',
                func=self.trending_keywords_job,
                cron_expression='0 9 * * *'  # 每天上午9点
            )
            
            # 添加数据清理任务（每周执行一次）
            self.add_cron_job(
                job_id='cleanup_weekly',
                func=self.cleanup_old_data_job,
                cron_expression='0 2 * * 0',  # 每周日凌晨2点
                days_to_keep=30
            )
            
            self.logger.info("默认定时任务设置完成")
            
        except Exception as e:
            self.logger.error(f"设置默认任务失败: {e}")
    
    def run_once(self, job_id: str):
        """立即执行一次指定任务"""
        try:
            if job_id in self.registered_jobs:
                job_data = self.registered_jobs[job_id]
                job = job_data['job']
                
                self.logger.info(f"立即执行任务: {job_id}")
                job.func(*job.args, **job.kwargs)
                self.logger.info(f"任务执行完成: {job_id}")
                
            else:
                self.logger.warning(f"任务 {job_id} 不存在")
                
        except Exception as e:
            self.logger.error(f"执行任务失败: {e}")
    
    def pause_job(self, job_id: str):
        """暂停任务"""
        try:
            if job_id in self.registered_jobs:
                self.scheduler.pause_job(job_id)
                self.logger.info(f"暂停任务: {job_id}")
            else:
                self.logger.warning(f"任务 {job_id} 不存在")
                
        except Exception as e:
            self.logger.error(f"暂停任务失败: {e}")
    
    def resume_job(self, job_id: str):
        """恢复任务"""
        try:
            if job_id in self.registered_jobs:
                self.scheduler.resume_job(job_id)
                self.logger.info(f"恢复任务: {job_id}")
            else:
                self.logger.warning(f"任务 {job_id} 不存在")
                
        except Exception as e:
            self.logger.error(f"恢复任务失败: {e}")