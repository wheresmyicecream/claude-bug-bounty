# Grindr — Recon Findings Template

**Subdomain takeover is explicitly OUT-OF-SCOPE for this program** ("Outdated
DNS entries or Subdomain Takeover" is listed as non-qualifying). This hunt
skips `tools/takeover_scanner.sh` entirely and focuses on what Grindr's
policy actually rewards instead:

- **High severity:** "API Disclosure of sensitive or personal information
  without expected access control or failure to protect such sensitive or
  personal information with reasonable encryption and key management."
- Exposed config files / secrets (env.js, .env, API keys in JS bundles).
- Public cloud storage buckets under the `grindr` brand.
- Known-CVE / misconfiguration hits via nuclei.

Grindr explicitly weighs "sensitive and personal data" heavily — this
includes private chats/media AND location information beyond what's normally
provided within the app. Handle anything touching real user data with extra
care; per the general rule, do not access, modify, or exfiltrate real user
data even if a gap is found — document exposure, don't harvest it.

## 7-Question Gate (adapted, no subdomain-takeover branch)

- **Q1 (usable now, step by step):** exact unauthenticated request that
  demonstrates the access-control gap or exposure, no account creation
  needed (per user's no-auth-testing constraint for this pass).
- **Q2 (accepted impact):** confirm the specific finding maps to a rewarded
  category in Grindr's severity table (Critical/High/Medium/Low) -- re-check
  the out-of-scope list before writing anything up.
- **Q3 (in-scope asset):** confirm via `.private/grindr/scope_check.sh`
  `check_asset` -- must be one of `*.grindr.io`/`*.grindr.com`/
  `*.grindr.mobi`/`web.grindr.com`, NOT dev/dev2/preprod (bounty-ineligible)
  or any of the explicitly excluded brands/URLs.
- **Q4 (no elevated privilege required):** must be reproducible with no
  account or an anonymous request.
- **Q5 (not already known):** search Grindr's disclosed reports for the
  endpoint/pattern first (114 resolved reports as of this hunt).
- **Q6 (proof beyond "technically possible"):** show the actual sensitive
  data class exposed (or absence of expected access control), not just a
  200 status code -- but stop short of pulling real user records.
- **Q7 (not a known-invalid class):** cross-check against the out-of-scope
  list (subdomain takeover, missing security headers, CSRF on
  logout/no-sensitive-action, rate-limiting/brute-force issues, GPS
  spoofing, third-party API keys in mobile app without clear impact --
  all explicitly excluded).

## Notes

- CVSS/impact reference: their severity table treats "Ability to inject
  arbitrary code into the Grindr mobile app... causing sensitive/personal
  data to be revealed" as Critical; general API PII disclosure without
  access control as High.
- Program launched 2023-02-23, bounty range $100-$4,000 (per HackerOne's
  displayed stats, not the policy text which doesn't publish numbers).
