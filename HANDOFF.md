# BugHunter — Session Handoff & Persistent-Machine Deploy Guide

Everything learned, installed, fixed, and every repo — plus how to run this on a
persistent machine (VPS or your own PC) where long scans don't die. Written to
hand off to a fresh Claude Code (or standalone) session.

> **Why this exists:** the cloud session this was built in is *ephemeral* — the
> container is reclaimed after inactivity, which **kills any background job**
> (subfinder/subjack/recon died ~5 times this way) and blocks long scans. Disk
> persists, processes don't. The fix is to run on a machine that stays up.

---

## 0. Ready-to-paste prompt for a NEW session

Paste this into a fresh Claude Code session on the persistent machine:

```
You are continuing a bug bounty hunting operation using the BugHunter toolkit
in this repo (see CLAUDE.md). Read HANDOFF.md first — it has the full history,
the methodology that works, the false-positive traps, and per-program status.

Operating rules (fixed):
- Authorized HackerOne programs only; confirm scope via memory/scope/<prog>.json
  and tools/scope_checker.py before touching anything.
- The USER does all HackerOne login and report submission manually. Never use
  their credentials; never create accounts. (On a persistent machine WITH a
  dedicated test device, authenticated testing via a user-provided session token
  is allowed — see HANDOFF §6.)
- No bot-detection/CAPTCHA bypass. No DoS. Respect each program's required
  identification header (see per-program notes).
- Kill weak findings fast. Before ANY report: run the blind-validator gate
  (spawn a context-free agent as a skeptical H1 triager) — see §5.
- This machine is persistent: long background scans are fine here. Still, make
  them resumable (offset files) as good practice.

Start by: (1) refreshing tools/program_finder.py data, (2) picking the next
un-hunted program with the best odds, (3) running the recon+takeover pipeline.
```

---

## 1. Deploy on a persistent machine

### 1a. Get the code
```bash
git clone https://github.com/wheresmyicecream/claude-bug-bounty.git
cd claude-bug-bounty
git checkout claude/eternal-recon-takeover-scan-rdvsae   # this session's branch
pip install -r requirements.txt        # requests + pytest (+ dnspython, see below)
pip install dnspython                   # needed by the takeover CNAME sweep + private-IP sweep
```

### 1b. Install the external scanners
```bash
./install_tools.sh          # repo's installer (subfinder/httpx/nuclei/katana/ffuf/dnsx/nmap/dalfox...)
# Go tools land in ~/go/bin ; make sure PATH includes them + cargo + pipx:
export PATH="$HOME/go/bin:$HOME/.cargo/bin:$HOME/.local/bin:/usr/local/bin:$PATH"
```
Confirmed-present this session: `subfinder httpx nuclei subjack ffuf cloud_enum gitleaks x8`.
Missing (install if needed): `katana dnsx dalfox arjun`.

**Gotchas found this session (already fixed in the repo, but reinstall notes):**
- `cloud_enum` on PyPI is a **name-squat placeholder** — install from source:
  `pip install git+https://github.com/initstring/cloud_enum` and it needs a
  mutations file; we use `/tmp/cloud_enum_data/fuzz.txt` (grab `enum_tools/fuzz.txt`
  from the cloud_enum repo).
- `subjack` prints `[SERVICE] host` for a hit / `[Not Vulnerable] host` otherwise
  (NOT a literal `[Vulnerable]`). Count hits with `grep -vc '^\[Not Vulnerable\]'`.
