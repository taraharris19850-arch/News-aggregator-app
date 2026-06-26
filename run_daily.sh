#!/bin/bash
# 每日抓取脚本(供 launchd / cron 调用)。会把日志写到 logs/ 目录。
cd "$(dirname "$0")" || exit 1
STAMP="$(date '+%Y-%m-%d %H:%M:%S')"
echo "===== $STAMP 开始抓取 =====" >> logs/run.log
/usr/bin/env python3 scraper.py >> logs/run.log 2>&1
echo "===== $STAMP 结束 =====" >> logs/run.log
