"""Regression tests for the Phase 6.5 config-exposure check in recon_engine.sh.

Two real bugs found in practice while hunting on Eternal and Xiaomi:

1. Soft-404 false positive: some hosts (click.grofer.io, an API gateway at
   api-aicall.aiasst.xiaomi.com) return HTTP 200 with a JS/JSON/text
   content-type for EVERY path, including ones that don't exist. The old
   check only verified status+content-type on the guessed config paths
   themselves, so it flagged all of them as "exposed" on such hosts. Fixed
   by probing one random nonexistent path per host first and skipping the
   whole host if that canary also looks "exposed".

2. `log_vuln` is not a function recon_engine.sh defines or sources (it only
   exists in vuln_scanner.sh) -- calling it produced a silent
   "log_vuln: command not found" in the log on every real hit. Fixed by
   using `log_warn`, which recon_engine.sh does define.
"""
from pathlib import Path

RECON_ENGINE_PATH = Path(__file__).resolve().parents[1] / "tools" / "recon_engine.sh"


def test_config_exposure_check_has_canary_probe():
    script = RECON_ENGINE_PATH.read_text()
    assert "CANARY_PATH=" in script
    assert "CANARY_STATUS=" in script
    # The canary skip must happen before the real CONFIG_PATHS loop runs.
    canary_idx = script.index("CANARY_PATH=")
    config_loop_idx = script.index('for path in "${CONFIG_PATHS[@]}"')
    assert canary_idx < config_loop_idx


def test_config_exposure_check_no_longer_calls_undefined_log_vuln():
    script = RECON_ENGINE_PATH.read_text()
    # log_vuln is only ever defined in vuln_scanner.sh, which recon_engine.sh
    # does not source -- must not be called here.
    assert "log_vuln" not in script
    assert 'log_warn "Config exposed:' in script
