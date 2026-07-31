#!/usr/bin/env python3
"""
Sample down large templated-subdomain clusters before feeding a host list into
recon_engine.sh. Some domains provision thousands of near-identical hosts
under one zone (e.g. mi.com had ~18,700 hosts under *.shop.mi.com -- same
page title, same tech stack, clearly one templated storefront generator
replicated per-tenant). Exhaustively httpx-probing / nuclei-scanning /
takeover-checking all of them has near-zero marginal value over a sample, and
turns a "quick" recon into a multi-hour run per domain.

Clusters by the zone immediately above the root (root_labels + 1 labels from
the right), e.g. for root "mi.com" that's the "shop.mi.com" / "api.mi.com"
level -- and groups ALL descendants under that zone regardless of how many
extra labels precede it. This matters: mi.com had BOTH "web4275.shop.mi.com"
(root+2 labels) AND "www.click.shop.mi.com" (root+3 labels) in the same
templated zone -- a naive "strip exactly one label" grouping puts these in
different buckets (they land on different suffix lengths) and misses that
they're the same explosion. Clustering on the fixed "root+1" zone catches
both regardless of extra depth.

Direct children of the root themselves (exactly root_labels + 1 labels, e.g.
"api.mi.com" or "shop.mi.com" with nothing after) are always counted as part
of their own zone's cluster -- if that zone is oversized, they're included in
the same sampling as their descendants; if not, kept in full either way.

BLIND SPOT the above doesn't cover, found on hubspot's hs-sites.com: a
per-tenant hosting platform where each customer gets their OWN direct child
of the root (customer1.hs-sites.com, customer2.hs-sites.com, ... 42,809 of
them). Every one of these is trivially its own single-member "zone" by the
above logic (a direct child's zone IS itself), so none look individually
oversized and the per-zone threshold check never fires -- 42,809 hosts sailed
through down to 38,670. Zone-based clustering can only catch "many hosts
under one shared deeper suffix"; it structurally cannot catch "there are
simply too many distinct direct children". Covered by a final flat cap
(--max-total) applied after zone-based sampling: if the result is still
too large, deterministically sample down to that ceiling regardless of
structure.

Usage:
    python3 tools/sample_subdomain_clusters.py <root-domain> <input> <output> \
        [--threshold 200] [--sample-size 40] [--max-total 2000]
"""
from __future__ import annotations

import argparse
from collections import defaultdict


def zone_above_root(host: str, root_label_count: int) -> str | None:
    """Return the (root_label_count + 1)-label zone this host falls under,
    or None if the host has fewer labels than that (shouldn't happen for
    genuine subdomains of root, but be defensive)."""
    parts = host.split(".")
    zone_len = root_label_count + 1
    if len(parts) < zone_len:
        return None
    return ".".join(parts[-zone_len:])


def sample_clusters(
    hosts: list[str], root: str, threshold: int, sample_size: int, max_total: int | None = None
) -> tuple[list[str], list[str]]:
    root_label_count = len(root.split("."))
    clusters: dict[str, list[str]] = defaultdict(list)
    unclustered: list[str] = []

    for h in hosts:
        zone = zone_above_root(h, root_label_count)
        if zone is None:
            unclustered.append(h)
        else:
            clusters[zone].append(h)

    kept: list[str] = list(unclustered)
    report: list[str] = []
    for zone, members in clusters.items():
        if len(members) > threshold:
            sample = sorted(members)[:sample_size]
            kept.extend(sample)
            report.append(f"{zone}: {len(members)} hosts -> sampled {len(sample)}")
        else:
            kept.extend(members)

    kept = sorted(set(kept))

    # Flat fallback cap: catches explosions zone-based clustering can't (many
    # distinct direct children, e.g. hs-sites.com's per-tenant hosting).
    if max_total is not None and len(kept) > max_total:
        final = kept[:max_total]
        report.append(f"(flat cap) {len(kept)} hosts remained after zone sampling -> capped to {len(final)}")
        kept = final

    return kept, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", help="Bare root domain (e.g. mi.com)")
    parser.add_argument("input", help="Input file, one host per line")
    parser.add_argument("output", help="Output file for the (possibly sampled) host list")
    parser.add_argument("--threshold", type=int, default=200, help="Cluster size above which sampling kicks in (default: 200)")
    parser.add_argument("--sample-size", type=int, default=40, help="How many hosts to keep per oversized cluster (default: 40)")
    parser.add_argument("--max-total", type=int, default=2000, help="Hard ceiling applied after zone sampling, catches flat per-tenant explosions zone clustering can't (default: 2000; 0 disables)")
    args = parser.parse_args(argv)

    with open(args.input) as f:
        hosts = [line.strip() for line in f if line.strip()]

    max_total = args.max_total if args.max_total > 0 else None
    kept, report = sample_clusters(hosts, args.root, args.threshold, args.sample_size, max_total)

    with open(args.output, "w") as f:
        f.write("\n".join(kept) + ("\n" if kept else ""))

    print(f"{len(hosts)} hosts -> {len(kept)} hosts")
    for line in report:
        print(" -", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
