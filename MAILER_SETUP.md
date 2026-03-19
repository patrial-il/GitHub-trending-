# GitHub Trending 邮件配置

## 环境变量方式（推荐用于生产环境）

```bash
# SMTP 服务器配置
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465

# SMTP 认证
SMTP_USERNAME=your-email@qq.com
SMTP_PASSWORD=your-smtp-auth-code  # 注意：是 SMTP 授权码，不是登录密码

# 发件人（可选，默认同 SMTP_USERNAME）
FROM_EMAIL=your-email@qq.com

# 收件人列表（逗号分隔）
TO_EMAILS=recipient1@example.com,recipient2@example.com
```

## 配置文件方式

复制 `mailer_config.example.json` 为 `mailer_config.json` 并修改配置。

## 常见 SMTP 服务器配置

### QQ 邮箱
- 服务器：smtp.qq.com
- 端口：465 (SSL)
- 授权码：在邮箱设置 -> POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV 服务中开启 SMTP 并获取授权码

### 163 邮箱
- 服务器：smtp.163.com
- 端口：465 (SSL)
- 授权码：在邮箱设置 -> POP3/SMTP/IMAP 中开启 SMTP 并获取授权码

### Gmail
- 服务器：smtp.gmail.com
- 端口：587 (TLS)
- 需要开启两步验证并生成应用专用密码

### Outlook/Office365
- 服务器：smtp.office365.com
- 端口：587 (TLS)
