# HubSpot — Recon Findings Template

Subdomain takeover **is** in scope here (unlike Grindr). This hunt is
CLI-only per user's no-account/no-auth-testing rule -- HubSpot's
highest-value bug classes (auth flows, cross-portal CRM data leakage, the
$15k-$20k CTF challenge) all require creating a trial portal and
authenticated testing, and are explicitly out of scope for this pass.

## 7-Question Gate (takeover)

- **Q1:** `dig CNAME <host>` + `curl -sk https://<host>`. Fingerprint match →
  claim → prove, same as prior hunts.
- **Q2:** Subdomain takeover not excluded per policy -- confirm still true
  before submitting (policies change).
- **Q3:** Confirm via `.private/hubspot/scope_check.sh` `check_asset` --
  must be one of the 7 wildcards or the 2 exact hosts (chatspot.ai,
  hubspot.net -- exact match only, no subdomains), and not one of the 6
  excluded hosts (connect.com, shop/trust/thespot/ir/events.hubspot.com).
- **Q4:** No elevated privilege to claim the resource.
- **Q5:** Search disclosed reports first (only 235 resolved as of this hunt).
- **Q6:** Actually claim + prove, per usual.
- **Q7:** Rule out wildcard DNS / CDN parking-page false positives, and
  ALWAYS run `tools/verify_takeover_candidates.py` against the CNAME before
  trusting any subjack hit -- the UPTIMEROBOT/GEMFURY generic-body-match
  false positive has shown up on every program hunted so far.

## Non-takeover recon (config/secrets/cloud/nuclei)

Same canary-protected config-exposure check, gitleaks/x8 if JS/params found,
cloud_enum against "hubspot" brand keyword, nuclei high/critical sweep.
Note HubSpot explicitly calls out interest in "sensitive data exposure" as a
high-impact class -- a genuine config/secret leak here would likely be
well-received, unlike Grindr's public-reCAPTCHA-key non-issue.

## Kill-fast notes specific to HubSpot

- This is a CRM/marketing platform used to host countless CUSTOMER sites
  under hs-sites.com/hubspotpagebuilder.com -- expect a huge, extremely
  templated subdomain footprint (same shape as Xiaomi's mi.com shop.*
  explosion). `tools/sample_subdomain_clusters.py` should catch this
  automatically, but sanity-check the sampled count before committing to a
  full recon_engine.sh run.
- "Other HubSpot-owned (sub)domains not listed as Out of Scope" is a broad
  catch-all -- if subfinder turns up something that looks HubSpot-owned but
  isn't obviously one of the 7 root domains, verify ownership (WHOIS/ASN)
  before testing, don't assume.
