#!/bin/bash
set -e

# ========= 配置 =========
SUB_URL="https://10ncydlf.flsubcn.cc:2096/zvlqjih1t/mukeyvbugo4xzyjj?singbox=1&extend=1"
CONFIG_DIR="/etc/sing-box"
CONFIG_FILE="$CONFIG_DIR/config.json"
UPDATE_SCRIPT="/usr/local/bin/singbox-refresh.sh"
# ========================

apt update
apt install -y curl wget unzip jq cron

# 获取最新 sing-box 版本
SB_VERSION=$(curl -s https://api.github.com/repos/SagerNet/sing-box/releases/latest | jq -r '.tag_name')
wget -O /tmp/sing-box.zip https://github.com/SagerNet/sing-box/releases/download/${SB_VERSION}/sing-box-${SB_VERSION}-linux-amd64v3.zip
unzip -o /tmp/sing-box.zip -d /usr/local/bin/
mv /usr/local/bin/sing-box*/sing-box /usr/local/bin/sing-box
chmod +x /usr/local/bin/sing-box
rm -rf /usr/local/bin/sing-box-*
rm -f /tmp/sing-box.zip

mkdir -p $CONFIG_DIR

# ========== 创建刷新脚本 ==========
cat > $UPDATE_SCRIPT <<'EOF'
#!/bin/bash
set -e

SUB_URL="https://10ncydlf.flsubcn.cc:2096/zvlqjih1t/mukeyvbugo4xzyjj?singbox=1&extend=1"
CONFIG_DIR="/etc/sing-box"
CONFIG_FILE="$CONFIG_DIR/config.json"

# 拉取订阅
curl -sL "$SUB_URL" -o $CONFIG_DIR/sub.json

# 生成配置文件（带健康检查和自动切换）
jq --argjson nodes "$(jq -r '.outbounds' $CONFIG_DIR/sub.json)" '
{
  "log": { "level": "info" },
  "dns": {
    "servers": [
      { "address": "8.8.8.8" },
      { "address": "1.1.1.1" }
    ]
  },
  "inbounds": [
    { "type": "socks", "listen": "127.0.0.1", "listen_port": 7890 },
    { "type": "http",  "listen": "127.0.0.1", "listen_port": 7890 }
  ],
  "outbounds": (
    $nodes + [
      {
        "type": "selector",
        "tag": "proxy",
        "outbounds": ($nodes | map(.tag)),
        "default": ($nodes | .[0].tag),
        "health_check": {
          "interval": "30s",
          "url": "http://www.gstatic.com/generate_204"
        }
      },
      { "type": "direct", "tag": "direct" },
      { "type": "block",  "tag": "block" }
    ]
  ),
  "route": {
    "auto_detect_interface": true,
    "rules": [
      { "outbound": "proxy" }
    ]
  }
}
' > $CONFIG_FILE

# 重启 sing-box
systemctl restart sing-box
echo "[$(date '+%F %T')] ✅ Sing-Box 配置已刷新并重启" >> /var/log/sing-box-update.log
EOF

chmod +x $UPDATE_SCRIPT

# ========== 首次运行一次 ==========
$UPDATE_SCRIPT

# ========== 创建 systemd 服务 ==========
cat >/etc/systemd/system/sing-box.service <<EOF
[Unit]
Description=Sing-Box Proxy Service
After=network.target

[Service]
ExecStart=/usr/local/bin/sing-box run -c $CONFIG_FILE
Restart=always
RestartSec=3
User=root
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reexec
systemctl enable sing-box
systemctl restart sing-box

# ========== 设置全局代理环境变量 ==========
grep -q "http_proxy" /etc/profile || cat >>/etc/profile <<'EOF'
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export all_proxy=socks5://127.0.0.1:7890
EOF
source /etc/profile

# ========== 配置 cron 每天 00:45 自动刷新 ==========
(crontab -l 2>/dev/null; echo "45 0 * * * $UPDATE_SCRIPT") | crontab -

echo "✅ Sing-Box 已部署完成"
echo "👉 代理端口: 127.0.0.1:7890"
echo "👉 每天 00:45 自动刷新订阅并重启"
echo "👉 查看运行日志: journalctl -u sing-box -f"
echo "👉 刷新日志文件: /var/log/sing-box-update.log"