#!/usr/bin/env python3
"""Build a deduplicated AltStore source from Moe's upstream JSON."""
import argparse
import copy
import datetime as dt
import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

UPSTREAM = "https://raw.githubusercontent.com/MountainofPenguin/moe-altstore/main/apps.json"

def version_key(value):
    parts = [int(n) for n in re.findall(r"\d+", str(value).split(" (")[0])]
    return tuple((parts + [0] * 8)[:8])

def valid_url(value):
    if not isinstance(value, str):
        return False
    p = urlparse(value)
    return p.scheme == "https" and bool(p.hostname) and not p.username and not p.password

def validate_app(app):
    if not isinstance(app, dict):
        raise ValueError("App must be an object")
    for key in ("name", "bundleIdentifier", "developerName", "iconURL", "localizedDescription", "versions"):
        if key not in app:
            raise ValueError(f"Missing {key}: {app.get('name', '?')}")
    if not isinstance(app["bundleIdentifier"], str) or not app["bundleIdentifier"].strip():
        raise ValueError("Invalid bundleIdentifier")
    if not valid_url(app["iconURL"]):
        raise ValueError("Invalid icon URL")
    versions = app["versions"]
    if not isinstance(versions, list) or not versions:
        raise ValueError("Missing versions")
    for v in versions:
        for key in ("version", "date", "downloadURL", "size"):
            if key not in v:
                raise ValueError(f"Missing version field {key}")
        dt.date.fromisoformat(v["date"])
        if not valid_url(v["downloadURL"]) or type(v["size"]) is not int or v["size"] <= 0:
            raise ValueError("Invalid download URL or size")

def rank(app):
    return max((version_key(v["version"]), v["date"], v["downloadURL"]) for v in app["versions"])

def transform(source, config):
    if not isinstance(source, dict) or source.get("apiVersion") != "v2" or not isinstance(source.get("apps"), list) or not source["apps"]:
        raise ValueError("Unsupported or empty AltStore source")
    chosen, removed = {}, []
    preferred = config.get("preferred_names", {})
    for app in source["apps"]:
        validate_app(app)
        bid = app["bundleIdentifier"]
        if bid not in chosen:
            chosen[bid] = app
            continue
        old = chosen[bid]
        pref = preferred.get(bid)
        if pref and (old["name"] == pref or app["name"] == pref):
            winner = old if old["name"] == pref else app
        else:
            winner = max((old, app), key=lambda a: (rank(a), a["name"]))
        loser = app if winner is old else old
        chosen[bid] = winner
        removed.append({"bundleIdentifier": bid, "kept": winner["name"], "removed": loser["name"]})
    output = copy.deepcopy(source)
    output["apps"] = list(chosen.values())
    if len(output["apps"]) != len({a["bundleIdentifier"] for a in output["apps"]}):
        raise ValueError("Deduplication failed")
    return output, removed

def download(url):
    if not valid_url(url):
        raise ValueError("HTTPS required")
    request = urllib.request.Request(url, headers={"User-Agent": "altstore-source-fix/1.0"})
    with urllib.request.urlopen(request, timeout=25) as response:
        if not valid_url(response.geturl()):
            raise ValueError("Unsafe redirect")
        payload = response.read(8_000_001)
        if len(payload) > 8_000_000:
            raise ValueError("Upstream JSON exceeds 8 MB")
        return json.loads(payload)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", default=UPSTREAM)
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--output", default="apps.json")
    parser.add_argument("--report", default="dedup-report.json")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    source = download(args.upstream)
    output, removed = transform(source, config)
    target = Path(args.output)
    if target.exists():
        previous = json.loads(target.read_text(encoding="utf-8"))
        minimum = config.get("min_retained_ratio", 0.6)
        if len(output["apps"]) < len(previous.get("apps", [])) * minimum:
            raise ValueError("Unexpected large reduction in app count")
    serialized = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    report = json.dumps({"input": len(source["apps"]), "output": len(output["apps"]), "removed": removed}, ensure_ascii=False, indent=2) + "\n"
    target.write_text(serialized, encoding="utf-8")
    Path(args.report).write_text(report, encoding="utf-8")
    print(f"Validated {len(source['apps'])} apps; published {len(output['apps'])}; removed {len(removed)} duplicates")

if __name__ == "__main__":
    main()
