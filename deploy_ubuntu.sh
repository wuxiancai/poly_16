#!/bin/bash

# 无头加密货币交易系统 - Ubuntu Server 22.04 一键部署脚本
# 包含Python虚拟环境、Chrome/Chromium、系统依赖安装

set -e  # 遇到错误立即退出

echo "🚀 开始部署无头加密货币交易系统到 Ubuntu Server 22.04..."

# 检查是否为root用户
if [[ $EUID -eq 0 ]]; then
    echo "❌ 请不要使用root用户运行此脚本"
    exit 1
fi

# 获取当前用户和目录
CURRENT_USER=$(whoami)
PROJECT_DIR=$(pwd)
VENV_DIR="$PROJECT_DIR/venv"

echo "📍 当前用户: $CURRENT_USER"
echo "📍 项目目录: $PROJECT_DIR"

# 1. 系统更新和基础依赖安装
echo "📦 更新系统并安装基础依赖..."
sudo apt update -y
sudo apt upgrade -y

# 安装Python3和pip
sudo apt install -y python3 python3-pip python3-venv python3-dev

# 安装系统依赖（Chrome/Chromium需要）
sudo apt install -y \
    wget \
    curl \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    xvfb \
    libgconf-2-4 \
    libxi6 \
    libxcursor1 \
    libxss1 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libgtk-3-0 \
    libgdk-pixbuf2.0-0 \
    libgtk-3-0 \
    libgbm-dev \
    libnss3-dev \
    libxss-dev

echo "✅ 系统基础依赖安装完成"

# 2. 安装Chrome浏览器
echo "🌐 安装Google Chrome..."

# 添加Google Chrome官方源
if [ ! -f /etc/apt/sources.list.d/google-chrome.list ]; then
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
    sudo apt update -y
fi

# 安装Chrome stable版本
sudo apt install -y google-chrome-stable

# 验证Chrome安装
if command -v google-chrome &> /dev/null; then
    CHROME_VERSION=$(google-chrome --version)
    echo "✅ Chrome安装成功: $CHROME_VERSION"
else
    echo "❌ Chrome安装失败，尝试安装Chromium..."
    sudo apt install -y chromium-browser
    if command -v chromium-browser &> /dev/null; then
        echo "✅ Chromium安装成功"
    else
        echo "❌ 浏览器安装失败"
        exit 1
    fi
fi

# 3. 创建Python虚拟环境
echo "🐍 创建Python虚拟环境..."

if [ -d "$VENV_DIR" ]; then
    echo "⚠️  虚拟环境已存在，删除重建..."
    rm -rf "$VENV_DIR"
fi

python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# 升级pip
pip install --upgrade pip setuptools wheel

echo "✅ Python虚拟环境创建完成"

# 4. 安装Python依赖
echo "📚 安装Python依赖包..."

# 检查requirements.txt是否存在
if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
    echo "📝 创建requirements.txt文件..."
    cat > "$PROJECT_DIR/requirements.txt" << EOF
flask>=2.2
selenium>=4.12
webdriver-manager>=3.8
EOF
fi

pip install -r "$PROJECT_DIR/requirements.txt"

echo "✅ Python依赖安装完成"

# 5. 配置Chrome Driver（使用webdriver-manager自动管理）
echo "🚗 配置Chrome Driver..."
cat > "$PROJECT_DIR/test_webdriver.py" << 'EOF'
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

try:
    # 配置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    
    # 自动安装和配置ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    driver.get("https://www.google.com")
    print("✅ WebDriver测试成功")
    driver.quit()
    
except Exception as e:
    print(f"❌ WebDriver测试失败: {e}")
    exit(1)
EOF

python "$PROJECT_DIR/test_webdriver.py"
rm "$PROJECT_DIR/test_webdriver.py"

echo "✅ Chrome Driver配置完成"

# 6. 设置项目权限
echo "🔐 设置项目权限..."
chmod +x "$PROJECT_DIR/headless_crypto_trader.py"
chmod +x "$PROJECT_DIR"/*.sh 2>/dev/null || true

# 7. 创建系统服务（可选）
read -p "🤖 是否创建systemd服务以便开机自启动？(y/n): " create_service

if [[ $create_service == "y" || $create_service == "Y" ]]; then
    SERVICE_NAME="crypto-trader"
    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
    
    echo "📝 创建systemd服务..."
    
    sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Headless Crypto Trader
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$VENV_DIR/bin:/usr/bin:/bin
ExecStart=$VENV_DIR/bin/python $PROJECT_DIR/headless_crypto_trader.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    
    echo "✅ 系统服务创建完成"
    echo "🎯 服务管理命令："
    echo "   启动服务: sudo systemctl start $SERVICE_NAME"
    echo "   停止服务: sudo systemctl stop $SERVICE_NAME"
    echo "   查看状态: sudo systemctl status $SERVICE_NAME"
    echo "   查看日志: sudo journalctl -u $SERVICE_NAME -f"
fi

# 8. 配置防火墙（如果启用了ufw）
if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
    echo "🔥 配置防火墙规则..."
    sudo ufw allow 5000/tcp comment "Crypto Trader Web Interface"
    echo "✅ 防火墙规则添加完成（端口5000）"
fi

# 9. 创建启动脚本
echo "📜 创建启动脚本..."
cat > "$PROJECT_DIR/start_trader.sh" << EOF
#!/bin/bash

# 激活虚拟环境
source "$VENV_DIR/bin/activate"

# 启动交易系统
cd "$PROJECT_DIR"
python headless_crypto_trader.py
EOF

chmod +x "$PROJECT_DIR/start_trader.sh"

# 10. 显示部署信息
echo ""
echo "🎉 部署完成！"
echo "=================================================="
echo "📁 项目目录: $PROJECT_DIR"
echo "🐍 虚拟环境: $VENV_DIR"
echo "🌐 Web界面: http://$(hostname -I | awk '{print $1}'):5000"
echo "🚀 启动命令: ./start_trader.sh"
echo "=================================================="
echo ""
echo "📋 下一步操作："
echo "1. 编辑配置: 运行 './start_trader.sh' 后访问Web界面"
echo "2. 设置URL: 在Web界面配置Polymarket交易页面"
echo "3. 调整参数: 根据需要修改交易价格和金额"
echo ""
echo "💡 提示："
echo "- 系统将自动计算交易金额（基于现金百分比）"
echo "- 如需修改，请访问Web配置页面"
echo "- 建议先在测试环境验证功能"
echo ""

# 询问是否立即启动
read -p "🚀 是否现在启动交易系统？(y/n): " start_now

if [[ $start_now == "y" || $start_now == "Y" ]]; then
    echo "🎯 启动交易系统..."
    ./start_trader.sh
fi