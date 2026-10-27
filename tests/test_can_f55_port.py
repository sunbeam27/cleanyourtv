"""Read-only acceptance checks for the local CAN F55 source configuration; never contacts a TV."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


SOURCE = Path(__file__).resolve().parents[1] / "launcher" / "app" / "src"
ANDROID = "{http://schemas.android.com/apk/res/android}"


def resources(source_set, name="config.xml"):
    root = ET.parse(SOURCE / source_set / "res" / "values" / name).getroot()
    return {item.get("name"): item for item in root}


def main_activity(manifest):
    return next(activity for activity in manifest.find("application").findall("activity")
                if activity.get(ANDROID + "name") in (".MainActivity", "com.gathin.tvhome.MainActivity"))


def main_filters(activity):
    return [{category.get(ANDROID + "name") for category in intent.findall("category")}
            for intent in activity.findall("intent-filter")
            if any(action.get(ANDROID + "name") == "android.intent.action.MAIN"
                   for action in intent.findall("action"))]


class CanF55SourceTest(unittest.TestCase):
    def test_home_and_both_app_catalogues_can_open_main_activity(self):
        manifest = ET.parse(SOURCE / "main" / "AndroidManifest.xml").getroot()
        main = main_activity(manifest)
        self.assertEqual("true", main.get(ANDROID + "exported"))
        filters = main_filters(main)
        self.assertFalse(any("android.intent.category.LAUNCHER" in entry for entry in filters),
                         "The standard build keeps the upstream app entry points")
        flavor = ET.parse(SOURCE / "canF55" / "AndroidManifest.xml").getroot()
        filters += main_filters(main_activity(flavor))
        self.assertTrue(any({"android.intent.category.HOME", "android.intent.category.DEFAULT"} <= entry
                            for entry in filters))
        for category in ("LAUNCHER", "LEANBACK_LAUNCHER"):
            self.assertTrue(any("android.intent.category." + category in entry for entry in filters))
        leanback = next(feature for feature in manifest.findall("uses-feature")
                        if feature.get(ANDROID + "name") == "android.software.leanback")
        self.assertEqual("false", leanback.get(ANDROID + "required"))

    def test_tvbox_and_stock_home_remain_available_as_selected_shortcuts(self):
        config = resources("canF55")
        expected = ["com.github.tvbox.osc.jun", "cn.cibntv.ott"]
        self.assertEqual(expected, [item.text for item in config["dock_apps"]])
        self.assertEqual(expected, [item.text for item in config["library_apps"]])
        self.assertEqual("true", config["app_library"].text)
        self.assertEqual("true", config["library_ok_opens"].text)

    def test_no_boot_app_or_stock_home_redirect_is_selected_by_default(self):
        effective = resources("main")
        effective.update(resources("canF55"))
        self.assertEqual("false", effective["boot_to_live_tv"].text)
        self.assertEqual("false", effective["open_on_start_choice"].text)
        self.assertFalse(effective["stock_home_redirect"].text)
        self.assertFalse(effective["live_tv_package"].text)

    def test_f55_uses_system_fonts_without_a_resource_font_loader(self):
        fonts = resources("canF55", "fonts.xml")
        for name in ("font_body", "font_regular", "font_light", "font_extralight", "font_medium"):
            self.assertTrue(fonts[name].text.startswith("sans-serif"), name)


if __name__ == "__main__":
    unittest.main()
