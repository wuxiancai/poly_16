#!/bin/bash

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "=== Ubuntu 自动化安装脚本 ==="

# 检查系统类型
if [[ "$(uname)" != "Linux" ]]; then
    echo "${RED}错误: 此脚本只能在 Linux 系统上运行${NC}"
    exit 1
fi

# 检查是否为Ubuntu系统
if ! grep -q "Ubuntu" /etc/os-release; then
    echo "${RED}警告: 此脚本专为 Ubuntu 系统设计,其他Linux发行版可能需要调整${NC}"
fi

CHIP_TYPE=$(uname -m)
echo "检测到芯片类型: $CHIP_TYPE"

# 自动确认所有提示
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

# 更新系统包列表
echo "更新系统包列表..."
sudo apt update

# 安装必要的系统依赖
echo "安装系统依赖..."
sudo apt install -y software-properties-common apt-transport-https ca-certificates gnupg lsb-release curl wget build-essential
sudo apt install -y unzip xvfb xauth x11-utils
# 安装图形界面相关依赖
sudo apt install -y libgtk-3-dev libx11-dev libxss1 libgconf-2-4 libnss3-dev libxrandr2 libasound2-dev libpangocairo-1.0-0 libatk1.0-dev libcairo-gobject2 libgtk-3-0 libgdk-pixbuf2.0-dev
# 确保安装了 python3-venv 和 python3-pip
echo "安装 python3-venv 和 python3-pip..."
sudo apt install -y python3-venv python3-pip python3-tk python3-dev

# ========================
# 配置区域：修改成你的域名
# ========================
DOMAIN="wuxiancai.win"   # 替换成你的域名
EMAIL="wuxiancai1978@gmail.com"  # 替换成你的邮箱，用于 Let's Encrypt
APP_PORT=8080             # 本地应用端口

# ========================
# 1️⃣ 安装 NGINX 和 Certbot
# ========================
echo "=== 更新系统并安装 NGINX + Certbot ==="
sudo apt install -y nginx certbot python3-certbot-nginx

# ========================
# 2️⃣ 创建反向代理配置
# ========================
echo "=== 创建 NGINX 反向代理配置 ==="
cat <<EOF | sudo tee /etc/nginx/sites-available/$DOMAIN > /dev/null
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

# 启用站点
sudo ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 检查 NGINX 配置
sudo nginx -t

# ========================
# 3️⃣ 重启 NGINX
# ========================
echo "=== 启动并启用 NGINX 服务 ==="
sudo systemctl reload nginx
sudo systemctl enable nginx

# ========================
# 4️⃣ 自动申请 HTTPS 证书
# ========================
echo "=== 使用 Certbot 自动申请 HTTPS 证书 ==="
sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos -m $EMAIL

# ========================
# 5️⃣ 自动设置 HTTP → HTTPS 重定向
# ========================
echo "=== 配置完成！HTTP 会自动跳转到 HTTPS ==="
echo "访问 https://$DOMAIN 就可以访问本地 $APP_PORT 服务了"

echo "=== 重启 NGINX 服务 ==="
sudo systemctl reload nginx
sudo systemctl enable nginx

echo "=== 部署完成！"
echo "访问 http://<你的服务器IP> 会自动反向代理到 127.0.0.1:8080"

# 创建虚拟环境
echo "创建虚拟环境..."
python3 -m venv venv --clear
source venv/bin/activate

# 升级 pip
echo "升级 pip..."
pip install --upgrade pip

# 安装依赖
echo "安装Python依赖..."
# 优先从requirements.txt安装
if [ -f "requirements.txt" ]; then
    echo "从requirements.txt安装依赖..."
    pip install --no-cache-dir -r requirements.txt
else
    echo "requirements.txt不存在，逐个安装依赖..."
    pip install --no-cache-dir selenium>=4.12
    pip install --no-cache-dir pyautogui
    pip install --no-cache-dir screeninfo
    pip install --no-cache-dir requests
    pip install --no-cache-dir flask>=2.2
    pip install --no-cache-dir websocket-client
    pip install --no-cache-dir psutil
    pip install --no-cache-dir urllib3
fi

# 安装GUI相关依赖（Ubuntu特有）
echo "安装GUI相关依赖..."
sudo apt install -y python3-xlib scrot
pip install --no-cache-dir python3-xlib

# 配置环境变量
echo "配置环境变量..."
if ! grep -q "# Python 配置" ~/.bashrc; then
    echo '# Python 配置' >> ~/.bashrc
    echo 'export PATH="/usr/bin:$PATH"' >> ~/.bashrc
    echo 'export TK_SILENCE_DEPRECATION=1' >> ~/.bashrc
    echo 'export DISPLAY=:0' >> ~/.bashrc
fi

# 获取脚本所在目录，作为项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

# 检查并安装 Chrome
echo "检查并安装 Chrome..."

# 添加Chrome存储库
if [ ! -f /etc/apt/sources.list.d/google-chrome.list ]; then
    echo "添加Google Chrome存储库..."
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    echo "deb [arch=amd64] https://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
    sudo apt update
fi

# 安装Chrome到系统
if ! command -v google-chrome-stable &> /dev/null; then
    echo "安装Google Chrome..."
    sudo apt install -y google-chrome-stable
    CHROME_INSTALLED=true
else
    echo "${GREEN}Chrome 已安装${NC}"
    CHROME_INSTALLED=true
fi

# 检查 ChromeDriver 是否已安装
if command -v chromedriver &> /dev/null; then
    echo "${GREEN}ChromeDriver 已安装${NC}"
    CHROMEDRIVER_INSTALLED=true
else
    echo "ChromeDriver 未安装"
    CHROMEDRIVER_INSTALLED=false
fi

