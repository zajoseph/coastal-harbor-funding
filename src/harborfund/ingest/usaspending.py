"""USAspending award pull for the T1.1 pilot (PIDP, BRIC, EDA in coastal CA/OR/WA).

Two steps, both driven by a TOML config (default: usaspending_pilot.toml next to this file):

    uv run python -m harborfund.ingest.usaspending download   # raw zips -> data/raw/usaspending/<date>/
    uv run python -m harborfund.ingest.usaspending process    # raw -> data/processed/usaspending_pilot/
    uv run python -m harborfund.ingest.usaspending all        # both
    uv run python -m harborfund.ingest.usaspending download --dry-run   # print requests, no network

`download` asks the USAspending custom download API for one national file per
Assistance Listing (ALN): prime award summaries, prime transactions and FFATA
subawards in one zip (POST /api/v2/download/search/). If that endpoint refuses
the request, it falls back to /api/v2/download/awards/ plus
/api/v2/download/transactions/. It also fetches the Census 2020 ZCTA-to-county
relationship file, which is used to give subawards a county. Every file is logged
in data/manifest.csv. A download that has already finished for that date is skipped
unless --force is given.

`process` keeps rows with any tie to the configured states and adds flag columns:
coastal-county match (recipient or place of performance), state-level BRIC primes,
program_id (separating earmark candidates sharing an ALN), earmark text flags,
the inventory's harbor keyword filter, UEI presence and EDA revolving-loan flags.
Nothing is dropped for being "not harbor-related". Amounts stay nominal.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import sys
import time
import tomllib
import zipfile
from pathlib import Path

import pandas as pd

from harborfund import config

API_BASE = "https://api.usaspending.gov"
SEARCH_ENDPOINT = "/api/v2/download/search/"
AWARDS_ENDPOINT = "/api/v2/download/awards/"
TRANSACTIONS_ENDPOINT = "/api/v2/download/transactions/"
SOURCE_ID = "usaspending"
LICENSE_NOTE = "U.S. federal spending data from USAspending.gov; terms of use not checked"
DEFAULT_CONFIG = Path(__file__).with_name("usaspending_pilot.toml")
OUT_SUBDIR = "usaspending_pilot"

STATE_FIPS = {
    "01": "AL",
    "02": "AK",
    "04": "AZ",
    "05": "AR",
    "06": "CA",
    "08": "CO",
    "09": "CT",
    "10": "DE",
    "11": "DC",
    "12": "FL",
    "13": "GA",
    "15": "HI",
    "16": "ID",
    "17": "IL",
    "18": "IN",
    "19": "IA",
    "20": "KS",
    "21": "KY",
    "22": "LA",
    "23": "ME",
    "24": "MD",
    "25": "MA",
    "26": "MI",
    "27": "MN",
    "28": "MS",
    "29": "MO",
    "30": "MT",
    "31": "NE",
    "32": "NV",
    "33": "NH",
    "34": "NJ",
    "35": "NM",
    "36": "NY",
    "37": "NC",
    "38": "ND",
    "39": "OH",
    "40": "OK",
    "41": "OR",
    "42": "PA",
    "44": "RI",
    "45": "SC",
    "46": "SD",
    "47": "TN",
    "48": "TX",
    "49": "UT",
    "50": "VT",
    "51": "VA",
    "53": "WA",
    "54": "WV",
    "55": "WI",
    "56": "WY",
    "60": "AS",
    "66": "GU",
    "69": "MP",
    "72": "PR",
    "78": "VI",
}

# Text patterns used for flags (case-insensitive). These are heuristics for the pilot;
# the definitive earmark tags come from the appropriations CPF/CDS tables (T2.4).
CPF_RE = r"community project|congressionally directed|\bcpf\b|\bcds\b|earmark"
PDM_RE = r"pre[- ]?disaster mitigation|\bpdm\b"
BRIC_RE = r"\bbric\b|building resilient infrastructure"
RLF_RE = r"revolving loan|\brlf\b"
ALN_RE = r"\d{2}\.\d{3}"
STATE_GOV_RE = r"state government|^a$|^a,|,a,|,a$"

DROP_COL_RE = re.compile(r"highly_compensated_officer", re.IGNORECASE)


# --------------------------------------------------------------------------- config


def load_config(path: Path | None = None) -> dict:
    path = Path(path) if path else DEFAULT_CONFIG
    with path.open("rb") as f:
        cfg = tomllib.load(f)
    cfg["_path"] = str(path)
    return cfg


def load_inventory(path: Path | None = None) -> pd.DataFrame:
    path = Path(path) if path else config.PROGRAM_INVENTORY_PATH
    inv = pd.read_csv(path, dtype=str).fillna("")
    return inv.set_index("program_id", drop=False)


def inventory_fy_start(
    inv: pd.DataFrame, program_id: str, default: int | None = None
) -> int | None:
    if program_id in inv.index and inv.at[program_id, "fy_start"].strip():
        return int(float(inv.at[program_id, "fy_start"]))
    return default


def download_window(dl: dict, cfg: dict, inv: pd.DataFrame) -> tuple[int, int]:
    """Fiscal years to request for one download block."""
    pull = cfg["pull"]
    if "fy_start" in dl:
        start = int(dl["fy_start"])
    else:
        starts = [inventory_fy_start(inv, p) for p in dl["program_ids"]]
        starts = [s for s in starts if s is not None]
        start = max(pull["fy_start"], min(starts)) if starts else pull["fy_start"]
    return start, int(dl.get("fy_end", pull["fy_end"]))


def fy_date_range(fy_start: int, fy_end: int) -> tuple[str, str]:
    return f"{fy_start - 1}-10-01", f"{fy_end}-09-30"


def build_filters(aln: str, fy_start: int, fy_end: int, award_type_codes: list[str]) -> dict:
    start, end = fy_date_range(fy_start, fy_end)
    return {
        "program_numbers": [aln],
        "award_type_codes": list(award_type_codes),
        "time_period": [{"start_date": start, "end_date": end}],
    }


def request_plan(filters: dict) -> dict:
    """Primary request and fallback requests for one ALN."""
    return {
        "primary": [
            (
                "search",
                SEARCH_ENDPOINT,
                {
                    "filters": filters,
                    "spending_level": ["awards", "transactions", "subawards"],
                    "file_format": "csv",
                },
            )
        ],
        "fallback": [
            ("awards", AWARDS_ENDPOINT, {"filters": filters, "file_format": "csv"}),
            ("transactions", TRANSACTIONS_ENDPOINT, {"filters": filters, "file_format": "csv"}),
        ],
    }


# --------------------------------------------------------------------------- manifest


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_csv_rows(path: Path) -> int:
    """Data rows (records, not lines: fields can contain newlines)."""
    with path.open(newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        next(reader, None)
        return sum(1 for _ in reader)


def append_manifest(rows: list[dict], manifest: Path | None = None) -> None:
    manifest = Path(manifest) if manifest else config.MANIFEST_PATH
    fields = ["source_id", "url", "retrieved_utc", "sha256", "license", "notes"]
    new = not manifest.exists() or manifest.stat().st_size == 0
    with manifest.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def manifest_row(
    path: Path, url: str, retrieved: str, notes: dict, source_id: str = SOURCE_ID
) -> dict:
    return {
        "source_id": source_id,
        "url": url,
        "retrieved_utc": retrieved,
        "sha256": sha256(path),
        "license": LICENSE_NOTE,
        "notes": json.dumps(notes, separators=(",", ":"), sort_keys=True),
    }


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(config.ROOT))
    except ValueError:
        return str(path)


# --------------------------------------------------------------------------- download


def _session():
    import requests  # imported here so `process` and the tests don't need it

    s = requests.Session()
    s.headers.update({"User-Agent": "harborfund (github.com/zajoseph/coastal-harbor-funding)"})
    return s


def _abs(url: str) -> str:
    return url if url.startswith("http") else API_BASE + url


def start_and_wait(session, endpoint: str, body: dict, poll: int, max_wait_min: float) -> dict:
    r = session.post(API_BASE + endpoint, json=body, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"POST {endpoint} -> HTTP {r.status_code}: {r.text[:500]}")
    job = r.json()
    status_url = _abs(job["status_url"])
    deadline = time.monotonic() + max_wait_min * 60
    while True:
        st = session.get(status_url, timeout=60).json()
        state = st.get("status")
        print(f"    {job['file_name']}: {state} (rows so far: {st.get('total_rows')})", flush=True)
        if state == "finished":
            st["_job"] = job
            return st
        if state == "failed":
            raise RuntimeError(f"Download failed: {st.get('message')}")
        if time.monotonic() > deadline:
            raise TimeoutError(f"Gave up waiting for {job['file_name']} after {max_wait_min} min")
        time.sleep(poll)


def fetch_file(session, url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with session.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    tmp.replace(dest)


def run_one_request(
    session, label, endpoint, body, out_dir: Path, pull_cfg: dict, meta: dict
) -> list[dict]:
    """Request, wait, fetch, unzip and describe one download. Returns manifest rows."""
    st = start_and_wait(
        session, endpoint, body, pull_cfg["poll_seconds"], pull_cfg["max_wait_minutes"]
    )
    url = _abs(st.get("file_url") or st["_job"]["file_url"])
    retrieved = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    zpath = out_dir / Path(url).name
    print(f"    fetching {url}", flush=True)
    fetch_file(session, url, zpath)

    base = {
        **meta,
        "endpoint": API_BASE + endpoint,
        "request": body,
        "request_label": label,
        "api_total_rows": st.get("total_rows"),
    }
    rows = [manifest_row(zpath, url, retrieved, {**base, "file": rel(zpath), "kind": "zip"})]
    with zipfile.ZipFile(zpath) as z:
        members = [m for m in z.namelist() if not m.endswith("/")]
        z.extractall(out_dir / zpath.stem)
    for m in members:
        p = out_dir / zpath.stem / m
        n = count_csv_rows(p) if p.suffix.lower() == ".csv" else None
        rows.append(
            manifest_row(
                p, f"{url}#{m}", retrieved, {**base, "file": rel(p), "kind": "member", "rows": n}
            )
        )
        print(f"      {m}: {n} rows", flush=True)
    return rows


def download(cfg: dict, run_date: str, only: list[str] | None, force: bool, dry_run: bool) -> None:
    inv = load_inventory()
    pull = cfg["pull"]
    run_dir = config.RAW_DIR / SOURCE_ID / run_date
    session = None if dry_run else _session()

    for dl in cfg["downloads"]:
        if only and dl["name"] not in only:
            continue
        fy0, fy1 = download_window(dl, cfg, inv)
        filters = build_filters(dl["aln"], fy0, fy1, pull["award_type_codes"])
        plan = request_plan(filters)
        out_dir = run_dir / dl["name"]
        done = out_dir / "_DONE"
        print(f"[{dl['name']}] ALN {dl['aln']} FY{fy0}-FY{fy1} -> {rel(out_dir)}")
        if dry_run:
            print(json.dumps(plan["primary"][0][2], indent=2))
            continue
        if done.exists() and not force:
            print("  already downloaded; skipping (use --force to redo)")
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "task": "T1.1",
            "download": dl["name"],
            "aln": dl["aln"],
            "program_ids": dl["program_ids"],
            "fy_start": fy0,
            "fy_end": fy1,
            "config": rel(Path(cfg["_path"])),
        }
        rows: list[dict] = []
        try:
            for label, ep, body in plan["primary"]:
                rows += run_one_request(session, label, ep, body, out_dir, pull, meta)
        except RuntimeError as e:
            print(
                f"  search download refused ({e}); falling back to awards + transactions",
                flush=True,
            )
            rows = []
            for label, ep, body in plan["fallback"]:
                rows += run_one_request(session, label, ep, body, out_dir, pull, meta)
        append_manifest(rows)
        done.write_text(json.dumps({"finished_utc": rows[0]["retrieved_utc"], "files": len(rows)}))

    if not only or "zcta_county" in only:
        download_zcta(cfg, run_date, force, dry_run, session)


def download_zcta(cfg: dict, run_date: str, force: bool, dry_run: bool, session) -> None:
    url = cfg["zcta_county"]["url"]
    dest = config.RAW_DIR / "census" / run_date / Path(url).name
    print(f"[zcta_county] {url} -> {rel(dest)}")
    if dry_run:
        return
    if dest.exists() and not force:
        print("  already downloaded; skipping")
        return
    fetch_file(session, url, dest)
    retrieved = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with dest.open(encoding="utf-8-sig") as f:
        n = sum(1 for _ in f) - 1
    append_manifest(
        [
            manifest_row(
                dest,
                url,
                retrieved,
                {
                    "task": "T1.1",
                    "file": rel(dest),
                    "rows": n,
                    "delimiter": "|",
                    "use": "ZCTA->county for USAspending subawards",
                },
                source_id="census_zcta_county_2020",
            )
        ]
    )
    print(f"  {n} rows")


# --------------------------------------------------------------------------- process helpers


def latest_date_dir(parent: Path) -> Path:
    dirs = sorted(
        p for p in parent.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name)
    )
    if not dirs:
        raise FileNotFoundError(f"No dated run folders in {parent}")
    return dirs[-1]


def read_kind(dl_dir: Path, kind: str) -> pd.DataFrame:
    """Read all assistance CSVs of one kind (PrimeAwardSummaries / PrimeTransactions / Subawards)."""
    files = sorted(
        p
        for p in dl_dir.rglob("*.csv")
        if kind.lower() in p.name.lower() and not p.name.lower().startswith("contract")
    )
    if not files:
        return pd.DataFrame()
    parts = []
    for f in files:
        d = pd.read_csv(f, dtype=str, low_memory=False)
        d = d.drop(columns=[c for c in d.columns if DROP_COL_RE.search(c)])
        parts.append(d)
    df = pd.concat(parts, ignore_index=True)
    # The fallback path downloads subawards twice (with awards and with transactions).
    df = df.drop_duplicates(ignore_index=True)
    df.attrs["source_files"] = [rel(f) for f in files]
    return df


def col(df: pd.DataFrame, *names: str) -> pd.Series:
    """First existing column among names, as stripped strings ('' when missing)."""
    for n in names:
        if n in df.columns:
            return df[n].fillna("").astype(str).str.strip()
    return pd.Series("", index=df.index, dtype="str")


def norm_county_geoid(county: pd.Series, state_fips: pd.Series) -> pd.Series:
    """5-digit county GEOID from a county FIPS column that may be 3- or 5-digit."""
    c = county.str.replace(r"\D", "", regex=True)
    s = state_fips.str.replace(r"\D", "", regex=True).str.zfill(2)
    out = c.where(c.str.len() == 5, "")
    short = (c.str.len().between(1, 3)) & (s != "00")
    out = out.mask(short, s + c.str.zfill(3))
    return out


def state_from_geoid(geoid: pd.Series) -> pd.Series:
    return geoid.str[:2].map(STATE_FIPS).fillna("")


def text_flag(text: pd.Series, pattern: str) -> pd.Series:
    return text.str.contains(pattern, case=False, regex=True, na=False)


def harbor_regex(inv: pd.DataFrame, program_id: str) -> str | None:
    """Keyword regex from the inventory's harbor_relevance_filter; None means 'all' (port program)."""
    if program_id not in inv.index:
        return ""
    rule = inv.at[program_id, "harbor_relevance_filter"].strip()
    if rule.lower().startswith("all"):
        return None
    m = re.search(r"\(([^()]*\|[^()]*)\)", rule)
    return m.group(1) if m else ""


