import argparse
import asyncio
import os
import urllib.parse
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

# --- 辅助函数 ---

def parse_cookie_string(cookie_string):
    """从文件内容解析 Cookie 字符串为字典列表。"""
    cookies = []
    if not cookie_string:
        return cookies
    
    for item in cookie_string.split(';'):
        if '=' in item:
            name, value = item.strip().split('=', 1)
            cookies.append({
                'name': name,
                'value': value,
                'domain': '.zread.ai',  # 如果需要可调整域名
                'path': '/'
            })
    return cookies

def build_output_path(url, output_dir, repo_path):
    """从 URL 生成输出文件路径，尽量保留路径层级避免重名。"""
    parsed = urlparse(url)
    path = parsed.path

    if repo_path and path.startswith(repo_path):
        path = path[len(repo_path):]

    path = path.lstrip('/')
    if not path:
        path = "index"

    # 如果是目录，补 index
    if path.endswith('/'):
        path = f"{path}index"

    rel_path = Path(path)
    # 统一输出为 .md
    rel_path = rel_path.with_suffix(".md")

    output_dir = Path(output_dir)
    return output_dir / rel_path

def extract_repo_path(url):
    """从完整 URL 中提取仓库路径 (例如: /user/repo)。"""
    parsed = urlparse(url)
    path = parsed.path
    # 清理尾部斜杠
    if path.endswith('/'):
        path = path[:-1]
    return path

# --- 爬虫逻辑 ---

async def fetch_page_html(crawler, url):
    """使用爬虫获取页面的原始 HTML。"""
    print(f"正在获取菜单页面: {url}")
    
    # 用于获取 HTML 的简单配置
    config = CrawlerRunConfig(
        verbose=True,
        wait_until="domcontentloaded",
        delay_before_return_html=3.0, # 等待动态内容加载
        magic=True,
        simulate_user=True,
        override_navigator=True,
        cache_mode=CacheMode.BYPASS
    )
    
    result = await crawler.arun(url, config=config)
    
    if result.success:
        return result.html
    else:
        print(f"❌ 获取菜单页面失败: {result.error_message}")
        return None

def parse_menu_links(html_content, base_url, repo_path):
    """解析 HTML 以查找仓库内的链接。"""
    soup = BeautifulSoup(html_content, 'html.parser')

    print(f"--- 正在分析菜单结构 ---")
    print(f"目标路径: {repo_path}")

    menu_items = []
    seen_hrefs = set()
    parsed_base = urlparse(base_url)

    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a.get("href")
        if not href:
            continue

        full_url = urllib.parse.urljoin(base_url, href)
        parsed_href = urlparse(full_url)

        if parsed_href.netloc and parsed_href.netloc != parsed_base.netloc:
            continue

        if repo_path and not parsed_href.path.startswith(repo_path):
            continue

        if full_url in seen_hrefs:
            continue

        seen_hrefs.add(full_url)
        menu_items.append({"text": text or full_url, "url": full_url})

    print(f"发现 {len(menu_items)} 个潜在链接")
    return menu_items

async def download_doc(crawler, url, output_dir, repo_path, css_selector="main", excluded_selector="nav,footer,header,aside"):
    """将单个文档页面下载为 Markdown。"""
    print(f"正在处理: {url}")
    
    # 用于触发懒加载的滚动脚本 (来自原脚本)
    js_scroll = """
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(r => setTimeout(r, 2000));
        window.scrollTo(0, 0);
    """
    
    config = CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator(),
        css_selector=css_selector,
        excluded_selector=excluded_selector,
        verbose=True,
        wait_until="domcontentloaded",
        js_code=[js_scroll],
        delay_before_return_html=5.0,
        magic=True,
        simulate_user=True,
        override_navigator=True,
        cache_mode=CacheMode.BYPASS
    )
    
    try:
        result = await crawler.arun(url, config=config)
        
        if result.success:
            filepath = build_output_path(url, output_dir, repo_path)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(result.markdown.raw_markdown)
            print(f"✅ 已保存: {filepath}")
        else:
            print(f"❌ 失败 {url}: {result.error_message}")
            
    except Exception as e:
        print(f"❌ 异常 {url}: {str(e)}")

