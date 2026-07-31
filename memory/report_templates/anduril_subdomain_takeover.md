# Anduril Industries — Subdomain Takeover Finding Template

One copy of this file per confirmed candidate. Rename to the vulnerable
hostname, e.g. `old-cdn.anduril.dev.md`. Do NOT submit anything until the
7-Question Gate below is fully answered — dangling-CNAME false positives
(service already reclaimed, wildcard DNS, transient NXDOMAIN, or subjack's
generic body-text fingerprint match — see kill-fast notes) are the most
common N/A in this bug class.

All requests for this hunt include `X-HackerOne-Research: whereismyicecream`
per the program's request.

## 7-Question Gate

- **Q1 (usable now, step by step):** 1. Setup: no account needed. 2. Request:
  `dig CNAME <host>` + `curl -sk https://<host>`. 3. Result: [service
  fingerprint match, e.g. "NoSuchBucket" / "There isn't a GitHub Pages site
  here"]. 4. Impact: attacker claims `<host>` on the third-party service and
  serves arbitrary content under Anduril's domain. 5. Cost: $0, minutes.
- **Q2 (accepted impact):** Subdomain takeover isn't explicitly excluded in
  Anduril's policy — confirm current policy page before submitting.
- **Q3 (in-scope asset):** Confirm `<host>` matches one of the 6 wildcards in
  `.private/anduril/scope_check.sh` / `memory/scope/anduril_industries.json`
  and is not `andurilgear.com` (excluded). If the host doesn't match any of
  the 6 wildcards but looks Anduril-related, ask the program team before
  submitting — their policy explicitly requests this for unscoped subdomains.
- **Q4 (no elevated privilege required):** Claiming the resource must not
  require anything beyond a free/self-serve account on the third-party
  service (S3, Heroku, GitHub Pages, Azure, etc.).
- **Q5 (not already known):** Search Anduril's HackerOne disclosed reports
  for this hostname/service first (only 18 resolved reports total as of this
  hunt, so this should be quick).
- **Q6 (proof beyond "technically possible"):** Actually claim the resource
  (or show unambiguous fingerprint + unclaimed status per
  can-i-take-over-xyz) and serve a harmless page — screenshot required. Do
  NOT exfiltrate any data (explicit program rule) and do NOT leave a claimed
  resource live/public longer than needed for PoC.
- **Q7 (not a known-invalid class):** Confirm this isn't wildcard-DNS
  masking (every random subdomain "resolves") or a CDN default parking page
  mistaken for a takeover signal.

## HackerOne Report

```markdown
## Summary

[One paragraph: dangling CNAME on <host> points to <third-party-service>,
which returns a claimable/unregistered-resource fingerprint. An attacker can
register the resource on <third-party-service> and serve arbitrary content
under Anduril's domain <host>.]

## Vulnerability Details

**Vulnerability Type:** Subdomain Takeover
**CVSS 3.1 Score:** [7.5 High typical — AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:N]
**Affected Host:** <host>
**CNAME Target:** <dangling-target, e.g. old-bucket.s3.amazonaws.com>

## Steps to Reproduce

1. `dig CNAME <host>` → shows CNAME to `<dangling-target>`
2. `curl -sk https://<host>` → response body contains
   `[exact fingerprint string]`, matching the [service] "unclaimed resource"
   signature per https://github.com/EdOverflow/can-i-take-over-xyz
3. Registered `<dangling-target>` on [service] (free tier)
4. Re-requested `https://<host>` → now serves attacker-controlled content
   (screenshot attached)

## Impact

[Concrete: phishing under a trusted Anduril subdomain, first-party cookie
theft if session cookies scope to the parent domain, brand damage, etc.]

## Recommended Fix

Remove the dangling DNS record, or re-claim/re-provision the third-party
resource under Anduril's ownership before decommissioning the CNAME.

## Supporting Materials

[Screenshot of claimed resource serving PoC page]
[dig/curl output]
```

## Kill-fast notes

- Wildcard DNS on the root mimics a takeover signal for every random
  hostname — verify with a clearly-nonexistent random subdomain first.
- subjack's real output format is `[SERVICE_NAME] host` for a match or
  `[Not Vulnerable] host` otherwise (NOT a literal `[Vulnerable]` label —
  see tools/takeover_scanner.sh). Every hit is auto-cross-checked against
  its expected CNAME via `tools/verify_takeover_candidates.py` — only
  `LIKELY REAL`/`CONFIRM/CLAIM` verdicts are worth pursuing; `FALSE POSITIVE`
  means the CNAME doesn't actually point to the claimed provider (generic
  body-text match, seen repeatedly on Eternal/Xiaomi hunts).
- This program launched Jan 2026 with only 18 resolved reports total as of
  this hunt — chosen specifically for low prior coverage, but that also
  means less precedent to compare against for Q5.