def load_counties(cfg: dict) -> pd.DataFrame:
    return pd.read_csv(config.ROOT / cfg["geography"]["counties_csv"], dtype=str)


def load_zcta_county(run_date: str | None = None) -> pd.DataFrame:
    parent = config.RAW_DIR / "census"
    d = parent / run_date if run_date and (parent / run_date).exists() else latest_date_dir(parent)
    f = d / "tab20_zcta520_county20_natl.txt"
    z = pd.read_csv(f, sep="|", dtype=str, encoding="utf-8-sig")
    return zcta_to_county(z)


def zcta_to_county(z: pd.DataFrame) -> pd.DataFrame:
    """One county per ZCTA (largest land-area overlap), with a multi-county flag."""
    z = z[z["GEOID_ZCTA5_20"].notna() & z["GEOID_COUNTY_20"].notna()].copy()
    z["land"] = pd.to_numeric(z["AREALAND_PART"], errors="coerce").fillna(0)
    n = z.groupby("GEOID_ZCTA5_20")["GEOID_COUNTY_20"].transform("nunique")
    z["zcta_multi_county"] = n > 1
    z = z.sort_values(["GEOID_ZCTA5_20", "land"], ascending=[True, False])
    best = z.drop_duplicates("GEOID_ZCTA5_20")
    return best.rename(columns={"GEOID_ZCTA5_20": "zip5", "GEOID_COUNTY_20": "county_geoid"})[
        ["zip5", "county_geoid", "zcta_multi_county"]
    ]


