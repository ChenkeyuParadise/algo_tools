import requests
import time
import logging
import random
from urllib.parse import quote, urljoin
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re

# 尝试导入可选依赖
try:
    from fake_useragent import UserAgent
    HAS_FAKE_USERAGENT = True
except ImportError:
    HAS_FAKE_USERAGENT = False

from .config import Config
from .database import DatabaseManager

# 更新的搜索引擎选择器配置
UPDATED_SELECTORS = {
    'baidu': {
        'result': [
            '.result.c-container[tpl]',  # 新版百度
            '.result.c-container',       # 通用容器
            '.result',                   # 经典选择器
            '[data-click]'               # 备用选择器
        ],
        'title': [
            'h3.c-title a',
            'h3.t a', 
            'h3 a',
            '.c-title-text a'
        ],
        'url': [
            'h3.c-title a',
            'h3.t a',
            'h3 a'
        ],
        'snippet': [
            '.c-abstract',
            '.c-span9',
            '.c-font-normal'
        ]
    },
    'bing': {
        'result': [
            '.b_algo',
            '.b_ans'
        ],
        'title': [
            'h2 a',
            '.b_title a'
        ],
        'url': [
            'h2 a',
            '.b_title a'
        ],
        'snippet': [
            '.b_caption p',
            '.b_caption',
            '.b_excerpt'
        ]
    },
    'sogou': {
        'result': [
            '.results .vrwrap',
            '.results .result',
            '.results .rb'
        ],
        'title': [
            '.vrTitle a',
            'h3 a',
            '.pt a'
        ],
        'url': [
            '.vrTitle a',
            'h3 a',
            '.pt a'
        ],
        'snippet': [
            '.str_info',
            '.ft'
        ]
    }
}

