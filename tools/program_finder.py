#!/usr/bin/env python3
"""
Program Finder — rank open, bounty-paying HackerOne programs by attack
surface size and responsiveness, for mobile/CLI-only hunting (no auth
testing, no manual browser work, no bot-detection bypass).

Pulls the public bounty-targets-data mirror (arkadiyt/bounty-targets-data,
refreshed every few hours from HackerOne's own directory) and ranks
programs by:
  - offers_bounties == True and submission_state == "open" (hard filters)
  - number of WILDCARD-type in-scope assets (proxy for "broad surface,
    good for subdomain takeover / recon-driven hunting")
  - average_time_to_first_program_response, ascending (NOT
    average_time_to_report_resolved -- that one has long-tail outliers
    that don't reflect whether a program is actively triaging)

Usage:
    python3 tools/program_finder.py                          # top 20, defaults
    python3 tools/program_finder.py --min-wildcards 10 --max-response-days 5
    python3 tools/program_finder.py --top 10 --json
    python3 tools/program_finder.py --refresh                # force re-download
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

DATA_URL = "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/hackerone_data.json"
CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".private", "bounty-targets-data", "hackerone_data.json")


def _load_data(refresh: bool) -> list[dict]:
    if refresh or not os.path.exists(CACHE_PATH):
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        req = urllib.request.Request(DATA_URL, headers={"User-Agent": "bughunter-program-finder"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
        with open(CACHE_PATH, "wb") as f:
            f.write(raw)
    with open(CACHE_PATH, "rb") as f:
        return json.load(f)


def _wildcard_count(program: dict) -> int:
    targets = (program.get("targets") or {}).get("in_scope") or []
    return sum(1 for t in targets if t.get("asset_type") == "WILDCARD")


def _asset_type_breakdown(program: dict) -> dict[str, int]:
    targets = (program.get("targets") or {}).get("in_scope") or []
    counts: dict[str, int] = {}
    for t in targets:
        at = t.get("asset_type", "UNKNOWN")
        counts[at] = counts.get(at, 0) + 1
    return counts


def rank_programs(
    data: list[dict],
    min_wildcards: int,
    max_response_days: float | None,
    require_response_known: bool,
) -> list[dict]:
    candidates = []
    for p in data:
        if not p.get("offers_bounties"):
            continue
        if p.get("submission_state") != "open":
            continue
        wc = _wildcard_count(p)
        if wc < min_wildcards:
            continue
        resp = p.get("average_time_to_first_program_response")
        if require_response_known and resp is None:
            continue
        if max_response_days is not None and resp is not None and resp > max_response_days:
            continue
        candidates.append({
            "handle": p["handle"],
            "name": p.get("name", p["handle"]),
            "url": p.get("url", f"https://hackerone.com/{p['handle']}"),
            "wildcard_count": wc,
            "asset_types": _asset_type_breakdown(p),
            "avg_first_response_days": resp,
            "avg_resolved_days": p.get("average_time_to_report_resolved"),
        })
    candidates.sort(key=lambda c: (-c["wildcard_count"], c["avg_first_response_days"] if c["avg_first_response_days"] is not None else 9999))
    return candidates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--min-wildcards", type=int, default=5, help="Minimum WILDCARD-type in-scope assets (default: 5)")
    parser.add_argument("--max-response-days", type=float, default=None, help="Max average first-response time in days")
    parser.add_argument("--require-response-known", action="store_true", help="Drop programs with no published response-time stat")
    parser.add_argument("--top", type=int, default=20, help="How many to show (default: 20)")
    parser.add_argument("--refresh", action="store_true", help="Force re-download of the dataset (cached under .private/ otherwise)")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of a table")
    args = parser.parse_args(argv)

    data = _load_data(args.refresh)
    ranked = rank_programs(data, args.min_wildcards, args.max_response_days, args.require_response_known)
    top = ranked[: args.top]

    if args.json:
        print(json.dumps(top, indent=2))
        return 0

    print(f"{len(ranked)} programs match filters (of {len(data)} total) -- showing top {len(top)}\n")
    print(f"{'handle':<28} {'wildcards':>9} {'resp(days)':>10}  name")
    print("-" * 80)
    for c in top:
        resp = f"{c['avg_first_response_days']:.0f}" if c["avg_first_response_days"] is not None else "?"
        print(f"{c['handle']:<28} {c['wildcard_count']:>9} {resp:>10}  {c['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
