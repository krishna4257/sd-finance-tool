"""
Blueprint route modules for SD Accounting Tool.
"""

from routes.mobile_api_routes import mobile_bp
from routes.feed_routes import feed_bp
from routes.payment_routes import payment_bp
from routes.banking_controller import banking_bp
from routes.chit_controller import chit_bp
from routes.fleet_telemetry_controller import register_fleet_telemetry_routes

__all__ = [
    "mobile_bp",
    "feed_bp",
    "payment_bp",
    "banking_bp",
    "chit_bp",
    "register_fleet_telemetry_routes",
]
