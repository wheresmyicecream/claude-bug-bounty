"""Tests for tools/verify_takeover_candidates.py -- cross-checks subjack hits
against its own fingerprint DB by resolving the actual CNAME, so a generic
body-text false positive (subjack's identify() doesn't verify CNAME target)
doesn't have to be checked by hand every time.
"""
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import verify_takeover_candidates as vtc  # noqa: E402


def test_fingerprints_file_loads_and_has_expected_services():
    fingerprints = vtc.load_fingerprints()
    assert "GITHUB" in fingerprints
    assert "github.io" in fingerprints["GITHUB"]
    assert "UPTIMEROBOT" in fingerprints
    assert "stats.uptimerobot.com" in fingerprints["UPTIMEROBOT"]


def test_classify_false_positive_when_cname_does_not_match():
    fingerprints = {"UPTIMEROBOT": ["stats.uptimerobot.com"]}
    with patch.object(vtc, "resolve_cname", return_value="extranet.alb.xiaomi.com"):
        verdict, reason = vtc.classify("UPTIMEROBOT", "host.xiaomi.com", fingerprints)
    assert verdict == "FALSE POSITIVE"
    assert "does NOT match" in reason


def test_classify_likely_real_when_cname_matches():
    fingerprints = {"GITHUB": ["github.io"]}
    with patch.object(vtc, "resolve_cname", return_value="someuser.github.io"):
        verdict, reason = vtc.classify("GITHUB", "blog.example.com", fingerprints)
    assert verdict == "LIKELY REAL"


def test_classify_false_positive_when_no_cname_at_all():
    fingerprints = {"UPTIMEROBOT": ["stats.uptimerobot.com"]}
    with patch.object(vtc, "resolve_cname", return_value=""):
        verdict, reason = vtc.classify("UPTIMEROBOT", "direct-a-record.example.com", fingerprints)
    assert verdict == "FALSE POSITIVE"
    assert "direct A record" in reason


def test_classify_manual_review_when_resolution_unavailable():
    fingerprints = {"UPTIMEROBOT": ["stats.uptimerobot.com"]}
    with patch.object(vtc, "resolve_cname", return_value=None):
        verdict, reason = vtc.classify("UPTIMEROBOT", "host.example.com", fingerprints)
    assert verdict == "MANUAL REVIEW"


def test_classify_domain_available_always_flagged_for_confirmation():
    verdict, reason = vtc.classify(
        "DOMAIN AVAILABLE - old-app.herokuapp.com", "host.example.com", {}
    )
    assert verdict == "CONFIRM/CLAIM"


def test_cli_exits_zero_when_all_false_positive(tmp_path):
    sample = tmp_path / "subjack.txt"
    sample.write_text(
        "[Not Vulnerable] clean.example.com\n"
        "[UPTIMEROBOT] flagged.example.com\n"
    )
    with patch.object(vtc, "resolve_cname", return_value="internal.example.com"):
        exit_code = vtc.main([str(sample)])
    assert exit_code == 0


def test_cli_exits_nonzero_when_likely_real_candidate_found(tmp_path):
    sample = tmp_path / "subjack.txt"
    sample.write_text("[GITHUB] dangling.example.com\n")
    with patch.object(vtc, "resolve_cname", return_value="someuser.github.io"):
        exit_code = vtc.main([str(sample)])
    assert exit_code == 1
