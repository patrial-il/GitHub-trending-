#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 Dify 报告的邮件推送入口

流程：
1. 使用 ConfigManager 加载邮箱配置
2. 调用 Dify Workflow 获取 HTML 报告（包含 GitHub Trending + 抖音热点等）
3. 使用 EmailSender 发送 HTML 邮件

使用方式示例：
    python dify_report_emailer.py              # 立即执行一次
    python dify_report_emailer.py --schedule   # 按 config.json 中的 schedule_time 每天定时执行
    python dify_report_emailer.py --test       # 测试模式：仅拉取 Dify 报告并保存到本地 HTML
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from mailer_core import ConfigManager, DEFAULT_CONFIG, EmailSender, Scheduler, logger
from dify_client import DifyClient


def main_task(config: ConfigManager) -> bool:
    """单次任务：拉取 Dify 报告并发送邮件。"""
    if not config.validate():
        logger.error("配置验证失败，请检查 config.json 文件")
        print(" " + "=" * 60)
        print("配置文件示例:")
        print(json.dumps(DEFAULT_CONFIG, indent=4, ensure_ascii=False))
        print("=" * 60 + " ")
        return False

    client = DifyClient()
    subject, html = client.fetch_html_report()

    sender = EmailSender(config)
    logger.info("准备发送 Dify 报告邮件...")
    success = sender.send(subject, html)

    if success:
        logger.info("Dify 报告邮件发送成功！")
    else:
        logger.error("Dify 报告邮件发送失败！")

    return success


def main() -> None:
    parser = argparse.ArgumentParser(
        description="基于 Dify 报告的邮件推送程序",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
python dify_report_emailer.py                     # 立即执行一次
python dify_report_emailer.py --schedule          # 定时执行（按 config.json 的 schedule_time）
python dify_report_emailer.py --test              # 测试模式，只生成本地 HTML 不发邮件
python dify_report_emailer.py --config custom.json    # 使用自定义配置文件
""",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="启用定时任务模式（使用 Scheduler 和 main_task）",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="测试模式：调用 Dify 获取 HTML 并保存到本地，不发送邮件",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="配置文件路径（默认: config.json）",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别",
    )

    args = parser.parse_args()

    if args.log_level:
        from logging import getLogger

        # 调整已创建 logger 的级别
        getLogger("GitHubTrending").setLevel(args.log_level)

    config = ConfigManager(args.config)

    if args.test:
        # 测试模式：只生成 HTML 文件，便于前期调试 Dify Workflow
        logger.info("运行 Dify 报告测试模式...")
        client = DifyClient()
        # 使用今天日期方便确认
        subject, html = client.fetch_html_report(date.today().isoformat())
        test_file = Path("test_email_dify.html")
        test_file.write_text(html, encoding="utf-8")
        logger.info(f"测试 HTML 报告已保存到: {test_file}，邮件标题将为: {subject}")
        return

    if args.schedule:
        if not config.validate():
            return
        scheduler = Scheduler(config)
        scheduler.run(lambda: main_task(config))
    else:
        main_task(config)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info(" 程序已被用户中断")
        sys.exit(0)
    except Exception as exc:  # pragma: no cover - 入口的兜底异常
        logger.error("程序发生未预期的错误: %s", exc, exc_info=True)
        sys.exit(1)

