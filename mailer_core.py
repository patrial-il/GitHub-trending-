#!/usr/bin/env python3
"""
邮件发送核心模块
发送 GitHub Trending HTML 内容到指定邮箱
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import date
from typing import List, Optional
import glob


class TrendingMailer:
    """GitHub Trending 邮件发送器"""

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
        to_emails: List[str],
        use_ssl: bool = True,
        use_tls: bool = True
    ):
        """
        初始化邮件发送器

        Args:
            smtp_server: SMTP 服务器地址
            smtp_port: SMTP 端口
            username: SMTP 用户名
            password: SMTP 密码（或授权码）
            from_email: 发件人邮箱
            to_emails: 收件人邮箱列表
            use_ssl: 是否使用 SSL
            use_tls: 是否使用 TLS
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
        self.use_ssl = use_ssl
        self.use_tls = use_tls

    def _get_today_html(self, html_dir: str = "html") -> Optional[tuple]:
        """
        获取今天的 HTML 文件内容

        Args:
            html_dir: HTML 文件目录

        Returns:
            (html_content, file_path) 元组，如果文件不存在则返回 None
        """
        today = date.today().strftime("%Y%m%d")
        html_file = os.path.join(html_dir, f"trending_{today}.html")

        if not os.path.exists(html_file):
            # 尝试获取最新的 HTML 文件
            html_files = glob.glob(os.path.join(html_dir, "trending_*.html"))
            if html_files:
                html_file = max(html_files, key=os.path.getmtime)
                print(f"[INFO] 今天 HTML 不存在，使用最新文件：{html_file}")
            else:
                print(f"[WARN] HTML 文件不存在：{html_file}")
                return None

        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"[OK] 已读取 HTML: {html_file}")
            return (content, html_file)
        except IOError as e:
            print(f"[ERROR] 读取 HTML 失败：{e}")
            return None

    def _create_message(self, html_content: str, subject: str = None) -> MIMEMultipart:
        """
        创建邮件消息

        Args:
            html_content: HTML 内容
            subject: 邮件主题

        Returns:
            MIMEMultipart 消息对象
        """
        if subject is None:
            today = date.today().strftime("%Y-%m-%d")
            subject = f"🔥 GitHub Trending | {today}"

        msg = MIMEMultipart("alternative")
        msg["From"] = self.from_email
        msg["To"] = ", ".join(self.to_emails)
        msg["Subject"] = Header(subject, "utf-8")

        # 添加纯文本版本（兼容性）
        text_content = f"GitHub Trending - {date.today().strftime('%Y-%m-%d')}"
        msg.attach(MIMEText(text_content, "plain", "utf-8"))

        # 添加 HTML 版本（主要内容）
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        return msg

    def send(
        self,
        html_content: str = None,
        subject: str = None,
        html_dir: str = "html"
    ) -> bool:
        """
        发送邮件

        Args:
            html_content: HTML 内容，如果为 None 则自动读取今天的文件
            subject: 邮件主题
            html_dir: HTML 文件目录

        Returns:
            True 表示发送成功，False 表示失败
        """
        # 获取 HTML 内容
        if html_content is None:
            result = self._get_today_html(html_dir)
            if result is None:
                return False
            html_content, _ = result

        # 创建邮件
        msg = self._create_message(html_content, subject)

        try:
            # 连接 SMTP 服务器
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)

            with server:
                # 启用 TLS
                if not self.use_ssl and self.use_tls:
                    server.starttls()

                # 登录
                if self.username and self.password:
                    server.login(self.username, self.password)

                # 发送邮件
                server.sendmail(self.from_email, self.to_emails, msg.as_string())

            print(f"[OK] 邮件已发送至：{', '.join(self.to_emails)}")
            return True

        except smtplib.SMTPAuthenticationError:
            print("[ERROR] SMTP 认证失败，请检查用户名和密码")
            return False
        except smtplib.SMTPConnectError:
            print(f"[ERROR] 无法连接 SMTP 服务器：{self.smtp_server}:{self.smtp_port}")
            return False
        except Exception as e:
            print(f"[ERROR] 发送邮件失败：{e}")
            return False


def send_trending_email(
    smtp_server: str,
    smtp_port: int,
    username: str,
    password: str,
    from_email: str,
    to_emails: List[str],
    subject: str = None,
    html_dir: str = "html"
) -> bool:
    """
    便捷函数：发送 GitHub Trending 邮件

    Args:
        smtp_server: SMTP 服务器地址
        smtp_port: SMTP 端口
        username: SMTP 用户名
        password: SMTP 密码
        from_email: 发件人邮箱
        to_emails: 收件人邮箱列表
        subject: 邮件主题
        html_dir: HTML 文件目录

    Returns:
        True 表示发送成功
    """
    mailer = TrendingMailer(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        username=username,
        password=password,
        from_email=from_email,
        to_emails=to_emails
    )
    return mailer.send(subject=subject, html_dir=html_dir)


# 示例配置（常见邮箱 SMTP 服务器）
SMTP_CONFIGS = {
    "qq": {
        "server": "smtp.qq.com",
        "port": 465,
        "use_ssl": True
    },
    "163": {
        "server": "smtp.163.com",
        "port": 465,
        "use_ssl": True
    },
    "gmail": {
        "server": "smtp.gmail.com",
        "port": 587,
        "use_ssl": False,
        "use_tls": True
    },
    "outlook": {
        "server": "smtp.office365.com",
        "port": 587,
        "use_ssl": False,
        "use_tls": True
    }
}


if __name__ == "__main__":
    # 示例：从环境变量读取配置并发送邮件
    # 或者在这里直接配置

    # 从环境变量读取（推荐方式）
    smtp_server = os.getenv("SMTP_SERVER", "smtp.qq.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("FROM_EMAIL", username)
    to_emails_str = os.getenv("TO_EMAILS", "")

    if not username or not password or not to_emails_str:
        print("[ERROR] 请设置以下环境变量:")
        print("  SMTP_USERNAME - SMTP 用户名")
        print("  SMTP_PASSWORD - SMTP 密码/授权码")
        print("  TO_EMAILS - 收件人邮箱列表（逗号分隔）")
        print("  FROM_EMAIL - 发件人邮箱（可选，默认同用户名）")
        exit(1)

    to_emails = [email.strip() for email in to_emails_str.split(",")]

    # 发送邮件
    success = send_trending_email(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        username=username,
        password=password,
        from_email=from_email,
        to_emails=to_emails
    )

    if success:
        print("[OK] 邮件发送成功!")
    else:
        print("[ERROR] 邮件发送失败!")
        exit(1)
