import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from .config import Config

class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建搜索任务表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    search_engine TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT
                )
            ''')
            
            # 创建搜索结果表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER,
                    keyword TEXT NOT NULL,
                    search_engine TEXT NOT NULL,
                    title TEXT,
                    url TEXT,
                    snippet TEXT,
                    rank_position INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES search_tasks (id)
                )
            ''')
            
            # 创建统计数据表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    search_engine TEXT NOT NULL,
                    total_results INTEGER DEFAULT 0,
                    successful_results INTEGER DEFAULT 0,
                    failed_results INTEGER DEFAULT 0,
                    avg_response_time REAL DEFAULT 0,
                    date DATE DEFAULT CURRENT_DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建关键词表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_searched TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def add_keyword(self, keyword: str) -> bool:
        """添加关键词"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO keywords (keyword) VALUES (?)",
                    (keyword,)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"添加关键词失败: {e}")
            return False
    
    def get_active_keywords(self) -> List[str]:
        """获取活跃的关键词列表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT keyword FROM keywords WHERE is_active = 1"
            )
            return [row[0] for row in cursor.fetchall()]
    
    def create_search_task(self, keyword: str, search_engine: str) -> int:
        """创建搜索任务"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO search_tasks (keyword, search_engine, status, created_at)
                VALUES (?, ?, 'pending', ?)
            ''', (keyword, search_engine, datetime.now()))
            conn.commit()
            return cursor.lastrowid
    
    def update_task_status(self, task_id: int, status: str, error_message: str = None):
        """更新任务状态"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if status == 'running':
                cursor.execute('''
                    UPDATE search_tasks 
                    SET status = ?, started_at = ? 
                    WHERE id = ?
                ''', (status, datetime.now(), task_id))
            elif status == 'completed':
                cursor.execute('''
                    UPDATE search_tasks 
                    SET status = ?, completed_at = ? 
                    WHERE id = ?
                ''', (status, datetime.now(), task_id))
            elif status == 'failed':
                cursor.execute('''
                    UPDATE search_tasks 
                    SET status = ?, completed_at = ?, error_message = ?
                    WHERE id = ?
                ''', (status, datetime.now(), error_message, task_id))
            conn.commit()
    
    def save_search_results(self, task_id: int, keyword: str, search_engine: str, results: List[Dict]):
        """保存搜索结果"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for i, result in enumerate(results):
                cursor.execute('''
                    INSERT INTO search_results 
                    (task_id, keyword, search_engine, title, url, snippet, rank_position)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task_id, keyword, search_engine,
                    result.get('title', ''),
                    result.get('url', ''),
                    result.get('snippet', ''),
                    i + 1
                ))
            conn.commit()
    
    def update_statistics(self, keyword: str, search_engine: str, 
                         total_results: int, successful_results: int, 
                         response_time: float):
        """更新统计数据"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            today = datetime.now().date()
            
            # 检查今天是否已有记录
            cursor.execute('''
                SELECT id FROM statistics 
                WHERE keyword = ? AND search_engine = ? AND date = ?
            ''', (keyword, search_engine, today))
            
            existing = cursor.fetchone()
            if existing:
                # 更新现有记录
                cursor.execute('''
                    UPDATE statistics 
                    SET total_results = total_results + ?,
                        successful_results = successful_results + ?,
                        failed_results = failed_results + ?,
                        avg_response_time = (avg_response_time + ?) / 2
                    WHERE id = ?
                ''', (total_results, successful_results, 
                      total_results - successful_results, response_time, existing[0]))
            else:
                # 创建新记录
                cursor.execute('''
                    INSERT INTO statistics 
                    (keyword, search_engine, total_results, successful_results,
                     failed_results, avg_response_time, date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (keyword, search_engine, total_results, successful_results,
                      total_results - successful_results, response_time, today))
            
            conn.commit()
    
    def get_task_statistics(self, days: int = 7) -> List[Dict]:
        """获取任务统计数据"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    keyword,
                    search_engine,
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_tasks,
                    date(created_at) as date
                FROM search_tasks 
                WHERE created_at >= date('now', '-{} days')
                GROUP BY keyword, search_engine, date(created_at)
                ORDER BY created_at DESC
            '''.format(days))
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_search_results_count(self, keyword: str = None, search_engine: str = None, days: int = 7) -> List[Dict]:
        """获取搜索结果数量统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            where_conditions = ["created_at >= date('now', '-{} days')".format(days)]
            params = []
            
            if keyword:
                where_conditions.append("keyword = ?")
                params.append(keyword)
            
            if search_engine:
                where_conditions.append("search_engine = ?")
                params.append(search_engine)
            
            where_clause = " AND ".join(where_conditions)
            
            cursor.execute(f'''
                SELECT 
                    keyword,
                    search_engine,
                    COUNT(*) as result_count,
                    date(created_at) as date
                FROM search_results 
                WHERE {where_clause}
                GROUP BY keyword, search_engine, date(created_at)
                ORDER BY created_at DESC
            ''', params)
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]