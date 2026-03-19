# GitHub Trending 邮件订阅系统

自动爬取 GitHub Trending 仓库，生成美观的 HTML 页面，并定时发送到指定邮箱。

## 功能特点

- 🔥 **自动爬取** - 每日自动获取 GitHub Trending 仓库信息
- 📱 **移动端优化** - 生成的 HTML 完美适配手机和邮件客户端
- 📧 **邮件发送** - 支持 SMTP 发送，HTML 直接嵌入邮件正文
- 💾 **智能缓存** - 按天缓存数据，避免重复请求
- ⏰ **定时任务** - 支持 Windows/Linux 定时自动执行
- 🎨 **深色主题** - 采用 GitHub 风格深色主题

## 项目结构

```
.
├── get_github_trending.py    # GitHub Trending 爬虫核心
├── trending_cache.py         # 缓存管理模块
├── generate_html.py          # HTML 页面生成器
├── mailer_core.py            # 邮件发送模块
├── run_trending.py           # 定时任务主脚本
├── run_trending.bat          # Windows 批处理执行脚本
├── setup_cron.sh             # Linux/macOS cron 设置脚本
├── mailer_config.example.json # 配置文件示例
├── MAILER_SETUP.md           # 邮件配置详细说明
└── WINDOWS_SCHEDULER.md      # Windows 定时任务设置指南
```

## 快速开始

### 1. 安装依赖

```bash
pip install aiohttp beautifulsoup4
```

### 2. 配置邮箱

复制配置文件并修改：

```bash
cp mailer_config.example.json mailer_config.json
```

编辑 `mailer_config.json`：

```json
{
  "smtp_provider": "qq",
  "username": "your-email@qq.com",
  "password": "your-smtp-auth-code",
  "from_email": "your-email@qq.com",
  "to_emails": "recipient@example.com",
  "subject": "GitHub Trending 日报"
}
```

### 3. 测试运行

```bash
# 完整流程：爬取 + 生成 HTML + 发送邮件
python run_trending.py --config mailer_config.json

# 仅爬取数据（不发送邮件）
python run_trending.py --skip-email

# 仅发送邮件（使用现有缓存）
python run_trending.py --email-only
```

## 命令行参数

| 参数 | 说明 |
|------|------|
| `--config, -c` | 配置文件路径（默认：mailer_config.json） |
| `--top-k, -k` | 获取 trending top N 仓库（默认：20） |
| `--skip-fetch` | 跳过爬取步骤（使用现有缓存） |
| `--skip-email` | 跳过邮件发送步骤 |
| `--email-only` | 仅发送邮件（不爬取，不生成 HTML） |

## 设置定时任务

### Windows

1. 参考 [WINDOWS_SCHEDULER.md](WINDOWS_SCHEDULER.md)
2. 使用任务计划程序每天固定时间执行 `run_trending.bat`

### Linux/macOS

```bash
# 运行设置脚本
bash setup_cron.sh
```

或使用环境变量方式：

```bash
# 设置环境变量
export SMTP_USERNAME="your-email@qq.com"
export SMTP_PASSWORD="your-auth-code"
export TO_EMAILS="recipient@example.com"

# 添加 cron 任务（每天 9 点执行）
crontab -e
# 添加：0 9 * * * cd /path/to/project && python3 run_trending.py
```

## 邮件服务商配置

### QQ 邮箱

```json
{
  "smtp_provider": "qq",
  "smtp_server": "smtp.qq.com",
  "smtp_port": 465,
  "username": "your-email@qq.com",
  "password": "your-smtp-auth-code"
}
```

> 注意：需要在邮箱设置中开启 SMTP 服务并获取授权码

### 163 邮箱

```json
{
  "smtp_provider": "163",
  "smtp_server": "smtp.163.com",
  "smtp_port": 465,
  "username": "your-email@163.com",
  "password": "your-smtp-auth-code"
}
```

### Gmail

```json
{
  "smtp_provider": "gmail",
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "username": "your-email@gmail.com",
  "password": "your-app-password"
}
```

### Outlook/Office365

```json
{
  "smtp_provider": "outlook",
  "smtp_server": "smtp.office365.com",
  "smtp_port": 587,
  "username": "your-email@outlook.com",
  "password": "your-password"
}
```

详细配置说明见 [MAILER_SETUP.md](MAILER_SETUP.md)

## 模块说明

### TrendingCache (缓存管理)

```python
from trending_cache import TrendingCache

cache = TrendingCache()

# 检查是否需要更新
if cache.should_update():
    # 获取新数据并保存
    cache.save(repos)

# 加载今天的数据
data = cache.load_today()

# 加载最新数据（今天或昨天）
data = cache.load_latest()

# 获取缓存信息
info = cache.get_cache_info()

# 清理旧缓存（保留最近 7 天）
cache.cleanup_old_cache(keep_days=7)
```

### GitHubTrendingScraper (爬虫)

```python
from get_github_trending import GitHubTrendingScraper

# 创建爬虫（默认启用缓存）
scraper = GitHubTrendingScraper(cache_enabled=True)

# 爬取数据
repos = await scraper.scrape(top_k=10, since='daily')

# 强制更新缓存
repos = await scraper.scrape(top_k=10, force_update=True)

# 禁用缓存
scraper = GitHubTrendingScraper(cache_enabled=False)
```

### TrendingMailer (邮件发送)

```python
from mailer_core import TrendingMailer

mailer = TrendingMailer(
    smtp_server="smtp.qq.com",
    smtp_port=465,
    username="your-email@qq.com",
    password="your-auth-code",
    from_email="your-email@qq.com",
    to_emails=["recipient1@example.com", "recipient2@example.com"]
)

# 发送邮件（自动读取今天的 HTML）
mailer.send()

# 或指定 HTML 内容
mailer.send(html_content=html_string)
```

## 环境变量

也可以使用环境变量代替配置文件：

```bash
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465
SMTP_USERNAME=your-email@qq.com
SMTP_PASSWORD=your-auth-code
FROM_EMAIL=your-email@qq.com
TO_EMAILS=recipient1@example.com,recipient2@example.com
```

## 输出示例

### 缓存文件 (cache/github_trending_YYYYMMDD.json)

```json
{
  "cache_date": "20260319",
  "created_at": "2026-03-19T22:10:06.422598",
  "repositories": [
    {
      "rank": 1,
      "name": "owner/repo",
      "url": "https://github.com/owner/repo",
      "description": "项目描述",
      "language": "Python",
      "total_stars": "10,234",
      "stars_today": "1,234 stars today",
      "zread_link": "https://zread.ai/owner/repo"
    }
  ]
}
```

### HTML 输出目录 (html/)

- `trending_YYYYMMDD.html` - 每日 Trending 页面
- 自动清理 30 天前的旧文件

## 日志

日志文件位置：`logs/cron.log`

查看日志：
```bash
# Linux/macOS
tail -f logs/cron.log

# Windows
Get-Content logs\cron.log -Tail 50 -Wait
```

## 常见问题

### 1. SMTP 认证失败

- 确认使用的是 SMTP 授权码，不是登录密码
- 检查邮箱是否开启了 SMTP 服务

### 2. 邮件进入垃圾箱

- 将发件人邮箱添加到联系人
- 使用主流邮箱服务商（QQ、163、Gmail 等）

### 3. 爬虫失败

- 检查网络连接
- GitHub 页面结构可能变化，需要更新解析逻辑

## License

MIT
