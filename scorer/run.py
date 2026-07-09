"""Daily snapshot runner.

  TOP_N=10000 python run.py          # full daily run (GitHub Actions)
  TOP_N=300  python run.py           # smoke / demo run

Writes snapshots/YYYY-MM-DD/{scores.json,scores.csv,meta.json}.
Never overwrites an existing snapshot for the same date: the series
is append-only by construction.
"""
import csv
import hashlib
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch import fetch_all, top_packages          # noqa: E402
from score import METHODOLOGY_VERSION, score_package  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPDIR = ROOT / "snapshots" / date.today().isoformat()


def _csv_safe(v):
    """OWASP CSV-injection guard: scoped npm names start with '@', which
    spreadsheet apps treat as a formula sigil. Prefix risky cells."""
    s = str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def main():
    n = int(os.environ.get("TOP_N", "10000"))
    if SNAPDIR.exists() and (SNAPDIR / "meta.json").exists():
        print(f"snapshot for {date.today()} already exists; append-only series, exiting")
        return

    print(f"[1/3] top {n} package list…")
    names = top_packages(n)
    print(f"      got {len(names)} from live sources")
    cache = ROOT / "data" / "package_list.json"
    floor = max(50, n // 2)
    if len(names) >= floor:
        cache.parent.mkdir(exist_ok=True)
        cache.write_text(json.dumps(names))
    elif cache.exists():
        cached = json.loads(cache.read_text())[:n]
        print(f"      live sources thin; using cached list ({len(cached)})")
        names = cached
    if len(names) < floor:
        sys.exit(f"ABORT: {len(names)}/{n} names after fallbacks; "
                 "refusing to write a thin snapshot (moat integrity)")

    # GitHub branch-rule enrichment is capped to the top-ranked slice to stay
    # under the 5,000/hr REST limit (2 calls/repo). Signal is flags-based and
    # medium-fidelity, so capping it does not distort the headline score.
    enrich_n = int(os.environ.get("ENRICH_TOP_N", "2000"))
    # I/O-bound (per-package: packument + attestation + raw governance-file
    # 404 round-trips), so throughput scales with workers well past core count.
    # 16 workers put a 10K run at ~113 min, over the CI 120-min gate; 32 halves it.
    workers = int(os.environ.get("WORKERS", "32"))
    print(f"[2/3] fetching metadata ({len(names)} packages; {workers} workers; "
          f"branch-rule enrichment for top {min(enrich_n, len(names))})…")
    raw = fetch_all(names, workers=workers, progress=100, enrich_top_n=enrich_n)

    print("[3/3] scoring…")
    rows = [score_package(s) for s in raw]
    ok = [r for r in rows if "error" not in r]
    if len(ok) < max(50, len(names) // 2):
        sys.exit(f"ABORT: only {len(ok)}/{len(names)} scored; "
                 "refusing to finalize (transient upstream failure likely)")
    ok.sort(key=lambda r: (-r["weekly_downloads"], r["name"]))

    tmp = SNAPDIR.parent / (SNAPDIR.name + ".tmp")
    if tmp.exists():
        import shutil; shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    with open(tmp / "scores.json", "w") as f:
        json.dump(ok, f, separators=(",", ":"))
    with open(tmp / "scores.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "version", "score", "grade", "flags",
                    "maintainer_count", "weekly_downloads", "methodology_version"])
        for r in ok:
            w.writerow([_csv_safe(r["name"]), _csv_safe(r["version"]),
                        r["score"], r["grade"], _csv_safe("|".join(r["flags"])),
                        r["maintainer_count"], r["weekly_downloads"],
                        r["methodology_version"]])

    dist = {}
    for r in ok:
        dist[r["grade"]] = dist.get(r["grade"], 0) + 1
    attested = sum(1 for r in ok if r["signals"].get("latest_attested"))
    single = sum(1 for r in ok if "SINGLE_MAINTAINER" in r["flags"])
    meta = {
        "date": date.today().isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "methodology_version": METHODOLOGY_VERSION,
        "requested": n, "scored": len(ok),
        "errors": len(rows) - len(ok),
        "grade_distribution": dist,
        "pct_latest_attested": round(100 * attested / max(len(ok), 1), 1),
        "pct_single_maintainer": round(100 * single / max(len(ok), 1), 1),
    }
    # Tamper-evidence: hash the data files; meta.json written LAST so a
    # crashed run never registers as a completed snapshot (append-only moat).
    meta["sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (tmp / "scores.json", tmp / "scores.csv")}
    with open(tmp / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    if SNAPDIR.exists():
        import shutil; shutil.rmtree(SNAPDIR)
    tmp.rename(SNAPDIR)

    print(json.dumps(meta, indent=2))
    print(f"snapshot written: {SNAPDIR}")


if __name__ == "__main__":
    main()
