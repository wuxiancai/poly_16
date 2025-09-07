#!/bin/bash
set -e

echo "🚀 开始安装 X2Go Server..."

# 当前执行用户
CURRENT_USER=$(whoami)
echo "👤 当前用户: $CURRENT_USER"

# 确保系统更新
sudo apt-get update -y
sudo apt-get upgrade -y

# 检查是否已安装 LXDE
if dpkg -l | grep -q lxde-core; then
    echo "✅ 检测到系统已安装 LXDE，跳过安装步骤"
else
    echo "📦 未检测到 LXDE，开始安装..."
    sudo apt-get install -y lxde
    echo "✅ LXDE 安装完成"
fi

# 安装 X2Go Server
if dpkg -l | grep -q x2goserver; then
    echo "✅ X2Go Server 已安装，跳过"
else
    echo "📦 开始安装 X2Go Server..."
    sudo apt-get install -y x2goserver x2goserver-xsession
    echo "✅ X2Go Server 安装完成"
fi

# 确认当前用户存在（一般一定存在）
if id "$CURRENT_USER" &>/dev/null; then
    echo "✅ 用户 $CURRENT_USER 已存在"
else
    echo "⚠️ 用户 $CURRENT_USER 不存在，创建中..."
    sudo adduser --disabled-password --gecos "" "$CURRENT_USER"
fi

# 设置当前用户密码
echo "$CURRENT_USER:noneboy" | sudo chpasswd
echo "✅ 用户 $CURRENT_USER 密码已设置为 noneboy"

# 开放 X2Go 使用的 SSH 22 端口
if command -v ufw &>/dev/null; then
    sudo ufw allow 22/tcp || true
    echo "✅ 已允许 SSH 22 端口"
else
    echo "⚠️ 未检测到 ufw，跳过防火墙配置"
fi

echo "🎉 安装完成！现在你可以在 macOS 上用 X2Go Client 登录："
echo "  - 主机: <你的云服务器IP>"
echo "  - 用户名: $CURRENT_USER"
echo "  - 密码: noneboy"
echo "  - 会话类型: LXDE"