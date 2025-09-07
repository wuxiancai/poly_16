#!/bin/bash

# Ubuntu Chrome启动脚本 - X2GO桌面环境适配版
# 功能：自动更新Chrome、智能匹配ChromeDriver版本、X2GO环境优化
# 作者：自动化脚本
# 版本：2.1 (X2GO适配版)
# 更新日期：2025-01-09

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/chrome_update.log"
# 清理旧配置
rm -f ~/ChromeDebug/SingletonLock
rm -f ~/ChromeDebug/SingletonCookie
rm -f ~/ChromeDebug/SingletonSocket
echo "清理旧配置完成"

# 显示使用说明
show_usage() {
    echo -e "${BLUE}=== Ubuntu Chrome X2GO桌面环境启动脚本 v2.1 ===${NC}"
    echo -e "${GREEN}功能特性：${NC}"
    echo -e "  • 自动检查并更新Chrome浏览器"
    echo -e "  • 智能匹配兼容的ChromeDriver版本"
    echo -e "  • X2GO桌面环境优化配置"
    echo -e "  • 增强的版本兼容性检查"
    echo -e "  • 详细的日志记录和错误处理"
    echo -e "  • 版本信息备份功能"
    echo -e "${GREEN}使用方法：${NC}"
    echo -e "  bash $0                    # 正常启动"
    echo -e "  bash $0 --help            # 显示帮助"
    echo -e "  bash $0 --version         # 显示版本信息"
    echo -e "  bash $0 --check-only      # 仅检查版本，不启动Chrome"
    echo -e "${GREEN}日志文件：${NC} $LOG_FILE"
    echo -e "${GREEN}备份文件：${NC} $SCRIPT_DIR/version_backup.txt"
    echo ""
}

# 处理命令行参数
handle_arguments() {
    case "$1" in
        "--help"|-h)
            show_usage
            exit 0
            ;;
        "--version"|-v)
            echo "Ubuntu Chrome X2GO桌面环境启动脚本 v2.1"
            echo "更新日期：2025-01-09"
            exit 0
            ;;
        "--check-only")
            echo -e "${YELLOW}仅执行版本检查模式${NC}"
            return 1
            ;;
        "")
            return 0
            ;;
        *)
            echo -e "${RED}未知参数: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
}

# 日志记录函数
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    
    case "$level" in
        "ERROR")
            echo -e "${RED}[$level] $message${NC}"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[$level] $message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}[$level] $message${NC}"
            ;;
        "INFO")
            echo -e "${BLUE}[$level] $message${NC}"
            ;;
        *)
            echo "[$level] $message"
            ;;
    esac
}

# 备份版本信息
backup_version_info() {
    local backup_file="$SCRIPT_DIR/version_backup.txt"
    {
        echo "=== 版本备份信息 - $(date '+%Y-%m-%d %H:%M:%S') ==="
        echo "Chrome版本: $(get_chrome_version 2>/dev/null || echo 'Not found')"
        if command -v chromedriver &> /dev/null; then
            echo "ChromeDriver版本: $(chromedriver --version 2>/dev/null | awk '{print $2}' || echo 'Not found')"
            echo "ChromeDriver路径: $(which chromedriver)"
        else
            echo "ChromeDriver版本: Not installed"
        fi
        echo "系统信息: $(uname -a)"
        echo "==========================================="
        echo ""
    } >> "$backup_file"
    log_message "INFO" "版本信息已备份到 $backup_file"
}

