#!/usr/bin/env python3
"""
Siva Durga Infrastructure Sentinel - Telemetry Agent
===================================================
Lightweight, zero-dependency monitoring daemon designed for Ubuntu/Debian remote nodes
and Windows WSL2 hosts. Pushes real-time physical & guest metrics (Storage, CPU, RAM,
Uptime, Services, Power state) to the central Sivadurga web platform via
HMAC-SHA256 authenticated HTTPS heartbeats.

Runs continuously as a systemd background service without needing any interactive terminal.
"""

import os
import sys
import time
import json
import socket
import shutil
import hashlib
import hmac
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone

# Default Configuration (Override via CLI flags or /etc/sd-telemetry.conf or env)
DEFAULT_ENDPOINT = "https://sivadurga.in/api/v1/telemetry/heartbeat"
DEFAULT_INTERVAL = 30  # seconds between heartbeats
DEFAULT_CONF_PATH = "/etc/sd-telemetry.conf"


def load_config():
    """Load settings from config file if present, overridden by environment variables."""
    cfg = {
        "server_id": "main_server",
        "server_name": "Primary Core Server (sivadurga.in)",
        "server_role": "Core Web & Database",
        "location": "Primary Remote Site",
        "endpoint": DEFAULT_ENDPOINT,
        "secret_key": "sdfinance-telemetry-default-key-2026",
        "interval": DEFAULT_INTERVAL,
        "monitored_services": "sdfin,postgresql,cloudflared,nginx"
    }

    # Load from /etc/sd-telemetry.conf or local .env if available
    paths_to_check = [DEFAULT_CONF_PATH, ".env", "../.env", "/srv/sd-finance-tool/.env"]
    for p in paths_to_check:
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip().upper()
                        v = v.strip().strip("'\"")
                        if k == "TELEMETRY_SERVER_ID": cfg["server_id"] = v
                        elif k == "TELEMETRY_SERVER_NAME": cfg["server_name"] = v
                        elif k == "TELEMETRY_SERVER_ROLE": cfg["server_role"] = v
                        elif k == "TELEMETRY_LOCATION": cfg["location"] = v
                        elif k == "TELEMETRY_ENDPOINT": cfg["endpoint"] = v
                        elif k in ("TELEMETRY_SECRET_KEY", "MOBILE_QUEUE_HMAC_SECRET"): cfg["secret_key"] = v
                        elif k == "TELEMETRY_INTERVAL": cfg["interval"] = int(v)
                        elif k == "TELEMETRY_SERVICES": cfg["monitored_services"] = v
            except Exception as e:
                print(f"[Agent] Notice reading {p}: {e}", file=sys.stderr)

    # Environment variables take final precedence
    if os.environ.get("TELEMETRY_SERVER_ID"): cfg["server_id"] = os.environ["TELEMETRY_SERVER_ID"]
    if os.environ.get("TELEMETRY_SERVER_NAME"): cfg["server_name"] = os.environ["TELEMETRY_SERVER_NAME"]
    if os.environ.get("TELEMETRY_SERVER_ROLE"): cfg["server_role"] = os.environ["TELEMETRY_SERVER_ROLE"]
    if os.environ.get("TELEMETRY_LOCATION"): cfg["location"] = os.environ["TELEMETRY_LOCATION"]
    if os.environ.get("TELEMETRY_ENDPOINT"): cfg["endpoint"] = os.environ["TELEMETRY_ENDPOINT"]
    if os.environ.get("TELEMETRY_SECRET_KEY"): cfg["secret_key"] = os.environ["TELEMETRY_SECRET_KEY"]
    if os.environ.get("TELEMETRY_INTERVAL"): cfg["interval"] = int(os.environ["TELEMETRY_INTERVAL"])
    if os.environ.get("TELEMETRY_SERVICES"): cfg["monitored_services"] = os.environ["TELEMETRY_SERVICES"]

    return cfg


def is_wsl():
    """Detect if running inside WSL2 on Windows."""
    return os.path.exists("/mnt/c") and (
        os.path.exists("/proc/sys/fs/binfmt_misc/WSLInterop") or os.path.exists("/etc/wsl.conf")
    )


