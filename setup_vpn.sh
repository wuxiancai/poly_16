#!/bin/bash
set -e

# ========= 配置 =========
SUB_URL="https://10ncydlf.flsubcn.cc:2096/zvlqjih1t/mukeyvbugo4xzyjj?singbox=1&extend=1"

# 检测操作系统类型
OS_TYPE=""
if [[ "$(uname)" == "Darwin" ]]; then
    OS_TYPE="macos"
    echo "检测到 macOS 系统"
    # macOS 路径配置
    BINARY_PATH="/usr/local/bin/sing-box"
    CONFIG_DIR="/usr/local/etc/sing-box"
    SERVICE_LOG_DIR="/usr/local/var/log"
    UPDATE_SCRIPT="/usr/local/bin/singbox-refresh.sh"
    LOG_FILE="/usr/local/var/log/sing-box-update.log"
elif [[ "$(uname)" == "Linux" ]]; then
    # 进一步检测Linux发行版
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        if [[ "$ID" == "ubuntu" ]]; then
            OS_TYPE="ubuntu"
            echo "检测到 Ubuntu 系统 (版本: $VERSION_ID)"
        else
            OS_TYPE="linux"
            echo "检测到 Linux 系统 (发行版: $ID)"
        fi
    else
        OS_TYPE="linux"
        echo "检测到 Linux 系统"
    fi
    # Ubuntu/Linux 路径配置
    BINARY_PATH="/usr/local/bin/sing-box"
    CONFIG_DIR="/etc/sing-box"
    SERVICE_LOG_DIR="/var/log"
    UPDATE_SCRIPT="/usr/local/bin/singbox-refresh.sh"
    LOG_FILE="/var/log/sing-box-update.log"
else
    echo "错误: 不支持的操作系统 $(uname)"
    echo "此脚本仅支持 macOS 和 Ubuntu Server"
    exit 1
fi

# 通用配置
CONFIG_FILE="$CONFIG_DIR/config.json"
# ========================

# 检查是否为root用户
if [[ $EUID -ne 0 ]]; then
   echo "错误: 此脚本需要root权限运行"
   exit 1
fi

# 创建必要的目录
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$CONFIG_DIR"

# 安装系统依赖
echo "正在检查和安装系统依赖..."
if [[ "$OS_TYPE" == "macos" ]]; then
    # 检查是否安装了Homebrew
    if ! command -v brew &> /dev/null; then
        echo "错误: 需要安装Homebrew"
        echo "请运行: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    echo "正在检查依赖包..."
    # 确保必要的工具已安装
    for tool in curl wget unzip jq tar; do
        if ! command -v $tool &> /dev/null; then
            echo "正在安装 $tool..."
            brew install $tool
        fi
    done
elif [[ "$OS_TYPE" == "ubuntu" || "$OS_TYPE" == "linux" ]]; then
    # 更新软件包列表
    echo "正在更新软件包列表..."
    if ! apt update; then
        echo "错误: 无法更新软件包列表，请检查网络连接和软件源配置"
        exit 1
    fi
    
    # 安装依赖包
    echo "正在安装依赖包..."
    if ! apt install -y curl wget unzip jq cron tar; then
        echo "错误: 依赖包安装失败"
        exit 1
    fi
    
    # 确保cron服务运行
    if command -v systemctl &> /dev/null; then
        systemctl enable cron
        systemctl start cron
    fi
fi

# 检测系统架构
ARCH=$(uname -m)
case $ARCH in
    x86_64)
        SB_ARCH="amd64"
        ;;
    aarch64|arm64)
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

# 根据操作系统选择平台
if [[ "$(uname)" == "Darwin" ]]; then
    SB_PLATFORM="darwin"
else
    SB_PLATFORM="linux"
fi

DOWNLOAD_URL="https://github.com/SagerNet/sing-box/releases/download/${SB_VERSION}/sing-box-${VERSION_NUMBER}-${SB_PLATFORM}-${SB_ARCH}.tar.gz"
echo "下载地址: $DOWNLOAD_URL"

# 检查是否提供了本地文件
if [[ -n "$1" && -f "$1" ]]; then
    echo "使用本地文件: $1"
    cp "$1" "$TMP_DIR/sing-box.tar.gz"
