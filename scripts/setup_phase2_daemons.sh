#!/usr/bin/env bash
# ==============================================================================
# SD Finance: Phase 2 Daemons Setup & Hardening Script (Centrifugo v5 + Redis)
# File: SD_Accounting_Tool/scripts/setup_phase2_daemons.sh
# Usage: sudo bash setup_phase2_daemons.sh
# ==============================================================================

set -euo pipefail

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "[-] Error: This installation script must be run as root (sudo)."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================================="
echo "    Siva Durga Finance: Phase 2 Infrastructure Setup      "
echo "=========================================================="

# ------------------------------------------------------------------------------
# STEP 0: Detect Application SECRET_KEY from .env
# ------------------------------------------------------------------------------
APP_SECRET_KEY="default-secret-key-2026"
ENV_FILES=("/srv/sd-finance-tool/.env" "$APP_DIR/.env" "$SCRIPT_DIR/../.env" "$SCRIPT_DIR/.env")
for ef in "${ENV_FILES[@]}"; do
    if [ -f "$ef" ]; then
        FOUND_CENT_KEY=$(grep -E "^CENTRIFUGO_SECRET_KEY=" "$ef" | head -n1 | cut -d '=' -f2- | tr -d " '\r\n\"" || true)
        if [ -n "$FOUND_CENT_KEY" ]; then
            APP_SECRET_KEY="$FOUND_CENT_KEY"
            echo "[*] Detected application CENTRIFUGO_SECRET_KEY from $ef"
            break
        fi
        FOUND_KEY=$(grep -E "^SECRET_KEY=" "$ef" | head -n1 | cut -d '=' -f2- | tr -d " '\r\n\"" || true)
        if [ -n "$FOUND_KEY" ]; then
            APP_SECRET_KEY="$FOUND_KEY"
            echo "[*] Detected application SECRET_KEY from $ef"
            break
        fi
    fi
done

# ------------------------------------------------------------------------------
# STEP 1: Redis Server Installation & Hardening
# ------------------------------------------------------------------------------
echo "[*] Step 1: Checking and configuring Redis Server..."
if ! command -v redis-server &>/dev/null; then
    echo "    Installing redis-server package..."
    apt-get update -qq
    apt-get install -y -qq redis-server
else
    echo "    redis-server is already installed."
fi

REDIS_CONF="/etc/redis/redis.conf"
if [ -f "$REDIS_CONF" ]; then
    echo "    Hardening Redis memory limits (128mb, volatile-lru)..."
    sed -i -E 's/^bind .*/bind 127.0.0.1 ::1/' "$REDIS_CONF" || true
    
    if ! grep -q "^maxmemory " "$REDIS_CONF"; then
        echo "maxmemory 128mb" >> "$REDIS_CONF"
    else
        sed -i 's/^maxmemory .*/maxmemory 128mb/' "$REDIS_CONF"
    fi

    if ! grep -q "^maxmemory-policy " "$REDIS_CONF"; then
        echo "maxmemory-policy volatile-lru" >> "$REDIS_CONF"
    else
        sed -i 's/^maxmemory-policy .*/maxmemory-policy volatile-lru/' "$REDIS_CONF"
    fi

    systemctl restart redis-server || true
    systemctl enable redis-server || true
    echo "    [+] Redis service hardened and active."
fi

# ------------------------------------------------------------------------------
# STEP 2: Centrifugo v5 Real-time Engine Installation
# ------------------------------------------------------------------------------
echo "[*] Step 2: Setting up Centrifugo v5 Daemon..."
CENTRIFUGO_BIN="/usr/local/bin/centrifugo"
CENTRIFUGO_VERSION="5.4.5"

if [ ! -f "$CENTRIFUGO_BIN" ]; then
    echo "    Downloading Centrifugo v${CENTRIFUGO_VERSION}..."
    ARCH="linux_amd64"
    if [ "$(uname -m)" = "aarch64" ]; then
        ARCH="linux_arm64"
    fi
    TMP_TAR="/tmp/centrifugo.tar.gz"
    curl -fsSL "https://github.com/centrifugal/centrifugo/releases/download/v${CENTRIFUGO_VERSION}/centrifugo_${CENTRIFUGO_VERSION}_${ARCH}.tar.gz" -o "$TMP_TAR"
    tar -xzf "$TMP_TAR" -C /tmp/
    mv /tmp/centrifugo "$CENTRIFUGO_BIN"
    chmod 755 "$CENTRIFUGO_BIN"
    rm -f "$TMP_TAR"
    echo "    [+] Installed Centrifugo binary to $CENTRIFUGO_BIN"
else
    echo "    Centrifugo binary exists at $CENTRIFUGO_BIN"
fi

# Deploy Centrifugo v5 JSON Configuration with dynamic secret injection
mkdir -p /etc/centrifugo
CONFIG_PATH="/etc/centrifugo/config.json"

cat <<EOF > "$CONFIG_PATH"
{
  "address": "127.0.0.1",
  "port": 8001,
  "health": true,
  "api_key": "sdfinance-centrifugo-api-key-2026",
  "token_hmac_secret_key": "$APP_SECRET_KEY",
  "allowed_origins": [
    "*",
    "https://sivadurga.in",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
  ],
  "allow_subscribe_for_client": true,
  "namespaces": [
    {
      "name": "chat",
      "allow_subscribe_for_client": true,
      "presence": true,
      "history_size": 100,
      "history_ttl": "300s"
    },
    {
      "name": "broadcast",
      "allow_subscribe_for_client": true,
      "presence": true,
      "history_size": 50,
      "history_ttl": "86400s"
    }
  ]
}
EOF
chmod 644 "$CONFIG_PATH"
echo "    [+] Generated Centrifugo v5 config with synchronized HMAC secret."

