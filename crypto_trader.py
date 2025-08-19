# -*- coding: utf-8 -*-
# polymarket_v1
import platform
import tkinter as tk
from tkinter import E, ttk, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import json
import threading
import time
import os
import logging
from datetime import datetime, timedelta
import re
import pyautogui
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import socket
import sys
import logging
from xpath_config import XPathConfig
import random
import websocket
import subprocess
import shutil
import csv
from flask import Flask, render_template_string, request, url_for, jsonify
import psutil
import socket
import urllib.request
import requests


class StatusDataManager:
    """线程安全的状态数据管理器"""
    def __init__(self):
        self._data = {
            'trading': {
                'is_running': False,
                'current_url': '',
                'selected_coin': 'BTC',
                'auto_find_time': '2:00',
                'last_trade_time': None,
                'trade_count': 22,
                'remaining_trades': 22
            },
            'prices': {
                'polymarket_up': '--',
                'polymarket_down': '--',
                'binance_current': '--',
                'binance_zero_time': '--',
                'price_change_rate': '--'
            },
            'account': {
                'portfolio_value': '--',
                'available_cash': '--',
                'zero_time_cash': '--',
                'initial_amount': 0,
                'first_rebound': 0,
                'n_rebound': 0,
                'profit_rate': '0%',
                'doubling_weeks': 0
            },
            'positions': {
                'up_positions': [
                    {'price': '0', 'amount': '0'},
                    {'price': '0', 'amount': '0'},
                    {'price': '0', 'amount': '0'},
                    {'price': '0', 'amount': '0'}
                ],
                'down_positions': [
                    {'price': '0', 'amount': '0'},
                    {'price': '0', 'amount': '0'},
                    {'price': '0', 'amount': '0'},
                    {'price': '0', 'amount': '0'}
                ]
            },
            'system': {
                'browser_status': '未连接',
                'monitoring_status': '未启动',
                'last_update': None,
                'error_count': 0,
                'trading_pair': '--'
            }
        }
        self._lock = threading.RLock()
    
    def update(self, category, key, value):
        """更新指定分类下的数据"""
        with self._lock:
            if category in self._data and key in self._data[category]:
                self._data[category][key] = value
                self._data['system']['last_update'] = datetime.now().strftime('%H:%M:%S')
    
    def update_data(self, category, key, value):
        """更新指定分类下的数据（兼容旧接口）"""
        with self._lock:
            if category not in self._data:
                self._data[category] = {}
            self._data[category][key] = value
            self._data['system']['last_update'] = datetime.now().strftime('%H:%M:%S')
    
    def update_position(self, position_type, index, price=None, amount=None):
        """更新持仓信息"""
        with self._lock:
            if position_type in ['up_positions', 'down_positions'] and 0 <= index < 4:
                if price is not None:
                    self._data['positions'][position_type][index]['price'] = str(price)
                if amount is not None:
                    self._data['positions'][position_type][index]['amount'] = str(amount)
                self._data['system']['last_update'] = datetime.now().strftime('%H:%M:%S')
    
    def get_all(self):
        """获取所有数据的副本"""
        with self._lock:
            return self._data.copy()
    
    def get_category(self, category):
        """获取指定分类的数据"""
        with self._lock:
            return self._data.get(category, {}).copy()
    
    def get_value(self, category, key):
        """获取指定值"""
        with self._lock:
            return self._data.get(category, {}).get(key)
    
    def get_legacy_format(self):
        """获取兼容旧格式的数据结构，用于API接口"""
        with self._lock:
            data = self._data
            return {
                'status': {
                    'monitoring': data['system']['monitoring_status'],
                    'url': data['trading']['current_url'],
                    'browser_status': data['system']['browser_status'],
                    'last_update': data['system']['last_update'] or datetime.now().strftime('%H:%M:%S')
                },
                'prices': {
                    'up_price': data['prices']['polymarket_up'] if data['prices']['polymarket_up'] != '--' else '--',
                    'down_price': data['prices']['polymarket_down'] if data['prices']['polymarket_down'] != '--' else '--',
                    'binance_price': data['prices']['binance_current'],
                    'binance_zero_price': data['prices']['binance_zero_time'],
                    'binance_rate': data['prices']['price_change_rate']
                },
                'account': {
                    'portfolio': data['account']['portfolio_value'],
                    'cash': data['account']['available_cash'],
                    'zero_time_cash': data['account']['zero_time_cash']
                },
                'positions': {
                    'up1_price': data['positions']['up_positions'][0]['price'],
                    'up1_amount': data['positions']['up_positions'][0]['amount'],
                    'up2_price': data['positions']['up_positions'][1]['price'],
                    'up2_amount': data['positions']['up_positions'][1]['amount'],
                    'up3_price': data['positions']['up_positions'][2]['price'],
                    'up3_amount': data['positions']['up_positions'][2]['amount'],
                    'up4_price': data['positions']['up_positions'][3]['price'],
                    'up4_amount': data['positions']['up_positions'][3]['amount'],
                    'down1_price': data['positions']['down_positions'][0]['price'],
                    'down1_amount': data['positions']['down_positions'][0]['amount'],
                    'down2_price': data['positions']['down_positions'][1]['price'],
                    'down2_amount': data['positions']['down_positions'][1]['amount'],
                    'down3_price': data['positions']['down_positions'][2]['price'],
                    'down3_amount': data['positions']['down_positions'][2]['amount'],
                    'down4_price': data['positions']['down_positions'][3]['price'],
                    'down4_amount': data['positions']['down_positions'][3]['amount']
                },
                'coin': data['trading']['selected_coin'],
                'auto_find_time': data['trading']['auto_find_time'],
                'remaining_trades': data['trading']['remaining_trades']
            }