else
    # 下载文件
    echo "正在下载 sing-box..."
    if ! curl -L --connect-timeout 30 --max-time 300 --retry 3 --retry-delay 5 -o "$TMP_DIR/sing-box.tar.gz" "$DOWNLOAD_URL"; then
        echo "错误: 下载失败，请检查网络连接"
        echo "下载地址: $DOWNLOAD_URL"
        echo ""
        echo "您可以手动下载文件并重新运行脚本:"
        echo "1. 下载: $DOWNLOAD_URL"
        echo "2. 运行: sudo $0 /path/to/downloaded/file.tar.gz"
        exit 1
    fi
fi

echo "正在解压文件..."
if ! tar -xzf "$TMP_DIR/sing-box.tar.gz" -C "$TMP_DIR/"; then
    echo "错误: 解压失败"
    exit 1
fi

echo "正在安装 sing-box..."
if ! install -m 755 "$TMP_DIR"/sing-box*/sing-box "$BINARY_PATH"; then
    echo "错误: 安装失败"
    exit 1
fi

# 验证安装
if ! "$BINARY_PATH" version &> /dev/null; then
    echo "错误: sing-box 安装验证失败"
    exit 1
fi

echo "✅ sing-box 安装成功: $("$BINARY_PATH" version | head -1)"

echo "清理临时文件..."
rm -rf "$TMP_DIR"

mkdir -p "$CONFIG_DIR"

# ========== 创建刷新脚本 ==========
echo "正在创建刷新脚本..."
cat > $UPDATE_SCRIPT <<'SCRIPT_EOF'
#!/bin/bash
set -e

SUB_URL="https://10ncydlf.flsubcn.cc:2096/zvlqjih1t/mukeyvbugo4xzyjj?singbox=1&extend=1"
CONFIG_DIR="REPLACE_CONFIG_DIR"
CONFIG_FILE="REPLACE_CONFIG_FILE"
LOG_FILE="REPLACE_LOG_FILE"
BINARY_PATH="REPLACE_BINARY_PATH"

echo "[$(date '+%F %T')] 开始刷新订阅..." >> $LOG_FILE

# 拉取订阅
echo "正在拉取订阅..."
if ! curl -sL --connect-timeout 10 --max-time 30 "$SUB_URL" -o $CONFIG_DIR/sub.json; then
    echo "[$(date '+%F %T')] ❌ 订阅拉取失败" >> $LOG_FILE
    exit 1
fi

# 检查订阅文件是否存在且不为空
if [[ ! -s $CONFIG_DIR/sub.json ]]; then
    echo "❌ 订阅文件为空或不存在"
    echo "[$(date '+%F %T')] ❌ 订阅文件为空" >> $LOG_FILE
    exit 1
fi

# 显示订阅文件的前几行用于调试
echo "订阅文件内容预览:"
head -5 $CONFIG_DIR/sub.json
echo "[$(date '+%F %T')] 订阅文件大小: $(wc -c < $CONFIG_DIR/sub.json) 字节" >> $LOG_FILE

# 检查订阅文件是否为有效JSON
if ! jq empty $CONFIG_DIR/sub.json 2>/dev/null; then
    echo "❌ 订阅文件不是有效的JSON格式"
    echo "[$(date '+%F %T')] ❌ 订阅文件JSON格式无效" >> $LOG_FILE
    echo "文件内容:" >> $LOG_FILE
    head -10 $CONFIG_DIR/sub.json >> $LOG_FILE
    exit 1
fi

# 检查是否包含outbounds字段
if ! jq -e '.outbounds' $CONFIG_DIR/sub.json >/dev/null 2>&1; then
    echo "❌ 订阅文件中没有找到outbounds字段"
    echo "[$(date '+%F %T')] ❌ 订阅文件缺少outbounds字段" >> $LOG_FILE
    echo "文件结构:" >> $LOG_FILE
    jq 'keys' $CONFIG_DIR/sub.json >> $LOG_FILE 2>&1
    exit 1
fi

# 生成配置文件（带健康检查和自动切换）
echo "正在生成配置文件..."
echo "[$(date '+%F %T')] 开始生成配置文件" >> $LOG_FILE

# 首先提取节点信息
echo "正在提取节点信息..."
if ! NODES=$(jq -c '.outbounds' $CONFIG_DIR/sub.json 2>/dev/null); then
    echo "[$(date '+%F %T')] ❌ 提取节点信息失败" >> $LOG_FILE
    exit 1
fi

# 验证NODES变量是否为有效JSON
if [[ -z "$NODES" || "$NODES" == "null" ]]; then
    echo "❌ 订阅文件中没有找到有效的节点信息"
    echo "[$(date '+%F %T')] ❌ 订阅文件中没有有效节点" >> $LOG_FILE
    exit 1
fi

