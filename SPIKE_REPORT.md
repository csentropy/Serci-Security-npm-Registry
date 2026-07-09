# Metadata Fidelity Spike — Findings

Run live against production APIs on 2026-07-05. Every claim below was verified by direct query, not recalled from documentation. This report gates the scorer: only signals verified here are in rubric v0.

## Verdict

The registry is buildable from public metadata at scoring-grade fidelity. One signal from the original pitch needed reframing (token type), one of my prior claims needed correction (moat boundary), and one signal turned out stronger than expected (branch rules are publicly queryable).

## Signal-by-signal results

**1. Signed publishing — EXTRACTABLE, but reframe it.**
Every package tested carries `dist.signatures` — npm signs everything itself since ~2022, so registry signatures are near-universal and carry no discriminating power. The discriminating signal is `dist.attestations`. Rubric scores attestations, not signatures.

**2. Release provenance — EXTRACTABLE, high fidelity. This is the anchor signal.**
The attestation bundle (public endpoint, no auth) contains the SLSA v1 provenance predicate: source repository, workflow path, git ref, resolved commit SHA, builder identity. Verified live on axios@1.18.1: repo `axios/axios`, workflow `.github/workflows/publish.yml`, hosted runner, commit `a209bfb1e5dc`. This proves CI-based release and enables a repo-linkage integrity check (does the attested repo match the claimed `repository` field — catches repo spoofing).

**3. Token type (ephemeral vs long-lived) — NOT directly extractable. Proxy is honest and strong.**
The npm user endpoint returns 401; no public API exposes token type or 2FA status. Jay's original framing ("does it use ephemeral tokens") cannot be measured as stated. What IS measurable: a provenance attestation requires an OIDC flow from CI, which means no long-lived publish token was used for that release. So the rubric scores "verifiable publish path" — presence and consistency of attestations — and treats absence as unverifiable, not as proven-bad. The registry must say what it measures. This phrasing discipline is also legal protection.

**4. CI-based release — EXTRACTABLE two ways.**
Directly from the attestation (workflow path + builder id), and corroborated by reading the workflow file itself from raw.githubusercontent.com (no API quota): verified `id-token: write` permission and `--provenance` flag present in axios's publish workflow.

**5. Multi-party approval — PARTIALLY extractable, better than expected.**
`GET /repos/{o}/{r}/rules/branches/{branch}` returns active rulesets on public repos without authentication. Verified live on vercel/next.js: `required_signatures`, deletion protection, ruleset source visible. Coverage caveat: only repos using rulesets (not legacy branch protection, which stays admin-only). Additional proxies verified: CODEOWNERS presence (raw fetch, cheap), signed-commit verification status (`verification.verified: true` on axios commit — public). Rubric treats this as medium-fidelity, flags-based.

**6. Maintainer surface — EXTRACTABLE (current state only).**
Packument exposes current maintainer list and per-version `_npmUser` (who published). chalk: single maintainer, human-account publishes — the exact profile of the Sept 2025 chalk/debug compromise, visible in metadata before the fact. `_npmUser: "GitHub Actions"` vs a human username is itself a publish-path discriminator.

**7. Consistency over time — EXTRACTABLE and it matters.**
axios has 142 versions, 53 attested — but published unattested versions on the 0.30.x line as recently as 2026-02-18, months after the main line was attested. An inconsistent publish path is a live attack channel (an attacker who compromises a token can publish an unattested version even when the project "uses provenance"). Rubric scores consistency across the last 180 days, not just the latest version.

## The moat boundary — correction to my prior claim

I previously stated "history cannot be backfilled by a fast-follower" as a blanket claim. That was partially wrong, and the distinction matters for how hard we defend it:

BACKFILLABLE (not moat): per-version attestation adoption history. It lives in the packument forever — anyone can reconstruct when a package started attesting. Shown live in section D of the spike.

NOT backfillable (real moat): maintainer-list changes over time (packument shows current state only), repo governance state at past dates (workflow contents, rulesets, CODEOWNERS — no retroactive query exists), download-trend granularity beyond the API's rolling window, and score trajectory under a fixed methodology version. A fast-follower starting in month 4 permanently lacks our months 1–3 of entity-state history. Daily snapshots start today for exactly this reason.

## Cost check against the capital-light constraint

Registry packument: no auth, no meaningful rate limit. Downloads API: bulk endpoint takes 128 packages per call — 10K packages is ~80 calls. Raw file checks: no API quota. GitHub REST (rules, commit verification): 5,000/hr with a free token — enrichment for the top 2K daily fits in one hour. Top-10K list: ecosyste.ms open API, verified live. Total infrastructure cost of the daily 10K snapshot: $0 on GitHub Actions free tier. Domain is the only spend.

## What this kills

The rubric contains no signal that failed verification. "2FA enforced," "token TTL," and "legacy branch protection settings" are out. Anything the registry publishes can be defended query-by-query — which is what "scoring-grade" has to mean when the scored parties dispute you in public, and they will.
