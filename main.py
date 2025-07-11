#!/usr/bin/env python3
"""
关键词爬虫工具主程序

使用方法:
    python main.py web              # 启动Web界面
    python main.py crawl            # 执行一次搜索
    python main.py schedule         # 启动定时任务
    python main.py visualize        # 生成可视化图表
    python main.py --help           # 显示帮助信息
"""

import argparse
import sys
import signal
import logging
from datetime import datetime

from keyword_crawler import (
    Config, 
    DatabaseManager, 
    SearchCrawler, 
    TaskScheduler, 
    DataVisualizer
)
from keyword_crawler.web_app import WebApp

def setup_logging():
    """设置日志"""
    Config.ensure_directories()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'{Config.LOGS_DIR}/main.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\n收到信号 {signum}，正在优雅地退出...")
    sys.exit(0)

def cmd_web(args):
    """启动Web界面"""
    print("🚀 启动Web界面...")
    
    try:
        web_app = WebApp()
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, lambda s, f: web_app.stop() or sys.exit(0))
        signal.signal(signal.SIGTERM, lambda s, f: web_app.stop() or sys.exit(0))
        
        print(f"📱 Web界面将在 http://{args.host}:{args.port} 启动")
        print("📊 功能包括：任务管理、数据统计、可视化图表等")
        print("⏹️  按 Ctrl+C 停止服务")
        
        web_app.run(host=args.host, port=args.port, debug=args.debug)
        
    except KeyboardInterrupt:
        print("\n👋 Web服务已停止")
    except Exception as e:
        print(f"❌ Web服务启动失败: {e}")
        sys.exit(1)

def cmd_crawl(args):
    """执行一次搜索"""
    print("🕷️ 开始执行搜索任务...")
    
    try:
        db_manager = DatabaseManager()
        crawler = SearchCrawler(db_manager)
        
        # 获取关键词
        if args.keywords:
            keywords = args.keywords
        else:
            keywords = db_manager.get_active_keywords()
            if not keywords:
                keywords = Config.DEFAULT_KEYWORDS
                # 添加默认关键词到数据库
                for keyword in keywords:
                    db_manager.add_keyword(keyword)
        
        print(f"🔍 搜索关键词: {', '.join(keywords)}")
        print(f"📄 搜索页数: {args.pages}")
        
        # 执行搜索
        results = crawler.search_all_engines(keywords, args.pages)
        
        # 统计结果
        total_results = 0
        for keyword, engine_results in results.items():
            keyword_total = sum(len(result_list) for result_list in engine_results.values())
            print(f"  📋 {keyword}: {keyword_total} 个结果")
            total_results += keyword_total
        
        print(f"✅ 搜索完成！总共获取 {total_results} 个结果")
        
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        sys.exit(1)

def cmd_schedule(args):
    """启动定时任务"""
    print("⏰ 启动定时任务调度器...")
    
    try:
        db_manager = DatabaseManager()
        scheduler = TaskScheduler(db_manager)
        
        # 设置默认任务
        scheduler.setup_default_jobs()
        scheduler.start()
        
        print("✅ 定时任务已启动")
        print("📋 默认任务:")
        
        jobs_info = scheduler.get_jobs_info()
        for job in jobs_info:
            print(f"  - {job['name']} ({job['type']}): 下次执行 {job['next_run_time']}")
        
        print("\n⏹️  按 Ctrl+C 停止调度器")
        
        # 保持运行
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 正在停止调度器...")
            scheduler.stop()
            print("👋 调度器已停止")
            
    except Exception as e:
        print(f"❌ 调度器启动失败: {e}")
        sys.exit(1)

def cmd_visualize(args):
    """生成可视化图表"""
    print(f"📊 生成最近 {args.days} 天的可视化图表...")
    
    try:
        db_manager = DatabaseManager()
        visualizer = DataVisualizer(db_manager)
        
        # 生成所有图表
        generated_files = visualizer.generate_all_visualizations(days=args.days)
        
        if generated_files:
            print("✅ 图表生成完成:")
            for chart_type, file_path in generated_files.items():
                print(f"  📈 {chart_type}: {file_path}")
                
            # 生成摘要报告
            summary = visualizer.generate_summary_report(days=args.days)
            print(f"\n📋 数据摘要 ({summary['period']}):")
            print(f"  🔢 总搜索结果: {summary['total_search_results']}")
            print(f"  📝 总任务数: {summary['total_tasks']}")
            print(f"  ✅ 成功率: {summary['success_rate']}%")
            print(f"  🏷️  活跃关键词: {summary['active_keywords']}")
            
        else:
            print("⚠️  没有足够的数据生成图表")
            
    except Exception as e:
        print(f"❌ 图表生成失败: {e}")
        sys.exit(1)