# --------------------------------------------------------------------------- classify


def fema_award_parts(fain: pd.Series) -> pd.DataFrame:
    """Round year and program code from FEMA award IDs, e.g. EMS-2022-PD-0002 -> 2022, PD.

    Codes seen in the 97.047 pull: BR = BRIC, PC = PDM competitive, PD = PDM (from FY2022
    the congressionally directed awards; before FY2020 used for older state PDM awards).
    """
    x = fain.str.upper().str.extract(r"^EM[A-Z]-(\d{4})-([A-Z]{2})")
    return pd.DataFrame(
        {
            "fema_round_fy": pd.to_numeric(x[0], errors="coerce").astype("Int64"),
            "fema_program_code": x[1].fillna(""),
        },
        index=fain.index,
    )


def marad_fon_family(fon: pd.Series) -> pd.Series:
    """Group 20.823 funding opportunity numbers (spelling varies: MA-PID-22-001, MAPID22001)."""
    f = fon.str.upper().str.replace(r"[^A-Z0-9]", "", regex=True)
    fam = pd.Series("other", index=fon.index, dtype="str")
    fam[f == ""] = "blank"
    fam[f.str.match(r"^MAPID\d{2}0*01$")] = "MA-PID-" + f.str.extract(r"^MAPID(\d{2})")[0].fillna(
        ""
    )
    fam[f.str.match(r"^693JF7\d{2}BAA")] = "MARAD BAA 20" + f.str.extract(r"^693JF7(\d{2})")[
        0
    ].fillna("")
    fam[f.str.startswith("DTOS59")] = "DOT BUILD"
    fam[f.str.startswith("NSMFHP")] = "DOT INFRA"
    return fam


