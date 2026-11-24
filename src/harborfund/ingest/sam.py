"""SAM.gov registration status for crosswalk entities (task T2.1).

Run on a machine that can reach api.sam.gov, with your own key in SAM_API_KEY::

    export SAM_API_KEY=...                                   # never written to disk
    uv run python -m harborfund.ingest.sam plan              # list the requests, no network
    uv run python -m harborfund.ingest.sam fetch             # up to --max-requests (default 10)
    uv run python -m harborfund.ingest.sam fetch             # next day: resumes where it stopped
    uv run python -m harborfund.ingest.sam process           # -> data/processed/sam/
    uv run python -m harborfund.ingest.sam apply             # fills sam_* columns in the crosswalk

What it asks SAM.gov (Entity Management API, public data, ``/entity-information/v3/entities``;
request format checked against https://open.gsa.gov/api/entity-api/ on 2026-11-23):

1. **UEI batches.** Every UEI in ``harbor_entity_crosswalk.csv`` (all roles; ``;`` cells
   split), 10 per request: ``ueiSAM=[U1~U2~...]&includeSections=entityRegistration,coreData``
   ``&page=0&size=10``. Ten per request because SAM returns at most 10 records per page.
2. **Expired re-check.** The documentation does not say whether expired registrations are
   returned when ``registrationStatus`` is omitted, so UEIs missing from step 1 are asked again
   with ``registrationStatus=E`` (10 per request). Still missing = ``none_found``. Entities that
   were never registered ("ID assigned" only, ``samRegistered=No``) need a federal system
   account, so the script cannot see them.
3. **Name lookups** for crosswalk rows with no UEI (e.g. County of Orange for Dana Point, the
   harbor districts with no USAspending profile): ``legalBusinessName=<name>`` and
   ``physicalAddressProvinceOrStateCode=<state>``. Name hits are **candidates for hand review
   only**: the project never matches on names (decisions log), so ``apply`` does not copy them
   into the crosswalk.

Request budget: a personal key without a SAM.gov role allows 10 requests a day (1,000 with a
role), per the API page. ``fetch`` stops after ``--max-requests``; responses are cached under
``data/raw/sam/<YYYY-MM-DD>/`` and a rerun skips every request already answered, so the run can
be spread over several days. Each saved response gets a row in ``data/manifest.csv`` (URL with
the key removed). The API key goes in the ``api_key`` query parameter, as in the documented
examples; ``--key-header`` sends it as an ``x-api-key`` header instead.

History: SAM's entity record is the **current** registration only (``registrationDate``,
``activationDate``, ``registrationExpirationDate``, ``lastUpdateDate``). It does not list past
registration periods. For a registration history (H1), the SAM.gov monthly public extracts
would have to be archived over time; not done here.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path

import pandas as pd

from harborfund import config
from harborfund.ingest.usaspending import append_manifest, rel, sha256

TASK = "T2.1"
SOURCE_ID = "sam_entity_api"
API = "https://api.sam.gov/entity-information/v3/entities"
DOC_URL = "https://open.gsa.gov/api/entity-api/"
LICENSE_NOTE = "SAM.gov public entity data (GSA); terms of use not checked"
SECTIONS = "entityRegistration,coreData"
BATCH = 10  # SAM returns at most 10 records per page
CROSSWALK_PATH = config.REFERENCE_DIR / "harbor_entity_crosswalk.csv"
RAW_DIR = config.RAW_DIR / "sam"
OUT_DIR = config.PROCESSED_DIR / "sam"
UEI_RE = re.compile(r"^[A-Z0-9]{12}$")
FORBIDDEN = set("&|{}^\\")  # characters SAM rejects in parameter values

# Search names for no-UEI rows where the crosswalk's plain name would miss the legal name.
# Keyed by (harbor_id, entity_name). Edit here, not in the crosswalk.
NAME_OVERRIDES: dict[tuple[str, str], list[str]] = {
    ("CA-dana-point", "County of Orange (OC Community Resources / Dana Point Harbor)"): [
        "County of Orange"
    ],
    ("CA-huntington-harbour", "Private marina lessees (multiple)"): [],  # not searchable
}


# --------------------------------------------------------------------------- plan


def split_ids(cell: str) -> list[str]:
    return [u.strip().upper() for u in str(cell or "").split(";") if u.strip()]


def search_names(row: pd.Series) -> list[str]:
    key = (row["harbor_id"], row["entity_name"])
    if key in NAME_OVERRIDES:
        return NAME_OVERRIDES[key]
    name = re.sub(r"\s*\(.*?\)", "", row["entity_name"]).strip()
    name = re.sub(r",?\s+(Inc|LLC|Ltd)\.?$", "", name, flags=re.IGNORECASE).strip(" ,")
    name = "".join(ch for ch in name if ch not in FORBIDDEN)
    return [name] if name else []


def crosswalk_ueis(cw: pd.DataFrame) -> list[str]:
    seen: dict[str, None] = {}
    for cell in cw["uei"]:
        for u in split_ids(cell):
            if UEI_RE.match(u):
                seen[u] = None
    return list(seen)


def name_lookups(cw: pd.DataFrame) -> list[dict]:
    out, seen = [], set()
    for _, r in cw[cw["uei"].str.strip() == ""].iterrows():
        for name in search_names(r):
            k = (name.lower(), r["state"])
            if k in seen:
                continue
            seen.add(k)
            out.append({"name": name, "state": r["state"]})
    return out


def uei_request(ueis: list[str], status: str | None = None) -> dict:
    p = {
        "ueiSAM": "[" + "~".join(ueis) + "]",
        "includeSections": SECTIONS,
        "page": "0",
        "size": str(BATCH),
    }
    if status:
        p["registrationStatus"] = status
    return {"kind": "uei" if not status else f"uei_status_{status}", "params": p, "ueis": ueis}


def name_request(name: str, state: str) -> dict:
    p = {
        "legalBusinessName": name,
        "physicalAddressProvinceOrStateCode": state,
        "includeSections": SECTIONS,
        "page": "0",
        "size": str(BATCH),
    }
    return {"kind": "name", "params": p, "name": name, "state": state}


def chunks(xs: list, n: int) -> list[list]:
    return [xs[i : i + n] for i in range(0, len(xs), n)]


def request_key(params: dict) -> str:
    s = json.dumps(params, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def build_plan(cw: pd.DataFrame, missing_after_step1: list[str] | None = None) -> list[dict]:
    """Requests in order: UEI batches, expired re-checks (if known), name lookups."""
    plan = [uei_request(c) for c in chunks(crosswalk_ueis(cw), BATCH)]
    if missing_after_step1:
        plan += [uei_request(c, "E") for c in chunks(missing_after_step1, BATCH)]
    plan += [name_request(n["name"], n["state"]) for n in name_lookups(cw)]
    for r in plan:
        r["key"] = request_key(r["params"])
    return plan


# --------------------------------------------------------------------------- cache


def cached_responses(raw_dir: Path | None = None) -> dict[str, Path]:
    """request key -> newest successful response file across date folders."""
    raw_dir = raw_dir or RAW_DIR
    out: dict[str, Path] = {}
    for p in sorted(raw_dir.glob("*/req_*.json")):
        meta = p.with_suffix(".meta.json")
        if meta.exists() and json.loads(meta.read_text()).get("http_status") == 200:
            out[p.stem.removeprefix("req_")] = p
    return out


def redacted_url(params: dict) -> str:
    return API + "?" + urllib.parse.urlencode(params, safe="[]~,")


def records(payload: dict) -> list[dict]:
    return payload.get("entityData") or []


def returned_ueis(payload: dict) -> set[str]:
    return {
        (e.get("entityRegistration") or {}).get("ueiSAM", "").upper()
        for e in records(payload)
        if (e.get("entityRegistration") or {}).get("ueiSAM")
    }


def missing_ueis(plan: list[dict], cache: dict[str, Path]) -> list[str] | None:
    """UEIs not returned by the step-1 batches; None until every batch is answered."""
    asked, got = [], set()
    for r in plan:
        if r["kind"] != "uei":
            continue
        if r["key"] not in cache:
            return None
        asked += r["ueis"]
        got |= returned_ueis(json.loads(cache[r["key"]].read_text()))
    return [u for u in asked if u not in got]


# --------------------------------------------------------------------------- fetch


def fetch(
    cw: pd.DataFrame, max_requests: int, key_header: bool, run_date: str, dry_run: bool = False
) -> int:
    api_key = os.environ.get("SAM_API_KEY", "")
    if not api_key and not dry_run:
        sys.exit("Set SAM_API_KEY (your personal SAM.gov API key).")
    import requests

    out_dir = RAW_DIR / run_date
    used = 0
    for _ in range(2):  # second pass adds expired re-checks once step 1 is complete
        cache = cached_responses()
        plan = build_plan(cw, missing_ueis(build_plan(cw), cache))
        todo = [r for r in plan if r["key"] not in cache]
        for r in todo:
            if used >= max_requests:
                print(
                    f"Stopped at --max-requests={max_requests}; {len(todo)} request(s) not yet"
                    " sent. Rerun later (tomorrow for a 10/day key)."
                )
                return used
            url = redacted_url(r["params"])
            print(f"[{r['kind']}] {url}")
            if dry_run:
                used += 1
                continue
            headers = {"Accept": "application/json"}
            if key_header:
                headers["x-api-key"] = api_key
                full = url
            else:  # brackets and tildes kept literal, as in the documented examples
                full = url + "&" + urllib.parse.urlencode({"api_key": api_key})
            resp = requests.get(full, headers=headers, timeout=60)
            used += 1
            out_dir.mkdir(parents=True, exist_ok=True)
            body_path = out_dir / f"req_{r['key']}.json"
            body_path.write_bytes(resp.content)
            retrieved = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            meta = {
                "http_status": resp.status_code,
                "kind": r["kind"],
                "url": url,
                "retrieved_utc": retrieved,
                "request": r["params"],
            }
            body_path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=1))
            n = None
            if resp.status_code == 200:
                try:
                    n = len(records(resp.json()))
                except ValueError:
                    meta["http_status"] = "invalid_json"
                    body_path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=1))
            append_manifest(
                [
                    {
                        "source_id": SOURCE_ID,
                        "url": url,
                        "retrieved_utc": retrieved,
                        "sha256": sha256(body_path),
                        "license": LICENSE_NOTE,
                        "notes": json.dumps(
                            {
                                "task": TASK,
                                "endpoint": API,
                                "kind": r["kind"],
                                "request": r["params"],
                                "http_status": resp.status_code,
                                "records": n,
                                "file": rel(body_path),
                                "doc": DOC_URL,
                            },
                            separators=(",", ":"),
                            sort_keys=True,
                        ),
                    }
                ]
            )
            if resp.status_code != 200:
                print(f"  HTTP {resp.status_code}: {resp.text[:300]}")
                if resp.status_code in (401, 403, 429):
                    print("  Stopping: key rejected or daily limit reached.")
                    return used
            time.sleep(1)
        if not todo:
            break
    print(f"Done: {used} request(s) sent; all planned requests answered.")
    return used


# --------------------------------------------------------------------------- process


def norm_status(s: str | None) -> str:
    s = (s or "").strip().lower()
    return {"a": "active", "e": "expired"}.get(s, s) or "unknown"


def flatten(e: dict) -> dict:
    reg = e.get("entityRegistration") or {}
    core = e.get("coreData") or {}
    addr = core.get("physicalAddress") or {}
    gen = core.get("generalInformation") or {}
    info = core.get("entityInformation") or {}
    return {
        "uei": (reg.get("ueiSAM") or "").upper(),
        "legal_business_name": reg.get("legalBusinessName"),
        "dba_name": reg.get("dbaName"),
        "registration_status": norm_status(reg.get("registrationStatus")),
        "registration_date": reg.get("registrationDate"),
        "activation_date": reg.get("activationDate"),
        "expiration_date": reg.get("registrationExpirationDate"),
        "last_update_date": reg.get("lastUpdateDate"),
        "purpose_of_registration": reg.get("purposeOfRegistrationDesc"),
        "entity_structure": gen.get("entityStructureDesc"),
        "division_name": info.get("entityDivisionName"),
        "city": addr.get("city"),
        "state": addr.get("stateOrProvinceCode"),
    }


def uei_status(
    cw: pd.DataFrame, plan: list[dict], cache: dict[str, Path], ents: pd.DataFrame
) -> pd.DataFrame:
    """One row per crosswalk UEI.

    sam_status: the registration status SAM returned (active / expired / other, lower case);
    ``none_found`` when neither the default query nor the expired re-check returned it;
    ``recheck_pending`` when the default query missed it and the re-check isn't answered yet;
    ``not_checked`` when its batch hasn't been sent.
    """
    asked_e = {u for r in plan if r["kind"].startswith("uei_status") for u in r["ueis"]}
    answered_1 = {u for r in plan if r["kind"] == "uei" and r["key"] in cache for u in r["ueis"]}
    answered_e = {
        u
        for r in plan
        if r["kind"].startswith("uei_status") and r["key"] in cache
        for u in r["ueis"]
    }
    found = ents.set_index("uei") if len(ents) else pd.DataFrame()
    e_meta = {}
    for r in plan:
        if r["kind"].startswith("uei_status") and r["key"] in cache:
            m = json.loads(cache[r["key"]].with_suffix(".meta.json").read_text())
            for u in r["ueis"]:
                e_meta[u] = (m["retrieved_utc"], rel(cache[r["key"]]))
    rows = []
    for u in crosswalk_ueis(cw):
        row = {"uei": u, "sam_status": "not_checked", "checked_utc": "", "source_file": ""}
        if u in found.index:
            rec = found.loc[u]
            row.update(
                sam_status=rec["registration_status"],
                checked_utc=rec["checked_utc"],
                source_file=rec["source_file"],
            )
        elif u in answered_e:
            row.update(sam_status="none_found", checked_utc=e_meta[u][0], source_file=e_meta[u][1])
        elif u in answered_1:
            row["sam_status"] = "recheck_pending" if u in asked_e or not asked_e else "none_found"
        rows.append(row)
    return pd.DataFrame(rows, columns=["uei", "sam_status", "checked_utc", "source_file"])


def process(cw: pd.DataFrame, out_dir: Path | None = None, raw_dir: Path | None = None) -> dict:
    out_dir = out_dir or OUT_DIR
    cache = cached_responses(raw_dir)
    plan = build_plan(cw, missing_ueis(build_plan(cw), cache) or [])
    ent, names, queries = [], [], []
    for r in plan:
        p = cache.get(r["key"])
        if p is None:
            continue
        meta = json.loads(p.with_suffix(".meta.json").read_text())
        if r["kind"] == "name":
            payload = json.loads(p.read_text())
            queries.append(
                {
                    "query_name": r["name"],
                    "query_state": r["state"],
                    "records": len(records(payload)),
                    "total_records": payload.get("totalRecords", ""),
                    "checked_utc": meta["retrieved_utc"],
                    "source_file": rel(p),
                }
            )
        for e in records(json.loads(p.read_text())):
            row = flatten(e) | {
                "query_kind": r["kind"],
                "checked_utc": meta["retrieved_utc"],
                "source_file": rel(p),
            }
            if r["kind"] == "name":
                names.append(row | {"query_name": r["name"], "query_state": r["state"]})
            else:
                ent.append(row)
    ents = pd.DataFrame(ent)
    if len(ents):  # prefer the step-1 answer for a UEI over the expired re-check
        ents = ents.sort_values("query_kind").drop_duplicates("uei", keep="first")
    status = uei_status(cw, plan, cache, ents)
    out_dir.mkdir(parents=True, exist_ok=True)
    ents.to_csv(out_dir / "sam_entities.csv", index=False)
    pd.DataFrame(
        names,
        columns=list(flatten({}).keys())
        + ["query_kind", "checked_utc", "source_file", "query_name", "query_state"],
    ).to_csv(out_dir / "sam_name_candidates.csv", index=False)
    pd.DataFrame(
        queries,
        columns=[
            "query_name",
            "query_state",
            "records",
            "total_records",
            "checked_utc",
            "source_file",
        ],
    ).to_csv(out_dir / "sam_name_queries.csv", index=False)
    status.to_csv(out_dir / "sam_status.csv", index=False)
    summary = {
        "ueis": len(status),
        "by_status": status["sam_status"].value_counts().to_dict() if len(status) else {},
        "name_candidates": len(names),
        "requests_answered": len(cache),
        "requests_planned": len(plan),
        "name_queries_with_more_than_one_page": [
            q["query_name"]
            for q in queries
            if str(q["total_records"]).isdigit() and int(q["total_records"]) > BATCH
        ],
    }
    (out_dir / "sam_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


# --------------------------------------------------------------------------- apply


def apply_status(
    cw: pd.DataFrame, status: pd.DataFrame, names: pd.DataFrame, queries: pd.DataFrame
) -> pd.DataFrame:
    """Fill sam_status / sam_checked_date / sam_source on crosswalk rows.

    Rows with UEIs get the primary UEI's status (other UEIs' statuses go in sam_source when they
    differ). Rows without a UEI get ``none_found`` if the name lookup returned nothing, or
    ``name_candidates_review`` if it returned candidates (never auto-assigned).
    """
    cw = cw.copy()
    for c in ("sam_status", "sam_checked_date", "sam_source"):
        if c not in cw:
            cw[c] = ""
    st = status.set_index("uei") if len(status) else pd.DataFrame()
    answered_names = {(q.query_name, q.query_state): q for q in queries.itertuples()}
    for i, r in cw.iterrows():
        ids = split_ids(r["uei"])
        if ids:
            if ids[0] not in st.index or st.loc[ids[0], "sam_status"] == "not_checked":
                continue
            s = st.loc[ids[0]]
            extra = [f"{u}={st.loc[u, 'sam_status']}" for u in ids[1:] if u in st.index]
            cw.at[i, "sam_status"] = s["sam_status"]
            cw.at[i, "sam_checked_date"] = str(s["checked_utc"])[:10]
            cw.at[i, "sam_source"] = (
                "SAM Entity API v3 "
                + str(s["source_file"])
                + (" ; other UEIs: " + ", ".join(extra) if extra else "")
            )
        else:
            qn = search_names(r)
            if (
                not qn
                or not answered_names
                or not all((n, r["state"]) in answered_names for n in qn)
            ):
                continue
            n_hit = 0
            if len(names):
                n_hit = int(
                    (names["query_name"].isin(qn) & (names["query_state"] == r["state"])).sum()
                )
            cw.at[i, "sam_status"] = "name_candidates_review" if n_hit else "none_found"
            cw.at[i, "sam_checked_date"] = str(answered_names[(qn[0], r["state"])].checked_utc)[:10]
            cw.at[i, "sam_source"] = (
                "SAM Entity API v3 legalBusinessName="
                + "|".join(qn)
                + f" state={r['state']}"
                + (
                    f" ({n_hit} candidate(s) in sam_name_candidates.csv;"
                    " pick by hand, never by name alone)"
                    if n_hit
                    else ""
                )
            )
    return cw


def apply(cw_path: Path | None = None, out_dir: Path | None = None) -> None:
    cw_path, out_dir = cw_path or CROSSWALK_PATH, out_dir or OUT_DIR
    cw = pd.read_csv(cw_path, dtype=str, keep_default_na=False)
    read = lambda f: pd.read_csv(out_dir / f, dtype=str, keep_default_na=False)
    new = apply_status(
        cw, read("sam_status.csv"), read("sam_name_candidates.csv"), read("sam_name_queries.csv")
    )
    new.to_csv(cw_path, index=False)
    print(new["sam_status"].value_counts().to_string())


# --------------------------------------------------------------------------- cli


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    f = sub.add_parser("fetch")
    f.add_argument("--max-requests", type=int, default=10)
    f.add_argument("--key-header", action="store_true", help="send the key as x-api-key")
    f.add_argument("--dry-run", action="store_true")
    sub.add_parser("process")
    sub.add_parser("apply")
    args = ap.parse_args(argv)
    cw = pd.read_csv(CROSSWALK_PATH, dtype=str, keep_default_na=False)
    if args.cmd == "plan":
        cache = cached_responses()
        plan = build_plan(cw, missing_ueis(build_plan(cw), cache))
        for r in plan:
            print(
                ("done " if r["key"] in cache else "todo ")
                + f"[{r['kind']}] "
                + redacted_url(r["params"])
            )
        print(
            f"{len(plan)} request(s) planned, {sum(r['key'] in cache for r in plan)} answered."
            " Expired re-checks are added once all UEI batches are answered."
        )
    elif args.cmd == "fetch":
        fetch(
            cw,
            args.max_requests,
            args.key_header,
            dt.datetime.now(dt.UTC).date().isoformat(),
            args.dry_run,
        )
    elif args.cmd == "process":
        print(json.dumps(process(cw), indent=2))
    elif args.cmd == "apply":
        apply()


if __name__ == "__main__":
    main()
