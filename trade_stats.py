#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化交易日志统计与可视化系统
实时监听交易日志，统计买入成功事件，提供Web可视化界面
"""

import json
import os
import re
import time
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Thread, Lock
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from flask import Flask, jsonify, render_template, request
import logging

class TradeStatsManager:
    """
    交易统计管理器
    负责数据存储、统计计算和API服务
    """
    
    def __init__(self, data_file='trade_stats.json'):
        self.data_file = data_file
        self.data = self._load_data()
        self.lock = Lock()  # 线程安全锁
        
    def _load_data(self):
        """加载统计数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save_data(self):
        """保存统计数据"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logging.error(f"保存数据失败: {e}")
    
    def add_trade_record(self, timestamp):
        """添加交易记录"""
        with self.lock:
            date_str = timestamp.strftime('%Y-%m-%d')
            hour = timestamp.hour
            
            if date_str not in self.data:
                self.data[date_str] = {}
            
            if str(hour) not in self.data[date_str]:
                self.data[date_str][str(hour)] = 0
            
            self.data[date_str][str(hour)] += 1
            self._save_data()
            
            logging.info(f"记录交易: {date_str} {hour}:00 (总计: {self.data[date_str][str(hour)]})")
    
    def get_daily_stats(self, date_str):
        """获取日统计数据"""
        with self.lock:
            day_data = self.data.get(date_str, {})
            
            # 初始化24小时数据
            counts = [0] * 24
            for hour_str, count in day_data.items():
                hour = int(hour_str)
                if 0 <= hour <= 23:
                    counts[hour] = count
            
            # 计算百分比
            total = sum(counts)
            percentages = [round(count / total * 100, 1) if total > 0 else 0 for count in counts]
            
            return {
                'date': date_str,
                'counts': counts,
                'percentages': percentages,
                'total': total
            }
    
    def get_weekly_stats(self, date_str):
        """获取周统计数据"""
        with self.lock:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
            # 找到本周一
            monday = target_date - timedelta(days=target_date.weekday())
            
            weekly_counts = [0] * 24
            dates = []
            
            for i in range(7):
                current_date = monday + timedelta(days=i)
                date_key = current_date.strftime('%Y-%m-%d')
                dates.append(date_key)
                
                day_data = self.data.get(date_key, {})
                for hour_str, count in day_data.items():
                    hour = int(hour_str)
                    if 0 <= hour <= 23:
                        weekly_counts[hour] += count
            
            total = sum(weekly_counts)
            percentages = [round(count / total * 100, 1) if total > 0 else 0 for count in weekly_counts]
            
            return {
                'week_start': monday.strftime('%Y-%m-%d'),
                'dates': dates,
                'counts': weekly_counts,
                'percentages': percentages,
                'total': total
            }
    
    def get_monthly_stats(self, date_str):
        """获取月统计数据"""
        with self.lock:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
            # 本月第一天
            first_day = target_date.replace(day=1)
            
            # 本月最后一天
            if target_date.month == 12:
                last_day = target_date.replace(year=target_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                last_day = target_date.replace(month=target_date.month + 1, day=1) - timedelta(days=1)
            
            monthly_counts = [0] * 24
            dates = []
            
            current_date = first_day
            while current_date <= last_day:
                date_key = current_date.strftime('%Y-%m-%d')
                dates.append(date_key)
                
                day_data = self.data.get(date_key, {})
                for hour_str, count in day_data.items():
                    hour = int(hour_str)
                    if 0 <= hour <= 23:
                        monthly_counts[hour] += count
                
                current_date += timedelta(days=1)
            
            total = sum(monthly_counts)
            percentages = [round(count / total * 100, 1) if total > 0 else 0 for count in monthly_counts]
            
            return {
                'month': target_date.strftime('%Y-%m'),
                'dates': dates,
                'counts': monthly_counts,
                'percentages': percentages,
                'total': total
            }

class LogMonitor(FileSystemEventHandler):
    """
    日志文件监听器
    监听日志文件变化，解析交易成功事件
    """
    
    def __init__(self, stats_manager, log_file_pattern=r'.*\.log$'):
        self.stats_manager = stats_manager
        self.log_file_pattern = re.compile(log_file_pattern)
        self.trade_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*交易验证成功.*Bought')
        
    def on_modified(self, event):
        """文件修改事件处理"""
        if event.is_directory:
            return
            
        if self.log_file_pattern.search(event.src_path):
            self._parse_log_file(event.src_path)
    
    def _parse_log_file(self, file_path):
        """解析日志文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # 只读取文件末尾的新内容
                f.seek(0, 2)  # 移动到文件末尾
                file_size = f.tell()
                
                # 读取最后1KB的内容（避免读取整个文件）
                read_size = min(1024, file_size)
                f.seek(max(0, file_size - read_size))
                content = f.read()
                
                # 查找交易成功记录
                matches = self.trade_pattern.findall(content)
                for timestamp_str in matches:
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        self.stats_manager.add_trade_record(timestamp)
                    except ValueError:
                        continue
                        
        except (IOError, UnicodeDecodeError) as e:
            logging.error(f"读取日志文件失败 {file_path}: {e}")

# Flask Web应用
app = Flask(__name__)
stats_manager = TradeStatsManager()

@app.route('/')
def index():
    """主页"""
    return render_template('trade_stats.html')

@app.route('/trade_stats.html')
def trade_stats_page():
    return render_template('trade_stats.html')

@app.route('/api/trades/daily')
def get_daily_trades():
    """获取日统计数据"""
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    return jsonify(stats_manager.get_daily_stats(date))

@app.route('/api/trades/weekly')
def get_weekly_trades():
    """获取周统计数据"""
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    return jsonify(stats_manager.get_weekly_stats(date))

@app.route('/api/trades/monthly')
def get_monthly_trades():
    """获取月统计数据"""
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    return jsonify(stats_manager.get_monthly_stats(date))

def start_log_monitoring(log_directory='.'):
    """启动日志监听"""
    event_handler = LogMonitor(stats_manager)
    observer = Observer()
    observer.schedule(event_handler, log_directory, recursive=False)
    observer.start()
    
    logging.info(f"开始监听日志目录: {log_directory}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    # 启动日志监听（在后台线程中）
    log_thread = Thread(target=start_log_monitoring, daemon=True)
    log_thread.start()
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=5000, debug=False)