#!/usr/bin/env python3
"""
Cross-check subjack takeover candidates against its own fingerprint database
by actually resolving each flagged host's CNAME and comparing it to the
expected third-party domain for that service.

Why this exists: subjack's live-host fingerprint match (identify() in
fingerprint.go) only checks whether the HTTP response body contains a
generic string (e.g. "page not found" for the "uptimerobot" fingerprint,
"404: This page could not be found." for "gemfury") -- it does NOT verify
the CNAME actually points to the claimed provider. Any host with an
ordinary custom 404 page can trip this. Observed in practice on both
Eternal and Xiaomi: every "[UPTIMEROBOT]"/"[GEMFURY]" hit so far resolved to
the target's OWN infrastructure (*.alb.xiaomi.com, mgslb.com, etc.), not
stats.uptimerobot.com / furyns.com.

This does NOT replace manual verification for a real report (still claim
the resource and prove it per the 7-Question Gate) -- it just separates
"CNAME actually matches the expected provider, worth investigating further"
from "CNAME points to the target's own infra, near-certainly a fingerprint
false positive" so you don't have to check dozens of hits by hand.

Usage:
    python3 tools/verify_takeover_candidates.py <subjack-output-file>
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

FINGERPRINTS_PATH = Path(__file__).resolve().parent / "data" / "subjack_fingerprints.json"

# Matches subjack output.go's printResult(): "[SERVICE_NAME] host" or
# "[DOMAIN AVAILABLE - x.com] host" / "[DEAD DOMAIN - x.com] host" /
# "[STALE A RECORD] host". "[Not Vulnerable] host" is excluded by the caller.
LINE_RE = re.compile(r"^\[(.+?)\]\s+(\S+)\s*$")


def load_fingerprints() -> dict[str, list[str]]:
    with open(FINGERPRINTS_PATH) as f:
        data = json.load(f)
    return {entry["service"].upper(): entry.get("cname", []) for entry in data}


def resolve_cname(host: str) -> str | None:
    """Return the CNAME target, "" if the host has a direct A record and no
    CNAME (can't be a dangling-CNAME takeover by definition), or None if
    resolution couldn't be determined at all (no dnspython/dig, or lookup
    failure)."""
    try:
        import dns.resolver  # type: ignore
        try:
            answers = dns.resolver.resolve(host, "CNAME")
            return str(answers[0].target).rstrip(".")
        except dns.resolver.NoAnswer:
            try:
                dns.resolver.resolve(host, "A")
                return ""
            except Exception:
                return None
        except Exception:
            return None
    except ImportError:
        pass

    if shutil.which("dig"):
        try:
            out = subprocess.run(
                ["dig", "+short", "CNAME", host], capture_output=True, text=True, timeout=10
            ).stdout.strip()
            if out:
                return out.rstrip(".")
            a_out = subprocess.run(
                ["dig", "+short", "A", host], capture_output=True, text=True, timeout=10
            ).stdout.strip()
            return "" if a_out else None
        except Exception:
            return None

    return None


def classify(label: str, host: str, fingerprints: dict[str, list[str]]) -> tuple[str, str]:
    if label.upper().startswith("DOMAIN AVAILABLE"):
        return "CONFIRM/CLAIM", f"subjack itself determined the CNAME target is available for registration: {label}"

    expected_cnames = fingerprints.get(label.upper())
    if expected_cnames is None:
        return "MANUAL REVIEW", f"'{label}' not found in fingerprint database (special label like STALE A RECORD/DEAD DOMAIN) -- check by hand"

    actual_cname = resolve_cname(host)
    if actual_cname is None:
        return "MANUAL REVIEW", "could not determine DNS records (no dnspython/dig available, or lookup failed) -- check by hand"
    if actual_cname == "":
        return "FALSE POSITIVE", "host has a direct A record, no CNAME at all -- cannot be a dangling-CNAME takeover by definition"

    if any(expected in actual_cname for expected in expected_cnames):
        return "LIKELY REAL", f"CNAME '{actual_cname}' matches expected provider domain(s) {expected_cnames} -- investigate further, still need to actually claim + prove per the 7-Question Gate"

    return "FALSE POSITIVE", f"CNAME '{actual_cname}' does NOT match expected provider domain(s) {expected_cnames} -- fingerprint false positive (generic body-text match)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("subjack_output", help="Path to a subjack .txt output file")
    args = parser.parse_args(argv)

    fingerprints = load_fingerprints()

    with open(args.subjack_output) as f:
        lines = [line.rstrip("\n") for line in f if line.strip()]

    candidates = [line for line in lines if not line.startswith("[Not Vulnerable]")]

    if not candidates:
        print("No candidates (every host was [Not Vulnerable]).")
        return 0

    exit_code = 0
    for line in candidates:
        m = LINE_RE.match(line)
        if not m:
            print(f"UNPARSEABLE: {line}")
            continue
        label, host = m.group(1), m.group(2)
        verdict, reason = classify(label, host, fingerprints)
        if verdict in ("LIKELY REAL", "CONFIRM/CLAIM"):
            exit_code = 1
        print(f"[{verdict}] {host} (label: {label})")
        print(f"    {reason}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