# 验证是否为有效的JSON数组
if ! echo "$NODES" | jq -e 'type == "array"' >/dev/null 2>&1; then
    echo "❌ 节点数据格式无效，不是JSON数组"
    echo "[$(date '+%F %T')] ❌ 节点数据格式无效" >> $LOG_FILE
    echo "节点数据内容: $NODES" >> $LOG_FILE
    exit 1
fi

NODE_COUNT=$(echo "$NODES" | jq 'length')
echo "节点数量: $NODE_COUNT" 
echo "[$(date '+%F %T')] 提取到 $NODE_COUNT 个节点" >> $LOG_FILE

if [[ "$NODE_COUNT" -eq 0 ]]; then
    echo "❌ 订阅文件中没有可用的节点"
    echo "[$(date '+%F %T')] ❌ 订阅文件中没有可用节点" >> $LOG_FILE
    exit 1
fi

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
    { "type": "socks", "listen": "127.0.0.1", "listen_port": 7892 },
     { "type": "http",  "listen": "127.0.0.1", "listen_port": 8891 }
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
    echo "[$(date '+%F %T')] ❌ 配置文件生成失败" >> $LOG_FILE
    exit 1
fi

echo "[$(date '+%F %T')] ✅ 配置文件生成成功" >> $LOG_FILE

# 验证配置文件
if ! $BINARY_PATH check -c $CONFIG_FILE; then
    echo "[$(date '+%F %T')] ❌ 配置文件验证失败" >> $LOG_FILE
    exit 1
fi

# 重启 sing-box
echo "正在重启 sing-box 服务..."
if [[ "$(uname)" == "Darwin" ]]; then
    # macOS 使用 launchctl
    if ! launchctl unload /Library/LaunchDaemons/com.sing-box.plist 2>/dev/null; then
        echo "服务未运行，直接启动"
    fi
    if ! launchctl load /Library/LaunchDaemons/com.sing-box.plist; then
        echo "[$(date '+%F %T')] ❌ 服务重启失败" >> $LOG_FILE
        exit 1
    fi
    # 等待服务启动
    sleep 3
    if ! launchctl list | grep -q com.sing-box; then
        echo "[$(date '+%F %T')] ❌ 服务启动失败" >> $LOG_FILE
        exit 1
    fi
else
    # Linux 使用 systemctl
    if ! systemctl restart sing-box; then
        echo "[$(date '+%F %T')] ❌ 服务重启失败" >> $LOG_FILE
        exit 1
    fi
    # 等待服务启动
    sleep 3
    if ! systemctl is-active --quiet sing-box; then
        echo "[$(date '+%F %T')] ❌ 服务启动失败" >> $LOG_FILE
        exit 1
    fi
fi
echo "[$(date '+%F %T')] ✅ Sing-Box 配置已刷新并重启" >> $LOG_FILE
SCRIPT_EOF

# 替换刷新脚本中的占位符
if [[ "$OS_TYPE" == "macos" ]]; then
    # macOS 使用 -i ''
    sed -i '' "s#REPLACE_CONFIG_DIR#$CONFIG_DIR#g" $UPDATE_SCRIPT
    sed -i '' "s#REPLACE_CONFIG_FILE#$CONFIG_FILE#g" $UPDATE_SCRIPT
    sed -i '' "s#REPLACE_LOG_FILE#$LOG_FILE#g" $UPDATE_SCRIPT
    sed -i '' "s#REPLACE_BINARY_PATH#$BINARY_PATH#g" $UPDATE_SCRIPT
else
    # Ubuntu/Linux 使用 -i
    sed -i "s#REPLACE_CONFIG_DIR#$CONFIG_DIR#g" $UPDATE_SCRIPT
    sed -i "s#REPLACE_CONFIG_FILE#$CONFIG_FILE#g" $UPDATE_SCRIPT
    sed -i "s#REPLACE_LOG_FILE#$LOG_FILE#g" $UPDATE_SCRIPT
    sed -i "s#REPLACE_BINARY_PATH#$BINARY_PATH#g" $UPDATE_SCRIPT
fi

chmod +x $UPDATE_SCRIPT

# ========== 创建系统服务 ==========
echo "正在创建系统服务..."
if [[ "$OS_TYPE" == "macos" ]]; then
    # 创建 macOS launchd 服务
    echo "正在创建 launchd 服务..."
    # 确保日志目录存在
    mkdir -p "$SERVICE_LOG_DIR"
    
    cat >/Library/LaunchDaemons/com.sing-box.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.sing-box</string>
    <key>ProgramArguments</key>
    <array>
        <string>$BINARY_PATH</string>
        <string>run</string>
        <string>-c</string>
        <string>$CONFIG_FILE</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$SERVICE_LOG_DIR/sing-box.log</string>
    <key>StandardErrorPath</key>
    <string>$SERVICE_LOG_DIR/sing-box.error.log</string>
    <key>WorkingDirectory</key>
    <string>/tmp</string>
