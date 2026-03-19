#!/bin/bash
# GitHub Trending 定时任务设置脚本
# 用于在 Linux/macOS 上设置 cron 任务

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_SCRIPT="$SCRIPT_DIR/run_trending.py"
LOG_FILE="$SCRIPT_DIR/logs/cron.log"

# 确保日志目录存在
mkdir -p "$SCRIPT_DIR/logs"

# 检测 Python 命令
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "错误：未找到 Python 命令"
    exit 1
fi

echo "=========================================="
echo "GitHub Trending 定时任务设置"
echo "=========================================="
echo ""
echo "脚本路径：$PYTHON_SCRIPT"
echo "日志路径：$LOG_FILE"
echo "Python 命令：$PYTHON_CMD"
echo ""

# 显示 cron 表达式选项
echo "请选择定时任务执行时间："
echo "1. 每天早上 8:00"
echo "2. 每天早上 9:00"
echo "3. 每天早上 10:00"
echo "4. 自定义时间"
echo ""
read -p "请输入选项 (1-4): " time_option

case $time_option in
    1)
        CRON_EXPR="0 8 * * *"
        TIME_DESC="每天 8:00"
        ;;
    2)
        CRON_EXPR="0 9 * * *"
        TIME_DESC="每天 9:00"
        ;;
    3)
        CRON_EXPR="0 10 * * *"
        TIME_DESC="每天 10:00"
        ;;
    4)
        read -p "请输入小时 (0-23): " hour
        read -p "请输入分钟 (0-59): " minute
        CRON_EXPR="$minute $hour * * *"
        TIME_DESC="每天 ${hour}:${minute}"
        ;;
    *)
        echo "无效选项"
        exit 1
        ;;
esac

echo ""
echo "将设置的定时任务：$TIME_DESC"
echo "Cron 表达式：$CRON_EXPR"
echo ""

# 创建 cron 任务
CRON_TASK="$CRON_EXPR cd $SCRIPT_DIR && $PYTHON_CMD $PYTHON_SCRIPT >> $LOG_FILE 2>&1"

echo "是否要添加此定时任务？"
read -p "(y/n): " confirm

if [ "$confirm" = "y" ]; then
    # 检查 crontab 是否可用
    if ! command -v crontab &> /dev/null; then
        echo "错误：crontab 命令不可用"
        exit 1
    fi

    # 获取当前 crontab
    CURRENT_CRONTAB=$(crontab -l 2>/dev/null || echo "")

    # 检查是否已存在相同的任务
    if echo "$CURRENT_CRONTAB" | grep -q "run_trending.py"; then
        echo "警告：已存在 run_trending.py 的定时任务"
        read -p "是否要覆盖？(y/n): " overwrite
        if [ "$overwrite" = "y" ]; then
            # 删除旧任务
            CURRENT_CRONTAB=$(echo "$CURRENT_CRONTAB" | grep -v "run_trending.py")
        else
            echo "已取消"
            exit 0
        fi
    fi

    # 添加新任务
    NEW_CRONTAB="$CURRENT_CRONTAB
# GitHub Trending - $TIME_DESC
$CRON_TASK"

    # 写入 crontab
    echo "$NEW_CRONTAB" | crontab -

    echo ""
    echo "✅ 定时任务设置成功!"
    echo ""
    echo "查看已设置的任务：crontab -l"
    echo "编辑任务：crontab -e"
    echo "删除任务：crontab -r"
    echo ""
    echo "日志文件：$LOG_FILE"
else
    echo "已取消"
fi