class Logger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # 如果logger已经有处理器，则不再添加新的处理器
        if not self.logger.handlers:
            # 创建logs目录（如果不存在）
            if not os.path.exists('logs'):
                os.makedirs('logs')
                
            # 设置日志文件名（使用当前日期）
            log_filename = f"logs/{datetime.now().strftime('%Y%m%d')}.log"
            
            # 创建文件处理器
            file_handler = logging.FileHandler(log_filename, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            # 创建控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            
            # 创建格式器
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # 添加处理器到logger
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    @staticmethod
    def get_latest_log_file():
        """获取最新的日志文件路径"""
        logs_dir = 'logs'
        if not os.path.exists(logs_dir):
            return None
        
        # 获取logs目录下所有.log文件
        log_files = [f for f in os.listdir(logs_dir) if f.endswith('.log')]
        if not log_files:
            return None
        
        # 按文件名排序，获取最新的文件
        log_files.sort(reverse=True)
        return os.path.join(logs_dir, log_files[0])
    
    def debug(self, message):
        self.logger.debug(message)
    
    def info(self, message):
        self.logger.info(message)
    
    def warning(self, message):
        self.logger.warning(message)
    
    def error(self, message):
        self.logger.error(message)
    
    def critical(self, message):
        self.logger.critical(message)

class CryptoTrader:
    def __init__(self):
        super().__init__()
        self.logger = Logger('poly')
        self.driver = None
        self.running = False
        self.trading = False
        self.login_running = False

        # 添加交易状态
        self.start_login_monitoring_running = False
        self.url_monitoring_running = False
        self.refresh_page_running = False

        # 添加重试次数和间隔
        self.retry_count = 3
        self.retry_interval = 5

        # 添加定时器
        self.refresh_page_timer = None  # 用于存储定时器ID
        self.url_check_timer = None

        # 添加登录状态监控定时器
        self.login_check_timer = None
        
        self.get_zero_time_cash_timer = None
        self.get_binance_zero_time_price_timer = None
        self.get_binance_price_websocket_timer = None
        self.comparison_binance_price_timer = None
        self.schedule_auto_find_coin_timer = None
        
        # 添加URL and refresh_page监控锁
        self.url_monitoring_lock = threading.Lock()
        self.refresh_page_lock = threading.Lock()
        self.login_attempt_lock = threading.Lock()
        self.restart_lock = threading.Lock()  # 添加重启锁
        self.is_restarting = False  # 重启状态标志

        # 添加元素缓存机制
        self.element_cache = {}
        self.cache_timeout = 30  # 缓存30秒后失效
        self.cache_lock = threading.Lock()
        self.restart_lock = threading.Lock()  # 添加重启锁
        self.is_restarting = False  # 重启状态标志

        # 初始化本金
        self.initial_amount = 0.4
        self.first_rebound = 127
        self.n_rebound = 127
        self.profit_rate = 1
        self.doubling_weeks = 60

        # 交易次数
        self.trade_count = 22
        
        # 真实交易次数 (22减去已交易次数)
        self.last_trade_count = 0

        # 默认买价
        self.default_target_price = 54 # 不修改

        # 添加交易次数计数器
        self.buy_count = 0
        self.sell_count = 0 
        self.reset_trade_count = 0

        # 买入价格冗余
        self.price_premium = 4 # 不修改
        
        # 按钮区域按键 WIDTH
        self.button_width = 8 # 不修改

        # 停止事件
        self.stop_event = threading.Event()

        # 初始化金额为 0
        for i in range(1, 4):  # 1到4
            setattr(self, f'yes{i}_amount', 0)
            setattr(self, f'no{i}_amount', 0)

         # 初始化 shares 属性
        self.shares = None
        self.price = None
        self.amount = None
        self.zero_time_cash_value = 0

        # 初始化状态数据管理器
        self.status_data = StatusDataManager()
        
        # 初始化状态数据
        self.status_data.update('account', 'initial_amount', self.initial_amount)
        self.status_data.update('account', 'first_rebound', self.first_rebound)
        self.status_data.update('account', 'n_rebound', self.n_rebound)
        self.status_data.update('account', 'profit_rate', f"{self.profit_rate}%")
        self.status_data.update('account', 'doubling_weeks', self.doubling_weeks)
        self.status_data.update('trading', 'trade_count', self.trade_count)
        
        # 初始化币种和时间信息到StatusDataManager
        # 注意：此时GUI还未创建，需要在setup_gui后再同步
        
        # 保持web_data兼容性 (用于向后兼容)
        self.web_data = {
            # 金额设置
            'initial_amount_entry': str(self.initial_amount),
            'first_rebound_entry': str(self.first_rebound),
            'n_rebound_entry': str(self.n_rebound),
            'profit_rate_entry': f"{self.profit_rate}%",
            'doubling_weeks_entry': str(self.doubling_weeks),
            
            # URL和币种设置
            'url_entry': '',
            'coin_combobox': 'BTC',
            'auto_find_time_combobox': '2:00',
            
            # 价格和金额输入框
            'yes1_price_entry': '0', 'yes1_amount_entry': '0',
            'yes2_price_entry': '0', 'yes2_amount_entry': '0',
            'yes3_price_entry': '0', 'yes3_amount_entry': '0',
            'yes4_price_entry': '0', 'yes4_amount_entry': '0',
            'no1_price_entry': '0', 'no1_amount_entry': '0',
            'no2_price_entry': '0', 'no2_amount_entry': '0',
            'no3_price_entry': '0', 'no3_amount_entry': '0',
            'no4_price_entry': '0', 'no4_amount_entry': '0',
            
            # 显示标签
            'trade_count_label': '22',
            'zero_time_cash_label': '--',
            'trading_pair_label': '--',
            'binance_zero_price_label': '--',
            'binance_now_price_label': '--',
            'binance_rate_label': '--',
            'binance_rate_symbol_label': '%',
            'yes_price_label': '--',
            'no_price_label': '--',
            'portfolio': '--',
            'cash': '--',
            
            # 按钮状态
            'start_button_state': 'normal',
            'set_amount_button_state': 'disabled',
            'find_coin_button_state': 'normal'
        }
        
        # 初始化零点时间现金值
        self.zero_time_cash_value = 0
        
        # 初始化Flask应用和历史记录
        self.csv_file = "cash_history.csv"
        # 首先尝试修复CSV文件（如果需要）
        self.repair_csv_file()
        self.cash_history = self.load_cash_history()
        self.flask_app = self.create_flask_app()
        self.start_flask_server()

        # 初始化配置和web模式
        try:
            self.config = self.load_config()
            self.setup_web_mode()
            
        except Exception as e:
            self.logger.error(f"初始化失败: {str(e)}")
            print(f"程序初始化失败: {str(e)}")
            sys.exit(1)

        # 初始化 UI 界面
        try:
            self.config = self.load_config()
            self.setup_gui()
            
        except Exception as e:
            self.logger.error(f"初始化失败: {str(e)}")
            messagebox.showerror("错误", "程序初始化失败，请检查日志文件")
            sys.exit(1)

        # 打印启动参数
        self.logger.info(f"✅ 初始化成功: {sys.argv}")
      
    def load_config(self):
        """加载配置文件，保持默认格式"""
        try:
            # 默认配置
            default_config = {
                'website': {'url': ''},
                'trading': {
                    'Up1': {'target_price': 0, 'amount': 0},
                    'Up2': {'target_price': 0, 'amount': 0},
                    'Up3': {'target_price': 0, 'amount': 0},
                    'Up4': {'target_price': 0, 'amount': 0},
                    'Up5': {'target_price': 0, 'amount': 0},

                    'Down1': {'target_price': 0, 'amount': 0},
                    'Down2': {'target_price': 0, 'amount': 0},
                    'Down3': {'target_price': 0, 'amount': 0},
                    'Down4': {'target_price': 0, 'amount': 0},
                    'Down5': {'target_price': 0, 'amount': 0}
                },
                'url_history': [],
                'selected_coin': 'BTC'  # 默认选择的币种
            }
            
            try:
                # 尝试读取现有配置
                with open('config.json', 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self.logger.info("✅ 成功加载配置文件")
                    
                    # 合并配置
                    for key in default_config:
                        if key not in saved_config:
                            saved_config[key] = default_config[key]
                        elif isinstance(default_config[key], dict):
                            for sub_key in default_config[key]:
                                if sub_key not in saved_config[key]:
                                    saved_config[key][sub_key] = default_config[key][sub_key]
                    return saved_config
            except FileNotFoundError:
                self.logger.warning("配置文件不存在，创建默认配置")
                with open('config.json', 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4, ensure_ascii=False)
                return default_config
            except json.JSONDecodeError:
                self.logger.error("配置文件格式错误，使用默认配置")
                with open('config.json', 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4, ensure_ascii=False)
                return default_config
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {str(e)}")
            raise
    
    def save_config(self):
        """保存配置到文件,保持JSON格式化"""
        try:
            for position, frame in [('Yes', self.yes_frame), ('No', self.no_frame)]:
                # 精确获取目标价格和金额的输入框
                entries = [
                    w for w in frame.winfo_children() 
                    if isinstance(w, ttk.Entry) and "price" in str(w).lower()
                ]
                amount_entries = [
                    w for w in frame.winfo_children()
                    if isinstance(w, ttk.Entry) and "amount" in str(w).lower()
                ]

                # 添加类型转换保护
                try:
                    target_price = float(entries[0].get().strip() or '0') if entries else 0
                except ValueError as e:
                    self.logger.error(f"价格转换失败: {e}, 使用默认值0")
                    target_price = 0

                try:
                    amount = float(amount_entries[0].get().strip() or '0') if amount_entries else 0
                except ValueError as e:
                    self.logger.error(f"金额转换失败: {e}, 使用默认值0")
                    amount = 0

                # 使用正确的配置键格式
                config_key = f"{'Up' if position == 'Yes' else 'Down'}1"  # 映射Yes->Up, No->Down
                self.config['trading'][config_key]['target_price'] = target_price
                self.config['trading'][config_key]['amount'] = amount

            # 处理网站地址历史记录
            current_url = self.url_entry.get().strip()
            if current_url:
                if 'url_history' not in self.config:
                    self.config['url_history'] = []
                
                # 清空历史记录
                self.config['url_history'].clear()
                # 只保留当前URL
                self.config['url_history'].insert(0, current_url)
                # 确保最多保留1条
                self.config['url_history'] = self.config['url_history'][:1]
                self.url_entry['values'] = self.config['url_history']
            
            # 保存第一次交易价格的时间设置
            if hasattr(self, 'auto_find_time_combobox'):
                self.config['auto_find_time'] = self.auto_find_time_combobox.get()
            
            # 保存币种选择设置
            if hasattr(self, 'coin_combobox'):
                self.config['selected_coin'] = self.coin_combobox.get()
            
            # 保存配置到文件，使用indent=4确保格式化
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(self.config, f)
                
        except Exception as e:
            self.logger.error(f"保存配置失败: {str(e)}")
            raise
    
    def setup_web_mode(self):
        """初始化Web模式，替代GUI界面"""
        self.logger.info("Web模式初始化完成")
        print("Web模式已启动，请在浏览器中访问 http://localhost:5000")
        
        # 加载配置到web_data
        if hasattr(self, 'config') and self.config:
            self.web_data['url_entry'] = self.config.get('website', {}).get('url', '')
            self.web_data['coin_combobox'] = self.config.get('coin', 'BTC')
            self.web_data['auto_find_time_combobox'] = self.auto_find_time_combobox.get() if hasattr(self, 'auto_find_time_combobox') else self.config.get('auto_find_time', '2:00')
    
    def get_web_value(self, key):
        """获取web数据值，替代GUI的get()方法"""
        return self.web_data.get(key, '')
    
    def get_gui_label_value(self, label_name):
        """直接从GUI标签获取实际值"""
        try:
            if hasattr(self, label_name):
                label = getattr(self, label_name)
                if hasattr(label, 'cget'):
                    text = label.cget('text')
                    # 处理带前缀的文本，如"Portfolio: 123.45" -> "123.45"
                    if ':' in text:
                        return text.split(':', 1)[1].strip()
                    return text
            return '--'
        except Exception as e:
            self.logger.error(f"获取GUI标签值失败 {label_name}: {e}")
            return '--'
    
    def _parse_date_for_sort(self, date_str):
        """解析日期字符串用于排序，支持多种日期格式"""
        try:
            return datetime.strptime(date_str, "%Y/%m/%d")
        except:
            try:
                return datetime.strptime(date_str, "%Y-%m-%d")
            except:
                return datetime.min
    
    def set_web_value(self, key, value):
        """设置web数据值，替代GUI的config()方法"""
        self.web_data[key] = str(value)
        # 同步更新到status_data
        self._sync_to_status_data(key, value)
    
    def set_web_state(self, key, state):
        """设置web组件状态，替代GUI的config(state=)方法"""
        state_key = f"{key}_state"
        if state_key in self.web_data:
            self.web_data[state_key] = state
            # 同步更新到status_data
            self._sync_to_status_data(state_key, state)
    
    def _sync_to_status_data(self, key, value):
        """将web_data的更新同步到status_data"""
        try:
            # 价格相关数据
            if 'price' in key.lower():
                if 'yes' in key.lower() or 'up' in key.lower():
                    self.status_data.update('prices', 'polymarket_up', str(value))
                elif 'no' in key.lower() or 'down' in key.lower():
                    self.status_data.update('prices', 'polymarket_down', str(value))
                elif 'binance' in key.lower():
                    if 'now' in key.lower():
                        self.status_data.update('prices', 'binance_current', str(value))
                    elif 'zero' in key.lower():
                        self.status_data.update('prices', 'binance_zero_time', str(value))
            
            # 账户相关数据
            elif 'cash' in key.lower():
                self.status_data.update('account', 'available_cash', str(value))
            elif 'portfolio' in key.lower():
                self.status_data.update('account', 'portfolio_value', str(value))
            
            # 交易相关数据
            elif 'amount' in key.lower():
                if 'yes' in key.lower():
                    self.status_data.update('trading', 'yes_amount', str(value))
                elif 'no' in key.lower():
                    self.status_data.update('trading', 'no_amount', str(value))
            
            # 系统状态
            elif 'monitoring' in key.lower():
                self.status_data.update('system', 'monitoring_status', str(value))
            elif 'url' in key.lower():
                self.status_data.update('trading', 'current_url', str(value))
            elif 'browser' in key.lower():
                self.status_data.update('system', 'browser_status', str(value))
                
        except Exception as e:
            self.logger.debug(f"同步数据到status_data失败: {e}")
    
    def _update_label_and_sync(self, label, text, data_category=None, data_key=None):
        """更新GUI标签并同步到status_data"""
        try:
            label.config(text=text)
            if data_category and data_key:
                self.status_data.update(data_category, data_key, text)
        except Exception as e:
            self.logger.debug(f"更新标签并同步失败: {e}")

    def setup_gui(self):
        """优化后的GUI界面设置"""
        self.root = tk.Tk()
        self.root.title("Polymarket Automatic Trading System Power by @wuxiancai")
        
        # 创建主滚动框架
        main_canvas = tk.Canvas(self.root, bg='#f8f9fa', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        
        # 创建内容Frame，放在Canvas里
        scrollable_frame = ttk.Frame(main_canvas)
        
        # 让Frame成为Canvas的一个window
        canvas_window = main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # 让scrollable_frame宽度始终和canvas一致
        def _on_canvas_configure(event):
            main_canvas.itemconfig(canvas_window, width=event.width)
        main_canvas.bind('<Configure>', _on_canvas_configure)

        # 让canvas的scrollregion始终覆盖全部内容
        def _on_frame_configure(event):
            main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        scrollable_frame.bind('<Configure>', _on_frame_configure)

        # pack布局，保证canvas和scrollbar都能自适应
        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        # 优化的滚动事件处理
        def _on_mousewheel(event):
            try:
                system = platform.system()
                if system == 'Linux':
                    delta = -1 if event.num == 4 else 1 if event.num == 5 else 0
                elif system == 'Darwin':
                    delta = -int(event.delta)
                else:  # Windows
                    delta = -int(event.delta/120)
                if delta:
                    main_canvas.yview_scroll(delta, "units")
            except Exception as e:
                self.logger.error(f"滚动事件处理错误: {str(e)}")
        
        def _on_arrow_key(event):
            try:
                delta = -1 if event.keysym == 'Up' else 1 if event.keysym == 'Down' else 0
                if delta:
                    main_canvas.yview_scroll(delta, "units")
            except Exception as e:
                self.logger.error(f"键盘滚动事件处理错误: {str(e)}")
        
        # 绑定滚动事件
        if platform.system() == 'Linux':
            main_canvas.bind_all("<Button-4>", _on_mousewheel)
            main_canvas.bind_all("<Button-5>", _on_mousewheel)
        else:
            main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        main_canvas.bind_all("<Up>", _on_arrow_key)
        main_canvas.bind_all("<Down>", _on_arrow_key)
        
        # 创建统一的样式配置
        style = ttk.Style()
        
        # 根据系统设置字体
        if platform.system() == 'Darwin':
            small_font = ('SF Pro Display', 10, 'normal')
            base_font = ('SF Pro Display', 12, 'normal')
            bold_font = ('SF Pro Display', 12, 'bold')
            large_font = ('SF Pro Display', 14, 'normal')
            title_font = ('SF Pro Display', 14, 'bold')
            huge_font = ('SF Pro Display', 16, 'bold')
        else:  # Linux and others
            small_font = ('DejaVu Sans', 10, 'normal')
            base_font = ('DejaVu Sans', 11, 'normal')
            bold_font = ('DejaVu Sans', 11, 'bold')
            large_font = ('DejaVu Sans', 13, 'normal')
            title_font = ('DejaVu Sans', 14, 'bold')
            huge_font = ('DejaVu Sans', 16, 'bold')
        
        # 配置样式
        styles_config = {
            'Red.TButton': {'foreground': '#dc3545', 'font': bold_font},
            'Black.TButton': {'foreground': '#212529', 'font': base_font},
            'Blue.TButton': {'foreground': '#0d6efd', 'font': base_font},
            'Red.TLabel': {'foreground': '#dc3545', 'font': large_font},
            'Red_bold.TLabel': {'foreground': '#dc3545', 'font': huge_font},
            'Black.TLabel': {'foreground': '#212529', 'font': base_font},
            'Top.TLabel': {'foreground': '#212529', 'font': base_font},
            'Warning.TLabelframe': {'font': title_font, 'foreground': '#FF0000', 'anchor': 'center'},
            'LeftAligned.TButton': {'anchor': 'w', 'foreground': '#212529', 'padding': (1, 1)},
            'Black.TLabelframe': {'font': small_font, 'foreground': '#212529', 'anchor': 'center'},
            'Centered.TLabelframe': {'font': base_font, 'foreground': '#212529'}
            
        }
        
        for style_name, config in styles_config.items():
            style.configure(style_name, **config)
        
        # 金额设置框架
        amount_settings_frame = ttk.LabelFrame(scrollable_frame, text="⚠️ 娟娟细流,终入大海! 宁静致远,财富自由!", 
                                             padding=(10, 8), style='Warning.TLabelframe')
        amount_settings_frame.pack(fill="x", padx=8, pady=6)

        # 创建主要设置容器
        settings_container = ttk.Frame(amount_settings_frame)
        settings_container.pack(fill=tk.X, pady=1)
        
        # 金额设置区域
        amount_frame = ttk.Frame(settings_container)
        amount_frame.pack(fill=tk.X, pady=1)

        # 设置金额配置
        settings_items = [
            ("Initial", "initial_amount_entry", self.initial_amount, 3),
            ("Turn-1", "first_rebound_entry", self.first_rebound, 3),
            ("Turn-N", "n_rebound_entry", self.n_rebound, 3),
            ("Margin", "profit_rate_entry", f"{self.profit_rate}%", 3)
        ]
        
        for i, (label_text, entry_attr, default_value, width) in enumerate(settings_items):
            item_frame = ttk.Frame(amount_frame)
            item_frame.pack(side=tk.LEFT, padx=2)
            
            ttk.Label(item_frame, text=label_text, style='Top.TLabel').pack(side=tk.LEFT, padx=(0, 2))
            entry = ttk.Entry(item_frame, width=width, font=base_font)
            entry.pack(side=tk.LEFT)
            entry.insert(0, str(default_value))
            setattr(self, entry_attr, entry)

        # 翻倍天数设置
        double_frame = ttk.Frame(amount_frame)
        double_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(double_frame, text="D.B", style='Top.TLabel').pack(side=tk.LEFT, padx=(0, 2))
        self.doubling_weeks_entry = ttk.Entry(double_frame, width=3)
        self.doubling_weeks_entry.pack(side=tk.LEFT)
        self.doubling_weeks_entry.insert(0, str(self.doubling_weeks))
        
        # 剩余交易次数设置
        trade_count_frame = ttk.Frame(amount_frame)
        trade_count_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(trade_count_frame, text="CNT:", style='Top.TLabel').pack(side=tk.LEFT, padx=(0, 1))
        self.trade_count_label = ttk.Label(trade_count_frame, text="22", style='Red_bold.TLabel')
        self.trade_count_label.pack(side=tk.LEFT, padx=(0, 1))

        # 监控网站配置
        url_frame = ttk.LabelFrame(scrollable_frame, text="Website Monitoring", padding=(8, 5))
        url_frame.pack(fill="x", padx=8, pady=6)
        
        url_container = ttk.Frame(url_frame)
        url_container.pack(fill="x", pady=2)
        
        ttk.Label(url_container, text="", style='Black.TLabel').pack(side=tk.LEFT, padx=(0, 5))
        self.url_entry = ttk.Combobox(url_container, font=base_font, width=2)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 从配置文件加载历史记录
        if 'url_history' not in self.config:
            self.config['url_history'] = []
        self.url_entry['values'] = self.config['url_history']
        
        # 如果有当前URL，设置为默认值
        current_url = self.config.get('website', {}).get('url', '')
        if current_url:
            self.url_entry.set(current_url)
        
        # 控制按钮区域
        control_frame = ttk.LabelFrame(scrollable_frame, text="Control Panel", padding=(8, 5))
        control_frame.pack(fill="x", padx=8, pady=6)
        
        # 主控制按钮行
        main_controls = ttk.Frame(control_frame)
        main_controls.pack(fill="x", pady=2)
        
        # 开始按钮
        self.start_button = ttk.Button(main_controls, text="Start", 
                                      command=self.start_monitoring, width=4,
                                      style='Blue.TButton')
        self.start_button.pack(side=tk.LEFT, padx=1)
        
        # 设置金额按钮
        self.set_amount_button = ttk.Button(main_controls, text="Set Amount", width=10,
                                           command=self.set_yes_no_cash, style='LeftAligned.TButton')
        self.set_amount_button.pack(side=tk.LEFT, padx=3)
        self.set_amount_button['state'] = 'disabled'

        # 币种选择
        ttk.Label(main_controls, text="Coin:", style='Black.TLabel').pack(side=tk.LEFT, padx=(2, 2))
        self.coin_combobox = ttk.Combobox(main_controls, values=['BTC', 'ETH', 'SOL', 'XRP'], width=3)
        self.coin_combobox.pack(side=tk.LEFT, padx=2)
        
        # 从配置文件加载保存的币种选择
        saved_coin = self.config.get('selected_coin', 'BTC')
        self.coin_combobox.set(saved_coin)
        
        # 绑定币种选择变化事件
        self.coin_combobox.bind('<<ComboboxSelected>>', self.on_coin_changed)
        
        # 手动找币按钮
        self.find_coin_button = ttk.Button(main_controls, text="F.Coin", width=5,
                                           command=lambda: self.find_54_coin(), style='LeftAligned.TButton')
        self.find_coin_button.pack(side=tk.LEFT, padx=1)

        # 零点时间CASH 显示
        ttk.Label(main_controls, text="Cash:", style='Black.TLabel').pack(side=tk.LEFT, padx=(0, 2))
        self.zero_time_cash_label = ttk.Label(main_controls, text="0", style='Red.TLabel')
        self.zero_time_cash_label.pack(side=tk.LEFT)
        
        # 安排每日0:30记录Cash到CSV（root已就绪）
        try:
            self.schedule_record_cash_daily()
        except Exception as e:
            self.logger.error(f"安排每日记录任务失败: {e}")
        
        # 设置第一次交易价格的时间选择
        auto_find_frame = ttk.Frame(main_controls)
        auto_find_frame.pack(fill="x", pady=2)
        
        self.auto_find_time_combobox = ttk.Combobox(auto_find_frame, values=['1:00', '2:00', '3:00', '4:00', '5:00', '6:00', '7:00', '8:00', '9:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00', '21:00', '22:00', '23:00'], width=5, state='readonly')
        self.auto_find_time_combobox.pack(side=tk.LEFT, padx=2)
        
        # 从配置文件加载保存的时间设置
        saved_time = self.config.get('auto_find_time', '2:00')
        self.auto_find_time_combobox.set(saved_time)
        
        # 绑定时间选择变化事件
        self.auto_find_time_combobox.bind('<<ComboboxSelected>>', self.on_auto_find_time_changed)

        # 交易币对显示
        pair_container = ttk.Frame(scrollable_frame)
        pair_container.pack(fill="x", pady=2)
        
        ttk.Label(pair_container, text="Trading Pair:", style='Black.TLabel').pack(side=tk.LEFT, padx=(8, 5))
        self.trading_pair_label = ttk.Label(pair_container, text="----", style='Black.TLabel')
        self.trading_pair_label.pack(side=tk.LEFT)

        # 币安价格信息
        binance_price_frame = ttk.LabelFrame(scrollable_frame, text="Binance Price", padding=(8, 5), style='Centered.TLabelframe')
        binance_price_frame.pack(fill="x", padx=8, pady=6)

        binance_container = ttk.Frame(binance_price_frame)
        binance_container.pack(pady=2)
        
        # 币安价格信息网格布局
        price_info_items = [
            ("Midnight:", "binance_zero_price_label", "0"),
            ("Now:", "binance_now_price_label", "0"),
            ("Rate:", "binance_rate_display", "0%")
        ]
        
        for i, (label_text, attr_name, default_value) in enumerate(price_info_items):
            item_frame = ttk.Frame(binance_container)
            item_frame.pack(side=tk.LEFT, padx=5)
            
            ttk.Label(item_frame, text=label_text, style='Black.TLabel').pack(side=tk.LEFT)
            
            if attr_name == "binance_rate_display":
                # 创建涨跌显示容器
                rate_frame = ttk.Frame(item_frame)
                rate_frame.pack(side=tk.LEFT, padx=(2, 0))
                
                self.binance_rate_label = ttk.Label(rate_frame, text="0", style='Black.TLabel')
                self.binance_rate_label.pack(side=tk.LEFT)
                
                self.binance_rate_symbol_label = ttk.Label(rate_frame, text="%", style='Black.TLabel')
                self.binance_rate_symbol_label.pack(side=tk.LEFT)
            else:
                label = ttk.Label(item_frame, text=default_value, font=large_font, foreground='blue')
                label.pack(side=tk.LEFT, padx=(2, 0))
                setattr(self, attr_name, label)
        
        # 实时价格显示区域
        price_frame = ttk.LabelFrame(scrollable_frame, text="Live Prices", padding=(8, 5))
        price_frame.pack(fill="x", padx=8, pady=6)
        
        # 价格显示容器
        prices_container = ttk.Frame(price_frame)
        prices_container.pack(fill="x", pady=2)
        
        # Up/Down 价格和份额显示
        price_items = [
            ("Up:", "yes_price_label", "Up: --"),
            ("Down:", "no_price_label", "Down: --")
        ]
        
        for i, (icon_text, attr_name, default_text) in enumerate(price_items):
            item_container = ttk.Frame(prices_container)
            item_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            # 价格显示
            price_frame_item = ttk.Frame(item_container)
            price_frame_item.pack(fill="x", pady=1)
            
            price_label = ttk.Label(price_frame_item, text=default_text, 
                                   font=(base_font[0], 16, 'bold'), foreground='#9370DB')
            price_label.pack()
            setattr(self, attr_name, price_label)

        # 资金显示区域
        balance_frame = ttk.LabelFrame(scrollable_frame, text="Account Balance", padding=(8, 5))
        balance_frame.pack(fill="x", padx=8, pady=6)
        
        balance_container = ttk.Frame(balance_frame)
        balance_container.pack(fill="x", pady=2)
        
        # Portfolio 和 Cash 显示
        balance_items = [
            ("Portfolio:", "portfolio_label", "Portfolio: --"),
            ("Cash:", "cash_label", "Cash: --")
        ]
        
        for i, (label_text, attr_name, default_text) in enumerate(balance_items):
            item_frame = ttk.Frame(balance_container)
            item_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
            
            balance_label = ttk.Label(item_frame, text=default_text, 
                                     font=(base_font[0], 14, 'normal'), foreground='#16A34A')
            balance_label.pack()
            setattr(self, attr_name, balance_label)
        
        # 创建UP 和 DOWN 价格和金额左右分栏
        config_container = ttk.Frame(scrollable_frame)
        config_container.pack(fill="x", pady=2)
        
        # Up 区域配置
        self.yes_frame = ttk.LabelFrame(config_container, text="Up Positions", padding=(5, 3))
        self.yes_frame.grid(row=0, column=0, padx=(0, 4), sticky="nsew")
        config_container.grid_columnconfigure(0, weight=1)

        # Down 配置区域
        self.no_frame = ttk.LabelFrame(config_container, text="Down Positions", padding=(5, 3))
        self.no_frame.grid(row=0, column=1, padx=(4, 0), sticky="nsew")
        config_container.grid_columnconfigure(1, weight=1)
        
        # Up 配置项
        up_configs = [
            ("Up1", "yes1_price_entry", "yes1_amount_entry", "0", "0"),
            ("Up2", "yes2_price_entry", "yes2_amount_entry", "0", "0"),
            ("Up3", "yes3_price_entry", "yes3_amount_entry", "0", "0"),
            ("Up4", "yes4_price_entry", "yes4_amount_entry", "0", "0"),
            ("Up5", "yes5_price_entry", None, "0", "0")
        ]
        
        for i, (label, price_attr, amount_attr, price_val, amount_val) in enumerate(up_configs):
            row_base = i * 2
            
            # 价格标签和输入框
            ttk.Label(self.yes_frame, text=f"{label} Price(¢):", style='Black.TLabel').grid(
                row=row_base, column=0, padx=3, pady=2, sticky="w")
            price_entry = ttk.Entry(self.yes_frame, font=base_font)
            price_entry.insert(0, price_val)
            price_entry.grid(row=row_base, column=1, padx=3, pady=2, sticky="ew")
            setattr(self, price_attr, price_entry)
            
            # 金额标签和输入框（仅当amount_attr不为None时创建）
            if amount_attr is not None:
                ttk.Label(self.yes_frame, text=f"{label} Amount:", style='Black.TLabel').grid(
                    row=row_base+1, column=0, padx=3, pady=2, sticky="w")
                amount_entry = ttk.Entry(self.yes_frame, font=base_font)
                amount_entry.insert(0, amount_val)
                amount_entry.grid(row=row_base+1, column=1, padx=3, pady=2, sticky="ew")
                setattr(self, amount_attr, amount_entry)
        
        # 配置列权重
        self.yes_frame.grid_columnconfigure(1, weight=1)

        # Down 配置项
        down_configs = [
            ("Down1", "no1_price_entry", "no1_amount_entry", "0", "0"),
            ("Down2", "no2_price_entry", "no2_amount_entry", "0", "0"),
            ("Down3", "no3_price_entry", "no3_amount_entry", "0", "0"),
            ("Down4", "no4_price_entry", "no4_amount_entry", "0", "0"),
            ("Down5", "no5_price_entry", None, "0", "0")
        ]
        
        for i, (label, price_attr, amount_attr, price_val, amount_val) in enumerate(down_configs):
            row_base = i * 2
            
            # 价格标签和输入框
            ttk.Label(self.no_frame, text=f"{label} Price(¢):", style='Black.TLabel').grid(
                row=row_base, column=0, padx=3, pady=2, sticky="w")
            price_entry = ttk.Entry(self.no_frame, font=base_font)
            price_entry.insert(0, price_val)
            price_entry.grid(row=row_base, column=1, padx=3, pady=2, sticky="ew")
            setattr(self, price_attr, price_entry)
            
            # 金额标签和输入框（仅当amount_attr不为None时创建）
            if amount_attr is not None:
                ttk.Label(self.no_frame, text=f"{label} Amount:", style='Black.TLabel').grid(
                    row=row_base+1, column=0, padx=3, pady=2, sticky="w")
                amount_entry = ttk.Entry(self.no_frame, font=base_font)
                amount_entry.insert(0, amount_val)
                amount_entry.grid(row=row_base+1, column=1, padx=3, pady=2, sticky="ew")
                setattr(self, amount_attr, amount_entry)
        
        # 配置列权重
        self.no_frame.grid_columnconfigure(1, weight=1)

        # 创建按钮区域
        trade_frame = ttk.LabelFrame(scrollable_frame, text="Buttons", style='Black.TLabelframe')
        trade_frame.pack(fill="x", padx=2, pady=2)
        
        # 按钮配置
        button_configs = [
            # 第一行：主要交易按钮
            [("buy_button", "Buy", self.click_buy),
             ("buy_yes_button", "Buy-Up", self.click_buy_yes),
             ("buy_no_button", "Buy-Down", self.click_buy_no)],
            # 第二行：确认和金额按钮
            [("buy_confirm_button", "Buy-confirm", self.click_buy_confirm_button),
             ("amount_yes1_button", "Amount-Up1", None),
             ("amount_yes2_button", "Amount-Up2", None)],
            # 第三行：Yes金额按钮
            [("amount_yes3_button", "Amount-Up3", None),
             ("amount_yes4_button", "Amount-Up4", None),
             ("amount_no1_button", "Amount-Down1", None)],
            # 第四行：No金额按钮
            [("amount_no2_button", "Amount-Down2", None),
             ("amount_no3_button", "Amount-Down3", None),
             ("amount_no4_button", "Amount-Down4", None)],
            # 第五行：卖出按钮
            [("position_sell_yes_button", "Positions-Sell-Up", self.click_position_sell_yes),
             ("position_sell_no_button", "Positions-Sell-Down", self.click_position_sell_no),
             ("sell_confirm_button", "Sell-confirm", self.click_sell_confirm_button)]
        ]
        
        for row, button_row in enumerate(button_configs):
            for col, (attr_name, text, command) in enumerate(button_row):
                if attr_name:  # 跳过占位符
                    button = ttk.Button(trade_frame, text=text, width=self.button_width)
                    
                    if command:
                        button.configure(command=command)
                    else:
                        # 金额按钮：改为使用 command 以便支持 invoke()
                        # 通过 lambda 传递具体按钮引用
                        button.configure(command=lambda: None) # 这里原来是绑定click_amount函数
                    
                    button.grid(row=row, column=col, padx=2, pady=2, sticky="ew")
                    setattr(self, attr_name, button)
        
        # 配置列权重使按钮均匀分布
        for i in range(3):
            trade_frame.grid_columnconfigure(i, weight=1)
            
        # 窗口自适应内容大小
        self.root.update_idletasks()
        
        content_height = scrollable_frame.winfo_reqheight()
        
        # 计算并设置窗口的初始大小
        final_width = 550
        # 高度自适应，确保能显示所有内容
        final_height = max(300, content_height)

        self.root.geometry(f'{final_width}x{final_height}+0+0')
        self.root.minsize(300, final_height)
        
        # 最后一次更新确保布局正确
        self.root.update_idletasks()
        
        # 初始化币种和时间信息到StatusDataManager
        initial_coin = self.coin_combobox.get()
        initial_time = self.auto_find_time_combobox.get()
        self.status_data.update('trading_info', 'coin', initial_coin)
        self.status_data.update('trading_info', 'time', initial_time)
    
    def start_monitoring(self):
        """开始监控"""
        # 直接使用当前显示的网址
        target_url = self.url_entry.get().strip()
        self.logger.info(f"\033[34m✅ 开始监控网址: {target_url}\033[0m")
        
        # 启用开始按钮，启用停止按钮
        self.start_button['state'] = 'disabled'
            
        # 将"开始监控"文字变为红色
        self.start_button.configure(style='Red.TButton')
        
        # 重置交易次数计数器
        self.buy_count = 0

        # 启动浏览器作线程
        threading.Thread(target=self._start_browser_monitoring, args=(target_url,), daemon=True).start()

        self.running = True

        # 1.启用设置金额按钮
        self.set_amount_button['state'] = 'normal'

        # 2.检查是否登录
        self.login_check_timer = self.root.after(4000, self.start_login_monitoring)

        # 3.启动URL监控
        self.url_check_timer = self.root.after(8000, self.start_url_monitoring)

        # 4.启动零点 CASH 监控
        self.root.after(3000, self.schedule_get_zero_time_cash)

        # 5.启动币安零点时价格监控
        self.get_binance_zero_time_price_timer = self.root.after(14000, self.get_binance_zero_time_price)
        
        # 6.启动币安实时价格监控
        self.get_binance_price_websocket_timer = self.root.after(16000, self.get_binance_price_websocket)

        # 7.启动币安价格对比
        self.comparison_binance_price_timer = self.root.after(20000, self.comparison_binance_price)

        # 8.启动自动找币
        self.root.after(30000, self.schedule_auto_find_coin)

        # 9.启动设置 YES1/NO1价格为 54
        self.root.after(36000, self.schedule_price_setting)
        
        # 10.启动页面刷新
        self.refresh_page_timer = self.root.after(40000, self.refresh_page)
        self.logger.info("\033[34m✅ 40秒后启动页面刷新!\033[0m")
        
        # 11.启动夜间自动卖出检查（每30分钟检查一次）
        self.root.after(45000, self.schedule_night_auto_sell_check)
        
        # 12.启动自动Swap检查（每30分钟检查一次）
        self.root.after(100000, self.schedule_auto_use_swap)

        # 13.启动自动清除缓存
        self.root.after(120000, self.schedule_clear_chrome_mem_cache)

        # 14. 启动程序立即获取当前CASH值
        self.root.after(50000, self.get_cash_value)
        
        # 15.每天 0:30 获取 cash 值并展示历史记录页面
        self.root.after(60000, self.schedule_record_and_show_cash)
           
    def _start_browser_monitoring(self, new_url):
        """在新线程中执行浏览器操作"""
        try:
            if not self.driver and not self.is_restarting:
                chrome_options = Options()
                chrome_options.debugger_address = "127.0.0.1:9222"
                chrome_options.add_argument('--disable-dev-shm-usage')

                # 清理旧配置
                os.system('rm -f ~/ChromeDebug/SingletonLock')
                os.system('rm -f ~/ChromeDebug/SingletonCookie')
                os.system('rm -f ~/ChromeDebug/SingletonSocket')
                os.system('rm -f ~/ChromeDebug/Default/Recovery/*')
                os.system('rm -f ~/ChromeDebug/Default/Sessions/*')
                os.system('rm -f ~/ChromeDebug/Default/Last*')

                system = platform.system()
                if system == 'Linux':
                    # 添加与启动脚本一致的所有参数
                    chrome_options.add_argument('--no-sandbox')
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
                    chrome_options.add_argument('--disable-features=TranslateUI,BlinkGenPropertyTrees,SitePerProcess,IsolateOrigins')
                    chrome_options.add_argument('--noerrdialogs')
                    chrome_options.add_argument('--disable-infobars')
                    chrome_options.add_argument('--disable-notifications')
                    chrome_options.add_argument('--test-type')
                    
                self.driver = webdriver.Chrome(options=chrome_options)
            try:
                # 在当前标签页打开URL
                self.driver.get(new_url)
                
                # 等待页面加载
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )
                self.logger.info("\033[34m✅ 浏览器启动成功!\033[0m")
                
                # 保存配置
                if 'website' not in self.config:
                    self.config['website'] = {}
                self.config['website']['url'] = new_url
                
                # 更新URL历史记录
                if 'url_history' not in self.config:
                    self.config['url_history'] = []
                if new_url not in self.config['url_history']:
                    self.config['url_history'].insert(0, new_url)
                    # 保持历史记录不超过10条
                    self.config['url_history'] = self.config['url_history'][:10]
                    self.url_entry['values'] = self.config['url_history']
                
                self.save_config()
                
                # 更新交易币对显示
                try:
                    pair = re.search(r'event/([^?]+)', new_url)
                    if pair:
                        self.trading_pair_label.config(text=pair.group(1))
                    else:
                        self.trading_pair_label.config(text="无识别事件名称")
                except Exception:
                    self.trading_pair_label.config(text="解析失败")
                    
                #  开启监控
                self.running = True
                
                # 启动监控线程
                self.monitoring_thread = threading.Thread(target=self.monitor_prices, daemon=True)
                self.monitoring_thread.start()
                self.logger.info("\033[34m✅ 启动实时监控价格和资金线程\033[0m")
                
            except Exception as e:
                error_msg = f"加载网站失败: {str(e)}"
                self.logger.error(error_msg)
                self._show_error_and_reset(error_msg)  
        except Exception as e:
            error_msg = f"启动浏览器失败: {str(e)}"
            self.logger.error(f"启动监控失败: {str(e)}")
            self.logger.error(error_msg)
            self._show_error_and_reset(error_msg)

    def _show_error_and_reset(self, error_msg):
        """显示错误并重置按钮状态"""
        # 用after方法确保在线程中执行GUI操作
        # 在尝试显示消息框之前，检查Tkinter主窗口是否仍然存在
        if self.root and self.root.winfo_exists():
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
            self.root.after(0, lambda: self.start_button.config(state='normal'))
        else:
            # 如果主窗口不存在，则直接记录错误到日志
            self.logger.error(f"GUI主窗口已销毁,无法显示错误消息: {error_msg}")
        self.running = False

    def monitor_prices(self):
        """优化版价格监控 - 动态调整监控频率"""
        base_interval = 0.3  # 基础监控间隔300ms
        error_count = 0
        
        while not self.stop_event.is_set():
            try:
                start_time = time.time()
                
                self.check_balance()
                self.check_prices()
                
                # 根据执行时间动态调整间隔
                execution_time = time.time() - start_time
                sleep_time = max(0.1, base_interval - execution_time)
                
                time.sleep(sleep_time)
                error_count = 0  # 重置错误计数
                
            except (StaleElementReferenceException, NoSuchElementException) as e:
                error_count += 1
                self.logger.warning(f"元素引用失效: {str(e)}")
                # 轻量级重试
                sleep_time = min(2, base_interval * (2 ** error_count))
                time.sleep(sleep_time)
            except (TimeoutException, AttributeError) as e:
                error_count += 1
                self.logger.error(f"浏览器连接异常: {str(e)}")
                # 浏览器级别重试
                sleep_time = min(5, base_interval * (2 ** error_count))
                if error_count > 3:
                    self.logger.error("连续浏览器异常，尝试重启")
                    self.restart_browser()
                    error_count = 0
                time.sleep(sleep_time)
            except Exception as e:
                error_count += 1
                self.logger.error(f"价格监控异常: {str(e)}")
                # 通用异常处理
                sleep_time = min(5, base_interval * (2 ** error_count))
                time.sleep(sleep_time)
    
    def restart_browser(self,force_restart=True):
        """统一的浏览器重启/重连函数
        Args:
            force_restart: True=强制重启Chrome进程,False=尝试重连现有进程
        """
        # 清空元素缓存，因为浏览器即将重启
        self._clear_element_cache()
        
        # 先关闭浏览器
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.warning(f"关闭浏览器失败: {str(e)}")
                
        # 彻底关闭所有Chrome进程
        if force_restart:
            try:
                system = platform.system()
                if system == "Windows":
                    subprocess.run("taskkill /f /im chrome.exe", shell=True)
                    subprocess.run("taskkill /f /im chromedriver.exe", shell=True)
                elif system == "Darwin":  # macOS
                    subprocess.run("pkill -9 'Google Chrome'", shell=True)
                    subprocess.run("pkill -9 'chromedriver'", shell=True)
                else:  # Linux
                    subprocess.run("pkill -9 chrome", shell=True)
                    subprocess.run("pkill -9 chromedriver", shell=True)
                    
                self.logger.info("已强制关闭所有Chrome进程")
            except Exception as e:
                self.logger.error(f"强制关闭Chrome进程失败: {str(e)}")
                
        self.driver = None

        # 检查是否已在重启中
        with self.restart_lock:
            if self.is_restarting:
                self.logger.info("浏览器正在重启中，跳过重复重启")
                return True
            self.is_restarting = True

        try:
            self.logger.info(f"正在{'重启' if force_restart else '重连'}浏览器...")
            
            # 1. 清理现有连接
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None
            
            # 2. 如果需要强制重启，启动新的Chrome进程
            if force_restart:
                try:
                    # 根据操作系统选择启动脚本
                    script_path = ('start_chrome_macos.sh' if platform.system() == 'Darwin' 
                                else 'start_chrome_ubuntu.sh')
                    script_path = os.path.abspath(script_path)
                    
                    # 检查脚本是否存在
                    if not os.path.exists(script_path):
                        raise FileNotFoundError(f"启动脚本不存在: {script_path}")
                    
                    # 启动Chrome进程（异步）
                    process = subprocess.Popen(['bash', script_path], 
                                             stdout=subprocess.PIPE, 
                                             stderr=subprocess.PIPE)
                    
                    # 等待Chrome调试端口可用
                    max_wait_time = 30
                    wait_interval = 1
                    for wait_time in range(0, max_wait_time, wait_interval):
                        time.sleep(wait_interval)
                        try:
                            # 检查调试端口是否可用
                            import requests
                            response = requests.get('http://127.0.0.1:9222/json', timeout=2)
                            if response.status_code == 200:
                                self.logger.info(f"✅ Chrome浏览器已重新启动,调试端口可用 (等待{wait_time+1}秒)")
                                break
                        except:
                            continue
                    else:
                        raise Exception("Chrome调试端口在30秒内未能启动")
                    
                except Exception as e:
                    self.logger.error(f"启动Chrome失败: {e}")
                    self.restart_browser(force_restart=True)
                    return False
            
            # 3. 重新连接浏览器（带重试机制）
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    chrome_options = Options()
                    chrome_options.debugger_address = "127.0.0.1:9222"
                    chrome_options.add_argument('--disable-dev-shm-usage')

                    # 清理旧配置
                    os.system('rm -f ~/ChromeDebug/SingletonLock')
                    os.system('rm -f ~/ChromeDebug/SingletonCookie')
                    os.system('rm -f ~/ChromeDebug/SingletonSocket')
                    os.system('rm -f ~/ChromeDebug/Default/Recovery/*')
                    os.system('rm -f ~/ChromeDebug/Default/Sessions/*')
                    os.system('rm -f ~/ChromeDebug/Default/Last*')

                    # Linux特定配置
                    if platform.system() == 'Linux':
                        
                        # 添加与启动脚本一致的所有参数
                        chrome_options.add_argument('--no-sandbox')
                        chrome_options.add_argument('--disable-gpu')
                        chrome_options.add_argument('--disable-software-rasterizer')
                        chrome_options.add_argument('--disable-dev-shm-usage')
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
                        chrome_options.add_argument('--disable-features=TranslateUI,BlinkGenPropertyTrees,SitePerProcess,IsolateOrigins')
                        chrome_options.add_argument('--noerrdialogs')
                        chrome_options.add_argument('--disable-infobars')
                        chrome_options.add_argument('--disable-notifications')
                        chrome_options.add_argument('--test-type')
                        
                    self.driver = webdriver.Chrome(options=chrome_options)
                    
                    # 验证连接
                    self.driver.execute_script("return navigator.userAgent")
                    
                    # 加载目标URL
                    target_url = self.url_entry.get()
                    if target_url:
                        self.driver.get(target_url)
                        WebDriverWait(self.driver, 10).until(
                            lambda d: d.execute_script('return document.readyState') == 'complete'
                        )
                        self.logger.info(f"✅ 成功加载页面: {target_url}")
                    
                    self.logger.info("✅ 浏览器连接成功")

                    # 连接成功后，重置监控线程
                    self._restore_monitoring_state()
                    return True
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        self.logger.warning(f"连接失败 ({attempt+1}/{max_retries}),2秒后重试: {e}")
                        time.sleep(2)
                    else:
                        self.logger.error(f"浏览器连接最终失败: {e}")
                        return False
            return False
            
        except Exception as e:
            self.logger.error(f"浏览器重启失败: {e}")
            self._send_chrome_alert_email()
            return False
        
        finally:
            with self.restart_lock:
                self.is_restarting = False

    def restart_browser_after_auto_find_coin(self):
        """重连浏览器后自动检查并更新URL中的日期"""
        try:
            # 从GUI获取当前监控的URL
            new_url = self.url_entry.get().strip()
            current_url = new_url.split('?', 1)[0].split('#', 1)[0]
            if not current_url:
                self.logger.info("📅 URL为空,跳过日期检查")
                return
            
            self.logger.info(f"📅 检查URL中的日期: {current_url}")
            
            # 从URL中提取日期 (例如: july-13)
            date_pattern = r'(january|february|march|april|may|june|july|august|september|october|november|december)-(\d{1,2})'
            match = re.search(date_pattern, current_url.lower())
            
            if not match:
                self.logger.info("📅 URL中未找到日期格式,跳过日期检查")
                return
            
            url_month = match.group(1)
            url_day = int(match.group(2))
            
            # 获取当前日期并格式化为相同格式
            current_date = datetime.now()
            current_month = current_date.strftime("%B").lower()  # 获取完整月份名称并转小写
            current_day = current_date.day
            
            current_date_str = f"{current_month}-{current_day}"
            url_date_str = f"{url_month}-{url_day}"
            
            self.logger.info(f"URL日期: {url_date_str}, 当前日期: {current_date_str}")
            
            # 比较日期
            if url_date_str == current_date_str:
                self.logger.info("📅 日期匹配,无需更新URL")
                return
            
            # 日期不匹配，需要更新URL
            self.logger.info(f"\033[31m日期不匹配,更新URL中的日期从 {url_date_str} 到 {current_date_str}\033[0m")
            
            # 替换URL中的日期
            old_date_pattern = f"{url_month}-{url_day}"
            new_date_pattern = f"{current_month}-{current_day}"
            updated_url = current_url.replace(old_date_pattern, new_date_pattern)
            
            # 更新GUI中的URL
            self.url_entry.delete(0, 'end')
            self.url_entry.insert(0, updated_url)
            
            # 保存到配置文件
            if 'website' not in self.config:
                self.config['website'] = {}
            self.config['website']['url'] = updated_url
            
            # 更新URL历史记录
            if 'url_history' not in self.config:
                self.config['url_history'] = []
            if updated_url not in self.config['url_history']:
                self.config['url_history'].insert(0, updated_url)
                # 保持历史记录不超过10条
                self.config['url_history'] = self.config['url_history'][:10]
                self.url_entry['values'] = self.config['url_history']
            
            self.save_config()
            
            self.logger.info(f"✅ \033[34mURL已更新为: {updated_url}\033[0m")
            
            # 如果浏览器已经打开，导航到新URL
            if self.driver:
                try:
                    self.driver.get(updated_url)
                    self.logger.info(f"✅ \033[34m浏览器已导航到新URL\033[0m")
                except Exception as e:
                    self.logger.error(f"导航到新URL失败: {e}")
            
        except Exception as e:
            self.logger.error(f"日期检查和更新失败: {e}")

    def _restore_monitoring_state(self):
        """恢复监控状态 - 重新同步监控逻辑，确保所有监控功能正常工作"""
        try:
            self.logger.info("🔄 恢复监控状态...")
            
            # 确保运行状态正确
            self.running = True
            
            # 重连浏览器后自动检查并更新URL中的日期
            self.restart_browser_after_auto_find_coin()
            
            # 重新启动各种监控功能（不是重新创建定时器，而是确保监控逻辑正常）
            # 1. 重新启动登录监控（如果当前没有运行）
            if hasattr(self, 'login_check_timer') and self.login_check_timer:
                self.root.after_cancel(self.login_check_timer)
            self.start_login_monitoring()
            self.logger.info("✅ 恢复了登录监控定时器")
            
            # 2. 重新启动URL监控（如果当前没有运行）
            if hasattr(self, 'url_check_timer') and self.url_check_timer:
                self.root.after_cancel(self.url_check_timer) 
            self.start_url_monitoring()
            self.logger.info("✅ 恢复了URL监控定时器")
            
            # 3. 重新启动页面刷新监控（如果当前没有运行）
            if hasattr(self, 'refresh_page_timer') and self.refresh_page_timer:
                self.root.after_cancel(self.refresh_page_timer)     
            self.refresh_page()
            self.logger.info("✅ 恢复了页面刷新监控定时器")

            # 6.重新开始价格比较
            if hasattr(self,'comparison_binance_price_timer') and self.comparison_binance_price_timer:
                self.root.after_cancel(self.comparison_binance_price_timer)
            self.comparison_binance_price()
            self.logger.info("✅ 恢复了价格比较定时器")
            
            # 7.重新启动自动找币功能
            if hasattr(self,'schedule_auto_find_coin_timer') and self.schedule_auto_find_coin_timer:
                self.root.after_cancel(self.schedule_auto_find_coin_timer)
            self.schedule_auto_find_coin()
            self.logger.info("✅ 恢复了自动找币定时器")

            # 8.重新启动夜间自动卖出检查
            if hasattr(self,'night_auto_sell_timer') and self.night_auto_sell_timer:
                self.root.after_cancel(self.night_auto_sell_timer)
            self.schedule_night_auto_sell_check()
            self.logger.info("✅ 恢复了夜间自动卖出检查定时器")
            
            # 9.重新启动自动Swap检查
            if hasattr(self,'auto_use_swap_timer') and self.auto_use_swap_timer:
                self.root.after_cancel(self.auto_use_swap_timer)
            self.schedule_auto_use_swap()
            self.logger.info("✅ 恢复了自动Swap检查定时器")
            
            # 10.重新启动自动清除缓存
            if hasattr(self,'clear_chrome_mem_cache_timer') and self.clear_chrome_mem_cache_timer:
                self.root.after_cancel(self.clear_chrome_mem_cache_timer)
            self.clear_chrome_mem_cache()
            self.logger.info("✅ 恢复了自动清除缓存定时器")

            # 智能恢复时间敏感类定时器
            current_time = datetime.now()
            
            # 8. binance_zero_timer: 计算到下一个零点的时间差
            next_zero_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            if current_time >= next_zero_time:
                next_zero_time += timedelta(days=1)
            
            seconds_until_next_run = int((next_zero_time - current_time).total_seconds() * 1000)  # 转换为毫秒
            
            # 只在合理的时间范围内恢复零点价格定时器
            if seconds_until_next_run > 0:
                self.get_binance_zero_time_price_timer = self.root.after(seconds_until_next_run, self.get_binance_zero_time_price)
                self.logger.info(f"✅ 恢复获取币安零点价格定时器，{round(seconds_until_next_run / 3600000, 2)} 小时后执行")
            
            # 9. zero_cash_timer: 类似的计算逻辑
            # 现金监控可以稍微提前一点，比如在23:59:30开始
            next_cash_time = current_time.replace(hour=23, minute=59, second=30, microsecond=0)
            if current_time >= next_cash_time:
                next_cash_time += timedelta(days=1)
            
            seconds_until_cash_run = int((next_cash_time - current_time).total_seconds() * 1000)
            
            if seconds_until_cash_run > 0:
                self.get_zero_time_cash_timer = self.root.after(seconds_until_cash_run, self.get_zero_time_cash)
                self.logger.info(f"✅ 恢复获取零点 CASH定时器,{round(seconds_until_cash_run / 3600000, 2)} 小时后执行")
            
            # 11. 重新启动币安价格WebSocket定时器
            if hasattr(self, 'get_binance_price_websocket_timer') and self.get_binance_price_websocket_timer:
                self.root.after_cancel(self.get_binance_price_websocket_timer)
            self.get_binance_price_websocket_timer = self.root.after(16000, self.get_binance_price_websocket)
            self.logger.info("✅ 恢复了币安价格WebSocket定时器")
            
            # 12. 重新启动设置默认目标价格定时器（如果需要）
            # 注意：这个定时器通常由用户操作触发，这里只是确保清理状态
            if hasattr(self, 'set_yes1_no1_default_target_price_timer') and self.set_yes1_no1_default_target_price_timer:
                self.root.after_cancel(self.set_yes1_no1_default_target_price_timer)
                self.set_yes1_no1_default_target_price_timer = None
            self.logger.info("✅ 清理了设置默认目标价格定时器状态")
            
            # 13. 重新启动重试更新金额定时器（如果需要）
            # 注意：这个定时器通常由错误情况触发，这里只是确保清理状态
            if hasattr(self, 'retry_update_amount_timer') and self.retry_update_amount_timer:
                self.root.after_cancel(self.retry_update_amount_timer)
                self.retry_update_amount_timer = None
            self.logger.info("✅ 清理了重试更新金额定时器状态")
            
            # 14. 重新启动币安零点价格线程定时器（如果需要）
            # 注意：这个是threading.Timer，需要特殊处理
            if hasattr(self, 'binance_zero_price_timer') and self.binance_zero_price_timer:
                try:
                    if self.binance_zero_price_timer.is_alive():
                        self.binance_zero_price_timer.cancel()
                except:
                    pass
                self.binance_zero_price_timer = None
            self.logger.info("✅ 清理了币安零点价格线程定时器状态")
            
            # 15. 恢复记录利润定时器（安排每日0:30记录）
            if hasattr(self, 'record_and_show_cash_timer') and self.record_and_show_cash_timer:
                self.logger.info("✅ 记录利润定时器已存在，保持不变")
            else:
                self.schedule_record_cash_daily()
                self.logger.info("✅ 恢复记录利润定时器（每日0:30）")
            
            self.logger.info("✅ 所有监控状态恢复完成")
            
        except Exception as e:
            self.logger.error(f"恢复所有监控状态失败: {e}")

    def check_prices(self):
        """检查价格变化 - 增强版本，支持多种获取方式和更好的错误处理"""
        # 直接检查driver是否存在，不存在就重启
        if not self.driver and not self.is_restarting:
            self.logger.warning("浏览器未初始化，尝试重启...")
            if not self.restart_browser(force_restart=True):
                self.logger.error("浏览器重启失败，跳过本次检查")
                return
        if self.driver is None:
            return
            
        try:
            # 验证浏览器连接是否正常
            self.driver.execute_script("return navigator.userAgent")
            
            # 高度优化的JavaScript获取价格 - 最小化DOM查询
            prices = self.driver.execute_script("""
                function getPricesOptimized() {
                    const prices = {up: null, down: null};
                    const priceRegex = /(\\d+(?:\\.\\d+)?)¢/;
                    
                    // 使用更精确的选择器，减少遍历范围
                    const selectors = [
                        'button[class*="btn"]',
                        'button[class*="button"]', 
                        'div[class*="price"]',
                        'span[class*="price"]',
                        'button'
                    ];
                    
                    for (let selector of selectors) {
                        try {
                            const elements = document.querySelectorAll(selector);
                            for (let el of elements) {
                                const text = el.textContent || el.innerText;
                                if (!text || !text.includes('¢')) continue;
                                
                                if (text.includes('Up') && prices.up === null) {
                                    const match = text.match(priceRegex);
                                    if (match) prices.up = parseFloat(match[1]);
                                }
                                if (text.includes('Down') && prices.down === null) {
                                    const match = text.match(priceRegex);
                                    if (match) prices.down = parseFloat(match[1]);
                                }
                                
                                // 如果两个价格都找到了，立即返回
                                if (prices.up !== null && prices.down !== null) return prices;
                            }
                            
                            // 如果当前选择器找到了价格，不再尝试其他选择器
                            if (prices.up !== null || prices.down !== null) break;
                        } catch (e) {
                            continue; // 忽略选择器错误，继续下一个
                        }
                    }
                    
                    return prices;
                }
                return getPricesOptimized();
            """)

            # 验证获取到的数据
            if prices['up'] is not None and prices['down'] is not None:
                # 获取价格
                up_price_val = float(prices['up'])
                down_price_val = float(prices['down'])
                
                # 数据合理性检查
                if 0 <= up_price_val <= 100 and 0 <= down_price_val <= 100:
                    # 更新价格显示和数据
                    self._update_label_and_sync(self.yes_price_label, f"Up: {up_price_val:.1f}", 'prices', 'polymarket_up')
                    self._update_label_and_sync(self.no_price_label, f"Down: {down_price_val:.1f}", 'prices', 'polymarket_down')
                    
                    # 同时更新web_data以保持兼容性
                    self.set_web_value('yes_price_label', f"Up: {up_price_val:.1f}")
                    self.set_web_value('no_price_label', f"Down: {down_price_val:.1f}")
                    
                    # 重置失败计数器（价格获取成功）
                    if hasattr(self, 'price_check_fail_count'):
                        self.price_check_fail_count = 0
                    if hasattr(self, 'element_fail_count'):
                        self.element_fail_count = 0
                    
                    # 执行所有交易检查函数（仅在没有交易进行时）
                    if not self.trading:
                        self.First_trade(up_price_val, down_price_val)
                        self.Second_trade(up_price_val, down_price_val)
                        self.Third_trade(up_price_val, down_price_val)
                        self.Forth_trade(up_price_val, down_price_val)
                        
                else:
                    self.logger.warning(f"价格数据异常: Up={up_price_val}, Down={down_price_val}")
                    self.yes_price_label.config(text="Up: Invalid")
                    self.no_price_label.config(text="Down: Invalid")
                    
            else:
                # 显示具体的缺失信息
                missing_info = []
                if prices['up'] is None:
                    missing_info.append("Up价格")
                if prices['down'] is None:
                    missing_info.append("Down价格")
                    
                self.logger.warning(f"数据获取不完整，缺失: {', '.join(missing_info)}")
                self.yes_price_label.config(text="Up: N/A")
                self.no_price_label.config(text="Down: N/A")
                # 智能刷新：仅在连续失败时才刷新
                if not hasattr(self, 'price_check_fail_count'):
                    self.price_check_fail_count = 0
                self.price_check_fail_count += 1
                
                if self.price_check_fail_count >= 3:
                    try:
                        self.logger.info("连续3次价格获取失败，执行页面刷新")
                        self.driver.refresh()
                        time.sleep(2)
                        self.price_check_fail_count = 0
                    except Exception:
                        pass

        except (StaleElementReferenceException, NoSuchElementException) as e:
            self.logger.warning(f"元素引用失效: {str(e)}")
            self.yes_price_label.config(text="Up: Retry")
            self.no_price_label.config(text="Down: Retry")
            # 智能刷新：仅在元素失效时才刷新
            if not hasattr(self, 'element_fail_count'):
                self.element_fail_count = 0
            self.element_fail_count += 1
            
            if self.element_fail_count >= 2:
                try:
                    self.logger.info("连续2次元素失效，执行页面刷新")
                    self.driver.refresh()
                    time.sleep(2)
                    self.element_fail_count = 0
                except Exception:
                    pass
        except AttributeError as e:
            self.logger.error(f"浏览器连接异常: {str(e)}")
            if not self.is_restarting:
                self.restart_browser()
            return
        except Exception as e:
            self.logger.error(f"价格检查异常: {str(e)}")
            self.yes_price_label.config(text="Up: Fail")
            self.no_price_label.config(text="Down: Fail")
            
    def check_balance(self):
        """获取Portfolio和Cash值"""  
        try:
            # 验证浏览器连接是否正常
            self.driver.execute_script("return navigator.userAgent")
            # 等待页面完全加载
            WebDriverWait(self.driver, 3).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )
        except Exception as e:
            self.logger.error(f"浏览器连接异常: {str(e)}")
            if not self.is_restarting:
                self.restart_browser()
            return
        
        try:
            # 取Portfolio值和Cash值
            self.cash_value = None
            self.portfolio_value = None

            # 获取Portfolio和Cash值
            try:
                portfolio_element = self.driver.find_element(By.XPATH, XPathConfig.PORTFOLIO_VALUE[0])
            except (NoSuchElementException, StaleElementReferenceException):
                portfolio_element = self._find_element_with_retry(XPathConfig.PORTFOLIO_VALUE, timeout=2, silent=True)
                
            
            try:
                cash_element = self.driver.find_element(By.XPATH, XPathConfig.CASH_VALUE[0])
            except (NoSuchElementException, StaleElementReferenceException):
                cash_element = self._find_element_with_retry(XPathConfig.CASH_VALUE, timeout=2, silent=True)
            
            if portfolio_element and cash_element:
                self.cash_value = cash_element.text
                self.portfolio_value = portfolio_element.text
            else:
                self.cash_value = "获取失败"
                self.portfolio_value = "获取失败"
        
            # 更新Portfolio和Cash显示
            self.portfolio_label.config(text=f"Portfolio: {self.portfolio_value}")
            self.cash_label.config(text=f"Cash: {self.cash_value}")
            
            # 同步数据到StatusDataManager
            self.status_data.update('account', 'portfolio_value', self.portfolio_value)
            self.status_data.update('account', 'available_cash', self.cash_value)

        except Exception as e:
            self.portfolio_label.config(text="Portfolio: Fail")
            self.cash_label.config(text="Cash: Fail")
    
    def schedule_update_amount(self, retry_count=0):
        """设置金额,带重试机制"""
        try:
            if retry_count < 15:  # 最多重试15次
                # 1秒后执行
                self.root.after(1000, lambda: self.try_update_amount(retry_count))
            else:
                self.logger.warning("更新金额操作达到最大重试次数")
        except Exception as e:
            self.logger.error(f"安排更新金额操作失败: {str(e)}")

    def try_update_amount(self, current_retry=0):
        """尝试设置金额"""
        try:
            self.set_yes_no_cash()
            
        except Exception as e:
            self.logger.error(f"更新金额操作失败 (尝试 {current_retry + 1}/15): {str(e)}")
            # 如果失败，安排下一次重试
            self.schedule_update_amount(current_retry + 1)

    def set_yes_no_cash(self):
        """设置 Yes/No 各级金额"""
        try:
            #设置重试参数
            max_retry = 15
            retry_count = 0
            cash_value = 0

            while retry_count < max_retry:
                try:
                    # 获取 Cash 值
                    cash_value = float(self.zero_time_cash_value)
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retry:
                        time.sleep(2)
                    else:
                        raise ValueError("获取Cash值失败")
            if cash_value is None:
                raise ValueError("获取Cash值失败")
            
            # 获取金额设置中的百分比值
            initial_percent = float(self.initial_amount_entry.get()) / 100  # 初始金额百分比
            first_rebound_percent = float(self.first_rebound_entry.get()) / 100  # 反水一次百分比
            n_rebound_percent = float(self.n_rebound_entry.get()) / 100  # 反水N次百分比

            # 设置 UP1 和 DOWN1金额
            base_amount = cash_value * initial_percent
            self.yes1_entry = self.yes_frame.grid_slaves(row=1, column=1)[0]
            self.yes1_amount_entry.delete(0, tk.END)
            self.yes1_amount_entry.insert(0, f"{base_amount:.2f}")
            self.no1_entry = self.no_frame.grid_slaves(row=1, column=1)[0]
            self.no1_amount_entry.delete(0, tk.END)
            self.no1_amount_entry.insert(0, f"{base_amount:.2f}")
            
            # 计算并设置 UP2/DOWN2金额
            self.yes2_amount = base_amount * first_rebound_percent
            self.yes2_entry = self.yes_frame.grid_slaves(row=3, column=1)[0]
            self.yes2_entry.delete(0, tk.END)
            self.yes2_entry.insert(0, f"{self.yes2_amount:.2f}")
            self.no2_entry = self.no_frame.grid_slaves(row=3, column=1)[0]
            self.no2_entry.delete(0, tk.END)
            self.no2_entry.insert(0, f"{self.yes2_amount:.2f}")
            
            # 计算并设置 UP3/DOWN3 金额
            self.yes3_amount = self.yes2_amount * n_rebound_percent
            self.yes3_entry = self.yes_frame.grid_slaves(row=5, column=1)[0]
            self.yes3_entry.delete(0, tk.END)
            self.yes3_entry.insert(0, f"{self.yes3_amount:.2f}")
            self.no3_entry = self.no_frame.grid_slaves(row=5, column=1)[0]
            self.no3_entry.delete(0, tk.END)
            self.no3_entry.insert(0, f"{self.yes3_amount:.2f}")

            # 计算并设置 UP4/DOWN4金额
            self.yes4_amount = self.yes3_amount * n_rebound_percent
            self.yes4_entry = self.yes_frame.grid_slaves(row=7, column=1)[0]
            self.yes4_entry.delete(0, tk.END)
            self.yes4_entry.insert(0, f"{self.yes4_amount:.2f}")
            self.no4_entry = self.no_frame.grid_slaves(row=7, column=1)[0]
            self.no4_entry.delete(0, tk.END)
            self.no4_entry.insert(0, f"{self.yes4_amount:.2f}")

            # 同步金额到StatusDataManager
            self.status_data.update('positions', 'up_positions', [
                {'price': '0', 'amount': f"{base_amount:.2f}"},
                {'price': '0', 'amount': f"{self.yes2_amount:.2f}"},
                {'price': '0', 'amount': f"{self.yes3_amount:.2f}"},
                {'price': '0', 'amount': f"{self.yes4_amount:.2f}"}
            ])
            self.status_data.update('positions', 'down_positions', [
                {'price': '0', 'amount': f"{base_amount:.2f}"},
                {'price': '0', 'amount': f"{self.yes2_amount:.2f}"},
                {'price': '0', 'amount': f"{self.yes3_amount:.2f}"},
                {'price': '0', 'amount': f"{self.yes4_amount:.2f}"}
            ])
            
            # 获取当前CASH并显示,此CASH再次点击start按钮时会更新
            self.logger.info("\033[34m✅ YES/NO 金额设置完成\033[0m")
            
        except Exception as e:
            self.logger.error(f"设置金额失败: {str(e)}")
            
            self.schedule_retry_update_amount()

    def schedule_retry_update_amount(self):
        """安排重试更新金额"""
        if hasattr(self, 'retry_update_amount_timer'):
            self.root.after_cancel(self.retry_update_amount_timer)
        self.retry_update_amount_timer = self.root.after(3000, self.set_yes_no_cash)  # 3秒后重试
    
    def start_url_monitoring(self):
        """启动URL监控"""
        with self.url_monitoring_lock:
            if getattr(self, 'is_url_monitoring', False):
                self.logger.debug("URL监控已在运行中")
                return

            self.url_monitoring_running = True
            self.logger.info("\033[34m✅ 启动URL监控\033[0m")

            def check_url():
                if self.running and self.driver:
                    try:
                        # 验证浏览器连接是否正常
                        self.driver.execute_script("return navigator.userAgent")
                        current_page_url = self.driver.current_url # 获取当前页面URL
                        target_url = self.url_entry.get().strip() # 获取输入框中的URL,这是最原始的URL

                        # 去除URL中的查询参数(?后面的部分)
                        def clean_url(url):
                            return url.split('?')[0].rstrip('/')
                            
                        clean_current = clean_url(current_page_url)
                        clean_target = clean_url(target_url)
                        
                        # 如果URL基础部分不匹配，重新导航
                        if clean_current != clean_target:
                            self.logger.info(f"❌ URL不匹配,重新导航到: {target_url}")
                            self.driver.get(target_url)

                    except Exception as e:
                        self.logger.error(f"URL监控出错: {str(e)}")

                        # 重新导航到目标URL
                        if self.driver:
                            try:
                                self.driver.get(target_url)
                                self.logger.info(f"\033[34m✅ URL监控已自动修复: {target_url}\033[0m")
                            except Exception:
                                self.restart_browser(force_restart=True)
                        else:
                            self.restart_browser(force_restart=True)
                    # 继续监控
                    if self.running:
                        self.url_check_timer = self.root.after(10000, check_url)  # 每10秒检查一次
            
            # 开始第一次检查
            self.url_check_timer = self.root.after(1000, check_url)

    def stop_url_monitoring(self):
        """停止URL监控"""
        
        with self.url_monitoring_lock:
            # 检查是否有正在运行的URL监控
            if not hasattr(self, 'url_monitoring_running') or not self.url_monitoring_running:
                self.logger.debug("URL监控未在运行中,无需停止")
                return
            
            # 取消定时器
            if hasattr(self, 'url_check_timer') and self.url_check_timer:
                try:
                    self.root.after_cancel(self.url_check_timer)
                    self.url_check_timer = None
                    
                except Exception as e:
                    self.logger.error(f"取消URL监控定时器时出错: {str(e)}")
            
            # 重置监控状态
            self.url_monitoring_running = False
            self.logger.info("\033[31m❌ URL监控已停止\033[0m")

    def start_login_monitoring(self):
        """监控登录状态"""
        # 检查是否已经登录
        try:
            # 查找登录按钮 - 使用更安全的方式
            login_button = None
            try:
                login_button = self.driver.find_element(By.XPATH, XPathConfig.LOGIN_BUTTON[0])
            except (NoSuchElementException, StaleElementReferenceException):
                try:
                    login_button = self._find_element_with_retry(XPathConfig.LOGIN_BUTTON, timeout=2, silent=True)
                except Exception:
                    login_button = None
                
            if login_button:
                self.logger.info("✅ 已发现登录按钮,尝试登录")
                self.stop_url_monitoring()
                self.stop_refresh_page()

                login_button.click()
                time.sleep(1)
                
                # 查找Google登录按钮
                try:
                    google_login_button = self.driver.find_element(By.XPATH, XPathConfig.LOGIN_WITH_GOOGLE_BUTTON[0])
                except (NoSuchElementException, StaleElementReferenceException):
                    google_login_button = self._find_element_with_retry(XPathConfig.LOGIN_WITH_GOOGLE_BUTTON, timeout=2, silent=True)
                    
                if google_login_button:
                    try:
                        google_login_button.click()
                        self.logger.info("✅ 已点击Google登录按钮")
                    except Exception as e:
                        self.logger.info(f"❌ 点击Google登录按钮失败,使用坐标法点击")
                        self.use_x_y_click_google_login_button()
                    
                    # 不再固定等待15秒，而是循环检测CASH值
                    max_attempts = 20 # 最多检测20次
                    check_interval = 1 # 每1秒检测一次
                    cash_value = None
                    
                    for attempt in range(max_attempts):
                        try:
                            # 获取CASH值
                            try:
                                cash_element = self.driver.find_element(By.XPATH, XPathConfig.CASH_VALUE[0])
                            except (NoSuchElementException, StaleElementReferenceException):
                                cash_element = self._find_element_with_retry(XPathConfig.CASH_VALUE, timeout=2, silent=True)
                                
                            if cash_element:
                                cash_value = cash_element.text
                                self.logger.info(f"✅ 已找到CASH值: {cash_value}, 登录成功.")
                                self.driver.get(self.url_entry.get().strip())
                                time.sleep(2)
                                break
                        except NoSuchElementException:
                            self.logger.info(f"⏳ 第{attempt+1}次尝试: 等待登录完成...")                       
                        # 等待指定时间后再次检测
                        time.sleep(check_interval)

                    self.url_check_timer = self.root.after(10000, self.start_url_monitoring)
                    self.refresh_page_timer = self.root.after(360000, self.refresh_page)  # 优化为6分钟
                    self.logger.info("✅ 已重新启用URL监控和页面刷新")

        except NoSuchElementException as e:
            # 未找到登录按钮，可能已经登录
            self.logger.debug(f"未找到登录按钮，可能已经登录: {str(e)}")
        except Exception as e:
            # 处理其他所有异常
            self.logger.error(f"登录监控过程中发生错误: {str(e)}")
        finally:
            # 每15秒检查一次登录状态
            try:
                self.login_check_timer = self.root.after(15000, self.start_login_monitoring)
            except Exception as e:
                self.logger.error(f"设置登录检查定时器失败: {str(e)}")

    def use_x_y_click_google_login_button(self):
        """点击Google登录按钮"""
        self.logger.info("使用坐标法开始执行点击Google登录按钮")
        try:
            screen_width, screen_height = pyautogui.size()
            
            target_x = 0
            target_y = 0

            if platform.system() == "Linux": # 分辨率 2560X1600
                # Linux 系统下的特定坐标
                target_x = screen_width - 781
                target_y = 589
                
            else:
                # 其他操作系统的默认坐标分辨率 1920x1080
                target_x = screen_width - 460
                target_y = 548
                
            # 移动鼠标到目标位置并点击
            pyautogui.moveTo(target_x, target_y, duration=0.2) # 可选，平滑移动
            pyautogui.click(target_x, target_y)
            
            self.logger.info("✅ \033[34m使用坐标法点击ACCEPT成功\033[0m")
            self.driver.refresh()

        except Exception as e:
            self.logger.error(f"执行 click_accept 点击操作失败: {str(e)}")

    def click_accept(self):
        """使用坐标法点击ACCEPT按钮"""
        self.logger.info("✅ \033[34m使用坐标法执行点击ACCEPT按钮\033[0m")
        try:
            screen_width, screen_height = pyautogui.size()
            
            target_x = 0
            target_y = 0

            if platform.system() == "Linux": # 分辨率 2560X1600
                # Linux 系统下的特定坐标
                target_x = screen_width - 630
                target_y = 969
                
            else:
                # 其他操作系统的默认坐标分辨率 1920x1080
                target_x = screen_width - 520
                target_y = 724
                
            # 移动鼠标到目标位置并点击
            pyautogui.moveTo(target_x, target_y, duration=0.2) # 可选，平滑移动
            pyautogui.click(target_x, target_y)
            
            self.logger.info("✅ \033[34m使用坐标法点击ACCEPT成功\033[0m")
            self.driver.refresh()

        except Exception as e:
            self.logger.error(f"执行 click_accept 点击操作失败: {str(e)}")

    def refresh_page(self):
        """智能定时刷新页面 - 优化刷新频率和条件"""
        # 增加刷新间隔到8-15分钟，减少不必要的刷新
        random_minutes = random.uniform(8, 15)
        self.refresh_interval = int(random_minutes * 60000)  # 转换为毫秒
        
        # 初始化刷新失败计数器（如果不存在）
        if not hasattr(self, 'refresh_fail_count'):
            self.refresh_fail_count = 0

        with self.refresh_page_lock:
            self.refresh_page_running = True
            try:
                # 先取消可能存在的旧定时器
                if hasattr(self, 'refresh_page_timer') and self.refresh_page_timer:
                    try:
                        self.root.after_cancel(self.refresh_page_timer)
                        self.refresh_page_timer = None
                    except Exception as e:
                        self.logger.error(f"取消旧定时器失败: {str(e)}")

                # 智能刷新条件判断
                should_refresh = self._should_refresh_page()
                
                if self.running and self.driver and not self.trading and should_refresh:
                    try:
                        # 验证浏览器连接是否正常
                        self.driver.execute_script("return navigator.userAgent")
                        refresh_time = self.refresh_interval / 60000 # 转换为分钟,用于输入日志
                        
                        # 清空元素缓存，因为页面即将刷新
                        self._clear_element_cache()
                        self.driver.refresh()
                        
                        # 重置失败计数器
                        self.refresh_fail_count = 0
                        #self.logger.info(f"✅ 页面已刷新，{round(refresh_time, 2)}分钟后再次检查")
                        
                    except Exception as e:
                        self.refresh_fail_count += 1
                        self.logger.warning(f"浏览器连接异常，无法刷新页面 (失败次数: {self.refresh_fail_count})")
                        
                        # 连续失败3次后尝试重启浏览器
                        if self.refresh_fail_count >= 3 and not self.is_restarting:
                            self.logger.warning("连续刷新失败3次，尝试重启浏览器")
                            self.refresh_fail_count = 0
                            self.restart_browser()
                else:
                    if not should_refresh:
                        self.logger.debug("跳过刷新：页面状态良好")
                    else:
                        self.logger.debug(f"跳过刷新：running={self.running}, driver={bool(self.driver)}, trading={self.trading}")
                    
            except Exception as e:
                self.refresh_fail_count += 1
                self.logger.warning(f"页面刷新失败: {str(e)} (失败次数: {self.refresh_fail_count})")
                
            finally:
                # 安排下一次检查（确保循环持续）
                self.refresh_page_timer = self.root.after(self.refresh_interval, self.refresh_page)

    def _should_refresh_page(self):
        """智能判断是否需要刷新页面"""
        try:
            # 检查页面是否响应正常
            if not self.driver:
                return False
                
            # 检查页面加载状态
            ready_state = self.driver.execute_script("return document.readyState")
            if ready_state != "complete":
                return True  # 页面未完全加载，需要刷新
                
            # 检查是否存在关键元素（价格按钮）
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                price_buttons = [btn for btn in buttons if '¢' in btn.text and ('Up' in btn.text or 'Down' in btn.text)]
                if len(price_buttons) < 2:
                    return True  # 关键元素缺失，需要刷新
            except Exception:
                return True  # 元素查找失败，需要刷新
                
            # 检查页面是否有错误信息
            try:
                error_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Error') or contains(text(), '错误') or contains(text(), 'Failed')]") 
                if error_elements:
                    return True  # 页面有错误，需要刷新
            except Exception:
                pass
                
            # 检查网络连接状态
            try:
                online_status = self.driver.execute_script("return navigator.onLine")
                if not online_status:
                    return True  # 网络断开，需要刷新
            except Exception:
                pass
                
            return False  # 页面状态良好，无需刷新
            
        except Exception as e:
            self.logger.debug(f"页面状态检查失败: {str(e)}")
            return True  # 检查失败，保守起见进行刷新
    
    def stop_refresh_page(self):
        """停止页面刷新"""
        with self.refresh_page_lock:
            
            if hasattr(self, 'refresh_page_timer') and self.refresh_page_timer:
                try:
                    self.root.after_cancel(self.refresh_page_timer)
                    self.refresh_page_timer = None
                    self.logger.info("\033[31m❌ 刷新定时器已停止\033[0m")
                except Exception as e:
                    self.logger.error("取消页面刷新定时器时出错")
            # 重置监控状态
            self.refresh_page_running = False
            self.logger.info("\033[31m❌ 刷新状态已停止\033[0m")
    
    def change_buy_and_trade_count(self):
        """改变交易次数"""
        self.buy_count += 1
        self.trade_count -= 1
        self.trade_count_label.config(text=str(self.trade_count))
        
        # 同步剩余交易次数到StatusDataManager
        self.status_data.update('trading', 'remaining_trades', str(self.trade_count))

    def First_trade(self, up_price, down_price):
        """第一次交易价格设置为 0.54 买入,最多重试3次,失败发邮件"""
        try:
            if (up_price is not None and up_price > 10) and (down_price is not None and down_price > 10):
                yes1_price = float(self.yes1_price_entry.get())
                no1_price = float(self.no1_price_entry.get())
                self.trading = True

                # 检查Up1价格匹配
                if 0 <= round((up_price - yes1_price), 2) <= self.price_premium and up_price > 20:
                    for retry in range(3):
                        self.logger.info(f"✅ \033[32mUp 1: {up_price}¢ 价格匹配,执行自动买入,第{retry+1}次尝试\033[0m")
                        # 如果买入次数大于 18 次,那么先卖出,后买入
                        if self.buy_count > 14:
                            self.only_sell_down()

                        # 买入 UP1
                        # 传 Tkinter 的 AmountEntry 对象，比如 self.yes1_amount_entry
                        self.send_amount_and_click_buy_confirm(self.yes1_amount_entry)

                        time.sleep(2)
                        if self.Verify_buy_up():
                            self.buy_yes1_amount = float(self.yes1_amount_entry.get())
                            
                            # 重置Up1和Down1价格为0
                            self.yes1_price_entry.configure(foreground='black')
                            self.yes1_price_entry.delete(0, tk.END)
                            self.yes1_price_entry.insert(0, "0")
                            self.no1_price_entry.configure(foreground='black')
                            self.no1_price_entry.delete(0, tk.END)
                            self.no1_price_entry.insert(0, "0")
                            
                            # 同步UP1和DOWN1价格到StatusDataManager
                            self.status_data.update('positions', 'up_positions', [
                                {'price': '0', 'amount': self.status_data.data['positions']['up_positions'][0]['amount']},
                                self.status_data.data['positions']['up_positions'][1],
                                self.status_data.data['positions']['up_positions'][2],
                                self.status_data.data['positions']['up_positions'][3]
                            ])
                            self.status_data.update('positions', 'down_positions', [
                                {'price': '0', 'amount': self.status_data.data['positions']['down_positions'][0]['amount']},
                                self.status_data.data['positions']['down_positions'][1],
                                self.status_data.data['positions']['down_positions'][2],
                                self.status_data.data['positions']['down_positions'][3]
                            ])
                            #self.logger.info("\033[34m✅ Up1和Down1价格已重置为0\033[0m")

                            # 第一次买 UP1,不用卖出 DOWN
                            if self.trade_count < 22:
                                # 因为不会双持仓,所以不用判断卖 UP 还是卖 DOWN,直接卖点击 SELL 卖出仓位
                                self.only_sell_down()

                            # 设置No2价格为默认值
                            self.no2_price_entry = self.no_frame.grid_slaves(row=2, column=1)[0]
                            self.no2_price_entry.delete(0, tk.END)
                            self.no2_price_entry.insert(0, str(self.default_target_price))
                            self.no2_price_entry.configure(foreground='red')
                            
                            # 同步DOWN2价格到StatusDataManager
                            self.status_data.update('positions', 'down_positions', [
                                self.status_data.data['positions']['down_positions'][0],
                                {'price': str(self.default_target_price), 'amount': self.status_data.data['positions']['down_positions'][1]['amount']},
                                self.status_data.data['positions']['down_positions'][2],
                                self.status_data.data['positions']['down_positions'][3]
                            ])
                            
                            self.logger.info(f"\033[34m✅ No2价格已重置为默认值{self.default_target_price}\033[0m")

                            # 自动改变交易次数
                            self.change_buy_and_trade_count()

                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Up1",
                                price=self.price,
                                amount=self.amount,
                                shares=self.shares,
                                trade_count=self.buy_count,
                                cash_value=self.cash_value,
                                portfolio_value=self.portfolio_value
                            )
                            self.logger.info(f"\033[34m✅ 第{self.buy_count}次 UP1成功\033[0m")

                            break
                        else:
                            self.logger.warning(f"❌ \033[31mBuy Up1 交易失败,第{retry+1}次,等待1秒后重试\033[0m")
                            time.sleep(1)
                    else:
                        # 3次失败后发邮件
                        self.send_trade_email(
                            trade_type="Buy Up1失败",
                            price=up_price,
                            amount=0,
                            shares=0,
                            trade_count=self.buy_count,
                            cash_value=self.cash_value,
                            portfolio_value=self.portfolio_value
                        )

                elif 0 <= round((down_price - no1_price), 2) <= self.price_premium and down_price > 20:
                    for retry in range(3):
                        self.logger.info(f"✅ \033[31mDown 1: {down_price}¢ 价格匹配,执行自动买入,第{retry+1}次尝试\033[0m")
                        # 如果买入次数大于 18 次,那么先卖出,后买入
                        if self.buy_count > 14:
                            self.only_sell_up()

                        # 执行交易操作
                        self.buy_no_button.invoke() 

                        # 传 Tkinter 的 AmountEntry 对象，比如 self.no1_amount_entry
                        self.send_amount_and_click_buy_confirm(self.no1_amount_entry)
                        
                        self.buy_yes_button.invoke()

                        time.sleep(2)
                        if self.Verify_buy_down():
                            self.buy_no1_amount = float(self.no1_amount_entry.get())

                            # 重置Up1和Down1价格为0
                            self.yes1_price_entry.delete(0, tk.END)
                            self.yes1_price_entry.insert(0, "0")
                            self.yes1_price_entry.configure(foreground='black')
                            self.no1_price_entry.delete(0, tk.END)
                            self.no1_price_entry.insert(0, "0")
                            self.no1_price_entry.configure(foreground='black')
                            
                            # 同步UP1和DOWN1价格到StatusDataManager
                            self.status_data.update('positions', 'up_positions', [
                                {'price': '0', 'amount': self.status_data.data['positions']['up_positions'][0]['amount']},
                                self.status_data.data['positions']['up_positions'][1],
                                self.status_data.data['positions']['up_positions'][2],
                                self.status_data.data['positions']['up_positions'][3]
                            ])
                            self.status_data.update('positions', 'down_positions', [
                                {'price': '0', 'amount': self.status_data.data['positions']['down_positions'][0]['amount']},
                                self.status_data.data['positions']['down_positions'][1],
                                self.status_data.data['positions']['down_positions'][2],
                                self.status_data.data['positions']['down_positions'][3]
                            ])
                            #self.logger.info("\033[34m✅ Up1和Down1价格已重置为0\033[0m")

                            # 第一次买 UP1,不用卖出 DOWN
                            if self.trade_count < 22:
                                # 因为不会双持仓,所以不用判断卖 UP 还是卖 DOWN,直接卖点击 SELL 卖出仓位
                                self.only_sell_up()

                            # 设置Yes2价格为默认值
                            self.yes2_price_entry = self.yes_frame.grid_slaves(row=2, column=1)[0]
                            self.yes2_price_entry.delete(0, tk.END)
                            self.yes2_price_entry.insert(0, str(self.default_target_price))
                            self.yes2_price_entry.configure(foreground='red')
                            
                            # 同步UP2价格到StatusDataManager
                            self.status_data.update('positions', 'up_positions', [
                                self.status_data.data['positions']['up_positions'][0],
                                {'price': str(self.default_target_price), 'amount': self.status_data.data['positions']['up_positions'][1]['amount']},
                                self.status_data.data['positions']['up_positions'][2],
                                self.status_data.data['positions']['up_positions'][3]
                            ])
                            
                            self.logger.info(f"\033[34m✅ Yes2价格已重置为{self.default_target_price}\033[0m")

                            # 自动改变交易次数
                            self.change_buy_and_trade_count()

                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Down1",
                                price=self.price,
                                amount=self.amount,
                                shares=self.shares,
                                trade_count=self.buy_count,
                                cash_value=self.cash_value,
                                portfolio_value=self.portfolio_value
                            )
                            self.logger.info(f"\033[34m✅ 第{self.buy_count}次 BUY DOWN1成功\033[0m")

                            break
                        else:
                            self.logger.warning(f"❌ \033[31mBuy Down1 交易失败,第{retry+1}次,等待1秒后重试\033[0m")
                            time.sleep(1)
                    else:
                        self.send_trade_email(
                            trade_type="Buy Down1失败",
                            price=down_price,
                            amount=0,
                            
                            trade_count=self.buy_count,
                            cash_value=self.cash_value,
                            portfolio_value=self.portfolio_value
                        )
        except ValueError as e:
            self.logger.error(f"价格转换错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"First_trade执行失败: {str(e)}")
        finally:
            self.trading = False
            
    def Second_trade(self, up_price, down_price):
        """处理Yes2/No2的自动交易"""
        try:
            if (up_price is not None and up_price > 10) and (down_price is not None and down_price > 10):
                # 获Yes2和No2的价格输入框
                yes2_price = float(self.yes2_price_entry.get())
                no2_price = float(self.no2_price_entry.get())
                self.trading = True

                # 检查Yes2价格匹配
                if 0 <= round((up_price - yes2_price), 2) <= self.price_premium and up_price > 20:
                    for retry in range(3):
                        self.logger.info(f"✅  \033[32mUp 2: {up_price}¢ 价格匹配,执行自动买入,第{retry+1}次尝试\033[0m")
                        # 如果买入次数大于 18 次,那么先卖出,后买入
                        if self.buy_count > 14:
                            self.only_sell_down()

                        # 传 Tkinter 的 AmountEntry 对象，比如 self.yes2_amount_entry
                        self.send_amount_and_click_buy_confirm(self.yes2_amount_entry)
                        
                        time.sleep(2)
                        if self.Verify_buy_up():
                            self.buy_yes2_amount = float(self.yes2_amount_entry.get())
                            
                            # 重置Yes2和No2价格为0
                            self.yes2_price_entry.delete(0, tk.END)
                            self.yes2_price_entry.insert(0, "0")
                            self.yes2_price_entry.configure(foreground='black')
                            self.no2_price_entry.delete(0, tk.END)
                            self.no2_price_entry.insert(0, "0")
                            self.no2_price_entry.configure(foreground='black')
                            
                            # 同步UP2和DOWN2价格到StatusDataManager
                            self.status_data.update('positions', 'up_positions', [
                                self.status_data.data['positions']['up_positions'][0],
                                {'price': '0', 'amount': self.status_data.data['positions']['up_positions'][1]['amount']},
                                self.status_data.data['positions']['up_positions'][2],
                                self.status_data.data['positions']['up_positions'][3]
                            ])
                            self.status_data.update('positions', 'down_positions', [
                                self.status_data.data['positions']['down_positions'][0],
                                {'price': '0', 'amount': self.status_data.data['positions']['down_positions'][1]['amount']},
                                self.status_data.data['positions']['down_positions'][2],
                                self.status_data.data['positions']['down_positions'][3]
                            ])
                            #self.logger.info(f"\033[34m✅ Yes2和No2价格已重置为0\033[0m")

                            # 卖出DOWN
                            self.only_sell_down()

                            # 设置No3价格为默认值
                            self.no3_price_entry = self.no_frame.grid_slaves(row=4, column=1)[0]
                            self.no3_price_entry.delete(0, tk.END)
                            self.no3_price_entry.insert(0, str(self.default_target_price))
                            self.no3_price_entry.configure(foreground='red')
                            
                            # 同步DOWN3价格到StatusDataManager
                            self.status_data.update('positions', 'down_positions', [
                                self.status_data.data['positions']['down_positions'][0],
                                self.status_data.data['positions']['down_positions'][1],
                                {'price': str(self.default_target_price), 'amount': self.status_data.data['positions']['down_positions'][2]['amount']},
                                self.status_data.data['positions']['down_positions'][3]
                            ])
                            #self.logger.info(f"✅ No3价格已重置为{self.default_target_price}")

                            # 自动改变交易次数
                            self.change_buy_and_trade_count()
                            
                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Up2",
                                price=self.price,
                                amount=self.amount,
                                shares=self.shares,
                                trade_count=self.buy_count,
                                cash_value=self.cash_value,
                                portfolio_value=self.portfolio_value
                            )
                                 
                            break
                        else:
                            self.logger.warning(f"❌ \033[31mBuy Up2 交易失败,第{retry+1}次,等待1秒后重试\033[0m")
                            time.sleep(1)
                    else:
                        self.send_trade_email(
                            trade_type="Buy Up2失败",
                            price=up_price,
                            amount=0,
                            shares=0,
                            trade_count=self.buy_count,
                            cash_value=self.cash_value,
                            portfolio_value=self.portfolio_value
                        )
                # 检查No2价格匹配
                elif 0 <= round((down_price - no2_price), 2) <= self.price_premium and down_price > 20:
                    for retry in range(3):
                        self.logger.info(f"✅ \033[31mDown 2: {down_price}¢ 价格匹配,执行自动买入,第{retry+1}次尝试\033[0m")
                        # 如果买入次数大于 18 次,那么先卖出,后买入
                        if self.buy_count > 14:
                            self.only_sell_up()

                        # 执行交易操作
                        self.buy_no_button.invoke()

                        # 传 Tkinter 的 AmountEntry 对象，比如 self.no2_amount_entry
                        self.send_amount_and_click_buy_confirm(self.no2_amount_entry)
                        
                        time.sleep(2)
                        if self.Verify_buy_down():
                            self.buy_no2_amount = float(self.no2_amount_entry.get())
                            
                            # 重置Yes2和No2价格为0
                            self.yes2_price_entry.delete(0, tk.END)
                            self.yes2_price_entry.insert(0, "0")
                            self.yes2_price_entry.configure(foreground='black')
                            self.no2_price_entry.delete(0, tk.END)
                            self.no2_price_entry.insert(0, "0")
                            self.no2_price_entry.configure(foreground='black')
                            
                            # 同步UP2和DOWN2价格到StatusDataManager
                            self.status_data.update('positions', 'up_positions', [
                                self.status_data.data['positions']['up_positions'][0],
                                {'price': '0', 'amount': self.status_data.data['positions']['up_positions'][1]['amount']},
                                self.status_data.data['positions']['up_positions'][2],
                                self.status_data.data['positions']['up_positions'][3]
                            ])
                            self.status_data.update('positions', 'down_positions', [
                                self.status_data.data['positions']['down_positions'][0],
                                {'price': '0', 'amount': self.status_data.data['positions']['down_positions'][1]['amount']},
                                self.status_data.data['positions']['down_positions'][2],
                                self.status_data.data['positions']['down_positions'][3]
                            ])
                            #self.logger.info(f"\033[34m✅ Yes2和No2价格已重置为0\033[0m")

                            # 卖出UP
                            self.only_sell_up()

                            # 设置YES3价格为默认值
                            self.yes3_price_entry = self.yes_frame.grid_slaves(row=4, column=1)[0]
                            self.yes3_price_entry.delete(0, tk.END)
                            self.yes3_price_entry.insert(0, str(self.default_target_price))
                            self.yes3_price_entry.configure(foreground='red')
                            
                            # 同步UP3价格到StatusDataManager
                            self.status_data.update('positions', 'up_positions', [
                                self.status_data.data['positions']['up_positions'][0],
                                self.status_data.data['positions']['up_positions'][1],
                                {'price': str(self.default_target_price), 'amount': self.status_data.data['positions']['up_positions'][2]['amount']},
                                self.status_data.data['positions']['up_positions'][3]
                            ])
                            
                            self.logger.info(f"✅ \033[34mYes3价格已重置为{self.default_target_price}\033[0m")

                            # 自动改变交易次数
                            self.change_buy_and_trade_count()
                            
                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Down2",
                                price=self.price,
                                amount=self.amount,
                                shares=self.shares,
                                trade_count=self.buy_count,
                                cash_value=self.cash_value,
                                portfolio_value=self.portfolio_value
                            )
                            self.logger.info(f"\033[34m✅ 第{self.buy_count}次 BUY DOWN2成功\033[0m")
                            
                            break
                        else:
                            self.logger.warning(f"❌ \033[31mBuy Down2 交易失败,第{retry+1}次,等待1秒后重试\033[0m")
                            time.sleep(1)
                    else:
                        self.send_trade_email(
                            trade_type="Buy Down2失败",
                            price=down_price,
                            amount=0,
                            shares=0,
                            trade_count=self.buy_count,
                            cash_value=self.cash_value,
                            portfolio_value=self.portfolio_value
                        )
        except ValueError as e:
            self.logger.error(f"价格转换错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"Second_trade执行失败: {str(e)}")
        finally:
            self.trading = False
    
    def Third_trade(self, up_price, down_price):
        """处理Yes3/No3的自动交易"""
        try:
            if (up_price is not None and up_price > 10) and (down_price is not None and down_price > 10):              
                # 获取Yes3和No3的价格输入框
                yes3_price = float(self.yes3_price_entry.get())
                no3_price = float(self.no3_price_entry.get())
                self.trading = True  # 开始交易
            
                # 检查Yes3价格匹配
                if 0 <= round((up_price - yes3_price), 2) <= self.price_premium and up_price > 20:
                    for retry in range(3):
                        self.logger.info(f"✅ \033[32mUp 3: {up_price}¢ 价格匹配,执行自动买入,第{retry+1}次尝试\033[0m")
                        # 如果买入次数大于 18 次,那么先卖出,后买入
                        if self.buy_count > 14:
                            self.only_sell_down()

                        # 传 Tkinter 的 AmountEntry 对象，比如 self.yes3_amount_entry
                        self.send_amount_and_click_buy_confirm(self.yes3_amount_entry)

                        time.sleep(2)
                        if self.Verify_buy_up():
                            # 获取 YES3 的金额
                            self.buy_yes3_amount = float(self.yes3_amount_entry.get())
                            
                            # 重置Yes3和No3价格为0
                            self.yes3_price_entry.delete(0, tk.END)
                            self.yes3_price_entry.insert(0, "0")
                            self.yes3_price_entry.configure(foreground='black')
                            self.no3_price_entry.delete(0, tk.END)
                            self.no3_price_entry.insert(0, "0")
                            self.no3_price_entry.configure(foreground='black')
                            #self.logger.info(f"\033[34m✅ Yes3和No3价格已重置为0\033[0m")

                            # 同步UP3/DOWN3价格重置到StatusDataManager
                            self.status_data.update('positions', 'up_positions', [
                                {"price": float(self.yes1_price_entry.get())},
                                {"price": float(self.yes2_price_entry.get())},
                                {"price": 0},  # UP3重置为0
                                {"price": float(self.yes4_price_entry.get())}
                            ])
                            self.status_data.update('positions', 'down_positions', [
                                {"price": float(self.no1_price_entry.get())},
                                {"price": float(self.no2_price_entry.get())},
                                {"price": 0},  # DOWN3重置为0
                                {"price": float(self.no4_price_entry.get())}
                            ])

                            # 卖出DOWN
                            self.only_sell_down()

                            # 设置No4价格为默认值
                            self.no4_price_entry = self.no_frame.grid_slaves(row=6, column=1)[0]
                            self.no4_price_entry.delete(0, tk.END)
                            self.no4_price_entry.insert(0, str(self.default_target_price))
                            self.no4_price_entry.configure(foreground='red')
                            #self.logger.info(f"✅ \033[34mNo4价格已重置为{self.default_target_price}\033[0m")

                            # 同步DOWN4价格设置到StatusDataManager
                            self.status_data.update('positions', 'up_positions', [
                                {"price": float(self.yes1_price_entry.get())},
                                {"price": float(self.yes2_price_entry.get())},
                                {"price": 0},
                                {"price": float(self.yes4_price_entry.get())}
                            ])
                            self.status_data.update('positions', 'down_positions', [
                                {"price": float(self.no1_price_entry.get())},
                                {"price": float(self.no2_price_entry.get())},
                                {"price": 0},
                                {"price": self.default_target_price}  # DOWN4设置为默认值
                            ])

                            # 自动改变交易次数
                            self.change_buy_and_trade_count()

                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Up3",
                                price=self.price,
                                amount=self.amount,
                                shares=self.shares,
                                trade_count=self.buy_count,
                                cash_value=self.cash_value,
                                portfolio_value=self.portfolio_value
                            )   
                            self.logger.info(f"\033[34m✅ 第{self.buy_count}次 BUY UP3成功\033[0m")

                            break
                        else:
                            self.logger.warning(f"❌ \033[31mBuy Up3 交易失败,等待1秒后重试\033[0m")
                            time.sleep(1)  # 添加延时避免过于频繁的重试
                    else:
                        # 3次失败后发邮件
                        self.send_trade_email(
                            trade_type="Buy UP3失败",
                            price=up_price,
                            amount=0,
                            shares=0,
                            trade_count=self.buy_count,
                            cash_value=self.cash_value,
                            portfolio_value=self.portfolio_value
                        )   

                # 检查No3价格匹配
                elif 0 <= round((down_price - no3_price), 2) <= self.price_premium and down_price > 20:
                    for retry in range(3):
                        self.logger.info(f"✅ \033[31mDown 3: {down_price}¢ 价格匹配,执行自动买入,第{retry+1}次尝试\033[0m")
                        # 如果买入次数大于 18 次,那么先卖出,后买入
                        if self.buy_count > 14:
                            self.only_sell_up()

                        # 执行交易操作
                        self.buy_no_button.invoke()
                        # 传 Tkinter 的 AmountEntry 对象，比如 self.no3_amount_entry
                        self.send_amount_and_click_buy_confirm(self.no3_amount_entry)

                        time.sleep(2)
                        if self.Verify_buy_down():
                            self.buy_no3_amount = float(self.no3_amount_entry.get())
                            
                            # 重置Yes3和No3价格为0
                            self.yes3_price_entry.delete(0, tk.END)
                            self.yes3_price_entry.insert(0, "0")
                            self.yes3_price_entry.configure(foreground='black')
                            self.no3_price_entry.delete(0, tk.END)
                            self.no3_price_entry.insert(0, "0")
                            self.no3_price_entry.configure(foreground='black')
                            #self.logger.info(f"\033[34m✅ Yes3和No3价格已重置为0\033[0m")

                            # 同步UP3/DOWN3价格重置到StatusDataManager
                            self.status_data.update('positions', 'up_positions', [
                                {"price": float(self.yes1_price_entry.get())},
                                {"price": float(self.yes2_price_entry.get())},
                                {"price": 0},  # UP3重置为0
                                {"price": float(self.yes4_price_entry.get())}
                            ])
                            self.status_data.update('positions', 'down_positions', [
                                {"price": float(self.no1_price_entry.get())},
                                {"price": float(self.no2_price_entry.get())},
                                {"price": 0},  # DOWN3重置为0
                                {"price": float(self.no4_price_entry.get())}
                            ])

                            # 卖出UP
                            self.only_sell_up()

                            # 设置Yes4价格为默认值
                            self.yes4_price_entry = self.yes_frame.grid_slaves(row=6, column=1)[0]
                            self.yes4_price_entry.delete(0, tk.END)
                            self.yes4_price_entry.insert(0, str(self.default_target_price))
                            self.yes4_price_entry.configure(foreground='red')
                            #self.logger.info(f"✅ \033[34mYes4价格已重置为{self.default_target_price}\033[0m")

                            # 同步UP4价格设置到StatusDataManager
                            self.status_data.update('positions', 'up_positions', [
                                {"price": float(self.yes1_price_entry.get())},
                                {"price": float(self.yes2_price_entry.get())},
                                {"price": 0},
                                {"price": self.default_target_price}  # UP4设置为默认值
                            ])
                            self.status_data.update('positions', 'down_positions', [
                                {"price": float(self.no1_price_entry.get())},
                                {"price": float(self.no2_price_entry.get())},
                                {"price": 0},
                                {"price": float(self.no4_price_entry.get())}
                            ])

                            # 自动改变交易次数
                            self.change_buy_and_trade_count()

                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Down3",
                                price=self.price,
                                amount=self.amount,
                                shares=self.shares,
                                trade_count=self.buy_count,
                                cash_value=self.cash_value,
                                portfolio_value=self.portfolio_value
                            )
                            self.logger.info(f"\033[34m✅ 第{self.buy_count}次 BUY DOWN3成功\033[0m")

                            break
                        else:
                            self.logger.warning(f"❌ \033[31mBuy Down3 交易失败,第{retry+1}次,等待1秒后重试\033[0m")
                            time.sleep(1)  # 添加延时避免过于频繁的重试
                    else:
                        # 3次失败后发邮件
                        self.send_trade_email(
                            trade_type="Buy Down3失败",
                            price=down_price,
                            amount=0,
                            shares=0,
                            trade_count=self.buy_count,
                            cash_value=self.cash_value,
                            portfolio_value=self.portfolio_value
                        )   
            
        except ValueError as e:
            self.logger.error(f"价格转换错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"Third_trade执行失败: {str(e)}")    
        finally:
            self.trading = False

    def Forth_trade(self, up_price, down_price):
        """处理Yes4/No4的自动交易"""
        try:
            if (up_price is not None and up_price > 10) and (down_price is not None and down_price > 10):  
                # 获取Yes4和No4的价格输入框
                yes4_price = float(self.yes4_price_entry.get())
                no4_price = float(self.no4_price_entry.get())
                self.trading = True  # 开始交易
            
                # 检查Yes4价格匹配
                if 0 <= round((up_price - yes4_price), 2) <= self.price_premium and up_price > 20:
                    for retry in range(3):
                        self.logger.info(f"✅ \033[32mUp 4: {up_price}¢\033[0m 价格匹配,执行自动买入,第{retry+1}次尝试")
                        # 如果买入次数大于 18 次,那么先卖出,后买入
                        if self.buy_count > 14:
                            self.only_sell_down()

                        # 传 Tkinter 的 AmountEntry 对象，比如 self.yes4_amount_entry
                        self.send_amount_and_click_buy_confirm(self.yes4_amount_entry)

                        time.sleep(2)
                        if self.Verify_buy_up():
                            self.yes4_amount = float(self.yes4_amount_entry.get())
                            
                            # 设置 YES4/No4的价格为0
                            self.no4_price_entry.delete(0, tk.END)
                            self.no4_price_entry.insert(0, "0") 
                            self.no4_price_entry.configure(foreground='black')
                            self.yes4_price_entry.delete(0, tk.END)
                            self.yes4_price_entry.insert(0, "0") 
                            self.yes4_price_entry.configure(foreground='black')
                            #self.logger.info(f"✅ \033[34mYES4/No4价格已重置为0\033[0m")

                            # 同步UP4/DOWN4价格重置到StatusDataManager
                            self.status_data.update('positions', 'up_positions', [
                                {"price": float(self.yes1_price_entry.get())},
                                {"price": float(self.yes2_price_entry.get())},
                                {"price": float(self.yes3_price_entry.get())},
                                {"price": 0}  # UP4重置为0
                            ])
                            self.status_data.update('positions', 'down_positions', [
                                {"price": float(self.no1_price_entry.get())},
                                {"price": float(self.no2_price_entry.get())},
                                {"price": float(self.no3_price_entry.get())},
                                {"price": 0}  # DOWN4重置为0
                            ])

                            # 卖出DOWN
                            self.only_sell_down()

                            # 设置 NO1 价格为默认值
                            self.no1_price_entry.delete(0, tk.END)
                            self.no1_price_entry.insert(0, str(self.default_target_price))
                            self.no1_price_entry.configure(foreground='red')

                            # 同步DOWN1价格设置到StatusDataManager
                            self.status_data.update('positions', 'up_positions', [
                                {"price": float(self.yes1_price_entry.get())},
                                {"price": float(self.yes2_price_entry.get())},
                                {"price": float(self.yes3_price_entry.get())},
                                {"price": 0}
                            ])
                            self.status_data.update('positions', 'down_positions', [
                                {"price": self.default_target_price},  # DOWN1设置为默认值
                                {"price": float(self.no2_price_entry.get())},
                                {"price": float(self.no3_price_entry.get())},
                                {"price": 0}
                            ])

                            # 重新设置 UP1/DOWN1 的金额,功能等同于函数:set_yes_no_amount()
                            self.reset_yes_no_amount()

                            # 自动改变交易次数
                            self.change_buy_and_trade_count()

                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Up4",
                                price=self.price,
                                amount=self.amount,
                                shares=self.shares,
                                trade_count=self.buy_count,
                                cash_value=self.cash_value,
                                portfolio_value=self.portfolio_value
                            )
                            self.logger.info(f"\033[34m✅ 第{self.buy_count}次 BUY UP4成功\033[0m")
                           
                            break
                        else:
                            self.logger.warning(f"❌ \033[31mBuy Up4 交易失败,第{retry+1}次,等待2秒后重试\033[0m")
                            time.sleep(2)  # 添加延时避免过于频繁的重试
                    else:
                        # 3次失败后发邮件
                        self.send_trade_email(
                            trade_type="Buy Up4失败",
                            price=up_price,
                            amount=0,
                            shares=0,
                            trade_count=self.buy_count,
                            cash_value=self.cash_value,
                            portfolio_value=self.portfolio_value
                        )
                # 检查No4价格匹配
                elif 0 <= round((down_price - no4_price), 2) <= self.price_premium and down_price > 20:
                    for retry in range(3):
                        self.logger.info(f"✅ \033[31mDown 4: {down_price}¢ 价格匹配,执行自动买入,第{retry+1}次尝试\033[0m")
                        # 如果买入次数大于 18 次,那么先卖出,后买入
                        if self.buy_count > 14:
                            self.only_sell_up()

                        # 执行交易操作
                        self.buy_no_button.invoke()

                        # 传 Tkinter 的 AmountEntry 对象，比如 self.no4_amount_entry
                        self.send_amount_and_click_buy_confirm(self.no4_amount_entry)
                        
                        time.sleep(2)
                        if self.Verify_buy_down():
                            self.no4_amount = float(self.no4_amount_entry.get())
                            # 设置 YES4/No4的价格为0
                            self.no4_price_entry.delete(0, tk.END)
                            self.no4_price_entry.insert(0, "0") 
                            self.no4_price_entry.configure(foreground='black')
                            self.yes4_price_entry.delete(0, tk.END)
                            self.yes4_price_entry.insert(0, "0") 
                            self.yes4_price_entry.configure(foreground='black')
                            #self.logger.info(f"✅ \033[34mYES4/No4价格已重置为0\033[0m")

                            # 同步UP4/DOWN4价格重置到StatusDataManager
                            self.status_data.update('positions', 'up_positions', [
                                {"price": float(self.yes1_price_entry.get())},
                                {"price": float(self.yes2_price_entry.get())},
                                {"price": float(self.yes3_price_entry.get())},
                                {"price": 0}  # UP4重置为0
                            ])
                            self.status_data.update('positions', 'down_positions', [
                                {"price": float(self.no1_price_entry.get())},
                                {"price": float(self.no2_price_entry.get())},
                                {"price": float(self.no3_price_entry.get())},
                                {"price": 0}  # DOWN4重置为0
                            ])

                            # 卖出UP
                            self.only_sell_up()

                            #设置 YES1价格为默认买入价
                            self.yes1_price_entry.configure(foreground='red')
                            self.yes1_price_entry.delete(0, tk.END)
                            self.yes1_price_entry.insert(0, str(self.default_target_price))

                            # 同步UP1价格设置到StatusDataManager
                            self.status_data.update('positions', 'up_positions', [
                                {"price": self.default_target_price},  # UP1设置为默认值
                                {"price": float(self.yes2_price_entry.get())},
                                {"price": float(self.yes3_price_entry.get())},
                                {"price": 0}
                            ])
                            self.status_data.update('positions', 'down_positions', [
                                {"price": float(self.no1_price_entry.get())},
                                {"price": float(self.no2_price_entry.get())},
                                {"price": float(self.no3_price_entry.get())},
                                {"price": 0}
                            ])

                            # 重新设置 UP1/DOWN1 的金额,功能等同于函数:set_yes_no_amount()
                            self.reset_yes_no_amount()

                            # 自动改变交易次数
                            self.change_buy_and_trade_count()

                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Down4",
                                price=self.price,
                                amount=self.amount,
                                shares=self.shares,
                                trade_count=self.buy_count,
                                cash_value=self.cash_value,
                                portfolio_value=self.portfolio_value
                            )
                            self.logger.info(f"\033[34m✅ 第{self.buy_count}次 BUY DOWN4成功\033[0m")
                            
                            break
                        else:
                            self.logger.warning(f"❌ \033[31mBuy Down4 交易失败,第{retry+1}次,等待1秒后重试\033[0m")
                            time.sleep(1)  # 添加延时避免过于频繁的重试
                    else:
                        # 3次失败后发邮件
                        self.send_trade_email(
                            trade_type="Buy Down4失败",
                            price=down_price,
                            amount=0,
                            shares=0,
                            trade_count=self.buy_count,
                            cash_value=self.cash_value,
                            portfolio_value=self.portfolio_value
                        )   
            
        except ValueError as e:
            self.logger.error(f"价格转换错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"Forth_trade执行失败: {str(e)}")  
        finally:
            self.trading = False

    def reset_yes_no_amount(self):
        """重置 YES/NO ENTRY 金额"""
        # 设置 UP1 和 DOWN1金额
        yes1_amount = float(self.yes4_amount_entry.get()) * (self.n_rebound / 100)
        self.yes1_entry = self.yes_frame.grid_slaves(row=1, column=1)[0]
        self.yes1_amount_entry.delete(0, tk.END)
        self.yes1_amount_entry.insert(0, f"{yes1_amount:.2f}")
        self.no1_entry = self.no_frame.grid_slaves(row=1, column=1)[0]
        self.no1_amount_entry.delete(0, tk.END)
        self.no1_amount_entry.insert(0, f"{yes1_amount:.2f}")
        
        # 计算并设置 UP2/DOWN2金额
        yes2_amount = yes1_amount * (self.n_rebound / 100)
        self.yes2_entry = self.yes_frame.grid_slaves(row=3, column=1)[0]
        self.yes2_entry.delete(0, tk.END)
        self.yes2_entry.insert(0, f"{yes2_amount:.2f}")
        self.no2_entry = self.no_frame.grid_slaves(row=3, column=1)[0]
        self.no2_entry.delete(0, tk.END)
        self.no2_entry.insert(0, f"{yes2_amount:.2f}")
        
        # 计算并设置 UP3/DOWN3 金额
        yes3_amount = yes2_amount * (self.n_rebound / 100)
        self.yes3_entry = self.yes_frame.grid_slaves(row=5, column=1)[0]
        self.yes3_entry.delete(0, tk.END)
        self.yes3_entry.insert(0, f"{yes3_amount:.2f}")
        self.no3_entry = self.no_frame.grid_slaves(row=5, column=1)[0]
        self.no3_entry.delete(0, tk.END)
        self.no3_entry.insert(0, f"{yes3_amount:.2f}")

        # 计算并设置 UP4/DOWN4金额
        yes4_amount = yes3_amount * (self.n_rebound / 100)
        self.yes4_entry = self.yes_frame.grid_slaves(row=7, column=1)[0]
        self.yes4_entry.delete(0, tk.END)
        self.yes4_entry.insert(0, f"{yes4_amount:.2f}")
        self.no4_entry = self.no_frame.grid_slaves(row=7, column=1)[0]
        self.no4_entry.delete(0, tk.END)
        self.no4_entry.insert(0, f"{yes4_amount:.2f}")
        
        # 同步金额到StatusDataManager
        self.status_data.update('positions', 'up_positions', [
            {'price': '0', 'amount': f"{yes1_amount:.2f}"},
            {'price': '0', 'amount': f"{yes2_amount:.2f}"},
            {'price': '0', 'amount': f"{yes3_amount:.2f}"},
            {'price': '0', 'amount': f"{yes4_amount:.2f}"}
        ])
        self.status_data.update('positions', 'down_positions', [
            {'price': '0', 'amount': f"{yes1_amount:.2f}"},
            {'price': '0', 'amount': f"{yes2_amount:.2f}"},
            {'price': '0', 'amount': f"{yes3_amount:.2f}"},
            {'price': '0', 'amount': f"{yes4_amount:.2f}"}
        ])
        
        self.logger.info("设置 YES1-4/NO1-4金额成功")

    def send_amount_and_click_buy_confirm(self, amount_entry):
        """改进版买入交易执行 - 使用批量DOM操作并增强错误处理"""
        try:
            amount = amount_entry.get()
            #self.logger.info(f"\033[34m开始执行买入交易,金额: ${amount}\033[0m")
            
            # 定义批量操作 - 设置金额并点击确认
            operations = [
                {'xpath': XPathConfig.AMOUNT_INPUT[0], 'action': 'set_value', 'value': amount},
                {'xpath': XPathConfig.BUY_CONFIRM_BUTTON[0], 'action': 'click', 'delay': 200},
                {'xpath': XPathConfig.ACCEPT_BUTTON[0], 'action': 'click', 'delay': 100, 'optional': True}
            ]
            
            # 定义回退操作
            fallback_operations = [
                lambda: self._fallback_buy_operation(amount),
            ]
            
            # 使用批量DOM操作方法
            result = self._execute_batch_dom_operations(operations, fallback_operations)
            
            if result.get('success') or result.get('partial_success'):
                # self.logger.info("✅ \033[34m使用批量操作买入完成\033[0m")
                # 增加等待时间让交易完成 - 给服务器更多时间处理交易
                # self.logger.info("等待交易处理完成...")
                time.sleep(2)  # 增加到2秒
            else:
                self.logger.warning("⚠️ \033[31m批量操作失败，已执行回退操作\033[0m")
                # 回退操作后也需要等待
                time.sleep(2)
                
        except Exception as e:
            self.logger.error(f"买入交易执行失败: {str(e)}")
            # 尝试回退操作
            try:
                self._fallback_buy_operation(amount_entry.get())
            except Exception as fallback_error:
                self.logger.error(f"回退操作也失败: {str(fallback_error)}")
                
    def _fallback_buy_operation(self, amount):
        """买入操作的回退方法"""
        try:
            self.logger.info("\033[34m执行买入回退操作\033[0m")
            
            # 查找并设置金额输入框
            amount_input = WebDriverWait(self.driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, XPathConfig.AMOUNT_INPUT[0]))
            )
            
            # 清空并设置新值
            amount_input.clear()
            amount_input.send_keys(str(amount))
            
            # 点击确认按钮
            buy_confirm_button = WebDriverWait(self.driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, XPathConfig.BUY_CONFIRM_BUTTON[0]))
            )
            buy_confirm_button.click()
            
            # 处理可能的ACCEPT弹窗
            try:
                accept_button = WebDriverWait(self.driver, 1).until(
                    EC.element_to_be_clickable((By.XPATH, XPathConfig.ACCEPT_BUTTON[0]))
                )
                accept_button.click()
                #self.logger.info("✅ 点击了ACCEPT按钮")
            except TimeoutException:
                self.logger.info("ℹ️ 没有ACCEPT弹窗出现")
                
            self.logger.info("✅ \033[34m回退买入操作完成\033[0m")
            
        except Exception as e:
            self.logger.error(f"回退买入操作失败: {str(e)}")
            raise

    def click_positions_sell_and_sell_confirm_and_accept(self):
        """卖出并点击确认 - 使用顺序执行的批量操作"""
        try:
            # 定义顺序执行的操作 - 包含延迟确保按钮响应
            operations = [
                {'xpath': XPathConfig.POSITION_SELL_BUTTON[0], 'action': 'click'},
                {'xpath': XPathConfig.SELL_CONFIRM_BUTTON[0], 'action': 'click', 'delay': 100},
                {'xpath': XPathConfig.ACCEPT_BUTTON[0], 'action': 'click', 'delay': 100, 'optional': True}
            ]
            
            # 定义回退操作
            fallback_operations = [
                lambda: self._fallback_sell_operation(),
            ]
            
            # 使用顺序执行方法
            self._execute_sequential_dom_operations(operations, fallback_operations)
            
        except Exception as e:
            self.logger.error(f"卖出失败: {str(e)}")
            
    def _fallback_sell_operation(self):
        """卖出操作的回退方法"""
        try:
            # 点击卖出按钮
            try:
                positions_sell_button = self.driver.find_element(By.XPATH, XPathConfig.POSITION_SELL_BUTTON[0])
                positions_sell_button.click()
            except TimeoutException:
                positions_sell_button = WebDriverWait(self.driver, 0.5).until(
                    EC.element_to_be_clickable((By.XPATH, XPathConfig.POSITION_SELL_BUTTON[0]))
                )
                positions_sell_button.click()
                #self.logger.error("❌ \033[31m没有出现SELL按钮,跳过点击\033[0m")

            # 点击卖出确认按钮
            try:
                sell_confirm_button = self.driver.find_element(By.XPATH, XPathConfig.SELL_CONFIRM_BUTTON[0])
                sell_confirm_button.click()
            except TimeoutException:
                sell_confirm_button = WebDriverWait(self.driver, 0.5).until(
                    EC.element_to_be_clickable((By.XPATH, XPathConfig.SELL_CONFIRM_BUTTON[0]))
                )
                sell_confirm_button.click()
                #self.logger.error("❌ \033[31m没有出现SELL_CONFIRM按钮,跳过点击\033[0m")

            # 等待ACCEPT弹窗出现
            try:
                accept_button = WebDriverWait(self.driver, 1).until(
                    EC.element_to_be_clickable((By.XPATH, XPathConfig.ACCEPT_BUTTON[0]))
                )
                accept_button.click()
            except TimeoutException:
                pass  # 弹窗没出现,不用处理
        except Exception as e:
            self.logger.error(f"回退卖出操作失败: {str(e)}")

    def only_sell_up(self):
        """只卖出YES,且验证交易是否成功"""
        # 重试 3 次
        for retry in range(3):
            self.logger.info("\033[32m执行only_sell_up\033[0m")

            self.click_positions_sell_and_sell_confirm_and_accept()

            if self._verify_trade('Sold', 'Up')[0]:
                # 增加卖出计数
                self.sell_count += 1
                # 发送交易邮件 - 卖出YES
                self.send_trade_email(
                    trade_type="Sell Up",
                    price=self.price,
                    amount=self.amount,
                    shares=self.shares,
                    trade_count=self.sell_count,
                    cash_value=self.cash_value,
                    portfolio_value=self.portfolio_value
                )
                self.logger.info(f"卖出 Up 成功")
                self.driver.refresh()
                break
            else:
                self.logger.warning(f"❌ \033[31m卖出only_sell_up第{retry+1}次验证失败,重试\033[0m")
                time.sleep(1)
      
    def only_sell_down(self):
        """只卖出Down,且验证交易是否成功"""
        # 重试 3 次
        for retry in range(3): 
            self.logger.info("\033[32m执行only_sell_down\033[0m")

            self.click_positions_sell_and_sell_confirm_and_accept()

            if self._verify_trade('Sold', 'Down')[0]:
                # 增加卖出计数
                self.sell_count += 1
                
                # 发送交易邮件 - 卖出NO
                self.send_trade_email(
                    trade_type="Sell Down",
                    price=self.price,
                    amount=self.amount,
                    shares=self.shares,
                    trade_count=self.sell_count,
                    cash_value=self.cash_value,
                    portfolio_value=self.portfolio_value
                )
                self.logger.info(f"卖出 Down 成功")
                self.driver.refresh()
                break
            else:
                self.logger.warning(f"❌ \033[31m卖出only_sell_down第{retry+1}次验证失败,重试\033[0m")
                time.sleep(1)

    def Verify_buy_up(self):
        """
        验证买入YES交易是否成功完成
        
        Returns:
            bool: 交易是否成功
        """
        return self._verify_trade('Bought', 'Up')[0]
        
    def Verify_buy_down(self):
        """
        验证买入NO交易是否成功完成
        
        Returns:
            bool: 交易是否成功
        """
        return self._verify_trade('Bought', 'Down')[0]
    
    def Verify_sold_up(self):
        """
        验证卖出YES交易是否成功完成
        
        Returns:
            bool: 交易是否成功
        """
        return self._verify_trade('Sold', 'Up')[0]
        
    def Verify_sold_down(self):
        """
        验证卖出NO交易是否成功完成
        
        Returns:
            bool: 交易是否成功
        """
        return self._verify_trade('Sold', 'Down')[0]

    def _verify_trade(self, action_type, direction):
        """
        验证交易是否成功完成
        基于时间的循环:在6秒时间窗口内不断查找,时间到了就刷新,循环2次
        
        Args:
            action_type: 'Bought' 或 'Sold'
            direction: 'Up' 或 'Down'
            
        Returns:
            tuple: (是否成功, 价格, 金额, 份额)
        """
        try:
            for attempt in range(2):
                #  重试 2次,每次智能等待3秒
                max_retries = 2  # 最大重试次数
                wait_interval = 1  # 检查间隔
                
                for retry in range(max_retries):
                    try:
                        # 等待历史记录元素出现                  
                        try:
                            # 将元素查找超时时间从默认值减少到0.5秒，加快查找速度
                            history_element = WebDriverWait(self.driver, 3).until(
                                EC.presence_of_element_located((By.XPATH, XPathConfig.HISTORY[0])))
                        except (NoSuchElementException, StaleElementReferenceException, TimeoutException):
                            # 将重试查找超时时间从2秒减少到0.5秒
                            history_element = self._find_element_with_retry(XPathConfig.HISTORY, timeout=0.5, silent=True)
                        
                        if history_element:
                            # 获取历史记录文本
                            history_text = history_element.text
                            #self.logger.info(f"找到交易记录: \033[34m{history_text}\033[0m")
                            
                            # 分别查找action_type和direction，避免同时匹配导致的问题
                            action_found = re.search(rf"\b{action_type}\b", history_text, re.IGNORECASE)
                            direction_found = re.search(rf"\b{direction}\b", history_text, re.IGNORECASE)
                            
                            if action_found and direction_found:
                                # 提取价格和金额 - 优化正则表达式
                                price_match = re.search(r'at\s+(\d+\.?\d*)¢', history_text)
                                amount_match = re.search(r'\(\$(\d+\.\d+)\)', history_text)
                                # 提取SHARES - shares是Bought/Sold后的第一个数字
                                shares_match = re.search(r'(?:Bought|Sold)\s+(\d+(?:\.\d+)?)', history_text, re.IGNORECASE)
                                
                                self.price = float(price_match.group(1)) if price_match else 0
                                self.amount = float(amount_match.group(1)) if amount_match else 0
                                self.shares = float(shares_match.group(1)) if shares_match else 0

                                self.logger.info(f"✅ \033[32m交易验证成功: {action_type} {direction} 价格: {self.price} 金额: {self.amount} Shares: {self.shares}\033[0m")
                                
                                # 同步交易验证信息到StatusDataManager
                                self.status_data.update('trade_verification', 'direction', direction_found)
                                self.status_data.update('trade_verification', 'shares', self.shares)
                                self.status_data.update('trade_verification', 'price', self.price)
                                self.status_data.update('trade_verification', 'amount', self.amount)
                                
                                return True, self.price, self.amount, self.shares
                    
                    except StaleElementReferenceException:
                        self.logger.warning(f"\033[31m未找到交易记录,重新定位元素\033[0m")
                        continue  # 继续下一次重试，不退出循环
                    except Exception as e:
                        self.logger.warning(f"元素操作异常: {str(e)}")
                        continue
                    
                    # 如果不是最后一次重试，等待1秒后继续
                    if retry < max_retries - 1:
                        time.sleep(wait_interval)
            # 超时未找到匹配的交易记录
            self.logger.warning(f"❌ \033[31m交易验证失败,已尝试2轮\033[0m")

            return False, 0, 0, 0
        except Exception as e:
            self.logger.error(f"交易验证失败: {str(e)}")
            return False, 0, 0, 0

    def click_buy_confirm_button(self):
        try:
            buy_confirm_button = self.driver.find_element(By.XPATH, XPathConfig.BUY_CONFIRM_BUTTON[0])
            buy_confirm_button.click()
        except NoSuchElementException:
            
            buy_confirm_button = self._find_element_with_retry(
                XPathConfig.BUY_CONFIRM_BUTTON,
                timeout=3,
                silent=True
            )
            buy_confirm_button.click()
    
    def click_position_sell_no(self):
        """点击 Positions-Sell-No 按钮"""
        try:
            position_value = self.find_position_label_up()
            # position_value 的值是true 或 false
            # 根据position_value的值决定点击哪个按钮
            if position_value:
                # 如果第一行是Up，点击第二的按钮
                try:
                    button = self.driver.find_element(By.XPATH, XPathConfig.POSITION_SELL_NO_BUTTON[0])
                except NoSuchElementException:
                    button = self._find_element_with_retry(
                        XPathConfig.POSITION_SELL_NO_BUTTON,
                        timeout=3,
                        silent=True
                    )
            else:
                # 如果第一行不存在或不是Up，使用默认的第一行按钮
                try:
                    button = self.driver.find_element(By.XPATH, XPathConfig.POSITION_SELL_BUTTON[0])
                except NoSuchElementException:
                    button = self._find_element_with_retry(
                        XPathConfig.POSITION_SELL_BUTTON,
                        timeout=3,
                        silent=True
                    )
            # 执行点击
            self.driver.execute_script("arguments[0].click();", button)
            
        except Exception as e:
            error_msg = f"点击 Positions-Sell-No 按钮失败: {str(e)}"
            self.logger.error(error_msg)
            
    def click_position_sell_yes(self):
        """点击 Positions-Sell-Yes 按钮"""
        try:
            position_value = self.find_position_label_down()
            
            # 根据position_value的值决定点击哪个按钮
            
            if position_value:
                # 如果第二行是No，点击第一行YES 的 SELL的按钮
                try:
                    button = self.driver.find_element(By.XPATH, XPathConfig.POSITION_SELL_YES_BUTTON[0])
                except NoSuchElementException:
                    button = self._find_element_with_retry(
                        XPathConfig.POSITION_SELL_YES_BUTTON,
                        timeout=3,
                        silent=True
                    )
            else:
                # 如果第二行不存在或不是No，使用默认的第一行按钮
                try:
                    button = self.driver.find_element(By.XPATH, XPathConfig.POSITION_SELL_BUTTON[0])
                except NoSuchElementException:
                    button = self._find_element_with_retry(
                        XPathConfig.POSITION_SELL_BUTTON,
                        timeout=3,
                        silent=True
                    )
            # 执行点击
            self.driver.execute_script("arguments[0].click();", button)
             
        except Exception as e:
            error_msg = f"点击 Positions-Sell-Yes 按钮失败: {str(e)}"
            self.logger.error(error_msg)
            
    def click_sell_confirm_button(self):
        """点击sell-卖出按钮"""
        try:
            # 点击Sell-卖出按钮
            try:
                sell_confirm_button = self.driver.find_element(By.XPATH, XPathConfig.SELL_CONFIRM_BUTTON[0])
            except NoSuchElementException:
                sell_confirm_button = self._find_element_with_retry(
                    XPathConfig.SELL_CONFIRM_BUTTON,
                    timeout=3,
                    silent=True
                )
            sell_confirm_button.click()
            
        except Exception as e:
            error_msg = f"卖出操作失败: {str(e)}"
            self.logger.error(error_msg)

    def click_buy(self):
        try:
            try:
                button = self.driver.find_element(By.XPATH, XPathConfig.BUY_BUTTON[0])
            except (NoSuchElementException, StaleElementReferenceException):
                button = self._find_element_with_retry(XPathConfig.BUY_BUTTON, timeout=2, silent=True)

            if button:
                button.click()
            else:
                self.logger.warning("Buy按钮未找到")
            
        except (TimeoutException, AttributeError) as e:
            self.logger.error(f"浏览器连接异常，点击Buy按钮失败: {str(e)}")
        except Exception as e:
            self.logger.error(f"点击 Buy 按钮失败: {str(e)}")

    def click_buy_yes(self):
        """点击 Buy-Yes 按钮"""
        try:           
            # 查找买YES按钮
            try:
                button = self.driver.find_element(By.XPATH, XPathConfig.BUY_YES_BUTTON[0])
            except (NoSuchElementException, StaleElementReferenceException):
                button = self._find_element_with_retry(XPathConfig.BUY_YES_BUTTON, timeout=2, silent=True)
                
            if button:
                button.click()
            else:
                self.logger.warning("Buy-Yes按钮未找到")
            
        except (TimeoutException, AttributeError) as e:
            self.logger.error(f"浏览器连接异常，点击Buy-Yes按钮失败: {str(e)}")
        except Exception as e:
            self.logger.error(f"点击 Buy-Yes 按钮失败: {str(e)}")

    def click_buy_no(self):
        """点击 Buy-No 按钮"""
        try:
            # 查找买NO按钮
            try:
                button = self.driver.find_element(By.XPATH, XPathConfig.BUY_NO_BUTTON[0])
            except (NoSuchElementException, StaleElementReferenceException):
                button = self._find_element_with_retry(XPathConfig.BUY_NO_BUTTON, timeout=2, silent=True)
                
            if button:
                button.click()
            else:
                self.logger.warning("Buy-No按钮未找到")
            
        except (TimeoutException, AttributeError) as e:
            self.logger.error(f"浏览器连接异常，点击Buy-No按钮失败: {str(e)}")
        except Exception as e:
            self.logger.error(f"点击 Buy-No 按钮失败: {str(e)}")
    
    def close_windows(self):
        """关闭多余窗口"""
        try:
            # 检查并关闭多余的窗口，只保留一个
            all_handles = self.driver.window_handles
            
            if len(all_handles) > 1:
                # self.logger.info(f"当前窗口数: {len(all_handles)}，准备关闭多余窗口")
                
                # 获取目标URL
                target_url = self.url_entry.get() if hasattr(self, 'url_entry') else None
                target_handle = None
                
                # 查找包含目标URL的窗口
                if target_url:
                    for handle in all_handles:
                        try:
                            self.driver.switch_to.window(handle)
                            current_url = self.driver.current_url
                            # 检查当前窗口是否包含目标URL的关键部分
                            if target_url in current_url or any(key in current_url for key in ['polymarket.com/event', 'up-or-down-on']):
                                target_handle = handle
                                break
                        except Exception as e:
                            self.logger.warning(f"检查窗口URL失败: {e}")
                            continue
                
                # 如果没有找到目标窗口，使用最后一个窗口作为备选
                if not target_handle:
                    target_handle = all_handles[-1]
                    self.logger.warning("未找到目标URL窗口,使用最后一个窗口")
                
                # 关闭除了目标窗口外的所有窗口
                for handle in all_handles:
                    if handle != target_handle:
                        try:
                            self.driver.switch_to.window(handle)
                            self.driver.close()
                        except Exception as e:
                            self.logger.warning(f"关闭窗口失败: {e}")
                            continue
                
                # 切换到保留的目标窗口
                try:
                    self.driver.switch_to.window(target_handle)
                    self.logger.info(f"✅ 已保留目标窗口，关闭了 {len(all_handles)-1} 个多余窗口")
                except Exception as e:
                    self.logger.warning(f"切换到目标窗口失败: {e}")
                
            else:
                self.logger.warning("❗ 当前窗口数不足2个,无需切换")
                
        except Exception as e:
            self.logger.error(f"关闭窗口操作失败: {e}")
            # 如果窗口操作失败，可能是浏览器会话已失效，不需要重启浏览器
            # 因为调用此方法的上层代码通常会处理浏览器重启

    def send_trade_email(self, trade_type, price, amount, shares, trade_count,
                         cash_value, portfolio_value):
        """发送交易邮件"""
        max_retries = 2
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                hostname = socket.gethostname()
                sender = 'huacaihuijin@126.com'
                
                # 根据HOSTNAME决定邮件接收者
                receivers = ['2049330@qq.com']  # 默认接收者，必须接收所有邮件
                if 'ZZY' in hostname:
                    receivers.append('2049330@qq.com')  # 如果HOSTNAME包含ZZY，添加QQ邮箱 # 272763832@qq.com
                
                app_password = 'PUaRF5FKeKJDrYH7'  # 有效期 180 天，请及时更新，下次到期日 2025-11-29
                
                # 获取交易币对信息
                full_pair = self.trading_pair_label.cget("text")
                trading_pair = full_pair.split('-')[0]
                if not trading_pair or trading_pair == "--":
                    trading_pair = "未知交易币对"
                
                # 根据交易类型选择显示的计数
                count_in_subject = self.sell_count if "Sell" in trade_type else trade_count
                
                msg = MIMEMultipart()
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                subject = f'{hostname}第{count_in_subject}次{trade_type}-{trading_pair}'
                msg['Subject'] = Header(subject, 'utf-8')
                msg['From'] = sender
                msg['To'] = ', '.join(receivers)

                # 修复格式化字符串问题，确保cash_value和portfolio_value是字符串
                str_cash_value = str(cash_value)
                str_portfolio_value = str(portfolio_value)
                
                content = f"""
                交易价格: {price:.2f}¢
                交易金额: ${amount:.2f}
                SHARES: {shares}
                当前买入次数: {self.buy_count}
                当前卖出次数: {self.sell_count}
                当前 CASH 值: {str_cash_value}
                当前 PORTFOLIO 值: {str_portfolio_value}
                交易时间: {current_time}
                """
                msg.attach(MIMEText(content, 'plain', 'utf-8'))
                
                # 使用126.com的SMTP服务器
                server = smtplib.SMTP_SSL('smtp.126.com', 465, timeout=5)  # 使用SSL连接
                server.set_debuglevel(0)
                
                try:
                    server.login(sender, app_password)
                    server.sendmail(sender, receivers, msg.as_string())
                    #self.logger.info(f"✅ \033[34m邮件发送成功: {trade_type} -> {', '.join(receivers)}\033[0m")
                    return  # 发送成功,退出重试循环
                except Exception as e:
                    self.logger.error(f"❌ SMTP操作失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                    if attempt < max_retries - 1:
                        self.logger.info(f"等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                finally:
                    try:
                        server.quit()
                    except Exception:
                        pass          
            except Exception as e:
                self.logger.error(f"❌ 邮件准备失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)     
        # 所有重试都失败
        error_msg = f"发送邮件失败,已重试{max_retries}次"
        self.logger.error(error_msg)

    def _send_chrome_alert_email(self):
        """发送Chrome异常警报邮件"""
        try:
            hostname = socket.gethostname()
            sender = 'huacaihuijin@126.com'
            receiver = '2049330@qq.com'
            app_password = 'PUaRF5FKeKJDrYH7'
            
            # 获取交易币对信息
            full_pair = self.trading_pair_label.cget("text")
            trading_pair = full_pair.split('-')[0] if full_pair and '-' in full_pair else "未知交易币对"
            
            msg = MIMEMultipart()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            subject = f'🚨{hostname}-Chrome异常-{trading_pair}-需要手动介入'
            msg['Subject'] = Header(subject, 'utf-8')
            msg['From'] = sender
            msg['To'] = receiver
            
            # 获取当前状态信息
            try:
                cash_value = self.cash_label.cget("text")
                portfolio_value = self.portfolio_label.cget("text")
            except:
                cash_value = "无法获取"
                portfolio_value = "无法获取"
            
            content = f"""
            🚨 Chrome浏览器异常警报 🚨

            异常时间: {current_time}
            主机名称: {hostname}
            交易币对: {trading_pair}
            当前买入次数: {self.buy_count}
            当前卖出次数: {self.sell_count}
            重启次数: {self.reset_trade_count}
            当前 CASH 值: {cash_value}
            当前 PORTFOLIO 值: {portfolio_value}

            ⚠️  请立即手动检查并介入处理！
            """
            
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            # 发送邮件
            server = smtplib.SMTP_SSL('smtp.126.com', 465, timeout=5)
            server.set_debuglevel(0)
            
            try:
                server.login(sender, app_password)
                server.sendmail(sender, receiver, msg.as_string())
                #self.logger.info(f"✅ Chrome异常警报邮件发送成功")
            except Exception as e:
                self.logger.error(f"❌ Chrome异常警报邮件发送失败: {str(e)}")
            finally:
                try:
                    server.quit()
                except Exception:
                    pass
                    
        except Exception as e:
            self.logger.error(f"发送Chrome异常警报邮件时出错: {str(e)}")

    def retry_operation(self, operation, *args, **kwargs):
        """通用重试机制"""
        for attempt in range(self.retry_count):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                self.logger.warning(f"{operation.__name__} 失败，尝试 {attempt + 1}/{self.retry_count}: {str(e)}")
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_interval)
                else:
                    raise

    def find_position_label_up(self):
        """查找Yes持仓标签"""
        max_retries = 3
        retry_delay = 0.3
        
        for attempt in range(max_retries):
            try:
                # 等待页面加载完成
                WebDriverWait(self.driver, 3).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )
                
                # 尝试获取Up标签
                try:
                    position_label_up = None
                    try:
                        position_label_up = self.driver.find_element(By.XPATH, XPathConfig.POSITION_UP_LABEL[0])
                    except (NoSuchElementException, StaleElementReferenceException):
                        position_label_up = self._find_element_with_retry(XPathConfig.POSITION_UP_LABEL, timeout=3, silent=True)
                        
                    if position_label_up is not None and position_label_up:
                        self.logger.info("✅ find-element,找到了Up持仓标签: {position_label_up.text}")
                        return True
                    else:
                        self.logger.info("❌ find_element,未找到Up持仓标签")
                        return False
                except NoSuchElementException:
                    position_label_up = self._find_element_with_retry(XPathConfig.POSITION_UP_LABEL, timeout=3, silent=True)
                    if position_label_up is not None and position_label_up:
                        self.logger.info(f"✅ with-retry,找到了Up持仓标签: {position_label_up.text}")
                        return True
                    else:
                        self.logger.info("❌ use with-retry,未找到Up持仓标签")
                        return False
                         
            except TimeoutException:
                self.logger.debug(f"第{attempt + 1}次尝试未找到UP标签,正常情况!")
            
            if attempt < max_retries - 1:
                self.logger.info(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                self.driver.refresh()
        return False
        
    def find_position_label_down(self):
        """查找Down持仓标签"""
        max_retries = 3
        retry_delay = 0.3
        
        for attempt in range(max_retries):
            try:
                # 等待页面加载完成
                WebDriverWait(self.driver, 3).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )
                
                # 尝试获取Down标签
                try:
                    position_label_down = None
                    try:
                        position_label_down = self.driver.find_element(By.XPATH, XPathConfig.POSITION_DOWN_LABEL[0])
                    except (NoSuchElementException, StaleElementReferenceException):
                        position_label_down = self._find_element_with_retry(XPathConfig.POSITION_DOWN_LABEL, timeout=3, silent=True)
                        
                    if position_label_down is not None and position_label_down:
                        self.logger.info(f"✅ find-element,找到了Down持仓标签: {position_label_down.text}")
                        return True
                    else:
                        self.logger.info("❌ find-element,未找到Down持仓标签")
                        return False
                except NoSuchElementException:
                    position_label_down = self._find_element_with_retry(XPathConfig.POSITION_DOWN_LABEL, timeout=3, silent=True)
                    if position_label_down is not None and position_label_down:
                        self.logger.info(f"✅ with-retry,找到了Down持仓标签: {position_label_down.text}")
                        return True
                    else:
                        self.logger.info("❌ with-retry,未找到Down持仓标签")
                        return False
                               
            except TimeoutException:
                self.logger.warning(f"第{attempt + 1}次尝试未找到Down标签")
                
            if attempt < max_retries - 1:
                self.logger.info(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                self.driver.refresh()
        return False
      
    def _get_cached_element(self, cache_key):
        """从缓存中获取元素"""
        with self.cache_lock:
            if cache_key in self.element_cache:
                cached_data = self.element_cache[cache_key]
                # 检查缓存是否过期
                if time.time() - cached_data['timestamp'] < self.cache_timeout:
                    try:
                        # 验证元素是否仍然有效
                        element = cached_data['element']
                        element.is_displayed()  # 这会触发StaleElementReferenceException如果元素无效
                        return element
                    except (StaleElementReferenceException, NoSuchElementException):
                        # 元素已失效，从缓存中移除
                        del self.element_cache[cache_key]
                else:
                    # 缓存过期，移除
                    del self.element_cache[cache_key]
            return None
    
    def _cache_element(self, cache_key, element):
        """将元素添加到缓存"""
        with self.cache_lock:
            self.element_cache[cache_key] = {
                'element': element,
                'timestamp': time.time()
            }
    
    def _clear_element_cache(self):
        """清空元素缓存"""
        with self.cache_lock:
            self.element_cache.clear()
    
    def _execute_batch_dom_operations(self, operations, fallback_operations=None):
        """批量执行DOM操作 - 支持顺序执行和延迟
        
        Args:
            operations: 要执行的操作列表，每个操作包含 {xpath, action, value?, delay?, optional?}
            fallback_operations: 批量操作失败时的回退操作函数列表
            
        Returns:
            dict: {success: bool, results: list, error: str?}
        """
        try:
            # 对于需要顺序执行的操作，使用异步JavaScript
            has_delays = any(op.get('delay', 0) > 0 for op in operations)
            
            if has_delays:
                # 使用异步方式处理有延迟的操作
                return self._execute_sequential_dom_operations(operations, fallback_operations)
            
            # 对于无延迟的操作，使用同步批量处理
            js_operations = []
            for i, op in enumerate(operations):
                xpath = op['xpath']
                action = op['action']  # 'click', 'setValue', 'getText'
                value = op.get('value', '')
                optional = op.get('optional', False)
                
                if action == 'click':
                    action_code = f'element{i}.click();'
                elif action == 'set_value':
                    # 清空输入框并设置新值，触发必要的事件
                    action_code = f'''
                        element{i}.focus();
                        element{i}.value = "";
                        element{i}.value = "{value}";
                        element{i}.dispatchEvent(new Event("input", {{bubbles: true}}));
                        element{i}.dispatchEvent(new Event("change", {{bubbles: true}}));
                    '''
                elif action == 'getText':
                    action_code = f'results.push(element{i}.textContent || element{i}.innerText);'
                else:
                    action_code = ''
                
                if optional:
                    js_operations.append(f"""
                        // 操作 {i+1}: {action} (可选)
                        const element{i} = document.evaluate(
                            '{xpath}', 
                            document, 
                            null, 
                            XPathResult.FIRST_ORDERED_NODE_TYPE, 
                            null
                        ).singleNodeValue;
                        
                        if (element{i}) {{
                            {action_code}
                            operations.push({{index: {i}, action: '{action}', success: true}});
                        }} else {{
                            operations.push({{index: {i}, action: '{action}', success: true, skipped: true}});
                        }}
                    """)
                else:
                    js_operations.append(f"""
                        // 操作 {i+1}: {action}
                        const element{i} = document.evaluate(
                            '{xpath}', 
                            document, 
                            null, 
                            XPathResult.FIRST_ORDERED_NODE_TYPE, 
                            null
                        ).singleNodeValue;
                        
                        if (element{i}) {{
                            {action_code}
                            operations.push({{index: {i}, action: '{action}', success: true}});
                        }} else {{
                            operations.push({{index: {i}, action: '{action}', success: false, error: 'Element not found'}});
                        }}
                    """)
            
            js_code = f"""
                try {{
                    let operations = [];
                    let results = [];
                    
                    {''.join(js_operations)}
                    
                    return {{success: true, operations: operations, results: results}};
                }} catch (e) {{
                    return {{success: false, error: e.message}};
                }}
            """
            
            result = self.driver.execute_script(js_code)
            
            if result.get('success'):
                successful_ops = [op for op in result.get('operations', []) if op.get('success')]
                failed_ops = [op for op in result.get('operations', []) if not op.get('success')]
                
                if failed_ops and fallback_operations:
                    self.logger.warning(f"批量操作中有{len(failed_ops)}个失败，执行回退操作")
                    # 只对失败的操作执行回退
                    for failed_op in failed_ops:
                        index = failed_op['index']
                        if index < len(fallback_operations):
                            try:
                                fallback_operations[index]()
                            except Exception as e:
                                self.logger.error(f"回退操作{index}失败: {str(e)}")
                
                return {
                    'success': True,
                    'operations': result.get('operations', []),
                    'results': result.get('results', []),
                    'partial_success': len(successful_ops) > 0
                }
            else:
                # 完全失败，执行所有回退操作
                if fallback_operations:
                    self.logger.warning(f"批量操作完全失败，执行所有回退操作: {result.get('error')}")
                    for i, fallback_op in enumerate(fallback_operations):
                        try:
                            fallback_op()
                        except Exception as e:
                            self.logger.error(f"回退操作{i}失败: {str(e)}")
                
                return {'success': False, 'error': result.get('error')}
                
        except Exception as e:
            self.logger.error(f"批量DOM操作执行失败: {str(e)}")
            # 执行所有回退操作
            if fallback_operations:
                for i, fallback_op in enumerate(fallback_operations):
                    try:
                        fallback_op()
                    except Exception as e:
                        self.logger.error(f"回退操作{i}失败: {str(e)}")
            
            return {'success': False, 'error': str(e)}
    
    def _execute_sequential_dom_operations(self, operations, fallback_operations=None):
        """顺序执行DOM操作 - 支持延迟和异步操作"""
        try:
            results = []
            operation_results = []
            
            for i, op in enumerate(operations):
                xpath = op['xpath']
                action = op['action']
                value = op.get('value', '')
                delay = op.get('delay', 0)
                optional = op.get('optional', False)
                
                try:
                    # 查找元素
                    element = WebDriverWait(self.driver, 0.5).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    
                    # 执行操作
                    if action == 'click':
                        element.click()
                    elif action == 'set_value':
                        # 清空输入框并设置新值，触发必要的事件
                        self.driver.execute_script("""
                            arguments[0].focus();
                            arguments[0].value = '';
                            arguments[0].value = arguments[1];
                            arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                            arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                        """, element, value)
                    elif action == 'getText':
                        results.append(element.text or element.get_attribute('textContent'))
                    
                    operation_results.append({
                        'index': i,
                        'action': action,
                        'success': True
                    })
                    
                    # 如果有延迟，等待指定时间
                    if delay > 0:
                        time.sleep(delay / 1000.0)  # 转换为秒
                        
                except (TimeoutException, NoSuchElementException) as e:
                    if optional:
                        # 可选操作失败不影响整体结果
                        operation_results.append({
                            'index': i,
                            'action': action,
                            'success': True,
                            'skipped': True
                        })
                    else:
                        # 必需操作失败，执行回退
                        operation_results.append({
                            'index': i,
                            'action': action,
                            'success': False,
                            'error': str(e)
                        })
                        
                        if fallback_operations and i < len(fallback_operations):
                            try:
                                fallback_operations[i]()
                            except Exception as fallback_error:
                                self.logger.error(f"回退操作{i}失败: {str(fallback_error)}")
            
            # 检查是否有失败的必需操作
            failed_required = [op for op in operation_results if not op.get('success') and not op.get('skipped')]
            
            return {
                'success': len(failed_required) == 0,
                'operations': operation_results,
                'results': results,
                'partial_success': any(op.get('success') for op in operation_results)
            }
            
        except Exception as e:
            self.logger.error(f"顺序DOM操作执行失败: {str(e)}")
            # 执行所有回退操作
            if fallback_operations:
                for i, fallback_op in enumerate(fallback_operations):
                    try:
                        fallback_op()
                    except Exception as fallback_error:
                        self.logger.error(f"回退操作{i}失败: {str(fallback_error)}")
            
            return {'success': False, 'error': str(e)}

    def _find_element_with_retry(self, xpaths, timeout=1, silent=True, use_cache=True):
        """优化版元素查找 - 支持缓存和并行查找多个XPath"""
        # 生成缓存键
        cache_key = str(sorted(xpaths)) if use_cache else None
        
        # 尝试从缓存获取元素
        if use_cache and cache_key:
            cached_element = self._get_cached_element(cache_key)
            if cached_element:
                return cached_element
        
        try:
            from concurrent.futures import ThreadPoolExecutor, TimeoutError
            
            def find_single_xpath(xpath):
                try:
                    return WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                except (TimeoutException, NoSuchElementException):
                    return None
            
            # 并行查找所有XPath
            with ThreadPoolExecutor(max_workers=len(xpaths)) as executor:
                futures = [executor.submit(find_single_xpath, xpath) for xpath in xpaths]
                
                for future in futures:
                    try:
                        result = future.result(timeout=timeout)
                        if result:
                            # 缓存找到的元素
                            if use_cache and cache_key:
                                self._cache_element(cache_key, result)
                            return result
                    except (TimeoutError, Exception):
                        continue
            
            for future in futures:
                try:
                    result = future.result(timeout=timeout)
                    if result:
                        # 缓存找到的元素
                        if use_cache and cache_key:
                            self._cache_element(cache_key, result)
                        return result
                except (TimeoutError, Exception):
                    continue
        
        except Exception as e:
            if not silent:
                self.logger.error(f"元素查找过程中发生错误: {str(e)}")
        
        return None

    def schedule_price_setting(self):
        """安排每天指定时间执行价格设置"""
        now = datetime.now()
        
        # 从GUI获取选择的时间
        selected_time = self.auto_find_time_combobox.get()
        hour = int(selected_time.split(':')[0])
        
        # 同步交易时间到StatusDataManager
        self.status_data.update('trading_info', 'time', selected_time)
        
        # 计算下一个指定时间的时间点（在选择时间的02分执行）
        next_run = now.replace(hour=hour, minute=2, second=0, microsecond=0)
        
        # 如果当前时间已经超过了今天的指定时间，则直接安排到明天
        # 为了确保绝对不会在同一天重复执行，我们检查当前时间是否已经过了指定的小时
        if now.hour >= hour:
            next_run += timedelta(days=1)
        
        # 计算等待时间(毫秒)
        wait_time = (next_run - now).total_seconds() * 1000
        wait_time_hours = wait_time / 3600000
        
        # 设置定时器
        self.set_yes1_no1_default_target_price_timer = self.root.after(int(wait_time), lambda: self.set_yes1_no1_default_target_price())
        self.logger.info(f"✅ \033[34m{round(wait_time_hours,2)}\033[0m小时后开始设置 YES1/NO1 价格为54")

    def on_auto_find_time_changed(self, event=None):
        """当时间选择改变时的处理函数"""
        # 保存新的时间设置到配置文件
        self.save_config()
        
        # 同步交易时间到StatusDataManager
        selected_time = self.auto_find_time_combobox.get()
        self.status_data.update('trading_info', 'time', selected_time)
        
        if hasattr(self, 'set_yes1_no1_default_target_price_timer') and self.set_yes1_no1_default_target_price_timer:
            # 取消当前的定时器
            self.root.after_cancel(self.set_yes1_no1_default_target_price_timer)
            self.logger.info("🔄 设置 YES1/NO1 价格时间已更改，重新安排定时任务")
            # 使用新的时间设置重新安排定时任务，确保使用正确的时间计算
            self.schedule_price_setting()
    
    def set_yes1_no1_default_target_price(self):
        """设置默认目标价格54"""
        
        self.no1_price_entry.delete(0, tk.END)
        self.no1_price_entry.insert(0, "54")
        self.no1_price_entry.configure(foreground='red')
        self.logger.info(f"✅ 设置DOWN1价格为54成功")
    
        self.yes1_price_entry.delete(0, tk.END)
        self.yes1_price_entry.insert(0, "54")
        self.yes1_price_entry.configure(foreground='red')
        self.logger.info(f"✅ 设置UP1价格为54成功")

        # 同步UP1/DOWN1价格设置到StatusDataManager
        self.status_data.update('positions', 'up_positions', [
            {"price": 54},  # UP1设置为54
            {"price": float(self.yes2_price_entry.get())},
            {"price": float(self.yes3_price_entry.get())},
            {"price": float(self.yes4_price_entry.get())}
        ])
        self.status_data.update('positions', 'down_positions', [
            {"price": 54},  # DOWN1设置为54
            {"price": float(self.no2_price_entry.get())},
            {"price": float(self.no3_price_entry.get())},
            {"price": float(self.no4_price_entry.get())}
        ])

        self.close_windows()
        
        # 价格设置完成后，重新安排下一次的价格设置定时任务
        # 使用schedule_price_setting确保与GUI时间选择保持一致
        self.logger.info("🔄 价格设置完成，重新安排下一次定时任务")
        self.schedule_price_setting()
        
    def on_coin_changed(self, event=None):
        """当币种选择改变时的处理函数"""
        # 保存新的币种选择到配置文件
        self.save_config()
        selected_coin = self.coin_combobox.get()
        self.logger.info(f"💰 币种选择已更改为: {selected_coin}")
        
        # 同步币种选择到StatusDataManager
        self.status_data.update('trading_info', 'coin', selected_coin)

    def schedule_auto_find_coin(self):
        """安排每天指定时间执行自动找币"""
        now = datetime.now()
        self.logger.info(f"当前时间: {now}")

        # 计算下一个指定时间的时间点
        next_run = now.replace(hour=0, minute=10, second=0, microsecond=0)
        self.logger.info(f"自动找币下次执行时间: {next_run}")

        if now >= next_run:
            next_run += timedelta(days=1)
        
        # 计算等待时间(毫秒)
        wait_time = (next_run - now).total_seconds() * 1000
        wait_time_hours = wait_time / 3600000
        
        # 设置定时器
        self.schedule_auto_find_coin_timer = self.root.after(int(wait_time), lambda: self.find_54_coin())
        self.logger.info(f"✅ \033[34m{round(wait_time_hours,2)}\033[0m小时后,开始自动找币")
    
    def find_54_coin(self):
        try:
            # 第一步:先点击 CRYPTO 按钮
            try:
                crypto_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, XPathConfig.CRYPTO_BUTTON[0])))
                crypto_button.click()
                self.logger.info(f"✅ 成功点击CRYPTO按钮")

                # 等待CRYPTO按钮点击后的页面加载完成
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                self.logger.info("✅ CRYPTO按钮点击后的页面加载完成")
            except TimeoutException:
                self.logger.error(f"❌ 定位CRYPTO按钮超时")

            # 第二步:点击 DAILY 按钮
            try:
                daily_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, XPathConfig.DAILY_BUTTON[0])))
                daily_button.click()
                self.logger.info(f"✅ 成功点击DAILY按钮")

                # 等待DAILY按钮点击后的页面加载完成
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                self.logger.info("✅ DAILY按钮点击后的页面加载完成")
            except (TimeoutException):
                self.logger.error(f"❌ 定位DAILY按钮超时")
            
            # 第三步:点击目标 URL 按钮,在当前页面打开 URL
            if self.click_today_card():
                self.logger.info(f"✅ 成功点击目标URL按钮")
            
                # 第四步:获取当前 URL并保存到 GUI 和配置文件中
                new_url = self.driver.current_url.split('?', 1)[0].split('#', 1)[0]
                self.logger.info(f"✅ 成功获取到当前URL: {new_url}")
                time.sleep(8)
                
                # 保存当前 URL 到 config
                self.config['website']['url'] = new_url
                self.save_config()
                
                # 保存前,先删除现有的url
                self.url_entry.delete(0, tk.END)
                
                # 把保存到config的url放到self.url_entry中
                self.url_entry.insert(0, new_url)
                
                # 把保存到config的url放到self.trading_pair_label中  
                pair = re.search(r'event/([^?]+)', new_url)
                self.trading_pair_label.config(text=pair.group(1))
                self.logger.info(f"✅ {new_url}:已插入到主界面上并保存到配置文件")
            else:
                self.logger.error(f"❌ 未成功点击目标URL按钮")
                # 继续点击目标 URL 按钮
                if self.click_today_card():
                    self.logger.info(f"✅ 成功点击目标URL按钮")
                else:
                    self.logger.error(f"❌ 未成功点击目标URL按钮")

        except Exception as e:
            self.logger.error(f"自动找币失败.错误信息:{e}")
            
    def click_today_card(self):
        """使用Command/Ctrl+Click点击包含今天日期的卡片,打开新标签页"""
        try:
            # 获取当前日期字符串，比如 "April 18"
            if platform.system() == 'Darwin':  # macOS
                today_str = datetime.now().strftime("%B %-d")  # macOS格式
            else:  # Linux (Ubuntu)
                today_str = datetime.now().strftime("%B %d").replace(" 0", " ")  # Linux格式，去掉前导零
            self.logger.info(f"🔍 当前日期是 {today_str}")

            coin = self.coin_combobox.get()
            self.logger.info(f"🔍 选择的币种是 {coin}")

            card = None

            # 获取所有含 "Bitcoin Up or Down on" 的卡片元素
            try:
                if coin == 'BTC':
                    card = self.driver.find_element(By.XPATH, XPathConfig.SEARCH_BTC_BUTTON[0])
                elif coin == 'ETH':
                    card = self.driver.find_element(By.XPATH, XPathConfig.SEARCH_ETH_BUTTON[0])
                elif coin == 'SOL':
                    card = self.driver.find_element(By.XPATH, XPathConfig.SEARCH_SOL_BUTTON[0])
                
            except NoSuchElementException:
                try:
                    if coin == 'BTC':
                        card = self._find_element_with_retry(XPathConfig.SEARCH_BTC_BUTTON,timeout=3,silent=True)
                    elif coin == 'ETH':
                        card = self._find_element_with_retry(XPathConfig.SEARCH_ETH_BUTTON,timeout=3,silent=True)
                    elif coin == 'SOL':
                        card = self._find_element_with_retry(XPathConfig.SEARCH_SOL_BUTTON,timeout=3,silent=True)
                except NoSuchElementException:
                    card = None

            self.logger.info(f"🔍 找到的卡片文本: {card.text}")

            if today_str in card.text:
                self.logger.info(f"\033[34m✅ 找到匹配日期 {today_str} 的卡片: {card.text}\033[0m")

                # Command 键（macOS）或 Control 键（Windows/Linux）
                #modifier_key = Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL

                # 使用 ActionChains 执行 Command/Ctrl + Click
                #actions = ActionChains(self.driver)
                #actions.key_down(modifier_key).click(card).key_up(modifier_key).perform()

                # 直接点击元素
                card.click()
                self.logger.info(f"\033[34m✅ 成功点击链接！{card.text}\033[0m")

                # 等待目标URL按钮点击后的页面加载完成
                WebDriverWait(self.driver, 20).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                self.logger.info(f"✅ {card.text}页面加载完成")
                return True
            else:
                self.logger.warning("\033[31m❌ 没有找到包含今天日期的链接\033[0m")
                return False

        except Exception as e:
            self.logger.error(f"查找并点击今天日期卡片失败: {str(e)}")
            return False

    def get_cash_value(self):
        """获取当前CASH值"""
        for i in range(3):
            try:
                # 获取当前CASH值
                self.logger.info(f"尝试获取CASH值,第 {i + 1} 次")
                try:
                    cash_element = self.driver.find_element(By.XPATH, XPathConfig.CASH_VALUE[0])
                except (NoSuchElementException, StaleElementReferenceException):
                    cash_element = self._find_element_with_retry(XPathConfig.CASH_VALUE, timeout=2, silent=True)
                    
                if cash_element:
                    cash_value = cash_element.text
                else:
                    self.logger.warning("无法找到CASH值元素")
                    return
                
                # 使用正则表达式提取数字
                cash_match = re.search(r'\$?([\d,]+\.?\d*)', cash_value)

                if not cash_match:
                    self.logger.error("❌ 无法从Cash值中提取数字")
                    return

                # 移除逗号并转换为浮点数
                self.zero_time_cash_value = round(float(cash_match.group(1).replace(',', '')), 2)
                self.zero_time_cash_label.config(text=f"{self.zero_time_cash_value}")
                self.logger.info(f"✅ 获取到原始CASH值:\033[34m${self.zero_time_cash_value}\033[0m")
                
                # 同步当天本金数据到StatusDataManager
                self.status_data.update('account', 'zero_time_cash', str(self.zero_time_cash_value))

                # 设置 YES/NO 金额,延迟5秒确保数据稳定
                self.root.after(5000, self.schedule_update_amount)
                self.logger.info("✅ \033[34m设置 YES/NO 金额成功!\033[0m")
                return
            except Exception as e:
                self.logger.warning(f"⚠️ 第 {i + 1} 次尝试失败: {str(e)}")
                time.sleep(1)
        self.logger.error("❌ 获取CASH值失败,已重试3次仍未成功")

    def schedule_get_zero_time_cash(self):
        """定时获取零点CASH值"""
        now = datetime.now()
        self.logger.info(f"当前时间: {now}")
        # 计算下一个指定时间的时间点
        next_run = now.replace(hour=0, minute=15, second=0, microsecond=0)
        self.logger.info(f"获取 0 点 CASH 值下次执行时间: {next_run}")
        if now >= next_run:
            next_run += timedelta(days=1)
        
        # 计算等待时间(毫秒)
        wait_time = (next_run - now).total_seconds() * 1000
        wait_time_hours = wait_time / 3600000
        
        # 设置定时器
        self.get_zero_time_cash_timer = self.root.after(int(wait_time), self.get_zero_time_cash)
        self.logger.info(f"✅ \033[34m{round(wait_time_hours,2)}\033[0m小时后,开始获取 0 点 CASH 值")

    def get_zero_time_cash(self):
        """获取币安BTC实时价格,并在中国时区00:00触发"""
        # 找币之前先查看是否有持仓
        if self.find_position_label_down():
            self.logger.info("✅ 有DOWN持仓,卖出 DOWN 持仓")
            self.only_sell_down()
        
        if self.find_position_label_up():
            self.logger.info("✅ 有UP持仓,卖出 UP 持仓")
            self.only_sell_up()

        try:
            # 获取零点CASH值
            try:
                cash_element = self.driver.find_element(By.XPATH, XPathConfig.CASH_VALUE[0])
            except (NoSuchElementException, StaleElementReferenceException):
                cash_element = self._find_element_with_retry(XPathConfig.CASH_VALUE, timeout=2, silent=True)
                
            if cash_element:
                cash_value = cash_element.text
            else:
                self.logger.warning("无法找到CASH值元素")
                return
            
            # 使用正则表达式提取数字
            cash_match = re.search(r'\$?([\d,]+\.?\d*)', cash_value)

            if not cash_match:
                self.logger.error("❌ 无法从Cash值中提取数字")
                return

            # 移除逗号并转换为浮点数
            self.zero_time_cash_value = round(float(cash_match.group(1).replace(',', '')), 2)
            self.zero_time_cash_label.config(text=f"{self.zero_time_cash_value}")
            self.logger.info(f"✅ 获取到原始CASH值:\033[34m${self.zero_time_cash_value}\033[0m")
            
            # 同步零点现金数据到StatusDataManager
            self.status_data.update('account', 'zero_time_cash', str(self.zero_time_cash_value))

            # 设置 YES/NO 金额,延迟5秒确保数据稳定
            self.root.after(5000, self.schedule_update_amount)
            self.logger.info("✅ \033[34m零点 10 分设置 YES/NO 金额成功!\033[0m")

            # 设置 YES1/NO1价格为 0
            self.yes1_price_entry.delete(0, tk.END)
            self.yes1_price_entry.insert(0, "0")
            self.no1_price_entry.delete(0, tk.END)
            self.no1_price_entry.insert(0, "0")
            self.logger.info("✅ \033[34m零点 5 分设置 YES/NO 价格为 0 成功!\033[0m")

            # 同步UP1/DOWN1价格重置到StatusDataManager
            self.status_data.update('positions', 'up_positions', [
                {"price": 0},  # UP1重置为0
                {"price": float(self.yes2_price_entry.get())},
                {"price": float(self.yes3_price_entry.get())},
                {"price": float(self.yes4_price_entry.get())}
            ])
            self.status_data.update('positions', 'down_positions', [
                {"price": 0},  # DOWN1重置为0
                {"price": float(self.no2_price_entry.get())},
                {"price": float(self.no3_price_entry.get())},
                {"price": float(self.no4_price_entry.get())}
            ])

            # 读取 GUI 上的交易次数
            trade_count = self.trade_count_label.cget("text")
            self.logger.info(f"最后一次交易次数: {trade_count}")

            # 真实交易了的次数
            self.last_trade_count = 22 - int(trade_count)
            self.logger.info(f"真实交易了的次数: {self.last_trade_count}")
            
            # 设置self.trade_count为 22
            self.trade_count_label.config(text="22")

        except Exception as e:
            self.logger.error(f"获取零点CASH值时发生错误: {str(e)}")
        finally:
            # 计算下一个00:10的时间
            now = datetime.now()
            tomorrow = now.replace(hour=0, minute=5, second=0, microsecond=0) + timedelta(days=1)
            seconds_until_midnight = (tomorrow - now).total_seconds()

            # 取消已有的定时器（如果存在）
            if hasattr(self, 'get_zero_time_cash_timer') and self.get_zero_time_cash_timer:
                self.root.after_cancel(self.get_zero_time_cash_timer)

            # 设置下一次执行的定时器
            if self.running and not self.stop_event.is_set():
                self.get_zero_time_cash_timer = threading.Timer(seconds_until_midnight, self.get_zero_time_cash)
                self.get_zero_time_cash_timer.daemon = True
                self.get_zero_time_cash_timer.start()
                self.logger.info(f"✅ \033[34m{round(seconds_until_midnight / 3600,2)}\033[0m小时后再次获取 \033[34mCASH\033[0m 值")
    
    def get_binance_zero_time_price(self):
        """获取币安BTC实时价格,并在中国时区00:00触发。此方法在threading.Timer的线程中执行。"""   
        # 先把所有 YES/NO 价格设置为 0
        for i in range(1,6):  # 1-5
            yes_entry = getattr(self, f'yes{i}_price_entry', None)
            no_entry = getattr(self, f'no{i}_price_entry', None)

            if yes_entry:
                yes_entry.delete(0, tk.END)
                yes_entry.insert(0, "0")
                yes_entry.configure(foreground='black')
                # 同步YES价格到StatusDataManager
                self.status_data.update('positions', f'yes{i}_price', "0")
            if no_entry:
                no_entry.delete(0, tk.END)
                no_entry.insert(0, "0")
                no_entry.configure(foreground='black')
                # 同步NO价格到StatusDataManager
                self.status_data.update('positions', f'no{i}_price', "0")

        api_data = None
        coin_form_websocket = ""
        max_retries = 10 # 最多重试次数
        retry_delay = 2  # 重试间隔（秒）

        for attempt in range(max_retries):
            try:
                # 1. 获取币种信息
                selected_coin = self.coin_combobox.get() 
                coin_form_websocket = selected_coin + 'USDT'

                # --- 新增 websocket 获取价格逻辑 ---
                ws_url = f"wss://stream.binance.com:9443/ws/{coin_form_websocket.lower()}@ticker"
                price_holder = {'price': None}
                ws_error = {'error': None}

                def on_message(ws, message):
                    try:
                        data = json.loads(message)
                        price = round(float(data['c']), 3)
                        price_holder['price'] = price
                        ws.close()  # 收到一次价格后立即关闭连接
                    except Exception as e:
                        ws_error['error'] = e
                        ws.close()
                def on_error(ws, error):
                    ws_error['error'] = error
                    ws.close()
                def on_close(ws, close_status_code, close_msg):
                    pass
                # 获取币安价格
                ws = websocket.WebSocketApp(ws_url, on_message=on_message, on_error=on_error, on_close=on_close)
                ws_thread = threading.Thread(target=ws.run_forever)
                ws_thread.start()
                
                # 等待 websocket 获取到价格或超时
                ws_thread.join(timeout=5)
                if ws_error['error']:
                    raise Exception(ws_error['error'])
                if price_holder['price'] is None:
                    raise Exception("WebSocket 未能获取到价格")
                price = price_holder['price']
                # --- websocket 获取价格逻辑结束 ---

                api_data = {"price": price, "coin": coin_form_websocket, "original_selected_coin": selected_coin}
                self.logger.info(f"✅ ({attempt + 1}/{max_retries}) 成功获取到币安 \033[34m{api_data['coin']}\033[0m 价格: \033[34m{api_data['price']}\033[0m")
                
                break # 获取成功，跳出重试循环

            except Exception as e:
                self.logger.warning(f"❌ (尝试 {attempt + 1}/{max_retries}) 获取币安 \033[34m{coin_form_websocket}\033[0m 价格时发生错误: {e}")
                if attempt < max_retries - 1: # 如果不是最后一次尝试
                    self.logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay) # 等待后重试
                else: # 最后一次尝试仍然失败
                    self.logger.error(f"❌ 获取币安 \033[34m{coin_form_websocket}\033[0m 价格失败，已达到最大重试次数 ({max_retries})。")
        
        # 3. 如果成功获取数据 (即try块没有异常且api_data不为None)，则安排GUI更新到主线程
        if api_data:
            def update_gui():
                try:
                    # 获取到币安价格,并更新到GUI
                    self.zero_time_price = api_data["price"]
                    self.binance_zero_price_label.config(text=f"{self.zero_time_price}")
                    
                    # 同步零点价格数据到StatusDataManager
                    self.status_data.update('prices', 'binance_zero_time', str(self.zero_time_price))
                except Exception as e_gui:
                    self.logger.debug(f"❌ 更新零点价格GUI时出错: {e_gui}")
            
            self.root.after(0, update_gui)

        # 设置定时器,每天00:00获取一次币安价格
        now = datetime.now()
        next_run_time = now.replace(hour=0, minute=0, second=59, microsecond=0)
        if now >= next_run_time:
            next_run_time += timedelta(days=1)

        seconds_until_next_run = (next_run_time - now).total_seconds()

        if hasattr(self, 'binance_zero_price_timer_thread') and self.binance_zero_price_timer and self.binance_zero_price_timer.is_alive():
            self.binance_zero_price_timer.cancel()

        if self.running and not self.stop_event.is_set():
            coin_for_next_log = self.coin_combobox.get() + 'USDT'
            self.binance_zero_price_timer = threading.Timer(seconds_until_next_run, self.get_binance_zero_time_price)
            self.binance_zero_price_timer.daemon = True
            self.binance_zero_price_timer.start()
            self.logger.info(f"✅ \033[34m{round(seconds_until_next_run / 3600,2)}\033[0m 小时后重新获取{coin_for_next_log} 零点价格")
    
    def get_binance_price_websocket(self):
        """获取币安价格,并计算上涨或下跌幅度"""
        # 获取币种信息
        selected_coin = self.coin_combobox.get()
        coin_form_websocket = selected_coin.lower() + 'usdt'
        # 获取币安价格
        ws_url = f"wss://stream.binance.com:9443/ws/{coin_form_websocket}@ticker"
        
        # 添加连接状态跟踪
        connection_attempts = 0
        first_connection = True

        def on_open(ws):
            nonlocal connection_attempts, first_connection
            if first_connection:
                self.logger.info(f"✅ WebSocket 连接成功建立 - {coin_form_websocket.upper()}")
                first_connection = False
            else:
                self.logger.info(f"🔄 WebSocket 重连成功 - {coin_form_websocket.upper()} (第{connection_attempts}次重连)")

        def on_message(ws, message):
            try:
                data = json.loads(message)
                # 获取最新成交价格
                now_price = round(float(data['c']), 3)
                # 计算上涨或下跌幅度
                zero_time_price_for_calc = getattr(self, 'zero_time_price', None)
                binance_rate_text = "--"
                rate_color = "blue"

                if zero_time_price_for_calc:
                    binance_rate = ((now_price - zero_time_price_for_calc) / zero_time_price_for_calc) * 100
                    binance_rate_text = f"{binance_rate:.3f}"
                    rate_color = "#1AAD19" if binance_rate >= 0 else "red"

                def update_gui():
                    try:
                        # 更新实时价格标签并同步到StatusDataManager
                        self.binance_now_price_label.config(text=f"{now_price}")
                        self.status_data.update('prices', 'binance_current', now_price)
                        
                        # 更新涨跌幅标签并同步到StatusDataManager
                        self.binance_rate_label.config(
                            text=f"{binance_rate_text}",
                            foreground=rate_color,
                            font=("Arial", 18, "bold")
                        )
                        self.status_data.update('prices', 'price_change_rate', binance_rate_text)
                    except Exception as e:
                        self.logger.debug("❌ 更新GUI时发生错误:", e)

                self.root.after(0, update_gui)
            except Exception as e:
                self.logger.warning(f"WebSocket 消息处理异常: {e}")

        def on_error(ws, error):
            self.logger.warning(f"WebSocket 错误: {error}")

        def on_close(ws, close_status_code, close_msg):
            self.logger.info("WebSocket 连接已关闭")

        def run_ws():
            nonlocal connection_attempts
            while self.running and not self.stop_event.is_set():
                try:
                    if connection_attempts > 0:
                        self.logger.info(f"🔄 尝试重连 WebSocket - {coin_form_websocket.upper()} (第{connection_attempts}次)")
                    
                    ws = websocket.WebSocketApp(ws_url, 
                                              on_open=on_open,
                                              on_message=on_message, 
                                              on_error=on_error, 
                                              on_close=on_close)
                    ws.run_forever()
                except Exception as e:
                    self.logger.warning(f"WebSocket 主循环异常: {e}")
                
                connection_attempts += 1
                if self.running and not self.stop_event.is_set():
                    time.sleep(5)  # 出错后延迟重连

        self.ws_thread = threading.Thread(target=run_ws, daemon=True)
        self.ws_thread.start()

    def comparison_binance_price(self):
        """设置定时器以在每天23点比较币安价格和当前价格"""
        now = datetime.now()
        # 设置目标时间为当天的23点
        target_time_today = now.replace(hour=23, minute=30, second=0, microsecond=0)

        if now < target_time_today:
            # 如果当前时间早于今天的23点，则在今天的23点执行
            next_run_time = target_time_today
        else:
            # 如果当前时间晚于或等于今天的23点，则在明天的23点执行
            next_run_time = target_time_today + timedelta(days=1)

        seconds_until_next_run = (next_run_time - now).total_seconds()
        # 取消已有的定时器（如果存在）
        if hasattr(self, 'comparison_binance_price_timer') and self.comparison_binance_price_timer:
            self.root.after_cancel(self.comparison_binance_price_timer)

        # 设置下一次执行的定时器
        selected_coin = self.coin_combobox.get()
        self.comparison_binance_price_timer = threading.Timer(seconds_until_next_run, self._perform_price_comparison)
        self.comparison_binance_price_timer.daemon = True
        self.comparison_binance_price_timer.start()
        self.logger.info(f"\033[34m{round(seconds_until_next_run / 3600,2)}\033[0m小时后比较\033[34m{selected_coin}USDT\033[0m币安价格")

    def _perform_price_comparison(self):
        """执行价格比较"""
        try:
            # 获取当前选择的币种
            selected_coin = self.coin_combobox.get()
            # 获取0点当天的币安价格
            zero_time_price = round(float(self.binance_zero_price_label.cget('text').replace('$', '')),2)
            # 获取当前价格
            now_price = round(float(self.binance_now_price_label.cget('text').replace('$', '')),2)
            # 计算上涨或下跌幅度
            price_change = round(((now_price - zero_time_price) / zero_time_price) * 100,3)
            # 比较价格
            if 0 <= price_change <= 0.004 or -0.004 <= price_change <= 0:
                price_change = f"{round(price_change,3)}%"
                self.logger.info(f"✅ \033[34m{selected_coin}USDT当前价格上涨或下跌幅度小于{price_change},请立即关注\033[0m")
                self.send_trade_email(
                                trade_type=f"{selected_coin}USDT当前价格上涨或下跌幅度小于{price_change}",
                                price=zero_time_price,
                                amount=now_price,
                                trade_count=price_change,
                                shares=0,
                                cash_value=0,
                                portfolio_value=0
                            )
            
        except Exception as e:
            pass
        finally:
            self.comparison_binance_price()

    def night_auto_sell_check(self):
        """
        夜间自动卖出检查函数
        在1点到上午6点时间内,如果self.trade_count小于等于14,则卖出仓位
        """
        try:
            # 获取当前时间
            now = datetime.now()
            current_hour = now.hour
            
            # 检查是否在1点到8点之间（包含1点，不包含8点）
            if 1 <= current_hour <= 8:
                #self.logger.info(f"✅ 当前时间 {now.strftime('%H:%M:%S')} 在夜间时段(01:00-08:00)内")
                
                # 检查交易次数是否小于等于14
                if self.trade_count <= 14:
                    self.logger.info(f"✅ 交易次数 {self.trade_count} <= 14,执行夜间自动卖出仓位")
                    
                    # 执行卖出仓位操作
                    self.click_positions_sell_and_sell_confirm_and_accept()
                    self.logger.info(f"✅ 夜间自动卖出仓位执行完成")

                    # 设置 YES1-4/NO1-4 价格为 0
                    for i in range(1,6):  # 1-5
                        yes_entry = getattr(self, f'yes{i}_price_entry', None)
                        no_entry = getattr(self, f'no{i}_price_entry', None)

                        if yes_entry:
                            yes_entry.delete(0, tk.END)
                            yes_entry.insert(0, "0")
                            yes_entry.configure(foreground='black')
                        if no_entry:
                            no_entry.delete(0, tk.END)
                            no_entry.insert(0, "0")
                            no_entry.configure(foreground='black')

                    # 设置 YES1/NO1 价格为默认值
                    self.no1_price_entry.delete(0, tk.END)
                    self.no1_price_entry.insert(0, str(self.default_target_price))
                    self.no1_price_entry.configure(foreground='red')
                    self.logger.info(f"\033[34m✅ 设置NO1价格{self.default_target_price}成功\033[0m")
                
                    self.yes1_price_entry.delete(0, tk.END)
                    self.yes1_price_entry.insert(0, str(self.default_target_price))
                    self.yes1_price_entry.configure(foreground='red')
                    self.logger.info(f"\033[34m✅ 设置YES1价格{self.default_target_price}成功\033[0m")

                    # 交易次数恢复到初始值
                    self.trade_count = 22
                    self.trade_count_label.config(text=str(self.trade_count))
                    self.logger.info(f"✅ 交易次数已恢复到初始值: {self.trade_count}")
                        
                else:
                    self.logger.info(f"ℹ️ 交易次数 {self.trade_count} > 14,不执行夜间自动卖出")
                
        except Exception as e:
            self.logger.error(f"❌ 夜间自动卖出检查失败: {str(e)}")

    def schedule_night_auto_sell_check(self):
        """
        调度夜间自动卖出检查
        每30分钟执行一次检查
        """
        #self.logger.info("\033[34m✅ 启动夜间自动卖出检查!\033[0m")
        try:
            # 执行夜间自动卖出检查
            self.night_auto_sell_check()
            
            # 设置下一次检查（30分钟后）
            if self.running and not self.stop_event.is_set():
                self.night_auto_sell_timer = self.root.after(30 * 60 * 1000, self.schedule_night_auto_sell_check)  # 30分钟 = 30 * 60 * 1000毫秒
                #self.logger.info("✅ 已设置30分钟后进行下一次夜间自动卖出检查")
                
        except Exception as e:
            self.logger.error(f"❌ 调度夜间自动卖出检查失败: {str(e)}")
            # 即使出错也要设置下一次检查
            if self.running and not self.stop_event.is_set():
                 self.night_auto_sell_timer = self.root.after(30 * 60 * 1000, self.schedule_night_auto_sell_check)

    def auto_use_swap(self):
        """
        自动Swap管理功能
        当系统可用内存少于400MB时自动启动swap
        """
        try:
            # 检查操作系统，只在Linux系统上执行
            if platform.system() != 'Linux':
                self.logger.debug("🔍 非Linux系统，跳过Swap检查")
                return
            
            # 设置触发阈值（单位：KB）
            THRESHOLD_KB = 200 * 1024  # 200MB
            
            # 检查当前是否已有swap
            try:
                result = subprocess.run(['swapon', '--noheadings', '--show'], 
                                      capture_output=True, text=True, timeout=10)
                if '/swapfile' in result.stdout:
                    self.logger.info("✅ Swap已启用，停止定时检查")
                    # 取消定时器，停止继续检查
                    if hasattr(self, 'auto_use_swap_timer') and self.auto_use_swap_timer:
                        self.root.after_cancel(self.auto_use_swap_timer)
                        self.auto_use_swap_timer = None
                        self.logger.info("🛑 已停止自动Swap检查定时器")
                    return
            except Exception as e:
                self.logger.warning(f"检查Swap状态失败: {e}")
            
            # 获取当前可用内存（单位：KB）
            try:
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if line.startswith('MemAvailable:'):
                            available_kb = int(line.split()[1])
                            break
                    else:
                        self.logger.warning("无法获取MemAvailable信息")
                        return
                        
                available_mb = available_kb // 1024
                #self.logger.info(f"🔍 当前可用内存: {available_mb} MB")
                
                # 判断是否小于阈值
                if available_kb < THRESHOLD_KB:
                    self.logger.info(f"⚠️ 可用内存低于{available_mb}MB,开始创建Swap...")
                    
                    # 创建swap文件
                    commands = [
                        ['sudo', 'fallocate', '-l', '2G', '/swapfile'],
                        ['sudo', 'chmod', '600', '/swapfile'],
                        ['sudo', 'mkswap', '/swapfile'],
                        ['sudo', 'swapon', '/swapfile']
                    ]
                    
                    for cmd in commands:
                        try:
                            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                            if result.returncode != 0:
                                self.logger.error(f"命令执行失败: {' '.join(cmd)}, 错误: {result.stderr}")
                                return
                        except subprocess.TimeoutExpired:
                            self.logger.error(f"命令执行超时: {' '.join(cmd)}")
                            return
                        except Exception as e:
                            self.logger.error(f"命令执行异常: {' '.join(cmd)}, 错误: {e}")
                            return
                    
                    # 检查/etc/fstab中是否已有swap配置
                    try:
                        with open('/etc/fstab', 'r') as f:
                            fstab_content = f.read()
                        
                        if '/swapfile' not in fstab_content:
                            # 添加开机自动挂载
                            subprocess.run(['sudo', 'sh', '-c', 
                                          'echo "/swapfile none swap sw 0 0" >> /etc/fstab'], 
                                         timeout=10)
                            self.logger.info("✅ 已添加Swap到/etc/fstab")
                    except Exception as e:
                        self.logger.warning(f"配置/etc/fstab失败: {e}")
                    
                    # 调整swappiness
                    try:
                        subprocess.run(['sudo', 'sysctl', 'vm.swappiness=10'], timeout=10)
                        subprocess.run(['sudo', 'sh', '-c', 
                                      'echo "vm.swappiness=10" >> /etc/sysctl.conf'], 
                                     timeout=10)
                        self.logger.info("✅ 已调整vm.swappiness=10")
                    except Exception as e:
                        self.logger.warning(f"调整swappiness失败: {e}")
                    
                    self.logger.info("🎉 Swap启用完成，共2GB")
                    
            except Exception as e:
                self.logger.error(f"获取内存信息失败: {e}")
                
        except Exception as e:
            self.logger.error(f"❌ 自动Swap管理失败: {str(e)}")

    def schedule_auto_use_swap(self):
        """
        调度自动Swap检查
        每30分钟执行一次检查
        """
        try:
            # 执行Swap检查
            self.auto_use_swap()
            
            # 只有在定时器未被取消的情况下才设置下一次检查
            if (self.running and not self.stop_event.is_set() and 
                hasattr(self, 'auto_use_swap_timer') and self.auto_use_swap_timer is not None):
                self.auto_use_swap_timer = self.root.after(60 * 60 * 1000, self.schedule_auto_use_swap)  # 30分钟 = 30 * 60 * 1000毫秒
            
        except Exception as e:
            self.logger.error(f"❌ 调度自动Swap检查失败: {str(e)}")
            # 即使出错也要设置下一次检查（但要检查定时器状态）
            if (self.running and not self.stop_event.is_set() and 
                hasattr(self, 'auto_use_swap_timer') and self.auto_use_swap_timer is not None):
                self.auto_use_swap_timer = self.root.after(60 * 60 * 1000, self.schedule_auto_use_swap)

    def schedule_clear_chrome_mem_cache(self):
        """
        调度清除Chrome内存缓存
        每60分钟执行一次检查
        """
        try:
            # 执行清除内存缓存
            self.clear_chrome_mem_cache()
            
            # 只有在定时器未被取消的情况下才设置下一次检查
            if (self.running and not self.stop_event.is_set() and 
                hasattr(self, 'clear_chrome_mem_cache_timer') and self.clear_chrome_mem_cache_timer is not None):
                self.clear_chrome_mem_cache_timer = self.root.after(60 * 60 * 1000, self.schedule_clear_chrome_mem_cache)  # 60分钟 = 60 * 60 * 1000毫秒
            
        except Exception as e:
            self.logger.error(f"❌ 调度清除Chrome内存缓存失败: {str(e)}")
            # 即使出错也要设置下一次检查（但要检查定时器状态）
            if (self.running and not self.stop_event.is_set() and 
                hasattr(self, 'clear_chrome_mem_cache_timer') and self.clear_chrome_mem_cache_timer is not None):
                self.clear_chrome_mem_cache_timer = self.root.after(60 * 60 * 1000, self.schedule_clear_chrome_mem_cache)

    def clear_chrome_mem_cache(self):
        # 关闭所有 Chrome 和 chromedriver 进程
        # 设置触发阈值（单位：KB）
        THRESHOLD_KB = 200 * 1024  # 200MB

        # 获取当前可用内存（单位：KB）
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemAvailable:'):
                        available_kb = int(line.split()[1])
                        break
                else:
                    self.logger.warning("无法获取MemAvailable信息")
                    return
            
            # 判断是否小于阈值
            if available_kb < THRESHOLD_KB:
                self.logger.info(f"\033[31m可用内存低于{THRESHOLD_KB / 1024}MB,重启 CHROME\033[0m")
                
                system = platform.system()
                if system == "Windows":
                    subprocess.run("taskkill /f /im chrome.exe", shell=True)
                    subprocess.run("taskkill /f /im chromedriver.exe", shell=True)
                elif system == "Darwin":  # macOS
                    subprocess.run("pkill -9 'Google Chrome'", shell=True)
                    subprocess.run("pkill -9 chromedriver", shell=True)
                else:  # Linux
                    subprocess.run("pkill -9 chrome", shell=True)
                    subprocess.run("pkill -9 chromedriver", shell=True)

                    # 发送交易邮件
                    self.send_trade_email(
                        trade_type="可用内存低于300MB,已经重启 CHROME!",
                        price=self.price,
                        amount=self.amount,
                        shares=self.shares,
                        trade_count=self.buy_count,
                        cash_value=self.cash_value,
                        portfolio_value=self.portfolio_value
                    )
                # 删除真正的缓存文件夹：Cache/Cache_Data
                cache_data_path = os.path.expanduser("~/ChromeDebug/Default/Cache/Cache_Data")
                if os.path.exists(cache_data_path):
                    shutil.rmtree(cache_data_path)
                    self.logger.info("✅ 已删除 Cache_Data 缓存")
                else:
                    self.logger.info("ℹ️ 未找到 Cache_Data 缓存目录")

        except Exception as e:
            self.logger.error(f"❌ 关闭Chrome进程失败: {str(e)}")

    def schedule_record_and_show_cash(self):
        """安排每天 0:30 记录现金到CSV"""
        now = datetime.now()
        next_run = now.replace(hour=0, minute=30, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)
        wait_time = (next_run - now).total_seconds()
        self.record_and_show_cash_timer = threading.Timer(wait_time, self.record_cash_daily)
        self.record_and_show_cash_timer.daemon = True
        self.record_and_show_cash_timer.start()
        self.logger.info(f"✅ \033[32m已安排在 {next_run.strftime('%Y-%m-%d %H:%M:%S')} 记录利润\033[0m")

    def load_cash_history(self):
        """启动时从CSV加载全部历史记录, 兼容旧4/6列并补齐为7列(日期,Cash,利润,利润率,总利润,总利润率,交易次数)"""
        history = []
        try:
            if os.path.exists(self.csv_file):
                with open(self.csv_file, newline="", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    cumulative_profit = 0.0
                    first_cash = None
                    line_number = 0
                    for row in reader:
                        line_number += 1
                        try:
                            if len(row) >= 4:
                                date_str = row[0].strip()
                                
                                # 验证并转换数值，添加详细的错误信息
                                try:
                                    cash = float(row[1].strip())
                                except ValueError as ve:
                                    self.logger.error(f"第{line_number}行现金数值转换失败: '{row[1]}' - {ve}")
                                    continue
                                    
                                try:
                                    profit = float(row[2].strip())
                                except ValueError as ve:
                                    self.logger.error(f"第{line_number}行利润数值转换失败: '{row[2]}' - {ve}")
                                    continue
                                    
                                try:
                                    # 处理百分比格式的利润率
                                    profit_rate_str = row[3].strip()
                                    if profit_rate_str.endswith('%'):
                                        profit_rate = float(profit_rate_str.rstrip('%')) / 100
                                    else:
                                        profit_rate = float(profit_rate_str)
                                except ValueError as ve:
                                    self.logger.error(f"第{line_number}行利润率数值转换失败: '{row[3]}' - {ve}")
                                    continue
                                
                                if first_cash is None:
                                    first_cash = cash
                                    
                                # 如果已有6列或7列，直接采用并更新累计上下文
                                if len(row) >= 6:
                                    try:
                                        total_profit = float(row[4].strip())
                                        # 处理百分比格式的总利润率
                                        total_profit_rate_str = row[5].strip()
                                        if total_profit_rate_str.endswith('%'):
                                            total_profit_rate = float(total_profit_rate_str.rstrip('%')) / 100
                                        else:
                                            total_profit_rate = float(total_profit_rate_str)
                                        cumulative_profit = total_profit
                                    except ValueError as ve:
                                        self.logger.error(f"第{line_number}行总利润数值转换失败: '{row[4]}' 或 '{row[5]}' - {ve}")
                                        # 使用计算值作为备用
                                        cumulative_profit += profit
                                        total_profit = cumulative_profit
                                        total_profit_rate = (total_profit / first_cash) if first_cash else 0.0
                                else:
                                    cumulative_profit += profit
                                    total_profit = cumulative_profit
                                    total_profit_rate = (total_profit / first_cash) if first_cash else 0.0
                                    
                                # 第7列：交易次数
                                if len(row) >= 7:
                                    trade_times = row[6].strip()
                                else:
                                    trade_times = ""
                                    
                                history.append([
                                date_str,
                                f"{cash:.2f}",
                                f"{profit:.2f}",
                                f"{profit_rate*100:.2f}%",
                                f"{total_profit:.2f}",
                                f"{total_profit_rate*100:.2f}%",
                                trade_times
                            ])
                            else:
                                self.logger.warning(f"第{line_number}行数据列数不足: {len(row)}列, 需要至少4列")
                        except Exception as row_error:
                            self.logger.error(f"第{line_number}行数据处理失败: {row} - {row_error}")
                            continue
        except Exception as e:
            self.logger.error(f"加载历史CSV失败: {e}")
            # 如果CSV文件损坏，尝试修复
            if os.path.exists(self.csv_file):
                self.logger.info("尝试修复损坏的CSV文件...")
                try:
                    self.repair_csv_file()
                    # 修复后重新尝试加载
                    self.logger.info("CSV文件修复完成，重新尝试加载...")
                    return self.load_cash_history()
                except Exception as repair_error:
                    self.logger.error(f"CSV文件修复失败: {repair_error}")
                    # 创建备份并重新开始
                    backup_file = f"{self.csv_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    try:
                        shutil.copy2(self.csv_file, backup_file)
                        self.logger.info(f"已创建损坏CSV文件的备份: {backup_file}")
                    except Exception as backup_error:
                        self.logger.error(f"创建备份文件失败: {backup_error}")
        return history

    def repair_csv_file(self):
        """修复损坏的CSV文件，移除无效行并重建文件"""
        if not os.path.exists(self.csv_file):
            self.logger.info("CSV文件不存在，无需修复")
            return
            
        # 检查是否已经标准化过
        standardized_flag_file = f"{self.csv_file}.standardized"
        if os.path.exists(standardized_flag_file):
            # 检查CSV文件的修改时间是否晚于标记文件
            csv_mtime = os.path.getmtime(self.csv_file)
            flag_mtime = os.path.getmtime(standardized_flag_file)
            if csv_mtime <= flag_mtime:
                self.logger.info("CSV文件已标准化，跳过检查")
                return
            else:
                self.logger.info("CSV文件已更新，重新检查格式")
            
        valid_rows = []
        invalid_rows = []
        has_format_changes = False  # 标记是否有格式变更
        
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                line_number = 0
                for row in reader:
                    line_number += 1
                    try:
                        if len(row) >= 4:
                            # 验证每个数值字段
                            original_date_str = row[0].strip()
                            date_str = original_date_str
                            cash = float(row[1].strip())
                            profit = float(row[2].strip())
                            
                            # 处理百分比格式的利润率，特别处理被错误连接的情况
                            profit_rate_str = row[3].strip()
                            
                            # 检查是否包含日期信息（如 '0.00292025-08-18'）
                            if re.search(r'\d{4}-\d{2}-\d{2}', profit_rate_str):
                                # 尝试分离利润率和日期
                                match = re.match(r'([\d\.%-]+)(\d{4}-\d{2}-\d{2}.*)', profit_rate_str)
                                if match:
                                    profit_rate_str = match.group(1)
                                    self.logger.warning(f"第{line_number}行利润率字段包含日期信息，已分离: '{row[3]}' -> '{profit_rate_str}'")
                                    has_format_changes = True
                            
                            if profit_rate_str.endswith('%'):
                                profit_rate = float(profit_rate_str.rstrip('%')) / 100
                            else:
                                profit_rate = float(profit_rate_str)
                            
                            # 验证并标准化日期格式
                            try:
                                # 尝试标准格式 YYYY-MM-DD
                                parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
                            except ValueError:
                                try:
                                    # 尝试斜杠格式 YYYY/M/D 或 YYYY/MM/DD
                                    parsed_date = datetime.strptime(date_str, '%Y/%m/%d')
                                    # 标准化为 YYYY-MM-DD 格式
                                    date_str = parsed_date.strftime('%Y-%m-%d')
                                    self.logger.info(f"第{line_number}行日期格式已标准化: '{original_date_str}' -> '{date_str}'")
                                    has_format_changes = True
                                except ValueError:
                                    try:
                                        # 尝试其他可能的格式
                                        parsed_date = datetime.strptime(date_str, '%Y/%#m/%#d')  # Windows格式
                                        date_str = parsed_date.strftime('%Y-%m-%d')
                                        self.logger.info(f"第{line_number}行日期格式已标准化: '{original_date_str}' -> '{date_str}'")
                                        has_format_changes = True
                                    except ValueError:
                                        raise ValueError(f"日期格式不支持: {date_str}")
                            
                            # 如果有更多列，也验证它们
                            if len(row) >= 6:
                                total_profit = float(row[4].strip())
                                # 处理百分比格式的总利润率
                                total_profit_rate_str = row[5].strip()
                                
                                # 同样检查总利润率是否包含日期信息
                                if re.search(r'\d{4}-\d{2}-\d{2}', total_profit_rate_str):
                                    match = re.match(r'([\d\.%-]+)(\d{4}-\d{2}-\d{2}.*)', total_profit_rate_str)
                                    if match:
                                        total_profit_rate_str = match.group(1)
                                        self.logger.warning(f"第{line_number}行总利润率字段包含日期信息，已分离: '{row[5]}' -> '{total_profit_rate_str}'")
                                        has_format_changes = True
                                
                                if total_profit_rate_str.endswith('%'):
                                    total_profit_rate = float(total_profit_rate_str.rstrip('%')) / 100
                                else:
                                    total_profit_rate = float(total_profit_rate_str)
                            
                            # 重新构建修复后的行数据
                            fixed_row = [date_str, f"{cash:.2f}", f"{profit:.2f}", f"{profit_rate*100:.2f}%"]
                            if len(row) >= 6:
                                fixed_row.extend([f"{total_profit:.2f}", f"{total_profit_rate*100:.2f}%"])
                            if len(row) >= 7:
                                fixed_row.append(row[6].strip())
                            
                            valid_rows.append(fixed_row)
                        else:
                            invalid_rows.append((line_number, row, "列数不足"))
                    except Exception as e:
                        invalid_rows.append((line_number, row, str(e)))
                        
            # 如果有无效行或格式变更，需要重写文件
            if invalid_rows or has_format_changes:
                # 创建备份
                backup_file = f"{self.csv_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(self.csv_file, backup_file)
                
                if invalid_rows:
                    self.logger.info(f"发现{len(invalid_rows)}行无效数据，已创建备份: {backup_file}")
                    # 记录无效行
                    for line_num, row, error in invalid_rows:
                        self.logger.warning(f"移除第{line_num}行无效数据: {row} - {error}")
                
                if has_format_changes:
                    self.logger.info(f"发现格式需要标准化，已创建备份: {backup_file}")
                
                # 重写CSV文件，只保留有效行
                with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(valid_rows)
                    
                if invalid_rows and has_format_changes:
                    self.logger.info(f"CSV文件修复和格式标准化完成，保留{len(valid_rows)}行有效数据")
                elif invalid_rows:
                    self.logger.info(f"CSV文件修复完成，保留{len(valid_rows)}行有效数据")
                elif has_format_changes:
                    self.logger.info(f"CSV文件格式标准化完成，处理{len(valid_rows)}行数据")
                    
                # 创建标准化标记文件
                try:
                    with open(standardized_flag_file, 'w', encoding='utf-8') as flag_file:
                        flag_file.write(f"CSV文件已于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 标准化")
                    self.logger.info(f"已创建标准化标记文件: {standardized_flag_file}")
                except Exception as flag_error:
                    self.logger.warning(f"创建标准化标记文件失败: {flag_error}")
            else:
                self.logger.info("CSV文件检查完成，未发现无效数据或格式问题")
                # 即使没有变更，也创建标记文件避免下次重复检查
                try:
                    with open(standardized_flag_file, 'w', encoding='utf-8') as flag_file:
                        flag_file.write(f"CSV文件已于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 检查，无需标准化")
                except Exception as flag_error:
                    self.logger.warning(f"创建标准化标记文件失败: {flag_error}")
                
        except Exception as e:
            self.logger.error(f"CSV文件修复失败: {e}")

    def append_cash_record(self, date_str, cash_value):
        """追加一条记录到CSV并更新内存history"""
        try:
            cash_float = float(cash_value)
        except Exception:
            self.logger.error(f"现金数值转换失败: {cash_value}")
            return

        # 计算利润和利润率
        if self.cash_history:
            prev_cash = float(self.cash_history[-1][1])
            profit = cash_float - prev_cash
            profit_rate = (profit / prev_cash) if prev_cash else 0.0
        else:
            # 第一条记录
            profit = 0.0
            profit_rate = 0.0

        # 计算总利润和总利润率
        if self.cash_history:
            # 获取前一行的总利润
            prev_total_profit = float(self.cash_history[-1][4]) if len(self.cash_history[-1]) > 4 else 0.0
            total_profit = prev_total_profit + profit
            
            # 获取第一天的cash作为基础
            first_cash = float(self.cash_history[0][1])
            total_profit_rate = (total_profit / first_cash) if first_cash else 0.0
        else:
            # 第一条记录
            total_profit = 0.0
            total_profit_rate = 0.0
            
        # 追加写入CSV（append模式，不覆盖）7列：日期,Cash,利润,利润率,总利润,总利润率,交易次数
        try:
            with open(self.csv_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([date_str, f"{cash_float:.2f}", f"{profit:.2f}", f"{profit_rate*100:.2f}%", f"{total_profit:.2f}", f"{total_profit_rate*100:.2f}%", str(self.last_trade_count)])
            self.logger.info(f"✅ 已追加写入CSV: {date_str}, Cash:{cash_float:.2f}, 利润:{profit:.2f}, 总利润:{total_profit:.2f}, 交易次数:{self.last_trade_count}")
        except Exception as e:
            self.logger.error(f"写入CSV失败: {e}")
            
        # 更新内存中的历史记录
        new_record = [date_str, f"{cash_float:.2f}", f"{profit:.2f}", f"{profit_rate*100:.2f}%", f"{total_profit:.2f}", f"{total_profit_rate*100:.2f}%", str(self.last_trade_count)]
        self.cash_history.append(new_record)

    def create_flask_app(self):
        """创建Flask应用，展示内存中的cash_history"""
        app = Flask(__name__)

        @app.route("/")
        def index():
            """主仪表板页面"""
            # 获取实时数据
            current_data = {
                'url': self.get_web_value('url_entry'),
                'coin': self.get_web_value('coin_combobox'),
                'auto_find_time': self.auto_find_time_combobox.get() if hasattr(self, 'auto_find_time_combobox') else self.get_web_value('auto_find_time_combobox'),
                'account': {
                    'cash': self.status_data.get_value('account', 'available_cash') or self.get_gui_label_value('cash_label') or '--',
                    'portfolio': self.status_data.get_value('account', 'portfolio_value') or self.get_gui_label_value('portfolio_label') or '--',
                    'zero_time_cash': self.status_data.get_value('account', 'zero_time_cash') or self.get_gui_label_value('zero_time_cash_label') or '0'
                },
                'prices': {
                    'up_price': self.status_data.get_value('prices', 'polymarket_up') or self.get_gui_label_value('yes_price_label') or 'N/A',
                    'down_price': self.status_data.get_value('prices', 'polymarket_down') or self.get_gui_label_value('no_price_label') or 'N/A',
                    'binance_price': self.status_data.get_value('prices', 'binance_current') or self.get_gui_label_value('binance_now_price_label') or 'N/A',
                    'binance_zero_price': self.status_data.get_value('prices', 'binance_zero_time') or self.get_gui_label_value('binance_zero_price_label') or 'N/A',
                    'binance_rate': self.status_data.get_value('prices', 'price_change_rate') or self.get_gui_label_value('binance_rate_label') or 'N/A'
                },
                'trading_pair': self.get_web_value('trading_pair_label'),
                'live_prices': {
                    'up': self.get_web_value('yes_price_label') or '0',
                    'down': self.get_web_value('no_price_label') or '0'
                },
                'positions': {
                    'up1_price': self.get_web_value('yes1_price_entry'),
                    'up1_amount': self.get_web_value('yes1_amount_entry'),
                    'up2_price': self.get_web_value('yes2_price_entry'),
                    'up2_amount': self.get_web_value('yes2_amount_entry'),
                    'up3_price': self.get_web_value('yes3_price_entry'),
                    'up3_amount': self.get_web_value('yes3_amount_entry'),
                    'up4_price': self.get_web_value('yes4_price_entry'),
                    'up4_amount': self.get_web_value('yes4_amount_entry'),
                    'down1_price': self.get_web_value('no1_price_entry'),
                    'down1_amount': self.get_web_value('no1_amount_entry'),
                    'down2_price': self.get_web_value('no2_price_entry'),
                    'down2_amount': self.get_web_value('no2_amount_entry'),
                    'down3_price': self.get_web_value('no3_price_entry'),
                    'down3_amount': self.get_web_value('no3_amount_entry'),
                    'down4_price': self.get_web_value('no4_price_entry'),
                    'down4_amount': self.get_web_value('no4_amount_entry')
                },
                'cash_history': sorted(self.cash_history, key=lambda x: self._parse_date_for_sort(x[0]), reverse=True) if hasattr(self, 'cash_history') else []
            }
            
            dashboard_template = """
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Polymarket自动交易系统</title>
                <style>
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; 
                        padding: 0; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                    }
                    .container { 
                        max-width: 1160px; margin: 2px auto; background: rgba(255, 255, 255, 0.95); 
                        padding: 2px; border-radius: 15px; backdrop-filter: blur(10px);
                    }
                    .header { text-align: center; margin-bottom: 5px; }
                    .header h1 { 
                        color: #2c3e50; margin: 0; font-size: 36px; font-weight: 700;
                        background: linear-gradient(45deg, #667eea, #764ba2);
                        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
                    }
                    .header p { color: #5a6c7d; margin: 5px 0 0 0; font-size: 18px; font-weight: 500; }
                    .nav { 
                        display: flex; justify-content: center; gap: 20px; 
                        margin-bottom: 5px; padding: 8px; background: rgba(248, 249, 250, 0.8); 
                        border-radius: 12px; backdrop-filter: blur(5px);
                    }
                    .nav a { 
                        padding: 12px 24px; background: linear-gradient(45deg, #007bff, #0056b3); 
                        color: white; text-decoration: none; border-radius: 8px; font-weight: 600;
                        font-size: 16px; transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(0,123,255,0.3);
                    }
                    .nav a:hover { 
                        background: linear-gradient(45deg, #0056b3, #004085); 
                        transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,123,255,0.4);
                    }
                    .nav a.active { 
                        background: linear-gradient(45deg, #28a745, #20c997); 
                        box-shadow: 0 4px 15px rgba(40,167,69,0.3);
                    }
                    .nav button {
                        padding: 12px 24px; background: linear-gradient(45deg, #17a2b8, #138496);
                        border: none; color: white; border-radius: 8px; cursor: pointer;
                        font-size: 16px; font-weight: 600; transition: all 0.3s ease;
                        box-shadow: 0 4px 15px rgba(23,162,184,0.3);
                    }
                    .nav button:hover {
                        background: linear-gradient(45deg, #138496, #117a8b);
                        transform: translateY(-2px); box-shadow: 0 6px 20px rgba(23,162,184,0.4);
                    }
                    .nav button:disabled, button:disabled {
                        background: linear-gradient(45deg, #6c757d, #5a6268) !important;
                        cursor: not-allowed !important;
                        opacity: 0.6 !important;
                        transform: none !important;
                        box-shadow: none !important;
                    }
                    .nav button:disabled:hover, button:disabled:hover {
                        background: linear-gradient(45deg, #6c757d, #5a6268) !important;
                        transform: none !important;
                        box-shadow: none !important;
                    }

                    .main-layout {
                        display: flex;
                        gap: 20px;
                        max-width: 1160px;
    
                        padding: 5px 5px;
                        align-items: flex-start;
                    }
                    
                    .left-panel {
                        flex: 1;
                        min-width: 400px;
                    }
                    
                    .right-panel {
                        flex: 1;
                        display: flex;
                        flex-direction: column;
                        gap: 15px;
                        align-items: stretch;
                    }
                    

                    
                    .info-grid { 
                        display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); 
                        gap: 8px; 
                    }
                    .monitor-controls-section {
                        max-width: 1160px;
                        
                        padding: 2px 1px;
                        display: flex;
                        flex-wrap: wrap;
                        gap: 15px;
                        align-items: flex-start;
                        overflow: visible;
                    }
                    .info-item { 
                        padding: 3px; background: rgba(248, 249, 250, 0.8); border-radius: 8px;
                        transition: all 0.3s ease; border: 2px solid transparent;
                        flex: 1 1 auto;
                        min-width: 70px;
                        max-width: none;
                        white-space: nowrap;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 2px;
                        overflow: hidden;
                    }
                    .info-item:hover {
                        background: rgba(255, 255, 255, 0.9); border-color: #007bff;
                        transform: translateY(-2px); box-shadow: 0 4px 15px rgba(0,123,255,0.1);
                    }
                    .coin-select-item {
                        display: flex;
                        align-items: center;
                        font-size: 14px;
                        gap: 4px;
                        flex: 0 0 auto;
                        min-width: 120px;
                        max-width: 120px;
                    }
                    .time-select-item {
                        display: flex;
                        align-items: center;
                        font-size: 14px;
                        gap: 4px;
                        flex: 0 0 auto;
                        min-width: 140px;
                        max-width: 140px;
                    }
                    .info-item label { 
                        font-weight: 600; color: #6c757d; 
                        font-size: 14px; 
                        flex-shrink: 0;
                        margin-right: 2px;
                    }
                    .info-item .value { 
                        font-size: 14px; color: #2c3e50; font-weight: 600;
                        font-family: 'Monaco', 'Menlo', monospace;
                        flex: 1;
                    }
                    .info-item select {
                        padding: 4px 8px; border: 1px solid #dee2e6; border-radius: 4px;
                        font-size: 14px; font-weight: 600; background: white;
                        font-family: 'Monaco', 'Menlo', monospace;
                        color: #2c3e50;
                        transition: all 0.3s ease; cursor: pointer;
                        flex: 1;
                    }
                    .info-item select:focus {
                        border-color: #007bff; box-shadow: 0 0 0 2px rgba(0,123,255,0.1);
                        outline: none;
                    }
                    .position-container {
                        padding: 5px 5px;
                        background: rgba(248, 249, 250, 0.9);
                        border-radius: 6px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 8px;
                        flex-wrap: wrap;
                    }
                    .position-content {
                        font-size: 12px;
                        font-weight: 600;
                        color: #007bff;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        word-wrap: break-word;
                        width: 100%;
                        text-align: center;
                    }

                    .binance-price-container {
                        display: flex;
                        flex-direction: row;
                        gap: 5px;
                        flex: 1;
                        align-items: center;
                        justify-content: center; /* 水平居中 */
                    }
                    /* 减少上方币安价格区与下方资产区之间的垂直间距 */
                    .binance-price-container + .binance-price-container {
                        margin-top: 0px;
                    }
                    .binance-price-item {
                        display: flex;
                        align-items: center;
                        font-size: 14px;
                        gap: 4px;
                    }
                    .binance-label {
                        font-weight: 600;
                        color: #6c757d;
                    }
                    .binance-price-item .value {
                        font-size: 14px;
                        font-weight: 600;
                        font-family: 'Monaco', 'Menlo', monospace;
                        color: #2c3e50;
                    }
                    /* UP和DOWN价格显示独立样式 */
                    .up-down-prices-container {
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        gap: 25px;
                        
                        flex: 2;
                        min-height: 80px;
                    }
                    
                    .up-price-display, .down-price-display {
                        font-size: 28px;
                        font-weight: 800;
                        color: #2F3E46; /* 深灰蓝，比纯黑柔和 */
                        text-align: center;
                        padding: 12px 20px;
                        border-radius: 12px;
                        box-shadow: 0 6px 25px rgba(0,0,0,0.15);
                        min-width: 180px;
                        max-width: 250px;
                        flex: 1;
                        position: relative;
                        overflow: hidden;
                        transition: all 0.3s ease;
                        font-family: 'Monaco', 'Menlo', monospace;
                    }
                    
                    .up-price-display {
                        background: linear-gradient(135deg, #A8C0FF, #C6FFDD);
                        border: none;
                    }
                    
                    .down-price-display {
                        background: linear-gradient(135deg, #A8C0FF, #C6FFDD);
                        border: none;
                    }
                    
                    .up-price-display:hover, .down-price-display:hover {
                        transform: translateY(-3px);
                        box-shadow: 0 10px 35px rgba(0,0,0,0.2);
                    }
                    
                    .price-label {
                        color: #333;
                        font-weight: bold;
                        margin-right: 5px;
                    }
                    .price-display { 
                        display: flex; justify-content: space-around; text-align: center; gap: 12px;
                        margin-top: 10px;
                    }
                    .price-box { 
                        padding: 18px; border-radius: 12px; min-width: 150px;
                        font-size: 20px; font-weight: 800; transition: all 0.3s ease;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    }
                    .price-box:hover {
                        transform: translateY(-3px); box-shadow: 0 8px 10px rgba(0,0,0,0.15);
                    }
                    .price-up { 
                        background: linear-gradient(135deg, #d4edda, #c3e6cb); 
                        color: #155724; border: 2px solid #28a745;
                    }
                    .price-down { 
                        background: linear-gradient(135deg, #f8d7da, #f5c6cb); 
                        color: #721c24; border: 2px solid #dc3545;
                    }
                    .positions-grid { 
                        display: grid; 
                        grid-template-columns: 1fr 1fr; 
                        gap: 2px; 
                        margin-top: 0px;
                        flex: 0.5;
                        max-height: 250px;
                        overflow-y: auto;
                    }
                    .position-section {
                        background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(248,249,250,0.9));
                        border-radius: 8px;
                        padding: 8px;
                        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
                        backdrop-filter: blur(10px);
                        border: 1px solid rgba(255,255,255,0.2);
                        transition: all 0.3s ease;
                        position: relative;
                        overflow: hidden;
                        height: fit-content;
                    }
                    .position-section::before {
                        content: '';
                        position: absolute;
                        top: 0;
                        left: 0;
                        right: 0;
                        height: 4px;
                        background: linear-gradient(90deg, #667eea, #764ba2);
                        border-radius: 16px 16px 0 0;
                    }
                    .position-section:hover {
                        transform: translateY(-5px);
                        box-shadow: 0 12px 40px rgba(0,0,0,0.18);
                    }
                    .up-section::before {
                        background: linear-gradient(90deg, #00c9ff, #92fe9d);
                    }
                    .down-section::before {
                        background: linear-gradient(90deg, #fc466b, #3f5efb);
                    }
                    .position-section h4 { 
                        margin: 0 0 8px 0; 
                        padding: 8px 12px; 
                        border-radius: 8px; 
                        text-align: center; 
                        color: white; 
                        font-size: 14px; 
                        font-weight: 700;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        position: relative;
                        overflow: hidden;
                    }
                    .position-section h4::before {
                        content: '';
                        position: absolute;
                        top: 0;
                        left: -100%;
                        width: 100%;
                        height: 100%;
                        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                        transition: left 0.5s;
                    }
                    .position-section:hover h4::before {
                        left: 100%;
                    }
                    .up-section h4 { 
                        background: linear-gradient(135deg, #00c9ff, #92fe9d); 
                        box-shadow: 0 6px 20px rgba(0,201,255,0.4);
                    }
                    .down-section h4 { 
                        background: linear-gradient(135deg, #fc466b, #3f5efb); 
                        box-shadow: 0 6px 20px rgba(252,70,107,0.4);
                    }
                    .position-row { 
                        display: grid; 
                        grid-template-columns: 60px 1fr 1fr; 
                        gap: 6px; 
                        padding: 6px 0; 
                        border-bottom: 1px solid rgba(0,0,0,0.05); 
                        align-items: center; 
                        font-size: 12px; 
                        font-weight: 500;
                        transition: all 0.2s ease;
                    }
                    .position-row:last-child { border-bottom: none; }
                    .position-row:hover {
                        background: rgba(102,126,234,0.05);
                        border-radius: 8px;
                        padding-left: 8px;
                        padding-right: 8px;
                    }
                    .position-row.header {
                        background: linear-gradient(135deg, rgba(102,126,234,0.1), rgba(118,75,162,0.1));
                        border-radius: 6px;
                        font-weight: 700;
                        color: #2c3e50;
                        padding: 6px 8px;
                        
                        border: none;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                        font-size: 10px;
                    }
                    .position-label { 
                        font-weight: 700; 
                        color: #495057; 
                        text-align: center;
                    }
                    .position-name {
                        font-weight: 600;
                        color: #2F3E46; /* 深灰蓝，比纯黑柔和 */
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        background: linear-gradient(135deg, #A8C0FF, #C6FFDD);
                        border-radius: 8px;
                        padding: 8px;
                        font-size: 13px;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }
                    .position-input {
                        width: 100%;
                        padding: 6px 8px;
                        border: 1px solid rgba(0,0,0,0.1);
                        border-radius: 6px;
                        font-size: 11px;
                        text-align: center;
                        background: linear-gradient(135deg, rgba(255,255,255,0.9), rgba(248,249,250,0.9));
                        font-weight: 600;
                        color: #2c3e50;
                        transition: all 0.3s ease;
                        font-family: 'Monaco', 'Menlo', monospace;
                    }
                    .position-input:focus {
                        outline: none;
                        border-color: #667eea;
                        box-shadow: 0 0 0 4px rgba(102,126,234,0.15);
                        background: white;
                        transform: scale(1.02);
                    }
                    .position-input:hover {
                        border-color: rgba(102,126,234,0.5);
                        background: white;
                    }
                    .position-controls {
                        display: flex;
                        gap: 12px;
                        margin-top: 20px;
                        justify-content: center;
                        padding-top: 15px;
                        border-top: 1px solid rgba(0,0,0,0.05);
                    }
                    .save-btn, .reset-btn {
                        padding: 12px 24px;
                        border: none;
                        border-radius: 12px;
                        font-size: 14px;
                        font-weight: 700;
                        cursor: pointer;
                        transition: all 0.3s ease;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        position: relative;
                        overflow: hidden;
                        min-width: 100px;
                        backdrop-filter: blur(10px);
                    }
                    .save-btn::before, .reset-btn::before {
                        content: '';
                        position: absolute;
                        top: 0;
                        left: -100%;
                        width: 100%;
                        height: 100%;
                        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
                        transition: left 0.5s;
                    }
                    .save-btn:hover::before, .reset-btn:hover::before {
                        left: 100%;
                    }
                    .save-btn {
                        background: linear-gradient(135deg, #00c9ff, #92fe9d);
                        color: white;
                        box-shadow: 0 6px 25px rgba(0,201,255,0.4);
                        border: 2px solid rgba(255,255,255,0.2);
                    }
                    .save-btn:hover {
                        background: linear-gradient(135deg, #00b4e6, #7ee87f);
                        transform: translateY(-3px);
                        box-shadow: 0 10px 35px rgba(0,201,255,0.5);
                    }
                    .save-btn:active {
                        transform: translateY(-1px);
                        box-shadow: 0 4px 15px rgba(0,201,255,0.3);
                    }
                    .reset-btn {
                        background: linear-gradient(135deg, #667eea, #764ba2);
                        color: white;
                        box-shadow: 0 6px 25px rgba(102,126,234,0.4);
                        border: 2px solid rgba(255,255,255,0.2);
                    }
                    .reset-btn:hover {
                        background: linear-gradient(135deg, #5a6fd8, #6a4190);
                        transform: translateY(-3px);
                        box-shadow: 0 10px 35px rgba(102,126,234,0.5);
                    }
                    .reset-btn:active {
                        transform: translateY(-1px);
                        box-shadow: 0 4px 15px rgba(102,126,234,0.3);
                    }
                    .refresh-info {
                        margin-top: 20px;
                        padding: 16px 20px;
                        background: linear-gradient(135deg, rgba(102,126,234,0.1), rgba(118,75,162,0.1));
                        border-radius: 12px;
                        border: 1px solid rgba(102,126,234,0.2);
                        font-size: 14px;
                        color: #2c3e50;
                        box-shadow: 0 4px 20px rgba(102,126,234,0.1);
                        backdrop-filter: blur(10px);
                        position: relative;
                        overflow: hidden;
                        font-weight: 500;
                        text-align: center;
                    }
                    .refresh-info::before {
                        content: '';
                        position: absolute;
                        top: 0;
                        left: 0;
                        right: 0;
                        height: 3px;
                        background: linear-gradient(90deg, #667eea, #764ba2);
                        border-radius: 12px 12px 0 0;
                    }
                    .control-section {
                        max-width: 1160px;
                        min-width: 1140px;
                        padding: 10px 10px 0 10px;
                        
                    }
                    .url-input-group {
                        display: flex; gap: 15px; 
                    }
                    .url-input-group input {
                        flex: 1; padding: 2px 18px; border: 2px solid #ced4da;
                        border-radius: 8px; font-size: 14px; transition: all 0.3s ease;
                        background: linear-gradient(135deg, #A8C0FF, #C6FFDD);
                        color: #2F3E46;
                        text-align: center;
                    }
                    .url-input-group input:focus {
                        border-color: #007bff; box-shadow: 0 0 0 3px rgba(0,123,255,0.1);
                        outline: none;
                    }
                    .url-input-group button {
                        padding: 6px 8px; background: linear-gradient(135deg, #A8C0FF, #C6FFDD);
                        color: #2F3E46; border: none; border-radius: 8px; cursor: pointer;
                        font-size: 16px; font-weight: 600; white-space: nowrap;
                        transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(168,192,255,0.3);
                    }
                    .url-input-group button:hover {
                        background: linear-gradient(135deg, #9BB5FF, #B8F2DD);
                        transform: translateY(-2px); box-shadow: 0 6px 20px rgba(168,192,255,0.4);
                    }
                    .url-input-group button:disabled {
                        background: #6c757d; cursor: not-allowed; transform: none;
                        box-shadow: none;
                    }
                    .status-message {
                        padding: 12px; border-radius: 8px; font-size: 16px;
                        text-align: center; display: none; font-weight: 500;
                    }
                    .status-message.success {
                        background: linear-gradient(135deg, #d4edda, #c3e6cb);
                        color: #155724; border: 2px solid #c3e6cb; display: block;
                    }
                    .status-message.error {
                        background: linear-gradient(135deg, #f8d7da, #f5c6cb);
                        color: #721c24; border: 2px solid #f5c6cb; display: block;
                    }
                    .log-section {
                        background: rgba(255, 255, 255, 0.9);
                        border-radius: 2px; padding: 2px; color: #2c3e50;
                        font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
                        backdrop-filter: blur(5px);
                        border: 1px solid rgba(233, 236, 239, 0.5);
                    }
                    
                    .log-container {
                        height: 500px; overflow-y: auto; background: rgba(248, 249, 250, 0.8);
                        border-radius: 8px; padding: 18px; border: 2px solid rgba(233, 236, 239, 0.5);
                        margin-top: 0;
                        /* 自定义滚动条样式 */
                        scrollbar-width: thin;
                        scrollbar-color: transparent transparent;
                    }
                    /* Webkit浏览器滚动条样式 */
                    .log-container::-webkit-scrollbar {
                        width: 8px;
                    }
                    .log-container::-webkit-scrollbar-track {
                        background: transparent;
                    }
                    .log-container::-webkit-scrollbar-thumb {
                        background: transparent;
                        border-radius: 4px;
                        transition: background 0.3s ease;
                    }
                    /* 悬停时显示滚动条 */
                    .log-container:hover {
                        scrollbar-color: rgba(0, 0, 0, 0.3) transparent;
                    }
                    .log-container:hover::-webkit-scrollbar-thumb {
                        background: rgba(0, 0, 0, 0.3);
                    }
                    .log-container:hover::-webkit-scrollbar-thumb:hover {
                        background: rgba(0, 0, 0, 0.5);
                    }
                    .log-entry {
                        margin-bottom: 8px; font-size: 10px; line-height: 1.4;
                        word-wrap: break-word;
                        color: #000000;
                    }
                    .log-entry.info { color: #17a2b8; }
                    .log-entry.warning { color: #ffc107; }
                    .log-entry.error { color: #dc3545; }
                    .log-entry.success { color: #28a745; }

                    .side-by-side-container {
                        display: flex;
                        gap: 20px;
                        margin-top: 30px;
                    }
                    .half-width {
                        flex: 1;
                        width: 50%;
                        min-height: 500px;
                    }
                    .log-section.half-width {
                        margin-top: 0;
                        display: flex;
                        flex-direction: column;
                        height: 100%;
                    }
                    .card.half-width {
                        margin-top: 0;
                        display: flex;
                        flex-direction: column;
                        height: 100%;
                    }
                    .card.half-width .positions-grid {
                        flex: 1;
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 15px;
                    }
                    
                    /* 时间显示和倒计时样式 */
                    .time-display-section {
                        margin-top: 6px;
                        padding: 5px 10px;
                        background: rgba(248, 249, 250, 0.9);
                        border-radius: 6px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 8px;
                        flex-wrap: wrap;
                    }
                    
                    .current-time {
                        margin: 0;
                    }
                    
                    #currentTime {
                        font-size: 16px;
                        font-weight: 600;
                        color: #2c3e50;
                        background: linear-gradient(45deg, #667eea, #764ba2);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                    }
                    
                    .countdown-container {
                        display: flex;
                        align-items: center;
                        gap: 5px;
                    }
                    
                    .countdown-label {
                        font-size: 14px;
                        font-weight: 600;
                        background: linear-gradient(45deg, #667eea, #764ba2);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                    }
                    
                    .simple-clock {
                        display: flex;
                        gap: 1px;
                        align-items: center;
                        font-size: 16px;
                        font-weight: bold;
                        color: #dc3545;
                    }
                    
                    .simple-clock span {
                        min-width: 18px;
                        text-align: center;
                    }
                 
                </style>
                <script>
                    function updateData() {
                        fetch('/api/status')
                            .then(response => response.json())
                            .then(data => {
                                if (data.error) {
                                    console.error('API Error:', data.error);
                                    return;
                                }
                                
                                // 更新价格显示
                                const upPriceElement = document.querySelector('#upPrice');
                                const downPriceElement = document.querySelector('#downPrice');
                                const binancePriceElement = document.querySelector('#binancePrice');
                                const binanceZeroPriceElement = document.querySelector('#binanceZeroPrice');
                                const binanceRateElement = document.querySelector('#binanceRate');
                                
                                if (upPriceElement) upPriceElement.innerHTML = '<span class="price-label">RISE:</span> ' + (data.prices.up_price || 'N/A');
                                if (downPriceElement) downPriceElement.innerHTML = '<span class="price-label">DOWN:</span> ' + (data.prices.down_price || 'N/A');
                                if (binanceZeroPriceElement) binanceZeroPriceElement.textContent = data.prices.binance_zero_price;
                                
                                // 实时价格颜色逻辑：与零点价格比较
                                if (binancePriceElement) {
                                    binancePriceElement.textContent = data.prices.binance_price;
                                    const currentPrice = parseFloat(data.prices.binance_price);
                                    const zeroPrice = parseFloat(data.prices.binance_zero_price);
                                    
                                    if (!isNaN(currentPrice) && !isNaN(zeroPrice)) {
                                        if (currentPrice > zeroPrice) {
                                            binancePriceElement.style.color = '#28a745'; // 绿色
                                        } else if (currentPrice < zeroPrice) {
                                            binancePriceElement.style.color = '#dc3545'; // 红色
                                        } else {
                                            binancePriceElement.style.color = '#2c3e50'; // 默认颜色
                                        }
                                    }
                                }
                                
                                // 涨幅格式化和颜色逻辑
                                if (binanceRateElement) {
                                    const rateValue = parseFloat(data.prices.binance_rate);
                                    if (!isNaN(rateValue)) {
                                        // 格式化为百分比，保留三位小数
                                        const formattedRate = rateValue >= 0 ? 
                                            `${rateValue.toFixed(3)}%` : 
                                            `-${Math.abs(rateValue).toFixed(3)}%`;
                                        
                                        binanceRateElement.textContent = formattedRate;
                                        
                                        // 设置颜色：上涨绿色，下跌红色
                                        if (rateValue > 0) {
                                            binanceRateElement.style.color = '#28a745'; // 绿色
                                        } else if (rateValue < 0) {
                                            binanceRateElement.style.color = '#dc3545'; // 红色
                                        } else {
                                            binanceRateElement.style.color = '#2c3e50'; // 默认颜色
                                        }
                                    } else {
                                        binanceRateElement.textContent = data.prices.binance_rate;
                                        binanceRateElement.style.color = '#2c3e50';
                                    }
                                }
                                
                                // 更新账户信息
                                const portfolioElement = document.querySelector('#portfolio');
                                const cashElement = document.querySelector('#cash');
                                const zeroTimeCashElement = document.querySelector('#zeroTimeCash');
                                const remainingTradesElement = document.querySelector('#remainingTrades');
                                
                                if (portfolioElement) portfolioElement.textContent = data.account.portfolio;
                                if (cashElement) cashElement.textContent = data.account.cash;
                                if (zeroTimeCashElement) zeroTimeCashElement.textContent = data.account.zero_time_cash || '--';
                                if (remainingTradesElement) remainingTradesElement.textContent = data.remaining_trades || '--';
                                
                                // 更新币种和交易时间显示
                                const coinDisplayElement = document.querySelector('#coinDisplay');
                                const timeDisplayElement = document.querySelector('#timeDisplay');
                                
                                if (coinDisplayElement) coinDisplayElement.textContent = data.coin || '--';
                                if (timeDisplayElement) timeDisplayElement.textContent = data.auto_find_time || '--';
                                
                                // 持仓信息将在交易验证成功后自动更新，无需在此处调用
                                
                                // 更新状态信息
                                const statusElement = document.querySelector('.status-value');
                                const urlElement = document.querySelector('.url-value');
                                const browserElement = document.querySelector('.browser-value');
                                
                                if (statusElement) statusElement.textContent = data.status.monitoring;
                                if (urlElement) urlElement.textContent = data.status.url;
                                if (browserElement) browserElement.textContent = data.status.browser_status;
                                
                                // URL输入框不再自动更新，避免覆盖用户输入
                                // const urlInputElement = document.querySelector('#urlInput');
                                // if (urlInputElement && data.status.url && data.status.url !== '未设置') {
                                //     urlInputElement.value = data.status.url;
                                // }
                                
                                // 更新仓位信息
                                for (let i = 1; i <= 5; i++) {
                                    const upPriceEl = document.querySelector(`#up${i}_price`);
                                    const upAmountEl = document.querySelector(`#up${i}_amount`);
                                    const downPriceEl = document.querySelector(`#down${i}_price`);
                                    const downAmountEl = document.querySelector(`#down${i}_amount`);
                                    
                                    if (upPriceEl) upPriceEl.value = data.positions[`up${i}_price`];
                                    if (upAmountEl) upAmountEl.value = data.positions[`up${i}_amount`];
                                    if (downPriceEl) downPriceEl.value = data.positions[`down${i}_price`];
                                    if (downAmountEl) downAmountEl.value = data.positions[`down${i}_amount`];
                                }
                                
                                // 更新最后更新时间
                                const timeElement = document.querySelector('.last-update-time');
                                if (timeElement) timeElement.textContent = data.status.last_update;
                            })
                            .catch(error => {
                                console.error('更新数据失败:', error);
                            });
                    }
                    
                    function refreshPage() {
                        location.reload();
                    }
                    

                    
                    // 页面加载时初始化
                    document.addEventListener('DOMContentLoaded', function() {
                        // 开始定期更新数据
                        updateData();
                        setInterval(updateData, 2000);
                        
                        // 初始化时间显示和倒计时
                        initializeTimeDisplay();
                        
                        // 添加URL输入框事件监听器
                        const urlInput = document.getElementById('urlInput');
                        if (urlInput) {
                            urlInput.addEventListener('input', function() {
                                // 用户手动输入时清除防止自动更新的标志
                                window.preventUrlAutoUpdate = false;
                            });
                        }
                    });
                    
                    function updatePositionInfo() {
                        fetch('/api/positions')
                            .then(response => response.json())
                            .then(data => {
                                const positionContainer = document.getElementById('positionContainer');
                                const positionContent = document.getElementById('positionContent');
                                const sellBtn = document.getElementById('sellPositionBtn');
                                
                                if (!positionContainer || !positionContent) return;
                                
                                if (data.success && data.position) {
                                    const position = data.position;
                                    // 格式化持仓信息：持仓:方向:direction 数量:shares 价格:price 金额:amount
                                    const positionText = `方向:${position.direction} 数量:${position.shares} 价格:${position.price} 金额:${position.amount}`;
                                    
                                    // 设置文本内容
                                    positionContent.innerHTML = positionText;
                                    
                                    // 根据方向设置颜色
                                    if (position.direction === 'Up') {
                                        positionContent.style.color = '#28a745'; // 绿色
                                    } else if (position.direction === 'Down') {
                                        positionContent.style.color = '#dc3545'; // 红色
                                    } else {
                                        positionContent.style.color = '#2c3e50'; // 默认颜色
                                    }
                                    
                                    // 有持仓时保持卖出按钮样式
                                    if (sellBtn) {
                                        sellBtn.style.backgroundColor = '#dc3545';
                                        sellBtn.style.cursor = 'pointer';
                                    }
                                    
                                    positionContainer.style.display = 'block';
                                } else {
                                    positionContent.textContent = '方向: -- 数量: -- 价格: -- 金额: --';
                                    positionContent.style.color = '#2c3e50'; // 默认颜色
                                    
                                    // 无持仓时保持卖出按钮可点击
                                    if (sellBtn) {
                                        sellBtn.style.backgroundColor = '#dc3545';
                                        sellBtn.style.cursor = 'pointer';
                                    }
                                    
                                    positionContainer.style.display = 'block';
                                }
                            })
                            .catch(error => {
                                console.error('获取持仓信息失败:', error);
                                const positionContainer = document.getElementById('positionContainer');
                                const positionContent = document.getElementById('positionContent');
                                const sellBtn = document.getElementById('sellPositionBtn');
                                if (positionContainer && positionContent) {
                                    positionContent.textContent = '方向: -- 数量: -- 价格: -- 金额: --';
                                    positionContent.style.color = '#dc3545'; // 红色表示错误
                                    
                                    // 获取失败时保持卖出按钮可点击
                                    if (sellBtn) {
                                        sellBtn.style.backgroundColor = '#dc3545';
                                        sellBtn.style.cursor = 'pointer';
                                    }
                                    
                                    positionContainer.style.display = 'block';
                                }
                            });
                    }
                    

                    

                    
                    function updateCoin() {
                        const coin = document.getElementById('coinSelect').value;
                        fetch('/api/update_coin', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({coin: coin})
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                console.log('币种更新成功:', coin);
                            }
                        })
                        .catch(error => {
                            console.error('Error updating coin:', error);
                        });
                    }
                    
                    function updateTime() {
                        const time = document.getElementById('timeSelect').value;
                        fetch('/api/update_time', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({time: time})
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                console.log('时间更新成功:', time);
                            }
                        })
                        .catch(error => {
                            console.error('Error updating time:', error);
                        });
                    }
                    
                    // 时间显示和倒计时功能
                    function updateCurrentTime() {
                        const now = new Date();
                        const timeString = now.getFullYear() + '-' + 
                            String(now.getMonth() + 1).padStart(2, '0') + '-' + 
                            String(now.getDate()).padStart(2, '0') + ' ' + 
                            String(now.getHours()).padStart(2, '0') + ':' + 
                            String(now.getMinutes()).padStart(2, '0') + ':' + 
                            String(now.getSeconds()).padStart(2, '0');
                        document.getElementById('currentTime').textContent = timeString;
                    }
                    
                    function updateCountdown() {
                        const now = new Date();
                        const endOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
                        const timeDiff = endOfDay - now;
                        
                        if (timeDiff <= 0) {
                            // 如果已经过了当天23:59:59，显示00:00:00
                            updateFlipClock('00', '00', '00');
                            return;
                        }
                        
                        const hours = Math.floor(timeDiff / (1000 * 60 * 60));
                        const minutes = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60));
                        const seconds = Math.floor((timeDiff % (1000 * 60)) / 1000);
                        
                        const hoursStr = String(hours).padStart(2, '0');
                        const minutesStr = String(minutes).padStart(2, '0');
                        const secondsStr = String(seconds).padStart(2, '0');
                        
                        updateFlipClock(hoursStr, minutesStr, secondsStr);
                    }
                    
                    function updateFlipClock(hours, minutes, seconds) {
                        // 先检查元素是否存在
                        if (document.getElementById('hours') && 
                            document.getElementById('minutes') && 
                            document.getElementById('seconds')) {
                            updateSimpleUnit('hours', hours);
                            updateSimpleUnit('minutes', minutes);
                            updateSimpleUnit('seconds', seconds);
                        } else {
                            console.log('Countdown elements not found, retrying in 1 second...');
                        }
                    }
                    
                    function updateSimpleUnit(unitId, newValue) {
                        const unit = document.getElementById(unitId);
                        if (!unit) {
                            console.error('Element not found:', unitId);
                            return;
                        }
                        
                        // 直接更新数字内容
                        unit.textContent = newValue;
                    }
                    
                    // 初始化时间显示和倒计时
                    function initializeTimeDisplay() {
                        // 延迟执行以确保DOM完全加载
                        setTimeout(() => {
                            updateCurrentTime();
                            updateCountdown();
                            
                            // 每秒更新时间和倒计时
                            setInterval(updateCurrentTime, 1000);
                            setInterval(updateCountdown, 1000);
                        }, 100);
                    }
                    
                    // 注意：数据更新和按钮状态管理已在DOMContentLoaded事件中处理
                </script>
            </head>
            <body>
                <div class="container">
                    <div class="container">
                        <div class="header">
                            <h1>🚀 Polymarket自动交易系统</h1>
                        </div>
                        
                        <!-- 主要内容区域：左右分栏 -->
                        <div class="main-layout">
                            <!-- 左侧：日志显示区域 -->
                            <div class="left-panel log-section log-container" id="logContainer">
                                
                                    
                                <div class="log-loading">正在加载日志...</div>
                                    
                                
                            </div>
                            <!-- 右侧：价格和交易区域 -->
                            <div class="right-panel">
                                <!-- UP和DOWN价格显示 -->
                                <div class="up-down-prices-container">
                                    <div class="up-price-display" id="upPrice">
                                        <span class="price-label">RISE:</span> {{ data.prices.up_price or 'N/A' }}
                                    </div>
                                    <div class="down-price-display" id="downPrice">
                                        <span class="price-label">DOWN:</span> {{ data.prices.down_price or 'N/A' }}
                                    </div>
                                </div>
                                
                                <!-- 持仓显示区域 -->
                                <div class="position-container" id="positionContainer" style="display: block;">
                                    <div class="position-content" id="positionContent">
                                        方向: -- 数量: -- 价格: -- 金额: --
                                    </div>
                                </div>
                                
                                <!-- 币安价格和资产显示区域 -->
                                <div class="binance-price-container">
                                    <div class="binance-price-item">
                                        <span class="binance-label">零点价格:</span> <span class="value" id="binanceZeroPrice">{{ data.prices.binance_zero_price or '--' }}</span>
                                    </div>
                                    <div class="binance-price-item">
                                        <span class="binance-label">实时价格:</span> <span class="value" id="binancePrice">{{ data.prices.binance_price or '--' }}</span>
                                    </div>
                                    <div class="binance-price-item">
                                        <span class="binance-label">涨跌幅:</span> <span class="value" id="binanceRate">{{ data.prices.binance_rate or '--' }}</span>
                                    </div>
                                </div>
                                <div class="binance-price-container">
                                    <div class="binance-price-item">
                                        <span class="binance-label">预计收益:</span> <span class="value" id="portfolio">{{ data.account.portfolio or '0' }}</span>
                                    </div>
                                    <div class="binance-price-item">
                                        <span class="binance-label">剩余本金:</span> <span class="value" id="cash">{{ data.account.cash or '0' }}</span>
                                    </div>
                                    <div class="binance-price-item">
                                        <span class="binance-label">当天本金:</span> <span class="value" id="zeroTimeCash">{{ data.account.zero_time_cash or '--' }}</span>
                                    </div>
                                </div>
                                
                                <!-- 币种和交易时间显示区域 -->
                                <div class="binance-price-container">
                                    <div class="info-item coin-select-item">
                                            <label>币种:</label>
                                            <span id="coinDisplay" style="display: inline-block;">{{ data.coin }}</span>
                                    </div>
                                    <div class="info-item time-select-item" style="display: inline-block; padding: 5px 5px; background: linear-gradient(135deg, #A8C0FF, #C6FFDD); border-radius: 18px;">
                                            <label>开始交易时间:</label>
                                            <span id="timeDisplay">{{ data.auto_find_time }}</span>
                                    </div>
                                    <div class="binance-price-item" style="display: inline-block;">
                                        <span class="binance-label">剩余交易次数:</span> <span class="value" id="remainingTrades" style="color: {% if data.remaining_trades and data.remaining_trades|int < 7 %}red{% else %}blue{% endif %};">{{ data.remaining_trades or '--' }}</span>
                                    </div>
                                </div>
                                <!-- 交易仓位显示区域 -->
                                <div class="card">
                                <form id="positionsForm">
                                    <div class="positions-grid">
                                        <div class="position-section up-section">
                                            <div class="position-row header">
                                                <div class="position-label">方向</div>
                                                <div class="position-label">价格</div>
                                                <div class="position-label">金额</div>
                                            </div>
                                            <div class="position-row">
                                                <div class="position-name">Rise1</div>
                                                <input type="number" class="position-input" id="up1_price" name="up1_price" value="0" step="0.01" min="0" oninput="autoSavePosition(this)">
                                                <input type="number" class="position-input" id="up1_amount" name="up1_amount" value="0" step="0.01" min="0" oninput="autoSavePosition(this)">
                                            </div>
                                            <div class="position-row">
                                                <div class="position-name">Rise2</div>
                                                <input type="number" class="position-input" id="up2_price" name="up2_price" value="0" step="0.01" min="0" oninput="autoSavePosition(this)">
                                                <input type="number" class="position-input" id="up2_amount" name="up2_amount" value="0" step="0.01" min="0" oninput="autoSavePosition(this)">
                                            </div>
                                            <div class="position-row">
                                                <div class="position-name">Rise3</div>
                                                <input type="number" class="position-input" id="up3_price" name="up3_price" value="0" step="0.01" min="0" oninput="autoSavePosition(this)">
                                                <input type="number" class="position-input" id="up3_amount" name="up3_amount" value="0" step="0.01" min="0" oninput="autoSavePosition(this)">
                                            </div>
                                            <div class="position-row">
                                                <div class="position-name">Rise4</div>
                                                <input type="number" class="position-input" id="up4_price" name="up4_price" value="0" step="0.01" min="0" oninput="autoSavePosition(this)">
                                                <input type="number" class="position-input" id="up4_amount" name="up4_amount" value="0" step="0.01" min="0" oninput="autoSavePosition(this)">
                                            </div>

                                        </div>
                                        
                                        <div class="position-section down-section">
                                            <div class="position-row header">
                                                <div class="position-label">价格</div>
                                                <div class="position-label">金额</div>
                                                <div class="position-label">方向</div>
                                            </div>
                                            <div class="position-row">
                                                <input type="number" class="position-input" id="down1_price" name="down1_price" value="0" step="0.01" min="0" oninput="autoSavePosition(this)">
                                                <input type="number" class="position-input" id="down1_amount" name="down1_amount" value="0" step="0.01" min="0" oninput="autoSavePosition(this)">
                                                <div class="position-name">Down1</div>
                                            </div>
                                            <div class="position-row">
                                                <input type="number" class="position-input" id="down2_price" name="down2_price" value="0" step="0.01" min="0" oninput="autoSavePosition(this)">
                                                <input type="number" class="position-input" id="down2_amount" name="down2_amount" value="0" step="0.01" min="0" oninput="autoSavePosition(this)">
                                                <div class="position-name">Down2</div>
                                            </div>
                                            <div class="position-row">
                                                <input type="number" class="position-input" id="down3_price" name="down3_price" value="0" step="0.01" min="0" oninput="autoSavePosition(this)">
                                                <input type="number" class="position-input" id="down3_amount" name="down3_amount" value="0" step="0.01" min="0" oninput="autoSavePosition(this)">
                                                <div class="position-name">Down3</div>
                                            </div>
                                            <div class="position-row">
                                                <input type="number" class="position-input" id="down4_price" name="down4_price" value="0" step="0.01" min="0" oninput="autoSavePosition(this)">
                                                <input type="number" class="position-input" id="down4_amount" name="down4_amount" value="0" step="0.01" min="0" oninput="autoSavePosition(this)">
                                                <div class="position-name">Down4</div>
                                            </div>

                                        </div>
                                    </div>

                                    <!-- 时间显示和倒计时 -->
                                    <div class="time-display-section">
                                        <div class="current-time">
                                            <span id="currentTime">2025-08-17 18:08:30</span>
                                        </div>
                                        <div class="countdown-container">
                                            <span class="countdown-label">距离当天交易结束还有:</span>
                                            <div class="simple-clock">
                                                <span id="hours">06</span>:
                                                <span id="minutes">50</span>:
                                                <span id="seconds">30</span>
                                            </div>
                                        </div>
                                    </div>

                                </form>                           
                            </div>
                            
                        </div>
                            </div>
                        </div>
                        
                        <!-- 网站监控信息 -->
                        <div class="monitor-controls-section">
                         
                            <!-- URL输入区域 -->
                            <div class="control-section">
                                <div class="url-input-group">
                                    <input type="text" id="urlInput" placeholder="请输入Polymarket交易URL" value="{{ data.url or '' }}">
                                </div>
                                <div id="statusMessage" class="status-message"></div>
                            </div>
                        </div>
                    
                    <script>

                    
                    function showMessage(message, type) {
                        const statusMessage = document.getElementById('statusMessage');
                        statusMessage.textContent = message;
                        statusMessage.className = `status-message ${type}`;
                        
                        // 5秒后隐藏消息
                        setTimeout(() => {
                            statusMessage.style.display = 'none';
                        }, 5000);
                    }
                    

                    
                    // 检查浏览器状态的函数
                    function checkBrowserStatus() {
                        fetch('/api/browser_status')
                        .then(response => response.json())
                        .then(data => {
                            const startBtn = document.getElementById('startBtn');
                            if (data.browser_connected) {
                                // 浏览器已连接，禁用启动按钮
                                startBtn.disabled = true;
                                startBtn.textContent = '🌐 运行中...';
                                startBtn.style.backgroundColor = '#6c757d';
                                startBtn.style.cursor = 'not-allowed';
                                
                                // 停止检查状态
                                if (window.browserStatusInterval) {
                                    clearInterval(window.browserStatusInterval);
                                    window.browserStatusInterval = null;
                                }
                            }
                        })
                        .catch(error => {
                            console.error('检查浏览器状态失败:', error);
                        });
                    }
                    
                    // 启动浏览器状态检查
                    function startBrowserStatusCheck() {
                        // 每2秒检查一次浏览器状态
                        window.browserStatusInterval = setInterval(checkBrowserStatus, 2000);
                    }
                    
                    // 检查监控状态的函数
                    function checkMonitoringStatus() {
                        fetch('/api/monitoring_status')
                        .then(response => response.json())
                        .then(data => {
                            const startBtn = document.getElementById('startBtn');
                            if (data.monitoring_active) {
                                // 监控已启动，禁用启动按钮
                                startBtn.disabled = true;
                                startBtn.textContent = '程序运行中';
                                startBtn.style.backgroundColor = '#6c757d';
                                startBtn.style.cursor = 'not-allowed';
                                
                                // 停止检查状态
                                if (window.monitoringStatusInterval) {
                                    clearInterval(window.monitoringStatusInterval);
                                    window.monitoringStatusInterval = null;
                                }
                            }
                        })
                        .catch(error => {
                            console.error('检查监控状态失败:', error);
                        });
                    }
                    
                    // 启动监控状态检查
                    function startMonitoringStatusCheck() {
                        // 每2秒检查一次监控状态
                        window.monitoringStatusInterval = setInterval(checkMonitoringStatus, 2000);
                    }
                    
                    // 日志相关变量
                    let autoScroll = true;
                    let logUpdateInterval;
                    let userScrolling = false;
                    
                    // ANSI颜色代码转换函数
                    function convertAnsiToHtml(text) {
                        // 直接使用字符串替换，避免正则表达式转义问题
                        let result = text;
                        
                        // ANSI颜色代码替换
                        result = result.replace(/\\033\\[30m/g, '<span style="color: #000000">'); // 黑色
                        result = result.replace(/\\033\\[31m/g, '<span style="color: #dc3545">'); // 红色
                        result = result.replace(/\\033\\[32m/g, '<span style="color: #28a745">'); // 绿色
                        result = result.replace(/\\033\\[33m/g, '<span style="color: #ffc107">'); // 黄色
                        result = result.replace(/\\033\\[34m/g, '<span style="color: #007bff">'); // 蓝色
                        result = result.replace(/\\033\\[35m/g, '<span style="color: #6f42c1">'); // 紫色
                        result = result.replace(/\\033\\[36m/g, '<span style="color: #17a2b8">'); // 青色
                        result = result.replace(/\\033\\[37m/g, '<span style="color: #ffffff">'); // 白色
                        result = result.replace(/\\033\\[0m/g, '</span>'); // 重置
                        result = result.replace(/\\033\\[1m/g, '<span style="font-weight: bold">'); // 粗体
                        result = result.replace(/\\033\\[4m/g, '<span style="text-decoration: underline">'); // 下划线
                        
                        return result;
                    }
                    
                    // 日志相关函数
                    function updateLogs() {
                        fetch('/api/logs')
                            .then(response => response.json())
                            .then(data => {
                                const logContainer = document.getElementById('logContainer');
                                if (data.logs && data.logs.length > 0) {
                                    logContainer.innerHTML = data.logs.map(log => {
                                        const convertedMessage = convertAnsiToHtml(log.message);
                                        return `<div class="log-entry ${log.level.toLowerCase()}">
                                            <span class="log-time">${log.time}</span>
                                            <span class="log-level">[${log.level}]</span>
                                            <span class="log-message">${convertedMessage}</span>
                                        </div>`;
                                    }).join('');
                                    
                                    if (autoScroll) {
                                        logContainer.scrollTop = logContainer.scrollHeight;
                                    }
                                } else {
                                    logContainer.innerHTML = '<div class="log-empty">暂无日志记录</div>';
                                }
                            })
                            .catch(error => {
                                console.error('获取日志失败:', error);
                                document.getElementById('logContainer').innerHTML = '<div class="log-error">日志加载失败</div>';
                            });
                    }
                    

                    

                    
                    // 自动保存单个输入框的值
                    function autoSavePosition(inputElement) {
                        const fieldName = inputElement.name;
                        const fieldValue = parseFloat(inputElement.value) || 0;
                        
                        // 创建只包含当前字段的数据对象
                        const positions = {};
                        positions[fieldName] = fieldValue;
                        
                        // 静默保存，不显示成功消息
                        fetch('/api/positions/save', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify(positions)
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (!data.success) {
                                console.error('自动保存失败:', data.message || '未知错误');
                            }
                        })
                        .catch(error => {
                            console.error('自动保存错误:', error);
                        });
                    }
                    

                    
                    // 页面加载完成后启动日志更新
                    document.addEventListener('DOMContentLoaded', function() {
                        updateLogs();
                        // 每5秒更新一次日志
                        logUpdateInterval = setInterval(updateLogs, 5000);
                        
                        // 页面加载时检查监控状态
                        checkMonitoringStatus();
                        // 启动定期监控状态检查
                        startMonitoringStatusCheck();
                        
                        // 监听日志容器的滚动事件
                        const logContainer = document.getElementById('logContainer');
                        if (logContainer) {
                            logContainer.addEventListener('scroll', function() {
                                // 检查是否滚动到底部（允许5px的误差）
                                const isAtBottom = logContainer.scrollTop >= (logContainer.scrollHeight - logContainer.clientHeight - 5);
                                
                                if (isAtBottom) {
                                    // 用户滚动到底部，重新启用自动滚动
                                    autoScroll = true;
                                    userScrolling = false;
                                } else {
                                    // 用户手动滚动到其他位置，停止自动滚动
                                    autoScroll = false;
                                    userScrolling = true;
                                }
                            });
                        }
                    });
                    
                    // 定期检查价格更新
                    function checkPriceUpdates() {
                        fetch('/api/status')
                            .then(response => response.json())
                            .then(data => {
                                // 更新UP1价格
                                const up1Input = document.getElementById('up1_price');
                                const down1Input = document.getElementById('down1_price');
                                
                                if (up1Input && data.yes1_price_entry && data.yes1_price_entry !== up1Input.value) {
                                    up1Input.value = data.yes1_price_entry;
                                }
                                
                                if (down1Input && data.no1_price_entry && data.no1_price_entry !== down1Input.value) {
                                    down1Input.value = data.no1_price_entry;
                                }
                            })
                            .catch(error => {
                                console.log('价格检查失败:', error);
                            });
                    }
                    
                    // 每2秒检查一次价格更新
                    setInterval(checkPriceUpdates, 2000);
                    </script>
                    
                    <!-- 交易记录表格 -->
                    <div style="max-width: 1160px; padding: 10px; background-color: #f8f9fa;">
                        
                        {% if data.cash_history and data.cash_history|length > 0 %}
                        <div style="overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <thead>
                                    <tr style="background: linear-gradient(135deg, #007bff, #0056b3); color: white;">
                                        <th style="padding: 12px; text-align: center; border: 1px solid #ddd;">日期</th>
                                        <th style="padding: 12px; text-align: center; border: 1px solid #ddd;">Cash</th>
                                        <th style="padding: 12px; text-align: center; border: 1px solid #ddd;">利润</th>
                                        <th style="padding: 12px; text-align: center; border: 1px solid #ddd;">利润率</th>
                                        <th style="padding: 12px; text-align: center; border: 1px solid #ddd;">总利润</th>
                                        <th style="padding: 12px; text-align: center; border: 1px solid #ddd;">总利润率</th>
                                        <th style="padding: 12px; text-align: center; border: 1px solid #ddd;">交易次数</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for record in data.cash_history[:91] %}
                                    <tr style="{% if loop.index % 2 == 0 %}background-color: #f8f9fa;{% endif %}">
                                        <td style="padding: 10px; text-align: center; border: 1px solid #ddd;">{{ record[0] }}</td>
                                        <td style="padding: 10px; text-align: center; border: 1px solid #ddd; font-weight: bold;">{{ record[1] }}</td>
                                        <td style="padding: 10px; text-align: center; border: 1px solid #ddd; color: {% if record[2]|float > 0 %}#28a745{% elif record[2]|float < 0 %}#dc3545{% else %}#6c757d{% endif %}; font-weight: bold;">{{ record[2] }}</td>
                                        <td style="padding: 10px; text-align: center; border: 1px solid #ddd; color: {% if record[3]|replace('%','')|float > 0 %}#28a745{% elif record[3]|replace('%','')|float < 0 %}#dc3545{% else %}#6c757d{% endif %};">{{ record[3] }}</td>
                                        <td style="padding: 10px; text-align: center; border: 1px solid #ddd; color: {% if record[4]|float > 0 %}#28a745{% elif record[4]|float < 0 %}#dc3545{% else %}#6c757d{% endif %}; font-weight: bold;">{{ record[4] }}</td>
                                        <td style="padding: 10px; text-align: center; border: 1px solid #ddd; color: {% if record[5]|replace('%','')|float > 0 %}#28a745{% elif record[5]|replace('%','')|float < 0 %}#dc3545{% else %}#6c757d{% endif %};">{{ record[5] }}</td>
                                        <td style="padding: 10px; text-align: center; border: 1px solid #ddd;">{{ record[6] if record|length > 6 else '' }}</td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                        <div style="text-align: center; margin-top: 15px; color: #6c757d; font-size: 14px;">
                            显示最近 91 条记录 | 总记录数: {{ data.cash_history|length }} 条 | 
                            <a href="http://localhost:5000/history" target="_blank" style="color: #007bff; text-decoration: none;">查看完整记录</a>
                        </div>
                        {% else %}
                        <div style="text-align: center; padding: 40px; color: #6c757d;">
                            <p style="font-size: 18px; margin: 0;">📈 暂无交易记录</p>
                            <p style="font-size: 14px; margin: 10px 0 0 0;">数据将在每日 0:30 自动记录</p>
                        </div>
                        {% endif %}
                        <div style="text-align: center; margin-top: 5px; padding: 10px; background-color: #e9ecef; border-radius: 5px; font-size: 12px; color: #6c757d;">
                            📅 数据来源：每日 0:30 自动记录 | 💾 数据持久化：追加模式，程序重启不丢失 | 🔄 页面实时：24小时在线，随时可访问
                        </div>
                    </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            from datetime import datetime
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return render_template_string(dashboard_template, data=current_data, current_time=current_time)
        
        @app.route("/start", methods=['POST'])
        def start_trading():
            """处理启动按钮点击事件"""
            try:
                data = request.get_json()
                url = data.get('url', '').strip()
                
                if not url:
                    return jsonify({'success': False, 'message': '请输入有效的URL地址'})
                
                # 更新URL到web_values
                self.set_web_value('url_entry', url)
                
                # 保存URL到配置文件
                self.config['website']['url'] = url
                self.save_config()
                
                # 启动监控
                self.start_monitoring()
                
                return jsonify({'success': True, 'message': '交易监控已启动'})
            except Exception as e:
                self.logger.error(f"启动交易失败: {str(e)}")
                return jsonify({'success': False, 'message': f'启动失败: {str(e)}'})
        
        @app.route("/stop", methods=['POST'])
        def stop_trading():
            """处理停止监控按钮点击事件"""
            try:
                # 调用完整的停止监控方法
                self.stop_monitoring()
                return jsonify({'success': True, 'message': '监控已停止'})
            except Exception as e:
                self.logger.error(f"停止监控失败: {str(e)}")
                return jsonify({'success': False, 'message': f'停止失败: {str(e)}'})
        
        @app.route("/api/browser_status", methods=['GET'])
        def get_browser_status():
            """获取浏览器状态API"""
            try:
                # 检查浏览器是否已连接
                browser_connected = self.driver is not None
                monitoring_active = self.running
                
                return jsonify({
                    'browser_connected': browser_connected,
                    'monitoring_active': monitoring_active,
                    'status': 'connected' if browser_connected else 'disconnected'
                })
            except Exception as e:
                self.logger.error(f"获取浏览器状态失败: {str(e)}")
                return jsonify({
                    'browser_connected': False,
                    'monitoring_active': False,
                    'status': 'error',
                    'error': str(e)
                })
        
        @app.route("/api/monitoring_status", methods=['GET'])
        def get_monitoring_status():
            """获取监控状态API"""
            try:
                # 检查监控状态
                monitoring_status = self.get_web_value('monitoring_status') or '未启动'
                monitoring_active = monitoring_status == '运行中'
                
                return jsonify({
                    'monitoring_active': monitoring_active,
                    'status': 'running' if monitoring_active else 'stopped'
                })
            except Exception as e:
                self.logger.error(f"获取监控状态失败: {str(e)}")
                return jsonify({
                    'monitoring_active': False,
                    'status': 'error',
                    'error': str(e)
                })
        
        @app.route("/api/status")
        def get_status():
            """获取实时状态数据API"""
            try:
                # 使用新的StatusDataManager获取数据
                current_data = self.status_data.get_legacy_format()
                return jsonify(current_data)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        # 新的标准接口
        @app.route("/api/status")
        def get_status_api():
            """获取实时状态数据API"""
            return get_status()
        
        # 保持向后兼容性，保留原/api/data接口
        @app.route("/api/data")
        def get_data():
            """获取实时数据API (向后兼容)"""
            return get_status()
        
        @app.route("/api/positions")
        def get_positions_api():
            """获取持仓信息API"""
            try:
                # 从StatusDataManager获取交易验证信息
                trade_verification = self.status_data.get('trade_verification', {})
                
                if trade_verification and all(key in trade_verification for key in ['direction', 'shares', 'price', 'amount']):
                    position = {
                        'direction': trade_verification['direction'],
                        'shares': trade_verification['shares'],
                        'price': trade_verification['price'],
                        'amount': trade_verification['amount']
                    }
                    return jsonify({
                        'success': True,
                        'position': position
                    })
                else:
                    return jsonify({
                        'success': False,
                        'position': None
                    })
            except Exception as e:
                self.logger.error(f"获取持仓信息失败: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'position': None
                }), 500
         
        @app.route("/history")
        def history():
            """交易历史记录页面"""
            # 分页参数
            page = request.args.get('page', 1, type=int)
            per_page = 91
            
            # 按日期排序（最新日期在前）
            sorted_history = sorted(self.cash_history, key=lambda x: self._parse_date_for_sort(x[0]), reverse=True)
            
            # 计算分页
            total = len(sorted_history)
            start = (page - 1) * per_page
            end = start + per_page
            history_page = sorted_history[start:end]
            total_pages = (total + per_page - 1) // per_page
            
            # 分页信息
            has_prev = page > 1
            has_next = end < total
            prev_num = page - 1 if has_prev else None
            next_num = page + 1 if has_next else None
            
            html_template = """
            <html>
            <head>
                <meta charset=\"utf-8\">
                <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
                <title>Polymarket自动交易记录</title>
                <style>
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; 
                        padding: 5px; margin: 0; background: #f8f9fa; 
                    }
                    .container { max-width: 900px; margin: 0 auto; background: white; padding: 5px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                    h2 { color: #333; text-align: center; margin-bottom: 20px; }
                    table { border-collapse: collapse; width: 100%; margin-bottom: 10px; }
                    th, td { border: 1px solid #ddd; padding: 10px; text-align: right; }
                    th { background: #f6f8fa; text-align: center; font-weight: 600; }
                    td:first-child { text-align: center; }
                    .positive { color: #28a745; font-weight: 500; }
                    .negative { color: #dc3545; font-weight: 500; }
                    .zero { color: #6c757d; }
                    .info { margin-top: 15px; padding: 10px; background: #e9ecef; border-radius: 4px; font-size: 14px; color: #666; }
                    .total { margin-top: 10px; text-align: center; font-weight: bold; font-size: 16px; }
                    .pagination { 
                        margin: 20px 0; text-align: center; 
                    }
                    .pagination a, .pagination span { 
                        display: inline-block; padding: 8px 12px; margin: 0 4px; 
                        border: 1px solid #ddd; text-decoration: none; border-radius: 4px;
                    }
                    .pagination a:hover { background: #f5f5f5; }
                    .pagination .current { background: #007bff; color: white; border-color: #007bff; }
                    .page-info { margin: 10px 0; text-align: center; color: #666; }
                </style>
            </head>
            <body>
                
                <div class=\"container\">
                    <h2>Polymarket自动交易记录</h2>
                    <div class=\"page-info\">
                        显示第 {{ start + 1 if total > 0 else 0 }}-{{ end if end <= total else total }} 条，共 {{ total }} 条记录（第 {{ page }} / {{ total_pages }} 页）
                    </div>
                    <table>
                        <tr>
                            <th>日期</th>
                            <th>Cash</th>
                            <th>利润</th>
                            <th>利润率</th>
                            <th>总利润</th>
                            <th>总利润率</th>
                            <th>交易次数</th>
                        </tr>
                        {% for row in history_page %}
                        {% set profit = (row[2] | float) %}
                        {% set profit_rate = (row[3] | float) %}
                        {% set total_profit = (row[4] | float) if row|length > 4 else 0 %}
                        {% set total_profit_rate = (row[5] | float) if row|length > 5 else 0 %}
                        {% set trade_times = row[6] if row|length > 6 else '' %}
                        <tr>
                            <td>{{ row[0] }}</td>
                            <td>{{ row[1] }}</td>
                            <td class=\"{{ 'positive' if profit > 0 else ('negative' if profit < 0 else 'zero') }}\">
                                {{ row[2] }}
                            </td>
                            <td class=\"{{ 'positive' if profit_rate > 0 else ('negative' if profit_rate < 0 else 'zero') }}\">
                                {{ '%.2f%%' % (profit_rate * 100) }}
                            </td>
                            <td class=\"{{ 'positive' if total_profit > 0 else ('negative' if total_profit < 0 else 'zero') }}\">
                                {{ row[4] }}
                            </td>
                            <td class=\"{{ 'positive' if total_profit_rate > 0 else ('negative' if total_profit_rate < 0 else 'zero') }}\">
                                {{ '%.2f%%' % (total_profit_rate * 100) }}
                            </td>
                            <td>{{ trade_times }}</td>
                        </tr>
                        {% endfor %}
                    </table>
                    
                    {% if total > per_page %}
                    <div class=\"pagination\">
                        {% if has_prev %}
                            <a href=\"?page={{ prev_num }}\">&laquo; 上一页</a>
                        {% endif %}
                        
                        {% for p in range(1, total_pages + 1) %}
                            {% if p == page %}
                                <span class=\"current\">{{ p }}</span>
                            {% else %}
                                <a href=\"?page={{ p }}\">{{ p }}</a>
                            {% endif %}
                        {% endfor %}
                        
                        {% if has_next %}
                            <a href=\"?page={{ next_num }}\">下一页 &raquo;</a>
                        {% endif %}
                    </div>
                    {% endif %}
                    
                    <div class=\"total\">
                        总记录数: {{ total }} 条
                    </div>
                    <div class=\"info\">
                        📅 数据来源：每日 0:30 自动记录<br>
                        💾 数据持久化：追加模式，程序重启不丢失<br>
                        🔄 页面实时：24小时在线，随时可访问<br>
                        📄 分页显示：每页最多 {{ per_page }} 条记录
                </div>
            </body>
            </html>
            """
            return render_template_string(html_template, 
                                        history_page=history_page, 
                                        total=total,
                                        page=page,
                                        start=start,
                                        end=end,
                                        per_page=per_page,
                                        has_prev=has_prev,
                                        has_next=has_next,
                                        prev_num=prev_num,
                                        next_num=next_num,
                                        total_pages=total_pages)
        
        @app.route("/api/update_coin", methods=["POST"])
        def update_coin():
            """更新币种API"""
            try:
                data = request.get_json()
                coin = data.get('coin', '').strip()
                
                if not coin:
                    return jsonify({'success': False, 'message': '请选择币种'})
                
                # 更新币种到web_data
                self.set_web_value('coin_combobox', coin)
                
                # 直接更新StatusDataManager中的币种信息
                self.status_data.update('trading', 'selected_coin', coin)
                
                # 保存到配置文件
                if 'trading' not in self.config:
                    self.config['trading'] = {}
                self.config['trading']['coin'] = coin
                self.save_config()
                
                # 调用币种变化处理函数
                self.on_coin_changed()
                
                self.logger.info(f"币种已更新为: {coin}")
                return jsonify({'success': True, 'message': f'币种已更新为: {coin}'})
                
            except Exception as e:
                self.logger.error(f"更新币种失败: {e}")
                return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})
        
        @app.route("/api/update_time", methods=["POST"])
        def update_time():
            """更新时间API"""
            try:
                data = request.get_json()
                time = data.get('time', '').strip()
                
                if not time:
                    return jsonify({'success': False, 'message': '请选择时间'})
                
                # 更新时间到web_data
                self.set_web_value('auto_find_time_combobox', time)
                
                # 直接更新StatusDataManager中的时间信息
                self.status_data.update('trading', 'auto_find_time', time)
                
                # 保存到配置文件
                if 'trading' not in self.config:
                    self.config['trading'] = {}
                self.config['trading']['auto_find_time'] = time
                self.save_config()
                
                # 调用时间变化处理函数
                self.on_auto_find_time_changed()
                
                self.logger.info(f"时间已更新为: {time}")
                return jsonify({'success': True, 'message': f'时间已更新为: {time}'})
                
            except Exception as e:
                self.logger.error(f"更新时间失败: {e}")
                return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})
        
        @app.route("/api/update_prices", methods=["POST"])
        def update_prices():
            """更新价格API"""
            try:
                data = request.get_json()
                up1_price = data.get('up1_price', '')
                down1_price = data.get('down1_price', '')
                
                # 更新内存中的价格数据
                if up1_price:
                    self.set_web_value('yes1_price_entry', up1_price)
                if down1_price:
                    self.set_web_value('no1_price_entry', down1_price)
                
                self.logger.info(f"价格已更新 - UP1: {up1_price}, DOWN1: {down1_price}")
                return jsonify({'success': True, 'message': '价格更新成功', 'up1_price': up1_price, 'down1_price': down1_price})
                
            except Exception as e:
                self.logger.error(f"更新价格失败: {e}")
                return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})
        
        @app.route("/api/logs", methods=['GET'])
        def get_logs():
            """获取系统日志"""
            try:
                logs = []
                # 只读取%h/poly_16/logs/目录下的最新日志文件（监控目录）
                latest_log_file = Logger.get_latest_log_file()
                if latest_log_file and os.path.exists(latest_log_file):
                    with open(latest_log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()[-100:]  # 最近100行
                        for line in lines:
                            line = line.strip()
                            if line:
                                # 解析日志格式: 时间 - 级别 - 消息
                                parts = line.split(' - ', 2)
                                if len(parts) >= 3:
                                    logs.append({
                                        'time': parts[0],
                                        'level': parts[1],
                                        'message': parts[2]
                                    })
                                else:
                                    logs.append({
                                        'time': datetime.now().strftime('%H:%M:%S'),
                                        'level': 'INFO',
                                        'message': line
                                    })
                else:
                    # 如果找不到日志文件，返回提示信息
                    logs.append({
                        'time': datetime.now().strftime('%H:%M:%S'),
                        'level': 'INFO',
                        'message': '未找到%h/poly_16/logs/目录下的日志文件'
                    })
                
                return jsonify({'success': True, 'logs': logs})
            except Exception as e:
                return jsonify({'success': False, 'logs': [], 'error': str(e)})
        
        @app.route("/api/logs/clear", methods=['POST'])
        def clear_logs():
            """清空日志"""
            try:
                # 只清空%h/poly_16/logs/目录下的最新日志文件（监控目录）
                latest_log_file = Logger.get_latest_log_file()
                if latest_log_file and os.path.exists(latest_log_file):
                    with open(latest_log_file, 'w', encoding='utf-8') as f:
                        f.write('')
                
                self.logger.info("监控目录日志已清空")
                return jsonify({'success': True, 'message': '监控目录日志已清空'})
            except Exception as e:
                return jsonify({'success': False, 'message': f'清空日志失败: {str(e)}'})
        
        @app.route("/api/positions/save", methods=['POST'])
        def save_positions():
            """保存交易仓位设置"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'success': False, 'message': '无效的数据'})
                
                # 获取当前配置以便比较变化
                current_positions = self.config.get('positions', {})
                
                # 获取现有的positions配置，如果不存在则创建空字典
                if 'positions' not in self.config:
                    self.config['positions'] = {}
                positions_config = self.config['positions'].copy()
                
                # 只更新实际传入的字段，保持其他字段不变
                for field_name, field_value in data.items():
                    positions_config[field_name] = field_value
                
                # 更新内存中的配置
                self.config['positions'] = positions_config
                
                # 同时更新web_data，确保交易逻辑能获取到最新的价格和金额
                # 建立字段映射关系
                field_mapping = {
                    'up1_price': 'yes1_price_entry',
                    'up1_amount': 'yes1_amount_entry',
                    'up2_price': 'yes2_price_entry',
                    'up2_amount': 'yes2_amount_entry',
                    'up3_price': 'yes3_price_entry',
                    'up3_amount': 'yes3_amount_entry',
                    'up4_price': 'yes4_price_entry',
                    'up4_amount': 'yes4_amount_entry',
                    'down1_price': 'no1_price_entry',
                    'down1_amount': 'no1_amount_entry',
                    'down2_price': 'no2_price_entry',
                    'down2_amount': 'no2_amount_entry',
                    'down3_price': 'no3_price_entry',
                    'down3_amount': 'no3_amount_entry',
                    'down4_price': 'no4_price_entry',
                    'down4_amount': 'no4_amount_entry'
                }
                
                # 只更新实际传入的字段
                for field_name, field_value in data.items():
                    if field_name in field_mapping:
                        self.set_web_value(field_mapping[field_name], str(field_value))
                
                # 保存到文件
                self.save_config()
                
                # 只记录实际发生变化的字段，使用简洁的日志格式
                log_field_mapping = {
                    'up1_price': 'UP1 价格',
                    'up1_amount': 'UP1 金额',
                    'up2_price': 'UP2 价格',
                    'up2_amount': 'UP2 金额',
                    'up3_price': 'UP3 价格',
                    'up3_amount': 'UP3 金额',
                    'up4_price': 'UP4 价格',
                    'up4_amount': 'UP4 金额',
                    'down1_price': 'DOWN1 价格',
                    'down1_amount': 'DOWN1 金额',
                    'down2_price': 'DOWN2 价格',
                    'down2_amount': 'DOWN2 金额',
                    'down3_price': 'DOWN3 价格',
                    'down3_amount': 'DOWN3 金额',
                    'down4_price': 'DOWN4 价格',
                    'down4_amount': 'DOWN4 金额'
                }
                
                # 检查并记录变化的字段
                for field, value in data.items():
                    current_value = current_positions.get(field, 0)
                    if float(value) != float(current_value):
                        field_name = log_field_mapping.get(field, field)
                        self.logger.info(f"{field_name}设置为 {value}")
                
                return jsonify({'success': True, 'message': '交易仓位设置已保存'})
            except Exception as e:
                self.logger.error(f"保存交易仓位失败: {str(e)}")
                return jsonify({'success': False, 'message': f'保存失败: {str(e)}'})

        @app.route('/api/start_chrome', methods=['POST'])
        def start_chrome():
            """启动Chrome浏览器"""
            try:
                self.start_chrome_ubuntu()
                
                return jsonify({'success': True, 'message': 'Chrome浏览器启动成功'})
            except Exception as e:
                self.logger.error(f"启动Chrome浏览器失败: {str(e)}")
                return jsonify({'success': False, 'message': f'启动失败: {str(e)}'})

        @app.route('/api/restart_program', methods=['POST'])
        def restart_program():
            """重启程序"""
            try:
                self.logger.info("收到程序重启请求")
                
                # 执行重启命令
                current_user = os.getenv('USER') or os.getenv('USERNAME') or 'admin'
                service_name = f'run-poly.service'
                result = subprocess.run(['sudo', 'systemctl', 'restart', service_name], 
                                      capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    self.logger.info("程序重启命令执行成功")
                    return jsonify({'success': True, 'message': '程序重启命令已发送'})
                else:
                    error_msg = result.stderr or result.stdout or '未知错误'
                    self.logger.error(f"程序重启命令执行失败: {error_msg}")
                    return jsonify({'success': False, 'message': f'重启失败: {error_msg}'})
                    
            except subprocess.TimeoutExpired:
                self.logger.error("程序重启命令执行超时")
                return jsonify({'success': False, 'message': '重启命令执行超时'})
            except Exception as e:
                self.logger.error(f"程序重启失败: {str(e)}")
                return jsonify({'success': False, 'message': f'重启失败: {str(e)}'})

        return app

    def check_and_kill_port_processes(self, port):
        """检查端口是否被占用，如果被占用则强制杀死占用进程"""
        try:
            killed_processes = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    # 获取进程的网络连接
                    connections = proc.net_connections()
                    if connections:
                        for conn in connections:
                            if hasattr(conn, 'laddr') and conn.laddr and conn.laddr.port == port:
                                proc_name = proc.info['name']
                                proc_pid = proc.info['pid']
                                self.logger.warning(f"🔍 发现端口 {port} 被进程占用: {proc_name} (PID: {proc_pid})")
                                
                                # 强制杀死进程
                                proc.terminate()
                                try:
                                    proc.wait(timeout=3)
                                except psutil.TimeoutExpired:
                                    proc.kill()
                                    proc.wait()
                                
                                killed_processes.append(f"{proc_name} (PID: {proc_pid})")
                                self.logger.info(f"💀 已强制杀死进程: {proc_name} (PID: {proc_pid})")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            if killed_processes:
                self.logger.info(f"🧹 端口 {port} 清理完成，已杀死 {len(killed_processes)} 个进程")
                time.sleep(1)  # 等待端口释放
            else:
                self.logger.info(f"✅ 端口 {port} 未被占用")
                
        except Exception as e:
            self.logger.error(f"检查端口 {port} 时出错: {e}")

    def start_flask_server(self):
        """在后台线程中启动Flask，24小时常驻"""
        # 从环境变量读取配置，默认值为localhost:5000
        flask_host = os.environ.get('FLASK_HOST', '127.0.0.1')
        flask_port = int(os.environ.get('FLASK_PORT', '5000'))
        
        # 检查并清理端口占用
        self.logger.info(f"🔍 检查端口 {flask_port} 是否被占用...")
        self.check_and_kill_port_processes(flask_port)
        
        def run():
            try:
                # 关闭Flask详细日志
                import logging as flask_logging
                log = flask_logging.getLogger('werkzeug')
                log.setLevel(flask_logging.ERROR)
                
                self.flask_app.run(host=flask_host, port=flask_port, debug=False, use_reloader=False)
            except Exception as e:
                self.logger.error(f"Flask启动失败: {e}")
                # 如果启动失败，再次尝试清理端口
                if "Address already in use" in str(e) or "端口" in str(e):
                    self.logger.warning(f"🔄 端口 {flask_port} 仍被占用，再次尝试清理...")
                    self.check_and_kill_port_processes(flask_port)
                    time.sleep(2)
                    try:
                        self.flask_app.run(host=flask_host, port=flask_port, debug=False, use_reloader=False)
                    except Exception as retry_e:
                        self.logger.error(f"重试启动Flask失败: {retry_e}")
        
        flask_thread = threading.Thread(target=run, daemon=True)
        flask_thread.start()
        
        # 根据配置显示访问地址
        if flask_host == '127.0.0.1' or flask_host == 'localhost':
            self.logger.info(f"✅ Flask服务已启动，监听端口: {flask_port}")
            self.logger.info("🔒 服务仅监听本地地址，通过NGINX反向代理访问")
        else:
            self.logger.info(f"✅ Flask服务已启动，监听端口: {flask_port}")

    def schedule_record_cash_daily(self):
        """安排每天 0:30 记录现金到CSV"""
        now = datetime.now()
        next_run = now.replace(hour=0, minute=30, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)
        wait_time = (next_run - now).total_seconds()
        self.logger.info(f"📅 已安排在 {next_run.strftime('%Y-%m-%d %H:%M:%S')} 记录Cash到CSV")
        self.record_and_show_cash_timer = threading.Timer(wait_time, self.record_cash_daily)
        self.record_and_show_cash_timer.daemon = True
        self.record_and_show_cash_timer.start()

    def record_cash_daily(self):
        """实际记录逻辑：读取GUI Cash，计算并追加到CSV"""
        try:
            # 从GUI读取cash值
            cash_text = self.zero_time_cash_label.cget("text")  # 例如 "Cash: 123.45"
            if ":" in cash_text:
                cash_value = cash_text.split(":", 1)[1].strip()
            else:
                cash_value = cash_text.strip()
            
            date_str = datetime.now().strftime("%Y-%m-%d")
            self.logger.info(f"获取到零点时间CASH: {cash_value}")
            
            # 追加到CSV
            self.append_cash_record(date_str, cash_value)
            
        except Exception as e:
            self.logger.error(f"记录每日Cash失败: {e}")
        finally:
            # 安排下一天的任务
            self.schedule_record_cash_daily()

    def record_and_show_cash(self):
        """兼容旧接口：直接调用记录逻辑"""
        self.record_cash_daily()

if __name__ == "__main__":
    try:
        # 打印启动参数，用于调试
        
        # 初始化日志
        logger = Logger("main")
            
        # 创建并运行主程序
        app = CryptoTrader()
        app.root.mainloop()
        
    except Exception as e:
        print(f"程序启动失败: {str(e)}")
        if 'logger' in locals():
            logger.error(f"程序启动失败: {str(e)}")
        sys.exit(1)
    
