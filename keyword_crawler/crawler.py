import requests
import time
import logging
from urllib.parse import quote, urljoin
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import re

from .config import Config
from .database import DatabaseManager

class SearchCrawler:
    """搜索引擎爬虫类"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager or DatabaseManager()
        self.session = requests.Session()
        self.ua = UserAgent()
        self.logger = self._setup_logger()
        
        # 设置默认请求头
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def _setup_logger(self):
        """设置日志记录器"""
        logger = logging.getLogger('SearchCrawler')
        logger.setLevel(logging.INFO)
        
        # 创建文件处理器
        Config.ensure_directories()
        file_handler = logging.FileHandler(f'{Config.LOGS_DIR}/crawler.log', encoding='utf-8')
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
    
    def _get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        try:
            return self.ua.random
        except:
            return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    
    def _make_request(self, url: str, retries: int = 3) -> Optional[requests.Response]:
        """发送HTTP请求"""
        for attempt in range(retries):
            try:
                # 设置随机User-Agent
                self.session.headers['User-Agent'] = self._get_random_user_agent()
                
                response = self.session.get(
                    url,
                    timeout=Config.REQUEST_TIMEOUT,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    return response
                else:
                    self.logger.warning(f"请求失败，状态码: {response.status_code}, URL: {url}")
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"请求异常 (尝试 {attempt + 1}/{retries}): {e}")
                
            if attempt < retries - 1:
                time.sleep(Config.REQUEST_DELAY * (attempt + 1))
        
        return None
    
    def _parse_baidu_results(self, html: str) -> List[Dict]:
        """解析百度搜索结果"""
        results = []
        soup = BeautifulSoup(html, 'lxml')
        
        # 百度搜索结果选择器
        result_items = soup.select('.result, .c-container')
        
        for item in result_items:
            try:
                # 提取标题
                title_elem = item.select_one('h3 a, .t a')
                title = title_elem.get_text(strip=True) if title_elem else ''
                
                # 提取链接
                link = ''
                if title_elem and title_elem.get('href'):
                    link = title_elem['href']
                    # 处理百度重定向链接
                    if link.startswith('/link?url='):
                        link = 'https://www.baidu.com' + link
                
                # 提取摘要
                snippet_elem = item.select_one('.c-abstract, .c-span9')
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                
                if title:  # 只有标题不为空才添加结果
                    results.append({
                        'title': title,
                        'url': link,
                        'snippet': snippet
                    })
                    
            except Exception as e:
                self.logger.error(f"解析百度结果项时出错: {e}")
                continue
        
        return results
    
    def _parse_bing_results(self, html: str) -> List[Dict]:
        """解析必应搜索结果"""
        results = []
        soup = BeautifulSoup(html, 'lxml')
        
        # 必应搜索结果选择器
        result_items = soup.select('.b_algo')
        
        for item in result_items:
            try:
                # 提取标题
                title_elem = item.select_one('h2 a')
                title = title_elem.get_text(strip=True) if title_elem else ''
                
                # 提取链接
                link = title_elem['href'] if title_elem and title_elem.get('href') else ''
                
                # 提取摘要
                snippet_elem = item.select_one('.b_caption p')
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                
                if title:
                    results.append({
                        'title': title,
                        'url': link,
                        'snippet': snippet
                    })
                    
            except Exception as e:
                self.logger.error(f"解析必应结果项时出错: {e}")
                continue
        
        return results
    
    def _parse_sogou_results(self, html: str) -> List[Dict]:
        """解析搜狗搜索结果"""
        results = []
        soup = BeautifulSoup(html, 'lxml')
        
        # 搜狗搜索结果选择器
        result_items = soup.select('.results .rb, .result')
        
        for item in result_items:
            try:
                # 提取标题
                title_elem = item.select_one('h3 a, .pt a')
                title = title_elem.get_text(strip=True) if title_elem else ''
                
                # 提取链接
                link = title_elem['href'] if title_elem and title_elem.get('href') else ''
                
                # 提取摘要
                snippet_elem = item.select_one('.ft, .str_info')
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                
                if title:
                    results.append({
                        'title': title,
                        'url': link,
                        'snippet': snippet
                    })
                    
            except Exception as e:
                self.logger.error(f"解析搜狗结果项时出错: {e}")
                continue
        
        return results
    
    def search_keyword(self, keyword: str, search_engine: str, pages: int = 1) -> List[Dict]:
        """搜索关键词"""
        start_time = time.time()
        
        # 创建搜索任务
        task_id = self.db_manager.create_search_task(keyword, search_engine)
        self.db_manager.update_task_status(task_id, 'running')
        
        try:
            engine_config = Config.SEARCH_ENGINES.get(search_engine)
            if not engine_config:
                raise ValueError(f"不支持的搜索引擎: {search_engine}")
            
            all_results = []
            
            for page in range(pages):
                # 构建搜索URL
                if search_engine == 'baidu':
                    page_num = page * 10
                elif search_engine == 'bing':
                    page_num = page * 10 + 1
                else:  # sogou
                    page_num = page + 1
                
                search_url = engine_config['search_url'].format(
                    keyword=quote(keyword),
                    page=page_num
                )
                
                self.logger.info(f"搜索 '{keyword}' 在 {engine_config['name']} (第{page+1}页)")
                
                # 发送请求
                response = self._make_request(search_url)
                if not response:
                    continue
                
                # 解析结果
                if search_engine == 'baidu':
                    page_results = self._parse_baidu_results(response.text)
                elif search_engine == 'bing':
                    page_results = self._parse_bing_results(response.text)
                else:  # sogou
                    page_results = self._parse_sogou_results(response.text)
                
                all_results.extend(page_results)
                self.logger.info(f"第{page+1}页获取到 {len(page_results)} 个结果")
                
                # 页面间延迟
                if page < pages - 1:
                    time.sleep(Config.REQUEST_DELAY)
            
            # 保存结果
            self.db_manager.save_search_results(task_id, keyword, search_engine, all_results)
            
            # 更新统计
            response_time = time.time() - start_time
            self.db_manager.update_statistics(
                keyword, search_engine, len(all_results), len(all_results), response_time
            )
            
            # 更新任务状态
            self.db_manager.update_task_status(task_id, 'completed')
            
            self.logger.info(f"搜索完成: '{keyword}' 在 {engine_config['name']}, 共获取 {len(all_results)} 个结果")
            return all_results
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"搜索失败: {error_msg}")
            self.db_manager.update_task_status(task_id, 'failed', error_msg)
            
            # 更新失败统计
            response_time = time.time() - start_time
            self.db_manager.update_statistics(keyword, search_engine, 0, 0, response_time)
            
            return []
    
    def search_all_engines(self, keywords: List[str], pages: int = 1) -> Dict[str, Dict[str, List[Dict]]]:
        """在所有启用的搜索引擎中搜索关键词"""
        results = {}
        enabled_engines = Config.get_enabled_search_engines()
        
        for keyword in keywords:
            results[keyword] = {}
            
            for engine_name, engine_config in enabled_engines.items():
                self.logger.info(f"开始搜索: '{keyword}' 在 {engine_config['name']}")
                
                search_results = self.search_keyword(keyword, engine_name, pages)
                results[keyword][engine_name] = search_results
                
                # 搜索引擎间延迟
                time.sleep(Config.REQUEST_DELAY)
        
        return results
    
    def search_trending_keywords(self, search_engine: str = 'baidu') -> List[str]:
        """获取热门关键词（简单实现）"""
        trending_keywords = [
            "ChatGPT", "人工智能", "机器学习", "区块链", "元宇宙",
            "量子计算", "5G技术", "新能源汽车", "虚拟现实", "物联网"
        ]
        
        self.logger.info(f"获取到 {len(trending_keywords)} 个热门关键词")
        return trending_keywords