if [ -d "/etc/sudoers.d" ]; then
    echo "jayakrishna ALL=(ALL) NOPASSWD: /bin/systemctl restart centrifugo, /bin/systemctl status centrifugo" > /etc/sudoers.d/centrifugo
    chmod 440 /etc/sudoers.d/centrifugo
fi

# Deploy Centrifugo Systemd Service
CENTRIFUGO_SERVICE="/etc/systemd/system/centrifugo.service"
cat <<EOF > "$CENTRIFUGO_SERVICE"
[Unit]
Description=Centrifugo Realtime WebSocket Engine
Documentation=https://centrifugal.dev
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/centrifugo --config=/etc/centrifugo/config.json
Restart=always
RestartSec=3s
LimitNOFILE=65535
StandardOutput=journal
StandardError=journal
SyslogIdentifier=centrifugo

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable centrifugo
systemctl restart centrifugo
sleep 1
if ! systemctl is-active --quiet centrifugo; then
    echo "    [-] ERROR: Centrifugo failed to start! Journal logs:"
    journalctl -u centrifugo -n 30 --no-pager
    exit 1
fi
echo "    [+] Centrifugo service reloaded and active."

# ------------------------------------------------------------------------------
# STEP 3: Setup Chat Media Storage Directory
# ------------------------------------------------------------------------------
echo "[*] Step 3: Setting up Chat Media Directory..."
MEDIA_DIR="/var/www/sd-chat-media"
mkdir -p "$MEDIA_DIR"
if id "jayakrishna" &>/dev/null; then
    chown -R jayakrishna:www-data "$MEDIA_DIR"
elif id "www-data" &>/dev/null; then
    chown -R www-data:www-data "$MEDIA_DIR"
fi
chmod -R 775 "$MEDIA_DIR"
echo "    [+] Chat media directory ready at $MEDIA_DIR"

# ------------------------------------------------------------------------------
# STEP 4: Setup NotifKit Notification Orchestration Daemon
# ------------------------------------------------------------------------------
echo "[*] Step 4: Setting up NotifKit Notification Engine..."
NOTIFKIT_DIR="/opt/notifkit"
mkdir -p "$NOTIFKIT_DIR"

if [ -f "$SCRIPT_DIR/notifkit_daemon.py" ]; then
    cp "$SCRIPT_DIR/notifkit_daemon.py" "$NOTIFKIT_DIR/daemon.py"
    chmod 755 "$NOTIFKIT_DIR/daemon.py"
fi

# Detect Python interpreter (prefer virtualenv)
PYTHON_BIN="/usr/bin/python3"
if [ -f "/srv/sd-finance-tool/venv/bin/python3" ]; then
    PYTHON_BIN="/srv/sd-finance-tool/venv/bin/python3"
elif [ -f "$APP_DIR/venv/bin/python3" ]; then
    PYTHON_BIN="$APP_DIR/venv/bin/python3"
fi

NOTIFKIT_SERVICE="/etc/systemd/system/notifkit.service"
cat <<EOF > "$NOTIFKIT_SERVICE"
[Unit]
Description=NotifKit Notification Orchestration Engine
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/notifkit
Environment="NOTIFKIT_HOST=127.0.0.1"
Environment="NOTIFKIT_PORT=4000"
Environment="NOTIFKIT_API_SECRET=sdfinance-notifkit-secret-2026"
ExecStart=$PYTHON_BIN /opt/notifkit/daemon.py
Restart=always
RestartSec=3s
LimitNOFILE=65535
StandardOutput=journal
StandardError=journal
SyslogIdentifier=notifkit

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable notifkit
systemctl restart notifkit
sleep 1
echo "    [+] NotifKit systemd service active on port 4000."

# ------------------------------------------------------------------------------
# STEP 4.5: Automatic Nginx Reverse Proxy Configuration (Centrifugo WebSocket)
# ------------------------------------------------------------------------------
NGINX_TARGET="/etc/nginx/sites-available/sd_fin"
if [ -f "$NGINX_TARGET" ]; then
    echo "[*] Step 4.5: Configuring Nginx WebSocket gateway in $NGINX_TARGET..."
    cp "$NGINX_TARGET" "${NGINX_TARGET}.bak"
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
    if nginx -t &>/dev/null; then
        systemctl reload nginx || systemctl restart nginx
        echo "    [+] Nginx WebSocket gateway configured and reloaded."
    else
        echo "    [-] Nginx test failed, rolling back..."
        cp "${NGINX_TARGET}.bak" "$NGINX_TARGET"
        systemctl reload nginx || true
    fi
fi

# ------------------------------------------------------------------------------
# STEP 5: Service Status & Loopback Port Verification
# ------------------------------------------------------------------------------
echo "=========================================================="
echo "               Phase 2 Daemons Status                     "
echo "=========================================================="

echo "Checking Redis (port 6379)..."
if command -v redis-cli &>/dev/null; then
    REDIS_PING="$(redis-cli ping 2>/dev/null || echo 'DOWN')"
    echo "    Redis Ping: $REDIS_PING"
fi

echo "Checking Centrifugo (port 8001)..."
if command -v curl &>/dev/null; then
    CENT_RESP="$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/health || echo 'DOWN')"
    echo "    Centrifugo Health Check (HTTP): $CENT_RESP"
fi

echo "Checking NotifKit (port 4000)..."
if command -v curl &>/dev/null; then
    NOTIF_RESP="$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:4000/health || echo 'DOWN')"
    echo "    NotifKit Health Check (HTTP): $NOTIF_RESP"
fi

echo "=========================================================="
echo "[✓] Phase 2 setup completed successfully!"
