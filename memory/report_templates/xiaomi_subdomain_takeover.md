# Xiaomi — Subdomain Takeover Finding Template

**CRITICAL — Xiaomi's published policy explicitly excludes "Subdomain
takeovers - Unable to prove it can be taken over."** A subjack/dnsReaper
fingerprint match is NOT sufficient here, unlike a generic program. You must
actually register the dangling resource on the third-party service and show
it serving attacker content under the Xiaomi subdomain before this is
reportable. Fingerprint-only hits go on the lead board as "needs claim
verification," not straight to a report.

## 7-Question Gate

- **Q1:** 1. Setup: no account. 2. Request: `dig CNAME <host>` + claim the
  resource on the third-party service + `curl -sk https://<host>`. 3.
  Result: page now serves attacker-controlled content. 4. Impact: phishing /
  cookie theft under a trusted Xiaomi subdomain. 5. Cost: $0-minimal
  (whatever the third-party service charges for the resource), minutes-hours.
- **Q2:** Confirm current policy still lists takeover as in-scope-if-proven
  before submitting (policy pages change).
- **Q3:** Confirm `<host>` matches one of the 43 wildcards in
  `.private/xiaomi/scope_check.sh` / `memory/scope/xiaomi.json`.
- **Q4:** Claiming the resource must not require anything beyond a free
  self-serve account on the third-party service.
- **Q5:** Search Xiaomi's HackerOne disclosed reports for the hostname first.
- **Q6:** The claim itself + a served PoC page IS the proof — this is the one
  bug class here where Q6 and the out-of-scope carve-out are the same test.
- **Q7:** N/A if Q6 passed (claimed + proven).

## HackerOne Report

```markdown
## Summary

[Dangling CNAME on <host> pointed to <third-party-service>. Registered the
unclaimed resource and confirmed <host> now serves attacker-controlled
content — full takeover, not just a fingerprint match.]

## Vulnerability Details

**Vulnerability Type:** Subdomain Takeover (proven claim, per program policy)
**Affected Host:** <host>
**CNAME Target:** <dangling-target>

## Steps to Reproduce

1. `dig CNAME <host>` -> <dangling-target>
2. Registered <dangling-target> on [service] (free tier) on <date>
3. `curl -sk https://<host>` -> now returns attacker-controlled PoC page
   (screenshot attached)
4. [Immediately released/deleted the claimed resource after PoC, or note if
   still held for verification — do not leave live longer than necessary]

## Impact

[Specific to what this subdomain was used for.]

## Recommended Fix

Remove the dangling DNS record.

## Supporting Materials

[Screenshot of claimed resource serving PoC, dig output, timestamps]
```

## Kill-fast notes

- subjack `[Vulnerable]` alone = lead-board entry, NOT a report. Only promote
  to report after actually claiming + proving.
- Cloud storage bucket findings (S3/KSS/FDS) here are also judged
  case-by-case on "should this data be restricted" + "how sensitive is it" —
  a bare listing with non-sensitive filenames is unlikely to be rewarded per
  policy; only pursue if the exposed content itself looks sensitive.
