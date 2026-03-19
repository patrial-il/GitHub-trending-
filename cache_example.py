#!/usr/bin/env python3
"""
GitHub Trending 缓存使用示例
演示如何使用 trending_cache 模块
"""

import asyncio
from trending_cache import TrendingCache
from get_github_trending import GitHubTrendingScraper


async def example_1_basic_cache():
    """示例 1: 基本缓存使用"""
    print("=" * 60)
    print("示例 1: 基本缓存使用")
    print("=" * 60)

    cache = TrendingCache()

    # 检查是否需要更新
    if cache.should_update():
        print("需要更新缓存，正在获取新数据...")

        # 创建爬虫并获取数据
        scraper = GitHubTrendingScraper()
        repos = await scraper.scrape(top_k=10, output_json=False)

        # 保存到缓存
        cache.save(repos)
        print("✅ 数据已缓存")
    else:
        print("使用缓存数据...")
        data = cache.load_today()
        print(f"从缓存加载了 {len(data)} 个仓库")


async def example_2_scraper_with_cache():
    """示例 2: 使用带缓存的爬虫"""
    print("\n" + "=" * 60)
    print("示例 2: 使用带缓存的爬虫")
    print("=" * 60)

    # 创建带缓存的爬虫（默认启用）
    scraper = GitHubTrendingScraper(cache_enabled=True)

    # 第一次调用：会爬取并缓存
    print("\n--- 第一次调用（爬取并缓存）---")
    await scraper.scrape(top_k=5, since='daily')

    # 第二次调用：直接使用缓存
    print("\n--- 第二次调用（使用缓存）---")
    await scraper.scrape(top_k=5, since='daily')


async def example_3_force_update():
    """示例 3: 强制更新缓存"""
    print("\n" + "=" * 60)
    print("示例 3: 强制更新缓存")
    print("=" * 60)

    scraper = GitHubTrendingScraper(cache_enabled=True)

    # 强制更新，忽略现有缓存
    print("强制更新缓存...")
    await scraper.scrape(top_k=5, since='daily', force_update=True)


async def example_4_cache_info():
    """示例 4: 查看缓存信息"""
    print("\n" + "=" * 60)
    print("示例 4: 查看缓存信息")
    print("=" * 60)

    cache = TrendingCache()
    info = cache.get_cache_info()

    print(f"今天缓存存在：{info['today_cache_exists']}")
    print(f"昨天缓存存在：{info['yesterday_cache_exists']}")
    print(f"需要更新：{info['should_update']}")

    if info.get('today_cache_created'):
        print(f"缓存创建时间：{info['today_cache_created']}")
    if info.get('today_cache_repo_count'):
        print(f"缓存仓库数量：{info['today_cache_repo_count']}")


async def example_5_cleanup_old_cache():
    """示例 5: 清理旧缓存"""
    print("\n" + "=" * 60)
    print("示例 5: 清理 7 天前的旧缓存")
    print("=" * 60)

    cache = TrendingCache()
    cache.cleanup_old_cache(keep_days=7)
    print("清理完成")


async def main():
    """运行所有示例"""
    print("GitHub Trending 缓存使用示例\n")

    # 运行示例
    await example_1_basic_cache()
    await example_2_scraper_with_cache()
    await example_3_force_update()
    await example_4_cache_info()
    await example_5_cleanup_old_cache()

    print("\n" + "=" * 60)
    print("所有示例运行完成!")
    print("=" * 60)


if __name__ == '__main__':
    # 检查是否在 IDE 中运行，如果是则运行单个示例
    import sys
    if len(sys.argv) > 1:
        example_name = sys.argv[1]
        examples = {
            '1': example_1_basic_cache,
            '2': example_2_scraper_with_cache,
            '3': example_3_force_update,
            '4': example_4_cache_info,
            '5': example_5_cleanup_old_cache,
        }
        if example_name in examples:
            asyncio.run(examples[example_name]())
        else:
            print(f"未知示例：{example_name}")
            print("可用示例：1, 2, 3, 4, 5")
    else:
        asyncio.run(main())