class SearchCrawler:
    """搜索引擎爬虫类（优化版本）"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager or DatabaseManager()
        self.session = requests.Session()
        self.logger = self._setup_logger()
        
        # 初始化User-Agent
        if HAS_FAKE_USERAGENT:
            try:
                self.ua = UserAgent()
            except Exception as e:
                self.logger.warning(f"UserAgent初始化失败: {e}")
                self.ua = None
        else:
            self.ua = None
        
        # 设置默认请求头
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'DNT': '1'
        })
    
    def _setup_logger(self):
        """设置日志记录器"""
        logger = logging.getLogger('SearchCrawler')
        logger.setLevel(logging.INFO)
        
        # 避免重复添加处理器
        if logger.handlers:
            return logger
        
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
        if self.ua:
            try:
                return self.ua.random
            except Exception as e:
                self.logger.warning(f"获取随机UA失败: {e}")
        
        # 备用User-Agent列表
        fallback_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15'
        ]
        return random.choice(fallback_agents)
    
    def _is_blocked(self, response: requests.Response) -> bool:
        """检测是否被反爬虫拦截"""
        if response.status_code in [403, 429, 503]:
            return True
        
        content = response.text.lower()
        blocked_indicators = [
            '验证码', 'captcha', '人机验证', 
            'security check', '安全验证',
            'unusual traffic', '异常流量',
            'robot', '机器人', 'blocked',
            '请输入验证码', '访问验证',
            'access denied', '拒绝访问'
        ]
        
        return any(indicator in content for indicator in blocked_indicators)
    
    def _make_request(self, url: str, retries: int = 3) -> Optional[requests.Response]:
        """发送HTTP请求（增强版本）"""
        for attempt in range(retries):
            try:
                # 随机延迟（避免被检测为机器人）
                delay = random.uniform(2, 6) if attempt == 0 else random.uniform(3, 8)
                time.sleep(delay)
                
                # 设置随机User-Agent和更完整的请求头
                headers = {
                    'User-Agent': self._get_random_user_agent(),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0',
                    'DNT': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1'
                }
                
                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=Config.REQUEST_TIMEOUT,
                    allow_redirects=True
                )
                
                # 检测反爬虫
                if self._is_blocked(response):
                    self.logger.warning(f"请求被拦截 (尝试 {attempt + 1}/{retries}): {url}")
                    if attempt < retries - 1:
                        # 增加延迟时间
                        time.sleep(random.uniform(10, 20))
                    continue
                
                if response.status_code == 200:
                    self.logger.info(f"请求成功: {url}")
                    return response
                else:
                    self.logger.warning(f"请求失败，状态码: {response.status_code}, URL: {url}")
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"请求异常 (尝试 {attempt + 1}/{retries}): {e}")
                
            if attempt < retries - 1:
                # 指数退避策略
                backoff_delay = Config.REQUEST_DELAY * (2 ** attempt) + random.uniform(1, 3)
                time.sleep(backoff_delay)
        
        self.logger.error(f"所有请求尝试都失败: {url}")
        return None
    
    def _try_parse_with_selectors(self, soup: BeautifulSoup, selectors: Dict[str, List[str]]) -> List[Dict]:
        """使用多种选择器尝试解析"""
        results = []
        
        # 尝试不同的结果容器选择器
        for result_selector in selectors['result']:
            result_items = soup.select(result_selector)
            if result_items:
                self.logger.debug(f"使用选择器 '{result_selector}' 找到 {len(result_items)} 个结果")
                break
        else:
            return results
        
        for item in result_items:
            try:
                result = {}
                
                # 提取标题
                title = ''
                for title_selector in selectors['title']:
                    title_elem = item.select_one(title_selector)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        break
                
                # 提取链接
                url = ''
                for url_selector in selectors['url']:
                    url_elem = item.select_one(url_selector)
                    if url_elem and url_elem.get('href'):
                        url = url_elem['href']
                        break
                
                # 提取摘要
                snippet = ''
                for snippet_selector in selectors['snippet']:
                    snippet_elem = item.select_one(snippet_selector)
                    if snippet_elem:
                        snippet = snippet_elem.get_text(strip=True)
                        break
                
                # 只有标题不为空才添加结果
                if title:
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet
                    })
                    
            except Exception as e:
                self.logger.error(f"解析结果项时出错: {e}")
                continue
        
        return results
    
    def _parse_baidu_results(self, html: str) -> List[Dict]:
        """解析百度搜索结果（优化版本）"""
        soup = BeautifulSoup(html, 'lxml')
        results = self._try_parse_with_selectors(soup, UPDATED_SELECTORS['baidu'])
        
        # 处理百度重定向链接
        for result in results:
            if result['url'] and result['url'].startswith('/link?url='):
                result['url'] = 'https://www.baidu.com' + result['url']
        
        return results
    
    def _parse_bing_results(self, html: str) -> List[Dict]:
        """解析必应搜索结果（优化版本）"""
        soup = BeautifulSoup(html, 'lxml')
        return self._try_parse_with_selectors(soup, UPDATED_SELECTORS['bing'])
    
    def _parse_sogou_results(self, html: str) -> List[Dict]:
        """解析搜狗搜索结果（优化版本）"""
        soup = BeautifulSoup(html, 'lxml')
        return self._try_parse_with_selectors(soup, UPDATED_SELECTORS['sogou'])
    
    def search_keyword(self, keyword: str, search_engine: str, pages: int = 1) -> List[Dict]:
        """搜索关键词（优化版本）"""
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
                # 构建搜索URL（修正分页逻辑）
                if search_engine == 'baidu':
                    page_num = page * 10  # 百度分页：0, 10, 20, ...
                elif search_engine == 'bing':
                    page_num = page * 10 + 1  # 必应分页：1, 11, 21, ...
                else:  # sogou
                    page_num = page + 1  # 搜狗分页：1, 2, 3, ...
                
                search_url = engine_config['search_url'].format(
                    keyword=quote(keyword),
                    page=page_num
                )
                
                self.logger.info(f"搜索 '{keyword}' 在 {engine_config['name']} (第{page+1}页): {search_url}")
                
                # 发送请求
                response = self._make_request(search_url)
                if not response:
                    self.logger.warning(f"第{page+1}页请求失败，跳过")
                    continue
                
                # 解析结果
                try:
                    if search_engine == 'baidu':
                        page_results = self._parse_baidu_results(response.text)
                    elif search_engine == 'bing':
                        page_results = self._parse_bing_results(response.text)
                    else:  # sogou
                        page_results = self._parse_sogou_results(response.text)
                    
                    all_results.extend(page_results)
                    self.logger.info(f"第{page+1}页成功解析 {len(page_results)} 个结果")
                    
                    # 如果某页没有结果，可能已到最后一页
                    if not page_results:
                        self.logger.info(f"第{page+1}页无结果，停止翻页")
                        break
                        
                except Exception as e:
                    self.logger.error(f"解析第{page+1}页结果时出错: {e}")
                    continue
                
                # 页面间延迟（随机化以避免检测）
                if page < pages - 1:
                    page_delay = random.uniform(3, 8)
                    time.sleep(page_delay)
            
            # 保存结果到数据库
            if all_results:
                self.db_manager.save_search_results(task_id, keyword, search_engine, all_results)
            
            # 更新统计
            response_time = time.time() - start_time
            self.db_manager.update_statistics(
                keyword, search_engine, len(all_results), len(all_results), response_time
            )
            
            # 更新任务状态
            self.db_manager.update_task_status(task_id, 'completed')
            
            self.logger.info(f"搜索完成: '{keyword}' 在 {engine_config['name']}, 共获取 {len(all_results)} 个结果, 耗时 {response_time:.2f}秒")
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
        """在所有启用的搜索引擎中搜索关键词（优化版本）"""
        results = {}
        enabled_engines = Config.get_enabled_search_engines()
        
        total_tasks = len(keywords) * len(enabled_engines)
        current_task = 0
        
        for keyword in keywords:
            results[keyword] = {}
            
            for engine_name, engine_config in enabled_engines.items():
                current_task += 1
                self.logger.info(f"进度 [{current_task}/{total_tasks}] 开始搜索: '{keyword}' 在 {engine_config['name']}")
                
                try:
                    search_results = self.search_keyword(keyword, engine_name, pages)
                    results[keyword][engine_name] = search_results
                except Exception as e:
                    self.logger.error(f"搜索引擎 {engine_name} 处理关键词 '{keyword}' 时出错: {e}")
                    results[keyword][engine_name] = []
                
                # 搜索引擎间延迟（随机化）
                engine_delay = random.uniform(5, 12)
                time.sleep(engine_delay)
        
        return results
    
    def test_search_engine(self, search_engine: str) -> Dict[str, any]:
        """测试单个搜索引擎是否可用"""
        test_keyword = "Python"
        self.logger.info(f"测试搜索引擎: {search_engine}")
        
        try:
            results = self.search_keyword(test_keyword, search_engine, pages=1)
            
            return {
                'engine': search_engine,
                'success': len(results) > 0,
                'result_count': len(results),
                'sample_results': results[:3] if results else [],
                'error': None
            }
        except Exception as e:
            return {
                'engine': search_engine,
                'success': False,
                'result_count': 0,
                'sample_results': [],
                'error': str(e)
            }
    
    def test_all_engines(self) -> Dict[str, Dict[str, any]]:
        """测试所有搜索引擎"""
        results = {}
        enabled_engines = Config.get_enabled_search_engines()
        
        for engine_name in enabled_engines.keys():
            results[engine_name] = self.test_search_engine(engine_name)
            time.sleep(random.uniform(3, 6))  # 测试间延迟
        
        return results
    
    def search_trending_keywords(self, search_engine: str = 'baidu') -> List[str]:
        """获取热门关键词（简单实现）"""
        trending_keywords = [
            "ChatGPT", "人工智能", "机器学习", "区块链", "元宇宙",
            "量子计算", "5G技术", "新能源汽车", "虚拟现实", "物联网",
            "Python编程", "数据分析", "云计算", "网络安全", "大数据"
        ]
        
        self.logger.info(f"获取到 {len(trending_keywords)} 个热门关键词")
        return trending_keywords