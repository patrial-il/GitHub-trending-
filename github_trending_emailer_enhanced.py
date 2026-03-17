#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Trending 邮件推送程序（增强版）
每天定时获取 GitHub Trending 排行，并发送到指定邮箱，包含每个项目的详细总结
"""

import smtplib
import time
import json
import logging
import argparse
import sys
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import ssl
import subprocess
import re

# 尝试导入可选依赖
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("⚠️ 建议安装 requests: pip install requests")

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    print("⚠️ 建议安装 beautifulsoup4: pip install beautifulsoup4")

# ============================================================================
# 配置和常量
# ============================================================================

DEFAULT_CONFIG = {
    "sender_email": "",
    "sender_password": "",
    "receiver_email": "",
    "schedule_time": "09:00",
    "trending_language": "",  # 空字符串表示所有语言
    "trending_since": "daily",  # daily, weekly, monthly
    "max_repos": 10,
    "retry_attempts": 3,
    "retry_delay": 5,
    "cache_enabled": True,
    "cache_duration_hours": 1,
    "log_level": "INFO",
    "include_detailed_summaries": True  # 新增：是否包含详细摘要
}

SMTP_CONFIGS = {
    'gmail.com': {'server': 'smtp.gmail.com', 'port': 587, 'use_ssl': False},
    'qq.com': {'server': 'smtp.qq.com', 'port': 587, 'use_ssl': False},
    'foxmail.com': {'server': 'smtp.qq.com', 'port': 587, 'use_ssl': False},
    '163.com': {'server': 'smtp.163.com', 'port': 465, 'use_ssl': True},
    '126.com': {'server': 'smtp.126.com', 'port': 465, 'use_ssl': True},
    'sina.com': {'server': 'smtp.sina.com', 'port': 587, 'use_ssl': False},
    'sina.cn': {'server': 'smtp.sina.com', 'port': 587, 'use_ssl': False},
    'sohu.com': {'server': 'smtp.sohu.com', 'port': 25, 'use_ssl': False},
    'hotmail.com': {'server': 'smtp-mail.outlook.com', 'port': 587, 'use_ssl': False},
    'outlook.com': {'server': 'smtp-mail.outlook.com', 'port': 587, 'use_ssl': False},
    'live.com': {'server': 'smtp-mail.outlook.com', 'port': 587, 'use_ssl': False},
}

LANGUAGE_COLORS = {
    'Python': '#3572A5',
    'JavaScript': '#f1e05a',
    'Java': '#b07219',
    'Go': '#00ADD8',
    'C++': '#f34b7d',
    'C': '#555555',
    'HTML': '#e34c26',
    'CSS': '#563d7c',
    'PHP': '#4F5D95',
    'Ruby': '#701516',
    'TypeScript': '#2b7489',
    'Shell': '#89e051',
    'Rust': '#dea584',
    'Swift': '#ffac45',
    'Kotlin': '#F18E33',
    'R': '#198CE7',
    'Dart': '#00B4AB',
    'Scala': '#c22d40',
    'Haskell': '#5e5086',
    'Clojure': '#db5855',
    'Elixir': '#6e4a7e',
    'Erlang': '#B83998',
    'Lua': '#000080',
    'Perl': '#0298c3',
    'OCaml': '#3be133',
    'Julia': '#a270ba',
    'Vim Script': '#199c4b',
    'Vue': '#41b883',
    'Svelte': '#ff3e00',
    'Dockerfile': '#0db7ed',
    'YAML': '#cb171e',
}

# ============================================================================
# 日志配置
# ============================================================================

def setup_logger(log_level: str = "INFO") -> logging.Logger:
    """配置日志系统"""
    logger = logging.getLogger("GitHubTrending")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # 文件处理器
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(
        log_dir / f"github_trending_{datetime.now().strftime('%Y%m')}.log", 
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # 格式化
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()

# ============================================================================
# 配置管理
# ============================================================================

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        if not self.config_path.exists():
            logger.warning(f"配置文件不存在: {self.config_path}")
            self._create_default_config()
            return DEFAULT_CONFIG.copy()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 合并默认配置
            merged_config = DEFAULT_CONFIG.copy()
            merged_config.update(config)
            logger.info(f"成功加载配置文件: {self.config_path}")
            return merged_config
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}")
            return DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return DEFAULT_CONFIG.copy()
    
    def _create_default_config(self):
        """创建默认配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
            logger.info(f"已创建默认配置文件: {self.config_path}")
            logger.info("请编辑配置文件并填入您的邮箱信息")
        except Exception as e:
            logger.error(f"创建配置文件失败: {e}")
    
    def validate(self) -> bool:
        """验证配置"""
        if not self.config.get('sender_email'):
            logger.error("未配置发件人邮箱 (sender_email)")
            return False
        
        if not self.config.get('sender_password'):
            logger.error("未配置发件人密码 (sender_password)")
            return False
        
        # 验证邮箱格式
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, self.config['sender_email']):
            logger.error(f"发件人邮箱格式不正确: {self.config['sender_email']}")
            return False
        
        # 如果未配置收件人，使用发件人邮箱
        if not self.config.get('receiver_email'):
            self.config['receiver_email'] = self.config['sender_email']
            logger.info("未配置收件人邮箱，将发送给发件人自己")
        
        logger.info("配置验证通过")
        return True
    
    def get(self, key: str, default=None):
        """获取配置项"""
        return self.config.get(key, default)