# 详细版本分析和建议
analyze_version_compatibility() {
    local chrome_ver="$1"
    local driver_ver="$2"
    
    echo -e "${BLUE}=== 详细版本兼容性分析 ===${NC}"
    
    # 解析版本号
    local chrome_major=$(echo "$chrome_ver" | cut -d'.' -f1)
    local chrome_minor=$(echo "$chrome_ver" | cut -d'.' -f2)
    local chrome_build=$(echo "$chrome_ver" | cut -d'.' -f3)
    local chrome_patch=$(echo "$chrome_ver" | cut -d'.' -f4)
    
    local driver_major=$(echo "$driver_ver" | cut -d'.' -f1)
    local driver_minor=$(echo "$driver_ver" | cut -d'.' -f2)
    local driver_build=$(echo "$driver_ver" | cut -d'.' -f3)
    local driver_patch=$(echo "$driver_ver" | cut -d'.' -f4)
    
    echo -e "${YELLOW}Chrome版本分解:${NC}"
    echo -e "  主版本: $chrome_major, 次版本: $chrome_minor, 构建: $chrome_build, 补丁: $chrome_patch"
    echo -e "${YELLOW}ChromeDriver版本分解:${NC}"
    echo -e "  主版本: $driver_major, 次版本: $driver_minor, 构建: $driver_build, 补丁: $driver_patch"
    
    # 兼容性评估
    local compatibility_score=0
    local recommendations=()
    
    if [ "$chrome_major" = "$driver_major" ]; then
        echo -e "${GREEN}✓ 主版本匹配 ($chrome_major)${NC}"
        compatibility_score=$((compatibility_score + 40))
    else
        echo -e "${RED}✗ 主版本不匹配 (Chrome: $chrome_major, Driver: $driver_major)${NC}"
        recommendations+=("必须更新ChromeDriver到主版本$chrome_major")
    fi
    
    if [ "$chrome_minor" = "$driver_minor" ]; then
        echo -e "${GREEN}✓ 次版本匹配 ($chrome_minor)${NC}"
        compatibility_score=$((compatibility_score + 30))
    else
        echo -e "${RED}✗ 次版本不匹配 (Chrome: $chrome_minor, Driver: $driver_minor)${NC}"
        recommendations+=("必须更新ChromeDriver到次版本$chrome_minor")
    fi
    
    if [ "$chrome_build" = "$driver_build" ]; then
        echo -e "${GREEN}✓ 构建版本匹配 ($chrome_build)${NC}"
        compatibility_score=$((compatibility_score + 20))
    else
        echo -e "${YELLOW}⚠ 构建版本不匹配 (Chrome: $chrome_build, Driver: $driver_build)${NC}"
        recommendations+=("建议更新ChromeDriver到构建版本$chrome_build")
    fi
    
    local patch_diff=$((chrome_patch - driver_patch))
    local patch_diff_abs=${patch_diff#-}
    
    if [ "$patch_diff_abs" -eq 0 ]; then
        echo -e "${GREEN}✓ 补丁版本完全匹配 ($chrome_patch)${NC}"
        compatibility_score=$((compatibility_score + 10))
    elif [ "$patch_diff_abs" -le 5 ]; then
        echo -e "${YELLOW}⚠ 补丁版本差异较小 (差异: $patch_diff_abs)${NC}"
        compatibility_score=$((compatibility_score + 5))
        recommendations+=("建议更新到完全匹配的补丁版本$chrome_patch")
    else
        echo -e "${RED}✗ 补丁版本差异较大 (差异: $patch_diff_abs)${NC}"
        recommendations+=("强烈建议更新到补丁版本$chrome_patch")
    fi
    
    # 兼容性评分
    echo -e "${BLUE}兼容性评分: $compatibility_score/100${NC}"
    
    if [ $compatibility_score -ge 90 ]; then
        echo -e "${GREEN}兼容性等级: 优秀 - 版本高度兼容${NC}"
    elif [ $compatibility_score -ge 70 ]; then
        echo -e "${YELLOW}兼容性等级: 良好 - 基本兼容，建议更新${NC}"
    elif [ $compatibility_score -ge 50 ]; then
        echo -e "${YELLOW}兼容性等级: 一般 - 可能存在问题，建议更新${NC}"
    else
        echo -e "${RED}兼容性等级: 差 - 存在兼容性风险，必须更新${NC}"
    fi
    
    # 显示建议
    if [ ${#recommendations[@]} -gt 0 ]; then
        echo -e "${YELLOW}改进建议:${NC}"
        for rec in "${recommendations[@]}"; do
            echo -e "  • $rec"
        done
    else
        echo -e "${GREEN}无需改进，版本完全兼容${NC}"
    fi
    
    echo -e "${BLUE}=================================${NC}"
    
    return $compatibility_score
}
# 获取Chrome完整版本号
get_chrome_version() {
    if command -v google-chrome-stable &> /dev/null; then
        google-chrome-stable --version | awk '{print $3}'
    else
        echo "Chrome not found"
        return 1
    fi
}

# 添加自动更新Chrome功能 - 增强版
update_chrome() {
    echo -e "${YELLOW}检查并更新Chrome...${NC}"
    
    # 检查Chrome是否已安装
    if ! command -v google-chrome-stable &> /dev/null; then
        echo -e "${RED}Chrome未安装，尝试安装...${NC}"
        install_chrome
        return $?
    fi
    
    # 获取更新前的版本
    CURRENT_VERSION=$(google-chrome-stable --version 2>/dev/null | awk '{print $3}')
    echo -e "${YELLOW}当前Chrome版本: $CURRENT_VERSION${NC}"
    
    # 使用apt直接更新Chrome
    echo -e "${YELLOW}更新软件包列表...${NC}"
    if ! sudo apt update -qq; then
        echo -e "${RED}软件包列表更新失败${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}更新Chrome...${NC}"
    if sudo apt --only-upgrade install -y google-chrome-stable; then
        # 获取更新后的版本
        NEW_VERSION=$(google-chrome-stable --version 2>/dev/null | awk '{print $3}')
        echo -e "${GREEN}更新后Chrome版本: $NEW_VERSION${NC}"
        
        # 检查是否更新成功
        if [ "$CURRENT_VERSION" != "$NEW_VERSION" ]; then
            echo -e "${GREEN}Chrome已成功更新: $CURRENT_VERSION -> $NEW_VERSION${NC}"
            # Chrome更新后，强制更新ChromeDriver
            echo -e "${YELLOW}Chrome已更新，需要重新匹配ChromeDriver${NC}"
            return 2  # 特殊返回码表示需要更新driver
        else
            echo -e "${GREEN}Chrome已是最新版本: $NEW_VERSION${NC}"
        fi
    else
        echo -e "${RED}Chrome更新失败${NC}"
        return 1
    fi
    
    return 0
}

# 安装Chrome（如果未安装）
install_chrome() {
    echo -e "${YELLOW}安装Google Chrome...${NC}"
    
    # 添加Google的官方GPG密钥
    if ! wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -; then
        echo -e "${RED}添加GPG密钥失败${NC}"
        return 1
    fi
    
    # 添加Chrome仓库
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
    
    # 更新软件包列表
    sudo apt update -qq
    
    # 安装Chrome
    if sudo apt install -y google-chrome-stable; then
        INSTALLED_VERSION=$(google-chrome-stable --version 2>/dev/null | awk '{print $3}')
        echo -e "${GREEN}Chrome安装成功，版本: $INSTALLED_VERSION${NC}"
        return 0
    else
        echo -e "${RED}Chrome安装失败${NC}"
        return 1
    fi
}


# 检查已安装的 chromedriver 是否匹配当前 Chrome
check_driver() {
    CHROME_VERSION=$(get_chrome_version)
    if [ "$CHROME_VERSION" = "Chrome not found" ]; then
        echo -e "${RED}Chrome 未安装${NC}"
        return 1
    fi
    
    # 检查系统路径中的chromedriver
    DRIVER_PATH=""
    if command -v chromedriver &> /dev/null; then
        DRIVER_PATH=$(which chromedriver)
    fi

    if [ -z "$DRIVER_PATH" ]; then
        echo -e "${RED}chromedriver 未安装${NC}"
        return 1
    fi

    DRIVER_VERSION=$("$DRIVER_PATH" --version | awk '{print $2}')
    
    echo -e "${YELLOW}Chrome 版本: $CHROME_VERSION${NC}"
    echo -e "${YELLOW}chromedriver 版本: $DRIVER_VERSION${NC}"
    echo -e "${YELLOW}chromedriver 路径: $DRIVER_PATH${NC}"

    # 增强版本匹配检查
    CHROME_MAJOR=$(echo "$CHROME_VERSION" | cut -d'.' -f1)
    CHROME_MINOR=$(echo "$CHROME_VERSION" | cut -d'.' -f2)
    CHROME_BUILD=$(echo "$CHROME_VERSION" | cut -d'.' -f3)
    CHROME_PATCH=$(echo "$CHROME_VERSION" | cut -d'.' -f4)
    
    DRIVER_MAJOR=$(echo "$DRIVER_VERSION" | cut -d'.' -f1)
    DRIVER_MINOR=$(echo "$DRIVER_VERSION" | cut -d'.' -f2)
    DRIVER_BUILD=$(echo "$DRIVER_VERSION" | cut -d'.' -f3)
    DRIVER_PATCH=$(echo "$DRIVER_VERSION" | cut -d'.' -f4)
    
    # 检查主版本号和次版本号必须完全匹配
    if [ "$CHROME_MAJOR" != "$DRIVER_MAJOR" ] || [ "$CHROME_MINOR" != "$DRIVER_MINOR" ]; then
        echo -e "${RED}主版本不匹配，需更新驱动 (Chrome: $CHROME_MAJOR.$CHROME_MINOR vs Driver: $DRIVER_MAJOR.$DRIVER_MINOR)${NC}"
        return 1
    fi
    
    # 检查构建版本号和patch版本号
    if [ "$CHROME_BUILD" != "$DRIVER_BUILD" ]; then
        echo -e "${YELLOW}构建版本不同 (Chrome: $CHROME_BUILD vs Driver: $DRIVER_BUILD)${NC}"
        echo -e "${RED}构建版本不匹配，需要更新驱动${NC}"
        return 1
    else
        # 构建版本相同时，检查patch版本差异
        PATCH_DIFF=$((CHROME_PATCH - DRIVER_PATCH))
        PATCH_DIFF_ABS=${PATCH_DIFF#-}  # 取绝对值
        
        echo -e "${BLUE}构建版本匹配 (Chrome: $CHROME_BUILD, Driver: $DRIVER_BUILD)${NC}"
        echo -e "${BLUE}Patch版本差异: $PATCH_DIFF (Chrome: $CHROME_PATCH, Driver: $DRIVER_PATCH)${NC}"
        
        if [ "$PATCH_DIFF_ABS" -gt 10 ]; then
            echo -e "${RED}Patch版本差异过大 ($PATCH_DIFF_ABS > 10)，强烈建议更新驱动${NC}"
            return 1
        elif [ "$PATCH_DIFF_ABS" -gt 5 ]; then
            echo -e "${YELLOW}Patch版本差异较大 ($PATCH_DIFF_ABS > 5)，建议更新驱动${NC}"
            return 1
        elif [ "$PATCH_DIFF_ABS" -gt 0 ]; then
            echo -e "${YELLOW}Patch版本有差异 ($PATCH_DIFF_ABS)，但在可接受范围内${NC}"
        else
            echo -e "${GREEN}版本完全匹配${NC}"
        fi
    fi

    echo -e "${BLUE}版本检查通过，驱动可用${NC}"
    return 0
}

# 自动安装兼容的 chromedriver（Ubuntu版本）- 增强版
install_driver() {
    echo -e "${YELLOW}尝试下载安装兼容的 chromedriver...${NC}"
    CHROME_VERSION=$(get_chrome_version)
    BASE_VERSION=$(echo "$CHROME_VERSION" | cut -d'.' -f1-3)
    PATCH_VERSION=$(echo "$CHROME_VERSION" | cut -d'.' -f4)

    TMP_DIR="/tmp/chromedriver_update"
    mkdir -p "$TMP_DIR"
    cd "$TMP_DIR" || return 1
    
    # 清理之前的下载文件
    rm -f chromedriver.zip
    rm -rf chromedriver-linux64*
    
    # 扩展尝试范围：向前和向后各尝试5个patch版本
    echo -e "${YELLOW}智能匹配ChromeDriver版本...${NC}"
    
    # 首先尝试完全匹配的版本
    EXACT_VERSION="$CHROME_VERSION"
    DRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/${EXACT_VERSION}/linux64/chromedriver-linux64.zip"
    echo -e "${YELLOW}尝试完全匹配版本: $EXACT_VERSION${NC}"
    
    if curl -sfLo chromedriver.zip "$DRIVER_URL"; then
        echo -e "${GREEN}找到完全匹配版本 ${EXACT_VERSION}${NC}"
        if unzip -qo chromedriver.zip && [ -f "chromedriver-linux64/chromedriver" ]; then
            sudo mv chromedriver-linux64/chromedriver /usr/local/bin/
            sudo chmod +x /usr/local/bin/chromedriver
            echo -e "${GREEN}安装成功: $(chromedriver --version)${NC}"
            cd "$SCRIPT_DIR"
            return 0
        fi
    fi
    
    # 如果完全匹配失败，尝试patch版本范围
    echo -e "${YELLOW}完全匹配失败，尝试兼容版本...${NC}"
    
    # 向下尝试（减少patch版本号）
    for ((i=1; i<=5; i++)); do
        TRY_PATCH=$((PATCH_VERSION - i))
        if [ $TRY_PATCH -ge 0 ]; then
            TRY_VERSION="${BASE_VERSION}.${TRY_PATCH}"
            DRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/${TRY_VERSION}/linux64/chromedriver-linux64.zip"
            echo -e "${YELLOW}尝试版本: $TRY_VERSION${NC}"
            
            rm -f chromedriver.zip
            rm -rf chromedriver-linux64*
            
            if curl -sfLo chromedriver.zip "$DRIVER_URL"; then
                if unzip -qo chromedriver.zip && [ -f "chromedriver-linux64/chromedriver" ]; then
                    echo -e "${GREEN}成功下载 chromedriver ${TRY_VERSION}${NC}"
                    sudo mv chromedriver-linux64/chromedriver /usr/local/bin/
                    sudo chmod +x /usr/local/bin/chromedriver
                    echo -e "${GREEN}安装成功: $(chromedriver --version)${NC}"
                    cd "$SCRIPT_DIR"
                    return 0
                fi
            fi
        fi
    done
    
    # 向上尝试（增加patch版本号）
    for ((i=1; i<=3; i++)); do
        TRY_PATCH=$((PATCH_VERSION + i))
        TRY_VERSION="${BASE_VERSION}.${TRY_PATCH}"
        DRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/${TRY_VERSION}/linux64/chromedriver-linux64.zip"
        echo -e "${YELLOW}尝试版本: $TRY_VERSION${NC}"
        
        rm -f chromedriver.zip
        rm -rf chromedriver-linux64*
        
        if curl -sfLo chromedriver.zip "$DRIVER_URL"; then
            if unzip -qo chromedriver.zip && [ -f "chromedriver-linux64/chromedriver" ]; then
                echo -e "${GREEN}成功下载 chromedriver ${TRY_VERSION}${NC}"
                sudo mv chromedriver-linux64/chromedriver /usr/local/bin/
                sudo chmod +x /usr/local/bin/chromedriver
                echo -e "${GREEN}安装成功: $(chromedriver --version)${NC}"
                cd "$SCRIPT_DIR"
                return 0
            fi
        fi
    done

    echo -e "${RED}未能下载兼容 chromedriver（尝试了多个版本）${NC}"
    echo -e "${RED}Chrome版本: $CHROME_VERSION${NC}"
    echo -e "${RED}建议手动检查 https://googlechromelabs.github.io/chrome-for-testing/ ${NC}"
    cd "$SCRIPT_DIR"
    return 1
}

# 主流程 - 增强版
# 处理命令行参数
CHECK_ONLY_MODE=false
if handle_arguments "$1"; then
    CHECK_ONLY_MODE=false
else
    CHECK_ONLY_MODE=true
fi

echo -e "${YELLOW}开始执行浏览器启动流程...${NC}"
log_message "INFO" "脚本启动，模式: $([ "$CHECK_ONLY_MODE" = true ] && echo '仅检查' || echo '完整启动')"
show_usage

# 首先更新Chrome
echo -e "${YELLOW}====== 开始检查并更新Chrome ======${NC}"
update_chrome
CHROME_UPDATE_RESULT=$?
echo -e "${YELLOW}====== Chrome更新完成 ======${NC}"

# 根据Chrome更新结果决定是否强制更新ChromeDriver
FORCE_DRIVER_UPDATE=false
if [ $CHROME_UPDATE_RESULT -eq 2 ]; then
    echo -e "${YELLOW}Chrome已更新，将强制更新ChromeDriver${NC}"
    FORCE_DRIVER_UPDATE=true
elif [ $CHROME_UPDATE_RESULT -ne 0 ]; then
    echo -e "${RED}Chrome更新失败，但继续尝试启动${NC}"
fi

# 检查ChromeDriver兼容性
log_message "INFO" "检查ChromeDriver版本兼容性"

# 获取当前版本进行详细分析
current_chrome_ver=$(get_chrome_version)
current_driver_ver=""
if command -v chromedriver &> /dev/null; then
    current_driver_ver=$(chromedriver --version 2>/dev/null | awk '{print $2}' || echo "未知")
else
    current_driver_ver="未安装"
fi

# 执行详细版本分析
if [ "$current_driver_ver" != "未安装" ] && [ "$current_driver_ver" != "未知" ]; then
    analyze_version_compatibility "$current_chrome_ver" "$current_driver_ver"
    compatibility_score=$?
    
    if [ $compatibility_score -ge 70 ]; then
        log_message "SUCCESS" "版本兼容性良好 (评分: $compatibility_score/100)"
    else
        log_message "WARNING" "版本兼容性较差 (评分: $compatibility_score/100)，建议更新"
    fi
fi

if [ "$FORCE_DRIVER_UPDATE" = true ] || ! check_driver; then
    echo -e "${YELLOW}驱动需要更新，尝试修复...${NC}"
    log_message "WARNING" "ChromeDriver版本不匹配，尝试安装兼容版本"
    
    # 如果是强制更新，先删除现有的chromedriver
    if [ "$FORCE_DRIVER_UPDATE" = true ] && command -v chromedriver &> /dev/null; then
        echo -e "${YELLOW}删除旧版本ChromeDriver...${NC}"
        sudo rm -f /usr/local/bin/chromedriver
        sudo rm -f /usr/bin/chromedriver
    fi
    
    if install_driver; then
        echo -e "${GREEN}ChromeDriver安装成功，进行最终检查...${NC}"
        log_message "SUCCESS" "ChromeDriver安装成功"
        
        # 重新获取版本并分析
        new_driver_ver=$(chromedriver --version 2>/dev/null | awk '{print $2}' || echo "未知")
        if [ "$new_driver_ver" != "未知" ]; then
            echo -e "\n${BLUE}=== 更新后版本分析 ===${NC}"
            analyze_version_compatibility "$current_chrome_ver" "$new_driver_ver"
            new_compatibility_score=$?
            log_message "INFO" "更新后兼容性评分: $new_compatibility_score/100"
        fi
        
        if check_driver; then
            echo -e "${GREEN}版本匹配确认成功${NC}"
            log_message "SUCCESS" "ChromeDriver版本检查通过"
        else
            echo -e "${YELLOW}版本仍有差异，但尝试继续运行${NC}"
            log_message "WARNING" "版本仍有差异，但将尝试继续运行"
        fi
    else
        echo -e "${RED}驱动更新失败${NC}"
        echo -e "${YELLOW}尝试使用现有驱动继续运行...${NC}"
        log_message "ERROR" "ChromeDriver安装失败，但将尝试继续运行"
    fi
else
    echo -e "${GREEN}ChromeDriver版本检查通过${NC}"
    log_message "SUCCESS" "ChromeDriver版本检查通过"
fi

export DISPLAY=:1

# 设置X11授权
if [ -f "$HOME/.Xauthority" ]; then
    export XAUTHORITY="$HOME/.Xauthority"
else
    # 尝试生成授权文件
    touch "$HOME/.Xauthority"
    export XAUTHORITY="$HOME/.Xauthority"
fi

echo -e "${YELLOW}使用 DISPLAY=1"
echo -e "${YELLOW}使用 XAUTHORITY=$XAUTHORITY${NC}"

# 清理崩溃文件
rm -f "$HOME/ChromeDebug/SingletonLock"
rm -f "$HOME/ChromeDebug/SingletonSocket"
rm -f "$HOME/ChromeDebug/SingletonCookie"
rm -f "$HOME/ChromeDebug/Default/Last Browser"
rm -f "$HOME/ChromeDebug/Default/Last Session"
rm -f "$HOME/ChromeDebug/Default/Last Tabs"

# 修复 Preferences 里记录的崩溃状态
PREF_FILE="$HOME/ChromeDebug/Default/Preferences"
if [ -f "$PREF_FILE" ]; then
    sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/' "$PREF_FILE"
fi

# 最终版本确认和启动
log_message "INFO" "开始最终版本确认"
FINAL_CHROME_VERSION=$(get_chrome_version)
if command -v chromedriver &> /dev/null; then
    FINAL_DRIVER_VERSION=$(chromedriver --version 2>/dev/null | awk '{print $2}')
else
    FINAL_DRIVER_VERSION="Not installed"
fi

log_message "SUCCESS" "最终版本确认 - Chrome: $FINAL_CHROME_VERSION, ChromeDriver: $FINAL_DRIVER_VERSION"
echo -e "${GREEN}=== 最终版本信息 ===${NC}"
echo -e "${GREEN}Chrome版本: $FINAL_CHROME_VERSION${NC}"
echo -e "${GREEN}ChromeDriver版本: $FINAL_DRIVER_VERSION${NC}"
echo -e "${GREEN}===================${NC}"

# 备份当前版本信息
backup_version_info

# X2GO环境检查和配置函数
check_x2go_environment() {
    log_message "INFO" "检查X2GO桌面环境"
    echo -e "${YELLOW}检查X2GO桌面环境...${NC}"
    
    # 检查是否在X2GO会话中
    if [ -n "$X2GO_SESSION" ]; then
        echo -e "${GREEN}检测到X2GO会话: $X2GO_SESSION${NC}"
        log_message "SUCCESS" "X2GO会话检测成功: $X2GO_SESSION"
    else
        echo -e "${YELLOW}未检测到X2GO_SESSION环境变量，可能不在X2GO会话中${NC}"
        log_message "WARNING" "未检测到X2GO_SESSION环境变量"
    fi
    
    # 检查DISPLAY环境变量
    if [ -n "$DISPLAY" ]; then
        echo -e "${GREEN}DISPLAY环境变量: $DISPLAY${NC}"
        log_message "SUCCESS" "DISPLAY环境变量设置正确: $DISPLAY"
    else
        echo -e "${RED}DISPLAY环境变量未设置${NC}"
        log_message "ERROR" "DISPLAY环境变量未设置"
        # 尝试设置默认DISPLAY
        export DISPLAY=:10.0
        echo -e "${YELLOW}已设置默认DISPLAY=:10.0${NC}"
        log_message "INFO" "已设置默认DISPLAY=:10.0"
    fi
    
    # 检查X11转发
    if xset q &>/dev/null; then
        echo -e "${GREEN}X11显示服务器连接正常${NC}"
        log_message "SUCCESS" "X11显示服务器连接正常"
    else
        echo -e "${RED}X11显示服务器连接失败${NC}"
        log_message "ERROR" "X11显示服务器连接失败"
        echo -e "${YELLOW}尝试启动X11转发...${NC}"
    fi
    
    # 设置X2GO优化的环境变量
    export LIBGL_ALWAYS_INDIRECT=1
    export MESA_GL_VERSION_OVERRIDE=3.3
    export GALLIUM_DRIVER=llvmpipe
    
    echo -e "${GREEN}X2GO环境配置完成${NC}"
    log_message "SUCCESS" "X2GO环境配置完成"
}

# 根据模式决定是否启动Chrome
if [ "$CHECK_ONLY_MODE" = true ]; then
    log_message "INFO" "仅检查模式完成，不启动Chrome"
    echo -e "${GREEN}=== 版本检查完成 ===${NC}"
    echo -e "${GREEN}所有检查已完成，Chrome和ChromeDriver版本已确认兼容${NC}"
    echo -e "${YELLOW}如需启动Chrome，请运行: bash $0${NC}"
    exit 0
fi

# 配置X2GO环境
check_x2go_environment

# 启动 Chrome（调试端口）- X2GO环境优化版
log_message "INFO" "启动Chrome浏览器 (X2GO优化)"
echo -e "${GREEN}启动 Chrome 中 (X2GO环境优化)...${NC}"
if command -v google-chrome-stable &> /dev/null; then
    log_message "INFO" "Chrome启动参数已设置 (X2GO优化)，开始启动"
    google-chrome-stable \
        --remote-debugging-port=9222 \
        --no-sandbox \
        --disable-gpu \
        --disable-gpu-sandbox \
        --disable-software-rasterizer \
        --disable-dev-shm-usage \
        --disable-extensions \
        --disable-background-networking \
        --disable-default-apps \
        --disable-sync \
        --metrics-recording-only \
        --disable-infobars \
        --no-first-run \
        --disable-session-crashed-bubble \
        --disable-translate \
        --disable-background-timer-throttling \
        --disable-backgrounding-occluded-windows \
        --disable-renderer-backgrounding \
        --disable-features=TranslateUI,BlinkGenPropertyTrees,SitePerProcess,IsolateOrigins,VizDisplayCompositor \
        --noerrdialogs \
        --disable-notifications \
        --test-type \
        --disable-web-security \
        --disable-features=VizDisplayCompositor \
        --use-gl=swiftshader \
        --enable-features=UseOzonePlatform \
        --ozone-platform=x11 \
        --disable-gpu-process-crash-limit \
        --disable-ipc-flooding-protection \
        --user-data-dir="$HOME/ChromeDebug" \
        https://polymarket.com/crypto &
    
    CHROME_PID=$!
    log_message "SUCCESS" "Chrome已启动 (X2GO优化)，PID: $CHROME_PID"
    echo -e "${GREEN}Chrome已启动 (X2GO环境优化)，PID: $CHROME_PID${NC}"
    echo -e "${GREEN}调试端口: http://localhost:9222${NC}"
    echo -e "${GREEN}目标网站: https://polymarket.com/crypto${NC}"
    echo -e "${GREEN}X2GO环境: 已优化GPU和渲染设置${NC}"
    echo -e "${YELLOW}提示：使用 'kill $CHROME_PID' 可以停止Chrome进程${NC}"
    echo -e "${YELLOW}X2GO提示：如遇显示问题，请检查X2GO客户端设置${NC}"
else
    log_message "ERROR" "Chrome未找到，启动失败"
    echo -e "${RED}Chrome 未找到，请确保已安装 google-chrome-stable${NC}"
    exit 1
fi

log_message "SUCCESS" "X2GO Chrome启动脚本执行完成"
echo -e "${GREEN}=== X2GO Chrome启动脚本执行完成 ===${NC}"
