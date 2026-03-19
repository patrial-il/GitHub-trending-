#!/usr/bin/env python3
"""
GitHub Trending Repository Scraper
爬取 GitHub Trending 页面的 top_k 仓库信息
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import json
import pprint
from trending_cache import TrendingCache


@dataclass
class Repository:
    """仓库信息数据类"""
    rank: int
    name: str
    url: str
    description: Optional[str]
    language: Optional[str]
    stars_today: Optional[str]
    total_stars: Optional[str]
    zread_link: Optional[str] = None

    def __post_init__(self):
        """初始化 zread 链接"""
        if self.url and not self.zread_link:
            self.zread_link = self.url.replace('github.com', 'zread.ai')


class GitHubTrendingScraper:
    """GitHub Trending 爬虫"""

    BASE_URL = "https://github.com/trending"

    def __init__(self, timeout: int = 10, cache_enabled: bool = True):
        """
        初始化爬虫

        Args:
            timeout: 请求超时时间（秒）
            cache_enabled: 是否启用缓存
        """
        self.timeout = timeout
        self.cache_enabled = cache_enabled
        self.cache = TrendingCache() if cache_enabled else None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    async def fetch_trending_page(
        self,
        language: str = "",
        spoken_language: str = "",
        since: str = "daily"
    ) -> Optional[str]:
        """
        获取 Trending 页面 HTML

        Args:
            language: 编程语言（如'python','javascript'等），留空表示所有语言
            spoken_language: 仓库语言（如'zh','en'等），留空表示所有
            since: 时间范围（'daily', 'weekly', 'monthly'）

        Returns:
            页面 HTML 内容，或 None 表示请求失败
        """
        params = {}
        if language:
            params['spoken_language_code'] = language
        if spoken_language:
            params['spoken_language_code'] = spoken_language
        if since:
            params['since'] = since

        try:
            timeout_config = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout_config) as session:
                async with session.get(
                    self.BASE_URL,
                    headers=self.headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        print(f"❌ 请求失败，状态码：{response.status}")
                        return None
        except asyncio.TimeoutError:
            print(f"❌ 请求超时（{self.timeout}s）")
            return None
        except Exception as e:
            print(f"❌ 请求异常：{e}")
            return None

    def parse_html(self, html: str, top_k: int = None) -> List[Repository]:
        """
        解析 HTML 并提取仓库信息

        Args:
            html: 页面 HTML 内容
            top_k: 只保留前 k 个仓库，None 表示全部

        Returns:
            Repository 对象列表
        """
        soup = BeautifulSoup(html, 'html.parser')
        repositories = []

        # 找到所有仓库项
        repo_items = soup.find_all('article', class_='Box-row')

        for rank, item in enumerate(repo_items, 1):
            try:
                # 仓库名和 URL
                repo_link = item.find('h2', class_='h3').find('a')
                if not repo_link:
                    continue

                repo_name = repo_link.get('href', '').strip('/')
                repo_url = 'https://github.com' + repo_link.get('href', '')

                # 描述
                description_elem = item.find('p', class_='col-9')
                description = description_elem.text.strip() if description_elem else None

                # 编程语言
                language_elem = item.find('span', attrs={'itemprop': 'programmingLanguage'})
                language = language_elem.text.strip() if language_elem else None

                # 获取统计信息容器
                stat_items = item.find_all('span', class_='d-inline-block float-sm-right')

                stars_today = None
                total_stars = None

                for stat_item in stat_items:
                    text = stat_item.text.strip()

                    # 今日 stars
                    if 'star' in text.lower() and 'today' in text.lower():
                        stars_today = text.replace('\n', ' ').strip()

                    # 总 stars
                    elif text.isdigit() or (text.replace(',', '').isdigit()):
                        total_stars = text

                # 尝试从其他位置获取统计数据
                if not total_stars:
                    star_link = item.find('a', href=lambda x: x and '/stargazers' in x)
                    if star_link:
                        total_stars = star_link.text.strip()

                # 创建 Repository 对象
                repo = Repository(
                    rank=rank,
                    name=repo_name,
                    url=repo_url,
                    description=description,
                    language=language,
                    stars_today=stars_today,
                    total_stars=total_stars
                )
                repositories.append(repo)

            except Exception as e:
                print(f"⚠️  解析第{rank}项时出错：{e}")
                continue

        # 只返回 top_k
        if top_k:
            repositories = repositories[:top_k]

        return repositories

    def format_output(self, repositories: List[Repository]) -> str:
        """格式化输出仓库信息"""
        output = f"\n{'='*80}\n"
        output += f"GitHub Trending - {len(repositories)} 个仓库\n"
        output += f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        output += f"{'='*80}\n\n"

        for repo in repositories:
            output += f"#{repo.rank}. {repo.name}\n"
            output += f"   🔗 {repo.url}\n"
            output += f"   📖 ZRead: {repo.zread_link}\n"
            if repo.description:
                output += f"   📝 {repo.description}\n"
            if repo.language:
                output += f"   💻 Language: {repo.language}\n"
            if repo.total_stars:
                output += f"   ⭐ Total Stars: {repo.total_stars}\n"
            if repo.stars_today:
                output += f"   🔥 Today: {repo.stars_today}\n"
            output += "\n"

        return output

    def to_json(self, repositories: List[Repository]) -> str:
        """转换为 JSON 格式"""
        data = [
            {
                'rank': repo.rank,
                'name': repo.name,
                'url': repo.url,
                'description': repo.description,
                'language': repo.language,
                'stars_today': repo.stars_today,
                'total_stars': repo.total_stars,
                'zread_link': repo.zread_link
            }
            for repo in repositories
        ]
        return json.dumps(data, ensure_ascii=False, indent=2)

    async def scrape(
        self,
        top_k: int = 10,
        language: str = "",
        since: str = "daily",
        output_json: bool = False,
        force_update: bool = False
    ) -> List[Repository]:
        """
        爬取 GitHub Trending（带缓存）

        Args:
            top_k: 获取前 k 个仓库
            language: 编程语言筛选
            since: 时间范围（'daily', 'weekly', 'monthly'）
            output_json: 是否输出 JSON 格式
            force_update: 是否强制更新缓存

        Returns:
            Repository 对象列表
        """
        # 检查缓存
        if self.cache_enabled and not force_update:
            cached_data = self.cache.load_today()
            if cached_data:
                print(f"📦 使用缓存数据 ({self.cache._get_cache_date_key()})")
                # 从缓存恢复 Repository 对象
                repositories = [Repository(**item) for item in cached_data]
                if output_json:
                    print(self.to_json(repositories))
                else:
                    print(self.format_output(repositories))
                return repositories

            # 检查是否有昨天的缓存（隔天情况）
            latest_data = self.cache.load_latest()
            if latest_data:
                print(f"⚠️  今天缓存不存在，使用最新缓存数据")

        print(f"🚀 开始爬取 GitHub Trending (top_{top_k})...")
        print(f"   语言：{language or '全部'}")
        print(f"   时间：{since}")

        # 获取页面
        html = await self.fetch_trending_page(language=language, since=since)
        if not html:
            print("❌ 无法获取页面内容")
            return []

        # 解析页面
        print("📊 正在解析页面...")
        repositories = self.parse_html(html, top_k=top_k)

        if not repositories:
            print("❌ 未找到仓库信息")
            return []

        print(f"✅ 成功获取 {len(repositories)} 个仓库\n")

        # 保存到缓存
        if self.cache_enabled:
            self.cache.save(repositories, metadata={
                'language': language,
                'since': since,
                'top_k': top_k
            })

        # 输出结果
        if output_json:
            output = self.to_json(repositories)
            print(output)
        else:
            output = self.format_output(repositories)
            print(output)

        return repositories

    def get_cache_info(self):
        """获取缓存状态信息"""
        if not self.cache_enabled:
            print("缓存已禁用")
            return None
        info = self.cache.get_cache_info()
        print("📊 缓存状态:")
        print(f"   今天缓存：{'存在' if info['today_cache_exists'] else '不存在'}")
        print(f"   昨天缓存：{'存在' if info['yesterday_cache_exists'] else '不存在'}")
        print(f"   需要更新：{'是' if info['should_update'] else '否'}")
        if info.get('today_cache_repo_count'):
            print(f"   缓存仓库数：{info['today_cache_repo_count']}")
        return info


async def get_github_trending_main():
    """主函数 - 示例使用"""
    # 启用缓存（默认）
    scraper = GitHubTrendingScraper(cache_enabled=True)

    # 显示缓存状态
    scraper.get_cache_info()
    print()

    # 示例 1: 获取今日全部语言 top 10（带缓存）
    repositories = await scraper.scrape(top_k=10, since='daily', output_json=True)

    # 强制更新缓存示例（取消注释使用）
    # repositories = await scraper.scrape(top_k=10, since='daily', output_json=True, force_update=True)

    # 禁用缓存示例（取消注释使用）
    # scraper_no_cache = GitHubTrendingScraper(cache_enabled=False)
    # repositories = await scraper_no_cache.scrape(top_k=10, since='daily', output_json=True)


if __name__ == '__main__':
    asyncio.run(get_github_trending_main())
