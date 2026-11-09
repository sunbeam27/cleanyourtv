"""Pure tests for the final APK basic-profile acceptance gate; no device or SDK required."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("verify_can_f55_apk", Path(__file__).resolve().parents[1] / "tools/verify_can_f55_apk.py")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class BasicProfileVerificationTest(unittest.TestCase):
    def report(self):
        return {"permissions": ["android.permission.ACCESS_NETWORK_STATE"],
                "activity_components": ["com.gathin.tvhome.MainActivity"],
                "service_components": ["com.gathin.tvhome.ClockDream"], "receiver_components": []}

    def test_basic_profile_passes(self):
        self.assertTrue(all(VERIFY.basic_profile_checks(self.report()).values()))

    def test_each_removed_helper_fails_acceptance(self):
        for name in ("HomeKeyService", "InputKeyService", "GuardRevival", "GuardConfig"):
            with self.subTest(name=name):
                report = self.report()
                report["receiver_components" if name == "GuardConfig" else "service_components"].append("com.gathin.tvhome." + name)
                self.assertFalse(VERIFY.basic_profile_checks(report)["no_home_interception_helpers"])

    def test_probe_activity_fails_acceptance(self):
        report = self.report()
        report["activity_components"].append("com.gathin.tvhome.ProbeActivity")
        self.assertFalse(VERIFY.basic_profile_checks(report)["no_probe_activity"])

    def test_each_removed_permission_fails_acceptance(self):
        for name in ("android.permission.WRITE_SECURE_SETTINGS", "android.permission.ACCESS_FINE_LOCATION", "yandex.tv.permission.ACCESS_TV_SOURCE"):
            with self.subTest(name=name):
                report = self.report()
                report["permissions"].append(name)
                self.assertFalse(all(VERIFY.basic_profile_checks(report).values()))