def classify(
    df: pd.DataFrame,
    aln: str,
    fy: pd.Series,
    text: pd.Series,
    inv: pd.DataFrame,
    fain: pd.Series | None = None,
    fon: pd.Series | None = None,
) -> pd.DataFrame:
    """Add program_id, program_basis, earmark and harbor flags. Never drops rows.

    97.047 uses the FEMA award ID (program code + round year); descriptions are
    unreliable (PDM earmark awards are often described as BRIC). 20.823 uses the
    funding opportunity family. Earmark tags here are candidates; T2.4's CPF/CDS
    tables are the definitive source.
    """
    out = pd.DataFrame(index=df.index)
    fain = fain if fain is not None else pd.Series("", index=df.index, dtype="str")
    fon = fon if fon is not None else pd.Series("", index=df.index, dtype="str")
    cpf = text_flag(text, CPF_RE)
    out["earmark_text_flag"] = cpf

    if aln == "20.823":
        cpf_start = inventory_fy_start(inv, "pidp_cpf", 2024)
        fam = marad_fon_family(fon)
        amhp = text_flag(text, r"\bamhp\b|marine highway")
        out["fon_family"] = fam
        out["program_id"] = "pidp"
        out["program_basis"] = "fon:" + fam
        other = fam.isin(["DOT BUILD", "DOT INFRA", "other"]) | amhp
        out.loc[other, "program_id"] = "other_20823"
        out.loc[amhp, "program_basis"] = "text:AMHP"
        out.loc[cpf, ["program_id", "program_basis"]] = ["pidp_cpf", "text:CPF"]
        out["earmark_candidate_year"] = fy >= cpf_start
        out["earmark_flag"] = cpf
    elif aln == "97.047":
        parts = fema_award_parts(fain)
        out = out.join(parts)
        code, rnd = parts["fema_program_code"], parts["fema_round_fy"]
        cpf_start = inventory_fy_start(inv, "pdm_cpf", 2022)
        pdm_cpf = ((code == "PD") & (rnd >= cpf_start)).fillna(False) | cpf
        out["program_id"] = "other_97047"
        out["program_basis"] = "fain:" + code.where(code != "", "?")
        out.loc[code == "BR", "program_id"] = "bric"
        out.loc[code == "PC", "program_id"] = "pdm_competitive"
        out.loc[(code == "PD") & ~pdm_cpf, "program_id"] = "pdm_other"
        out.loc[pdm_cpf, "program_id"] = "pdm_cpf"
        # no FEMA ID: fall back to text
        nofain = code == ""
        out.loc[nofain & text_flag(text, BRIC_RE), ["program_id", "program_basis"]] = [
            "bric",
            "text:BRIC",
        ]
        out.loc[nofain & text_flag(text, PDM_RE), ["program_id", "program_basis"]] = [
            "pdm_other",
            "text:PDM",
        ]
        out["earmark_candidate_year"] = (rnd >= cpf_start).fillna(False)
        out["earmark_flag"] = pdm_cpf
    else:
        pid = {"11.300": "eda_public_works", "11.307": "eda_eaa"}.get(aln, f"aln_{aln}")
        out["program_id"] = pid
        out["program_basis"] = "aln"
        out["earmark_candidate_year"] = False
        out["earmark_flag"] = cpf
        out["eda_rlf_flag"] = text_flag(text, RLF_RE)

    out["harbor_kw_flag"] = False
    out["harbor_rule"] = ""
    for pid in out["program_id"].unique():
        m = out["program_id"] == pid
        rx = harbor_regex(inv, pid)
        if rx is None:
            out.loc[m, "harbor_kw_flag"] = True
            out.loc[m, "harbor_rule"] = "all (port program)"
        elif rx:
            out.loc[m, "harbor_kw_flag"] = text_flag(text[m], whole_words(rx))
            out.loc[m, "harbor_rule"] = "keyword"
        else:
            out.loc[m, "harbor_rule"] = "no rule in inventory"
    return out


