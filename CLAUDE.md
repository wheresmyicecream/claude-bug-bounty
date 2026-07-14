# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

**BugHunter** (`claude-bug-bounty`) is a professional bug bounty hunting toolkit distributed two ways from one codebase:

1. **Claude Code plugin** — skills, slash commands, agents, and rules that get loaded into `~/.claude/` (or another agent harness) via `install.sh` and drive hunts interactively inside Claude Code / OpenCode / Pi / Codex.
2. **Standalone CLI (`bughunter`)** — `engine.py` runs the same recon→hunt→validate→report pipeline without any Claude subscription, using `brain.py` as a multi-provider LLM layer (Ollama, Groq, DeepSeek, Claude, OpenAI, Gemini, Kimi, Mistral, Together, Cerebras, Perplexity) and `agent.py` as an optional LangGraph-style ReAct autonomous agent.

Both modes call into the same `tools/` scanner pipeline and the same `memory/` persistence layer — the plugin surface (skills/commands/agents) is just a thin routing layer over those.

This is dual-use offensive-security tooling scoped to **authorized bug bounty programs only** (HackerOne, Bugcrowd, Intigriti, Immunefi, safe-harbor equivalents) — see "Authorized-use context" below before making changes that affect scope-checking or safety gates.

## Development Commands

```bash
pytest tests/                                    # full test suite
pytest tests/test_scope_checker.py               # one test file
pytest tests/test_scope_checker.py::TestOutOfScope::test_name -v   # one test
bash tests/test_cicd_scanner.sh                  # shell-based test (not pytest — runs standalone)
```

- No linter/formatter is configured (no `pyproject.toml`, `.flake8`, or CI workflow in `.github/`). Match existing style.
- `pytest.ini` sets `testpaths = tests` and `python_files = test_*.py`. `tests/conftest.py` adds both the repo root and `tools/` to `sys.path`, so tests import as either `tools.foo` or `foo`.
- Install Python deps: `pip install -r requirements.txt` (just `requests` + `pytest`; provider SDKs like LangGraph/Ollama clients are optional and probed at runtime).
- Install the plugin locally: `chmod +x install.sh && ./install.sh` (targets: `claude` (default), `opencode`, `pi`, `codex`, `agents`, `standalone`, `all`; add `--project` for a repo-local install instead of global).
- Install external scanning binaries (subfinder, httpx, nuclei, katana, ffuf, dnsx, nmap, dalfox, etc.): `./install_tools.sh`.
- Run the local vulnerable demo target for manual testing: `python3 serve.py` (serves `demo/`).

## Architecture

**Capability-gated tools.** Every script in `tools/` sources `tools/external_arsenal.sh` and checks `_have <tool>` before using an external binary — missing tools are skipped, not treated as errors. When adding a new tool wrapper, follow this pattern rather than hard-failing on a missing dependency.

**Hunt memory (`memory/`)** is the cross-session, cross-target state shared by nearly everything: `pattern_db.py` learns patterns across targets, `audit_log.py` provides a request audit log/rate limiter/circuit breaker, `rotation.py` auto-rotates JSONL files at a 10MB cap (keeps 3 backups) on every append, and `schemas.py` validates every record written. Data lives as JSONL under a hunt-memory directory (see `tests/conftest.py` fixtures for the on-disk shape). `tools/lead_board.py` sits on top of this memory to track one ledger entry per recon-discovered lead per target (`memory/leads/<target>.jsonl`), routing each to the right `hunt-*` skill and tracking investigated/killed/reported status — this is the mechanism that prevents findings from being silently dropped (see Critical Rule 6 below).

**Scope safety is deterministic, not LLM-judged.** `tools/scope_checker.py` is a plain Python scope matcher (wildcard/exact/excluded-domain matching) that gates every hunt — it is not an AI call, precisely so scope enforcement can't be talked out of itself.

**Standalone-mode layering:** `engine.py` (CLI entrypoint, arg parsing, phase dispatch) → `brain.py` (`Brain` class: picks an LLM provider by env var or auto-detect, exposes `--phase recon|scan|chains|report|js|triage|next|full|plan|autopilot|exploit`) → `agent.py` (optional; only engaged via `--agent`/LangGraph flags for a full ReAct loop with working-memory compression every 5 steps and crash-resumable JSON sessions) → `tools/*` (actual scanning). Plugin-mode skills/commands ultimately shell out to the same `tools/*` scripts.

**Multi-harness install.** `install.sh --agent <target>` copies/symlinks `skills/`, `commands/`, `agents/` into the right location per harness (`~/.claude/`, `~/.config/opencode/`, `~/.pi/agent/`, `~/.codex/`, `~/.agents/skills`, or installs the standalone `bughunter` binary). `CLAUDE.md` is the Claude Code manifest; `AGENTS.md` is the equivalent for the other harnesses — keep the skill/command/agent counts and tables in sync between the two when either changes.

### Skills (13 domains — load with `/bug-bounty`, `/web2-recon`, `/token-scan`, etc.)

