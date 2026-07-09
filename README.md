# depscore — Publish Path Score (working name; branding is an open decision)

Daily security-governance scores for the top 10,000 npm packages, computed
from public metadata only. No maintainer cooperation required. History is
append-only and starts the day this repo is pushed.

## Why this exists
Supply chain incidents arrive roughly monthly. Each post-mortem asks the
same question: was this predictable? The signals — publish provenance,
maintainer surface, release governance — are public. Nobody watches them
at ecosystem scale, daily, with a kept history. This does.

## What is in this repo
- SPIKE_REPORT.md — live verification that every scored signal is
  extractable at scoring-grade fidelity. Read this first. Signals that
  failed verification (token TTL, 2FA status) are excluded by rule.
- scorer/ — fetch.py (verified endpoints only), score.py (rubric
  v0.2.0, methodology_version stamped on every row), run.py (daily
  snapshot writer, append-only).
- .github/workflows/daily-snapshot.yml — the moat's heartbeat. Push the
  repo, enable Actions, history starts today. $0/month.
- snapshots/2026-07-07/ — founding row. Generated live at the production
  TOP_N=10000: 9,968 of 10,000 scored, 6 fetch errors (0.06%).
- templates/postmortem.md — the ambush kit. Pre-written incident
  analysis with fill-in slots; ship within 6 hours of the next incident.
- site/index.html — capture page. Swap the form action for your
  Buttondown/Tally endpoint, put it behind a domain.

## Day-1 numbers (top 10,000, blended list, rubric v0.2.0)
22.2% have an attested latest release. 53.6% are single-maintainer.
Grade distribution: A 349 | B 1409 | C 485 | D 1374 | F 6351 (of 9,968
scored). Grades measure verifiability of the publish path, not proven
compromise — an F is an UNVERIFIED_PUBLISH_PATH, not a vulnerability.
The single-maintainer share rises from 47% in the top 300 to 53.6%
across the top 10K: the long tail is where the surface concentrates.

## Operating rules (non-negotiable)
1. Absence of evidence scores as UNVERIFIED, never proven-bad. All
   public copy keeps this framing. It is also the legal posture.
2. Methodology changes bump the version; no historical row is ever
   rescored in place. The history is only a moat if it is auditable.
3. Disputes get a public process and corrections ship in the next
   daily snapshot with a changelog entry. Speed of correction is
   credibility.
4. Launch is triggered by the next incident, not by the calendar.
   Until then: snapshots accumulate silently.

## Security posture (audited against OWASP; see workflow comments)
Input validation at every trust boundary (npm name grammar, GitHub
segment rules, workflow-path allowlist), response size caps, CSV
formula-injection guard, SHA-pinned actions, hash-pinned dependencies
installed wheels-only, no write credentials present while untrusted
metadata is processed, atomic append-only snapshots with SHA-256
manifests, and fail-loud gates that abort rather than finalize a thin
snapshot. Crafted-metadata score inflation is treated as highest
severity per SECURITY.md.

## Known limits (be honest in public about these)
- Token type is not directly observable; attestation presence is the
  proxy. We say "verifiable publish path," never "uses ephemeral tokens."
- Branch-rule visibility covers only repos on GitHub rulesets.
- List source (ecosyste.ms) ranks by cumulative downloads; production
  should re-rank candidates by weekly downloads and union with the
  npm-high-impact list so anchors like react are never missed.
- Per-version attestation history is backfillable by anyone; the moat
  is entity-state history: maintainer changes, repo governance, score
  trajectory under a fixed methodology.
