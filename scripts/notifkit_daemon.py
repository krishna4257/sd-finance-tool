#!/usr/bin/env python3
"""
SD Finance: Lightweight Notification Orchestration Daemon (NotifKit)
File: SD_Accounting_Tool/scripts/notifkit_daemon.py

Listens on 127.0.0.1:4000 to orchestrate notifications:
- Chat Push Notifications (FCM)
- SMS Receipts for Loan & Chit collections
- Audit alerts for Management

Provides:
- GET  /health          -> 200 OK JSON status
- POST /api/v1/notify   -> 202 Accepted (Queues to Redis / Log)
"""

import os
import sys
import json
import time
import signal
import logging
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [NotifKit] %(message)s"
)
logger = logging.getLogger("notifkit")

HOST = os.environ.get("NOTIFKIT_HOST", "127.0.0.1")
PORT = int(os.environ.get("NOTIFKIT_PORT", 4000))
SECRET = os.environ.get("NOTIFKIT_API_SECRET", "sdfinance-notifkit-secret-2026")
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

# Attempt Redis connection for background queuing
redis_client = None
try:
    import redis
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_timeout=1.0)
    redis_client.ping()
    logger.info("Connected to Redis at %s:%s for notification queues.", REDIS_HOST, REDIS_PORT)
except Exception as e:
    logger.warning("Redis queue optional: %s (operating in direct mode)", e)


class NotifKitHandler(BaseHTTPRequestHandler):
    server_version = "NotifKit-Daemon/1.0"

    def log_message(self, format, *args):
        # Route standard server log to python logging
        logger.info("%s - - [%s] %s", self.client_address[0], self.log_date_time_string(), format % args)

    def send_json(self, status_code, data):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path in ("/health", "/healthz", "/", "/api/v1/health"):
            self.send_json(200, {
                "status": "healthy",
                "service": "notifkit-engine",
                "version": "1.0.0",
                "redis_connected": bool(redis_client),
                "timestamp": int(time.time())
            })
        else:
            self.send_json(404, {"error": "Not Found"})

    def do_POST(self):
        if self.path == "/api/v1/notify":
            # 1. Check Auth Header if secret is configured
            auth_header = self.headers.get("Authorization", "")
            if SECRET and auth_header != f"Bearer {SECRET}":
                self.send_json(401, {"error": "Unauthorized: Invalid secret key"})
                return

            # 2. Read Body
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(content_length).decode("utf-8")
                body = json.loads(raw_body)
            except Exception as e:
                self.send_json(400, {"error": f"Invalid JSON body: {e}"})
                return

            event_type = body.get("eventType", "unknown")
            recipient_id = body.get("recipientId")
            priority = body.get("priority", "normal")
            data = body.get("data", {})

            logger.info("Notification received: event=%s, recipient=%s, priority=%s", event_type, recipient_id, priority)

            # 3. Queue to Redis list if available
            if redis_client:
                try:
                    queue_payload = json.dumps({
                        "event": event_type,
                        "recipient": recipient_id,
                        "priority": priority,
                        "data": data,
                        "enqueued_at": time.time()
                    })
                    redis_client.lpush("notifkit:notifications:queue", queue_payload)
                except Exception as ex:
                    logger.warning("Failed to push to Redis queue: %s", ex)

            self.send_json(202, {
                "success": True,
                "message": "Notification accepted for delivery",
                "eventType": event_type,
                "recipientId": recipient_id
            })
        else:
            self.send_json(404, {"error": "Endpoint Not Found"})


def main():
    server_address = (HOST, PORT)
    httpd = ThreadingHTTPServer(server_address, NotifKitHandler)
    logger.info("Siva Durga Finance: NotifKit Daemon listening on http://%s:%s", HOST, PORT)

    def shutdown_signal(signum, frame):
        logger.info("Shutdown signal received. Stopping NotifKit...")
        httpd.server_close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_signal)
    signal.signal(signal.SIGTERM, shutdown_signal)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
