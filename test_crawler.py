#!/usr/bin/env python3
"""
爬虫功能测试脚本

用于测试SearchCrawler的各项功能
"""

import sys
import os
import logging
import traceback

# 添加项目路径
sys.path.append('.')

def setup_test_logging():
    """设置测试日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('test_crawler.log', encoding='utf-8')
        ]
    )

def test_imports():
    """测试导入功能"""
    print("🔧 测试模块导入...")
    
    try:
        from keyword_crawler.crawler import SearchCrawler
        from keyword_crawler.database import DatabaseManager
        from keyword_crawler.config import Config
        print("✅ 核心模块导入成功")
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_dependencies():
    """测试依赖包"""
    print("\n🔧 测试依赖包...")
    
    dependencies = {
        'requests': False,
        'beautifulsoup4': False,
        'lxml': False,
        'fake_useragent': False
    }
    
    try:
        import requests
        dependencies['requests'] = True
        print("✅ requests 可用")
    except ImportError:
        print("❌ requests 不可用")
    
    try:
        from bs4 import BeautifulSoup
        dependencies['beautifulsoup4'] = True
        print("✅ beautifulsoup4 可用")
    except ImportError:
        print("❌ beautifulsoup4 不可用")
    
    try:
        import lxml
        dependencies['lxml'] = True
        print("✅ lxml 可用")
    except ImportError:
        print("❌ lxml 不可用")
    
    try:
        from fake_useragent import UserAgent
        dependencies['fake_useragent'] = True
        print("✅ fake_useragent 可用")
    except ImportError:
        print("❌ fake_useragent 不可用 (可选依赖)")
    
    essential_deps = ['requests', 'beautifulsoup4']
    missing_essential = [dep for dep in essential_deps if not dependencies[dep]]
    
    if missing_essential:
        print(f"❌ 缺少必要依赖: {missing_essential}")
        return False
    else:
        print("✅ 必要依赖检查通过")
        return True

def test_crawler_initialization():
    """测试爬虫初始化"""
    print("\n🔧 测试爬虫初始化...")
    
    try:
        from keyword_crawler.crawler import SearchCrawler
        from keyword_crawler.database import DatabaseManager
        
        db_manager = DatabaseManager()
        crawler = SearchCrawler(db_manager)
        
        print("✅ 爬虫初始化成功")
        print(f"✅ 日志器设置: {type(crawler.logger).__name__}")
        print(f"✅ 会话设置: {type(crawler.session).__name__}")
        
        # 测试User-Agent生成
        ua = crawler._get_random_user_agent()
        print(f"✅ User-Agent生成: {ua[:50]}...")
        
        return crawler
        
    except Exception as e:
        print(f"❌ 爬虫初始化失败: {e}")
        traceback.print_exc()
        return None

def test_url_building():
    """测试URL构建"""
    print("\n🔧 测试URL构建...")
    
    try:
        from keyword_crawler.config import Config
        from urllib.parse import quote
        
        test_keyword = "Python编程"
        engines = Config.get_enabled_search_engines()
        
        for engine_name, engine_config in engines.items():
            search_url = engine_config['search_url'].format(
                keyword=quote(test_keyword),
                page=0
            )
            print(f"✅ {engine_config['name']}: {search_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ URL构建失败: {e}")
        return False

def test_selectors():
    """测试CSS选择器"""
    print("\n🔧 测试CSS选择器...")
    
    try:
        from keyword_crawler.crawler import UPDATED_SELECTORS
        
        for engine, selectors in UPDATED_SELECTORS.items():
            print(f"📋 {engine.upper()} 选择器:")
            print(f"  结果容器: {selectors['result']}")
            print(f"  标题: {selectors['title']}")
            print(f"  链接: {selectors['url']}")
            print(f"  摘要: {selectors['snippet']}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ 选择器测试失败: {e}")
        return False

def test_search_single_keyword(crawler):
    """测试单关键词搜索"""
    print("\n🔧 测试单关键词搜索...")
    
    if not crawler:
        print("❌ 爬虫未初始化，跳过测试")
        return False
    
    test_keyword = "Python"
    test_engines = ["baidu", "bing"]  # 限制测试范围
    
    results = {}
    
    for engine in test_engines:
        print(f"\n📍 测试搜索引擎: {engine}")
        
        try:
            # 只搜索1页，减少测试时间
            search_results = crawler.search_keyword(test_keyword, engine, pages=1)
            results[engine] = search_results
            
            print(f"✅ {engine} 搜索成功，获取 {len(search_results)} 个结果")
            
            # 显示前3个结果样例
            for i, result in enumerate(search_results[:3]):
                print(f"  [{i+1}] {result['title'][:50]}...")
                if result['url']:
                    print(f"      {result['url'][:60]}...")
                
        except Exception as e:
            print(f"❌ {engine} 搜索失败: {e}")
            results[engine] = []
    
    total_results = sum(len(r) for r in results.values())
    print(f"\n📊 搜索结果汇总: 共 {total_results} 个结果")
    
    return total_results > 0

def test_all_engines(crawler):
    """测试所有搜索引擎"""
    print("\n🔧 测试所有搜索引擎状态...")
    
    if not crawler:
        print("❌ 爬虫未初始化，跳过测试")
        return False
    
    try:
        test_results = crawler.test_all_engines()
        
        print("📊 搜索引擎测试结果:")
        for engine, result in test_results.items():
            status = "✅" if result['success'] else "❌"
            print(f"{status} {engine}: {result['result_count']} 个结果")
            
            if result['error']:
                print(f"    错误: {result['error']}")
            
            # 显示样例结果
            for i, sample in enumerate(result['sample_results']):
                print(f"    [{i+1}] {sample['title'][:40]}...")
        
        successful_engines = [e for e, r in test_results.items() if r['success']]
        print(f"\n📈 成功率: {len(successful_engines)}/{len(test_results)} 个引擎可用")
        
        return len(successful_engines) > 0
        
    except Exception as e:
        print(f"❌ 引擎测试失败: {e}")
        return False

def test_anti_crawler_detection():
    """测试反爬虫检测"""
    print("\n🔧 测试反爬虫检测...")
    
    try:
        from keyword_crawler.crawler import SearchCrawler
        import requests
        
        crawler = SearchCrawler()
        
        # 模拟正常响应
        class MockResponse:
            def __init__(self, status_code, text):
                self.status_code = status_code
                self.text = text
        
        # 测试正常响应
        normal_response = MockResponse(200, "<html><body>正常页面</body></html>")
        assert not crawler._is_blocked(normal_response), "正常响应被误判为拦截"
        print("✅ 正常响应检测正确")
        
        # 测试拦截响应
        blocked_response = MockResponse(403, "<html><body>验证码 captcha</body></html>")
        assert crawler._is_blocked(blocked_response), "拦截响应未被检测到"
        print("✅ 拦截响应检测正确")
        
        return True
        
    except Exception as e:
        print(f"❌ 反爬虫检测测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始爬虫功能全面测试")
    print("=" * 50)
    
    setup_test_logging()
    
    # 测试步骤
    test_results = []
    
    # 1. 测试导入
    test_results.append(("模块导入", test_imports()))
    
    # 2. 测试依赖
    test_results.append(("依赖包检查", test_dependencies()))
    
    # 3. 测试初始化
    crawler = test_crawler_initialization()
    test_results.append(("爬虫初始化", crawler is not None))
    
    # 4. 测试URL构建
    test_results.append(("URL构建", test_url_building()))
    
    # 5. 测试选择器
    test_results.append(("CSS选择器", test_selectors()))
    
    # 6. 测试反爬虫检测
    test_results.append(("反爬虫检测", test_anti_crawler_detection()))
    
    # 7. 测试搜索功能（如果依赖可用）
    if test_results[1][1]:  # 如果依赖检查通过
        test_results.append(("单关键词搜索", test_search_single_keyword(crawler)))
        test_results.append(("搜索引擎测试", test_all_engines(crawler)))
    else:
        print("\n⚠️  跳过搜索功能测试（缺少依赖）")
        test_results.append(("单关键词搜索", False))
        test_results.append(("搜索引擎测试", False))
    
    # 汇总测试结果
    print("\n" + "=" * 50)
    print("📋 测试结果汇总:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📊 总体结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！爬虫功能正常")
        return 0
    elif passed >= total * 0.7:  # 70%以上通过
        print("⚠️  大部分测试通过，爬虫基本可用")
        return 0
    else:
        print("🚨 多项测试失败，爬虫可能无法正常工作")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)