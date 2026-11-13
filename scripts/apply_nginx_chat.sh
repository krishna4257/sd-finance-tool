#!/usr/bin/env bash
# ==============================================================================
# SD Finance: Apply Centrifugo WebSocket Gateway to Nginx
# File: SD_Accounting_Tool/scripts/apply_nginx_chat.sh
# Usage: sudo bash scripts/apply_nginx_chat.sh
# ==============================================================================

set -euo pipefail

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "[-] Error: This script must be run as root (sudo bash scripts/apply_nginx_chat.sh)."
  exit 1
fi

NGINX_TARGET="/etc/nginx/sites-available/sd_fin"

if [ ! -f "$NGINX_TARGET" ]; then
    echo "[-] Error: $NGINX_TARGET not found!"
    exit 1
fi

echo "[*] Backing up current $NGINX_TARGET to ${NGINX_TARGET}.bak..."
cp "$NGINX_TARGET" "${NGINX_TARGET}.bak"

echo "[*] Writing Centrifugo WebSocket Gateway & Media locations into $NGINX_TARGET..."
cat << 'EOF' > "$NGINX_TARGET"
server {
    listen 80;
    server_name _;
    client_max_body_size 100M;

    # Centrifugo Real-time WebSocket Gateway
    location /connection/websocket {
        proxy_pass http://127.0.0.1:8001/connection/websocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_buffering off;
    }

    # Secure Chat Media Static Files (Photos & Audio Voice Notes)
    location /chat-media/ {
        alias /var/www/sd-chat-media/;
        expires 30d;
        add_header Cache-Control "private, no-transform";
        try_files $uri =404;
    }

    # Core SD Finance Flask App
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 120;
        proxy_send_timeout 120;
        proxy_read_timeout 120;
    }
}
EOF

echo "[*] Testing Nginx configuration syntax..."
nginx -t

echo "[*] Reloading Nginx service..."
systemctl reload nginx

echo "=========================================================="
echo "[✓] Nginx Centrifugo WebSocket Gateway is LIVE!"
echo "    Chat connection status will now turn green: ● Connected (Real-time)"
echo "=========================================================="
