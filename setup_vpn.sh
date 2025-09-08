#!/bin/bash
set -e

# ========= 配置 =========
SUB_URL="https://10ncydlf.flsubcn.cc:2096/zvlqjih1t/mukeyvbugo4xzyjj?singbox=1&extend=1"
CONFIG_DIR="/etc/sing-box"
CONFIG_FILE="$CONFIG_DIR/config.json"
UPDATE_SCRIPT="/usr/local/bin/singbox-refresh.sh"
# ========================

# 检查是否为root用户
if [[ $EUID -ne 0 ]]; then
   echo "错误: 此脚本需要root权限运行"
   exit 1
fi

echo "正在更新软件包列表..."
apt update
echo "正在安装依赖包..."
apt install -y curl wget unzip jq cron tar

# 检测系统架构
ARCH=$(uname -m)
case $ARCH in
    x86_64)
        SB_ARCH="amd64"
        ;;
    aarch64)
        SB_ARCH="arm64"
        ;;
    armv7l)
        SB_ARCH="armv7"
        ;;
    i686)
        SB_ARCH="386"
        ;;
    *)
        echo "不支持的架构: $ARCH"
        exit 1
        ;;
esac

# 获取最新 sing-box 版本
echo "正在获取最新版本信息..."
SB_VERSION=$(curl -s --connect-timeout 10 --max-time 30 https://api.github.com/repos/SagerNet/sing-box/releases/latest 2>/dev/null | jq -r '.tag_name' 2>/dev/null)

if [[ -z "$SB_VERSION" || "$SB_VERSION" == "null" ]]; then
    echo "警告: 无法获取最新版本，使用默认版本 v1.12.4"
    SB_VERSION="v1.12.4"
fi

echo "获取到版本: $SB_VERSION"

echo "将下载版本: $SB_VERSION，架构: $SB_ARCH"

TMP_DIR="/tmp/singbox_install"
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"

# 构建下载URL (移除版本号中的v前缀)
VERSION_NUMBER=${SB_VERSION#v}  # 移除v前缀
DOWNLOAD_URL="https://github.com/SagerNet/sing-box/releases/download/${SB_VERSION}/sing-box-${VERSION_NUMBER}-linux-${SB_ARCH}.tar.gz"
echo "下载地址: $DOWNLOAD_URL"

# 下载文件
echo "正在下载 sing-box..."
if ! wget --timeout=60 --tries=3 -O "$TMP_DIR/sing-box.tar.gz" "$DOWNLOAD_URL"; then
    echo "错误: 下载失败，请检查网络连接或版本号"
    exit 1
fi

echo "正在解压文件..."
if ! tar -xzf "$TMP_DIR/sing-box.tar.gz" -C "$TMP_DIR/"; then
    echo "错误: 解压失败"
    exit 1
fi

echo "正在安装 sing-box..."
if ! install -m 755 "$TMP_DIR"/sing-box*/sing-box /usr/local/bin/sing-box; then
    echo "错误: 安装失败"
    exit 1
fi

echo "清理临时文件..."
rm -rf "$TMP_DIR"

mkdir -p "$CONFIG_DIR"

# ========== 创建刷新脚本 ==========
echo "正在创建刷新脚本..."
cat > $UPDATE_SCRIPT <<'EOF'
#!/bin/bash
set -e

SUB_URL="https://10ncydlf.flsubcn.cc:2096/zvlqjih1t/mukeyvbugo4xzyjj?singbox=1&extend=1"
CONFIG_DIR="/etc/sing-box"
CONFIG_FILE="$CONFIG_DIR/config.json"

echo "[$(date '+%F %T')] 开始刷新订阅..." >> /var/log/sing-box-update.log

# 拉取订阅
echo "正在拉取订阅..."
if ! curl -sL --connect-timeout 10 --max-time 30 "$SUB_URL" -o $CONFIG_DIR/sub.json; then
    echo "[$(date '+%F %T')] ❌ 订阅拉取失败" >> /var/log/sing-box-update.log
    exit 1
fi

# 检查订阅文件是否有效
if ! jq empty $CONFIG_DIR/sub.json 2>/dev/null; then
    echo "[$(date '+%F %T')] ❌ 订阅文件格式无效" >> /var/log/sing-box-update.log
    exit 1
fi

# 生成配置文件（带健康检查和自动切换）
echo "正在生成配置文件..."
echo "[$(date '+%F %T')] 开始生成配置文件" >> /var/log/sing-box-update.log

# 首先提取节点信息
echo "正在提取节点信息..."
if ! NODES=$(jq -c '.outbounds' $CONFIG_DIR/sub.json 2>/dev/null); then
    echo "[$(date '+%F %T')] ❌ 提取节点信息失败" >> /var/log/sing-box-update.log
    exit 1
fi

echo "节点数量: $(echo "$NODES" | jq 'length')" 
echo "[$(date '+%F %T')] 提取到 $(echo "$NODES" | jq 'length') 个节点" >> /var/log/sing-box-update.log

# 生成基础配置
echo "正在生成基础配置..."
cat > $CONFIG_FILE << 'EOF'
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
  "outbounds": [],
  "route": {
    "auto_detect_interface": true,
    "rules": [
      { "outbound": "proxy" }
    ]
  }
}
EOF

# 使用jq合并节点信息
echo "正在合并节点配置..."
if ! jq --argjson nodes "$NODES" '
  .outbounds = ($nodes + [
    {
      "type": "selector",
      "tag": "proxy",
      "outbounds": ($nodes | map(.tag)),
      "default": ($nodes | if length > 0 then .[0].tag else "direct" end)
    },
    { "type": "direct", "tag": "direct" },
    { "type": "block", "tag": "block" }
  ])
' $CONFIG_FILE > $CONFIG_FILE.tmp && mv $CONFIG_FILE.tmp $CONFIG_FILE; then
    echo "[$(date '+%F %T')] ❌ 配置文件生成失败" >> /var/log/sing-box-update.log
    exit 1
fi

echo "[$(date '+%F %T')] ✅ 配置文件生成成功" >> /var/log/sing-box-update.log

# 验证配置文件
if ! /usr/local/bin/sing-box check -c $CONFIG_FILE; then
    echo "[$(date '+%F %T')] ❌ 配置文件验证失败" >> /var/log/sing-box-update.log
    exit 1
fi

# 重启 sing-box
echo "正在重启 sing-box 服务..."
if ! systemctl restart sing-box; then
    echo "[$(date '+%F %T')] ❌ 服务重启失败" >> /var/log/sing-box-update.log
    exit 1
fi

# 等待服务启动
sleep 3
if ! systemctl is-active --quiet sing-box; then
    echo "[$(date '+%F %T')] ❌ 服务启动失败" >> /var/log/sing-box-update.log
    exit 1
fi
echo "[$(date '+%F %T')] ✅ Sing-Box 配置已刷新并重启" >> /var/log/sing-box-update.log
EOF

chmod +x $UPDATE_SCRIPT

# ========== 创建 systemd 服务 ==========
echo "正在创建 systemd 服务..."
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

echo "正在重载 systemd 配置..."
systemctl daemon-reload
echo "正在启用 sing-box 服务..."
systemctl enable sing-box

# ========== 首次运行刷新脚本 ==========
echo "正在首次运行刷新脚本..."
if ! $UPDATE_SCRIPT; then
    echo "错误: 首次配置失败，请检查订阅地址"
    exit 1
fi

# ========== 设置全局代理环境变量 ==========
echo "正在设置全局代理环境变量..."
if ! grep -q "http_proxy" /etc/profile; then
    cat >>/etc/profile <<'EOF'
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export all_proxy=socks5://127.0.0.1:7890
EOF
    echo "环境变量已添加到 /etc/profile"
else
    echo "环境变量已存在，跳过设置"
fi

# ========== 配置 cron 每天 00:45 自动刷新 ==========
echo "正在配置定时任务..."
CRON_JOB="45 0 * * * $UPDATE_SCRIPT"
if ! crontab -l 2>/dev/null | grep -q "$UPDATE_SCRIPT"; then
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "定时任务已添加"
else
    echo "定时任务已存在，跳过设置"
fi

# ========== 验证服务状态 ==========
echo "正在验证服务状态..."
if systemctl is-active --quiet sing-box; then
    echo "✅ Sing-Box 服务运行正常"
else
    echo "⚠️  Sing-Box 服务未运行，请检查日志"
fi

echo ""
echo "🎉 Sing-Box 部署完成！"
echo "=============================="
echo "👉 代理端口: 127.0.0.1:7890 (HTTP/SOCKS)"
echo "👉 配置文件: $CONFIG_FILE"
echo "👉 刷新脚本: $UPDATE_SCRIPT"
echo "👉 定时刷新: 每天 00:45 自动更新订阅"
echo "👉 服务状态: systemctl status sing-box"
echo "👉 运行日志: journalctl -u sing-box -f"
echo "👉 刷新日志: /var/log/sing-box-update.log"
echo "👉 手动刷新: $UPDATE_SCRIPT"
echo "=============================="