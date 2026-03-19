@echo off
REM GitHub Trending 定时任务执行脚本
REM 用于 Windows 任务计划程序

cd /d "%~dp0"
python run_trending.py --config mailer_config.json >> logs\cron.log 2>&1
