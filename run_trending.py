#!/usr/bin/env python3
"""
GitHub Trending 定时任务脚本
爬取 trending -> 生成 HTML -> 发送邮件
"""

import asyncio
import argparse
import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

# 导入项目模块
from get_github_trending import GitHubTrendingScraper
from generate_html import main as generate_html
from mailer_core import send_trending_email, TrendingMailer, SMTP_CONFIGS


# 配置日志
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

log_file = os.path.join(LOG_DIR, "cron.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_config(config_file: str = None) -> dict:
    """
    加载配置文件

    Args:
        config_file: 配置文件路径，默认使用 mailer_config.json

    Returns:
        配置字典
    """
    if config_file is None:
        config_file = "mailer_config.json"

    if not os.path.exists(config_file):
        logger.warning(f"配置文件不存在：{config_file}")
        logger.info("尝试从环境变量读取配置...")
        return {}

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"已加载配置文件：{config_file}")
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败：{e}")
        return {}


def fetch_trending(top_k: int = 20) -> bool:
    """
    爬取 GitHub Trending 并缓存

    Args:
        top_k: 获取前 k 个仓库

    Returns:
        True 表示成功
    """
    logger.info(f"开始爬取 GitHub Trending (top_{top_k})...")

    async def scrape():
        scraper = GitHubTrendingScraper(cache_enabled=True)
        repos = await scraper.scrape(top_k=top_k, since='daily', output_json=False)
        return len(repos) > 0

    try:
        success = asyncio.run(scrape())
        if success:
            logger.info("爬取成功!")
            return True
        else:
            logger.error("爬取失败：未获取到任何仓库数据")
            return False
    except Exception as e:
        logger.error(f"爬取异常：{e}")
        return False


def generate_html_page() -> bool:
    """
    生成 HTML 页面

    Returns:
        True 表示成功
    """
    logger.info("开始生成 HTML 页面...")
    try:
        generate_html()
        logger.info("HTML 生成成功!")
        return True
    except Exception as e:
        logger.error(f"HTML 生成失败：{e}")
        return False


def send_email(config: dict) -> bool:
    """
    发送邮件

    Args:
        config: 邮件配置字典

    Returns:
        True 表示成功
    """
    logger.info("开始发送邮件...")

    # 从配置或环境变量获取参数
    smtp_provider = config.get("smtp_provider", "").lower()

    # 如果指定了 SMTP 提供商，使用预配置
    if smtp_provider in SMTP_CONFIGS:
        provider_config = SMTP_CONFIGS[smtp_provider]
        smtp_server = config.get("smtp_server", provider_config["server"])
        smtp_port = config.get("smtp_port", provider_config["port"])
        use_ssl = config.get("use_ssl", provider_config.get("use_ssl", True))
    else:
        smtp_server = config.get("smtp_server") or os.getenv("SMTP_SERVER", "smtp.qq.com")
        smtp_port = config.get("smtp_port") or int(os.getenv("SMTP_PORT", "465"))
        use_ssl = config.get("use_ssl", True)

    username = config.get("username") or os.getenv("SMTP_USERNAME")
    password = config.get("password") or os.getenv("SMTP_PASSWORD")
    from_email = config.get("from_email") or os.getenv("FROM_EMAIL", username)
    to_emails_str = config.get("to_emails") or os.getenv("TO_EMAILS", "")
    subject = config.get("subject")

    # 验证必要参数
    if not username or not password or not to_emails_str:
        logger.error("缺少必要的邮件配置:")
        logger.error("  - username/SMTP_USERNAME")
        logger.error("  - password/SMTP_PASSWORD")
        logger.error("  - to_emails/TO_EMAILS")
        return False

    to_emails = [email.strip() for email in to_emails_str.split(",")]

    # 发送邮件
    success = send_trending_email(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        username=username,
        password=password,
        from_email=from_email,
        to_emails=to_emails,
        subject=subject,
        html_dir="html"
    )

    if success:
        logger.info("邮件发送成功!")
    else:
        logger.error("邮件发送失败!")

    return success


def run_full_pipeline(config: dict, top_k: int = 20) -> bool:
    """
    运行完整流程：爬取 -> 生成 HTML -> 发送邮件

    Args:
        config: 邮件配置
        top_k: 获取前 k 个仓库

    Returns:
        True 表示全流程成功
    """
    logger.info("=" * 60)
    logger.info("开始运行 GitHub Trending 定时任务")
    logger.info(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # 步骤 1: 爬取数据
    if not fetch_trending(top_k=top_k):
        logger.error("流程中断：爬取失败")
        return False

    # 步骤 2: 生成 HTML
    if not generate_html_page():
        logger.error("流程中断：HTML 生成失败")
        return False

    # 步骤 3: 发送邮件
    if not send_email(config):
        logger.error("流程中断：邮件发送失败")
        return False

    logger.info("=" * 60)
    logger.info("定时任务执行完成!")
    logger.info("=" * 60)
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="GitHub Trending 定时任务 - 爬取、生成 HTML、发送邮件"
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="mailer_config.json",
        help="配置文件路径 (默认：mailer_config.json)"
    )
    parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=20,
        help="获取 trending top N 仓库 (默认：20)"
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="跳过爬取步骤（使用现有缓存）"
    )
    parser.add_argument(
        "--skip-email",
        action="store_true",
        help="跳过邮件发送步骤"
    )
    parser.add_argument(
        "--email-only",
        action="store_true",
        help="仅发送邮件（不爬取，不生成 HTML）"
    )

    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)

    # 根据参数决定执行哪些步骤
    if args.email_only:
        # 仅发送邮件
        success = send_email(config)
    elif args.skip_email:
        # 不发送邮件
        if not args.skip_fetch:
            success = fetch_trending(top_k=args.top_k)
        else:
            logger.info("跳过爬取步骤")
            success = True

        if success:
            success = generate_html_page()
    else:
        # 完整流程
        success = run_full_pipeline(config, top_k=args.top_k)

    # 退出状态
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