- `apkeep` (APK downloader, EFForg) — prebuilt binary:
  `curl -sSL https://github.com/EFForg/apkeep/releases/latest/download/apkeep-x86_64-unknown-linux-gnu -o apkeep && chmod +x apkeep`.
  Google-Play source needs a Google account; **huawei-app-gallery** source worked
  with no login (got Banco Plata's APK). Wolt/Playtika apps were NOT on huawei/apk-pure.

### 1c. Run it
- Interactive (plugin mode, this repo's skills/commands drive it inside Claude Code).
- **Standalone CLI** (no Claude subscription): `python3 engine.py --phase full --target <domain>`
  via `brain.py` (multi-provider LLM). See CLAUDE.md "Standalone-mode layering".
- Long scans: just run them — on a persistent box they finish. Nohup + a log is enough.

---

## 2. What I built / fixed this session (all committed to the branch)

### New tools
| File | What |
|---|---|
| `tools/program_finder.py` | Ranks H1 programs from the public `bounty-targets-data` mirror by wildcard count + response time. Flags: `--min-wildcards --max-response-days --require-response-known --top --refresh --json`. |
| `tools/sample_subdomain_clusters.py` | Caps templated-subdomain explosions (mi.com `*.shop.*`, hs-sites.com 42k tenants). Zone-above-root clustering + flat `--max-total` fallback. Has regression tests. |
| `tools/verify_takeover_candidates.py` | CNAME-verifies subjack hits against `tools/data/subjack_fingerprints.json`. Classifies FALSE POSITIVE / LIKELY REAL / CONFIRM-CLAIM. Every subjack hit ran through this — **all were false positives all session**. |
| `tools/data/subjack_fingerprints.json` | Bundled subjack fingerprint DB. |

### Fixes (each was a real, silent bug)
- `tools/takeover_scanner.sh` — detection matched a subjack output format that never exists; the whole session's "clean" was unvalidated until fixed. Now auto-runs the CNAME verifier.
- `tools/recon_engine.sh` — config-exposure check now has a **canary probe** (soft-404 catch-all hosts returned 200+JSON for any path → false positives on click.grofer.io, api-aicall.aiasst.xiaomi.com). Also fixed undefined `log_vuln`.
- `tools/cloud_recon.sh` — passed a nonexistent `cloud_enum` flag, silently failing every scan.
- `tools/external_arsenal.sh` — PATH didn't include cargo/pipx dirs → ~20 tools looked "not installed".
- `mcp/hackerone-mcp/server.py` — `get_program_stats()` queried GraphQL fields that don't exist; fixed via schema introspection (real fields: `currency`, `first_response_time`, `response_efficiency_percentage`, `submission_state`, bounty table values). Verified against H1's UI.

### Skills added
- **71 skills vendored from `elementalsouls/Claude-BugHunter`** (MIT) — all 57 `hunt-*` per-bug-class + 14 enterprise/OSINT/reporting. Fills `lead_board.py`'s routing table (it routed to 34 `hunt-*` skills that didn't exist). Provenance in `skills/THIRD_PARTY_NOTICES.md`.
- **`find-skills`** (vercel-labs/skills) + **~102 `yaklang/hack-skills`** reference skills (all pure markdown, reviewed safe). Installed via `npx skills add`. `skills-lock.json` tracks them.
- Skill count now **85** in `skills/` (+ the .agents/.claude symlinked ones).

### Reusable scanning helpers (in scratchpad — recreate on new machine)
- **Fast CNAME takeover sweep** (much better than subjack for breadth): resolve CNAME
  for each host, flag those pointing to takeover-able providers (S3/CloudFront/Heroku/
  GitHub Pages/Azure/Netlify/Shopify/Zendesk/etc.) whose target is NXDOMAIN = dangling.
  Processes ~2500 hosts / <2min, resumable via an offset file. **This is the takeover
  method to use going forward** — subjack is too slow for breadth.
- **Private-IP DNS sweep** — flags hosts whose public A-record is RFC1918 (internal
  topology disclosure). Verify any hit against 8.8.8.8 AND 1.1.1.1 (rule out sandbox
  DNS). Exclude 127.0.0.1 / 192.0.2.x (placeholders, not real leaks).
- **nmap shim** — `/tmp/no_nmap_shim/nmap` (a no-op) prepended to PATH; nmap `-sV
  --top-ports 1000` across thousands of hosts took >1h and huge traffic. On a
  persistent box you can re-enable nmap if you want it.

---

## 3. Persistence model (important)
- `memory/` is **tracked in git** (survives everything): `memory/scope/<prog>.json`
  (scope + policy notes), `memory/leads/<prog>.jsonl` (lead board — one entry per
  finding, status new/investigating/killed/reported), `memory/report_templates/`.
- `.private/<prog>/` is **gitignored** (scope_check.sh wrappers, recon logs, raw
  sensitive evidence). Sensitive raw data (e.g. Anduril's internal hostnames) is
  kept here and handed to you directly, never committed.
- `findings/` and `recon/` are **gitignored + ephemeral** (scan output).
- Lead board: `python3 tools/lead_board.py ingest <prog> --recon-dir recon/<...>`
  then `show` / `touch <prog> <id> --status <s> --note "..."`.

---

## 4. Per-program status (this session)

| Program | Result | Scope notes |
|---|---|---|
| Eternal (Zomato/Blinkit/Hyperpure) | 0 reportable | Blinkit OUT of scope. business-blog.zomato.com undocumented exclusion. Open GCS bucket `storage.googleapis.com/zomato` (billing-closed, no data retrievable). |
| Xiaomi | paused / **user said skip** | 43 wildcards, huge `*.shop.mi.com` explosion. Soft-404 catch-alls + WAF-returns-200 traps. |
| Anduril | **1 report SUBMITTED → Duplicate** | Internal DNS disclosure (640 hosts→RFC1918). Big Okta estate mapped (`okta.anduril.com`, `workspaces-*`). Program wants `X-HackerOne-Research: whereismyicecream` header. |
| Grindr | 0 | Takeover OUT of scope. |
| HubSpot | 0 | Auth-flow bugs need account (out of our scope). 7 CMS wildcards, huge tenant sprawl. |
| Banco Plata | 0 | **PRIVATE program** — kept in .private/ only. APK pulled via huawei (v2.7.1), static analysis clean. |
| Unico IDtech | 0 | Google Maps key exposed but properly API-restricted. Liveness scope needs physical device. |
| Deribit | 0 | **Only test.deribit.com allowed** for active testing (banned otherwise). kubernetes-dashboard→private IP (low). |
| Wolt | 0 | courier-api unauth-invited but 404/gated. ops.wolt.com SPA-gated. env.js = client-safe tokens. 5 private-IP hosts. |
| Superbet | 0 | Takeover = **$500 flat** (S3 excluded). Header `User-Agent: hackerone`. 13 gambling-brand wildcards, all clean. |
| Playtika | 0 | 147 hosts→RFC1918 (verified, but Low/Informative per blind validator). Header `X-Bug-Bounty: True`. Jenkins/Redash/admin all gated. |
| K Health | 0 | Takeover + staging-exposure both OUT of scope. Header must contain `(h1)`. Health data — endpoint-existence only. |
| Takeover breadth batch 1 (14 progs, 66k hosts) | 0 dangling | 8x8, flutteruki, elastic, amazonvrp, logitech, mercadolibre, spotify, grab, netflix, etc. |
| Anthropic (source review) | 0 (in progress) | Public program, avg **$750-1400**. **AI-written reports = auto-N/A** — user must author + provide working PoC. Reviewed plugins/hooks/skills: hookify engine safe, `safe_extract` correct, no clean bug yet. `github.com/anthropics` [Non-Core]. |

**Net: 1 submitted (dup), 0 paid.** Unauthenticated recon on these mature programs is
well-defended. The realistic unlock is authenticated testing (needs a dedicated device)
or web3/source-audit (Immunefi = big payouts, not the $100 tier the user prefers).

---

## 5. Hard-won lessons (read before hunting)

1. **Blind-validator gate before every report.** Spawn a context-free agent as a
   skeptical H1 triager; give it only the finding facts. It correctly called the
   Anduril finding "Informative, rescued only by naming" (→ came back Duplicate)
   and Playtika "not worth submitting." Don't submit anything it kills.
2. **False-positive traps that fooled the tooling:**
   - subjack "UPTIMEROBOT/STRIKINGLY" generic body-match → ALWAYS false; CNAME-verify.
   - Soft-404 catch-all hosts return 200+JSON for *any* path → canary-probe first.
   - WAF returns HTTP 200 with a block-message body (`api.mcc.miui.com/actuator/env`) → check body, not just status.
   - Private-IP "hits" that are 127.0.0.1 / 192.0.2.x → placeholders, not leaks.
   - Config `env.js` with Stripe `pk_live_` (publishable), PostHog/Sentry/Segment keys → client-safe by design, not secrets.
3. **Always read the program's exclusions first** — takeover, staging-exposure,
   info-disclosure, and specific hosts are excluded on many programs; and several
   require a specific identification header or you're ineligible / SOC-blocked.
4. **Private-IP-in-DNS is real but Low/Informative** unless the *naming* is sensitive
   (Anduril's military/ITAR names were the only thing that elevated it — and it still dup'd).
5. **The fast CNAME sweep beats subjack for breadth takeover hunting.**
6. **Environment discipline (this cloud box):** after any `pkill -f`, verify with
   `ps aux` and kill survivors by PID (orphaned httpx/subjack children kept running on
   deleted file handles). On your persistent machine this matters less.

---

## 6. Authenticated testing (for the persistent-machine + dedicated device setup)
The blocker in the cloud/mobile setup was extracting a session token. On a real
machine with a browser (or a dedicated Android + Burp/Reqable with a system CA):
- The USER logs in and provides their **session JWT/bearer** (not password); the
  agent does authenticated API testing (IDOR/BOLA/mass-assignment/authz) from it.
- Wolt's policy literally maps which admin portals a normal-user JWT *should* reach
  (`corporate/drive/merchant`) and invites you to show if it reaches MORE — a
  single-account authz test, ideal first authenticated target.
- Reqable/HTTP-Toolkit CA install needs the cert as a **user CA** (works for browser
  traffic) or **system CA** (needs root — get a cheap secondary Android to root).

---

## 7. All repos involved

| Repo | Role |
|---|---|
| `github.com/wheresmyicecream/claude-bug-bounty` | **Main working repo** (this one). Branch: `claude/eternal-recon-takeover-scan-rdvsae`. All my commits are here. |
| `github.com/shuvonsec/claude-bug-bounty` | The **upstream** this is forked from (byte-identical 13 skills / 27 commands). Nothing imported (100% dup). Note: its README carries a community meme-coin contract address (self-documented in its FAQ; not malicious, just odd). |
| `github.com/elementalsouls/Claude-BugHunter` | Source of the 71 vendored skills (MIT). |
| `github.com/vercel-labs/skills` | Source of `find-skills` + the `npx skills` CLI. |
| `github.com/yaklang/hack-skills` | ~102 reference hack skills (installed via `npx skills`). |
| `github.com/EFForg/apkeep` | APK downloader binary. |
| `github.com/initstring/cloud_enum` | Real cloud_enum (PyPI one is a placeholder). |
| `github.com/anthropics/*` | Source-review target (Anthropic H1 program). Reviewed: knowledge-work-plugins, claude-plugins-official, claude-for-legal, skills, defending-code-reference-harness, claude-code-action. |
| `bounty-targets-data` (arkadiyt mirror) | Program dataset behind `program_finder.py`, cached in `.private/bounty-targets-data/`. |

---

## 8. Next actions on the persistent machine
1. `git clone` + checkout the branch + install tools (§1).
2. Recreate the fast CNAME sweep + private-IP sweep scripts (§2; logic documented above) — or ask the agent to, they're simple.
3. `python3 tools/program_finder.py --refresh --require-response-known --top 30` → pick fresh, un-hunted programs (see §4 for what's done).
4. Run recon + fast-CNAME-takeover-sweep as long background jobs (they'll finish here).
5. Any candidate → verify → check program allows the class → **blind-validator gate** → user writes report + PoC → user submits.
6. Consider a dedicated rooted Android for authenticated testing (§6) — that's where the real bounty volume is.
