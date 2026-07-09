# [PACKAGE] was compromised. Its publish path was unverifiable the whole time.

<!-- SHIP RULE: publish within 6 hours of incident confirmation. Fill
slots, delete comments, run the neighbor query, post. Do not add
sections. Do not speculate about attribution. Every number must come
from a snapshot row or a public API response you can link.

NEIGHBOR QUERY (this is section "Who else fits this profile"): filter the
morning's snapshots/<date>/scores.csv by the incident's two flags + a
downloads floor. Baseline as of the 2026-07-07 founding snapshot, top 10K:
  - UNVERIFIED_PUBLISH_PATH + SINGLE_MAINTAINER + >1M weekly dl -> 567 packages
    (led by minimatch, lru-cache, chalk, type-fest, js-yaml)
  - INCONSISTENT_PUBLISH_PATH + >1M weekly dl -> 236 packages
Re-run against the incident-day snapshot before posting; never ship a
stale count. The number is large on purpose — that is the story. -->

**TL;DR:** `[PACKAGE]` ([X]M weekly downloads) shipped malicious code in
version `[VERSION]` on `[DATE]`. Our registry has scored its publish
path **[GRADE]** since we began tracking on `[FIRST_SNAPSHOT_DATE]`.
The signals were public the entire time: [TOP_2_FLAGS, plain words].
[N] packages in the top 10,000 share this exact risk profile today.
Check whether you depend on one: [LINK].

## What happened

[3–5 sentences. Mechanism only — what was published, when, what it did.
Link the advisory. No adjectives.]

## What the metadata showed before the incident

Score on day of compromise: **[SCORE]/100 ([GRADE])**
Flags at time of compromise:

- `[FLAG_1]` — [one plain-language sentence: what this means and why it
  is an attack channel]
- `[FLAG_2]` — [same]

Score history: [SPARKLINE / table of last 90 days of snapshot rows.
If the score CHANGED before the incident — maintainer added/removed,
publish path shifted — lead with that. "The score dropped from B to D
on [DATE] when [EVENT]" is the strongest possible frame.]

<!-- If our score was GOOD (B or better) on the compromised package:
still publish. Lead with "our rubric missed this, here is the signal
we did not weight, here is methodology v[NEXT]." Credibility of the
series > any single row. Do not bury a miss. -->

## The signals were free

Every signal above comes from public metadata — the npm packument, the
attestation endpoint, the repository. No scanner, no agent, no access
to [PACKAGE]'s systems. Anyone could have seen this. The problem is
nobody was looking at [10,000] packages every day. That is the entire
reason this registry exists.

## Who else fits this profile right now

Query: packages in the top 10,000 with `[FLAG_1]` + `[FLAG_2]` and
more than 1M weekly downloads, as of this morning's snapshot:

[TABLE: name | weekly downloads | score | flags — cap at 15 rows,
link the full query. THIS SECTION IS THE PRODUCT. The incident is the
hook; the neighbor list is why anyone signs up.]

## Check your own tree

Paste your `package-lock.json` — get the score and flags for every
package in your tree, and an alert when any of them changes:
**[SIGNUP_LINK]**

Methodology `[METHODOLOGY_VERSION]`, open and versioned: [LINK]. Every
row above links to the public API response behind it. If you maintain
`[PACKAGE]` or any package listed and believe a signal is wrong, the
dispute process is [LINK] — corrections ship in the next daily snapshot
with a changelog entry.
