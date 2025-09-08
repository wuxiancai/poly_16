#!/bin/bash

# ===========================
# Clash 一键安装与订阅配置
# ===========================

# 当前用户
USER_NAME=$(whoami)
HOME_DIR=$(eval echo "~$USER_NAME")

# Clash 配置目录
CLASH_DIR="$HOME_DIR/.config/clash"
CONFIG_FILE="$CLASH_DIR/config.yaml"

# Clash 订阅链接（替换为你的）
SUB_LINK="https://10ncydlf.flsubcn.cc:2096/zvlqjih1t/mukeyvbugo4xzyjj?clash=1&extend=1"

# ---------------------------
# 1. 安装依赖
# ---------------------------
sudo apt update
sudo apt install -y curl wget tar

# ---------------------------
# 2. 创建配置目录
# ---------------------------
mkdir -p "$CLASH_DIR"

# ---------------------------
# 3. 下载订阅配置
# ---------------------------
echo "下载 Clash 订阅配置..."
curl -k -o "$CONFIG_FILE" "$SUB_LINK"

# ---------------------------
# 4. 修改配置以支持局域网访问 Dashboard
# ---------------------------
echo "修改配置，允许局域网访问 Dashboard..."
# 允许局域网访问
sed -i 's/^external-controller:.*/external-controller: 0.0.0.0:9090/' "$CONFIG_FILE"
sed -i 's/^allow-lan:.*/allow-lan: true/' "$CONFIG_FILE"

# ---------------------------
# 5. 创建 systemd 服务
# ---------------------------
SERVICE_FILE="/etc/systemd/system/clash.service"
echo "创建 systemd 服务..."
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Clash Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/clash -d $CLASH_DIR
Restart=on-failure
User=$USER_NAME
Environment=HOME=$HOME_DIR

[Install]
WantedBy=multi-user.target
EOF

# ---------------------------
# 6. 启动服务并开机自启
# ---------------------------
sudo systemctl daemon-reload
sudo systemctl enable clash
sudo systemctl start clash

# ---------------------------
# 7. 输出提示信息
# ---------------------------
echo "=============================="
echo "Clash 已安装并启动！"
echo "局域网访问 Dashboard 请打开浏览器："
echo "http://$(hostname -I | awk '{print $1}'):9090/ui"
echo "HTTP/HTTPS 代理端口：7890"
echo "SOCKS5 代理端口：7891"
echo "=============================="