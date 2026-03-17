#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Trending 邮件推送程序 - 快捷入口（增强版）

此脚本提供一个简单的接口来运行 GitHub Trending 邮件推送程序（增强版）。
"""

import sys
import os
from pathlib import Path

def main():
    """主函数"""
    # 检查是否可以导入增强版程序
    try:
        # 将当前目录添加到模块搜索路径
        current_dir = Path(__file__).parent.absolute()
        sys.path.insert(0, str(current_dir))
        
        from github_trending_emailer_enhanced import main as emailer_main
        print("🚀 启动 GitHub Trending 邮件推送程序（增强版 - 带详细摘要）...")
        print("=" * 60)
        
        # 直接调用增强版程序的主函数
        emailer_main()
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请确保 github_trending_emailer_enhanced.py 文件存在于当前目录中")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 程序运行出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()