#!/usr/bin/env python3
"""
Sample down large templated-subdomain clusters before feeding a host list into
recon_engine.sh. Some domains provision thousands of near-identical hosts
under one deeper suffix (e.g. mi.com had 17,603 hosts under *.shop.mi.com --
same page title, same tech stack, clearly one templated storefront generator
replicated per-tenant). Exhaustively httpx-probing / nuclei-scanning /
takeover-checking all of them has near-zero marginal value over a sample, and
turns a "quick" recon into a multi-hour run per domain.

Only clusters DEEPER than the bare root are sampled -- direct children of the
root (api.<root>, account.<root>, shop.<root> itself, etc.) are the genuinely
diverse, important surface and are always kept in full, no matter how many
there are.

Usage:
    python3 tools/sample_subdomain_clusters.py <root-domain> <input> <output> \
        [--threshold 200] [--sample-size 40]
"""
from __future__ import annotations

import argparse
from collections import defaultdict


def suffix_after_first_label(host: str) -> str:
    parts = host.split(".")
    return ".".join(parts[1:]) if len(parts) > 1 else host


def sample_clusters(hosts: list[str], root: str, threshold: int, sample_size: int) -> tuple[list[str], list[str]]:
    clusters: dict[str, list[str]] = defaultdict(list)
    for h in hosts:
        clusters[suffix_after_first_label(h)].append(h)

    kept: list[str] = []
    report: list[str] = []
    for suffix, members in clusters.items():
        if suffix != root and len(members) > threshold:
            sample = sorted(members)[:sample_size]
            kept.extend(sample)
            report.append(f"{suffix}: {len(members)} hosts -> sampled {len(sample)}")
        else:
            kept.extend(members)
    return sorted(set(kept)), report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", help="Bare root domain (e.g. mi.com) -- its direct children are never sampled")
    parser.add_argument("input", help="Input file, one host per line")
    parser.add_argument("output", help="Output file for the (possibly sampled) host list")
    parser.add_argument("--threshold", type=int, default=200, help="Cluster size above which sampling kicks in (default: 200)")
    parser.add_argument("--sample-size", type=int, default=40, help="How many hosts to keep per oversized cluster (default: 40)")
    args = parser.parse_args(argv)

    with open(args.input) as f:
        hosts = [line.strip() for line in f if line.strip()]

    kept, report = sample_clusters(hosts, args.root, args.threshold, args.sample_size)

    with open(args.output, "w") as f:
        f.write("\n".join(kept) + ("\n" if kept else ""))

    print(f"{len(hosts)} hosts -> {len(kept)} hosts")
    for line in report:
        print(" -", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
