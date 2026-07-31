# Eternal — Subdomain Takeover Finding Template

One copy of this file per confirmed candidate. Rename to the vulnerable
hostname, e.g. `old-cdn.grofer.io.md`. Do NOT submit anything until the
7-Question Gate below is fully answered — dangling-CNAME false positives
(service already reclaimed, wildcard DNS, transient NXDOMAIN) are the most
common N/A in this bug class.

## 7-Question Gate

- **Q1 (usable now, step by step):** 1. Setup: no account needed. 2. Request:
  `dig CNAME <host>` + `curl -sk https://<host>`. 3. Result: [service
  fingerprint match, e.g. "NoSuchBucket" / "There isn't a GitHub Pages site
  here"]. 4. Impact: attacker claims `<host>` on the third-party service and
  serves arbitrary content under Eternal's domain. 5. Cost: $0, minutes.
- **Q2 (accepted impact):** Subdomain takeover is explicitly listed as
  in-scope/rewarded for this program — confirm current policy page before
  submit.
- **Q3 (in-scope asset):** Confirm `<host>` passes
  `.private/eternal/scope_check.sh` `check_asset` AND is not on the program's
  exclusion list (staging*.runnr.in, hyperpure dev/staging, *.ali.zomans.com,
  loose zomato.com hosts, blinkit.com subdomains).
- **Q4 (no elevated privilege required):** Claiming the resource must not
  require anything beyond a free/self-serve account on the third-party
  service (S3, Heroku, GitHub Pages, Azure, etc.).
- **Q5 (not already known):** Search Eternal's HackerOne disclosed reports
  for this hostname/service before reporting.
- **Q6 (proof beyond "technically possible"):** Actually claim the resource
  (or show unambiguous fingerprint + unclaimed status per
  can-i-take-over-xyz) and serve a harmless page — screenshot required.
  Do NOT leave a claimed resource live/public longer than needed for PoC.
- **Q7 (not a known-invalid class):** Confirm this isn't wildcard-DNS
  masking (every random subdomain "resolves") or a CDN default parking page
  mistaken for a takeover signal.

## HackerOne Report

```markdown
## Summary

[One paragraph: dangling CNAME on <host> points to <third-party-service>,
which returns a claimable/unregistered-resource fingerprint. An attacker can
register the resource on <third-party-service> and serve arbitrary content
under Eternal's domain <host>.]

## Vulnerability Details

**Vulnerability Type:** Subdomain Takeover
**CVSS 3.1 Score:** [7.5 High typical — AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:N,
adjust if session/cookie theft via related first-party cookies is provable]
**Affected Host:** <host>
**CNAME Target:** <dangling-target, e.g. old-bucket.s3.amazonaws.com>

## Steps to Reproduce

1. `dig CNAME <host>` → shows CNAME to `<dangling-target>`
2. `curl -sk https://<host>` → response body contains
   `[exact fingerprint string]`, matching the
   [service] "unclaimed resource" signature per
   https://github.com/EdOverflow/can-i-take-over-xyz
3. Registered `<dangling-target>` on [service] (free tier)
4. Re-requested `https://<host>` → now serves attacker-controlled content
   (screenshot attached)

## Impact

[Concrete: phishing under a trusted Eternal subdomain, first-party cookie
theft if session cookies scope to the parent domain, brand damage, etc. —
be specific to what this subdomain was used for before rebrand/decommission.]

## Recommended Fix

Remove the dangling DNS record, or re-claim/re-provision the third-party
resource under Eternal's ownership before decommissioning the CNAME.

## Supporting Materials

[Screenshot of claimed resource serving PoC page]
[dig/curl output]
```

## Kill-fast notes

- Wildcard DNS on the root (`*.district.in` etc. resolving everything to one
  IP) mimics a takeover signal for every random hostname — verify with a
  clearly-nonexistent random subdomain first; if that also "resolves", the
  whole root is wildcarded and individual CNAME hits need double-checking.
- subjack logs both `[Vulnerable]` and `[Not Vulnerable]` — only
  `^\[Vulnerable\]` lines are real candidates (see tools/takeover_scanner.sh).
- Zomans.com is flagged by the program itself as internal/AWS-sensitive —
  prioritize but don't assume; still needs the same fingerprint proof.
