# Changelog

Auditable record of pipeline and methodology changes. Scores are never
rescored in place (Operating rule #2) — this log exists so that any change in
what a snapshot row *contains* is explicable from a public diff of the
history. If a row's shape changes, the reason is here, dated.

## 2026-07-09 — canonical series starts; 2026-07-07 relabeled calibration

The `2026-07-07` run was generated from a **local** vantage (not CI). Its
raw-fetch governance signals — `codeowners` (+7), `security_md` (+6),
`workflow_oidc` (+5), all fetched from raw.githubusercontent — were depressed
by local-IP throttling, artificially lowering scores. Packument-derived
signals (attestation, maintainer count) were unaffected; that is why
attested (22.2%→22.3%) and single-maintainer (53.6%→53.4%) barely moved
between the two runs while the grade mix shifted. ~99% of the movement
decomposes into that {7,6,5} raw-fetch trio.

Resolution — **label, do not delete** (the same move that retired rubric
v0.1.0 pre-publication): `2026-07-07/meta.json` now carries
`"status": "calibration"`, `"vantage": "local"`, and a note. It is retained
(append-only series never remove entries) but **excluded from the series**.
The canonical daily series begins `2026-07-09` (CI vantage): 9,974 scored,
5 errors. When the alert layer is built, it must **skip any row whose
`status` is `calibration`**.

## 2026-07-09 — branch-rule enrichment wired (activates next scheduled run)

The `ENRICH_TOKEN` secret was added, enabling GitHub branch-rule enrichment,
capped to the top 2,000 packages by download rank (`ENRICH_TOP_N`, to stay
under the REST 5,000/hr limit). The first **enriched** snapshot is the first
scheduled run after the secret is set — expected `2026-07-10`.

From that row forward, top-ranked packages may carry the positive flags
`BRANCH_REQUIRES_PR` and `BRANCH_REQUIRES_SIGNATURES`.

- **Methodology is unchanged at v0.2.0.** Enrichment adds informational flags
  only; it awards **no score points**. A package's score and grade are
  identical with or without the token. This is not a rescore.
- The founding rows `2026-07-07` and `2026-07-09` were generated before the
  token was wired and are **intentionally left un-enriched**. They are NOT
  rewritten. The absence of branch-rule flags on those two dates is a true
  record of when the capability came online — not a bug to "fix."

## 2026-07-07 — calibration run (rubric v0.2.0, local vantage)

First full top-10,000 run: 9,968 scored, 6 errors. Executed locally, before
CI. Retained and labeled `status: calibration` — see the 2026-07-09 entry
above for why its governance signals read low. Not part of the canonical
series; the series and the moat clock begin 2026-07-09.