def cmd_status(args):
    """显示系统状态"""
    print("📊 系统状态:")
    
    try:
        db_manager = DatabaseManager()
        visualizer = DataVisualizer(db_manager)
        
        # 获取概要信息
        summary = visualizer.generate_summary_report(days=7)
        
        print(f"  📅 统计周期: {summary['period']}")
        print(f"  🔢 总搜索结果: {summary['total_search_results']}")
        print(f"  📝 总任务数: {summary['total_tasks']}")
        print(f"  ✅ 成功率: {summary['success_rate']}%")
        print(f"  🏷️  活跃关键词: {summary['active_keywords']}")
        print(f"  🔍 活跃搜索引擎: {summary['active_engines']}")
        
        if summary['top_keywords']:
            print("\n🔥 热门关键词:")
            for keyword, count in list(summary['top_keywords'].items())[:5]:
                print(f"  - {keyword}: {count} 个结果")
        
        print(f"\n🕐 最后更新: {summary['generated_at']}")
        
    except Exception as e:
        print(f"❌ 获取状态失败: {e}")
        sys.exit(1)

def cmd_init(args):
    """初始化系统"""
    print("🔧 初始化系统...")
    
    try:
        # 确保目录存在
        Config.ensure_directories()
        print("✅ 创建必要目录")
        
        # 初始化数据库
        db_manager = DatabaseManager()
        print("✅ 初始化数据库")
        
        # 添加默认关键词
        for keyword in Config.DEFAULT_KEYWORDS:
            db_manager.add_keyword(keyword)
        print(f"✅ 添加 {len(Config.DEFAULT_KEYWORDS)} 个默认关键词")
        
        print("🎉 系统初始化完成！")
        print("\n📋 使用指南:")
        print("  python main.py web       # 启动Web界面")
        print("  python main.py crawl     # 执行搜索")
        print("  python main.py schedule  # 启动定时任务")
        print("  python main.py status    # 查看状态")
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        sys.exit(1)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="关键词爬虫工具 - 定时爬取互联网关键词数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s init                           # 初始化系统
  %(prog)s web                            # 启动Web界面
  %(prog)s crawl -k "AI" "机器学习" -p 2   # 搜索指定关键词
  %(prog)s schedule                       # 启动定时任务
  %(prog)s visualize -d 30                # 生成30天的图表
  %(prog)s status                         # 查看系统状态
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # init命令
    parser_init = subparsers.add_parser('init', help='初始化系统')
    parser_init.set_defaults(func=cmd_init)
    
    # web命令
    parser_web = subparsers.add_parser('web', help='启动Web界面')
    parser_web.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser_web.add_argument('--port', type=int, default=5000, help='监听端口')
    parser_web.add_argument('--debug', action='store_true', help='调试模式')
    parser_web.set_defaults(func=cmd_web)
    
    # crawl命令
    parser_crawl = subparsers.add_parser('crawl', help='执行搜索任务')
    parser_crawl.add_argument('-k', '--keywords', nargs='+', help='关键词列表')
    parser_crawl.add_argument('-p', '--pages', type=int, default=1, help='搜索页数')
    parser_crawl.set_defaults(func=cmd_crawl)
    
    # schedule命令
    parser_schedule = subparsers.add_parser('schedule', help='启动定时任务')
    parser_schedule.set_defaults(func=cmd_schedule)
    
    # visualize命令
    parser_visualize = subparsers.add_parser('visualize', help='生成可视化图表')
    parser_visualize.add_argument('-d', '--days', type=int, default=7, help='统计天数')
    parser_visualize.set_defaults(func=cmd_visualize)
    
    # status命令
    parser_status = subparsers.add_parser('status', help='显示系统状态')
    parser_status.set_defaults(func=cmd_status)
    
    # 解析参数
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 设置日志
    setup_logging()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 执行命令
    try:
        args.func(args)
    except AttributeError:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()