def get_windows_host_metrics():
    """
    Query physical Windows host hardware metrics via PowerShell interop.
    Retrieves physical SSD storage, physical RAM, physical CPU, and boot time.
    """
    ps_path = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    if not (is_wsl() and os.path.isfile(ps_path)):
        return None

    try:
        script = """
        $disk = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | Where-Object DeviceID -eq "C:" | Select-Object @{Name="Total";Expression={[math]::Round($_.Size/1GB, 2)}}, @{Name="Free";Expression={[math]::Round($_.FreeSpace/1GB, 2)}}
        $os = Get-CimInstance Win32_OperatingSystem | Select-Object @{Name="TotalRAM";Expression={[math]::Round($_.TotalVisibleMemorySize/1MB, 2)}}, @{Name="FreeRAM";Expression={[math]::Round($_.FreePhysicalMemory/1MB, 2)}}, @{Name="Boot";Expression={$_.LastBootUpTime.ToString("o")}}
        $cpu = Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, LoadPercentage | Select-Object -First 1
        $cs = Get-CimInstance Win32_ComputerSystem | Select-Object Name, Model
        @{
            disk = $disk;
            os = $os;
            cpu = $cpu;
            cs = $cs;
        } | ConvertTo-Json -Compress
        """
        res = subprocess.run([ps_path, "-NoProfile", "-Command", script], capture_output=True, text=True, timeout=4)
        if res.returncode == 0 and res.stdout.strip():
            text = res.stdout.strip()
            idx = text.find("{")
            if idx != -1:
                return json.loads(text[idx:])
    except Exception as e:
        print(f"[Agent] Notice querying Windows host: {e}", file=sys.stderr)

    return None


def get_cpu_info(win_data=None):
    """Calculate CPU usage percent and load average."""
    if win_data and "cpu" in win_data and win_data["cpu"]:
        c = win_data["cpu"]
        cores = int(c.get("NumberOfCores") or 8)
        threads = int(c.get("NumberOfLogicalProcessors") or 16)
        cpu_percent = float(c.get("LoadPercentage") or 0.0)
        load_avg = f"Windows Load: {int(cpu_percent)}% ({threads} Threads)"
        return cpu_percent, cores, load_avg

    load_avg = "0.00, 0.00, 0.00"
    cpu_cores = os.cpu_count() or 1
    cpu_percent = 0.0

    try:
        load = getattr(os, 'getloadavg')()
        load_avg = f"{load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}"
        cpu_percent = min(100.0, round((load[0] / cpu_cores) * 100.0, 1))
    except (AttributeError, OSError):
        pass

    try:
        if os.path.exists("/proc/stat"):
            with open("/proc/stat", "r") as f:
                fields = [float(column) for column in f.readline().strip().split()[1:5]]
            idle1, total1 = fields[3], sum(fields)
            time.sleep(0.1)
            with open("/proc/stat", "r") as f:
                fields = [float(column) for column in f.readline().strip().split()[1:5]]
            idle2, total2 = fields[3], sum(fields)
            idle_delta, total_delta = idle2 - idle1, total2 - total1
            if total_delta > 0:
                cpu_percent = round(100.0 * (1.0 - idle_delta / total_delta), 1)
    except Exception:
        pass

    return cpu_percent, cpu_cores, load_avg


def get_memory_info(win_data=None):
    """Retrieve memory usage in GB and percent."""
    if win_data and "os" in win_data and win_data["os"]:
        o = win_data["os"]
        total_gb = float(o.get("TotalRAM") or 0.0)
        free_gb = float(o.get("FreeRAM") or 0.0)
        used_gb = round(max(0.0, total_gb - free_gb), 2)
        percent = round((used_gb / total_gb) * 100.0, 1) if total_gb > 0 else 0.0
        return percent, used_gb, total_gb

    total_gb = 0.0
    used_gb = 0.0
    percent = 0.0

    try:
        if os.path.exists("/proc/meminfo"):
            mem = {}
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip().split()[0]
                        mem[key] = float(val)
            total_kb = mem.get("MemTotal", 0.0)
            avail_kb = mem.get("MemAvailable", mem.get("MemFree", 0.0) + mem.get("Buffers", 0.0) + mem.get("Cached", 0.0))
            used_kb = max(0.0, total_kb - avail_kb)

            total_gb = round(total_kb / (1024 * 1024), 2)
            used_gb = round(used_kb / (1024 * 1024), 2)
            percent = round((used_kb / total_kb) * 100.0, 1) if total_kb > 0 else 0.0
            return percent, used_gb, total_gb
    except Exception:
        pass

    return 30.0, 2.0, 8.0


