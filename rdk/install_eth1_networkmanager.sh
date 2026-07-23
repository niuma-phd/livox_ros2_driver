#!/usr/bin/env bash
set -euo pipefail

profile="${LIVOX_NM_PROFILE:-livox_lidar}"
interface="${LIVOX_INTERFACE:-eth1}"
address="${LIVOX_HOST_ADDRESS:-}"
ssh_client="${SSH_CLIENT:-}"
management_host="${LIVOX_MANAGEMENT_HOST:-${ssh_client%% *}}"

fail() { printf '错误: %s\n' "$*" >&2; exit 1; }

if ((EUID != 0)); then
  [[ -x /usr/bin/sudo ]] || fail "需要 root，且系统没有 /usr/bin/sudo"
  exec /usr/bin/sudo --preserve-env=LIVOX_NM_PROFILE,LIVOX_INTERFACE,LIVOX_HOST_ADDRESS,LIVOX_MANAGEMENT_HOST,SSH_CLIENT \
    "$0" "$@"
fi

export PATH=/usr/sbin:/usr/bin:/sbin:/bin

for command in ip nmcli python3; do
  command -v "$command" >/dev/null || fail "找不到 $command"
done
[[ -n "$address" ]] ||
  fail "必须显式设置 LIVOX_HOST_ADDRESS（例如主机的雷达专网 CIDR）"
ip link show "$interface" >/dev/null 2>&1 || fail "接口不存在: $interface"

management_route=""
management_device=""
management_gateway=""
if [[ -n "$management_host" ]]; then
  management_route="$(ip -4 route get "$management_host" | head -1)"
  management_device="$(awk '{for(i=1;i<=NF;i++) if($i=="dev") print $(i+1)}' <<<"$management_route")"
  management_gateway="$(awk '{for(i=1;i<=NF;i++) if($i=="via") print $(i+1)}' <<<"$management_route")"
  [[ "$management_device" != "$interface" ]] ||
    fail "管理端当前已走 $interface，无法安全推断原管理路由；请先从本地控制台修复"
fi

needs_host_route=0
if [[ -n "$management_host" && -n "$management_device" && "$management_device" != "$interface" ]]; then
  if python3 - "$management_host" "$address" <<'PY'
import ipaddress
import sys
raise SystemExit(
    0 if ipaddress.ip_address(sys.argv[1]) in ipaddress.ip_interface(sys.argv[2]).network else 1
)
PY
  then
    needs_host_route=1
  fi
fi

if ((needs_host_route)); then
  [[ -n "$management_gateway" ]] ||
    fail "管理端 $management_host 与雷达同网段，但原路由没有可持久化网关: $management_route"
  ip route replace "$management_host/32" \
    via "$management_gateway" dev "$management_device" metric 10

  if ! grep -Rqs -- "to: $management_host/32" /etc/netplan 2>/dev/null; then
    route_file="/etc/netplan/99-livox-management-route.yaml"
    cat >"$route_file" <<YAML
network:
  version: 2
  renderer: NetworkManager
  ethernets:
    $management_device:
      routes:
        - to: $management_host/32
          via: $management_gateway
          metric: 10
YAML
    chmod 0600 "$route_file"
    command -v netplan >/dev/null && netplan generate
  fi
fi

if nmcli -t -f NAME connection show | grep -Fxq "$profile"; then
  nmcli connection modify "$profile" connection.interface-name "$interface"
else
  nmcli connection add type ethernet ifname "$interface" con-name "$profile" >/dev/null
fi

nmcli connection modify "$profile" \
  connection.autoconnect yes \
  connection.autoconnect-priority 100 \
  connection.mdns no \
  connection.llmnr no \
  802-3-ethernet.auto-negotiate yes \
  ipv4.method manual \
  ipv4.addresses "$address" \
  ipv4.gateway "" \
  ipv4.dns "" \
  ipv4.never-default yes \
  ipv4.ignore-auto-routes yes \
  ipv4.ignore-auto-dns yes \
  ipv6.method disabled
nmcli connection reload
ip link set "$interface" up

if [[ "$(cat "/sys/class/net/$interface/carrier" 2>/dev/null || echo 0)" == "1" ]]; then
  nmcli connection up "$profile" >/dev/null
else
  echo "$interface 当前无载波；配置已保存，连接雷达后会自动激活。"
fi

default_routes="$(ip -4 route show default)"
[[ -n "$default_routes" ]] || fail "配置后没有 IPv4 默认路由"
if grep -Eq "(^| )dev $interface( |$)" <<<"$default_routes"; then
  nmcli connection down "$profile" >/dev/null 2>&1 || true
  fail "eth1 意外获得默认路由，已停用 $profile"
fi

if [[ -n "$management_host" && -n "$management_device" ]]; then
  route_after="$(ip -4 route get "$management_host" | head -1)"
  grep -Eq "(^| )dev $management_device( |$)" <<<"$route_after" || {
    nmcli connection down "$profile" >/dev/null 2>&1 || true
    fail "管理路由从 $management_device 偏移，已停用 $profile: $route_after"
  }
fi

nmcli -f \
connection.id,connection.interface-name,connection.autoconnect,ipv4.method,ipv4.addresses,ipv4.gateway,ipv4.never-default,ipv4.dns,ipv6.method \
  connection show "$profile"
echo "--- 默认路由（不得走 $interface） ---"
ip -4 route show default
if [[ -n "$management_host" ]]; then
  echo "--- 管理端路由 ---"
  ip -4 route get "$management_host" | head -1
fi
