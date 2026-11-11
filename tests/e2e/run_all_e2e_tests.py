"""Master End-to-End Test Suite Runner for SD Finance Tool.
Executes all 5 domains sequentially against PostgreSQL and outputs a detailed verification report.
"""

import sys
import os
import time
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.e2e.test_village_accounting_e2e import TestVillageAccountingE2E
from tests.e2e.test_mobile_push_and_feed_e2e import TestMobilePushAndFeedE2E
from tests.e2e.test_central_banking_e2e import TestCentralBankingE2E
from tests.e2e.test_chit_fund_e2e import TestChitFundE2E
from tests.e2e.test_admin_and_telemetry_e2e import TestAdminAndTelemetryE2E

class DetailedTestResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_records = []

    def startTest(self, test):
        super().startTest(test)
        self._start_time = time.time()

    def addSuccess(self, test):
        super().addSuccess(test)
        elapsed = time.time() - self._start_time
        doc = (test._testMethodDoc or test._testMethodName).strip().split("\n")[0]
        self.test_records.append({
            "name": test._testMethodName,
            "domain": test.__class__.__name__,
            "description": doc,
            "status": "WORKED",
            "elapsed_ms": round(elapsed * 1000, 2),
            "error": None
        })

    def addFailure(self, test, err):
        super().addFailure(test, err)
        elapsed = time.time() - self._start_time
        doc = (test._testMethodDoc or test._testMethodName).strip().split("\n")[0]
        self.test_records.append({
            "name": test._testMethodName,
            "domain": test.__class__.__name__,
            "description": doc,
            "status": "NOT WORKED",
            "elapsed_ms": round(elapsed * 1000, 2),
            "error": str(err[1])
        })

    def addError(self, test, err):
        super().addError(test, err)
        elapsed = time.time() - self._start_time
        doc = (test._testMethodDoc or test._testMethodName).strip().split("\n")[0]
        self.test_records.append({
            "name": test._testMethodName,
            "domain": test.__class__.__name__,
            "description": doc,
            "status": "NOT WORKED",
            "elapsed_ms": round(elapsed * 1000, 2),
            "error": str(err[1])
        })


def run_master_suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all 5 domains in sequence
    suite.addTests(loader.loadTestsFromTestCase(TestVillageAccountingE2E))
    suite.addTests(loader.loadTestsFromTestCase(TestMobilePushAndFeedE2E))
    suite.addTests(loader.loadTestsFromTestCase(TestCentralBankingE2E))
    suite.addTests(loader.loadTestsFromTestCase(TestChitFundE2E))
    suite.addTests(loader.loadTestsFromTestCase(TestAdminAndTelemetryE2E))

    runner = unittest.TextTestRunner(resultclass=DetailedTestResult, verbosity=2)
    start = time.time()
    result = runner.run(suite)
    total_elapsed = time.time() - start

    print("\n" + "=" * 80)
    print("MASTER END-TO-END ECOSYSTEM VERIFICATION REPORT")
    print("=" * 80)
    print(f"Total Tests Run: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed / Errors: {len(result.failures) + len(result.errors)}")
    print(f"Total Execution Time: {round(total_elapsed, 2)}s\n")

    print(f"{'DOMAIN':<30} | {'TEST CASE':<32} | {'STATUS':<10} | {'TIME (ms)':<10}")
    print("-" * 88)
    for rec in result.test_records:
        domain_label = rec['domain'].replace("Test", "").replace("E2E", "")
        status_str = "PASS" if rec['status'] == "WORKED" else "FAIL"
        print(f"{domain_label:<30} | {rec['name']:<32} | {status_str:<10} | {rec['elapsed_ms']:<10}")

    if result.wasSuccessful():
        print("\nALL FEATURES WORKED CLEANLY ACROSS ALL 5 ECOSYSTEM DOMAINS!")
        return 0
    else:
        print("\nISSUES DETECTED IN TEST RUN:")
        for rec in result.test_records:
            if rec['status'] != "WORKED":
                print(f"[-] {rec['domain']}.{rec['name']}: {rec['error']}")
        return 1

if __name__ == "__main__":
    sys.exit(run_master_suite())
