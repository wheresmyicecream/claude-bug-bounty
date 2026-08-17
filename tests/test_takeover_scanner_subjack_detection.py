"""Regression test for the subjack candidate-detection bug in takeover_scanner.sh.

This subjack version (haccer/subjack, output.go's printResult) never prints a
literal "[Vulnerable]" label -- a match is printed as "[SERVICE_NAME] host"
(e.g. "[GITHUB] host", "[DOMAIN AVAILABLE - x.com] host"), and a clean host
is "[Not Vulnerable] host". The scanner previously grepped for
'^\\[Vulnerable\\]', which matched neither format and silently reported
"clean" no matter what subjack actually found.
"""
import re
import subprocess
from pathlib import Path

SCANNER_PATH = Path(__file__).resolve().parents[1] / "tools" / "takeover_scanner.sh"


def test_scanner_no_longer_checks_for_literal_vulnerable_label():
    scanner = SCANNER_PATH.read_text()
    # The buggy pattern is referenced in an explanatory comment (documenting
    # what was wrong and why) but must not appear as an active, uncommented
    # shell invocation anymore.
    active_lines = [
        line for line in scanner.splitlines()
        if "grep -c '^\\[Vulnerable\\]'" in line and not line.strip().startswith("#")
    ]
    assert active_lines == []


def test_scanner_detects_candidates_by_excluding_not_vulnerable():
    scanner = SCANNER_PATH.read_text()
    assert "grep -vc '^\\[Not Vulnerable\\]'" in scanner


def test_detection_regex_matches_real_subjack_output_formats(tmp_path):
    sample = tmp_path / "subjack.txt"
    sample.write_text(
        "[Not Vulnerable] clean1.example.com\n"
        "[GITHUB] dangling.example.com\n"
        "[Not Vulnerable] clean2.example.com\n"
        "[DOMAIN AVAILABLE - old-app.herokuapp.com] another.example.com\n"
    )

    # Mirror the exact shell logic used in takeover_scanner.sh.
    result = subprocess.run(
        ["grep", "-vc", r"^\[Not Vulnerable\]", str(sample)],
        capture_output=True, text=True,
    )
    assert int(result.stdout.strip()) == 2


def test_detection_regex_reports_zero_when_all_clean(tmp_path):
    sample = tmp_path / "subjack.txt"
    sample.write_text(
        "[Not Vulnerable] clean1.example.com\n"
        "[Not Vulnerable] clean2.example.com\n"
    )

    result = subprocess.run(
        ["grep", "-vc", r"^\[Not Vulnerable\]", str(sample)],
        capture_output=True, text=True,
    )
    assert int(result.stdout.strip()) == 0
