#!/bin/bash

CHROME_PROFILE="$HOME/ChromeDebug"

echo "🛠️ 正在尝试解除 Chrome 锁定：$CHROME_PROFILE"

# 1. 彻底终止使用该目录的 Chrome 进程
echo "🔍 查找并终止使用该目录的 Chrome 进程..."
PIDS=$(ps aux | grep "chrome.*--user-data-dir=$CHROME_PROFILE" | grep -v grep | awk '{print $2}')
if [ -n "$PIDS" ]; then
  echo "🔪 杀死以下进程: $PIDS"
  kill -9 $PIDS
else
  echo "✅ 没有发现活跃进程"
fi

# 2. 删除锁文件
echo "🗑️ 删除锁文件..."
rm -f "$CHROME_PROFILE/SingletonLock"
rm -f "$CHROME_PROFILE/SingletonSocket"
rm -f "$CHROME_PROFILE/SingletonCookie"
rm -f "$CHROME_PROFILE/lockfile"
rm -f "$CHROME_PROFILE/.pid"

# 3. 确认删除
echo "📂 剩余锁文件："
ls -l "$CHROME_PROFILE" | grep -i 'Singleton\|lock\|\.pid'

# 4. 提示重启
echo "🚀 你现在可以尝试重新启动 Chrome："
echo "google-chrome --user-data-dir=$CHROME_PROFILE &"