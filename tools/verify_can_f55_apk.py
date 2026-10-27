#!/usr/bin/env python3
"""Verify both locally built APK variants without installing or contacting a device.

Example (run from the repository root):
  python tools/verify_can_f55_apk.py --sdk "$ANDROID_HOME" \
    --f55 launcher/app/build/outputs/apk/canF55/release/app-canF55-release.apk \
    --standard launcher/app/build/outputs/apk/standard/release/app-standard-release.apk \
    --output artifacts/apk-verification

--output is a report prefix, optionally ending in .json or .md. Both files are
written. Reports contain APK basenames and certificate digests, not local paths,
signer distinguished names, keystores, private keys, or environment identifiers.
Only official SDK build-tools (aapt, apksigner, zipalign) are invoked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile


MAIN = "android.intent.action.MAIN"
HOME = "android.intent.category.HOME"
DEFAULT = "android.intent.category.DEFAULT"
LAUNCHER = "android.intent.category.LAUNCHER"
LEANBACK = "android.intent.category.LEANBACK_LAUNCHER"
MAIN_ACTIVITY = "com.gathin.tvhome.MainActivity"
INTERNET = "android.permission.INTERNET"
LEANBACK_FEATURE = "android.software.leanback"
SIGNING_NOTICE = (
    "Test/debug build only, not a production release. Signature checks establish "
    "APK integrity and scheme compatibility; a certificate digest does not establish publisher trust."
)


class VerificationError(Exception):
    """An operational error whose message is safe to put in a public CI report."""


def find_tools(sdk: Path) -> tuple[str, dict[str, list[str]]]:
    root = sdk / "build-tools"
    versions = [p for p in root.iterdir() if p.is_dir()] if root.is_dir() else []
    # Match the fixed compile toolchain instead of silently taking a newer runner SDK.
    versions = [p for p in versions if p.name == "34.0.0"]
    for directory in versions:
        commands: dict[str, list[str]] = {}
        for name in ("aapt", "zipalign"):
            executable = directory / (name + (".exe" if os.name == "nt" else ""))
            if executable.is_file():
                commands[name] = [str(executable)]
        signer = directory / "apksigner"
        signer_jar = directory / "lib" / "apksigner.jar"
        if os.name != "nt" and signer.is_file():
            commands["apksigner"] = [str(signer)]
        elif signer_jar.is_file() and shutil.which("java"):
            # Calling the official jar directly avoids Windows .bat shell quoting.
            commands["apksigner"] = [shutil.which("java"), "-jar", str(signer_jar)]
        if len(commands) == 3:
            return directory.name, commands
    raise VerificationError("SDK build-tools 34.0.0 with aapt, apksigner and zipalign was not found.")


def run_tool(command: list[str], label: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        # Exception text can include host paths. Keep it out of saved artifacts.
        raise VerificationError(f"{label} could not execute or exceeded 60 seconds.") from None


def checked_output(command: list[str], label: str) -> str:
    result = run_tool(command, label)
    if result.returncode:
        raise VerificationError(f"{label} failed with exit code {result.returncode}; raw output is not retained.")
    return result.stdout


def xml_value(value: str):
    raw = re.search(r'\(Raw: ("(?:[^"\\]|\\.)*")\)\s*$', value)
    quoted = raw.group(1) if raw else None
    if quoted is None:
        match = re.match(r'("(?:[^"\\]|\\.)*")', value)
        quoted = match.group(1) if match else None
    if quoted is not None:
        try:
            return json.loads(quoted)
        except ValueError:
            raise VerificationError("aapt emitted an unsupported quoted manifest attribute.") from None
    typed = re.fullmatch(r"\(type 0x([0-9a-fA-F]+)\)\s*(0x[0-9a-fA-F]+|-?\d+)", value.strip())
    if typed:
        kind, number = int(typed.group(1), 16), int(typed.group(2), 0)
        return bool(number) if kind == 0x12 else number
    return value.strip()


def parse_xmltree(output: str) -> dict:
    """Reconstruct aapt's indentation tree so query intents cannot pass activity checks."""
    roots: list[dict] = []
    stack: list[tuple[int, dict]] = []
    for line in output.splitlines():
        indent = len(line) - len(line.lstrip())
        content = line.strip()
        element = re.match(r"E: ([^\s(]+)", content)
        if element:
            node = {"tag": element.group(1), "attrs": {}, "children": []}
            while stack and stack[-1][0] >= indent:
                stack.pop()
            (stack[-1][1]["children"] if stack else roots).append(node)
            stack.append((indent, node))
        elif content.startswith("A:"):
            attribute = re.match(r"A: ([^\s(=]+)(?:\(0x[0-9a-fA-F]+\))?=(.*)", content)
            if not stack or not attribute:
                raise VerificationError("aapt emitted an unsupported manifest tree attribute.")
            stack[-1][1]["attrs"][attribute.group(1)] = xml_value(attribute.group(2))
    if len(roots) != 1 or roots[0]["tag"] != "manifest":
        raise VerificationError("aapt manifest output did not contain exactly one manifest root.")
    return roots[0]


