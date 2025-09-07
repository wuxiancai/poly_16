#!/bin/bash

# X2GO Host Key Verification Failed 修复脚本
# 功能：解决X2GO连接时的主机密钥验证失败问题
# 作者：自动化脚本
# 版本：1.0
# 更新日期：2025-01-09

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== X2GO Host Key Verification Failed 修复工具 ===${NC}"
echo -e "${YELLOW}此脚本将帮助解决X2GO连接时的主机密钥验证问题${NC}"
echo ""

# 显示使用说明
show_usage() {
    echo -e "${GREEN}常见解决方案：${NC}"
    echo -e "  1. 清除已知主机密钥"
    echo -e "  2. 重新生成SSH主机密钥"
    echo -e "  3. 配置SSH客户端跳过主机验证"
    echo -e "  4. 手动添加主机密钥"
    echo ""
    echo -e "${GREEN}使用方法：${NC}"
    echo -e "  bash $0 [服务器IP地址]    # 修复指定服务器的连接问题"
    echo -e "  bash $0 --help          # 显示帮助信息"
    echo ""
}

# 处理命令行参数
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_usage
    exit 0
fi

# 获取服务器IP
SERVER_IP="$1"
if [ -z "$SERVER_IP" ]; then
    echo -e "${YELLOW}请输入X2GO服务器的IP地址：${NC}"
    read -r SERVER_IP
    if [ -z "$SERVER_IP" ]; then
        echo -e "${RED}错误：必须提供服务器IP地址${NC}"
        exit 1
    fi
fi

echo -e "${BLUE}目标服务器IP：$SERVER_IP${NC}"
echo ""

# 解决方案1：清除已知主机密钥
fix_known_hosts() {
    echo -e "${YELLOW}方案1：清除已知主机密钥...${NC}"
    
    # 检查known_hosts文件是否存在
    if [ -f "$HOME/.ssh/known_hosts" ]; then
        echo -e "${BLUE}备份当前known_hosts文件...${NC}"
        cp "$HOME/.ssh/known_hosts" "$HOME/.ssh/known_hosts.backup.$(date +%Y%m%d_%H%M%S)"
        
        echo -e "${BLUE}从known_hosts中移除服务器密钥...${NC}"
        ssh-keygen -R "$SERVER_IP" 2>/dev/null
        
        echo -e "${GREEN}✓ 已清除服务器 $SERVER_IP 的主机密钥${NC}"
    else
        echo -e "${YELLOW}known_hosts文件不存在，跳过此步骤${NC}"
    fi
    echo ""
}

# 解决方案2：获取并添加新的主机密钥
add_host_key() {
    echo -e "${YELLOW}方案2：获取并添加新的主机密钥...${NC}"
    
    # 创建.ssh目录（如果不存在）
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
    
    echo -e "${BLUE}尝试获取服务器主机密钥...${NC}"
    
    # 使用ssh-keyscan获取主机密钥
    if ssh-keyscan -H "$SERVER_IP" >> "$HOME/.ssh/known_hosts" 2>/dev/null; then
        echo -e "${GREEN}✓ 成功添加服务器主机密钥${NC}"
    else
        echo -e "${RED}✗ 无法获取服务器主机密钥${NC}"
        echo -e "${YELLOW}可能的原因：${NC}"
        echo -e "  • 服务器未启动或无法访问"
        echo -e "  • SSH服务未运行"
        echo -e "  • 防火墙阻止连接"
        echo -e "  • IP地址错误"
    fi
    echo ""
}

# 解决方案3：创建SSH配置跳过主机验证（临时解决方案）
create_ssh_config() {
    echo -e "${YELLOW}方案3：配置SSH跳过主机验证（临时解决方案）...${NC}"
    
    SSH_CONFIG="$HOME/.ssh/config"
    
    # 备份现有配置
    if [ -f "$SSH_CONFIG" ]; then
        cp "$SSH_CONFIG" "$SSH_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # 添加配置
    echo "" >> "$SSH_CONFIG"
    echo "# X2GO服务器配置 - 跳过主机验证" >> "$SSH_CONFIG"
    echo "Host $SERVER_IP" >> "$SSH_CONFIG"
    echo "    StrictHostKeyChecking no" >> "$SSH_CONFIG"
    echo "    UserKnownHostsFile /dev/null" >> "$SSH_CONFIG"
    echo "    LogLevel QUIET" >> "$SSH_CONFIG"
    
    chmod 600 "$SSH_CONFIG"
    
    echo -e "${GREEN}✓ 已添加SSH配置跳过主机验证${NC}"
    echo -e "${RED}警告：此方法会降低安全性，仅建议临时使用${NC}"
    echo ""
}

# 解决方案4：测试连接
test_connection() {
    echo -e "${YELLOW}方案4：测试SSH连接...${NC}"
    
    echo -e "${BLUE}尝试连接到服务器...${NC}"
    
    # 测试SSH连接
    if timeout 10 ssh -o ConnectTimeout=5 -o BatchMode=yes "$SERVER_IP" exit 2>/dev/null; then
        echo -e "${GREEN}✓ SSH连接测试成功${NC}"
    else
        echo -e "${RED}✗ SSH连接测试失败${NC}"
        echo -e "${YELLOW}请检查：${NC}"
        echo -e "  • 服务器是否正在运行"
        echo -e "  • SSH服务是否启动"
        echo -e "  • 防火墙设置"
        echo -e "  • 网络连接"
    fi
    echo ""
}

# 显示X2GO客户端配置建议
show_x2go_config() {
    echo -e "${YELLOW}X2GO客户端配置建议：${NC}"
    echo -e "${BLUE}在X2GO客户端中：${NC}"
    echo -e "  1. 打开会话配置"
    echo -e "  2. 在'连接'选项卡中"
    echo -e "  3. 勾选'使用RSA/DSA密钥进行SSH身份验证'"
    echo -e "  4. 或者在'高级'选项中禁用'严格主机密钥检查'"
    echo ""
    echo -e "${BLUE}命令行连接测试：${NC}"
    echo -e "  ssh -o StrictHostKeyChecking=no $SERVER_IP"
    echo ""
}

# 主执行流程
echo -e "${GREEN}开始修复Host key verification failed问题...${NC}"
echo ""

# 执行修复步骤
fix_known_hosts
add_host_key
create_ssh_config
test_connection
show_x2go_config

echo -e "${GREEN}=== 修复完成 ===${NC}"
echo -e "${YELLOW}如果问题仍然存在，请检查：${NC}"
echo -e "  • X2GO服务器是否正确安装和配置"
echo -e "  • SSH服务是否正常运行"
    echo -e "  • 防火墙是否允许SSH连接（端口22）"
echo -e "  • 用户账户是否存在且有正确权限"
echo ""
echo -e "${BLUE}现在可以尝试重新连接X2GO${NC}"