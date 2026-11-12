#!/usr/bin/env python3
"""
SD Finance: Chat Infrastructure & Services Health Checker
File: SD_Accounting_Tool/scripts/check_chat_services.py

Performs health and connectivity checks against:
1. Redis (In-memory queue - port 6379)
2. Centrifugo (Real-time WebSocket engine - port 8001)
3. NotifKit (Notification orchestrator - port 4000)
4. Chat Media Storage (/var/www/sd-chat-media)
"""

import os
import sys
import socket
import urllib.request
import urllib.error
import shutil
import json
import time


def check_port(host, port, timeout=1.5):
    """Check if a TCP socket is open and listening."""
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            latency = (time.time() - start) * 1000
            return True, f"{latency:.1f}ms"
    except Exception as e:
        return False, str(e)


def check_http_endpoint(url, timeout=2.0, expected_codes=(200, 404, 401)):
    """Check if an HTTP service responds."""
    start = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SDFinance-HealthCheck/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            latency = (time.time() - start) * 1000
            return True, f"HTTP {response.status} ({latency:.1f}ms)"
    except urllib.error.HTTPError as e:
        latency = (time.time() - start) * 1000
        if e.code in expected_codes:
            return True, f"HTTP {e.code} ({latency:.1f}ms)"
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, f"Connection Failed: {e}"


def check_websocket_handshake(host="127.0.0.1", port=8001, path="/connection/websocket", timeout=2.0):
    """Verify Centrifugo WebSocket upgrade handshake."""
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            req = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}:{port}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
                f"Sec-WebSocket-Version: 13\r\n\r\n"
            )
            s.sendall(req.encode("utf-8"))
            res = s.recv(1024).decode("utf-8", errors="ignore")
            latency = (time.time() - start) * 1000
            if "101 Switching Protocols" in res:
                return True, f"101 Switching Protocols ({latency:.1f}ms)"
            return False, f"Handshake failed: {res.splitlines()[0] if res else 'No response'}"
    except Exception as e:
        return False, str(e)


def check_media_storage(path="/var/www/sd-chat-media"):
    """Check media directory existence, writability, and free disk space."""
    if not os.path.exists(path):
        return False, f"Directory does not exist: {path}"
    
    # Check writability
    test_file = os.path.join(path, ".health_check_write_test")
    try:
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        writable = True
    except Exception:
        writable = False

    try:
        total, used, free = shutil.disk_usage(path)
        free_gb = free / (1024 ** 3)
        total_gb = total / (1024 ** 3)
        return True, f"Writable: {writable} | Free: {free_gb:.1f} GB of {total_gb:.1f} GB"
    except Exception as e:
        return False, f"Disk check error: {e}"


def main():
    print("==========================================================")
    print("      Siva Durga Finance: Chat Services Health Sentinel   ")
    print("==========================================================")

    services = [
        ("Redis Server", "127.0.0.1", 6379, "TCP Socket"),
        ("Centrifugo HTTP Health", "http://127.0.0.1:8001/health", None, "HTTP Health API"),
        ("Centrifugo WS Protocol", "127.0.0.1", 8001, "ws_handshake"),
        ("NotifKit Engine", "http://127.0.0.1:4000/health", None, "HTTP Health API")
    ]

    all_passed = True

    for name, target, port, stype in services:
        if stype == "ws_handshake":
            ok, detail = check_websocket_handshake(target, port)
        elif port is not None:
            ok, detail = check_port(target, port)
        else:
            ok, detail = check_http_endpoint(target)

        status_tag = "[PASS]" if ok else "[FAIL]"
        print(f"{status_tag} {name:<25} -> {detail}")
        if not ok:
            all_passed = False

    # Check Media Storage
    media_path = "/var/www/sd-chat-media"
    ok, detail = check_media_storage(media_path)
    status_tag = "[PASS]" if ok else "[WARN]"
    print(f"{status_tag} {'Media Storage (' + media_path + ')' :<25} -> {detail}")

    print("==========================================================")
    if all_passed:
        print("[✓] All real-time chat infrastructure daemons are active.")
        sys.exit(0)
    else:
        print("[!] Note: Some daemons are not running locally.")
        print("    Run: sudo bash scripts/setup_phase2_daemons.sh")
        sys.exit(1)


if __name__ == "__main__":
    main()