# 安装 ChromeDriver 到系统路径
if [ "$CHROMEDRIVER_INSTALLED" = false ]; then
    echo "安装 ChromeDriver..."
    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"
    CHROME_VERSION=$(google-chrome-stable --version | awk '{print $3}' | cut -d'.' -f1-3)
    DRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}")
    if [ -z "$DRIVER_VERSION" ]; then
        DRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE")
    fi
    wget -O chromedriver.zip "https://chromedriver.storage.googleapis.com/${DRIVER_VERSION}/chromedriver_linux64.zip"
    unzip -o chromedriver.zip
    sudo mv chromedriver /usr/local/bin/
    sudo chmod +x /usr/local/bin/chromedriver
    rm chromedriver.zip
    cd - > /dev/null
    echo "${GREEN}ChromeDriver 已安装到 /usr/local/bin/chromedriver${NC}"
fi

# 设置Chrome启动脚本权限
chmod +x start_chrome_ubuntu.sh

# 创建自动启动脚本
cat > run_trader.sh << 'EOL'
#!/bin/bash

# 在VNC环境下,通常DISPLAY是:1
export DISPLAY=":1"

# 设置X11授权
if [ -f "$HOME/.Xauthority" ]; then
    export XAUTHORITY="$HOME/.Xauthority"
else
    # 尝试生成授权文件
    touch "$HOME/.Xauthority"
    export XAUTHORITY="$HOME/.Xauthority"
fi

echo -e "${YELLOW}使用 DISPLAY=$DISPLAY${NC}"
echo -e "${YELLOW}使用 XAUTHORITY=$XAUTHORITY${NC}"

# 打印接收到的参数，用于调试
echo "run_trader.sh received args: $@"

# 激活虚拟环境
source venv/bin/activate

# 运行交易程序
exec python3 -u crypto_trader.py "$@"
EOL

chmod +x run_trader.sh

# 验证安装
echo "=== 验证安装 ==="
echo "Python 路径: $(which python3)"
echo "Python 版本: $(python3 --version)"
echo "Pip 版本: $(pip3 --version)"
echo "Chrome 版本: $(google-chrome-stable --version 2>/dev/null || echo '未安装')"
echo "ChromeDriver 版本: $(chromedriver --version 2>/dev/null || echo '未安装')"
echo "已安装的Python包:"
pip3 list
echo "${GREEN}安装完成！${NC}"

echo "使用说明:"
echo "1. 直接运行 ./run_trader.sh 即可启动程序"
echo "2. 程序会自动启动 Chrome 并运行交易脚本"
echo "3. 所有配置已自动完成，无需手动操作"
echo "4. 如果遇到显示问题,请确保已设置DISPLAY环境变量"

# 自动清理安装缓存
sudo apt autoremove -y
sudo apt autoclean
pip3 cache purge

# 添加安装检查
echo "\n${GREEN}===== 安装检查 =====${NC}"
echo "检查关键组件是否正确安装..."

# 初始化错误计数和错误列表
ERROR_COUNT=0
ERROR_LIST=""

# 检查 Python 3
if ! command -v python3 &> /dev/null; then
    ERROR_COUNT=$((ERROR_COUNT+1))
    ERROR_LIST="${ERROR_LIST}\n${RED}[未安装] Python 3${NC} - 请运行: sudo apt install -y python3 python3-venv python3-dev python3-distutils"
fi

# 检查 pip
if ! command -v pip3 &> /dev/null; then
    ERROR_COUNT=$((ERROR_COUNT+1))
    ERROR_LIST="${ERROR_LIST}\n${RED}[未安装] pip3${NC} - 请运行: sudo apt install -y python3-pip 然后 pip install --upgrade pip"
fi

# 检查 Chrome
if ! command -v google-chrome-stable &> /dev/null; then
    ERROR_COUNT=$((ERROR_COUNT+1))
    ERROR_LIST="${ERROR_LIST}\n${RED}[未安装] Google Chrome${NC} - 请运行: wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add - && echo \"deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main\" | sudo tee /etc/apt/sources.list.d/google-chrome.list && sudo apt update && sudo apt install -y google-chrome-stable"
fi

# 检查 ChromeDriver
if ! command -v chromedriver &> /dev/null; then
    ERROR_COUNT=$((ERROR_COUNT+1))
    ERROR_LIST="${ERROR_LIST}\n${RED}[未安装] ChromeDriver${NC} - 请先安装Chrome，然后运行脚本中的ChromeDriver安装部分"
fi

# 检查关键Python包
PACKAGES=("selenium" "pyautogui" "screeninfo" "requests" "flask" "websocket-client" "psutil" "urllib3" "python3-xlib")
for pkg in "${PACKAGES[@]}"; do
    if ! pip3 list | grep -i "$pkg" &> /dev/null; then
        ERROR_COUNT=$((ERROR_COUNT+1))
        ERROR_LIST="${ERROR_LIST}\n${RED}[未安装] Python包: $pkg${NC} - 请运行: pip install --no-cache-dir $pkg"
    fi
done

# 检查虚拟环境
if [ ! -d "venv" ]; then
    ERROR_COUNT=$((ERROR_COUNT+1))
    ERROR_LIST="${ERROR_LIST}\n${RED}[未创建] Python虚拟环境${NC} - 请运行: python3 -m venv venv --clear"
fi

# 输出检查结果
if [ $ERROR_COUNT -eq 0 ]; then
    echo "${GREEN}所有组件已成功安装!${NC}"
else
    echo "${RED}检测到 $ERROR_COUNT 个安装问题:${NC}"
    echo -e "$ERROR_LIST"
    echo "\n您可以单独安装上述未成功安装的组件,无需重新运行整个脚本。"
fi

echo "${GREEN}Ubuntu安装脚本执行完成!${NC}"