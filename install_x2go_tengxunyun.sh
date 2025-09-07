#!/bin/bash

# X2GO + LXDE 一键安装脚本 - 腾讯云 Ubuntu Server 22.04
# 作者: Auto Generated Script
# 日期: $(date '+%Y-%m-%d')
# 用途: 在腾讯云Ubuntu Server 22.04上安装LXDE桌面环境和X2GO服务端

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要使用root用户运行此脚本！"
        log_info "请使用普通用户运行: bash $0"
        exit 1
    fi
}

# 检查系统版本
check_system() {
    if [[ ! -f /etc/os-release ]]; then
        log_error "无法检测系统版本"
        exit 1
    fi
    
    source /etc/os-release
    if [[ "$ID" != "ubuntu" ]] || [[ "$VERSION_ID" != "22.04" ]]; then
        log_warning "此脚本专为Ubuntu 22.04设计，当前系统: $PRETTY_NAME"
        read -p "是否继续安装？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "安装已取消"
            exit 0
        fi
    fi
}

# 检查网络连接
check_network() {
    log_info "检查网络连接..."
    if ! ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        log_error "网络连接失败，请检查网络设置"
        exit 1
    fi
    log_success "网络连接正常"
}

# 更新系统包列表
update_system() {
    log_info "更新系统包列表..."
    sudo apt update
    log_success "系统包列表更新完成"
}

# 检查并安装LXDE
install_lxde() {
    log_info "检查LXDE安装状态..."
    
    if dpkg -l | grep -q "^ii.*lxde-core"; then
        log_success "LXDE已安装，跳过安装步骤"
        return 0
    fi
    
    log_info "开始安装LXDE桌面环境..."
    
    # 安装LXDE核心组件
    sudo apt install -y lxde-core lxde-common
    
    # 安装额外的桌面组件
    sudo apt install -y \    
        lxterminal \        # 终端
        pcmanfm \           # 文件管理器
        leafpad \           # 文本编辑器
        firefox \           # 浏览器
        synaptic \          # 软件包管理器
        gdebi \             # deb包安装器
        network-manager-gnome  # 网络管理器
    
    log_success "LXDE桌面环境安装完成"
}

# 检查并安装X2GO服务端
install_x2go_server() {
    log_info "检查X2GO服务端安装状态..."
    
    if dpkg -l | grep -q "^ii.*x2goserver"; then
        log_success "X2GO服务端已安装，跳过安装步骤"
        return 0
    fi
    
    log_info "开始安装X2GO服务端..."
    
    # 添加X2GO官方PPA源
    if ! grep -q "x2go" /etc/apt/sources.list.d/* 2>/dev/null; then
        sudo apt install -y software-properties-common
        sudo add-apt-repository -y ppa:x2go/stable
        sudo apt update
    fi
    
    # 安装X2GO服务端组件
    sudo apt install -y \    
        x2goserver \        # X2GO服务端
        x2goserver-xsession \  # 会话支持
        x2golxdebindings    # LXDE绑定
    
    # 启动并启用X2GO服务
    sudo systemctl enable x2goserver
    sudo systemctl start x2goserver
    
    log_success "X2GO服务端安装完成"
}

# 配置用户密码
setup_user_password() {
    local current_user=$(whoami)
    log_info "为用户 $current_user 设置密码..."
    
    # 检查用户是否已有密码设置
    if sudo passwd -S "$current_user" | grep -q "P"; then
        log_warning "用户 $current_user 已设置密码"
        read -p "是否重新设置密码为 'noneboy'？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "跳过密码设置"
            return 0
        fi
    fi
    
    # 设置密码为noneboy
    echo "$current_user:noneboy" | sudo chpasswd
    log_success "用户 $current_user 密码已设置为: noneboy"
}

# 配置防火墙
setup_firewall() {
    log_info "配置防火墙规则..."
    
    # 检查ufw状态
    if sudo ufw status | grep -q "Status: active"; then
        # 允许X2GO端口(22)
        sudo ufw allow 22/tcp comment "SSH/X2GO"
        log_success "防火墙规则已配置"
    else
        log_info "防火墙未启用，跳过配置"
    fi
}

# 优化系统配置
optimize_system() {
    log_info "优化系统配置..."
    
    # 创建X2GO会话目录
    mkdir -p ~/.x2go
    
    # 设置LXDE为默认桌面环境
    if [[ ! -f ~/.xsession ]]; then
        echo "exec startlxde" > ~/.xsession
        chmod +x ~/.xsession
    fi
    
    # 创建桌面目录
    mkdir -p ~/Desktop
    
    log_success "系统配置优化完成"
}

# 显示安装信息
show_installation_info() {
    local current_user=$(whoami)
    local server_ip=$(curl -s ifconfig.me 2>/dev/null || echo "获取失败")
    
    echo
    echo "======================================"
    log_success "X2GO + LXDE 安装完成！"
    echo "======================================"
    echo
    echo "连接信息:"
    echo "  服务器IP: $server_ip"
    echo "  用户名: $current_user"
    echo "  密码: noneboy"
    echo "  端口: 22 (SSH/X2GO)"
    echo "  会话类型: LXDE"
    echo
    echo "客户端下载:"
    echo "  Windows: https://code.x2go.org/releases/X2GoClient_latest_mswin32-setup.exe"
    echo "  macOS: https://code.x2go.org/releases/X2GoClient_latest_macosx_10_13.dmg"
    echo "  Linux: sudo apt install x2goclient"
    echo
    echo "连接步骤:"
    echo "  1. 下载并安装X2GO客户端"
    echo "  2. 创建新会话，填入上述连接信息"
    echo "  3. 会话类型选择 'LXDE'"
    echo "  4. 点击连接即可使用远程桌面"
    echo
    log_warning "请确保腾讯云安全组已开放22端口！"
    echo "======================================"
}

# 主函数
main() {
    echo "======================================"
    echo "  X2GO + LXDE 一键安装脚本"
    echo "  适用于: 腾讯云 Ubuntu Server 22.04"
    echo "======================================"
    echo
    
    # 执行安装步骤
    check_root
    check_system
    check_network
    update_system
    install_lxde
    install_x2go_server
    setup_user_password
    setup_firewall
    optimize_system
    show_installation_info
    
    log_success "所有安装步骤已完成！"
}

# 错误处理
trap 'log_error "安装过程中发生错误，请检查日志"; exit 1' ERR

# 运行主函数
main "$@"