def whole_words(rx: str) -> str:
    """Anchor inventory keywords at word starts and allow simple endings.

    'port' then matches port/ports but not support/transportation/opportunity;
    stems such as 'dredg' still match dredge/dredging.
    """
    return r"\b(?:" + rx + r")(?:s|es|e|ed|ing)?\b"


def geo_flags(
    rec_geoid: pd.Series,
    pop_geoid: pd.Series,
    rec_state: pd.Series,
    pop_state: pd.Series,
    counties: set[str],
    states: set[str],
) -> pd.DataFrame:
    out = pd.DataFrame(index=rec_geoid.index)
    out["recipient_county_geoid"] = rec_geoid
    out["pop_county_geoid"] = pop_geoid
    out["recipient_state"] = rec_state
    out["pop_state"] = pop_state
    r = rec_geoid.isin(counties)
    p = pop_geoid.isin(counties)
    out["recipient_in_coastal_county"] = r
    out["pop_in_coastal_county"] = p
    out["in_coastal_county"] = r | p
    out["geo_match_basis"] = ""
    out.loc[r & p, "geo_match_basis"] = "both"
    out.loc[r & ~p, "geo_match_basis"] = "recipient"
    out.loc[~r & p, "geo_match_basis"] = "pop"
    out["in_states"] = rec_state.isin(states) | pop_state.isin(states)
    return out


