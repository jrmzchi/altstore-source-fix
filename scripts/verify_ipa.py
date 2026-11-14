#!/usr/bin/env python3
"""Verify Infuse IPA metadata and correct source version using Info.plist.

Downloads only the latest Infuse IPA, never modifies the IPA itself.
"""
import argparse
import json
import plistlib
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlparse

TARGET_BUNDLE_ID = "com.firecore.infuse"

def inspect_ipa(url, path):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ("github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"):
        raise ValueError("Untrusted IPA download host")
    request = urllib.request.Request(url, headers={"User-Agent": "altstore-source-fix/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, path.open("wb") as f:
        import shutil
        shutil.copyfileobj(response, f)
    with zipfile.ZipFile(path) as archive:
        candidates = [n for n in archive.namelist() if n.startswith("Payload/") and n.count("/") == 2 and n.endswith(".app/Info.plist")]
        if len(candidates) != 1:
            raise ValueError(f"Expected one app Info.plist, found {len(candidates)}")
        info = plistlib.loads(archive.read(candidates[0]))
    return {k: info.get(k) for k in ("CFBundleIdentifier", "CFBundleShortVersionString", "CFBundleVersion")}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="apps.json")
    parser.add_argument("--report", default="ipa-verification.json")
    args = parser.parse_args()
    source_path = Path(args.source)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    apps = [a for a in source["apps"] if a["bundleIdentifier"] == TARGET_BUNDLE_ID]
    if len(apps) != 1:
        raise ValueError("Expected exactly one Infuse entry")
    app = apps[0]
    if not app.get("versions"):
        raise ValueError("Infuse has no versions")
    latest = app["versions"][0]
    ipa_path = Path("/tmp/altstore-infuse-verification.ipa")
    try:
        info = inspect_ipa(latest["downloadURL"], ipa_path)
    finally:
        ipa_path.unlink(missing_ok=True)
    if info["CFBundleIdentifier"] != TARGET_BUNDLE_ID:
        raise ValueError("IPA Bundle ID does not match source")
    version = info["CFBundleShortVersionString"]
    build = info["CFBundleVersion"]
    if not isinstance(version, str) or not version.strip() or not isinstance(build, str) or not build.strip():
        raise ValueError("IPA version/build metadata missing")
    original = latest["version"]
    latest["version"] = version
    latest["buildVersion"] = build
    report = {"app": app["name"], "bundleIdentifier": TARGET_BUNDLE_ID,
              "sourceVersion": original, "ipaVersion": version, "ipaBuildVersion": build,
              "corrected": original != version}
    source_path.write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))

if __name__ == "__main__":
    main()
