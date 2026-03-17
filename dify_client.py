#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dify Workflow 客户端

负责：
- 调用 Dify Workflow 接口
- 返回用于邮件的 (subject, html) 内容

约定：
- 通过环境变量配置 Dify：
  - DIFY_API_KEY
  - DIFY_WORKFLOW_ID
  - DIFY_BASE_URL (可选，默认 https://api.dify.ai)
"""

import os
from datetime import date
from typing import Dict, Optional, Tuple

from mailer_core import logger

try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover - 运行时提示
    requests = None  # type: ignore
    logger.warning("未安装 requests 库，Dify 客户端将无法工作。请安装: pip install requests")


class DifyClient:
    """简单的 Dify Workflow API 客户端。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        workflow_id: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("DIFY_API_KEY", "")
        self.workflow_id = workflow_id or os.getenv("DIFY_WORKFLOW_ID", "")
        self.base_url = base_url or os.getenv("DIFY_BASE_URL", "https://api.dify.ai")

        if not self.api_key:
            logger.error("未配置 DIFY_API_KEY 环境变量")
        if not self.workflow_id:
            logger.error("未配置 DIFY_WORKFLOW_ID 环境变量")

    def _ensure_ready(self) -> bool:
        if requests is None:
            return False
        if not self.api_key or not self.workflow_id:
            return False
        return True

    def fetch_html_report(
        self,
        date_str: Optional[str] = None,
        extra_inputs: Optional[Dict] = None,
    ) -> Tuple[str, str]:
        """
        调用 Dify Workflow，返回 (subject, html)。

        期望 Workflow 输出：
        - outputs.html_report 或 outputs.html
        - 可选 outputs.subject
        """
        if not self._ensure_ready():
            raise RuntimeError("DifyClient 未正确配置或缺少 requests 库")

        date_str = date_str or date.today().isoformat()

        url = f"{self.base_url.rstrip('/')}/v1/workflows/{self.workflow_id}/run"
        payload: Dict = {
            "inputs": {
                "date": date_str,
            },
            "response_mode": "blocking",
            "user": "cron-job",
        }
        if extra_inputs:
            payload["inputs"].update(extra_inputs)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        logger.info("调用 Dify Workflow 获取 HTML 报告...")
        resp = requests.post(url, json=payload, headers=headers, timeout=60)  # type: ignore[arg-type]
        resp.raise_for_status()
        data = resp.json()

        outputs = data.get("data", {}).get("outputs", {}) or {}

        html = (
            outputs.get("html_report")
            or outputs.get("html")
            or data.get("answer")
        )

        if not html:
            logger.error("未从 Dify 响应中解析到 HTML 内容")
            raise RuntimeError("Dify 响应中缺少 html_report/html/answer 字段")

        subject = (
            outputs.get("subject")
            or f"今日技术 & 内容热点简报 - {date_str}"
        )

        return subject, html


__all__ = ["DifyClient"]

