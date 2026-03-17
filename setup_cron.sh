#!/bin/bash

# GitHub Trending 邮件推送程序 - 定时任务设置脚本

echo "设置 GitHub Trending 定时邮件推送..."

# 检测当前脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 检查是否存在 github_trending_emailer.py
if [ ! -f "$SCRIPT_DIR/github_trending_emailer.py" ]; then
    echo "错误: 找不到 github_trending_emailer.py 文件"
    exit 1
fi

# 检查 config.json 是否存在
if [ ! -f "$SCRIPT_DIR/config.json" ]; then
    echo "错误: 找不到 config.json 文件"
    echo "请先创建 config.json 文件，格式如下："
    echo "{"
    echo "    \"sender_email\": \"your_email@gmail.com\","
    echo "    \"sender_password\": \"your_app_specific_password\","
    echo "    \"receiver_email\": \"recipient@gmail.com\""
    echo "}"
    exit 1
fi

# 获取当前用户的 crontab
CURRENT_CRON=$(crontab -l 2>/dev/null)

# 检查是否已有相同的定时任务
if echo "$CURRENT_CRON" | grep -q "github_trending_emailer.py"; then
    echo "定时任务已存在，正在移除旧任务..."
    NEW_CRON=$(echo "$CURRENT_CRON" | grep -v "github_trending_emailer.py")
elif echo "$CURRENT_CRON" | grep -q "github_trending_simplified.py"; then
    echo "发现旧的定时任务，正在移除..."
    NEW_CRON=$(echo "$CURRENT_CRON" | grep -v "github_trending_simplified.py")
else
    NEW_CRON="$CURRENT_CRON"
fi

# 添加新的定时任务 (每天上午9点执行)
NEW_LINE="0 9 * * * cd $SCRIPT_DIR && /usr/bin/python github_trending_emailer_enhanced.py >> $SCRIPT_DIR/logs/cron.log 2>&1"
NEW_CRON="${NEW_CRON}
$NEW_LINE"

# 应用新的 crontab
echo "$NEW_CRON" | crontab -

echo "✅ 定时任务已设置成功！"
echo "定时任务: 每天上午9:00自动推送 GitHub Trending 邮件"
echo ""
echo "当前的 crontab 内容："
crontab -l

echo ""
echo "💡 提示:"
echo "- 请确保已在 config.json 中正确配置邮箱信息"
echo "- 使用 Gmail 时，请使用应用专用密码而非账户登录密码"
echo "- 日志将保存到 logs/cron.log 文件中"
echo "- 如需取消定时任务，可运行: crontab -e 并删除对应行"