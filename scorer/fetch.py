"""Fetch public metadata for npm packages. Every endpoint here was
verified live in SPIKE_REPORT.md. No authentication required for the
core path; GITHUB_TOKEN enables optional enrichment (branch rules).
"""
import base64
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests

REGISTRY = "https://registry.npmjs.org"
DOWNLOADS = "https://api.npmjs.org/downloads/point/last-week"
ECOSYSTEMS = "https://packages.ecosyste.ms/api/v1/registries/npmjs.org/packages"
JSDELIVR = "https://data.jsdelivr.com/v1/stats/packages"
RAW = "https://raw.githubusercontent.com"
GH_API = "https://api.github.com"

UA = {"User-Agent": "depscore/0.1 (public metadata scorer)"}
GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")



# --- Input validation (A03/A10/A08: untrusted metadata flows into URLs,
# CSV cells, and score computation; validate at the trust boundary) ---
NPM_NAME_RE = re.compile(r"^(@[a-z0-9~][a-z0-9._~-]*/)?[a-z0-9~][a-z0-9._~-]*$")
GH_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
GH_REPO_RE = re.compile(r"^(?!.*\.\.)[A-Za-z0-9._-]{1,100}$")
WF_PATH_RE = re.compile(r"^\.github/workflows/(?!.*\.\.)[A-Za-z0-9._/-]+\.ya?ml$")


def valid_npm_name(name):
    return bool(name) and len(name) <= 214 and bool(NPM_NAME_RE.match(name))

def _session():
    s = requests.Session()
    s.headers.update(UA)
    s.max_redirects = 3
    return s


def _get(session, url, timeout=20, retries=2, **kw):
    for attempt in range(retries + 1):
        try:
            r = session.get(url, timeout=timeout, **kw)
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            return r
        except requests.RequestException:
            if attempt == retries:
                return None
            time.sleep(1 + attempt)
    return None



def _get_json_capped(session, url, max_mb=80, **kw):
    r = _get(session, url, stream=True, **kw)
    if r is None or r.status_code != 200:
        return None
    limit, buf = max_mb * 1024 * 1024, bytearray()
    for chunk in r.iter_content(chunk_size=65536):
        buf.extend(chunk)
        if len(buf) > limit:
            r.close()
            return None
    try:
        return json.loads(bytes(buf))
    except ValueError:
        return None


def top_packages(n=10000, session=None):
    """Top packages by usage. Two independent sources so one flaky
    upstream cannot hole the daily series: ecosyste.ms (registry
    downloads) then jsDelivr (CDN hits). Caller applies the floor."""
    s = session or _session()
    names = _ecosystems_list(n, s)
    if len(names) < n:
        seen = set(names)
        for x in _jsdelivr_list(n, s):
            if x not in seen:
                names.append(x); seen.add(x)
    return names[:n]


