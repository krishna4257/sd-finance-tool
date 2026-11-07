import os
import unittest
from unittest.mock import patch, MagicMock

from app import app
from routes.mobile_api_routes import mobile_bp
from routes.feed_routes import feed_bp
from routes.payment_routes import payment_bp
from routes.chit_controller import chit_bp
from routes.banking_controller import banking_bp


class TestPhase4ModularBlueprints(unittest.TestCase):
    """
    Validation test suite for Phase 4 Incremental Blueprint Modularization.
    Ensures blueprints are registered, route URLs are preserved, auth decorators work,
    and no circular imports or regressions exist.
    """

    def setUp(self):
        self.orig_csrf = app.config.get("WTF_CSRF_ENABLED", True)
        app.config["WTF_CSRF_ENABLED"] = False
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        app.config["WTF_CSRF_ENABLED"] = self.orig_csrf
        self.app_context.pop()

    def test_blueprint_registration(self):
        """Verify all blueprints are loaded and registered with correct names."""
        registered_bps = app.blueprints
        self.assertIn("mobile_bp", registered_bps)
        self.assertIn("feed_bp", registered_bps)
        self.assertIn("payment_bp", registered_bps)
        self.assertIn("chit_bp", registered_bps)
        self.assertIn("banking_bp", registered_bps)

    def test_mobile_blueprint_routes_registered(self):
        """Verify mobile API routes are registered and mapped to mobile_bp."""
        rules = {rule.rule: rule.endpoint for rule in app.url_map.iter_rules()}
        
        self.assertIn("/api/mobile/login", rules)
        self.assertTrue(rules["/api/mobile/login"].startswith("mobile_bp."))

        self.assertIn("/api/mobile/customers", rules)
        self.assertTrue(rules["/api/mobile/customers"].startswith("mobile_bp."))

        self.assertIn("/api/mobile/payments", rules)
        self.assertTrue(rules["/api/mobile/payments"].startswith("mobile_bp."))

        self.assertIn("/api/mobile/reset_database", rules)
        self.assertTrue(rules["/api/mobile/reset_database"].startswith("mobile_bp."))

        self.assertIn("/api/mobile/customer_feed", rules)
        self.assertTrue(rules["/api/mobile/customer_feed"].startswith("mobile_bp."))

        self.assertIn("/api/mobile/payment_feed_batch", rules)
        self.assertTrue(rules["/api/mobile/payment_feed_batch"].startswith("mobile_bp."))

    def test_feed_blueprint_routes_registered(self):
        """Verify feed management routes are registered and mapped to feed_bp."""
        rules = {rule.rule: rule.endpoint for rule in app.url_map.iter_rules()}

        self.assertIn("/feed", rules)
        self.assertTrue(rules["/feed"].startswith("feed_bp."))

        self.assertIn("/feed/payment/accept_batch", rules)
        self.assertTrue(rules["/feed/payment/accept_batch"].startswith("feed_bp."))

        self.assertIn("/feed/payment/accept/<feed_payment_id>", rules)
        self.assertTrue(rules["/feed/payment/accept/<feed_payment_id>"].startswith("feed_bp."))

        self.assertIn("/feed/closure/accept/<feed_id>", rules)
        self.assertTrue(rules["/feed/closure/accept/<feed_id>"].startswith("feed_bp."))

    def test_payment_blueprint_routes_registered(self):
        """Verify posting and payment routes are registered and mapped to payment_bp."""
        rules = {rule.rule: rule.endpoint for rule in app.url_map.iter_rules()}

        self.assertIn("/posting", rules)
        self.assertTrue(rules["/posting"].startswith("payment_bp."))

        self.assertIn("/delete_payment", rules)
        self.assertTrue(rules["/delete_payment"].startswith("payment_bp."))

        self.assertIn("/submit_post_payment", rules)
        self.assertTrue(rules["/submit_post_payment"].startswith("payment_bp."))

        self.assertIn("/api/posting_report", rules)
        self.assertTrue(rules["/api/posting_report"].startswith("payment_bp."))

        self.assertIn("/api/payment_day_stats", rules)
        self.assertTrue(rules["/api/payment_day_stats"].startswith("payment_bp."))

    def test_mobile_route_unauthenticated_blocks(self):
        """Verify mobile routes enforce mobile authentication."""
        res = self.app.get("/api/mobile/customers?vid=1")
        self.assertEqual(res.status_code, 401)
        self.assertIn("missing token", res.get_json().get("error", "").lower())

    def test_feed_route_unauthenticated_redirects(self):
        """Verify feed route requires session authentication."""
        res = self.app.get("/feed")
        # Unauthenticated HTML request redirects to /login
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers.get("Location", "").endswith("/login"))

    def test_payment_route_unauthenticated_blocks(self):
        """Verify payment route requires authentication and returns 401 on AJAX."""
        res = self.app.post("/delete_payment", json={"pid": 123})
        self.assertEqual(res.status_code, 401)
        self.assertTrue(res.get_json().get("session_expired", False))

    def test_no_circular_imports_across_modules(self):
        """Verify leaf modules and blueprints can be imported cleanly in isolation."""
        import security.auth
        import security.mobile_auth
        import services.audit_service
        import services.mobile_service
        import services.customer_service
        import services.payment_service
        import routes.mobile_api_routes
        import routes.feed_routes
        import routes.payment_routes

        self.assertIsNotNone(security.auth.login_required)
        self.assertIsNotNone(security.mobile_auth.mobile_auth_required)
        self.assertIsNotNone(services.audit_service.audit_log)
        self.assertIsNotNone(services.mobile_service.normalize_account_number)
        self.assertIsNotNone(services.customer_service.recalc_customer_balance)
        self.assertIsNotNone(services.payment_service.is_village_monthly)
        self.assertIsNotNone(routes.mobile_api_routes.mobile_bp)
        self.assertIsNotNone(routes.feed_routes.feed_bp)
        self.assertIsNotNone(routes.payment_routes.payment_bp)


if __name__ == "__main__":
    unittest.main()