def children(node: dict, tag: str) -> list[dict]:
    return [child for child in node["children"] if child["tag"] == tag]


def component_name(name: str, package: str) -> str:
    if name.startswith("."):
        return package + name
    return name if "." in name else package + "." + name


def manifest_summary(root: dict, package: str) -> dict:
    applications = children(root, "application")
    if len(applications) != 1:
        raise VerificationError("Manifest does not contain exactly one application.")
    application = applications[0]
    activities = []
    for node in application["children"]:
        if node["tag"] not in ("activity", "activity-alias"):
            continue
        attrs = node["attrs"]
        filters = []
        for intent in children(node, "intent-filter"):
            filters.append({
                "actions": sorted(c["attrs"].get("android:name", "") for c in children(intent, "action")),
                "categories": sorted(c["attrs"].get("android:name", "") for c in children(intent, "category")),
            })
        activities.append({
            "name": component_name(attrs.get("android:name", ""), package),
            "enabled": application["attrs"].get("android:enabled", True) is not False
                       and attrs.get("android:enabled", True) is not False,
            "exported": attrs.get("android:exported", bool(filters)) is not False,
            "intent_filters": filters,
        })
    main = [activity for activity in activities if activity["name"] == MAIN_ACTIVITY]
    permissions = sorted({node["attrs"].get("android:name", "") for node in root["children"]
                          if node["tag"] in ("uses-permission", "uses-permission-sdk-23", "uses-permission-sdk-m")})
    leanback = [node["attrs"].get("android:required", True) for node in children(root, "uses-feature")
                if node["attrs"].get("android:name") == LEANBACK_FEATURE]
    sdk = children(root, "uses-sdk")
    return {
        "manifest_package": root["attrs"].get("package"),
        "manifest_min_sdk": sdk[0]["attrs"].get("android:minSdkVersion") if len(sdk) == 1 else None,
        "manifest_target_sdk": sdk[0]["attrs"].get("android:targetSdkVersion") if len(sdk) == 1 else None,
        "main_activity": main[0] if len(main) == 1 else None,
        "launcher_activities": [activity["name"] for activity in activities
                                if has_entry(activity, {LAUNCHER})],
        "permissions": permissions,
        "leanback_required": leanback[0] if len(leanback) == 1 else None,
    }


def has_entry(activity: dict | None, categories: set[str]) -> bool:
    return bool(activity and activity["enabled"] and activity["exported"]
                and any(MAIN in intent["actions"] and categories.issubset(intent["categories"])
                        for intent in activity["intent_filters"]))


