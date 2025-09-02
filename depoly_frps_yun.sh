#!/bin/bash

# ===============================
# 一键部署 FRPS + 家里 10 台 FRPC 配置
# ===============================

# 云服务器配置
FRPS_DIR=/usr/local/frp
FRPS_PORT=7000
DASHBOARD_PORT=7500
DASHBOARD_USER=admin
DASHBOARD_PWD=admin123

# 家里机器 IP 和映射端口
# 数组格式: "local_port:remote_port"
FRPC_CONFIGS=("5000:5000" "5001:5001" "5002:5002" "5003:5003" "5004:5004" "5005:5005" "5006:5006" "5007:5007" "5008:5008" "8888:8888")

# 获取云服务器公网 IP
PUBLIC_IP=$(curl -s ifconfig.me)

# ===============================
# 部署 FRPS
# ===============================
echo "==> 创建 FRPS 目录 $FRPS_DIR"
mkdir -p $FRPS_DIR
cd $FRPS_DIR || exit

# 下载 FRP
if [ ! -f frp_latest_linux_amd64.tar.gz ]; then
    echo "==> 下载 FRP"
    wget -q https://github.com/fatedier/frp/releases/latest/download/frp_0.59.0_linux_amd64.tar.gz -O frp_latest_linux_amd64.tar.gz
    tar xf frp_latest_linux_amd64.tar.gz --strip-components=1
fi

# 生成 frps.ini
cat > $FRPS_DIR/frps.ini <<EOF
[common]
bind_port = $FRPS_PORT
dashboard_port = $DASHBOARD_PORT
dashboard_user = $DASHBOARD_USER
dashboard_pwd = $DASHBOARD_PWD
EOF

# systemd 服务
cat > /etc/systemd/system/frps.service <<EOF
[Unit]
Description=FRP Server Service
After=network.target

[Service]
Type=simple
ExecStart=$FRPS_DIR/frps -c $FRPS_DIR/frps.ini
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable frps
systemctl restart frps

echo "==> FRPS 已启动: $PUBLIC_IP:$FRPS_PORT"
echo "Dashboard: http://$PUBLIC_IP:$DASHBOARD_PORT 用户:$DASHBOARD_USER 密码:$DASHBOARD_PWD"

# ===============================
# 生成家里机器 FRPC 部署脚本
# ===============================
FRPC_SCRIPT=/home/ubuntu/deploy_frpc.sh
cat > $FRPC_SCRIPT <<'EOF'
#!/bin/bash
# 家里机器 FRPC 自动部署脚本
# 用法: sudo bash deploy_frpc.sh <local_port> <remote_port>

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <local_port> <remote_port>"
    exit 1
fi

LOCAL_PORT=$1
REMOTE_PORT=$2

# 替换为云服务器公网 IP
SERVER_ADDR="PUBLIC_IP_PLACEHOLDER"
FRPS_PORT=7000

FRPC_DIR=/usr/local/frp
mkdir -p $FRPC_DIR
cd $FRPC_DIR || exit

# 下载 FRPC
if [ ! -f frp_latest_linux_amd64.tar.gz ]; then
    wget -q https://github.com/fatedier/frp/releases/latest/download/frp_0.59.0_linux_amd64.tar.gz -O frp_latest_linux_amd64.tar.gz
    tar xf frp_latest_linux_amd64.tar.gz --strip-components=1
fi

# 生成 frpc.ini
cat > $FRPC_DIR/frpc.ini <<EOF2
[common]
server_addr = $SERVER_ADDR
server_port = $FRPS_PORT

[web_$LOCAL_PORT]
type = tcp
local_ip = 127.0.0.1
local_port = $LOCAL_PORT
remote_port = $REMOTE_PORT
EOF2

# systemd 服务
cat > /etc/systemd/system/frpc.service <<EOF2
[Unit]
Description=FRP Client Service
After=network.target

[Service]
Type=simple
ExecStart=$FRPC_DIR/frpc -c $FRPC_DIR/frpc.ini
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF2

systemctl daemon-reload
systemctl enable frpc
systemctl restart frpc

echo "FRPC 已启动: 本地 $LOCAL_PORT -> 云端 $REMOTE_PORT"
EOF

# 替换脚本中的 PUBLIC_IP
sed -i "s|PUBLIC_IP_PLACEHOLDER|$PUBLIC_IP|g" $FRPC_SCRIPT
chmod +x $FRPC_SCRIPT

echo "==> 家里机器部署脚本已生成: $FRPC_SCRIPT"
echo "你可以将 $FRPC_SCRIPT 复制到家里机器执行"
echo "scp ubuntu@$PUBLIC_IP:/home/ubuntu/deploy_frpc.sh /home/user/"
echo "示例: sudo bash deploy_frpc.sh 5000 5000"