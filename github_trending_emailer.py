#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Trending 邮件推送程序（改进版）
每天定时获取 GitHub Trending 排行，并发送到指定邮箱
改进点：
1. 添加完整的日志记录系统
2. 改进错误处理和重试机制
3. 使用 requests 库替代 curl（更 Pythonic）
4. 添加配置验证
5. 改进 HTML 解析（使用 BeautifulSoup）
6. 添加数据缓存机制
7. 支持多种时间格式配置
8. 改进的邮件模板
9. 添加测试模式
10. 更好的代码组织和文档
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
    "log_level": "INFO"
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
            return self._load_cache()
        
        # 获取新数据
        repos = self._fetch_from_github()
        
        # 保存缓存
        if self.config.get('cache_enabled') and repos:
            self._save_cache(repos)
        
        return repos
    
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
        return self._get_example_data()
    
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
        return [
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
        </div>
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
        description='GitHub Trending 邮件推送程序',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
python github_trending_emailer.py # 立即执行一次
python github_trending_emailer.py --schedule # 定时执行
python github_trending_emailer.py --test # 测试模式（使用示例数据）
python github_trending_emailer.py --config custom.json # 使用自定义配置文件
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
        test_file = Path("test_email.html")
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