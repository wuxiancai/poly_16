#!/bin/bash

LOGFILE="/var/log/clean_memory.log"
echo "[$(date)] 开始释放内存、SWAP，并清理 ChromeDebug 缓存" >> "$LOGFILE"

# 判断可用内存（单位 KB）
MEM_AVAILABLE=$(awk '/MemAvailable:/ {print $2}')
if [ "$MEM_AVAILABLE" -lt 400000 ]; then
  echo "[$(date)] 可用内存过低 (${MEM_AVAILABLE}KB)，跳过操作" >> "$LOGFILE"
  exit 0
fi

# Chrome 缓存路径
CACHE_DIR="$HOME/ChromeDebug/Default/Cache"

# 判断缓存大小（单位 KB），如果大于 200MB 才清理
if [ -d "$CACHE_DIR" ]; then
  CACHE_SIZE_KB=$(du -sk "$CACHE_DIR" | awk '{print $1}')
  if [ "$CACHE_SIZE_KB" -gt 200000 ]; then
    echo "[$(date)] ChromeDebug 缓存过大 ($(($CACHE_SIZE_KB/1024))MB)，执行清理" >> "$LOGFILE"
    rm -rf "$CACHE_DIR"/*
  else
    echo "[$(date)] ChromeDebug 缓存仅为 $(($CACHE_SIZE_KB/1024))MB，跳过清理" >> "$LOGFILE"
  fi
else
  echo "[$(date)] 未找到缓存目录: $CACHE_DIR" >> "$LOGFILE"
fi

# 释放 PageCache
sync && echo 1 > /proc/sys/vm/drop_caches
echo "[$(date)] 已释放内存缓存" >> "$LOGFILE"

# 判断 swap 是否超过 100MB，再释放
SWAP_USED=$(free | awk '/Swap:/ {print $3}')
if [ "$SWAP_USED" -gt 102400 ]; then
  echo "[$(date)] SWAP 使用 $(($SWAP_USED/1024))MB，开始释放..." >> "$LOGFILE"
  swapoff -a && sleep 1 && swapon -a
  echo "[$(date)] SWAP 已释放" >> "$LOGFILE"
else
  echo "[$(date)] SWAP 使用较少，跳过" >> "$LOGFILE"
fi