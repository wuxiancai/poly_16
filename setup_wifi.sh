#!/usr/bin/env bash
set -euo pipefail

# 需要 root
if [ "$EUID" -ne 0 ]; then
  echo "请用 sudo 运行：sudo bash setup_wifi.sh"
  exit 1
fi

NETPLAN_DIR="/etc/netplan"
OUT_FILE="$NETPLAN_DIR/99-wifi-multi.yaml"

# 检测无线网卡（存在 wireless 目录即认为是 Wi-Fi 设备）
mapfile -t WIFI_IFACES < <(for p in /sys/class/net/*; do
  iface=$(basename "$p")
  [ -d "/sys/class/net/$iface/wireless" ] && echo "$iface"
done)

if [ ${#WIFI_IFACES[@]} -eq 0 ]; then
  echo "❌ 未发现无线网卡。可用 'ip link' 或 'lshw -C network' 排查。"
  exit 1
fi

if [ ${#WIFI_IFACES[@]} -eq 1 ]; then
  IFACE="${WIFI_IFACES[0]}"
else
  echo "检测到多个无线网卡，请选择："
  select opt in "${WIFI_IFACES[@]}"; do
    [ -n "${opt:-}" ] && IFACE="$opt" && break
  done
fi
echo "✅ 使用无线网卡：$IFACE"

# 检测现有 renderer（NetworkManager 或 networkd），若没有则留空以使用系统默认
CURRENT_RENDERER=$(grep -RhoE 'renderer:\s*(NetworkManager|networkd)' "$NETPLAN_DIR"/*.yaml 2>/dev/null | head -n1 | awk '{print $2}')
if [ -n "${CURRENT_RENDERER:-}" ]; then
  RENDERER_LINE="  renderer: $CURRENT_RENDERER"
  echo "✅ 继承 renderer：$CURRENT_RENDERER"
else
  RENDERER_LINE=""
  echo "ℹ️ 未检测到 renderer，使用系统默认。"
fi

# 交互输入两个 Wi-Fi
read -rp "请输入 Wi-Fi #1 SSID: " SSID1
read -rsp "请输入 \"$SSID1\" 的密码: " PASS1; echo
read -rp "Wi-Fi #1 优先级(数字, 回车默认10，数值越大优先级越高): " PRIO1; PRIO1=${PRIO1:-10}

read -rp "请输入 Wi-Fi #2 SSID: " SSID2
read -rsp "请输入 \"$SSID2\" 的密码: " PASS2; echo
read -rp "Wi-Fi #2 优先级(数字, 回车默认5): " PRIO2; PRIO2=${PRIO2:-5}

read -rp "是否设置国家代码(如 CN/US，回车跳过): " COUNTRY

# 备份旧文件
if [ -f "$OUT_FILE" ]; then
  cp -a "$OUT_FILE" "$OUT_FILE.bak.$(date +%s)"
  echo "🔁 已备份旧文件：$OUT_FILE.bak.$(date +%s)"
fi

# 生成合并配置（不改动原始 50-cloud-init.yaml 等文件）
{
  echo "# 自动生成于 $(date -Is)"
  echo "network:"
  echo "  version: 2"
  [ -n "$RENDERER_LINE" ] && echo "$RENDERER_LINE"
  echo "  wifis:"
  echo "    $IFACE:"
  echo "      dhcp4: true"
  echo "      optional: true"
  [ -n "$COUNTRY" ] && echo "      country: $COUNTRY"
  echo "      access-points:"
  echo "        \"$SSID1\":"
  echo "          password: \"$PASS1\""
  echo "          priority: $PRIO1"
  echo "        \"$SSID2\":"
  echo "          password: \"$PASS2\""
  echo "          priority: $PRIO2"
} > "$OUT_FILE"

echo "📝 已写入：$OUT_FILE"
echo "⏳ 应用 netplan ..."
if ! netplan apply 2>/tmp/netplan.apply.err; then
  echo "❌ netplan apply 失败，输出调试信息："
  netplan --debug apply || true
  echo "查看错误：/tmp/netplan.apply.err"
  exit 1
fi

echo "✅ 配置已应用。可用以下命令查看状态："
echo "  netplan get"
echo "  ip a show $IFACE"
echo "  networkctl status $IFACE  # 若使用 systemd-networkd"