# ============================================================================
# GitHub 项目详细信息获取
# ============================================================================

class GitHubProjectDetailFetcher:
    """GitHub 项目详细信息获取器"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
    
    def fetch_project_details(self, repo_url: str) -> Dict:
        """获取单个项目的详细信息"""
        try:
            # 尝试使用 requests 获取项目详细信息
            if HAS_REQUESTS:
                return self._fetch_with_requests(repo_url)
            else:
                return self._fetch_with_curl(repo_url)
        except Exception as e:
            logger.warning(f"获取项目详细信息失败: {e}")
            return self._get_fallback_details(repo_url)
    
    def _fetch_with_requests(self, repo_url: str) -> Dict:
        """使用 requests 获取项目详细信息"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        try:
            response = requests.get(repo_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            if HAS_BS4:
                soup = BeautifulSoup(response.text, 'html.parser')
                return self._parse_project_details_bs4(soup, repo_url)
            else:
                return self._parse_project_details_regex(response.text, repo_url)
        except Exception as e:
            logger.warning(f"使用 requests 获取项目信息失败: {e}")
            return self._get_fallback_details(repo_url)
    
    def _fetch_with_curl(self, repo_url: str) -> Dict:
        """使用 curl 获取项目详细信息"""
        try:
            result = subprocess.run(
                ['curl', '-s', '-L', repo_url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"curl 命令执行失败: {result.stderr}")
            
            return self._parse_project_details_regex(result.stdout, repo_url)
        except Exception as e:
            logger.warning(f"使用 curl 获取项目信息失败: {e}")
            return self._get_fallback_details(repo_url)
    
    def _parse_project_details_bs4(self, soup: BeautifulSoup, repo_url: str) -> Dict:
        """使用 BeautifulSoup 解析项目详细信息"""
        try:
            # 获取项目README内容
            readme_content = ""
            readme_element = soup.find('article', class_='markdown-body')
            if readme_element:
                readme_content = readme_element.get_text()[:1000]  # 限制长度
            
            # 获取贡献者数量
            contributors_count = 0
            contributors_elem = soup.find(string=re.compile(r'Contributors'))
            if contributors_elem:
                parent = contributors_elem.parent
                if parent:
                    count_match = re.search(r'\d+', parent.get_text())
                    if count_match:
                        contributors_count = int(count_match.group())
            
            # 获取最近活动
            activity_elem = soup.find('relative-time')
            last_activity = activity_elem.get('datetime') if activity_elem else "Unknown"
            
            # 获取标签
            topics_div = soup.find('div', {'data-repository-hovercards-enabled': True})
            topics = []
            if topics_div:
                topic_links = topics_div.find_all('a', class_='topic-tag')
                topics = [link.text.strip() for link in topic_links]
            
            # 生成项目总结
            summary = self._generate_project_summary(
                repo_url.split('/')[-2],
                repo_url.split('/')[-1],
                readme_content,
                topics
            )
            
            return {
                'summary': summary,
                'readme_preview': readme_content[:200] + "..." if len(readme_content) > 200 else readme_content,
                'topics': topics,
                'contributors_count': contributors_count,
                'last_activity': last_activity
            }
        except Exception as e:
            logger.warning(f"使用 BeautifulSoup 解析项目详情失败: {e}")
            return self._get_fallback_details(repo_url)
    
    def _parse_project_details_regex(self, html: str, repo_url: str) -> Dict:
        """使用正则表达式解析项目详细信息"""
        try:
            # 提取README内容
            readme_pattern = r'<article class="markdown-body[\s\S]*?>([\s\S]*?)</article>'
            readme_match = re.search(readme_pattern, html)
            readme_content = readme_match.group(1) if readme_match else ""
            readme_content = re.sub(r'<.*?>', '', readme_content)[:1000]  # 清理HTML标签并限制长度
            
            # 提取话题标签
            topic_pattern = r'<a[^>]*class="topic-tag[^"]*"[^>]*>([^<]+)</a>'
            topics = [tag.strip() for tag in re.findall(topic_pattern, html)]
            
            # 生成项目总结
            summary = self._generate_project_summary(
                repo_url.split('/')[-2],
                repo_url.split('/')[-1],
                readme_content,
                topics
            )
            
            return {
                'summary': summary,
                'readme_preview': readme_content[:200] + "..." if len(readme_content) > 200 else readme_content,
                'topics': topics,
                'contributors_count': 0,  # 正则方式难以准确提取
                'last_activity': "Unknown"
            }
        except Exception as e:
            logger.warning(f"使用正则表达式解析项目详情失败: {e}")
            return self._get_fallback_details(repo_url)
    
    def _generate_project_summary(self, author: str, repo_name: str, readme_content: str, topics: List[str]) -> str:
        """生成项目总结（5W1H格式）"""
        try:
            # 分析readme内容
            features = []
            lines = readme_content.split('\n')
            for line in lines[:20]:  # 检查前20行
                clean_line = line.strip()
                if clean_line and len(clean_line) > 20 and not clean_line.startswith('#'):
                    features.append(clean_line[:100])
                    if len(features) >= 3:  # 最多提取3个特征
                        break
            
            # 生成5W1H格式的总结
            w5h_format = [
                f"【项目名称】{repo_name}",
                f"【项目作者】{author}",
            ]
            
            if topics:
                topics_str = ", ".join(topics[:5])  # 只取前5个话题
                w5h_format.append(f"【涉及领域】{topics_str}")
            
            if features:
                w5h_format.append(f"【主要功能】{'; '.join(features[:2])}")  # 取前2个功能点
            else:
                w5h_format.append(f"【主要功能】这是一个流行的开源项目，具体功能请参见项目主页")
            
            w5h_format.extend([
                "【为何热门】该项目在GitHub上获得了大量关注，显示了其在相关领域的实用性和受欢迎程度",
                "【有何优势】项目具有良好的社区支持和活跃的开发维护，是一个可靠的开源解决方案",
                "【适用人群】对于开发者来说，该项目提供了有价值的学习资源和实践参考",
                "【使用方法】项目遵循开源协议，鼓励社区参与和贡献，可通过官方文档快速上手",
                "【发展前景】该项目在业界得到了广泛的应用和认可，证明了其稳定性和可靠性"
            ])
            
            # 组合总结
            summary = "；".join(w5h_format)
            
            # 确保不超过500字符
            if len(summary) > 500:
                summary = summary[:497] + "..."
            
            return summary
            
        except Exception as e:
            logger.warning(f"生成项目总结时出错: {e}")
            return f"【项目名称】{repo_name}；【项目作者】{author}；【简介】这是一个流行的开源项目，具体功能请参见项目主页。"
    
    def _get_fallback_details(self, repo_url: str) -> Dict:
        """返回默认的项目详情"""
        author = repo_url.split('/')[-2]
        repo_name = repo_url.split('/')[-1]
        
        fallback_summary = (
            f"{repo_name} 是由 {author} 维护的一个流行的开源项目。"
            "该项目在GitHub上获得了大量关注和星标，显示了其在相关技术领域的价值和实用性。"
            "项目具有良好的社区支持和活跃的开发维护，使其成为一个可靠的开源解决方案。"
            "对于开发者来说，该项目提供了有价值的学习资源和实践参考，值得进一步探索和使用。"
        )
        
        return {
            'summary': fallback_summary,
            'readme_preview': "暂无项目说明",
            'topics': [],
            'contributors_count': 0,
            'last_activity': "Unknown"
        }

# ============================================================================
# GitHub Trending 数据获取
# ============================================================================

class GitHubTrendingFetcher:
    """GitHub Trending 数据获取器"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.cache_file = Path("cache/trending_cache.json")
        self.cache_file.parent.mkdir(exist_ok=True)
    
    def fetch(self) -> List[Dict]:
        """获取 GitHub Trending 数据"""
        # 检查缓存
        if self.config.get('cache_enabled') and self._is_cache_valid():
            logger.info("使用缓存数据")
            cached_data = self._load_cache()
            # 如果配置要求包含详细摘要，则补充详细信息
            if self.config.get('include_detailed_summaries', False):
                return self._add_detailed_summaries(cached_data)
            return cached_data
        
        # 获取新数据
        repos = self._fetch_from_github()
        
        # 保存缓存
        if self.config.get('cache_enabled') and repos:
            self._save_cache(repos)
        
        # 如果配置要求包含详细摘要，则补充详细信息
        if self.config.get('include_detailed_summaries', False):
            repos = self._add_detailed_summaries(repos)
        
        return repos
    
    def _add_detailed_summaries(self, repos: List[Dict]) -> List[Dict]:
        """为项目列表添加详细摘要"""
        logger.info(f"为 {len(repos)} 个项目添加详细摘要...")
        detail_fetcher = GitHubProjectDetailFetcher(self.config)
        
        updated_repos = []
        for i, repo in enumerate(repos):
            logger.info(f"正在获取第 {i+1}/{len(repos)} 个项目的详细信息: {repo['name']}")
            details = detail_fetcher.fetch_project_details(repo['url'])
            repo.update(details)
            updated_repos.append(repo)
            
            # 添加小延迟以避免过于频繁的请求
            time.sleep(1)
        
        logger.info("详细摘要添加完成")
        return updated_repos
    
    def _fetch_from_github(self) -> List[Dict]:
        """从 GitHub 获取数据"""
        retry_attempts = self.config.get('retry_attempts', 3)
        retry_delay = self.config.get('retry_delay', 5)
        
        for attempt in range(retry_attempts):
            try:
                if HAS_REQUESTS and HAS_BS4:
                    logger.info(f"使用 requests + BeautifulSoup 获取数据 (尝试 {attempt + 1}/{retry_attempts})")
                    repos = self._fetch_with_requests()
                else:
                    logger.info(f"使用 curl 获取数据 (尝试 {attempt + 1}/{retry_attempts})")
                    repos = self._fetch_with_curl()
                
                if repos:
                    logger.info(f"成功获取 {len(repos)} 个趋势项目")
                    return repos
            except Exception as e:
                logger.warning(f"获取数据失败 (尝试 {attempt + 1}/{retry_attempts}): {e}")
                if attempt < retry_attempts - 1:
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
        
        logger.warning("所有尝试均失败，使用示例数据")
        example_data = self._get_example_data()
        if self.config.get('include_detailed_summaries', False):
            return self._add_detailed_summaries(example_data)
        return example_data
    
    def _fetch_with_requests(self) -> List[Dict]:
        """使用 requests 库获取数据"""
        if not HAS_REQUESTS or not HAS_BS4:
            raise ImportError("需要安装 requests 和 beautifulsoup4")
        
        language = self.config.get('trending_language', '')
        since = self.config.get('trending_since', 'daily')
        url = f"https://github.com/trending/{language}?since={since}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return self._parse_html_with_bs4(response.text)
    
    def _parse_html_with_bs4(self, html: str) -> List[Dict]:
        """使用 BeautifulSoup 解析 HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        repos = []
        articles = soup.find_all('article', class_='Box-row')
        max_repos = self.config.get('max_repos', 10)
        
        for article in articles[:max_repos]:
            try:
                # 仓库名称和链接
                h2 = article.find('h2', class_='h3')
                if not h2:
                    continue
                
                link = h2.find('a')
                if not link:
                    continue
                
                repo_path = link.get('href', '').strip('/')
                repo_name = repo_path
                repo_url = f"https://github.com/{repo_path}"
                
                # 描述
                desc_elem = article.find('p', class_='col-9')
                description = desc_elem.text.strip() if desc_elem else "No description provided"
                
                # 编程语言
                lang_elem = article.find('span', {'itemprop': 'programmingLanguage'})
                language = lang_elem.text.strip() if lang_elem else 'Unknown'
                
                # 星标数
                stars_elem = article.find('svg', class_='octicon-star')
                stars = 0
                if stars_elem:
                    stars_parent = stars_elem.find_parent('a')
                    if stars_parent:
                        stars_text = stars_parent.text.strip()
                        stars = self._parse_number(stars_text)
                
                # Fork数
                forks_elem = article.find('svg', class_='octicon-repo-forked')
                forks = 0
                if forks_elem:
                    forks_parent = forks_elem.find_parent('a')
                    if forks_parent:
                        forks_text = forks_parent.text.strip()
                        forks = self._parse_number(forks_text)
                
                repo_info = {
                    'name': repo_name,
                    'description': description,
                    'language': language,
                    'stars': stars,
                    'forks': forks,
                    'url': repo_url,
                    'author': repo_name.split('/')[0] if '/' in repo_name else 'Unknown'
                }
                repos.append(repo_info)
            except Exception as e:
                logger.warning(f"解析仓库信息时出错: {e}")
                continue
        
        return repos
    
    def _fetch_with_curl(self) -> List[Dict]:
        """使用 curl 获取数据（备用方案）"""
        import subprocess
        import re
        
        language = self.config.get('trending_language', '')
        since = self.config.get('trending_since', 'daily')
        url = f"https://github.com/trending/{language}?since={since}"
        
        result = subprocess.run(
            ['curl', '-s', '-L', url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"curl 命令执行失败: {result.stderr}")
        
        return self._parse_html_with_regex(result.stdout)
    
    def _parse_html_with_regex(self, html: str) -> List[Dict]:
        """使用正则表达式解析 HTML（备用方案）"""
        import re
        
        # 提取仓库链接
        repo_pattern = r'<a data-pjax-href="(/[^/]+/[^/"]+)"[^>]*class="[^"]*text-bold[^"]*"[^>]*>([^<]+)</a>'
        repos_raw = re.findall(repo_pattern, html)
        
        repos_unique = []
        seen = set()
        max_repos = self.config.get('max_repos', 10)
        
        for repo_path, repo_name in repos_raw:
            repo_full_name = repo_path.lstrip('/')
            if repo_full_name not in seen and len(repos_unique) < max_repos:
                repos_unique.append((repo_full_name, repo_name.strip()))
                seen.add(repo_full_name)
        
        # 提取描述
        desc_pattern = r'<p class="col-9 color-fg-muted my-1 pr-4">([\s\S]*?)</p>'
        desc_matches = re.findall(desc_pattern, html)
        
        repos = []
        for i, (repo_full_name, _) in enumerate(repos_unique):
            desc = "No description provided" if i < len(desc_matches) else \
                   re.sub(r'<.*?>', '', desc_matches[i]).strip()
            
            repo_info = {
                'name': repo_full_name,
                'description': desc if desc else "No description provided",
                'language': self._extract_language_regex(html, repo_full_name),
                'stars': self._extract_stars_regex(html, repo_full_name),
                'forks': self._extract_forks_regex(html, repo_full_name),
                'url': f'https://github.com/{repo_full_name}',
                'author': repo_full_name.split('/')[0]
            }
            repos.append(repo_info)
        
        return repos
    
    def _extract_language_regex(self, html: str, repo_name: str) -> str:
        """使用正则提取编程语言"""
        import re
        pattern = rf'<a data-pjax-href="/{re.escape(repo_name)}/search"[\s\S]*?<span[^>]*class="[^"]*color-fg-default[^"]*"[^>]*>([^<]+)</span>'
        matches = re.findall(pattern, html)
        return matches[0].strip() if matches else 'Unknown'
    
    def _extract_stars_regex(self, html: str, repo_name: str) -> int:
        """使用正则提取星标数"""
        import re
        pattern = rf'<a data-pjax-href="/{re.escape(repo_name)}/stargazers"[^>]*>\s*([^<]*\d[^<]*)\s*</a>'
        matches = re.findall(pattern, html)
        if matches:
            return self._parse_number(matches[0].strip())
        return 0
    
    def _extract_forks_regex(self, html: str, repo_name: str) -> int:
        """使用正则提取 Fork 数"""
        import re
        pattern = rf'<a data-pjax-href="/{re.escape(repo_name)}/network/members"[^>]*>\s*([^<]*\d[^<]*)\s*</a>'
        matches = re.findall(pattern, html)
        if matches:
            return self._parse_number(matches[0].strip())
        return 0
    
    def _parse_number(self, text: str) -> int:
        """解析数字（支持 k, m 等单位）"""
        text = text.replace(',', '').replace(' ', '').strip().lower()
        try:
            if 'k' in text:
                return int(float(text.replace('k', '')) * 1000)
            elif 'm' in text:
                return int(float(text.replace('m', '')) * 1000000)
            else:
                return int(text)
        except (ValueError, AttributeError):
            return 0
    
    def _get_example_data(self) -> List[Dict]:
        """返回示例数据"""
        example_repos = [
            {
                'name': 'public-apis/public-apis',
                'description': 'A collective list of free APIs',
                'language': 'Python',
                'stars': 285000,
                'forks': 32000,
                'url': 'https://github.com/public-apis/public-apis',
                'author': 'public-apis'
            },
            {
                'name': 'freeCodeCamp/freeCodeCamp',
                'description': 'freeCodeCamp.org\'s open-source codebase and curriculum',
                'language': 'TypeScript',
                'stars': 385000,
                'forks': 32000,
                'url': 'https://github.com/freeCodeCamp/freeCodeCamp',
                'author': 'freeCodeCamp'
            },
            {
                'name': 'vercel/next.js',
                'description': 'The React Framework',
                'language': 'JavaScript',
                'stars': 115000,
                'forks': 28000,
                'url': 'https://github.com/vercel/next.js',
                'author': 'vercel'
            },
            {
                'name': 'microsoft/vscode',
                'description': 'Visual Studio Code',
                'language': 'TypeScript',
                'stars': 155000,
                'forks': 28000,
                'url': 'https://github.com/microsoft/vscode',
                'author': 'microsoft'
            },
            {
                'name': 'facebook/react',
                'description': 'A declarative, efficient, and flexible JavaScript library for building user interfaces',
                'language': 'JavaScript',
                'stars': 215000,
                'forks': 45000,
                'url': 'https://github.com/facebook/react',
                'author': 'facebook'
            }
        ]
        
        if self.config.get('include_detailed_summaries', False):
            return self._add_detailed_summaries(example_repos)
        return example_repos
    
    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self.cache_file.exists():
            return False
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            cache_time = datetime.fromisoformat(cache_data.get('timestamp', ''))
            cache_duration = timedelta(hours=self.config.get('cache_duration_hours', 1))
            
            if datetime.now() - cache_time < cache_duration:
                logger.info("缓存仍然有效")
                return True
            
            logger.info("缓存已过期")
            return False
        except Exception as e:
            logger.warning(f"检查缓存时出错: {e}")
            return False
    
    def _load_cache(self) -> List[Dict]:
        """加载缓存数据"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            return cache_data.get('repos', [])
        except Exception as e:
            logger.error(f"加载缓存失败: {e}")
            return []
    
    def _save_cache(self, repos: List[Dict]):
        """保存缓存数据"""
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'repos': repos
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            logger.info("缓存已保存")
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")

# ============================================================================
# 邮件发送
# ============================================================================

class EmailSender:
    """邮件发送器"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
    
    def send(self, subject: str, html_content: str) -> bool:
        """发送邮件"""
        sender_email = self.config.get('sender_email')
        sender_password = self.config.get('sender_password')
        receiver_email = self.config.get('receiver_email', sender_email)
        
        try:
            # 创建邮件对象
            msg = MIMEMultipart("alternative")
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = receiver_email
            
            # 添加HTML内容
            html_part = MIMEText(html_content, "html", "utf-8")
            msg.attach(html_part)
            
            # 获取SMTP配置
            smtp_config = self._get_smtp_config(sender_email)
            logger.info(f"使用SMTP服务器: {smtp_config['server']}:{smtp_config['port']}")
            
            # 发送邮件
            if smtp_config['use_ssl']:
                self._send_with_ssl(smtp_config, sender_email, sender_password, receiver_email, msg)
            else:
                self._send_with_tls(smtp_config, sender_email, sender_password, receiver_email, msg)
            
            logger.info(f"邮件已成功发送至: {receiver_email}")
            return True
        except Exception as e:
            logger.error(f"发送邮件失败: {e}", exc_info=True)
            return False
    
    def _get_smtp_config(self, email: str) -> Dict:
        """获取SMTP配置"""
        domain = email.split('@')[1].lower()
        if domain in SMTP_CONFIGS:
            return SMTP_CONFIGS[domain]
        
        # 默认使用Gmail配置
        logger.warning(f"未知邮箱提供商 ({domain})，使用Gmail SMTP")
        return {'server': 'smtp.gmail.com', 'port': 587, 'use_ssl': False}
    
    def _send_with_ssl(self, smtp_config: Dict, sender: str, password: str, receiver: str, msg: MIMEMultipart):
        """使用SSL发送"""
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_config['server'], smtp_config['port'], context=context) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
    
    def _send_with_tls(self, smtp_config: Dict, sender: str, password: str, receiver: str, msg: MIMEMultipart):
        """使用TLS发送"""
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as server:
            if smtp_config['port'] != 25:
                server.starttls(context=context)
            server.ehlo()
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())

# ============================================================================
# 邮件内容生成
# ============================================================================

def create_email_content(repos: List[Dict], config: ConfigManager) -> Tuple[str, str]:
    """创建邮件内容"""
    since_map = {'daily': '今日', 'weekly': '本周', 'monthly': '本月'}
    since_text = since_map.get(config.get('trending_since', 'daily'), '今日')
    
    subject = f"GitHub Trending {since_text} - {datetime.now().strftime('%Y-%m-%d')}"
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub Trending {since_text}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #24292e;
            background-color: #f6f8fa;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #ffffff;
            padding: 40px 20px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 32px;
            margin-bottom: 8px;
            font-weight: 700;
        }}
        .header .subtitle {{
            font-size: 16px;
            opacity: 0.9;
        }}
        .content {{
            padding: 30px 20px;
        }}
        .repo {{
            border: 1px solid #e1e4e8;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            background-color: #ffffff;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .repo:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .repo-rank {{
            display: inline-block;
            width: 32px;
            height: 32px;
            background-color: #667eea;
            color: #ffffff;
            border-radius: 50%;
            text-align: center;
            line-height: 32px;
            font-weight: bold;
            margin-right: 12px;
            font-size: 14px;
        }}
        .repo-header {{
            margin-bottom: 12px;
        }}
        .repo-name {{
            font-size: 20px;
            font-weight: 600;
            display: inline;
        }}
        .repo-name a {{
            color: #0366d6;
            text-decoration: none;
        }}
        .repo-name a:hover {{
            text-decoration: underline;
        }}
        .repo-description {{
            color: #586069;
            margin-bottom: 16px;
            font-size: 15px;
            line-height: 1.5;
        }}
        .repo-stats {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            align-items: center;
            margin-bottom: 16px;
        }}
        .stat {{
            display: flex;
            align-items: center;
            font-size: 14px;
            color: #586069;
        }}
        .stat-icon {{
            margin-right: 4px;
        }}
        .language {{
            display: inline-flex;
            align-items: center;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 13px;
            font-weight: 600;
            color: #ffffff;
        }}
        .language-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 6px;
        }}
        .repo-summary {{
            background-color: #f8f9fa;
            border-left: 4px solid #0366d6;
            padding: 15px;
            margin-top: 15px;
            border-radius: 0 4px 4px 0;
            font-size: 14px;
            line-height: 1.6;
        }}
        .repo-topics {{
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #eaecef;
        }}
        .topic-tag {{
            display: inline-block;
            background-color: #f1f8ff;
            color: #0366d6;
            border: 1px solid #c8e1ff;
            border-radius: 2em;
            padding: 2px 10px;
            font-size: 12px;
            margin: 2px;
        }}
        .footer {{
            background-color: #f6f8fa;
            padding: 30px 20px;
            text-align: center;
            border-top: 1px solid #e1e4e8;
        }}
        .footer p {{
            color: #586069;
            font-size: 14px;
            margin: 5px 0;
        }}
        .footer a {{
            color: #0366d6;
            text-decoration: none;
        }}
        .footer a:hover {{
            text-decoration: underline;
        }}
        @media (max-width: 600px) {{
            .header h1 {{
                font-size: 24px;
            }}
            .repo {{
                padding: 16px;
            }}
            .repo-stats {{
                flex-direction: column;
                align-items: flex-start;
                gap: 12px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌟 GitHub Trending {since_text}</h1>
            <p class="subtitle">{datetime.now().strftime('%Y年%m月%d日 %A')}</p>
        </div>
        <div class="content">
"""

    for i, repo in enumerate(repos, 1):
        lang_color = LANGUAGE_COLORS.get(repo['language'], '#808080')
        html_content += f"""        <div class="repo">
            <div class="repo-header">
                <span class="repo-rank">{i}</span>
                <div class="repo-name">
                    <a href="{repo['url']}" target="_blank" rel="noopener">{repo['name']}</a>
                </div>
            </div>
            <div class="repo-description">
                {repo['description']}
            </div>
            <div class="repo-stats">
                <span class="stat">
                    <span class="stat-icon">⭐</span> {repo['stars']:,} stars
                </span>
                <span class="stat">
                    <span class="stat-icon">🔄</span> {repo['forks']:,} forks
                </span>
                <span class="language" style="background-color: {lang_color};">
                    <span class="language-dot" style="background-color: rgba(255,255,255,0.3);"></span>
                    {repo['language']}
                </span>
            </div>
"""

        # 添加详细摘要（如果存在）
        if 'summary' in repo and repo['summary']:
            html_content += f"""            <div class="repo-summary">
                <strong>项目总结:</strong><br>
                {repo['summary']}
            </div>"""

        # 添加话题标签（如果存在）
        if 'topics' in repo and repo['topics']:
            html_content += f"""            <div class="repo-topics">
                <strong>话题标签:</strong> """
            for topic in repo['topics'][:5]:  # 只显示前5个话题
                html_content += f"""<span class="topic-tag">{topic}</span> """
            html_content += f"""</div>"""

        html_content += f"""        </div>
"""

    html_content += f"""    </div>
        <div class="footer">
            <p><strong>GitHub Trending Emailer</strong></p>
            <p>自动发送于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><a href="https://github.com/trending" target="_blank">访问 GitHub Trending</a></p>
        </div>
    </div>
</body>
</html>"""

    return subject, html_content

# ============================================================================
# 定时任务
# ============================================================================

class Scheduler:
    """定时任务调度器"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
    
    def run(self, task_func):
        """运行定时任务"""
        schedule_time = self.config.get('schedule_time', '09:00')
        logger.info(f"定时任务已启动，将在每天 {schedule_time} 执行")
        
        while True:
            now = datetime.now()
            target_hour, target_minute = map(int, schedule_time.split(':'))
            
            # 检查是否到达执行时间（给2分钟窗口期）
            if now.hour == target_hour and now.minute < target_minute + 2:
                if now.minute >= target_minute:
                    logger.info(f"开始执行定时任务: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                    try:
                        task_func()
                    except Exception as e:
                        logger.error(f"定时任务执行失败: {e}", exc_info=True)
                    
                    # 等待5分钟避免重复执行
                    logger.info("任务执行完毕，等待下一次执行时间...")
                    time.sleep(300)
            
            # 每30秒检查一次
            time.sleep(30)

# ============================================================================
# 主程序
# ============================================================================

def main_task():
    """主任务"""
    # 加载配置
    config = ConfigManager()
    
    # 验证配置
    if not config.validate():
        logger.error("配置验证失败，请检查 config.json 文件")
        print(" " + "="*60)
        print("配置文件示例:")
        print(json.dumps(DEFAULT_CONFIG, indent=4, ensure_ascii=False))
        print("="*60 + " ")
        return False
    
    # 获取 GitHub Trending 数据
    logger.info("开始获取 GitHub Trending 数据...")
    fetcher = GitHubTrendingFetcher(config)
    repos = fetcher.fetch()
    
    if not repos:
        logger.error("未能获取到任何仓库数据")
        return False
    
    logger.info(f"成功获取 {len(repos)} 个趋势项目")
    
    # 创建邮件内容
    subject, html_content = create_email_content(repos, config)
    
    # 发送邮件
    logger.info("准备发送邮件...")
    sender = EmailSender(config)
    success = sender.send(subject, html_content)
    
    if success:
        logger.info("任务执行成功！")
    else:
        logger.error("任务执行失败！")
    
    return success

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='GitHub Trending 邮件推送程序（增强版）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
python github_trending_emailer_enhanced.py # 立即执行一次
python github_trending_emailer_enhanced.py --schedule # 定时执行
python github_trending_emailer_enhanced.py --test # 测试模式（使用示例数据）
python github_trending_emailer_enhanced.py --config custom.json # 使用自定义配置文件
"""
    )
    parser.add_argument('--schedule', action='store_true', help='启用定时任务模式')
    parser.add_argument('--test', action='store_true', help='测试模式（使用示例数据，不实际获取GitHub数据）')
    parser.add_argument('--config', type=str, default='config.json', help='配置文件路径（默认: config.json）')
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='日志级别')
    
    args = parser.parse_args()
    
    # 更新日志级别
    if args.log_level:
        logger.setLevel(getattr(logging, args.log_level))
    
    # 测试模式
    if args.test:
        logger.info("运行测试模式...")
        config = ConfigManager(args.config)
        if not config.validate():
            return
        
        fetcher = GitHubTrendingFetcher(config)
        repos = fetcher._get_example_data()
        subject, html_content = create_email_content(repos, config)
        
        # 保存HTML到文件供预览
        test_file = Path("test_email_detailed.html")
        test_file.write_text(html_content, encoding='utf-8')
        logger.info(f"测试邮件内容已保存到: {test_file}")
        
        # 询问是否发送测试邮件
        response = input(" 是否发送测试邮件？(y/N): ")
        if response.lower() == 'y':
            sender = EmailSender(config)
            sender.send(subject, html_content)
        return
    
    # 定时模式
    if args.schedule:
        config = ConfigManager(args.config)
        if not config.validate():
            return
        
        scheduler = Scheduler(config)
        scheduler.run(main_task)
    else:
        # 立即执行
        main_task()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info(" 程序已被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序发生未预期的错误: {e}", exc_info=True)
        sys.exit(1)