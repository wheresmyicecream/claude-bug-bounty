"""Tests for tools/sample_subdomain_clusters.py.

Covers two real bugs found in practice:
1. Zone-based clustering must catch a templated explosion regardless of how
   many extra labels precede the shared zone (mi.com's *.shop.mi.com had both
   web4275.shop.mi.com and www.click.shop.mi.com in the same explosion, at
   different label depths).
2. Zone-based clustering structurally cannot catch a FLAT explosion of many
   distinct direct children of the root (hs-sites.com: 42,809 hosts, each
   customer's own direct child -- none individually oversized as a "zone").
   The flat --max-total fallback cap exists specifically for this.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from sample_subdomain_clusters import sample_clusters, zone_above_root  # noqa: E402


def test_zone_above_root_direct_child():
    assert zone_above_root("api.mi.com", 2) == "api.mi.com"


def test_zone_above_root_deeper_host():
    assert zone_above_root("web4275.shop.mi.com", 2) == "shop.mi.com"
    assert zone_above_root("www.click.shop.mi.com", 2) == "shop.mi.com"


def test_catches_same_zone_at_different_depths():
    # The real mi.com bug: these must land in the SAME cluster despite
    # different total label counts.
    hosts = [f"web{i}.shop.mi.com" for i in range(150)] + [f"www.tag{i}.shop.mi.com" for i in range(150)]
    hosts.append("api.mi.com")  # untouched direct child
    kept, report = sample_clusters(hosts, "mi.com", threshold=200, sample_size=40)
    assert "api.mi.com" in kept
    shop_hosts = [h for h in kept if h.endswith("shop.mi.com")]
    assert len(shop_hosts) == 40
    assert any("shop.mi.com" in line for line in report)


def test_direct_children_kept_in_full_when_not_oversized():
    hosts = [f"service{i}.example.com" for i in range(50)]
    kept, report = sample_clusters(hosts, "example.com", threshold=200, sample_size=40)
    assert sorted(kept) == sorted(hosts)
    assert report == []


def test_flat_cap_catches_explosion_of_distinct_direct_children():
    # The real hs-sites.com bug: thousands of distinct direct children, each
    # its own singleton "zone" -- zone-based sampling alone does nothing.
    hosts = [f"tenant{i}.hs-sites.com" for i in range(5000)]
    kept, report = sample_clusters(hosts, "hs-sites.com", threshold=200, sample_size=40, max_total=2000)
    assert len(kept) == 2000
    assert any("flat cap" in line for line in report)


def test_flat_cap_disabled_when_none():
    hosts = [f"tenant{i}.hs-sites.com" for i in range(5000)]
    kept, report = sample_clusters(hosts, "hs-sites.com", threshold=200, sample_size=40, max_total=None)
    assert len(kept) == 5000


def test_flat_cap_not_applied_when_already_under_limit():
    hosts = [f"tenant{i}.hs-sites.com" for i in range(100)]
    kept, report = sample_clusters(hosts, "hs-sites.com", threshold=200, sample_size=40, max_total=2000)
    assert len(kept) == 100
    assert not any("flat cap" in line for line in report)