def _ecosystems_list(n, s):
    names, page = [], 1
    while len(names) < n and page <= (n // 100) + 2:
        data = None
        for attempt in range(3):
            data = _get_json_capped(s, ECOSYSTEMS, max_mb=5, params={
                "sort": "downloads", "order": "desc",
                "per_page": 100, "page": page})
            if data is not None:
                break
            time.sleep(3 * (attempt + 1))
        if not isinstance(data, list) or not data:
            break
        names.extend(p["name"] for p in data if valid_npm_name(p.get("name", "")))
        page += 1
    return names


def _jsdelivr_list(n, s):
    names, page = [], 1
    while len(names) < n and page <= (n // 100) + 2:
        data = _get_json_capped(s, JSDELIVR, max_mb=5, params={
            "period": "week", "type": "npm", "limit": 100, "page": page})
        if not isinstance(data, list) or not data:
            break
        names.extend(p["name"] for p in data if valid_npm_name(p.get("name", "")))
        page += 1
    return names


def bulk_downloads(names, session=None):
    """npm bulk downloads endpoint: 128 packages per call (verified, F3).
    Scoped packages are not supported in bulk; fetched individually."""
    s = session or _session()
    out = {}
    plain = [x for x in names if not x.startswith("@")]
    scoped = [x for x in names if x.startswith("@")]
    for i in range(0, len(plain), 128):
        chunk = plain[i:i + 128]
        r = _get(s, f"{DOWNLOADS}/{','.join(chunk)}")
        if r is not None and r.status_code == 200:
            data = r.json()
            if len(chunk) == 1:  # single-package response shape differs
                data = {chunk[0]: data}
            for k, v in data.items():
                out[k] = (v or {}).get("downloads", 0)
    for name in scoped:
        r = _get(s, f"{DOWNLOADS}/{requests.utils.quote(name, safe='@/')}")
        if r is not None and r.status_code == 200:
            out[name] = r.json().get("downloads", 0)
    return out


def _parse_repo(repo_field):
    """Extract owner/name from packument repository field. Returns None
    if the field is absent or not GitHub — scored as unlinked."""
    if not repo_field:
        return None
    url = repo_field.get("url", "") if isinstance(repo_field, dict) else str(repo_field)
    m = re.search(r"github\.com[/:]([\w.-]+)/([\w.-]+?)(?:\.git)?(?:[/#].*)?$", url)
    if not m:
        return None
    o, rp = m.group(1), m.group(2)
    if GH_OWNER_RE.match(o) and GH_REPO_RE.match(rp):
        return (o, rp)
    return None


def _raw_exists(session, owner, repo, path):
    """File presence via raw.githubusercontent (no API quota). HEAD
    symbolic ref resolves the default branch."""
    qpath = requests.utils.quote(path, safe="/")
    for ref in ("HEAD", "main", "master"):
        r = _get(session, f"{RAW}/{owner}/{repo}/{ref}/{qpath}", timeout=10, retries=1)
        if r is None:
            continue  # transport error: the ref didn't resolve, try the next
        if r.status_code == 200:
            return True, r
        if r.status_code == 404:
            # HEAD resolves the default branch on github.com, so a 404 here is
            # authoritative: the file is absent. Falling through to main/master
            # on every absent file tripled raw.githubusercontent traffic and
            # pushed the 10K run to 132 min (over the 120-min CI gate). A 404
            # ends the probe; only an unresolved ref (r is None) falls through.
            return False, None
    return False, None


def _attestation_provenance(session, name, version):
    """Fetch and decode the SLSA provenance predicate (verified, part B)."""
    url = (f"{REGISTRY}/-/npm/v1/attestations/"
           f"{requests.utils.quote(name, safe='@/')}@{requests.utils.quote(str(version), safe='')}")
    data = _get_json_capped(session, url, max_mb=5)
    if data is None:
        return None
    for a in data.get("attestations", []):
        if "slsa" not in a.get("predicateType", ""):
            continue
        try:
            payload = a["bundle"]["dsseEnvelope"]["payload"]
            st = json.loads(base64.b64decode(payload))
            bd = st.get("predicate", {}).get("buildDefinition", {})
            wf = bd.get("externalParameters", {}).get("workflow", {})
            deps = bd.get("resolvedDependencies", [{}])
            return {
                "workflow_repo": wf.get("repository", ""),
                "workflow_path": wf.get("path", ""),
                "workflow_ref": wf.get("ref", ""),
                "commit": (deps[0].get("digest", {}) or {}).get("gitCommit", ""),
            }
        except (KeyError, ValueError):
            continue
    return None


def fetch_package(name, session=None, deep=True, enrich=True):
    """One package -> raw signal dict. Single packument call plus cheap
    raw checks; attestation bundle fetched only when the manifest says
    one exists."""
    s = session or _session()
    if not valid_npm_name(name):
        return {"name": name, "error": "invalid_name"}
    pk = _get_json_capped(s, f"{REGISTRY}/{requests.utils.quote(name, safe='@/')}", max_mb=80)
    if pk is None:
        return {"name": name, "error": "packument:unavailable_or_oversized"}

    latest = pk.get("dist-tags", {}).get("latest")
    versions = pk.get("versions", {})
    times = pk.get("time", {})
    vlatest = versions.get(latest, {})
    now = datetime.now(timezone.utc)

    def _age_days(iso):
        try:
            return (now - datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
        except (ValueError, AttributeError):
            return None

    # Attestation consistency across versions published in last 180 days
    recent = []
    for v, meta in versions.items():
        d = _age_days(times.get(v, ""))
        if d is not None and d <= 180:
            recent.append(bool(meta.get("dist", {}).get("attestations")))

    sig = {
        "name": name,
        "version": latest,
        "last_publish_days": _age_days(times.get(latest, "")),
        "maintainers": [m.get("name", "") for m in pk.get("maintainers", [])],
        "publisher": (vlatest.get("_npmUser") or {}).get("name", ""),
        "has_attestation": bool(vlatest.get("dist", {}).get("attestations")),
        "recent_versions_180d": len(recent),
        "recent_attested_180d": sum(recent),
        "has_githead": bool(vlatest.get("gitHead")),
        "repo": _parse_repo(vlatest.get("repository") or pk.get("repository")),
        "deprecated": bool(vlatest.get("deprecated")),
    }

    # Provenance depth + repo-linkage integrity
    if sig["has_attestation"] and deep:
        prov = _attestation_provenance(s, name, latest)
        if prov:
            sig["provenance"] = prov
            if sig["repo"]:
                claimed = f"github.com/{sig['repo'][0]}/{sig['repo'][1]}".lower()
                sig["repo_linkage_match"] = claimed in prov["workflow_repo"].lower()

    # Cheap governance file checks (no API quota)
    if sig["repo"] and deep:
        o, rp = sig["repo"]
        sig["has_codeowners"] = (_raw_exists(s, o, rp, ".github/CODEOWNERS")[0]
                                 or _raw_exists(s, o, rp, "CODEOWNERS")[0])
        sig["has_security_md"] = _raw_exists(s, o, rp, "SECURITY.md")[0]
        wf_path = (sig.get("provenance") or {}).get("workflow_path", "")
        if wf_path and WF_PATH_RE.match(wf_path):
            ok, resp = _raw_exists(s, o, rp, wf_path)
            sig["workflow_oidc"] = bool(ok and resp and "id-token" in resp.text)

    # Optional enrichment: branch rules. Costs 2 GitHub REST calls/repo
    # against a 5,000/hr limit, so it is capped to the top-ranked slice by
    # the caller (enrich=False past the cap) — SPIKE cost check, section 6.
    # Without the cap a 10K run issues ~16K calls and rate-limits, silently
    # blanking the branch-rules signal for most packages.
    if sig["repo"] and GH_TOKEN and deep and enrich:
        o, rp = sig["repo"]
        h = {"Authorization": f"Bearer {GH_TOKEN}"}
        rr = _get(s, f"{GH_API}/repos/{o}/{rp}", headers=h, timeout=10, retries=0)
        if rr is not None and rr.status_code == 200:
            branch = rr.json().get("default_branch", "main")
            rr2 = _get(s, f"{GH_API}/repos/{o}/{rp}/rules/branches/{branch}",
                       headers=h, timeout=10, retries=0)
            if rr2 is not None and rr2.status_code == 200:
                rules = {x.get("type") for x in rr2.json()}
                sig["branch_rules"] = sorted(rules)
                sig["requires_pr"] = "pull_request" in rules
                sig["requires_signatures"] = "required_signatures" in rules

    return sig


def fetch_all(names, workers=16, deep=True, progress=None, enrich_top_n=None):
    # `names` is in download-rank order, so the first enrich_top_n are the
    # highest-impact packages; only they pay the GitHub-API enrichment cost.
    # None => enrich all (small runs); default cap applied by run.py at scale.
    s = _session()
    results = []
    cap = len(names) if enrich_top_n is None else enrich_top_n
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_package, n, _session(), deep, i < cap): n
                for i, n in enumerate(names)}
        for i, f in enumerate(as_completed(futs), 1):
            results.append(f.result())
            if progress and i % progress == 0:
                print(f"  fetched {i}/{len(names)}")
    dl = bulk_downloads(names, s)
    for r in results:
        r["weekly_downloads"] = dl.get(r["name"], 0)
    return results
