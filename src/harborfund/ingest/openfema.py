"""OpenFEMA HMA Subapplications v2: national snapshot and the T1.3 Pacific extract (task T2.5a).

    uv run python -m harborfund.ingest.openfema download     # full national file + catalog entry
    uv run python -m harborfund.ingest.openfema process      # -> data/processed/bric_pacific_subapplicants.csv
    uv run python -m harborfund.ingest.openfema all
    uv run python -m harborfund.ingest.openfema download --companions   # also the 3 linked datasets

`download` saves FEMA's full-file CSV of HmaSubapplications v2 (every program, status and
field; ~63.6k rows on 2026-11-18) to data/raw/openfema/<YYYY-MM-DD>/, plus the dataset's
OpenFEMA catalog entry (record count, lastRefresh, FEMA's own hash). It checks that the CSV
row count equals the catalog record count. `--companions` adds the linked tables
(financial transactions, congressional districts, project site inventories); they are not
needed for T2.5a.

`process` keeps CA/OR/WA BRIC and PDM subapplications (competitive and earmarked) and adds
`program_id` (inventory row), the subapplicant's coastal-county flags, and parsed amounts.

Program mapping (checked against the v2 data on 2026-11-18; see program_inventory_notes.md):
    "Building Resilient Infrastructure and Communities"           -> bric
    "Pre-Disaster Mitigation", fiscalYear <= 2019                  -> pdm_competitive
    "Pre-Disaster Mitigation", ID code PD and fiscalYear >= 2022   -> pdm_cpf   (FY2026 CDS
        round: FEMA GO records labelled plain "Pre-Disaster Mitigation")
    "Pre-Disaster Mitigation Congressionally Directed Spending"    -> pdm_cpf   (FY2022-24)
    "Legislative Pre-Disaster Mitigation"                          -> lpdm_legacy (FY2008-10
        earmarks; no inventory row)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

import pandas as pd

from harborfund import config
from harborfund.ingest.usaspending import (
    append_manifest,
    count_csv_rows,
    latest_date_dir,
    rel,
    sha256,
)

TASK = "T2.5a"
API = "https://www.fema.gov/api/open"
DATASET = "HmaSubapplications"
VERSION = 2
FULL_CSV = f"{API}/v{VERSION}/{DATASET}.csv"
CATALOG = f"{API}/v1/DataSets?$filter=name%20eq%20%27{DATASET}%27"
COMPANIONS = [
    "HmaSubapplicationsFinancialTransactions",
    "HmaSubapplicationsCongressionalDistricts",
    "HmaSubapplicationsProjectSiteInventories",
]
OUT_DIR = config.RAW_DIR / "openfema"
EXTRACT_PATH = config.PROCESSED_DIR / "bric_pacific_subapplicants.csv"
LICENSE_NOTE = "OpenFEMA; FEMA terms and citation requirements: https://www.fema.gov/about/openfema/terms-conditions"
STATES = ("CA", "OR", "WA")

BRIC = "Building Resilient Infrastructure and Communities"
PDM = "Pre-Disaster Mitigation"
PDM_CDS = "Pre-Disaster Mitigation Congressionally Directed Spending"
LPDM = "Legislative Pre-Disaster Mitigation"
BRIC_PDM_PROGRAMS = (BRIC, PDM, PDM_CDS, LPDM)
CPF_START = 2022  # pdm_cpf fy_start in program_inventory.csv

MONEY = [
    "federalShareAmount",
    "nonFederalShareAmount",
    "totalSubapplicationAmount",
    "totalObligatedAmount",
    "totalPaymentAmount",
    "selectionFederalShareAmount",
]


# --------------------------------------------------------------------------- download


def _session():
    import requests

    s = requests.Session()
    s.headers.update({"User-Agent": "harborfund (github.com/zajoseph/coastal-harbor-funding)"})
    return s


def _now() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stream(s, url: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    with s.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    tmp.replace(dest)


def catalog_entry(s, name: str) -> dict:
    url = f"{API}/v1/DataSets?$filter=name%20eq%20%27{name}%27"
    sets = s.get(url, timeout=60).json()["DataSets"]
    if not sets:
        raise RuntimeError(f"{name} is not in the OpenFEMA catalog")
    return max(sets, key=lambda d: d.get("version") or 0)


def download_one(s, name: str, version: int, d: Path, force: bool) -> dict:
    cat = catalog_entry(s, name)
    if cat.get("version") != version:
        print(f"note: catalog's latest {name} is v{cat.get('version')}, not v{version}")
    url = f"{API}/v{version}/{name}.csv"
    meta_path = d / f"{name}_v{version}_catalog.json"
    dest = d / f"{name}_v{version}.csv"
    if dest.exists() and not force:
        print(f"skip (exists): {rel(dest)}")
        return {}
    meta_path.write_text(json.dumps(cat, indent=2, sort_keys=True), encoding="utf-8")
    retrieved = _now()
    _stream(s, url, dest)
    rows = count_csv_rows(dest)
    expected = cat.get("recordCount")
    notes = {
        "task": TASK,
        "dataset": name,
        "version": version,
        "file": rel(dest),
        "bytes": dest.stat().st_size,
        "rows": rows,
        "catalog_record_count": expected,
        "catalog_last_refresh": cat.get("lastRefresh"),
        "catalog_last_dataset_refresh": cat.get("lastDataSetRefresh"),
        "catalog_hash": cat.get("hash"),
        "catalog_file": rel(meta_path),
        "data_dictionary": cat.get("dataDictionary"),
    }
    append_manifest(
        [
            {
                "source_id": "openfema",
                "url": url,
                "retrieved_utc": retrieved,
                "sha256": sha256(dest),
                "license": LICENSE_NOTE,
                "notes": json.dumps(notes, separators=(",", ":"), sort_keys=True),
            }
        ]
    )
    ok = "OK" if rows == expected else f"MISMATCH (catalog says {expected})"
    print(f"{name} v{version}: {rows:,} rows, {notes['bytes']:,} B -> {rel(dest)}  row check {ok}")
    if rows != expected:
        print("  The catalog count can lag the file; re-run with --force if it persists.")
    return notes


def download(run_date: str, force: bool, companions: bool, dry_run: bool) -> None:
    targets = [(DATASET, VERSION)] + ([(c, 1) for c in COMPANIONS] if companions else [])
    if dry_run:
        for n, v in targets:
            print(f"{API}/v{v}/{n}.csv")
        return
    d = OUT_DIR / run_date
    d.mkdir(parents=True, exist_ok=True)
    s = _session()
    for n, v in targets:
        download_one(s, n, v, d, force)


# --------------------------------------------------------------------------- process


def read_snapshot(run_date: str | None = None) -> pd.DataFrame:
    d = OUT_DIR / run_date if run_date else latest_date_dir(OUT_DIR)
    df = pd.read_csv(d / f"{DATASET}_v{VERSION}.csv", dtype=str, keep_default_na=False)
    df = df.replace({"": None})
    df["fiscalYear"] = pd.to_numeric(df["fiscalYear"], errors="coerce").astype("Int64")
    for c in MONEY:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df.attrs["snapshot_dir"] = rel(d)
    return df


def id_code(ident: pd.Series) -> pd.DataFrame:
    """Award-style parts of a FEMA GO subapplication ID, e.g. EMF-2020-BR-143-0016.

    eGrants/NEMIS IDs (PDMC-PJ-09-CA-2019-001, LPDM-..., DR-4308-0030-R) give blanks.
    """
    x = ident.fillna("").str.upper().str.extract(r"^(EM[A-Z])-(\d{4})-([A-Z]{2})-(\d+)")
    return pd.DataFrame(
        {
            "id_prefix": x[0].fillna(""),
            "id_round_fy": pd.to_numeric(x[1], errors="coerce").astype("Int64"),
            "id_code": x[2].fillna(""),
            "id_award": (x[0] + "-" + x[1] + "-" + x[2] + "-" + x[3]).fillna(""),
            "id_family": ident.fillna("").str.upper().str.extract(r"^([A-Z]+)")[0].fillna(""),
        },
        index=ident.index,
    )


def hma_program_id(df: pd.DataFrame) -> pd.Series:
    """Inventory program_id for BRIC/PDM rows; '' for other HMA programs."""
    prog = df["program"].fillna("")
    fy = df["fiscalYear"]
    code = id_code(df["subapplicationIdentifier"])["id_code"]
    out = pd.Series("", index=df.index, dtype="str")
    out[prog == BRIC] = "bric"
    out[(prog == PDM) & (fy <= 2019).fillna(False)] = "pdm_competitive"
    out[(prog == PDM) & (fy >= CPF_START).fillna(False) & (code == "PD")] = "pdm_cpf"
    out[(prog == PDM) & (out == "")] = "pdm_unclassified"
    out[prog == PDM_CDS] = "pdm_cpf"
    out[prog == LPDM] = "lpdm_legacy"
    return out


def _norm_county(name: str) -> str:
    n = name.upper().strip()
    n = re.sub(r"\b(COUNTY|PARISH|BOROUGH|CITY AND COUNTY OF)\b", "", n)
    return re.sub(r"[^A-Z]", "", n)


def load_coastal_counties() -> pd.DataFrame:
    c = pd.read_csv(config.REFERENCE_DIR / "coastal_counties.csv", dtype=str)
    c["key"] = c["county_name"].map(_norm_county)
    return c


def county_flags(df: pd.DataFrame, coastal: pd.DataFrame) -> pd.DataFrame:
    """Match `benefitingCounties` names (no state given) to coastal counties *in the
    subapplicant's state*. Names that don't match a coastal county in that state are kept
    in `counties_other` (they include inland counties and stray out-of-state names)."""
    lookup = {(r.state, r.key): r.county_fips for r in coastal.itertuples()}
    rows = []
    for st, raw in zip(df["subapplicantStateAbbreviation"], df["benefitingCounties"]):
        raw = raw if isinstance(raw, str) else ""
        names = [n.strip() for n in raw.split(";") if n.strip()]
        hit = [lookup[(st, _norm_county(n))] for n in names if (st, _norm_county(n)) in lookup]
        other = [n for n in names if (st, _norm_county(n)) not in lookup]
        rows.append(
            {
                "n_benefiting_counties": len(names),
                "coastal_county_fips": ";".join(dict.fromkeys(hit)),
                "counties_other": ";".join(other),
                "any_coastal_county": bool(hit),
            }
        )
    return pd.DataFrame(rows, index=df.index)


def zip_flags(df: pd.DataFrame, coastal: pd.DataFrame) -> pd.DataFrame | None:
    """Subapplicant ZIP -> county (Census ZCTA file from T1.1), if that file is on disk."""
    try:
        from harborfund.ingest.usaspending import load_zcta_county

        z = load_zcta_county()
    except (FileNotFoundError, OSError):
        return None
    zip5 = df["subapplicantZipCode"].fillna("").str.extract(r"(\d{5})")[0]
    m = pd.DataFrame({"zip5": zip5}, index=df.index).merge(z, on="zip5", how="left")
    m.index = df.index
    fips = set(coastal["county_fips"])
    return pd.DataFrame(
        {
            "zip_county_fips": m["county_geoid"],
            "zip_in_coastal_county": m["county_geoid"].isin(fips),
        },
        index=df.index,
    )


EXTRACT_COLS = [
    "subapplicationIdentifier",
    "program",
    "program_id",
    "fiscalYear",
    "id_award",
    "subapplicantName",
    "subapplicantUei",
    "subapplicantType",
    "subapplicantCity",
    "subapplicantStateAbbreviation",
    "subapplicantZipCode",
    "benefitingCounties",
    "subapplicationTitle",
    "subapplicationType",
    "fundingCategory",
    "primaryActivity",
    "status",
    "selectionStatus",
    "selectionFundingCategory",
    "dateSubmittedToFema",
    "totalSubapplicationAmount",
    "federalShareAmount",
    "selectionFederalShareAmount",
    "totalObligatedAmount",
    "totalPaymentAmount",
    "benefitCostRatio",
    "applicantName",
]


ID_COLS = ["id_prefix", "id_round_fy", "id_code", "id_award", "id_family"]


def _fresh(df: pd.DataFrame) -> pd.DataFrame:
    """Copy without derived columns, so helpers can take an already-annotated snapshot."""
    return df.drop(columns=[c for c in [*ID_COLS, "program_id"] if c in df.columns])


def pacific_extract(df: pd.DataFrame) -> pd.DataFrame:
    df = _fresh(df)
    df["program_id"] = hma_program_id(df)
    df = df[df["program"].isin(BRIC_PDM_PROGRAMS)]
    df = df[df["subapplicantStateAbbreviation"].isin(STATES)].copy()
    df = df.join(id_code(df["subapplicationIdentifier"])[["id_award"]])
    coastal = load_coastal_counties()
    out = df[[c for c in EXTRACT_COLS if c in df.columns]].join(county_flags(df, coastal))
    z = zip_flags(df, coastal)
    if z is not None:
        out = out.join(z)
    out["in_study_window"] = (out["fiscalYear"] >= config.STUDY_FY_START).fillna(False)
    out["has_uei"] = out["subapplicantUei"].notna()
    out["has_title"] = out["subapplicationTitle"].notna()
    return out.sort_values(["program_id", "fiscalYear", "subapplicationIdentifier"])


def crosscheck_award_ids(prime: pd.DataFrame, snap: pd.DataFrame) -> pd.DataFrame:
    """Test T1.1's 97.047 rule (FEMA award-ID code -> program) against OpenFEMA.

    `prime` is a USAspending Assistance_PrimeAwardSummaries table (T1.1's national 97.047
    pull). FEMA GO award IDs (EMx-YYYY-CC-...) can be joined to OpenFEMA subapplication IDs,
    either exactly or on the first four parts. eGrants-era awards (most `PC` and pre-2020
    `PD`) cannot be joined; they come back with `of_program_id` blank.
    """
    from harborfund.ingest.usaspending import fema_award_parts

    p = prime.copy()
    p = p.join(fema_award_parts(p["award_id_fain"].fillna("")))
    s = _fresh(snap)
    s["program_id"] = hma_program_id(s)
    s = s.join(id_code(s["subapplicationIdentifier"]))
    exact = s.assign(k=s["subapplicationIdentifier"].str.upper()).set_index("k")["program_id"]
    exact = exact[~exact.index.duplicated()]
    award = (
        s[s["id_award"] != ""]
        .groupby("id_award")["program_id"]
        .agg(lambda v: "|".join(sorted(set(v))))
    )
    fain = p["award_id_fain"].fillna("").str.upper()
    four = fain.str.extract(r"^(EM[A-Z]-\d{4}-[A-Z]{2}-\d+)")[0]
    p["of_program_id"] = fain.map(exact).fillna(fain.map(award)).fillna(four.map(award))
    p["of_join"] = "none"
    p.loc[fain.isin(exact.index), "of_join"] = "exact"
    p.loc[
        (p["of_join"] == "none") & (fain.map(award).notna() | four.map(award).notna()), "of_join"
    ] = "award_prefix"
    t11 = {"BR": "bric", "PC": "pdm_competitive"}
    rnd = p["fema_round_fy"]
    p["t11_program_id"] = p["fema_program_code"].map(t11).fillna("other_97047")
    is_pd = p["fema_program_code"] == "PD"
    p.loc[is_pd & (rnd >= CPF_START).fillna(False), "t11_program_id"] = "pdm_cpf"
    p.loc[is_pd & ~(rnd >= CPF_START).fillna(False), "t11_program_id"] = "pdm_other"
    p["agrees"] = (p["of_program_id"] == p["t11_program_id"]).where(p["of_join"] != "none")
    return p


def process(run_date: str | None) -> pd.DataFrame:
    df = read_snapshot(run_date)
    out = pacific_extract(df)
    EXTRACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(EXTRACT_PATH, index=False)
    summary = (
        out.groupby(["program_id", "subapplicantStateAbbreviation"])
        .agg(
            rows=("program_id", "size"),
            coastal=("any_coastal_county", "sum"),
            with_uei=("has_uei", "sum"),
        )
        .reset_index()
    )
    print(f"snapshot {df.attrs['snapshot_dir']}: {len(df):,} rows")
    print(f"wrote {rel(EXTRACT_PATH)}: {len(out):,} rows")
    print(summary.to_string(index=False))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m harborfund.ingest.openfema")
    ap.add_argument("step", choices=["download", "process", "all"])
    ap.add_argument(
        "--date", default=None, help="Run folder date (download: today UTC; process: latest)"
    )
    ap.add_argument("--force", action="store_true", help="Re-download if the file exists")
    ap.add_argument("--companions", action="store_true", help="Also download the linked HMA tables")
    ap.add_argument("--dry-run", action="store_true", help="Print URLs only")
    a = ap.parse_args(argv)
    if a.step in ("download", "all"):
        run_date = a.date or dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
        download(run_date, a.force, a.companions, a.dry_run)
        if a.dry_run:
            return 0
        a.date = run_date
    if a.step in ("process", "all"):
        process(a.date)
    return 0


if __name__ == "__main__":
    sys.exit(main())
