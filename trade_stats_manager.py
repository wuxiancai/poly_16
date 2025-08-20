#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易统计管理器
独立模块，不依赖 watchdog
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock
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
            try:
                # 解析时间戳
                if isinstance(timestamp, str):
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    dt = timestamp
                
                date_key = dt.strftime('%Y-%m-%d')
                hour_key = dt.hour
                
                # 初始化数据结构
                if date_key not in self.data:
                    self.data[date_key] = {'hourly': [0] * 24, 'total': 0}
                
                # 更新统计
                self.data[date_key]['hourly'][hour_key] += 1
                self.data[date_key]['total'] += 1
                
                # 保存数据
                self._save_data()
                
            except Exception as e:
                logging.error(f"添加交易记录失败: {e}")
    
    def get_daily_stats(self, date_str):
        """获取指定日期的统计数据"""
        with self.lock:
            if date_str in self.data:
                day_data = self.data[date_str]
                return {
                    'date': date_str,
                    'total_trades': day_data['total'],
                    'hourly_data': day_data['hourly'],
                    'peak_hour': f"{day_data['hourly'].index(max(day_data['hourly']))}:00" if max(day_data['hourly']) > 0 else "--:--",
                    'avg_per_hour': round(day_data['total'] / 24, 2)
                }
            else:
                return {
                    'date': date_str,
                    'total_trades': 0,
                    'hourly_data': [0] * 24,
                    'peak_hour': "--:--",
                    'avg_per_hour': 0
                }
    
    def get_weekly_stats(self, date_str):
        """获取指定日期所在周的统计数据"""
        with self.lock:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d')
                # 获取周一的日期
                monday = target_date - timedelta(days=target_date.weekday())
                
                weekly_data = [0] * 24
                total_trades = 0
                
                # 统计一周的数据
                for i in range(7):
                    day = monday + timedelta(days=i)
                    day_key = day.strftime('%Y-%m-%d')
                    if day_key in self.data:
                        day_data = self.data[day_key]
                        total_trades += day_data['total']
                        for hour in range(24):
                            weekly_data[hour] += day_data['hourly'][hour]
                
                return {
                    'week_start': monday.strftime('%Y-%m-%d'),
                    'week_end': (monday + timedelta(days=6)).strftime('%Y-%m-%d'),
                    'total_trades': total_trades,
                    'hourly_data': weekly_data,
                    'peak_hour': f"{weekly_data.index(max(weekly_data))}:00" if max(weekly_data) > 0 else "--:--",
                    'avg_per_hour': round(total_trades / (24 * 7), 2)
                }
            except Exception as e:
                logging.error(f"获取周统计失败: {e}")
                return {
                    'week_start': date_str,
                    'week_end': date_str,
                    'total_trades': 0,
                    'hourly_data': [0] * 24,
                    'peak_hour': "--:--",
                    'avg_per_hour': 0
                }
    
    def get_monthly_stats(self, date_str):
        """获取指定日期所在月的统计数据"""
        with self.lock:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d')
                year_month = target_date.strftime('%Y-%m')
                
                monthly_data = [0] * 24
                total_trades = 0
                
                # 统计整月的数据
                for date_key, day_data in self.data.items():
                    if date_key.startswith(year_month):
                        total_trades += day_data['total']
                        for hour in range(24):
                            monthly_data[hour] += day_data['hourly'][hour]
                
                # 计算月份天数
                if target_date.month == 12:
                    next_month = target_date.replace(year=target_date.year + 1, month=1, day=1)
                else:
                    next_month = target_date.replace(month=target_date.month + 1, day=1)
                
                first_day = target_date.replace(day=1)
                days_in_month = (next_month - first_day).days
                
                return {
                    'month': year_month,
                    'total_trades': total_trades,
                    'hourly_data': monthly_data,
                    'peak_hour': f"{monthly_data.index(max(monthly_data))}:00" if max(monthly_data) > 0 else "--:--",
                    'avg_per_hour': round(total_trades / (24 * days_in_month), 2)
                }
            except Exception as e:
                logging.error(f"获取月统计失败: {e}")
                return {
                    'month': date_str[:7],
                    'total_trades': 0,
                    'hourly_data': [0] * 24,
                    'peak_hour': "--:--",
                    'avg_per_hour': 0
                }