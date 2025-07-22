#!/bin/bash

# 设置触发阈值（单位：KB）
THRESHOLD_KB=$((400 * 1024))  # 400MB

# 检查当前是否已有 swap
if swapon --noheadings --show | grep -q '/swapfile'; then
    echo "[INFO] Swap 已启用，跳过配置。"
    exit 0
fi

# 获取当前可用内存（单位：KB）
AVAILABLE_KB=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)

echo "[INFO] 当前可用内存：$((AVAILABLE_KB / 1024)) MB"

# 判断是否小于阈值
if [ "$AVAILABLE_KB" -lt "$THRESHOLD_KB" ]; then
    echo "[INFO] 可用内存低于 400MB,开始创建 Swap..."

    # 创建 swap 文件
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile

    # 开机自动挂载
    if ! grep -q '/swapfile' /etc/fstab; then
        echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    fi

    # 调整 swappiness，降低频繁使用 swap 的概率
    sudo sysctl vm.swappiness=10
    echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

    echo "[SUCCESS] Swap 启用完成，共 2GB."
else
    echo "[INFO] 当前可用内存大于 400MB,暂不启用 Swap。"
fi