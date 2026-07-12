"""Post-run health check. Runs in CI via workflow_run after every
daily-snapshot completes (see .github/workflows/health-check.yml), and
locally as `python scorer/health.py`.

Three predicates over the two most recent CANONICAL snapshots (rows with
meta status=calibration are excluded from the series and from this check):

1. GRADE STABILITY — day-over-day grade-changers on the name intersection.
   The 07-07 calibration incident showed what an unhealthy diff looks like
   (vantage artifact in the raw-fetch trio). Clean CI-to-CI days measure in
   single/low-double digits (07-09→07-10: 2). FAIL above HARD_CHANGERS —
   that is the signal to promote the tri-state carry-forward patch.
2. ENRICHMENT — BRANCH_REQUIRES_* flags present means ENRICH_TOKEN is being
   read. Zero is a NOTICE, not a failure: enrichment is flags-only and
   never moves a score, so a dead token must not block the series.
3. RUN COST — errors single-digit, scored above the floor. Runtime is
   enforced by the workflow gate itself, not re-checked here.

Exit 0 = healthy (notices allowed). Exit 1 = at least one FAIL, which fails
the CI job and triggers GitHub's failure notification. No token, no webhook.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPDIR = ROOT / "snapshots"

HARD_CHANGERS = 150   # grade-changers above this = FAIL (promote tri-state patch)
WARN_CHANGERS = 100   # above this = warn, still healthy per the spec
MIN_SCORED = 9900
MAX_ERRORS = 9


def canonical_snapshots():
    """Snapshot dirs with meta.json, oldest→newest, calibration excluded."""
    out = []
    for d in sorted(SNAPDIR.iterdir()):
        mp = d / "meta.json"
        if not mp.exists():
            continue
        meta = json.loads(mp.read_text())
        if meta.get("status") == "calibration":
            continue
        out.append((d, meta))
    return out


def load_grades(d):
    with open(d / "scores.csv", newline="") as f:
        return {r["name"]: r for r in csv.DictReader(f)}


def main():
    snaps = canonical_snapshots()
    if len(snaps) < 2:
        print(f"only {len(snaps)} canonical snapshot(s); nothing to diff — OK")
        return 0
    (prev_dir, _), (cur_dir, cur_meta) = snaps[-2], snaps[-1]
    prev, cur = load_grades(prev_dir), load_grades(cur_dir)
    failures, notices = [], []

    # 1. grade stability
    inter = prev.keys() & cur.keys()
    changers = [(n, prev[n]["grade"], cur[n]["grade"])
                for n in inter if prev[n]["grade"] != cur[n]["grade"]]
    order = "FDCBA"
    up = sum(1 for _, o, n in changers if order.index(n) > order.index(o))
    line = (f"grade stability: {len(changers)} changers on {len(inter)} shared "
            f"({up} up / {len(changers) - up} down) [{prev_dir.name} → {cur_dir.name}]")
    if len(changers) > HARD_CHANGERS:
        failures.append(line + f" — EXCEEDS {HARD_CHANGERS}: promote the "
                        "tri-state carry-forward patch to urgent")
        for n, o, nw in sorted(changers)[:10]:
            print(f"    {n}: {o}->{nw}")
    elif len(changers) > WARN_CHANGERS:
        notices.append(line + f" — above {WARN_CHANGERS}, watch the trend")
    print(("FAIL  " if len(changers) > HARD_CHANGERS else "ok    ") + line)

    # 2. enrichment
    flagged = sum(1 for r in cur.values() if "BRANCH_REQUIRES" in r["flags"])
    if flagged == 0:
        notices.append("enrichment: 0 BRANCH_* flags — ENRICH_TOKEN not read? "
                       "Non-urgent (flags-only, scores unaffected).")
        print("note  enrichment: 0 rows flagged")
    else:
        print(f"ok    enrichment: {flagged} rows carry BRANCH_* flags")

    # 3. run cost
    scored, errors = cur_meta.get("scored", 0), cur_meta.get("errors", 99)
    line = f"run cost: scored={scored} errors={errors}"
    if scored < MIN_SCORED or errors > MAX_ERRORS:
        failures.append(line + f" — outside bounds (scored>={MIN_SCORED}, "
                        f"errors<={MAX_ERRORS})")
        print("FAIL  " + line)
    else:
        print("ok    " + line)

    for n in notices:
        print("NOTICE:", n)
    if failures:
        print("\nHEALTH CHECK FAILED:")
        for f_ in failures:
            print(" -", f_)
        return 1
    print("\nhealthy:", cur_dir.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