def get_disk_info(win_data=None):
    """
    Retrieve disk space utilization.
    If on WSL, reads physical C: drive (/mnt/c) to display real physical SSD stats.
    """
    # 1. Physical Windows C: drive on WSL
    if is_wsl() and os.path.exists("/mnt/c"):
        try:
            usage = shutil.disk_usage("/mnt/c")
            total_gb = round(usage.total / (1024 ** 3), 2)
            used_gb = round(usage.used / (1024 ** 3), 2)
            free_gb = round(usage.free / (1024 ** 3), 2)
            percent = round((usage.used / usage.total) * 100.0, 1) if usage.total > 0 else 0.0
            return percent, used_gb, free_gb, total_gb
        except Exception:
            pass

    # 2. Or from win_data if passed
    if win_data and "disk" in win_data and win_data["disk"]:
        d = win_data["disk"]
        total_gb = float(d.get("Total") or 0.0)
        free_gb = float(d.get("Free") or 0.0)
        used_gb = round(max(0.0, total_gb - free_gb), 2)
        percent = round((used_gb / total_gb) * 100.0, 1) if total_gb > 0 else 0.0
        return percent, used_gb, free_gb, total_gb

    # 3. Standard Linux root filesystem
    try:
        usage = shutil.disk_usage("/")
        total_gb = round(usage.total / (1024 ** 3), 2)
        used_gb = round(usage.used / (1024 ** 3), 2)
        free_gb = round(usage.free / (1024 ** 3), 2)
        percent = round((usage.used / usage.total) * 100.0, 1) if usage.total > 0 else 0.0
        return percent, used_gb, free_gb, total_gb
    except Exception as e:
        print(f"[Agent] Error reading disk info: {e}", file=sys.stderr)
        return 0.0, 0.0, 0.0, 0.0


def get_uptime_and_boot(win_data=None):
    """Retrieve system uptime in seconds and boot timestamp."""
    if win_data and "os" in win_data and win_data["os"].get("Boot"):
        boot_str = win_data["os"]["Boot"]
        try:
            boot_dt = datetime.fromisoformat(boot_str)
            uptime_seconds = int((datetime.now(timezone.utc) - boot_dt.astimezone(timezone.utc)).total_seconds())
            return max(0, uptime_seconds), boot_dt.astimezone(timezone.utc).isoformat()
        except Exception:
            pass

    uptime_seconds = 0
    boot_time = datetime.now(timezone.utc).isoformat()

    try:
        if os.path.exists("/proc/uptime"):
            with open("/proc/uptime", "r") as f:
                uptime_seconds = int(float(f.readline().split()[0]))
            boot_epoch = time.time() - uptime_seconds
            boot_time = datetime.fromtimestamp(boot_epoch, tz=timezone.utc).isoformat()
            return uptime_seconds, boot_time
    except Exception:
        pass

    return uptime_seconds, boot_time


def check_services(service_list_str):
    """Check status of critical systemd daemons (sdfin, postgresql, cloudflared, nginx, etc.)."""
    results = {}
    services = [s.strip() for s in service_list_str.split(",") if s.strip()]

    for s in services:
        try:
            res = subprocess.run(
                ["systemctl", "is-active", s],
                capture_output=True,
                text=True,
                timeout=3
            )
            status = res.stdout.strip()
            results[s] = status if status in ("active", "inactive", "failed") else "unknown"
        except Exception:
            results[s] = "unavailable"

    # Append Postgres connection count & DB size if reachable
    if "postgresql" in results and results["postgresql"] == "active":
        try:
            env_file = "/srv/sd-finance-tool/.env"
            if os.path.isfile(env_file):
                db_user = ""
                db_name = ""
                db_pwd = ""
                with open(env_file, "r") as ef:
                    for line in ef:
                        if line.startswith("DB_USER="): db_user = line.split("=", 1)[1].strip().strip("'\"")
                        elif line.startswith("DB_NAME="): db_name = line.split("=", 1)[1].strip().strip("'\"")
                        elif line.startswith("DB_PASSWORD="): db_pwd = line.split("=", 1)[1].strip().strip("'\"")
                if db_user and db_name:
                    pg_cmd = f"PGPASSWORD='{db_pwd}' psql -U '{db_user}' -h localhost -d '{db_name}' -t -A -c 'SELECT count(*) FROM pg_stat_activity;' 2>/dev/null"
                    pres = subprocess.run(pg_cmd, shell=True, capture_output=True, text=True, timeout=2)
                    if pres.returncode == 0 and pres.stdout.strip().isdigit():
                        results["postgresql"] = f"active ({pres.stdout.strip()} conns)"
        except Exception:
            pass

    return results


def get_network_ips(win_data=None):
    """Detect LAN IP and Tailscale IP."""
    lan_ip = "127.0.0.1"
    tailscale_ip = ""

    # Detect LAN IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1.0)
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        try:
            lan_ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            pass

    # Detect Tailscale IP if installed
    try:
        res = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            tailscale_ip = res.stdout.strip().splitlines()[0].strip()
    except Exception:
        pass

    # If in WSL, append Windows host Tailscale mesh node
    if is_wsl():
        win_tailscale = "100.126.200.48"
        if tailscale_ip:
            tailscale_ip = f"{win_tailscale} (Host) / {tailscale_ip} (WSL)"
        else:
            tailscale_ip = win_tailscale

    return lan_ip, tailscale_ip