| Skill | Domain |
|---|---|
| `skills/bug-bounty/` | Master workflow — recon to report, all vuln classes, LLM testing, chains |
| `skills/bb-methodology/` | **Hunting mindset + 5-phase non-linear workflow + tool routing + session discipline** |
| `skills/web2-recon/` | Subdomain enum, live host discovery, URL crawling, nuclei |
| `skills/web2-vuln-classes/` | 21 bug classes with bypass tables (SSRF, open redirect, file upload, Agentic AI) |
| `skills/security-arsenal/` | Payloads, bypass tables, gf patterns, always-rejected list |
| `skills/web3-audit/` | 10 smart contract bug classes, Foundry PoC template, pre-dive kill signals |
| `skills/meme-coin-audit/` | Meme coin rug pull detection, token authority checks, bonding curve exploits, LP attacks |
| `skills/report-writing/` | H1/Bugcrowd/Intigriti/Immunefi report templates, CVSS 3.1, human tone |
| `skills/triage-validation/` | 7-Question Gate, 4 gates, never-submit list, conditionally valid table |
| `skills/credential-attack/` | Password spray methodology — when/why, 4-stage pipeline, mode selection, lockout tactics, legal guardrails |
| `skills/mobile-pentest/` | Android/iOS app pentest — runtime-first proxy workflow, APK/IPA decompile, deeplink/exported-activity injection, WebView bridge, SSL pinning bypass |
| `skills/cicd-security/` | CI/CD pipeline hunting — GitHub Actions injection, secret exfil, self-hosted runner poisoning, OIDC abuse, supply chain attacks |
| `skills/graphql-audit/` | GraphQL hunting — introspection, field suggestions, batching DoS, IDOR via aliasing, injection, auth bypass, depth bombs |

### Commands (27 slash commands, in `commands/`)

> All commands are prefixed to avoid conflicts with Claude Code's built-ins. `/resume` is reserved by Claude Code — use `/pickup` to continue a previous hunt.

Core workflow: `/recon`, `/hunt`, `/validate`, `/report`, `/chain`, `/triage`, `/pickup`, `/remember`, `/autopilot`, `/surface`.
Scope: `/scope`, `/scope-aggregate`.
Recon/enum add-ons: `/intel`, `/secrets-hunt`, `/takeover`, `/cloud-recon`, `/param-discover`, `/bypass-403`, `/scan-cves`, `/graphql-audit`, `/arsenal`.
Web3: `/web3-audit`, `/token-scan`.
Credential attack (all require `--with-credential-attack`): `/wordlist-gen`, `/osint-employees`, `/breach-check`, `/spray`.
Utility: `/memory-gc`.

See `commands/README.md` for full per-command usage.

### Agents (9 specialized agents, in `agents/`)

- `recon-agent` — subdomain enum + live host discovery
- `report-writer` — generates H1/Bugcrowd/Immunefi reports
- `validator` — 4-gate checklist on a finding
- `web3-auditor` — smart contract bug class analysis
- `chain-builder` — builds A→B→C exploit chains
- `autopilot` — autonomous hunt loop (scope→recon→rank→hunt→validate→report)
- `recon-ranker` — attack surface ranking from recon output + memory
- `token-auditor` — fast meme coin/token rug pull and security analysis
- `credential-hunter` — orchestrates wordlist-gen + osint-employees + breach-check; hard-stops at spray for human go/no-go

### Rules (always active, in `rules/`)

- `rules/hunting.md` — 17 critical hunting rules, incl. the engagement-context rule (see below)
- `rules/reporting.md` — report quality rules

### Tools (`tools/`, ~35 Python/shell scanners)

Master orchestrator is `tools/hunt.py`; `tools/external_arsenal.sh` is the installed-tool registry other scripts source for `_have <tool>`. See `tools/README.md` for the full table (recon/discovery, web3, intelligence, memory/session groups).

### MCP integrations (`mcp/`)

- `mcp/burp-mcp-client/` — Burp Suite proxy integration
- `mcp/hackerone-mcp/` — HackerOne public API (Hacktivity, program stats, policy)

## Authorized-use context

Per `TERMS.md` and `rules/hunting.md` Rule 0: this tooling is meant to be operated by an authorized bug bounty hunter against public programs with published safe-harbor terms, only after scope has been confirmed (`/scope` / `tools/scope_checker.py`). Do not weaken or bypass scope-checking, add features aimed at out-of-scope/unauthorized targets, or remove the legal guardrails in `skills/credential-attack/` and `tools/spray_orchestrator.sh` (typed-hostname confirm, lockout warning, audit log, hard stop before live spraying).

## Critical Rules (Always Active)

1. READ FULL SCOPE before touching any asset
2. NEVER hunt theoretical bugs — "Can attacker do this RIGHT NOW?"
3. Run 7-Question Gate BEFORE writing any report
4. KILL weak findings fast — N/A hurts your validity ratio
5. 5-minute rule — nothing after 5 min = move on
6. **LEAD BOARD — never lose a lead.** After recon, run `lead_board.py ingest <target>` + `show`, and route each finding to its `hunt-*` skill in plain language ("GraphQL endpoint → hunt-graphql"). When starting/killing/reporting a lead, `touch` its status. The hunter focuses on one lead at a time; the board remembers the rest so none is forgotten. Surface stale high-priority leads unprompted.