</dict>
</plist>
EOF
    
    # 设置权限
    chmod 644 /Library/LaunchDaemons/com.sing-box.plist
    chown root:wheel /Library/LaunchDaemons/com.sing-box.plist
else
    # 创建 Linux systemd 服务
    echo "正在创建 systemd 服务..."
    cat >/etc/systemd/system/sing-box.service <<EOF
[Unit]
Description=Sing-Box Proxy Service
Documentation=https://sing-box.sagernet.org/
After=network.target nss-lookup.target
Wants=network.target

[Service]
Type=simple
ExecStart=$BINARY_PATH run -c $CONFIG_FILE
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=3
RestartPreventExitStatus=23
User=root
Group=root
UMask=0027
LimitNOFILE=65535
LimitNPROC=65535
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sing-box

[Install]
WantedBy=multi-user.target
EOF
fi

# 启用和启动服务
if [[ "$OS_TYPE" == "macos" ]]; then
    echo "正在加载 launchd 服务..."
    if ! launchctl load /Library/LaunchDaemons/com.sing-box.plist; then
        echo "警告: launchd 服务加载失败，请检查配置"
    fi
    # 启动服务
    launchctl start com.sing-box
else
    echo "正在重载 systemd 配置..."
    systemctl daemon-reload
    echo "正在启用 sing-box 服务..."
    if ! systemctl enable sing-box; then
        echo "警告: systemd 服务启用失败"
    fi
    # 启动服务
    systemctl start sing-box
fi

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
export http_proxy=http://127.0.0.1:8891
export https_proxy=http://127.0.0.1:8891
export all_proxy=socks5://127.0.0.1:7892
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
sleep 3  # 等待服务启动

if [[ "$OS_TYPE" == "macos" ]]; then
    if launchctl list | grep -q com.sing-box; then
        echo "✅ sing-box 服务运行正常"
        echo "服务状态: $(launchctl list | grep com.sing-box)"
    else
        echo "❌ sing-box 服务启动失败"
        echo "请检查日志: tail -f $SERVICE_LOG_DIR/sing-box.error.log"
        exit 1
    fi
else
    if systemctl is-active --quiet sing-box; then
        echo "✅ sing-box 服务运行正常"
        echo "服务状态: $(systemctl is-active sing-box)"
    else
        echo "❌ sing-box 服务启动失败"
        echo "服务状态详情:"
        systemctl status sing-box --no-pager
        echo "请检查日志: journalctl -u sing-box -f"
        exit 1
    fi
fi

echo ""
echo "======================================"
echo "🎉 sing-box 部署完成!"
echo "======================================"
echo "代理信息:"
echo "  SOCKS5: 127.0.0.1:7892"
echo "  HTTP:   127.0.0.1:8891"
echo ""
echo "配置文件: $CONFIG_FILE"
echo "刷新脚本: $UPDATE_SCRIPT"
echo "日志文件: $LOG_FILE"
echo "服务日志: $SERVICE_LOG_DIR/sing-box.log"
echo ""
echo "定时任务: 每天 00:45 自动刷新订阅"
echo ""
echo "服务管理:"
if [[ "$OS_TYPE" == "macos" ]]; then
    echo "  查看状态: launchctl list | grep com.sing-box"
    echo "  停止服务: sudo launchctl unload /Library/LaunchDaemons/com.sing-box.plist"
    echo "  启动服务: sudo launchctl load /Library/LaunchDaemons/com.sing-box.plist"
    echo "  查看日志: tail -f $SERVICE_LOG_DIR/sing-box.log"
else
    echo "  查看状态: systemctl status sing-box"
    echo "  停止服务: systemctl stop sing-box"
    echo "  启动服务: systemctl start sing-box"
    echo "  重启服务: systemctl restart sing-box"
    echo "  查看日志: journalctl -u sing-box -f"
fi
echo ""
echo "环境变量已设置，重新登录后生效:"
echo "  export http_proxy=http://127.0.0.1:8891"
echo "  export https_proxy=http://127.0.0.1:8891"
echo "  export all_proxy=socks5://127.0.0.1:7892"
echo "======================================"