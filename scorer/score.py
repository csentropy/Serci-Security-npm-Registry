"""Rubric v0.1.0 — Publish Path Score.

Design rules, in force permanently:
1. Only signals verified extractable in SPIKE_REPORT.md may be scored.
2. Absence of evidence scores as UNVERIFIED, never as proven-bad.
   The score measures verifiability of the publish path, not the
   morality of the maintainer. All public copy must keep this framing.
3. methodology_version stamps every row. Weight changes bump the
   version; historical rows are never rescored in place. The history
   is the moat only if the methodology is stable and auditable.
"""

METHODOLOGY_VERSION = "v0.2.0"
# v0.1.0 was retired pre-publication: three signals correlated ~100%
# with attestation, making the grade one-signal-dominated (bimodal,
# no gradient in the unattested majority). v0.2.0 rebalances toward
# maintainer surface and governance. Unattested ceiling: 52 (low C).

WEIGHTS = {
    # Publish-path verifiability — 36
    "latest_attested": 20,        # SLSA provenance on latest release
    "consistency_180d": 10,       # ALL versions in last 180d attested
    "trusted_publisher": 6,       # published by CI identity, not a human token
    # Source linkage — 16
    "repo_declared": 4,
    "githead_present": 5,
    "repo_linkage_match": 7,      # attested workflow repo == claimed repo
    # Release governance — 24
    "workflow_oidc": 5,           # publish workflow requests id-token
    "codeowners": 7,
    "security_md": 6,
    "active": 6,                  # published within 18 months
    # Maintainer surface — 24
    "multi_maintainer": 14,       # the chalk / xz single-point pattern
    "publisher_known": 5,         # publisher is a listed maintainer or CI
    "no_dormancy_burst": 5,       # no publish after >1y silence (hijack tell)
}

GRADES = [(85, "A"), (70, "B"), (50, "C"), (35, "D"), (0, "F")]


def score_package(sig):
    if sig.get("error"):
        return {"name": sig["name"], "error": sig["error"],
                "methodology_version": METHODOLOGY_VERSION}

    pts, flags, hits = 0, [], {}

    def award(key, cond):
        nonlocal pts
        got = bool(cond)
        hits[key] = got
        if got:
            pts += WEIGHTS[key]
        return got

    # --- Publish-path verifiability ---
    attested = award("latest_attested", sig.get("has_attestation"))
    if not attested:
        flags.append("UNVERIFIED_PUBLISH_PATH")

    rv, ra = sig.get("recent_versions_180d", 0), sig.get("recent_attested_180d", 0)
    consistent = rv > 0 and ra == rv
    award("consistency_180d", consistent)
    if attested and rv > ra:
        flags.append("INCONSISTENT_PUBLISH_PATH")  # the axios 0.30.x case

    ci_identity = sig.get("publisher", "") in ("GitHub Actions", "github-actions")
    award("trusted_publisher", ci_identity and attested)

    # --- Source linkage ---
    award("repo_declared", sig.get("repo"))
    award("githead_present", sig.get("has_githead"))
    linkage = sig.get("repo_linkage_match")
    award("repo_linkage_match", linkage is True)
    if linkage is False:
        flags.append("REPO_LINKAGE_MISMATCH")  # claimed repo != attested repo

    # --- Release governance ---
    award("workflow_oidc", sig.get("workflow_oidc"))
    award("codeowners", sig.get("has_codeowners"))
    award("security_md", sig.get("has_security_md"))
    lp = sig.get("last_publish_days")
    award("active", lp is not None and lp <= 540)
    if lp is not None and lp > 540:
        flags.append("DORMANT")

    # --- Maintainer surface ---
    m = sig.get("maintainers", [])
    single = len(m) == 1
    award("multi_maintainer", len(m) >= 2)
    if single:
        flags.append("SINGLE_MAINTAINER")
    pub = sig.get("publisher", "")
    award("publisher_known", ci_identity or (pub and pub in m))
    if pub and not ci_identity and m and pub not in m:
        flags.append("PUBLISHER_NOT_MAINTAINER")
    # Dormancy burst needs history we start capturing today; until the
    # snapshot series exists, award conservatively from packument gap.
    award("no_dormancy_burst", not sig.get("dormancy_burst", False))

    if sig.get("deprecated"):
        flags.append("DEPRECATED")
    if sig.get("requires_signatures"):
        flags.append("BRANCH_REQUIRES_SIGNATURES")  # positive flag
    if sig.get("requires_pr"):
        flags.append("BRANCH_REQUIRES_PR")          # positive flag

    grade = next(g for cut, g in GRADES if pts >= cut)
    return {
        "name": sig["name"],
        "version": sig.get("version"),
        "score": pts,
        "grade": grade,
        "flags": flags,
        "signals": hits,
        "weekly_downloads": sig.get("weekly_downloads", 0),
        "maintainer_count": len(m),
        "methodology_version": METHODOLOGY_VERSION,
    }
