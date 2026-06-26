#!/bin/bash
# 启动本地网页服务器,手机可在「同一 WiFi」下访问。
cd "$(dirname "$0")/web" || exit 1
PORT="${1:-8000}"
IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
echo "本机访问:   http://localhost:$PORT"
[ -n "$IP" ] && echo "手机访问:   http://$IP:$PORT   (手机与电脑连同一 WiFi)"
echo "按 Ctrl+C 停止"
exec python3 -m http.server "$PORT"