def _fy_from_date(dates: pd.Series) -> pd.Series:
    d = pd.to_datetime(dates, errors="coerce")
    fy = d.dt.year + (d.dt.month >= config.FISCAL_YEAR_START_MONTH).astype("Int64")
    return fy.astype("Int64")


def _int(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").astype("Int64")


def process_prime(
    df: pd.DataFrame,
    level: str,
    aln: str,
    fy_window: tuple[int, int],
    cfg: dict,
    inv: pd.DataFrame,
    counties: set[str],
) -> pd.DataFrame:
    """level = 'award' (PrimeAwardSummaries) or 'transaction' (PrimeTransactions)."""
    if df.empty:
        return df
    states = set(cfg["geography"]["states"])
    aln_text = col(df, "cfda_numbers_and_titles", "cfda_number")
    df = df[aln_text.str.contains(re.escape(aln), regex=True)].copy()
    if df.empty:
        return df
    pre = "prime_award_summary" if level == "award" else "prime_award_transaction"
    rec_sf = col(df, f"{pre}_recipient_state_fips_code", "recipient_location_state_fips")
    pop_sf = col(df, f"{pre}_place_of_performance_state_fips_code", "pop_state_fips")
    rec = norm_county_geoid(col(df, f"{pre}_recipient_county_fips_code"), rec_sf)
    pop = norm_county_geoid(
        col(df, f"{pre}_place_of_performance_county_fips_code", "pop_county_fips"), pop_sf
    )
    rec_state = col(df, "recipient_state_code").where(
        lambda s: s != "", rec_sf.str.zfill(2).map(STATE_FIPS).fillna("")
    )
    pop_state = pop_sf.str.zfill(2).map(STATE_FIPS).fillna("")
    pop_state = pop_state.where(pop_state != "", col(df, "primary_place_of_performance_state_code"))
    g = geo_flags(rec, pop, rec_state, pop_state, counties, states)

    if level == "award":
        date = col(df, "award_base_action_date")
        fy = _int(col(df, "award_base_action_date_fiscal_year"))
        amount = pd.to_numeric(col(df, "total_obligated_amount"), errors="coerce")
        amount_name = "total_obligated_nominal"
    else:
        date = col(df, "action_date")
        fy = _int(col(df, "action_date_fiscal_year"))
        amount = pd.to_numeric(col(df, "federal_action_obligation"), errors="coerce")
        amount_name = "federal_action_obligation_nominal"
    fy = fy.fillna(_fy_from_date(date))

    text = (
        col(df, "prime_award_base_transaction_description")
        + " | "
        + col(df, "transaction_description")
        + " | "
        + col(df, "funding_opportunity_goals_text")
    )
    c = classify(
        df,
        aln,
        fy,
        text,
        inv,
        fain=col(df, "award_id_fain"),
        fon=col(df, "funding_opportunity_number"),
    )

    out = pd.DataFrame(index=df.index)
    out["aln"] = aln
    out["level"] = level
    out["fy"] = fy
    out["in_fy_window"] = fy.between(*fy_window)
    out[amount_name] = amount
    out["has_uei"] = col(df, "recipient_uei") != ""
    out["has_duns"] = col(df, "recipient_duns") != ""
    out["recipient_is_state_gov"] = text_flag(
        col(df, "business_types_description"), r"state government"
    ) | text_flag(col(df, "business_types_code"), STATE_GOV_RE)
    state_level = aln in set(cfg["geography"].get("state_level_primes", []))
    out["state_level_prime"] = state_level
    res = pd.concat([out, g, c, df], axis=1)
    # State-level scope only for state-government primes; other primes (tribes,
    # universities, local governments) need a coastal-county match like everyone else.
    res["in_scope"] = res["in_coastal_county"] | (
        state_level & res["in_states"] & res["recipient_is_state_gov"]
    )
    return res[res["in_states"] | res["in_coastal_county"]].reset_index(drop=True)


def process_subawards(
    df: pd.DataFrame,
    aln: str,
    fy_window: tuple[int, int],
    cfg: dict,
    inv: pd.DataFrame,
    counties: set[str],
    zc: pd.DataFrame,
    prime_fon: dict | None = None,
) -> pd.DataFrame:
    """prime_fon maps prime_award_unique_key -> funding opportunity number (subaward files lack it)."""
    if df.empty:
        return df
    states = set(cfg["geography"]["states"])
    df = df[
        col(df, "prime_award_cfda_numbers_and_titles").str.contains(re.escape(aln), regex=True)
    ].copy()
    if df.empty:
        return df
    zmap = zc.set_index("zip5")
    sub_zip = col(df, "subawardee_zip_code").str.replace(r"\D", "", regex=True).str[:5]
    pop_zip = col(df, "sub_place_of_performance_zip").str.replace(r"\D", "", regex=True).str[:5]
    rec = sub_zip.map(zmap["county_geoid"]).fillna("")
    pop = pop_zip.map(zmap["county_geoid"]).fillna("")
    rec_state = col(df, "subawardee_state_code")
    pop_state = col(
        df, "sub_place_of_perform_state_code", "subaward_primary_place_of_performance_state_code"
    )
    g = geo_flags(rec, pop, rec_state, pop_state, counties, states)
    g["county_from"] = "zip5->zcta (largest land share)"
    g["zip_multi_county"] = sub_zip.map(zmap["zcta_multi_county"]).fillna(False).astype(
        bool
    ) | pop_zip.map(zmap["zcta_multi_county"]).fillna(False).astype(bool)
    g["zip_unmatched"] = ((sub_zip != "") & (rec == "")) | ((pop_zip != "") & (pop == ""))

    fy = _int(col(df, "subaward_action_date_fiscal_year")).fillna(
        _fy_from_date(col(df, "subaward_action_date"))
    )
    text = (
        col(df, "prime_award_base_transaction_description")
        + " | "
        + col(df, "subaward_description")
    )
    fon = col(df, "prime_award_unique_key").map(prime_fon or {}).fillna("")
    c = classify(df, aln, fy, text, inv, fain=col(df, "prime_award_fain"), fon=fon)

    out = pd.DataFrame(index=df.index)
    out["aln"] = aln
    out["level"] = "subaward"
    out["fy"] = fy
    out["in_fy_window"] = fy.between(*fy_window)
    out["subaward_amount_nominal"] = pd.to_numeric(col(df, "subaward_amount"), errors="coerce")
    out["has_uei"] = col(df, "subawardee_uei") != ""
    out["has_duns"] = col(df, "subawardee_duns") != ""
    out["prime_recipient_is_state_gov"] = text_flag(
        col(df, "prime_awardee_business_types"), r"state government"
    )
    res = pd.concat([out, g, c, df], axis=1)
    res["in_scope"] = res["in_coastal_county"]
    return res[res["in_states"] | res["in_coastal_county"]].reset_index(drop=True)


def process(cfg: dict, run_date: str | None) -> dict:
    inv = load_inventory()
    if "pidp_cpf" not in inv.index:
        print(
            "WARNING: program_inventory.csv has no pidp_cpf row (PR #3 not merged?). "
            "Using FY2024 as the PIDP earmark start.",
            file=sys.stderr,
        )
    counties = set(load_counties(cfg)["county_fips"])
    raw_parent = config.RAW_DIR / SOURCE_ID
    run_dir = raw_parent / run_date if run_date else latest_date_dir(raw_parent)
    zc = load_zcta_county(run_dir.name)
    out_dir = config.PROCESSED_DIR / OUT_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)

    frames = {"prime_awards": [], "prime_transactions": [], "subawards": []}
    log = {
        "raw_run": rel(run_dir),
        "processed_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "config": rel(Path(cfg["_path"])),
        "downloads": {},
    }
    for dl in cfg["downloads"]:
        dl_dir = run_dir / dl["name"]
        if not dl_dir.exists():
            print(f"[{dl['name']}] no raw folder in {rel(run_dir)}; skipped")
            continue
        window = download_window(dl, cfg, inv)
        a_raw = read_kind(dl_dir, "PrimeAwardSummaries")
        t_raw = read_kind(dl_dir, "PrimeTransactions")
        s_raw = read_kind(dl_dir, "Subawards")
        a = process_prime(a_raw, "award", dl["aln"], window, cfg, inv, counties)
        t = process_prime(t_raw, "transaction", dl["aln"], window, cfg, inv, counties)
        prime_fon = (
            dict(
                zip(
                    a_raw["assistance_award_unique_key"],
                    a_raw["funding_opportunity_number"].fillna(""),
                )
            )
            if {"assistance_award_unique_key", "funding_opportunity_number"} <= set(a_raw.columns)
            else {}
        )
        s = process_subawards(s_raw, dl["aln"], window, cfg, inv, counties, zc, prime_fon)
        frames["prime_awards"].append(a)
        frames["prime_transactions"].append(t)
        frames["subawards"].append(s)
        log["downloads"][dl["name"]] = {
            "source_files": a_raw.attrs.get("source_files", [])
            + t_raw.attrs.get("source_files", [])
            + s_raw.attrs.get("source_files", []),
            "raw_rows": {
                "prime_awards": len(a_raw),
                "prime_transactions": len(t_raw),
                "subawards": len(s_raw),
            },
            "kept_rows_in_states": {
                "prime_awards": len(a),
                "prime_transactions": len(t),
                "subawards": len(s),
            },
            "in_scope_rows": {
                k: int(v["in_scope"].sum()) if len(v) else 0
                for k, v in (("prime_awards", a), ("prime_transactions", t), ("subawards", s))
            },
        }
        print(f"[{dl['name']}] {log['downloads'][dl['name']]}")

    for name, parts in frames.items():
        parts = [p for p in parts if len(p)]
        df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
        path = out_dir / f"{name}.csv"
        df.to_csv(path, index=False)
        log[name] = {"file": rel(path), "rows": len(df)}
    (out_dir / "process_log.json").write_text(json.dumps(log, indent=2, default=str))
    print(f"Wrote {rel(out_dir)}")
    return log


# --------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m harborfund.ingest.usaspending", description=__doc__.split("\n")[0]
    )
    ap.add_argument("step", choices=["download", "process", "all"])
    ap.add_argument(
        "--config", type=Path, default=None, help="TOML config (default: usaspending_pilot.toml)"
    )
    ap.add_argument(
        "--date",
        default=None,
        help="Run folder date YYYY-MM-DD (download: default today UTC; process: default latest)",
    )
    ap.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Download names to run (e.g. aln_20.823 zcta_county)",
    )
    ap.add_argument(
        "--force", action="store_true", help="Re-download even if a finished download exists"
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="Print the requests without calling the API"
    )
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    if args.step in ("download", "all"):
        run_date = args.date or dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
        download(cfg, run_date, args.only, args.force, args.dry_run)
        if args.dry_run:
            return 0
        if args.step == "all":
            args.date = run_date
    if args.step in ("process", "all"):
        process(cfg, args.date)
    return 0


if __name__ == "__main__":
    sys.exit(main())