# --- 主执行逻辑 ---

async def main():
    parser = argparse.ArgumentParser(description="从 Zread 仓库下载文档。")
    parser.add_argument("repo_url", help="Zread 仓库的完整 URL (例如: https://zread.ai/user/repo)")
    parser.add_argument("--output", "-o", help="下载文件的输出目录。默认为 output/<项目名>")
    parser.add_argument("--cookies", "-c", default="cookies.txt", help="Cookie 文件路径 (私有仓库需要)")
    parser.add_argument("--selector", default="main", help="主内容的 CSS 选择器 (默认: 'main')")
    parser.add_argument("--exclude", default="nav,footer,header,aside", help="要排除的 CSS 选择器，用逗号分隔 (默认: 'nav,footer,header,aside')")
    parser.add_argument("--delay", type=float, default=2.0, help="每页下载后的延迟秒数 (默认: 2.0)")
    
    args = parser.parse_args()

    # 智能查找 cookies.txt: 如果当前目录没找到，尝试在脚本所在目录查找
    if args.cookies == "cookies.txt" and not os.path.exists(args.cookies):
        script_dir = Path(__file__).resolve().parent
        potential_path = script_dir / "cookies.txt"
        if potential_path.exists():
            args.cookies = str(potential_path)
            print(f"ℹ️ 在脚本目录下找到 Cookie 文件: {args.cookies}")

    # 确定输出目录
    output_dir = args.output
    if not output_dir:
        # 从模式中提取仓库名 (例如 /user/repo -> repo)
        repo_path = extract_repo_path(args.repo_url)
        repo_name = repo_path.strip('/').split('/')[-1] if repo_path else "unknown_repo"
        output_dir = os.path.join("output", repo_name)
    else:
        repo_path = extract_repo_path(args.repo_url)
    
    # 准备目录
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    print(f"输出目录: {output_dir}")
        
    # 加载 Cookie
    cookies = []
    if os.path.exists(args.cookies):
        with open(args.cookies, "r", encoding="utf-8") as f:
            cookie_str = f.read().strip()
            cookies = parse_cookie_string(cookie_str)
        print(f"✅ 从 {args.cookies} 加载了 {len(cookies)} 个 Cookie")
    else:
        print(f"⚠️ 警告: 未找到 Cookie 文件 '{args.cookies}'。可能无法访问私有仓库。")

    # 配置浏览器
    user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    browser_config = BrowserConfig(
        headless=True,
        user_agent=user_agent,
        cookies=cookies
    )
    
    # 从仓库 URL 推导目标模式
    # 例如: https://zread.ai/user/repo -> /user/repo
    target_pattern = extract_repo_path(args.repo_url)
    parsed_repo = urlparse(args.repo_url)
    base_url = f"{parsed_repo.scheme}://{parsed_repo.netloc}"
    
    print(f"目标仓库: {args.repo_url}")
    print(f"匹配模式: {target_pattern}")
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # 步骤 1: 获取并分析菜单
        print("\n步骤 1: 正在获取菜单...")
        menu_html = await fetch_page_html(crawler, args.repo_url)
        
        if not menu_html:
            print("❌ 无法获取菜单页面。中止。")
            return

        menu_items = parse_menu_links(menu_html, base_url, target_pattern)
        
        if not menu_items:
            print("❌ 未找到菜单项。请检查 URL 或 Cookie。")
            # 回退: 询问用户是否尝试本地文件？(为简化 CLI 暂时跳过)
            return
            
        print(f"\n✅ 识别到 {len(menu_items)} 个页面待下载。")
        
        # 步骤 2: 下载文档
        print("\n步骤 2: 正在下载文档...")
        for i, item in enumerate(menu_items):
            print(f"[{i+1}/{len(menu_items)}] {item['text']}")
            await download_doc(
                crawler,
                item['url'],
                output_dir,
                repo_path=target_pattern,
                css_selector=args.selector,
                excluded_selector=args.exclude
            )
            await asyncio.sleep(args.delay)  # 礼貌延迟
            
    print("\n🎉 所有任务已完成。")

if __name__ == "__main__":
    asyncio.run(main())
