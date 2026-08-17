# Third-Party Skill Notices

The following skill directories under `skills/` are vendored from
[elementalsouls/Claude-BugHunter](https://github.com/elementalsouls/Claude-BugHunter)
(MIT License, Copyright (c) 2026 Sachin Sharma), pulled in to fill a real gap:
`tools/lead_board.py`'s routing table already referenced 34 `hunt-*` skill
names that did not exist anywhere in this repo's `skills/` directory before
this import.

Content was reviewed before merging (no malicious code, no prompt injection,
no exfiltration) and filtered to exclude anything that duplicated a skill
already present here by name or substance, or that didn't fit this project's
authorized-use scope (public bug bounty programs, external attack surface
only).

## Imported as-is (MIT, unmodified except path)

All 57 `hunt-*` skills (`hunt-api-misconfig` through `hunt-xxe`) — matches
every skill name `tools/lead_board.py` routes leads to.

Plus 14 skills judged genuinely non-duplicate:
`apk-redteam-pipeline`, `ios-redteam-pipeline`, `bugcrowd-reporting`,
`cloud-iam-deep`, `enterprise-vpn-attack`, `evidence-hygiene`,
`m365-entra-attack`, `mid-engagement-ir-detection`, `offensive-osint`,
`okta-attack`, `osint-methodology`, `recon-scope-triage`, `redteam-mindset`,
`vmware-vcenter-attack`.

## Deliberately NOT imported

- 8 skills that already exist here under the same name (`bb-methodology`,
  `bug-bounty`, `meme-coin-audit`, `report-writing`, `security-arsenal`,
  `triage-validation`, `web2-recon`, `web3-audit`) — this repo's versions
  are a superset (13 skill domains vs. their 10).
- `bb-local-toolkit` — a variant of their own `bug-bounty` skill tied to
  their local CLI's tool-path conventions, not portable here.
- `redteam-report-template` — DOCX/client-deliverable format for
  non-platform external red-team engagements; this project only reports
  through HackerOne/Bugcrowd/Intigriti/Immunefi.
- `supply-chain-attack-recon` — substantially overlaps this repo's existing
  `cicd-security` skill (dependency confusion, GitHub Actions injection,
  supply chain attacks are already covered there).
- All 15 of their slash commands — every one collides by filename with a
  command already in `commands/`.

## A note on credential-attack skills

`m365-entra-attack` and `okta-attack` include password-spray technique
knowledge (AADSTS code reference, lockout math, etc.) with their own
lockout-discipline caps baked in. That knowledge does not replace this
repo's `skills/credential-attack/` safety gate — any live spraying against
an M365/Okta target must still go through the existing hard-stop workflow
(typed-hostname confirm, audit log, human go/no-go) before anything is sent
to a real target, per `rules/hunting.md` and the Authorized-use context in
`CLAUDE.md`.
