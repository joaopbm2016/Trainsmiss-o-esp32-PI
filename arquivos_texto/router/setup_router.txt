#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Execute como root: sudo bash setup_router.sh"
  exit 1
fi

if [[ -z "${SUDO_USER:-}" ]]; then
  echo "Execute com sudo para preservar o usuario normal."
  exit 1
fi

read -r -p "Nome da rede Wi-Fi dos ESP32 [ESP32-Router]: " WIFI_SSID
WIFI_SSID="${WIFI_SSID:-ESP32-Router}"

while true; do
  read -r -p "Senha da rede Wi-Fi (minimo 8 caracteres): " WIFI_PASSWORD
  if [[ ${#WIFI_PASSWORD} -ge 8 ]]; then
    break
  fi
  echo "A senha deve ter pelo menos 8 caracteres."
done

read -r -p "Interface Wi-Fi interna [wlan0]: " WIFI_IFACE
WIFI_IFACE="${WIFI_IFACE:-wlan0}"

read -r -p "Interface Ethernet externa [eth0]: " WAN_IFACE
WAN_IFACE="${WAN_IFACE:-eth0}"

for iface in "$WIFI_IFACE" "$WAN_IFACE"; do
  if ! ip link show "$iface" >/dev/null 2>&1; then
    echo "Erro: interface '$iface' nao encontrada."
    echo "Interfaces disponiveis:"
    ip -br link
    exit 1
  fi
done

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y hostapd dnsmasq nftables

mkdir -p /etc/dnsmasq.d

cat >/etc/dnsmasq.d/esp32-router.conf <<EOF
interface=${WIFI_IFACE}
bind-interfaces
dhcp-range=192.168.50.20,192.168.50.200,255.255.255.0,24h
dhcp-option=3,192.168.50.1
dhcp-option=6,192.168.50.1
domain-needed
bogus-priv
local=/lan/
EOF

cat >/etc/hostapd/hostapd.conf <<EOF
interface=${WIFI_IFACE}
driver=nl80211
ssid=${WIFI_SSID}
hw_mode=g
channel=6
wmm_enabled=1
auth_algs=1
wpa=2
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
wpa_passphrase=${WIFI_PASSWORD}
EOF

sed -i 's|^#*DAEMON_CONF=.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' \
  /etc/default/hostapd

if command -v nmcli >/dev/null 2>&1; then
  nmcli device set "$WIFI_IFACE" managed no || true
fi

ip addr flush dev "$WIFI_IFACE"
ip addr add 192.168.50.1/24 dev "$WIFI_IFACE"
ip link set "$WIFI_IFACE" up

cat >/etc/nftables.conf <<EOF
flush ruleset

table inet filter {
  chain input {
    type filter hook input priority 0; policy accept;
  }

  chain forward {
    type filter hook forward priority 0; policy accept;

    ct state established,related accept
    iifname "${WIFI_IFACE}" oifname "${WAN_IFACE}" accept
  }
}

table ip nat {
  chain postrouting {
    type nat hook postrouting priority 100; policy accept;
    oifname "${WAN_IFACE}" masquerade
  }
}
EOF

nft -f /etc/nftables.conf

cat >/etc/sysctl.d/99-esp32-router.conf <<EOF
net.ipv4.ip_forward=1
net.ipv6.conf.all.forwarding=0
EOF

sysctl --system >/dev/null

cat >/etc/systemd/system/esp32-router-ip.service <<EOF
[Unit]
Description=Configurar rede interna do Raspberry Pi para ESP32
After=network-pre.target
Before=hostapd.service dnsmasq.service

[Service]
Type=oneshot
ExecStart=/usr/sbin/ip address flush dev ${WIFI_IFACE}
ExecStart=/usr/sbin/ip address add 192.168.50.1/24 dev ${WIFI_IFACE}
ExecStart=/usr/sbin/ip link set ${WIFI_IFACE} up
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable esp32-router-ip.service

systemctl unmask hostapd
systemctl enable nftables
systemctl enable dnsmasq
systemctl enable hostapd

systemctl restart dnsmasq
systemctl restart nftables
systemctl restart hostapd

echo
echo "Configuracao concluida."
echo "Rede Wi-Fi: ${WIFI_SSID}"
echo "Faixa de IP: 192.168.50.20 a 192.168.50.200"
echo "Gateway/DNS do ESP32: 192.168.50.1"
echo "Interface interna: ${WIFI_IFACE}"
echo "Interface Internet: ${WAN_IFACE}"
echo
echo "Verifique:"
echo "  sudo systemctl status hostapd"
echo "  sudo systemctl status dnsmasq"
echo "  journalctl -u hostapd -n 30"
