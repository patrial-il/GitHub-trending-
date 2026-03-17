# GitHub Trending 邮件推送程序

这个程序会自动获取 GitHub 上最新的趋势项目，并通过电子邮件发送给您。

现在还新增了一个基于 Dify 的入口，可以将 **Dify Workflow 生成的 HTML 报告**（例如「GitHub Trending + 抖音热点 + NLP 总结」）作为邮件正文发送。

## 功能特性

- 自动获取 GitHub Trending 项目（本地爬取版）
- 基于 Dify Workflow 的 HTML 报告发送（推荐用于「GitHub Trending + 抖音热点 + NLP 总结」）
- 美观的 HTML 邮件格式
- 支持定时推送
- 显示项目名称、描述、编程语言、星标数和派生数（本地 GitHub 版本）
- 自动检测邮箱提供商并使用相应SMTP服务器
- 完整的日志记录系统
- 改进的错误处理和重试机制
- 支持 requests 库和 BeautifulSoup 进行更可靠的HTML解析
- 数据缓存机制，减少重复请求
- 配置验证功能
- 支持定时任务和测试模式
- 灵活的配置选项

## 依赖要求

- Python 3.x (已测试 Python 3.6+)
- 推荐安装: requests, beautifulsoup4 (用于更可靠的HTML解析)
- 系统 crontab (用于定时任务)

## 快速开始

### 1. 安装依赖（可选但推荐）

```bash
pip install requests beautifulsoup4
```

### 2. 配置邮箱信息

首先，编辑 `config.json` 文件，填入您的邮箱信息：

```json
{
    "sender_email": "your_email@provider.com",
    "sender_password": "your_app_password_or_auth_code",
    "receiver_email": "recipient@provider.com"
}
```

**重要提示 - 关于密码：**
- **Gmail**: 使用应用专用密码（非账户密码）- 访问 https://myaccount.google.com/apppasswords
- **QQ邮箱**: 使用授权码（非QQ密码）- 在邮箱设置中开启SMTP并获取授权码
- **163邮箱**: 使用客户端授权密码（非账户密码）- 在邮箱设置中开启SMTP服务
- **其他邮箱**: 使用对应的SMTP授权码

### 3. 使用 Dify 报告发送邮件（推荐）

如果你已经在 Dify 中搭好了一个 Workflow（例如：获取 GitHub Trending + 抖音热点，用 LLM 生成 HTML 报告），可以直接用本项目的 `dify_report_emailer.py` 来发送这份 HTML 报告：

1. 配置环境变量（建议放到 shell 或系统环境里）：

```bash
export DIFY_API_KEY="your_dify_api_key"
export DIFY_WORKFLOW_ID="your_workflow_id"
export DIFY_BASE_URL="https://api.dify.ai"  # 可选，默认即为此
```

2. 运行一次：

```bash
python dify_report_emailer.py
```

3. 测试模式（仅生成 HTML 文件 `test_email_dify.html`，不发送邮件）：

```bash
python dify_report_emailer.py --test
```

4. 定时执行（按 `config.json` 中的 `schedule_time` 每天发送 Dify 报告）：

```bash
python dify_report_emailer.py --schedule
```

### 4. 只使用本地 GitHub Trending 版本（原有模式）

在配置好邮箱后，可以先测试程序是否能正常运行：

```bash
# 立即执行一次（简化版）
python github_trending_emailer.py

# 测试模式（使用示例数据，不实际获取GitHub数据）
python github_trending_emailer.py --test

# 定时执行模式
python github_trending_emailer.py --schedule
```

### 5. 设置系统级定时任务（crontab）

运行以下命令设置每日定时推送：

```bash
./setup_cron.sh
```

这将在您的 crontab 中添加一个任务，每天上午9点自动执行。

## 高级配置

### 修改推送时间

如果您想更改推送时间，可以直接编辑 crontab：

```bash
crontab -e
```

修改时间部分。例如，`0 9 * * *` 表示每天上午9点，`30 14 * * *` 表示每天下午2点30分。

### 查看日志

定时任务的输出会被记录到 `logs/` 目录下的日志文件中：

```bash
tail -f logs/github_trending_*.log
```

### 配置选项

在 `config.json` 中可以设置以下选项：

```json
{
    "sender_email": "your_email@provider.com",
    "sender_password": "your_app_password_or_auth_code",
    "receiver_email": "recipient@provider.com",
    "schedule_time": "09:00",           // 推送时间 (HH:MM 格式)
    "trending_language": "",            // 特定编程语言 (空字符串表示所有语言)
    "trending_since": "daily",          // 时间范围 (daily, weekly, monthly)
    "max_repos": 10,                    // 最大仓库数量
    "retry_attempts": 3,                // 获取数据失败时重试次数
    "retry_delay": 5,                   // 重试间隔(秒)
    "cache_enabled": true,              // 是否启用缓存
    "cache_duration_hours": 1,          // 缓存有效期(小时)
    "log_level": "INFO"                 // 日志级别 (DEBUG, INFO, WARNING, ERROR)
}
```

## 支持的邮箱提供商

程序自动检测邮箱域名并使用相应的SMTP服务器：
- Gmail: `smtp.gmail.com`
- QQ邮箱: `smtp.qq.com`
- 163邮箱: `smtp.163.com`
- 126邮箱: `smtp.126.com`
- Outlook/Hotmail: `smtp-mail.outlook.com`
- 其他邮箱: 自动尝试通用配置

## 注意事项

1. 该程序优先使用 requests + BeautifulSoup 获取 GitHub 数据，若未安装则回退到 curl
2. 请确保网络连接正常，以便访问 GitHub
3. 为避免被反爬虫机制限制，程序默认每天只执行一次
4. 邮箱的用户名和密码存储在本地配置文件中，请注意保护文件安全
5. **重要**: 必须使用邮箱提供商的SMTP授权码，而不是常规登录密码
6. 程序具备缓存机制，可在短时间内避免重复请求

## 故障排除

### 邮件发送失败
- 检查 `config.json` 中的邮箱配置是否正确
- 确认使用的是SMTP授权码而非登录密码
- 检查邮箱的SMTP服务是否已开启

### 无法获取 GitHub 数据
- 确认系统中安装了 curl 或 requests + BeautifulSoup
- 检查网络连接是否正常
- 检查 GitHub 是否被防火墙限制

### 定时任务不执行
- 检查 crontab 配置 (`crontab -l`)
- 查看日志文件 (`logs/github_trending_*.log`) 了解错误信息

### 常见错误 `(535, b'5.7.8 Username and Password not accepted')`
- 这通常表示使用了账户登录密码而非SMTP授权码
- 请获取并使用相应邮箱提供商的SMTP授权码

## 依赖项

- Python 3.x
- 标准库: smtplib, email, subprocess, json, datetime, ssl, re, logging, argparse, pathlib
- 推荐库: requests, beautifulsoup4 (用于更可靠的HTML解析)
- 系统工具: curl (备选方案)

## 自定义

您可以修改程序中的以下参数：
- 推送时间：通过配置文件或 crontab 配置
- 项目数量：通过配置文件设置
- 邮件格式：修改 HTML 模板部分
- 获取策略：选择 requests + BeautifulSoup 或 curl 方案