#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用邮件发送与配置模块

提供：
- DEFAULT_CONFIG：基础配置项（邮箱、调度、重试等）
- ConfigManager：加载/校验配置
- EmailSender：根据邮箱域名自动选择 SMTP 并发送 HTML 邮件
- Scheduler：简单的每日定时调度器
- logger：统一日志实例
"""

import json
import logging
import smtplib
import ssl
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Callable

DEFAULT_CONFIG: Dict = {
    "sender_email": "",
    "sender_password": "",
    "receiver_email": "",
    "schedule_time": "09:00",
    "trending_language": "",
    "trending_since": "daily",
    "max_repos": 10,
    "retry_attempts": 3,
    "retry_delay": 5,
    "cache_enabled": True,
    "cache_duration_hours": 1,
    "log_level": "INFO",
}

SMTP_CONFIGS: Dict = {
    "gmail.com": {"server": "smtp.gmail.com", "port": 587, "use_ssl": False},
    "qq.com": {"server": "smtp.qq.com", "port": 587, "use_ssl": False},
    "foxmail.com": {"server": "smtp.qq.com", "port": 587, "use_ssl": False},
    "163.com": {"server": "smtp.163.com", "port": 465, "use_ssl": True},
    "126.com": {"server": "smtp.126.com", "port": 465, "use_ssl": True},
    "sina.com": {"server": "smtp.sina.com", "port": 587, "use_ssl": False},
    "sina.cn": {"server": "smtp.sina.com", "port": 587, "use_ssl": False},
    "sohu.com": {"server": "smtp.sohu.com", "port": 25, "use_ssl": False},
    "hotmail.com": {"server": "smtp-mail.outlook.com", "port": 587, "use_ssl": False},
    "outlook.com": {"server": "smtp-mail.outlook.com", "port": 587, "use_ssl": False},
    "live.com": {"server": "smtp-mail.outlook.com", "port": 587, "use_ssl": False},
}


def setup_logger(log_level: str = "INFO") -> logging.Logger:
    """配置并返回全局 logger。"""
    logger = logging.getLogger("GitHubTrending")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(
        log_dir / f"github_trending_{datetime.now().strftime('%Y%m')}.log",
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


logger = setup_logger()


class ConfigManager:
    """配置管理器，支持自定义默认配置（用于不同入口脚本扩展字段）。"""

    def __init__(
        self,
        config_path: str = "config.json",
        default_config: Optional[Dict] = None,
    ):
        self.config_path = Path(config_path)
        self.default_config = (default_config or DEFAULT_CONFIG).copy()
        self.config: Dict = self._load_config()

    def _load_config(self) -> Dict:
        """加载配置文件并与默认配置合并。"""
        if not self.config_path.exists():
            logger.warning(f"配置文件不存在: {self.config_path}")
            self._create_default_config()
            return self.default_config.copy()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            merged = self.default_config.copy()
            merged.update(config)
            logger.info(f"成功加载配置文件: {self.config_path}")
            return merged
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}")
            return self.default_config.copy()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return self.default_config.copy()

    def _create_default_config(self) -> None:
        """创建默认配置文件。"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.default_config, f, indent=4, ensure_ascii=False)
            logger.info(f"已创建默认配置文件: {self.config_path}")
            logger.info("请编辑配置文件并填入您的邮箱信息")
        except Exception as e:
            logger.error(f"创建配置文件失败: {e}")

    def validate(self) -> bool:
        """验证邮箱配置是否完整、格式是否正确。"""
        if not self.config.get("sender_email"):
            logger.error("未配置发件人邮箱 (sender_email)")
            return False

        if not self.config.get("sender_password"):
            logger.error("未配置发件人密码 (sender_password)")
            return False

        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, self.config["sender_email"]):
            logger.error(f"发件人邮箱格式不正确: {self.config['sender_email']}")
            return False

        if not self.config.get("receiver_email"):
            self.config["receiver_email"] = self.config["sender_email"]
            logger.info("未配置收件人邮箱，将发送给发件人自己")

        logger.info("配置验证通过")
        return True

    def get(self, key: str, default=None):
        return self.config.get(key, default)


class EmailSender:
    """基于配置自动选择 SMTP 并发送 HTML 邮件。"""

    def __init__(self, config: ConfigManager):
        self.config = config

    def send(self, subject: str, html_content: str) -> bool:
        sender_email = self.config.get("sender_email")
        sender_password = self.config.get("sender_password")
        receiver_email = self.config.get("receiver_email", sender_email)

        try:
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = sender_email
            msg["To"] = receiver_email

            html_part = MIMEText(html_content, "html", "utf-8")
            msg.attach(html_part)

            smtp_config = self._get_smtp_config(sender_email)
            logger.info(
                f"使用SMTP服务器: {smtp_config['server']}:{smtp_config['port']}"
            )

            if smtp_config["use_ssl"]:
                self._send_with_ssl(
                    smtp_config, sender_email, sender_password, receiver_email, msg
                )
            else:
                self._send_with_tls(
                    smtp_config, sender_email, sender_password, receiver_email, msg
                )

            logger.info(f"邮件已成功发送至: {receiver_email}")
            return True
        except Exception as e:
            logger.error(f"发送邮件失败: {e}", exc_info=True)
            return False

    def _get_smtp_config(self, email: str) -> Dict:
        domain = email.split("@")[1].lower()
        if domain in SMTP_CONFIGS:
            return SMTP_CONFIGS[domain]
        logger.warning(f"未知邮箱提供商 ({domain})，使用Gmail SMTP")
        return {"server": "smtp.gmail.com", "port": 587, "use_ssl": False}

    def _send_with_ssl(
        self,
        smtp_config: Dict,
        sender: str,
        password: str,
        receiver: str,
        msg,
    ) -> None:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            smtp_config["server"], smtp_config["port"], context=context
        ) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())

    def _send_with_tls(
        self,
        smtp_config: Dict,
        sender: str,
        password: str,
        receiver: str,
        msg,
    ) -> None:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_config["server"], smtp_config["port"]) as server:
            if smtp_config["port"] != 25:
                server.starttls(context=context)
            server.ehlo()
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())


class Scheduler:
    """简单的每日定时调度器，基于配置项 schedule_time。"""

    def __init__(self, config: ConfigManager):
        self.config = config

    def run(self, task_func: Callable[[], bool]) -> None:
        schedule_time = self.config.get("schedule_time", "09:00")
        logger.info(f"定时任务已启动，将在每天 {schedule_time} 执行")

        while True:
            now = datetime.now()
            target_hour, target_minute = map(int, schedule_time.split(":"))

            if now.hour == target_hour and now.minute < target_minute + 2:
                if now.minute >= target_minute:
                    logger.info(
                        f"开始执行定时任务: {now.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    try:
                        task_func()
                    except Exception as e:
                        logger.error("定时任务执行失败: %s", e, exc_info=True)

                    logger.info("任务执行完毕，等待下一次执行时间...")
                    time.sleep(300)

            time.sleep(30)

