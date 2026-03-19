#!/usr/bin/env python3
"""
GitHub Trending 缓存管理模块
为每天的 GitHub trending repositories 创建缓存，隔天更新缓存
"""

import json
import os
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import asdict


class TrendingCache:
    """GitHub Trending 缓存管理器"""

    def __init__(self, cache_dir: str = "cache"):
        """
        初始化缓存管理器

        Args:
            cache_dir: 缓存目录路径
        """
        self.cache_dir = cache_dir
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _get_cache_date_key(self) -> str:
        """获取缓存日期的键值（格式：YYYYMMDD）"""
        return date.today().strftime("%Y%m%d")

    def _get_cache_file_path(self, cache_key: Optional[str] = None) -> str:
        """
        获取缓存文件路径

        Args:
            cache_key: 缓存键（日期），None 表示使用今天

        Returns:
            缓存文件完整路径
        """
        if cache_key is None:
            cache_key = self._get_cache_date_key()
        return os.path.join(self.cache_dir, f"github_trending_{cache_key}.json")

    def _get_yesterday_date_key(self) -> str:
        """获取昨天的日期键值"""
        yesterday = date.today() - timedelta(days=1)
        return yesterday.strftime("%Y%m%d")

    def load_today(self) -> Optional[List[Dict[str, Any]]]:
        """
        加载今天的缓存数据

        Returns:
            缓存数据（仓库列表），如果缓存不存在则返回 None
        """
        cache_file = self._get_cache_file_path()
        if not os.path.exists(cache_file):
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('repositories')
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  读取缓存失败：{e}")
            return None

    def load_latest(self) -> Optional[List[Dict[str, Any]]]:
        """
        加载最新的缓存数据（今天或昨天）

        Returns:
            最新的缓存数据，如果没有则返回 None
        """
        # 先尝试加载今天的缓存
        today_data = self.load_today()
        if today_data:
            return today_data

        # 今天没有缓存，尝试加载昨天的
        yesterday_key = self._get_yesterday_date_key()
        cache_file = self._get_cache_file_path(yesterday_key)
        if not os.path.exists(cache_file):
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('repositories')
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  读取昨天缓存失败：{e}")
            return None

    def save(self, repositories: List[Any], metadata: Optional[Dict[str, Any]] = None):
        """
        保存数据到今天的缓存文件

        Args:
            repositories: 仓库数据列表（Repository 对象列表或字典列表）
            metadata: 额外的元数据
        """
        cache_file = self._get_cache_file_path()

        # 转换数据为字典格式
        repo_dicts = []
        for repo in repositories:
            if hasattr(repo, '__dataclass_fields__'):
                repo_dicts.append(asdict(repo))
            elif isinstance(repo, dict):
                repo_dicts.append(repo)
            else:
                repo_dicts.append(repo.__dict__ if hasattr(repo, '__dict__') else str(repo))

        cache_data = {
            'cache_date': self._get_cache_date_key(),
            'created_at': datetime.now().isoformat(),
            'repositories': repo_dicts,
            'metadata': metadata or {}
        }

        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            print(f"✅ 缓存已保存：{cache_file}")
        except IOError as e:
            print(f"❌ 保存缓存失败：{e}")

    def should_update(self) -> bool:
        """
        检查是否需要更新缓存

        Returns:
            True 表示需要更新（今天还没有缓存或已隔天）
            False 表示可以使用现有缓存
        """
        # 检查今天的缓存是否存在
        today_file = self._get_cache_file_path()
        if not os.path.exists(today_file):
            return True

        # 检查缓存日期，如果是昨天的缓存，今天需要更新
        try:
            with open(today_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cached_date = data.get('cache_date')
                today_key = self._get_cache_date_key()
                return cached_date != today_key
        except (json.JSONDecodeError, IOError):
            return True

    def is_fresh(self) -> bool:
        """
        检查缓存是否是今天的（未隔天）

        Returns:
            True 表示缓存是今天的，False 表示已隔天或不存在
        """
        today_file = self._get_cache_file_path()
        if not os.path.exists(today_file):
            return False

        try:
            with open(today_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cached_date = data.get('cache_date')
                return cached_date == self._get_cache_date_key()
        except (json.JSONDecodeError, IOError):
            return False

    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存信息

        Returns:
            包含缓存状态信息的字典
        """
        today_key = self._get_cache_date_key()
        yesterday_key = self._get_yesterday_date_key()
        today_file = self._get_cache_file_path(today_key)
        yesterday_file = self._get_cache_file_path(yesterday_key)

        info = {
            'today_cache_exists': os.path.exists(today_file),
            'yesterday_cache_exists': os.path.exists(yesterday_file),
            'today_cache_file': today_file,
            'yesterday_cache_file': yesterday_file,
            'should_update': self.should_update()
        }

        # 读取今天的缓存元数据
        if os.path.exists(today_file):
            try:
                with open(today_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    info['today_cache_created'] = data.get('created_at')
                    info['today_cache_repo_count'] = len(data.get('repositories', []))
            except (json.JSONDecodeError, IOError):
                pass

        return info

    def cleanup_old_cache(self, keep_days: int = 10):
        """
        清理旧缓存文件

        Args:
            keep_days: 保留最近多少天的缓存（默认 10 天）
        """
        if not os.path.exists(self.cache_dir):
            return

        cutoff_date = date.today() - timedelta(days=keep_days)
        cutoff_key = cutoff_date.strftime("%Y%m%d")

        for filename in os.listdir(self.cache_dir):
            if filename.startswith('github_trending_') and filename.endswith('.json'):
                # 提取日期键值
                date_key = filename.replace('github_trending_', '').replace('.json', '')
                if date_key < cutoff_key:
                    file_path = os.path.join(self.cache_dir, filename)
                    os.remove(file_path)
                    print(f"🗑️  已删除旧缓存：{filename}")


# 便捷函数
def get_trending_from_cache_or_fetch(
    fetch_func,
    cache: Optional[TrendingCache] = None,
    force_update: bool = False
) -> List[Dict[str, Any]]:
    """
    从缓存获取 trending 数据，如果没有则调用 fetch_func 获取并缓存

    Args:
        fetch_func: 异步函数，用于获取 trending 数据
        cache: TrendingCache 实例，None 则创建默认实例
        force_update: 是否强制更新

    Returns:
        仓库数据列表
    """
    import asyncio

    if cache is None:
        cache = TrendingCache()

    # 检查是否需要更新
    if not force_update and not cache.should_update():
        cached_data = cache.load_today()
        if cached_data:
            print(f"📦 使用缓存数据 ({cache._get_cache_date_key()})")
            return cached_data

    # 获取新数据并缓存
    print(f"🔄 获取最新数据...")
    if asyncio.iscoroutinefunction(fetch_func):
        data = asyncio.run(fetch_func())
    else:
        data = fetch_func()

    cache.save(data)
    return data