def get_power_status(win_data=None):
    """Detect AC power / battery status."""
    if is_wsl():
        return "Desktop PC (Direct AC Grid - No Battery)"

    try:
        power_dir = "/sys/class/power_supply"
        if os.path.isdir(power_dir):
            for supply in os.listdir(power_dir):
                online_path = os.path.join(power_dir, supply, "online")
                if os.path.isfile(online_path):
                    with open(online_path, "r") as f:
                        if f.read().strip() == "1":
                            return "AC Main Power Connected"
                status_path = os.path.join(power_dir, supply, "status")
                if os.path.isfile(status_path):
                    with open(status_path, "r") as f:
                        return f"Battery ({f.read().strip()})"
    except Exception:
        pass

    return "AC Main Power Connected"


def send_heartbeat(cfg):
    """Collect metrics, sign with HMAC-SHA256, and send HTTP POST."""
    win_data = get_windows_host_metrics()

    cpu_pct, cores, load_avg = get_cpu_info(win_data)
    mem_pct, mem_used, mem_total = get_memory_info(win_data)
    disk_pct, disk_used, disk_free, disk_total = get_disk_info(win_data)
    uptime_sec, boot_time = get_uptime_and_boot(win_data)
    services_status = check_services(cfg["monitored_services"])
    lan_ip, tailscale_ip = get_network_ips(win_data)
    power_stat = get_power_status(win_data)

    if win_data and "cs" in win_data and win_data["cs"].get("Name"):
        hostname = f"{win_data['cs']['Name']} (Win 11) + {socket.gethostname()} (WSL)"
    else:
        hostname = socket.gethostname()

    payload = {
        "server_id": cfg["server_id"],
        "server_name": cfg["server_name"],
        "server_role": cfg["server_role"],
        "location": cfg["location"],
        "hostname": hostname,
        "ip_address": lan_ip,
        "tailscale_ip": tailscale_ip,
        "cpu_percent": cpu_pct,
        "cpu_cores": cores,
        "load_avg": load_avg,
        "memory_percent": mem_pct,
        "memory_used_gb": mem_used,
        "memory_total_gb": mem_total,
        "disk_percent": disk_pct,
        "disk_used_gb": disk_used,
        "disk_free_gb": disk_free,
        "disk_total_gb": disk_total,
        "uptime_seconds": uptime_sec,
        "boot_time": boot_time,
        "services": services_status,
        "power_status": power_stat
    }

    raw_body = json.dumps(payload, separators=(",", ":"))
    timestamp = str(int(time.time()))

    # Compute HMAC-SHA256 signature
    msg = f"{timestamp}:{raw_body}".encode("utf-8")
    signature = hmac.new(cfg["secret_key"].encode("utf-8"), msg, hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Server-Id": cfg["server_id"],
        "X-Timestamp": timestamp,
        "X-Signature": signature,
        "User-Agent": "SD-Telemetry-Sentinel/2.0"
    }

    req = urllib.request.Request(
        cfg["endpoint"],
        data=raw_body.encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status_code = resp.status
            if status_code in (200, 201):
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Heartbeat dispatched: CPU {cpu_pct}% | RAM {mem_pct}% | Disk {disk_pct}% (Free: {disk_free}GB of {disk_total}GB) | HTTP {status_code}")
                return True
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Heartbeat HTTP Warning: {status_code}", file=sys.stderr)
                return False
    except urllib.error.HTTPError as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Heartbeat HTTP Error: {e.code} - {e.read().decode('utf-8', 'ignore')}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Heartbeat Connection Failed: {e}", file=sys.stderr)
        return False


def main():
    print("=" * 60)
    print("Siva Durga Infrastructure Sentinel - Starting Telemetry Daemon")
    print("=" * 60)
    cfg = load_config()
    print(f"Server ID      : {cfg['server_id']}")
    print(f"Server Name    : {cfg['server_name']}")
    print(f"Server Role    : {cfg['server_role']}")
    print(f"Location       : {cfg['location']}")
    print(f"Target Endpoint: {cfg['endpoint']}")
    print(f"Interval       : {cfg['interval']}s")
    print("-" * 60)

    # Initial instant heartbeat
    send_heartbeat(cfg)

    # Continuous monitoring loop
    while True:
        try:
            time.sleep(cfg["interval"])
            send_heartbeat(cfg)
        except KeyboardInterrupt:
            print("\nSentinel daemon shutting down gracefully.")
            break
        except Exception as e:
            print(f"[Sentinel Daemon Error] {e}", file=sys.stderr)
            time.sleep(10)


if __name__ == "__main__":
    main()
