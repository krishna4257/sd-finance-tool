#!/usr/bin/env bash
# ==============================================================================
# SD Finance: Apply Centrifugo WebSocket Gateway to Cloudflare Tunnel
# File: SD_Accounting_Tool/scripts/apply_cloudflared_chat.sh
# Usage: sudo bash scripts/apply_cloudflared_chat.sh
# ==============================================================================

set -euo pipefail

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "[-] Error: This script must be run as root (sudo bash scripts/apply_cloudflared_chat.sh)."
  exit 1
fi

CF_CONFIG="/etc/cloudflared/config.yml"

if [ ! -f "$CF_CONFIG" ]; then
    echo "[-] Error: $CF_CONFIG not found!"
    exit 1
fi

echo "[*] Backing up current $CF_CONFIG to ${CF_CONFIG}.bak..."
cp "$CF_CONFIG" "${CF_CONFIG}.bak"

echo "[*] Writing updated Cloudflare Tunnel ingress rules..."
cat << 'EOF' > "$CF_CONFIG"
tunnel: 6b3bd882-336e-4d9a-9077-dd4c9de54235

credentials-file: /home/jayakrishna/.cloudflared/6b3bd882-336e-4d9a-9077-dd4c9de54235.json

ingress:
  - hostname: sivadurga.in
    path: ^/connection/websocket.*
    service: http://127.0.0.1:8001

  - hostname: www.sivadurga.in
    path: ^/connection/websocket.*
    service: http://127.0.0.1:8001

  - hostname: sivadurga.in
    path: ^/chat-media/.*
    service: http://127.0.0.1:80

  - hostname: www.sivadurga.in
    path: ^/chat-media/.*
    service: http://127.0.0.1:80

  - hostname: sivadurga.in
    service: http://0.0.0.0:5000

  - hostname: www.sivadurga.in
    service: http://0.0.0.0:5000

  - service: http_status:404
EOF

echo "[*] Validating Cloudflare Tunnel configuration..."
/usr/bin/cloudflared --config "$CF_CONFIG" tunnel ingress validate

echo "[*] Restarting Cloudflare Tunnel daemon..."
systemctl restart cloudflared

echo "=========================================================="
echo "[✓] Cloudflare Tunnel WebSocket routing is LIVE!"
echo "    sivadurga.in/connection/websocket is now connected to Centrifugo!"
echo "=========================================================="
