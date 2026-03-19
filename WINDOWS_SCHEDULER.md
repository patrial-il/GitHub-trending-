# GitHub Trending 定时任务 - Windows 设置指南

## 方法一：使用任务计划程序（推荐）

### 步骤 1：创建批处理文件

创建 `run_trending.bat` 文件，内容如下：

```batch
@echo off
cd /d "%~dp0"
python run_trending.py --config mailer_config.json >> logs\cron.log 2>&1
```

### 步骤 2：打开任务计划程序

1. 按 `Win + R`，输入 `taskschd.msc`，回车
2. 点击右侧 "创建基本任务..."
3. 输入任务名称：`GitHub Trending`
4. 点击 "下一步"

### 步骤 3：设置触发器

1. 选择 "每天"
2. 点击 "下一步"
3. 设置开始时间（例如：09:00:00）
4. 点击 "下一步"

### 步骤 4：设置操作

1. 选择 "启动程序"
2. 点击 "下一步"
3. 程序/脚本：`python` 或完整路径如 `C:\Python39\python.exe`
4. 添加参数：`run_trending.py --config mailer_config.json`
5. 起始于：`D:\Code\26_17_02_begining`（你的项目目录）
6. 点击 "下一步"

### 步骤 5：完成

1. 勾选 "当点击完成时，打开此任务的属性对话框"
2. 点击 "完成"
3. 在属性对话框中：
   - 勾选 "不管用户是否登录都要运行"
   - 勾选 "使用最高权限运行"
   - 配置选项卡：勾选 "如果过了计划开始时间，立即启动任务"
4. 点击 "确定"

---

## 方法二：使用 PowerShell 脚本创建

以管理员身份运行 PowerShell，执行：

```powershell
$action = New-ScheduledTaskAction -Execute "python" -Argument "run_trending.py --config mailer_config.json" -WorkingDirectory "D:\Code\26_17_02_begining"
$trigger = New-ScheduledTaskTrigger -Daily -At 9am
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName "GitHub Trending" -Action $action -Trigger $trigger -Settings $settings -Principal $principal
```

---

## 常用命令

### 查看任务
```powershell
Get-ScheduledTask -TaskName "GitHub Trending"
```

### 手动运行任务
```powershell
Start-ScheduledTask -TaskName "GitHub Trending"
```

### 查看任务历史
```powershell
Get-ScheduledTaskInfo -TaskName "GitHub Trending"
```

### 删除任务
```powershell
Unregister-ScheduledTask -TaskName "GitHub Trending" -Confirm:$false
```

---

## 日志查看

日志文件位置：`logs\cron.log`

```powershell
Get-Content logs\cron.log -Tail 50 -Wait
```

---

## 测试

在设置定时任务前，先手动测试：

```bash
# 在命令行执行
cd D:\Code\26_17_02_begining
python run_trending.py --config mailer_config.json
```

或测试单个功能：

```bash
# 仅爬取数据
python run_trending.py --skip-email

# 仅发送邮件（使用现有缓存和 HTML）
python run_trending.py --email-only
```
