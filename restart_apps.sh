#!/bin/bash

# ==========================================================
# PTSS & Aegis 통합 재시작 스크립트 (restart_apps.sh)
# ==========================================================

# 1. PTSS 재시작
echo "------------------------------------------"
echo "[1/2] PTSS (Terminal & SFTP) 재시작 중..."
cd /home/az001a/Script/ptss
pkill -9 -f 'python3 ptss.py'
nohup python3 ptss.py > ptss.log 2>&1 &
echo "✅ PTSS 구동 완료! (Port: 6001)"

# 2. Aegis (홈 컨트롤) 재시작
echo "[2/2] Aegis (Home Control) 재시작 중..."
cd /home/az001a/Script/home_control
pkill -9 -f 'python3 -u web_server.py'
nohup python3 -u web_server.py > web.log 2>&1 &
echo "✅ Aegis 구동 완료! (Port: 5700)"

echo "------------------------------------------"
echo "🚀 모든 웹 서비스가 백그라운드에서 정상 재시작되었습니다."
echo "상태 확인: ps -ef | grep .py"
echo "------------------------------------------"
