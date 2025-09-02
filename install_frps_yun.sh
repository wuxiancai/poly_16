#!/bin/bash
set -e

# 安装必要工具
apt update -y
apt install -y wget tar

# 下载 FRP 最新版 (amd64)
cd /usr/local
FRP_VER="0.61.0"
wget https://github.com/fatedier/frp/releases/download/v${FRP_VER}/frp_${FRP_VER}_linux_amd64.tar.gz
tar -xzf frp_${FRP_VER}_linux_amd64.tar.gz
mv frp_${FRP_VER}_linux_amd64 frp
cd frp

# 创建 frps 配置文件
cat > /usr/local/frp/frps.ini <<EOF
[common]
bind_port = 7000
dashboard_port = 7500
dashboard_user = admin
dashboard_pwd = admin123
EOF

# 创建 systemd 服务
cat > /etc/systemd/system/frps.service <<EOF
[Unit]
Description=FRP Server Service
After=network.target

[Service]
ExecStart=/usr/local/frp/frps -c /usr/local/frp/frps.ini
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
systemctl daemon-reexec
systemctl enable frps
systemctl restart frps

echo "==========================================="
echo "FRP 服务端部署完成！"
echo "Dashboard: http://119.28.204.194:7500"
echo "用户名：admin  密码：admin123"
echo "==========================================="