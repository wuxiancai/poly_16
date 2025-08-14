#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polymarket 无头自动交易系统
作者: @wuxiancai
功能: 基于Web+Chrome Headless的高性能交易系统

主要改进:
1. 完全无头模式，节省80%内存和CPU
2. 基于Flask Web API的控制面板
3. 实时价格监控，低延迟交易触发
4. 命令行和Web双重控制接口
5. 详细配置注释，新手友好
"""

import os
import sys
import json
import time
import threading
import logging
import platform
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from flask import Flask, render_template_string, request, jsonify, redirect
import csv
import re
from xpath_config import XPathConfig

class HeadlessLogger:
    """无头模式专用日志器"""
    def __init__(self, name, log_file="headless_trader.log"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # 创建文件处理器
        fh = logging.FileHandler(log_file, encoding='utf-8')
        # 创建控制台处理器
        ch = logging.StreamHandler()
        
        # 创建格式器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # 添加处理器
        if not self.logger.handlers:
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)
    
    def info(self, message):
        self.logger.info(message)
    
    def warning(self, message):
        self.logger.warning(message)
    
    def error(self, message):
        self.logger.error(message)
    
    def critical(self, message):
        self.logger.critical(message)


class HeadlessTrader:
    """无头交易核心类"""
    
    def __init__(self):
        self.logger = HeadlessLogger('HeadlessTrader')
        self.driver = None
        self.running = False
        self.trading_enabled = True
        
        # 价格监控状态
        self.current_up_price = 0.0
        self.current_down_price = 0.0
        self.last_price_update = None
        
        # 配置文件
        self.config_file = "headless_config.json"
        self.config = self.load_config()
        
        # 交易统计
        self.trade_count = 0
        self.last_trade_time = None
        
        # Flask应用
        self.flask_app = self.create_flask_app()
        
        # 价格监控线程锁
        self.price_lock = threading.Lock()
        
        self.logger.info("✅ HeadlessTrader 初始化完成")
    
    def load_config(self):
        """
        加载配置文件
        配置文件包含所有交易参数，每个参数都有详细说明
        """
        default_config = {
            "website": {
                "url": "",  # 交易页面URL
                "description": "Polymarket交易页面地址，格式如: https://polymarket.com/event/..."
            },
            "trading": {
                "description": "交易配置 - Up/Down分别对应原来的Yes/No",
                
                # UP方向交易配置（原Yes）
                "Up1": {
                    "target_price": 45.0,  # 目标价格（¢，分）
                    "amount": 1.0,         # 交易金额（美元）
                    "enabled": True,       # 是否启用此交易
                    "description": "第一档UP交易：当UP价格≤45¢时买入$1"
                },
                "Up2": {
                    "target_price": 40.0,
                    "amount": 2.0,
                    "enabled": False,
                    "description": "第二档UP交易：当UP价格≤40¢时买入$2"
                },
                "Up3": {
                    "target_price": 35.0,
                    "amount": 4.0,
                    "enabled": False,
                    "description": "第三档UP交易：当UP价格≤35¢时买入$4"
                },
                "Up4": {
                    "target_price": 30.0,
                    "amount": 8.0,
                    "enabled": False,
                    "description": "第四档UP交易：当UP价格≤30¢时买入$8"
                },
                "Up5": {
                    "target_price": 25.0,
                    "amount": 16.0,
                    "enabled": False,
                    "description": "第五档UP交易：当UP价格≤25¢时买入$16"
                },
                
                # DOWN方向交易配置（原No）
                "Down1": {
                    "target_price": 45.0,  # 目标价格（¢，分）
                    "amount": 1.0,         # 交易金额（美元）
                    "enabled": True,       # 是否启用此交易
                    "description": "第一档DOWN交易：当DOWN价格≤45¢时买入$1"
                },
                "Down2": {
                    "target_price": 40.0,
                    "amount": 2.0,
                    "enabled": False,
                    "description": "第二档DOWN交易：当DOWN价格≤40¢时买入$2"
                },
                "Down3": {
                    "target_price": 35.0,
                    "amount": 4.0,
                    "enabled": False,
                    "description": "第三档DOWN交易：当DOWN价格≤35¢时买入$4"
                },
                "Down4": {
                    "target_price": 30.0,
                    "amount": 8.0,
                    "enabled": False,
                    "description": "第四档DOWN交易：当DOWN价格≤30¢时买入$8"
                },
                "Down5": {
                    "target_price": 25.0,
                    "amount": 16.0,
                    "enabled": False,
                    "description": "第五档DOWN交易：当DOWN价格≤25¢时买入$16"
                }
            },
            "headless": {
                "description": "无头模式配置",
                "enabled": True,                    # 启用无头模式
                "window_size": "1920,1080",        # 浏览器窗口大小
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "page_load_timeout": 30,           # 页面加载超时时间（秒）
                "element_wait_timeout": 5          # 元素等待超时时间（秒）
            },
            "monitoring": {
                "description": "价格监控配置",
                "price_check_interval": 2.0,       # 价格检查间隔（秒）
                "max_price_age": 10.0,             # 最大价格数据年龄（秒）
                "retry_count": 3,                  # 获取价格失败重试次数
                "browser_restart_threshold": 10    # 连续失败次数达到此值时重启浏览器
            },
            "safety": {
                "description": "安全设置",
                "min_trade_interval": 30,          # 最小交易间隔（秒）
                "max_daily_trades": 50,            # 每日最大交易次数
                "trading_hours": {
                    "start": "00:00",              # 开始交易时间
                    "end": "23:59"                 # 结束交易时间
                }
            },
            "amount_strategy": {
                "description": "自动金额设置（来源于原GUI的start_gui逻辑）",
                "enabled": True,                  # 是否开启自动金额配置
                "initial_percent": 0.4,          # 初始金额占现金百分比（%）
                "first_rebound_percent": 124.0,  # 第二档金额为第一档的倍数（%）
                "n_rebound_percent": 127.0,      # 后续档位递进倍数（%）
                "levels": 5                      # 计算到第几档（1-5）
            }
        }
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
                # 合并默认配置和保存的配置
                self._merge_config(default_config, saved_config)
                self.logger.info("✅ 配置文件加载成功")
                return saved_config
        except FileNotFoundError:
            self.logger.warning("配置文件不存在，创建默认配置")
            self.save_config(default_config)
            return default_config
        except json.JSONDecodeError as e:
            self.logger.error(f"配置文件格式错误: {e}")
            return default_config
    
    def _merge_config(self, default, saved):
        """递归合并配置"""
        for key, value in default.items():
            if key not in saved:
                saved[key] = value
            elif isinstance(value, dict) and isinstance(saved[key], dict):
                self._merge_config(value, saved[key])
    
    def save_config(self, config=None):
        """保存配置到文件"""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            self.logger.info("✅ 配置文件保存成功")
        except Exception as e:
            self.logger.error(f"保存配置文件失败: {e}")
    
    def setup_headless_chrome(self):
        """
        配置Chrome无头模式
        根据优化计划设置最佳性能参数
        """
        chrome_options = Options()
        
        # 基础无头配置
        if self.config['headless']['enabled']:
            chrome_options.add_argument('--headless=new')  # 使用新版无头模式
        
        # 性能优化参数
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-background-networking')
        chrome_options.add_argument('--disable-default-apps')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-sync')
        chrome_options.add_argument('--metrics-recording-only')
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument('--disable-session-crashed-bubble')
        chrome_options.add_argument('--disable-translate')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-features=TranslateUI,BlinkGenPropertyTrees')
        chrome_options.add_argument('--noerrdialogs')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--test-type')
        
        # 窗口大小和用户代理
        chrome_options.add_argument(f'--window-size={self.config["headless"]["window_size"]}')
        chrome_options.add_argument(f'--user-agent={self.config["headless"]["user_agent"]}')
        
        # 内存优化
        chrome_options.add_argument('--memory-pressure-off')
        chrome_options.add_argument('--max_old_space_size=4096')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.config['headless']['page_load_timeout'])
            
            self.logger.info("✅ Chrome无头模式启动成功")
            return True
        except Exception as e:
            self.logger.error(f"Chrome无头模式启动失败: {e}")
            return False
    
    def get_current_prices(self):
        """
        实时获取UP和DOWN价格
        这是最关键的功能，确保价格获取的实时性和准确性
        """
        if not self.driver:
            self.logger.error("浏览器未初始化")
            return None, None
        
        try:
            # 等待页面完全加载
            WebDriverWait(self.driver, 5).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )

            # 使用增强的JavaScript获取价格
            prices = self.driver.execute_script("""
                function getPricesHeadless() {
                    const prices = {up: null, down: null};
                    
                    // 搜索所有可能包含价格的元素
                    const allElements = document.querySelectorAll('span, button, div');
                    
                    for (let el of allElements) {
                        const text = el.textContent.trim();
                        
                        // 匹配Up价格（原Yes）
                        if ((text.includes('Up') || text.includes('Yes')) && text.includes('¢')) {
                            const match = text.match(/(\\d+(?:\\.\\d+)?)¢/);
                            if (match && !prices.up) {
                                prices.up = parseFloat(match[1]);
                            }
                        }
                        
                        // 匹配Down价格（原No）
                        if ((text.includes('Down') || text.includes('No')) && text.includes('¢')) {
                            const match = text.match(/(\\d+(?:\\.\\d+)?)¢/);
                            if (match && !prices.down) {
                                prices.down = parseFloat(match[1]);
                            }
                        }
                        
                        // 如果都找到了就提前退出
                        if (prices.up !== null && prices.down !== null) {
                            break;
                        }
                    }
                    
                    return prices;
                }
                
                return getPricesHeadless();
            """)
            
            up_price = prices.get('up')
            down_price = prices.get('down')
            
            # 使用XPath作为备用方案
            if up_price is None or down_price is None:
                try:
                    # 尝试使用XPath获取UP按钮价格
                    if up_price is None:
                        up_elements = self.driver.find_elements(By.XPATH, XPathConfig.BUY_YES_BUTTON[0])
                        for element in up_elements:
                            text = element.text
                            if '¢' in text:
                                import re
                                match = re.search(r'(\\d+(?:\\.\\d+)?)¢', text)
                                if match:
                                    up_price = float(match.group(1))
                                    break
                    
                    # 尝试使用XPath获取DOWN按钮价格
                    if down_price is None:
                        down_elements = self.driver.find_elements(By.XPATH, XPathConfig.BUY_NO_BUTTON[0])
                        for element in down_elements:
                            text = element.text
                            if '¢' in text:
                                import re
                                match = re.search(r'(\\d+(?:\\.\\d+)?)¢', text)
                                if match:
                                    down_price = float(match.group(1))
                                    break
                except Exception as e:
                    self.logger.warning(f"XPath备用方案获取价格失败: {e}")
            
            # 更新价格数据
            with self.price_lock:
                if up_price is not None:
                    self.current_up_price = up_price
                if down_price is not None:
                    self.current_down_price = down_price
                self.last_price_update = datetime.now()
            
            if up_price is not None and down_price is not None:
                self.logger.info(f"📊 当前价格 - UP: {up_price}¢, DOWN: {down_price}¢")
            else:
                self.logger.warning(f"⚠️ 价格获取不完整 - UP: {up_price}, DOWN: {down_price}")
            
            return up_price, down_price
            
        except Exception as e:
            self.logger.error(f"获取价格失败: {e}")
            return None, None
    
    def execute_buy_operation(self, direction, amount):
        """
        执行买入操作
        direction: 'up' 或 'down'
        amount: 交易金额
        """
        try:
            self.logger.info(f"🔥 开始执行买入: {direction.upper()} ${amount}")
            
            # 1. 点击对应的买入按钮
            if direction.lower() == 'up':
                button_xpath = XPathConfig.BUY_YES_BUTTON[0]
            else:
                button_xpath = XPathConfig.BUY_NO_BUTTON[0]
            
            # 等待并点击买入按钮
            buy_button = WebDriverWait(self.driver, self.config['headless']['element_wait_timeout']).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath))
            )
            buy_button.click()
            self.logger.info(f"✅ 点击{direction.upper()}买入按钮成功")
            
            # 2. 输入金额
            amount_input = WebDriverWait(self.driver, self.config['headless']['element_wait_timeout']).until(
                EC.element_to_be_clickable((By.XPATH, XPathConfig.AMOUNT_INPUT[0]))
            )
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", amount_input)
            except Exception:
                pass
            amount_input.clear()
            try:
                # 双重保险清空输入框内容
                amount_input.send_keys(Keys.CONTROL, 'a')
                amount_input.send_keys(Keys.BACKSPACE)
                amount_input.send_keys(Keys.COMMAND, 'a')
                amount_input.send_keys(Keys.BACKSPACE)
            except Exception:
                pass
            amount_input.send_keys(str(amount))
            self.logger.info(f"✅ 输入金额 ${amount} 成功")
            
            # 3. 点击确认按钮
            confirm_button = WebDriverWait(self.driver, self.config['headless']['element_wait_timeout']).until(
                EC.element_to_be_clickable((By.XPATH, XPathConfig.BUY_CONFIRM_BUTTON[0]))
            )
            confirm_button.click()
            self.logger.info(f"✅ 点击确认按钮成功")
            
            # 4. 更新交易统计
            self.trade_count += 1
            self.last_trade_time = datetime.now()
            
            # 5. 如果买入UP，立即卖出DOWN仓位（反之亦然）
            self._execute_opposite_sell(direction)
            
            self.logger.info(f"🎉 交易完成: {direction.upper()} ${amount}")
            return True
            
        except TimeoutException:
            self.logger.error(f"❌ 交易超时: {direction.upper()} ${amount}")
            return False
        except Exception as e:
            self.logger.error(f"❌ 交易失败: {direction.upper()} ${amount} - {e}")
            return False
    
    def _execute_opposite_sell(self, bought_direction):
        """
        执行反向卖出操作
        如果买入UP，则卖出DOWN仓位；如果买入DOWN，则卖出UP仓位
        """
        try:
            # 确定要卖出的方向
            sell_direction = 'down' if bought_direction.lower() == 'up' else 'up'
            
            self.logger.info(f"🔄 开始卖出{sell_direction.upper()}仓位")
            
            # 根据方向选择卖出按钮
            if sell_direction.lower() == 'up':
                sell_xpath = XPathConfig.POSITION_SELL_YES_BUTTON[0]
            else:
                sell_xpath = XPathConfig.POSITION_SELL_NO_BUTTON[0]
            
            # 尝试找到并点击卖出按钮
            try:
                sell_button = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, sell_xpath))
                )
                sell_button.click()
                
                # 点击卖出确认按钮
                sell_confirm = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, XPathConfig.SELL_CONFIRM_BUTTON[0]))
                )
                sell_confirm.click()
                
                self.logger.info(f"✅ 卖出{sell_direction.upper()}仓位成功")
                
            except TimeoutException:
                self.logger.info(f"ℹ️ 没有{sell_direction.upper()}仓位需要卖出")
                
        except Exception as e:
            self.logger.warning(f"卖出反向仓位时出错: {e}")
    
    def check_trading_conditions(self):
        """
        检查交易条件并执行交易
        这是核心交易逻辑
        """
        if not self.trading_enabled:
            return
        
        # 检查是否在交易时间内
        if not self._is_trading_hours():
            return
        
        # 检查最小交易间隔
        if (self.last_trade_time and 
            (datetime.now() - self.last_trade_time).total_seconds() < self.config['safety']['min_trade_interval']):
            return
        
        # 检查每日交易次数限制
        if self.trade_count >= self.config['safety']['max_daily_trades']:
            self.logger.warning("已达到每日最大交易次数限制")
            return
        
        # 获取当前价格
        up_price, down_price = self.get_current_prices()
        
        if up_price is None or down_price is None:
            self.logger.warning("价格数据不完整，跳过交易检查")
            return
        
        # 检查UP方向交易条件
        for level in range(1, 6):  # Up1 到 Up5
            config_key = f"Up{level}"
            if config_key in self.config['trading']:
                trade_config = self.config['trading'][config_key]
                
                if (trade_config.get('enabled', False) and 
                    up_price <= trade_config['target_price']):
                    
                    self.logger.info(f"🎯 触发UP交易条件: 价格{up_price}¢ ≤ 目标{trade_config['target_price']}¢")
                    
                    if self.execute_buy_operation('up', trade_config['amount']):
                        # 交易成功后禁用此配置，避免重复交易
                        trade_config['enabled'] = False
                        self.save_config()
                        return
        
        # 检查DOWN方向交易条件
        for level in range(1, 6):  # Down1 到 Down5
            config_key = f"Down{level}"
            if config_key in self.config['trading']:
                trade_config = self.config['trading'][config_key]
                
                if (trade_config.get('enabled', False) and 
                    down_price <= trade_config['target_price']):
                    
                    self.logger.info(f"🎯 触发DOWN交易条件: 价格{down_price}¢ ≤ 目标{trade_config['target_price']}¢")
                    
                    if self.execute_buy_operation('down', trade_config['amount']):
                        # 交易成功后禁用此配置，避免重复交易
                        trade_config['enabled'] = False
                        self.save_config()
                        return
    
    def _is_trading_hours(self):
        """检查是否在交易时间内"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        start_time = self.config['safety']['trading_hours']['start']
        end_time = self.config['safety']['trading_hours']['end']
        
        return start_time <= current_time <= end_time
    
    def start_monitoring(self, url):
        """开始监控指定URL"""
        try:
            self.logger.info(f"🚀 开始启动无头交易系统...")
            
            # 1. 设置浏览器
            if not self.setup_headless_chrome():
                return False
            
            # 2. 打开交易页面
            self.driver.get(url)
            self.config['website']['url'] = url
            self.save_config()
            
            self.logger.info(f"📱 已打开交易页面: {url}")
            
            # 3. 等待页面加载
            WebDriverWait(self.driver, self.config['headless']['page_load_timeout']).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )
            
            # 3.1 页面已就绪后，尝试根据现金自动计算并写入各档金额
            try:
                if self.config.get('amount_strategy', {}).get('enabled', True):
                    self.apply_auto_amounts()
            except Exception as e:
                self.logger.warning(f"自动计算金额失败，将继续运行: {e}")
            
            # 4. 开始价格监控循环
            self.running = True
            
            def monitoring_loop():
                consecutive_failures = 0
                
                while self.running:
                    try:
                        # 检查交易条件
                        self.check_trading_conditions()
                        
                        # 重置失败计数
                        consecutive_failures = 0
                        
                        # 等待下次检查
                        time.sleep(self.config['monitoring']['price_check_interval'])
                        
                    except Exception as e:
                        consecutive_failures += 1
                        self.logger.error(f"监控循环出错: {e}")
                        
                        # 如果连续失败达到阈值，重启浏览器
                        if consecutive_failures >= self.config['monitoring']['browser_restart_threshold']:
                            self.logger.warning("连续失败过多，重启浏览器...")
                            if self.restart_browser():
                                consecutive_failures = 0
                            else:
                                self.logger.error("浏览器重启失败，停止监控")
                                self.running = False
                        
                        time.sleep(5)  # 失败后等待更长时间
            
            # 在后台线程中运行监控
            self.monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            self.logger.info("✅ 无头交易系统启动成功！")
            return True
            
        except Exception as e:
            self.logger.error(f"启动监控失败: {e}")
            return False
    
    def restart_browser(self):
        """重启浏览器"""
        try:
            self.logger.info("🔄 重启浏览器...")
            
            # 关闭当前浏览器
            if self.driver:
                self.driver.quit()
                self.driver = None
            
            # 等待一段时间
            time.sleep(3)
            
            # 重新启动
            if self.setup_headless_chrome():
                # 重新打开页面
                if self.config['website']['url']:
                    self.driver.get(self.config['website']['url'])
                    self.logger.info("✅ 浏览器重启成功")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"重启浏览器失败: {e}")
            return False
    
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        self.trading_enabled = False
        
        if self.driver:
            self.driver.quit()
            self.driver = None
        
        self.logger.info("🛑 监控已停止")
    
    def _get_cash_value(self):
        """从页面右上角Wallet区域提取Cash美元数值，失败返回None"""
        try:
            # 多个XPath备选
            xpaths = XPathConfig.CASH_VALUE if isinstance(XPathConfig.CASH_VALUE, list) else [XPathConfig.CASH_VALUE]
            cash_text = None
            for xp in xpaths:
                try:
                    el = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, xp))
                    )
                    text = el.text.strip()
                    if text and ('$' in text or any(ch.isdigit() for ch in text)):
                        cash_text = text
                        break
                except Exception:
                    continue
            if not cash_text:
                return None
            m = re.search(r'\$?([\d,]+\.?\d*)', cash_text)
            if not m:
                return None
            return float(m.group(1).replace(',', ''))
        except Exception:
            return None

    def apply_auto_amounts(self):
        """根据amount_strategy和页面CASH值，计算并写入Up/Down各档金额到配置文件"""
        strategy = self.config.get('amount_strategy', {})
        if not strategy.get('enabled', True):
            self.logger.info("自动金额设置未启用，跳过")
            return
        cash = self._get_cash_value()
        if cash is None or cash <= 0:
            self.logger.warning("无法获取有效的CASH值，跳过自动金额设置")
            return
        initial_percent = float(strategy.get('initial_percent', 0.4)) / 100.0
        first_rebound = float(strategy.get('first_rebound_percent', 124.0)) / 100.0
        n_rebound = float(strategy.get('n_rebound_percent', 127.0)) / 100.0
        levels = int(strategy.get('levels', 5))
        levels = max(1, min(levels, 5))
        # 计算金额序列
        amounts = []
        base = cash * initial_percent
        amounts.append(round(base, 2))
        if levels >= 2:
            a2 = base * first_rebound
            amounts.append(round(a2, 2))
        if levels >= 3:
            a3 = amounts[1] * n_rebound
            amounts.append(round(a3, 2))
        if levels >= 4:
            a4 = amounts[2] * n_rebound
            amounts.append(round(a4, 2))
        if levels >= 5:
            a5 = amounts[3] * n_rebound
            amounts.append(round(a5, 2))
        # 写入到Up/Down配置中
        for i, amt in enumerate(amounts, start=1):
            up_key = f"Up{i}"
            down_key = f"Down{i}"
            if up_key in self.config['trading']:
                self.config['trading'][up_key]['amount'] = float(amt)
            if down_key in self.config['trading']:
                self.config['trading'][down_key]['amount'] = float(amt)
        self.save_config()
        self.logger.info(f"✅ 自动金额设置完成，基于CASH ${cash:.2f} -> {amounts}")

    def get_status(self):
        """获取系统状态"""
        status = {
            'running': self.running,
            'trading_enabled': self.trading_enabled,
            'current_prices': {
                'up': self.current_up_price,
                'down': self.current_down_price,
                'last_update': self.last_price_update.isoformat() if self.last_price_update else None
            },
            'trade_stats': {
                'count': self.trade_count,
                'last_trade': self.last_trade_time.isoformat() if self.last_trade_time else None
            },
            'config': self.config
        }
        return status
    
    def create_flask_app(self):
        """创建Flask Web控制面板"""
        app = Flask(__name__)
        
        @app.route('/')
        def dashboard():
            """主控制面板"""
            status = self.get_status()
            
            html_template = """
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Polymarket无头交易系统</title>
                <style>
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
                        margin: 0; padding: 20px; background: #f8f9fa; 
                    }
                    .container { max-width: 1200px; margin: 0 auto; }
                    .header { text-align: center; margin-bottom: 30px; }
                    .header h1 { color: #333; margin-bottom: 10px; }
                    .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
                    .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                    .card h3 { margin-top: 0; color: #333; }
                    .status-indicator { 
                        display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; 
                    }
                    .status-running { background: #28a745; }
                    .status-stopped { background: #dc3545; }
                    .price-display { font-size: 24px; font-weight: bold; text-align: center; margin: 10px 0; }
                    .price-up { color: #28a745; }
                    .price-down { color: #dc3545; }
                    .btn { 
                        padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; 
                        font-size: 14px; text-decoration: none; display: inline-block; margin: 5px;
                    }
                    .btn-primary { background: #007bff; color: white; }
                    .btn-success { background: #28a745; color: white; }
                    .btn-danger { background: #dc3545; color: white; }
                    .btn-warning { background: #ffc107; color: black; }
                    .btn:hover { opacity: 0.8; }
                    .config-section { margin-top: 30px; }
                    .config-item { margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 4px; }
                    .form-row { display: flex; gap: 10px; align-items: center; margin: 5px 0; }
                    .form-row input, .form-row select { padding: 5px; border: 1px solid #ddd; border-radius: 4px; }
                    .refresh-btn { position: fixed; top: 20px; right: 20px; }
                </style>
                <script>
                    function refreshPage() { location.reload(); }
                    setInterval(refreshPage, 10000);  // 每10秒自动刷新
                </script>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🚀 Polymarket无头交易系统</h1>
                        <p>基于Web+Chrome Headless的高性能交易平台</p>
                    </div>
                    
                    <button class="btn btn-primary refresh-btn" onclick="refreshPage()">🔄 刷新</button>
                    
                    <div class="status-grid">
                        <div class="card">
                            <h3>📊 系统状态</h3>
                            <p>
                                <span class="status-indicator {{ 'status-running' if status.running else 'status-stopped' }}"></span>
                                {{ '运行中' if status.running else '已停止' }}
                            </p>
                            <p>
                                <span class="status-indicator {{ 'status-running' if status.trading_enabled else 'status-stopped' }}"></span>
                                {{ '交易启用' if status.trading_enabled else '交易禁用' }}
                            </p>
                            <div style="margin-top: 15px;">
                                {% if status.running %}
                                    <a href="/stop" class="btn btn-danger">⏹️ 停止监控</a>
                                {% else %}
                                    <a href="/start" class="btn btn-success">▶️ 开始监控</a>
                                {% endif %}
                                <a href="/restart" class="btn btn-warning">🔄 重启浏览器</a>
                            </div>
                        </div>
                        
                        <div class="card">
                            <h3>💰 实时价格</h3>
                            <div class="price-display">
                                <div class="price-up">UP: {{ status.current_prices.up }}¢</div>
                                <div class="price-down">DOWN: {{ status.current_prices.down }}¢</div>
                            </div>
                            <p style="text-align: center; font-size: 12px; color: #666;">
                                最后更新: {{ status.current_prices.last_update[:19] if status.current_prices.last_update else '暂无数据' }}
                            </p>
                        </div>
                        
                        <div class="card">
                            <h3>📈 交易统计</h3>
                            <p><strong>总交易次数:</strong> {{ status.trade_stats.count }}</p>
                            <p><strong>最后交易:</strong> {{ status.trade_stats.last_trade[:19] if status.trade_stats.last_trade else '暂无交易' }}</p>
                        </div>
                    </div>
                    
                    <div class="card config-section">
                        <h3>⚙️ 交易配置</h3>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                            <div>
                                <h4>🔼 UP交易配置</h4>
                                {% for i in range(1, 6) %}
                                    {% set config_key = 'Up' ~ i %}
                                    {% if config_key in status.config.trading %}
                                        <div class="config-item">
                                            <strong>{{ config_key }}:</strong><br>
                                            目标价格: {{ status.config.trading[config_key].target_price }}¢<br>
                                            交易金额: ${{ status.config.trading[config_key].amount }}<br>
                                            状态: {{ '启用' if status.config.trading[config_key].enabled else '禁用' }}
                                        </div>
                                    {% endif %}
                                {% endfor %}
                            </div>
                            <div>
                                <h4>🔽 DOWN交易配置</h4>
                                {% for i in range(1, 6) %}
                                    {% set config_key = 'Down' ~ i %}
                                    {% if config_key in status.config.trading %}
                                        <div class="config-item">
                                            <strong>{{ config_key }}:</strong><br>
                                            目标价格: {{ status.config.trading[config_key].target_price }}¢<br>
                                            交易金额: ${{ status.config.trading[config_key].amount }}<br>
                                            状态: {{ '启用' if status.config.trading[config_key].enabled else '禁用' }}
                                        </div>
                                    {% endif %}
                                {% endfor %}
                            </div>
                        </div>
                        <div style="margin-top: 20px;">
                            <a href="/config" class="btn btn-primary">📝 编辑配置</a>
                            <a href="/reset" class="btn btn-warning">🔄 重置交易状态</a>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return render_template_string(html_template, status=status)
        
        @app.route('/start')
        def start_monitoring_route():
            """启动监控"""
            url = self.config.get('website', {}).get('url', '')
            if url:
                if self.start_monitoring(url):
                    return redirect('/')
                else:
                    return "启动失败", 500
            else:
                return "请先设置交易URL", 400
        
        @app.route('/stop')
        def stop_monitoring_route():
            """停止监控"""
            self.stop_monitoring()
            return redirect('/')
        
        @app.route('/restart')
        def restart_browser_route():
            """重启浏览器"""
            if self.restart_browser():
                return redirect('/')
            else:
                return "重启失败", 500
        
        @app.route('/reset')
        def reset_trading_route():
            """重置交易状态"""
            # 重新启用所有交易配置
            for key in self.config['trading']:
                if isinstance(self.config['trading'][key], dict) and 'enabled' in self.config['trading'][key]:
                    self.config['trading'][key]['enabled'] = True
            
            self.save_config()
            return redirect('/')
        
        @app.route('/config', methods=['GET', 'POST'])
        def config_route():
            """查看/编辑配置"""
            if request.method == 'POST':
                # 更新网站URL
                url = request.form.get('website_url', '').strip()
                self.config['website']['url'] = url
                
                # 更新交易配置
                for prefix in ['Up', 'Down']:
                    for i in range(1, 6):
                        key = f"{prefix}{i}"
                        if key in self.config['trading']:
                            try:
                                target_price = float(request.form.get(f'{key}_target_price', self.config['trading'][key]['target_price']))
                                amount = float(request.form.get(f'{key}_amount', self.config['trading'][key]['amount']))
                                enabled = request.form.get(f'{key}_enabled') == 'on'
                                self.config['trading'][key]['target_price'] = target_price
                                self.config['trading'][key]['amount'] = amount
                                self.config['trading'][key]['enabled'] = enabled
                            except Exception as e:
                                self.logger.warning(f"更新配置{key}失败: {e}")
                
                # 更新安全配置
                try:
                    self.config['safety']['min_trade_interval'] = int(request.form.get('min_trade_interval', self.config['safety']['min_trade_interval']))
                    self.config['safety']['max_daily_trades'] = int(request.form.get('max_daily_trades', self.config['safety']['max_daily_trades']))
                    self.config['safety']['trading_hours']['start'] = request.form.get('trading_start', self.config['safety']['trading_hours']['start'])
                    self.config['safety']['trading_hours']['end'] = request.form.get('trading_end', self.config['safety']['trading_hours']['end'])
                except Exception as e:
                    self.logger.warning(f"更新安全配置失败: {e}")
                
                self.save_config()
                return redirect('/')
            
            # GET 渲染配置表单
            status = self.get_status()
            html = """
            <!DOCTYPE html>
            <html lang=\"zh-CN\">
            <head>
                <meta charset=\"UTF-8\">
                <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
                <title>编辑配置</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }
                    .container { max-width: 1000px; margin: 0 auto; }
                    .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                    .form-row { display: grid; grid-template-columns: 200px 1fr; gap: 10px; align-items: center; margin: 10px 0; }
                    input[type=text], input[type=number] { padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
                    .section-title { margin-top: 20px; border-left: 4px solid #007bff; padding-left: 8px; color: #333; }
                    .btn { padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
                    .btn-primary { background: #007bff; color: #fff; }
                    .btn-secondary { background: #6c757d; color: #fff; }
                    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
                    .item { padding: 12px; border: 1px dashed #ddd; border-radius: 6px; background: #fafafa; }
                    label { color: #555; }
                </style>
            </head>
            <body>
                <div class=\"container\">
                    <div class=\"card\">
                        <h2>📝 编辑配置</h2>
                        <form method=\"post\">
                            <h3 class=\"section-title\">网站设置</h3>
                            <div class=\"form-row\">
                                <label>交易页面URL（Polymarket事件页面地址）</label>
                                <input type=\"text\" name=\"website_url\" value=\"{{ status.config.website.url }}\" placeholder=\"https://polymarket.com/event/...\" />
                            </div>
                            <p style=\"color:#666; font-size:12px; margin-top:-8px;\">说明: 设置要监控与交易的具体事件页面URL。</p>
                            
                            <h3 class=\"section-title\">安全设置</h3>
                            <div class=\"form-row\"><label>最小交易间隔（秒）</label><input type=\"number\" name=\"min_trade_interval\" value=\"{{ status.config.safety.min_trade_interval }}\" /></div>
                            <div class=\"form-row\"><label>每日最大交易次数</label><input type=\"number\" name=\"max_daily_trades\" value=\"{{ status.config.safety.max_daily_trades }}\" /></div>
                            <div class=\"form-row\"><label>开始交易时间（HH:MM）</label><input type=\"text\" name=\"trading_start\" value=\"{{ status.config.safety.trading_hours.start }}\" /></div>
                            <div class=\"form-row\"><label>结束交易时间（HH:MM）</label><input type=\"text\" name=\"trading_end\" value=\"{{ status.config.safety.trading_hours.end }}\" /></div>
                            <p style=\"color:#666; font-size:12px; margin-top:-8px;\">说明: 限制交易频率和时间窗口，降低风险与误触发。</p>
                            
                            <h3 class=\"section-title\">UP 交易配置（原 Yes）</h3>
                            <div class=\"grid\">
                                {% for i in range(1,6) %}
                                {% set key = 'Up' ~ i %}
                                <div class=\"item\">
                                    <strong>{{ key }}</strong>
                                    <div class=\"form-row\"><label>目标价格（¢）</label><input type=\"number\" step=\"0.1\" name=\"{{ key }}_target_price\" value=\"{{ status.config.trading[key].target_price }}\" /></div>
                                    <div class=\"form-row\"><label>交易金额（$）</label><input type=\"number\" step=\"0.1\" name=\"{{ key }}_amount\" value=\"{{ status.config.trading[key].amount }}\" /></div>
                                    <div class=\"form-row\"><label>启用</label><input type=\"checkbox\" name=\"{{ key }}_enabled\" {% if status.config.trading[key].enabled %}checked{% endif %} /></div>
                                    <p style=\"color:#666; font-size:12px; margin-top:-8px;\">{{ status.config.trading[key].description }}</p>
                                </div>
                                {% endfor %}
                            </div>
                            
                            <h3 class=\"section-title\">DOWN 交易配置（原 No）</h3>
                            <div class=\"grid\">
                                {% for i in range(1,6) %}
                                {% set key = 'Down' ~ i %}
                                <div class=\"item\">
                                    <strong>{{ key }}</strong>
                                    <div class=\"form-row\"><label>目标价格（¢）</label><input type=\"number\" step=\"0.1\" name=\"{{ key }}_target_price\" value=\"{{ status.config.trading[key].target_price }}\" /></div>
                                    <div class=\"form-row\"><label>交易金额（$）</label><input type=\"number\" step=\"0.1\" name=\"{{ key }}_amount\" value=\"{{ status.config.trading[key].amount }}\" /></div>
                                    <div class=\"form-row\"><label>启用</label><input type=\"checkbox\" name=\"{{ key }}_enabled\" {% if status.config.trading[key].enabled %}checked{% endif %} /></div>
                                    <p style=\"color:#666; font-size:12px; margin-top:-8px;\">{{ status.config.trading[key].description }}</p>
                                </div>
                                {% endfor %}
                            </div>
                            
                            <div style=\"margin-top: 20px;\">
                                <button type=\"submit\" class=\"btn btn-primary\">💾 保存并返回</button>
                                <a href=\"/\" class=\"btn btn-secondary\">取消</a>
                            </div>
                        </form>
                    </div>
                </div>
            </body>
            </html>
            """
            return render_template_string(html, status=status)
        
        @app.route('/api/status')
        def api_status():
            """API: 获取状态"""
            return jsonify(self.get_status())
        
        @app.route('/api/prices')
        def api_prices():
            """API: 获取当前价格"""
            up_price, down_price = self.get_current_prices()
            return jsonify({
                'up': up_price,
                'down': down_price,
                'timestamp': datetime.now().isoformat()
            })
        
        @app.route('/api/start', methods=['POST'])
        def api_start():
            """API: 启动监控，可携带url参数"""
            url = request.json.get('url') if request.is_json else request.form.get('url')
            if url:
                self.config['website']['url'] = url
                self.save_config()
            url = self.config['website']['url']
            if not url:
                return jsonify({"ok": False, "error": "缺少url"}), 400
            ok = self.start_monitoring(url)
            return jsonify({"ok": ok})
        
        @app.route('/api/stop', methods=['POST'])
        def api_stop():
            self.stop_monitoring()
            return jsonify({"ok": True})
        
        @app.route('/api/buy', methods=['POST'])
        def api_buy():
            """API: 手动下单 /api/buy {direction: up|down, amount: number}"""
            data = request.json or {}
            direction = data.get('direction')
            amount = float(data.get('amount', 0))
            if direction not in ['up', 'down'] or amount <= 0:
                return jsonify({"ok": False, "error": "参数不合法"}), 400
            ok = self.execute_buy_operation(direction, amount)
            return jsonify({"ok": ok})
        
        return app
    
    def start_flask_server(self, host='0.0.0.0', port=5000):
        """启动Flask服务器"""
        def run():
            try:
                import logging as flask_logging
                log = flask_logging.getLogger('werkzeug')
                log.setLevel(flask_logging.ERROR)
                
                self.flask_app.run(host=host, port=port, debug=False, use_reloader=False)
            except Exception as e:
                self.logger.error(f"Flask服务器启动失败: {e}")
        
        flask_thread = threading.Thread(target=run, daemon=True)
        flask_thread.start()
        self.logger.info(f"✅ Web控制面板已启动: http://{host}:{port}")


def main():
    """主函数"""
    print("🚀 Polymarket无头交易系统 v1.0")
    print("=" * 50)
    
    trader = HeadlessTrader()
    
    # 启动Web控制面板
    trader.start_flask_server()
    
    # 如果配置中有URL，直接启动监控
    url = trader.config.get('website', {}).get('url', '')
    if url:
        print(f"📱 发现配置的URL，自动启动监控: {url}")
        trader.start_monitoring(url)
    else:
        print("⚠️ 请在Web控制面板中设置交易URL")
    
    print("\n📊 Web控制面板: http://localhost:5000")
    print("🔧 配置文件: headless_config.json")
    print("📋 日志文件: headless_trader.log")
    print("\n按Ctrl+C退出...")
    
    try:
        # 保持程序运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 正在关闭系统...")
        trader.stop_monitoring()
        print("✅ 系统已关闭")


if __name__ == "__main__":
    main()