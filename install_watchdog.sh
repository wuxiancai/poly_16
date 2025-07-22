#!/bin/bash

set -e

# === 配置 ====
SCRIPT_NAME="watchdog.py"
SCRIPT_PATH="$HOME/$SCRIPT_NAME"
SERVICE_NAME="watchdog"
TIMER_NAME="$SERVICE_NAME.timer"
PYTHON_BIN=$(which python3)

# === 创建 watchdog.py ===
cat > "$SCRIPT_PATH" << 'EOF'
import psutil
import smtplib
from email.mime.text import MIMEText

EMAIL_USER = "huacaihuijin@126.com"
EMAIL_PASS = "PUaRF5FKeKJDrYH7"  # 网易授权码
SMTP_SERVER = "smtp.126.com"
SMTP_PORT = 465
EMAIL_TO = "huacaihuijin@126.com"

CPU_LOW = 30
CPU_HIGH = 95
MEM_LOW_MB = 920
MEM_HIGH_MB = 1700
# 获取当前主机名
HOSTNAME = socket.gethostname()

def send_email(subject, body):
    full_subject = f"[{HOSTNAME}] {subject}"
    full_body = f"主机名: {HOSTNAME}\n\n{body}"
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_TO

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
    except Exception as e:
        print(f"邮件发送失败: {e}")

def check_and_alert():
    cpu_percent = psutil.cpu_percent(interval=1)
    mem_used_mb = (psutil.virtual_memory().total - psutil.virtual_memory().available) / 1024 / 1024
    disk_usage = psutil.disk_usage('/')
    disk_free_gb = disk_usage.free / 1024 / 1024 / 1024

    if cpu_percent > CPU_HIGH:
        send_email("⚠️ CPU 过载", f"CPU 使用率过高：{cpu_percent:.1f}%")
    elif cpu_percent < CPU_LOW:
        send_email("⚠️ CPU 使用率过低", f"CPU 使用率过低：{cpu_percent:.1f}%")

    if mem_used_mb < MEM_LOW_MB:
        send_email("⚠️ 内存使用过低", f"当前内存使用：{mem_used_mb:.1f}MB")
    elif mem_used_mb > MEM_HIGH_MB:
        send_email("⚠️ 内存使用过高", f"当前内存使用：{mem_used_mb:.1f}MB")

    if disk_free_gb < 1:
        send_email("⚠️ 磁盘空间不足", f"可用磁盘空间仅 {disk_free_gb:.2f} GB")
        
if __name__ == "__main__":
    check_and_alert()
EOF

chmod +x "$SCRIPT_PATH"
echo "✅ 已创建 $SCRIPT_PATH"

# === 创建 systemd 服务 ===
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Resource Watchdog Script

[Service]
Type=oneshot
ExecStart=$PYTHON_BIN $SCRIPT_PATH
EOF

echo "✅ 已创建 $SERVICE_FILE"

# === 创建 systemd 定时器 ===
TIMER_FILE="/etc/systemd/system/$TIMER_NAME"
sudo bash -c "cat > $TIMER_FILE" <<EOF
[Unit]
Description=Run Watchdog Script Every 30 Minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=30min
Persistent=true

[Install]
WantedBy=timers.target
EOF

echo "✅ 已创建 $TIMER_FILE"

# === 启用定时器 ===
sudo systemctl daemon-reload
sudo systemctl enable --now "$TIMER_NAME"

echo "✅ watchdog.timer 已启动，每 30 分钟执行一次 $SCRIPT_PATH"