def parse_badging(output: str) -> dict:
    package = re.search(r"^package: (.*)$", output, re.MULTILINE)
    minimum = re.search(r"^sdkVersion:'(\d+)'", output, re.MULTILINE)
    target = re.search(r"^targetSdkVersion:'(\d+)'", output, re.MULTILINE)
    attrs = dict(re.findall(r"([\w-]+)='([^']*)'", package.group(1))) if package else {}
    if not all(name in attrs for name in ("name", "versionCode", "versionName")) or not minimum or not target:
        raise VerificationError("aapt badging output lacked package, version, minSdk or targetSdk.")
    return {"package_name": attrs["name"], "version_code": attrs["versionCode"],
            "version_name": attrs["versionName"], "min_sdk": int(minimum.group(1)),
            "target_sdk": int(target.group(1))}


def signature_summary(output: str, returncode: int) -> dict:
    schemes = {version: result == "true" for version, result in re.findall(
        r"^Verified using (v[\d.]+) scheme[^:]*:\s*(true|false)\s*$", output, re.MULTILINE)}
    digests = [digest.replace(":", "").lower() for digest in re.findall(
        r"^Signer #\d+ certificate SHA-256 digest:\s*([0-9a-fA-F:]+)\s*$", output, re.MULTILINE)]
    return {"verified": returncode == 0, "schemes": schemes,
            "certificate_sha256": digests,
            "single_certificate_digest": len(digests) == 1 and bool(re.fullmatch(r"[0-9a-f]{64}", digests[0])),
            "notice": SIGNING_NOTICE}


def verify_apk(path: Path, variant: str, commands: dict[str, list[str]]) -> dict:
    report = {"variant": variant, "apk_file": path.name, "passed": False, "checks": {}}
    try:
        if not path.is_file():
            raise VerificationError("APK file does not exist.")
        report["size_bytes"] = path.stat().st_size
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        report["sha256"] = digest.hexdigest()
        with zipfile.ZipFile(path) as archive:
            report["native_libraries"] = sorted(name for name in archive.namelist()
                                                 if name.startswith("lib/") and name.endswith(".so"))
        report.update(parse_badging(checked_output(commands["aapt"] + ["dump", "badging", str(path)], "aapt badging")))
        manifest = parse_xmltree(checked_output(commands["aapt"] + ["dump", "xmltree", str(path), "AndroidManifest.xml"], "aapt xmltree"))
        report.update(manifest_summary(manifest, report["package_name"]))
        signed = run_tool(commands["apksigner"] + ["verify", "--verbose", "--print-certs", "--min-sdk-version",
                                                   str(report["min_sdk"]), str(path)], "apksigner verify")
        report["signing"] = signature_summary(signed.stdout + "\n" + signed.stderr, signed.returncode)
        aligned = run_tool(commands["zipalign"] + ["-c", "-v", "4", str(path)], "zipalign check")
        expected_package, expected_minimum = (("com.gathin.tvhome.canf55", 21) if variant == "canF55"
                                              else ("com.gathin.tvhome", 26))
        report["checks"] = {
            "package_name": report["package_name"] == expected_package == report["manifest_package"],
            "min_sdk": report["min_sdk"] == expected_minimum == report["manifest_min_sdk"],
            "target_sdk_34": report["target_sdk"] == 34 == report["manifest_target_sdk"],
            "main_home_default": has_entry(report["main_activity"], {HOME, DEFAULT}),
            "main_leanback_launcher": has_entry(report["main_activity"], {LEANBACK}),
            "leanback_optional": report["leanback_required"] is False,
            "no_internet_permission": INTERNET not in report["permissions"],
            "no_native_libraries": not report["native_libraries"],
            "signature_verified": report["signing"]["verified"],
            "single_certificate_sha256": report["signing"]["single_certificate_digest"],
            "zipalign_4_bytes": aligned.returncode == 0,
        }
        if variant == "canF55":
            report["checks"]["main_android_launcher"] = has_entry(report["main_activity"], {LAUNCHER})
            report["checks"]["v1_signature_for_api_21"] = report["signing"]["schemes"].get("v1") is True
        else:
            report["checks"]["no_android_launcher_entry"] = not report["launcher_activities"]
        report["passed"] = all(report["checks"].values())
    except VerificationError as error:
        report["error"] = str(error)
    except (OSError, zipfile.BadZipFile):
        report["error"] = "APK could not be read as a ZIP archive."
    except (ValueError, TypeError, KeyError, AttributeError):
        report["error"] = "SDK output did not match the supported manifest or signature format."
    return report


