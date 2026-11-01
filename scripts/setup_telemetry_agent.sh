#!/usr/bin/env bash
# ==============================================================================
# Siva Durga Remote Node Telemetry Agent Installer
# ==============================================================================
# Usage:
#   sudo bash setup_telemetry_agent.sh [server_id] [server_name] [role] [location]
#
# Examples:
#   Primary Node:
#     sudo bash setup_telemetry_agent.sh main_server "Primary Core Server (sivadurga.in)" "Core Web & DB" "Primary Remote Office"
#
#   Backup Node:
#     sudo bash setup_telemetry_agent.sh backup_server "Secondary Disaster Recovery Machine" "Database Replica & Cold Backup" "Backup Remote Site"
# ==============================================================================

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Error: Please run this installation script as root (sudo)."
  exit 1
fi

SERVER_ID="${1:-main_server}"
SERVER_NAME="${2:-Primary Core Server (sivadurga.in)}"
SERVER_ROLE="${3:-Core Web & Database}"
LOCATION="${4:-Remote Site 1}"
ENDPOINT="https://sivadurga.in/api/v1/telemetry/heartbeat"
SECRET_KEY="${TELEMETRY_SECRET_KEY:-sdfinance-telemetry-default-key-2026}"

echo "=========================================================="
echo "Installing Siva Durga Telemetry Sentinel on $(hostname)"
echo "Node ID   : $SERVER_ID"
echo "Node Name : $SERVER_NAME"
echo "Role      : $SERVER_ROLE"
echo "Location  : $LOCATION"
echo "Endpoint  : $ENDPOINT"
echo "=========================================================="

if [ "$SERVER_ID" = "main_server" ]; then
    SERVICES="sdfin,postgresql,cloudflared,nginx"
else
    SERVICES="postgresql,cron,tailscaled"
fi

# Create /etc/sd-telemetry.conf
cat <<EOF > /etc/sd-telemetry.conf
# Siva Durga Sentinel Agent Configuration
TELEMETRY_SERVER_ID="$SERVER_ID"
TELEMETRY_SERVER_NAME="$SERVER_NAME"
TELEMETRY_SERVER_ROLE="$SERVER_ROLE"
TELEMETRY_LOCATION="$LOCATION"
TELEMETRY_ENDPOINT="$ENDPOINT"
TELEMETRY_SECRET_KEY="$SECRET_KEY"
TELEMETRY_INTERVAL="30"
TELEMETRY_SERVICES="$SERVICES"
EOF

chmod 600 /etc/sd-telemetry.conf
echo "✔ Saved configuration to /etc/sd-telemetry.conf"

# Copy agent script
SCRIPT_SRC="$(dirname "$0")/sd_node_agent.py"
if [ -f "$SCRIPT_SRC" ]; then
    cp "$SCRIPT_SRC" /usr/local/bin/sd_node_agent.py
else
    # Download or copy from known path
    echo "Using existing agent script or fallback..."
fi
chmod +x /usr/local/bin/sd_node_agent.py

# Create systemd service
cat <<EOF > /etc/systemd/system/sd-telemetry-agent.service
[Unit]
Description=Siva Durga Remote Node Telemetry & Infrastructure Sentinel
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
EnvironmentFile=/etc/sd-telemetry.conf
ExecStart=/usr/bin/python3 /usr/local/bin/sd_node_agent.py
Restart=always
RestartSec=10s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sd-telemetry-agent

[Install]
WantedBy=multi-user.target
EOF

# Reload & enable
systemctl daemon-reload
systemctl enable sd-telemetry-agent.service
systemctl restart sd-telemetry-agent.service

echo "=========================================================="
echo "✔ Siva Durga Telemetry Sentinel installed & active!"
echo "Status check: systemctl status sd-telemetry-agent.service"
echo "Live logs   : journalctl -u sd-telemetry-agent.service -f"
echo "=========================================================="
