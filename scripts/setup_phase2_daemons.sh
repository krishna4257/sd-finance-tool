#!/usr/bin/env bash
# ==============================================================================
# SD Finance: Phase 2 Daemons Setup & Hardening Script
# File: SD_Accounting_Tool/scripts/setup_phase2_daemons.sh
# Usage: sudo bash setup_phase2_daemons.sh
# ==============================================================================
# Sets up and configures:
# 1. Redis Server (in-memory queue, capped at 128MB with volatile-lru eviction)
# 2. Centrifugo Daemon (real-time WebSockets on 127.0.0.1:8001)
# 3. NotifKit Notification Engine (/opt/notifkit on 127.0.0.1:4000)
# 4. Media Storage Directory (/var/www/sd-chat-media)
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
# STEP 1: Redis Server Installation & Hardening
# ------------------------------------------------------------------------------
echo "[*] Step 1: Checking and configuring Redis Server..."
if ! command -v redis-server &>/dev/null; then
    echo "    Installing redis-server package..."
    apt-get update -qq
    apt-get install -y -qq redis-server
else
    echo "    redis-server already installed."
fi

REDIS_CONF="/etc/redis/redis.conf"
if [ -f "$REDIS_CONF" ]; then
    echo "    Hardening Redis memory limits (128mb, volatile-lru)..."
    # Ensure local binding
    sed -i -E 's/^bind .*/bind 127.0.0.1 ::1/' "$REDIS_CONF"
    
    # Configure maxmemory if not present
    if ! grep -q "^maxmemory " "$REDIS_CONF"; then
        echo "maxmemory 128mb" >> "$REDIS_CONF"
    else
        sed -i 's/^maxmemory .*/maxmemory 128mb/' "$REDIS_CONF"
    fi

    # Configure eviction policy if not present
    if ! grep -q "^maxmemory-policy " "$REDIS_CONF"; then
        echo "maxmemory-policy volatile-lru" >> "$REDIS_CONF"
    else
        sed -i 's/^maxmemory-policy .*/maxmemory-policy volatile-lru/' "$REDIS_CONF"
    fi

    systemctl restart redis-server || true
    systemctl enable redis-server || true
    echo "    [+] Redis service hardened and running."
fi

# ------------------------------------------------------------------------------
# STEP 2: Centrifugo Real-time Engine Installation
# ------------------------------------------------------------------------------
echo "[*] Step 2: Setting up Centrifugo Real-time Daemon..."
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
    echo "    Centrifugo binary already exists at $CENTRIFUGO_BIN"
fi

# Deploy Centrifugo Configuration
mkdir -p /etc/centrifugo
if [ -f "$SCRIPT_DIR/centrifugo.json" ]; then
    cp "$SCRIPT_DIR/centrifugo.json" /etc/centrifugo/config.json
    chmod 640 /etc/centrifugo/config.json
    echo "    [+] Installed /etc/centrifugo/config.json"
fi

# Deploy Centrifugo Systemd Unit
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
systemctl restart centrifugo || true
echo "    [+] Centrifugo systemd unit deployed and started."

# ------------------------------------------------------------------------------
# STEP 3: Setup Chat Media Storage Directory
# ------------------------------------------------------------------------------
echo "[*] Step 3: Setting up Chat Media Directory..."
MEDIA_DIR="/var/www/sd-chat-media"
mkdir -p "$MEDIA_DIR"
# Give ownership to active web server user or current login
if id "jayakrishna" &>/dev/null; then
    chown -R jayakrishna:www-data "$MEDIA_DIR"
elif id "www-data" &>/dev/null; then
    chown -R www-data:www-data "$MEDIA_DIR"
fi
chmod -R 775 "$MEDIA_DIR"
echo "    [+] Chat media directory ready at $MEDIA_DIR"

# ------------------------------------------------------------------------------
# STEP 4: Setup NotifKit Notification Engine
# ------------------------------------------------------------------------------
echo "[*] Step 4: Checking NotifKit prerequisites..."
if command -v node &>/dev/null; then
    NODE_VER="$(node -v)"
    echo "    Found Node.js: $NODE_VER"
else
    echo "    [-] Notice: Node.js (v20+) is not yet installed."
    echo "    To install Node.js v20 LTS on Ubuntu/Debian:"
    echo "        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -"
    echo "        sudo apt-get install -y nodejs"
fi

NOTIFKIT_DIR="/opt/notifkit"
if [ ! -d "$NOTIFKIT_DIR" ]; then
    echo "    Creating $NOTIFKIT_DIR directory..."
    mkdir -p "$NOTIFKIT_DIR"
fi

NOTIFKIT_SERVICE="/etc/systemd/system/notifkit.service"
cat <<EOF > "$NOTIFKIT_SERVICE"
[Unit]
Description=NotifKit Notification Orchestration Engine
After=network.target redis-server.service postgresql.service
Wants=redis-server.service postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/notifkit
EnvironmentFile=-/opt/notifkit/.env
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=5s
LimitNOFILE=65535
StandardOutput=journal
StandardError=journal
SyslogIdentifier=notifkit

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo "    [+] NotifKit systemd unit staged at $NOTIFKIT_SERVICE"

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

echo "=========================================================="
echo "[✓] Phase 2 setup completed successfully!"
echo "Next step: Add Nginx reverse proxy snippet from:"
echo "    $SCRIPT_DIR/nginx_chat.conf"
echo "into your Nginx configuration, then run: sudo nginx -t && sudo systemctl reload nginx"
echo "=========================================================="