def markdown_report(report: dict) -> str:
    lines = ["# CAN F55 APK verification", "", f"Result: **{'PASS' if report['passed'] else 'FAIL'}**", "",
             SIGNING_NOTICE, "", "Static APK checks only. No device installation, HOME selection or runtime test was performed.", ""]
    if "error" in report:
        lines.extend([f"Error: {report['error']}", ""])
    if "build_tools_version" in report:
        lines.extend([f"SDK build-tools: `{report['build_tools_version']}`", ""])
    for apk in report["apks"]:
        lines.extend([f"## {apk['variant']}", "", f"Result: **{'PASS' if apk['passed'] else 'FAIL'}**", ""])
        for key in ("apk_file", "package_name", "min_sdk", "target_sdk", "version_code", "version_name", "size_bytes", "sha256"):
            if key in apk:
                lines.append(f"- {key}: `{apk[key]}`")
        lines.extend(["", "| Check | Result |", "| --- | --- |"])
        lines.extend(f"| {name} | {'PASS' if passed else 'FAIL'} |" for name, passed in apk["checks"].items())
        if "main_activity" in apk:
            activity = apk["main_activity"]
            lines.extend(["", f"Main activity: `{activity['name'] if activity else 'MISSING'}`"])
            if activity:
                lines.append("")
                lines.extend(f"- actions: `{', '.join(intent['actions'])}`; categories: `{', '.join(intent['categories'])}`"
                             for intent in activity["intent_filters"])
        lines.extend(["", "Native libraries: " + (", ".join(apk.get("native_libraries", [])) or "none"), ""])
        if "signing" in apk:
            lines.extend(["Signature schemes: `" + json.dumps(apk["signing"]["schemes"], sort_keys=True) + "`", ""])
            lines.extend(f"Certificate SHA-256: `{digest}`" for digest in apk["signing"]["certificate_sha256"])
            lines.append("")
        if "error" in apk:
            lines.extend([f"Error: {apk['error']}", ""])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sdk", type=Path, required=True, help="Android SDK root containing build-tools")
    parser.add_argument("--f55", type=Path, required=True, help="CAN F55 release APK")
    parser.add_argument("--standard", type=Path, required=True, help="Standard release APK")
    parser.add_argument("--output", type=Path, required=True, help="Report prefix; writes PREFIX.json and PREFIX.md")
    args = parser.parse_args()
    report = {"schema_version": 1, "passed": False, "runtime_tested": False,
              "signing_notice": SIGNING_NOTICE, "apks": []}
    try:
        version, commands = find_tools(args.sdk)
        report["build_tools_version"] = version
        report["apks"] = [verify_apk(args.f55, "canF55", commands), verify_apk(args.standard, "standard", commands)]
        report["passed"] = all(apk["passed"] for apk in report["apks"])
    except (VerificationError, OSError) as error:
        report["error"] = str(error) if isinstance(error, VerificationError) else "SDK build-tools directory could not be read."
    prefix = args.output.with_suffix("") if args.output.suffix in (".json", ".md") else args.output
    json_path, md_path = Path(str(prefix) + ".json"), Path(str(prefix) + ".md")
    try:
        prefix.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        md_path.write_text(markdown_report(report), encoding="utf-8")
    except OSError:
        print("FAIL: verification reports could not be written.", file=sys.stderr)
        return 2
    print(f"{'PASS' if report['passed'] else 'FAIL'}: APK verification; JSON and Markdown reports written.")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
