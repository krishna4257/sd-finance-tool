#!/usr/bin/env bash
# ==============================================================================
# Siva Durga Safe Storage Auto-Purge & Health Sentinel
# ==============================================================================
# Safely purges accumulated logs, package caches, and systemd journal bloat
# to prevent disk-full crashes on remote Ubuntu server nodes.
# ==============================================================================

set -euo pipefail

ALERT_THRESHOLD=85
ROOT_PATH="/"

echo "=========================================================="
echo " Siva Durga Storage Sentinel - Health & Purge Check"
echo " Timestamp: $(date)"
echo "=========================================================="

# Check current disk usage
CURRENT_USAGE=$(df -h "$ROOT_PATH" | awk 'NR==2 {print $5}' | tr -d '%')
echo "[Status] Current root disk usage: ${CURRENT_USAGE}%"

echo "[1/4] Vacuuming systemd journals to max 200MB..."
if command -v journalctl >/dev/null 2>&1; then
    journalctl --vacuum-size=200M || true
    echo "✔ Journal vacuumed successfully."
fi

echo "[2/4] Cleaning apt package cache and obsolete archives..."
if command -v apt-get >/dev/null 2>&1; then
    apt-get clean -y || true
    apt-get autoremove --purge -y || true
    echo "✔ Apt package cache cleared."
fi

echo "[3/4] Truncating oversized rotated logs older than 14 days in /var/log..."
find /var/log -type f -name "*.gz" -mtime +14 -delete 2>/dev/null || true
find /var/log -type f -name "*.1" -mtime +14 -delete 2>/dev/null || true
echo "✔ Old log archives purged."

echo "[4/4] Checking PostgreSQL temp files..."
if [ -d "/var/lib/postgresql" ]; then
    echo "PostgreSQL directory size: $(du -sh /var/lib/postgresql 2>/dev/null | awk '{print $1}')"
fi

FINAL_USAGE=$(df -h "$ROOT_PATH" | awk 'NR==2 {print $5}' | tr -d '%')
FREE_GB=$(df -h "$ROOT_PATH" | awk 'NR==2 {print $4}')
echo "=========================================================="
echo "✔ Storage maintenance complete."
echo "Disk usage: ${FINAL_USAGE}% (Free Space: ${FREE_GB})"
if [ "$FINAL_USAGE" -ge "$ALERT_THRESHOLD" ]; then
    echo "⚠️ WARNING: Disk usage is still high (${FINAL_USAGE}% >= ${ALERT_THRESHOLD}%)."
    echo "Immediate manual review or database vacuum may be required."
else
    echo "✔ Disk usage is within healthy operating thresholds."
fi
echo "=========================================================="
