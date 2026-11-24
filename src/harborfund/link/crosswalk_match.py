"""Match USAspending awards and OpenFEMA subapplicants to pilot harbors (T1.3).

Matching follows the settled rule: the harbor-entity crosswalk is the only
harbor<->entity link. For each award:

1. UEI: the award's recipient UEI is looked up among the crosswalk UEIs
   (cells split on ``;``).
2. Legacy DUNS: only if no UEI matched, the recipient DUNS is looked up among
   the crosswalk DUNS (9 digits, leading zeros kept).
3. Location check: the matched entity's harbor state and county are compared
   with the award's recipient and place-of-performance counties. Every
   disagreement is flagged, never resolved silently.

An award is **auto-matched** only when exactly one harbor matches and the
location check agrees. ID matches that fail the location check, or that hit
more than one harbor, are ``flagged`` for manual review. The ID-only result is
kept alongside so the effect of the location gate can be measured.

Four crosswalk versions (kickoff step 4):

- ``own_op``: owner and operator rows, all confidence levels
- ``own_op_nolow``: owner and operator rows, ``low`` confidence dropped
- ``own_op_parent``: plus ``parent_government`` rows, all confidence levels
- ``own_op_parent_nolow``: plus ``parent_government`` rows, ``low`` dropped

Run::

    uv run python -m harborfund.link.crosswalk_match [--version own_op_parent]

Writes ``data/processed/match_pilot/`` (not committed): the review universe,
the match result for every version, and the subapplicant matches. Match rates
are measured against the hand-coded truth set in notebook 04, before overrides.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from harborfund import config

CROSSWALK_PATH = config.REFERENCE_DIR / "harbor_entity_crosswalk.csv"
TRUTH_PATH = config.REFERENCE_DIR / "award_harbor_truth_pilot.csv"
OVERRIDES_PATH = config.REFERENCE_DIR / "award_harbor_overrides.csv"
PILOT_DIR = config.PROCESSED_DIR / "usaspending_pilot"
SUBAPP_PATH = config.PROCESSED_DIR / "bric_pacific_subapplicants.csv"
OUT_DIR = config.PROCESSED_DIR / "match_pilot"

VERSIONS: dict[str, dict] = {
    "own_op": {"roles": {"owner", "operator"}, "drop_low": False},
    "own_op_nolow": {"roles": {"owner", "operator"}, "drop_low": True},
    "own_op_parent": {"roles": {"owner", "operator", "parent_government"}, "drop_low": False},
    "own_op_parent_nolow": {
        "roles": {"owner", "operator", "parent_government"},
        "drop_low": True,
    },
}
PRIMARY_VERSION = "own_op_parent"


# --- Identifiers ------------------------------------------------------------


def norm_uei(s: pd.Series) -> pd.Series:
    """Upper-case, trimmed UEI; empty -> <NA>."""
    out = s.astype("string").str.strip().str.upper()
    return out.where(out.str.len() > 0)


def norm_duns(s: pd.Series) -> pd.Series:
    """9-digit DUNS with leading zeros; non-numeric or empty -> <NA>."""
    out = s.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    out = out.where(out.str.fullmatch(r"\d{1,9}").fillna(False))
    return out.str.zfill(9)


def load_crosswalk(path: Path | None = None) -> pd.DataFrame:
    """Crosswalk rows as read (all strings)."""
    return pd.read_csv(path or CROSSWALK_PATH, dtype=str, keep_default_na=False)


def crosswalk_ids(cw: pd.DataFrame, version: str | None = None) -> pd.DataFrame:
    """Long table: one row per crosswalk row x identifier.

    Columns: harbor_id, state, county_fips, entity_name, entity_role,
    entity_type, match_confidence, id_type ('uei' | 'duns'), id_value, cw_row.
    ``version`` filters rows by role and confidence (None = all rows).
    """
    cw = cw.reset_index(drop=True).copy()
    cw["cw_row"] = cw.index
    if version is not None:
        v = VERSIONS[version]
        keep = cw["entity_role"].isin(v["roles"])
        if v["drop_low"]:
            keep &= cw["match_confidence"] != "low"
        cw = cw[keep]
    keep_cols = [
        "harbor_id",
        "state",
        "county_fips",
        "entity_name",
        "entity_role",
        "entity_type",
        "match_confidence",
        "cw_row",
    ]
    parts = []
    for id_type, col, norm in (("uei", "uei", norm_uei), ("duns", "legacy_duns", norm_duns)):
        x = cw[keep_cols + [col]].copy()
        x[col] = x[col].str.split(";")
        x = x.explode(col)
        x["id_value"] = norm(x[col])
        x["id_type"] = id_type
        parts.append(x.drop(columns=[col]).dropna(subset=["id_value"]))
    return pd.concat(parts, ignore_index=True)


# --- Award tables -----------------------------------------------------------

UNIFIED_COLS = [
    "award_id",
    "award_source",
    "program_id",
    "fy",
    "amount_nominal",
    "recipient_name",
    "uei",
    "duns",
    "recipient_state",
    "recipient_county",
    "pop_state",
    "pop_county",
    "pop_city",
    "description",
    "harbor_kw_flag",
    "earmark_candidate_year",
    "geo_match_basis",
    "prime_award_id",
]


def _bool(s: pd.Series) -> pd.Series:
    return s.astype("string").str.lower().map({"true": True, "false": False}).fillna(False)


def unify_primes(p: pd.DataFrame) -> pd.DataFrame:
    """USAspending prime awards in the common shape."""
    return pd.DataFrame(
        {
            "award_id": p["award_id_fain"].fillna(p["award_id_uri"]),
            "award_source": "prime",
            "program_id": p["program_id"],
            "fy": pd.to_numeric(p["fy"], errors="coerce").astype("Int64"),
            "amount_nominal": pd.to_numeric(p["total_obligated_nominal"], errors="coerce"),
            "recipient_name": p["recipient_name"],
            "uei": norm_uei(p["recipient_uei"]),
            "duns": norm_duns(p["recipient_duns"]),
            "recipient_state": p["recipient_state"],
            "recipient_county": p["recipient_county_geoid"],
            "pop_state": p["pop_state"],
            "pop_county": p["pop_county_geoid"],
            "pop_city": p["primary_place_of_performance_city_name"],
            "description": p["prime_award_base_transaction_description"],
            "harbor_kw_flag": _bool(p["harbor_kw_flag"]),
            "earmark_candidate_year": _bool(p["earmark_candidate_year"]),
            "geo_match_basis": p["geo_match_basis"],
            "prime_award_id": pd.NA,
        }
    )


def unify_subawards(s: pd.DataFrame) -> pd.DataFrame:
    """FFATA subawards in the common shape. award_id = prime FAIN|subaward no.|SAM report id."""
    return pd.DataFrame(
        {
            "award_id": (
                s["prime_award_fain"].fillna("")
                + "|"
                + s["subaward_number"].fillna("")
                + "|"
                + s["subaward_sam_report_id"].fillna("")
            ),
            "award_source": "subaward",
            "program_id": s["program_id"],
            "fy": pd.to_numeric(s["fy"], errors="coerce").astype("Int64"),
            "amount_nominal": pd.to_numeric(s["subaward_amount_nominal"], errors="coerce"),
            "recipient_name": s["subawardee_name"],
            "uei": norm_uei(s["subawardee_uei"]),
            "duns": norm_duns(s["subawardee_duns"]),
            "recipient_state": s["recipient_state"],
            "recipient_county": s["recipient_county_geoid"],
            "pop_state": s["pop_state"],
            "pop_county": s["pop_county_geoid"],
            "pop_city": s["subaward_primary_place_of_performance_city_name"],
            "description": s["subaward_description"],
            "harbor_kw_flag": _bool(s["harbor_kw_flag"]),
            "earmark_candidate_year": _bool(s["earmark_candidate_year"]),
            "geo_match_basis": s["geo_match_basis"],
            "prime_award_id": s["prime_award_fain"],
        }
    )


def flag_duplicate_subaward_reports(s: pd.DataFrame) -> pd.Series:
    """True for FFATA rows that repeat an earlier row exactly.

    Same prime, subaward number, subawardee, amount and action date. These
    are double reports (T1.1: subaward totals can be double-reported).
    """
    key = [
        "prime_award_fain",
        "subaward_number",
        "subawardee_name",
        "subaward_amount",
        "subaward_action_date",
    ]
    return s.duplicated(subset=key, keep="first")


def sample_counties(cw: pd.DataFrame) -> set[str]:
    return set(cw["county_fips"]) - {""}


def review_universe(
    primes: pd.DataFrame, subawards: pd.DataFrame, counties: set[str]
) -> pd.DataFrame:
    """In-scope primes (in FY window) and in-scope subawards in the sample counties.

    Exact duplicate FFATA reports are dropped (counted in ``dropped_duplicates``
    attribute of the returned frame).
    """
    p = primes[_bool(primes["in_scope"]) & _bool(primes["in_fy_window"])]
    p = p[p["recipient_county_geoid"].isin(counties) | p["pop_county_geoid"].isin(counties)]
    s = subawards[_bool(subawards["in_scope"])]
    s = s[s["recipient_county_geoid"].isin(counties) | s["pop_county_geoid"].isin(counties)]
    dup = flag_duplicate_subaward_reports(s)
    u = pd.concat([unify_primes(p), unify_subawards(s[~dup])], ignore_index=True)
    u.attrs["dropped_duplicates"] = int(dup.sum())
    return u[UNIFIED_COLS]


def unify_subapplicants(sa: pd.DataFrame) -> pd.DataFrame:
    """OpenFEMA BRIC/PDM subapplicants in the common shape (no DUNS in the source)."""
    counties = sa["coastal_county_fips"].fillna("").astype("string")
    return pd.DataFrame(
        {
            "award_id": sa["subapplicationIdentifier"],
            "award_source": "subapplicant",
            "program_id": sa["program_id"],
            "fy": pd.to_numeric(sa["fiscalYear"], errors="coerce").astype("Int64"),
            "amount_nominal": pd.to_numeric(sa["federalShareAmount"], errors="coerce"),
            "recipient_name": sa["subapplicantName"],
            "uei": norm_uei(sa["subapplicantUei"]),
            "duns": pd.Series(pd.NA, index=sa.index, dtype="string"),
            "recipient_state": sa["subapplicantStateAbbreviation"],
            "recipient_county": sa["zip_county_fips"].astype("string"),
            "pop_state": sa["subapplicantStateAbbreviation"],
            # benefiting counties may list several; kept as a ;-list
            "pop_county": counties,
            "pop_city": sa["subapplicantCity"],
            "description": sa["subapplicationTitle"],
            "harbor_kw_flag": False,
            "earmark_candidate_year": False,
            "geo_match_basis": pd.NA,
            "prime_award_id": sa["id_award"],
            "status": sa["status"],
            "selection_status": sa["selectionStatus"],
        }
    )


def subapplicant_universe(sa: pd.DataFrame, counties: set[str]) -> pd.DataFrame:
    """FY2010+ subapplicants whose benefiting or ZIP county is a sample county.

    ``in_study_window`` is recomputed as fiscalYear >= STUDY_FY_START (same
    rule as harborfund.ingest.openfema) because older extracts lack the column.
    """
    fy = pd.to_numeric(sa["fiscalYear"], errors="coerce")
    sa = sa[fy >= config.STUDY_FY_START]
    ben = sa["coastal_county_fips"].fillna("").astype(str).str.split(r"[;,]\s*", regex=True)
    hit = ben.map(lambda xs: bool({x.strip() for x in xs} & counties))
    hit |= sa["zip_county_fips"].astype(str).isin(counties)
    return unify_subapplicants(sa[hit]).reset_index(drop=True)


# --- Matching ---------------------------------------------------------------


def _county_set(v) -> set[str]:
    if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NA:
        return set()
    return {x.strip() for x in str(v).replace(",", ";").split(";") if x.strip()}


def geo_check(row: pd.Series, harbor_state: str, harbor_county: str) -> str:
    """'agree' | 'state_only' | 'disagree' | 'no_location'."""
    counties = _county_set(row["recipient_county"]) | _county_set(row["pop_county"])
    states = {s for s in (row["recipient_state"], row["pop_state"]) if isinstance(s, str) and s}
    if not counties and not states:
        return "no_location"
    if harbor_county in counties:
        return "agree"
    if harbor_state in states:
        return "state_only"
    return "disagree"


def match_awards(awards: pd.DataFrame, ids: pd.DataFrame) -> pd.DataFrame:
    """Add match columns to ``awards``.

    id_basis ('uei' | 'duns' | 'none'), id_harbors (;-list), id_entities,
    id_roles, id_confidence, n_id_harbors, id_harbor_id (single harbor or <NA>),
    geo (check against id_harbor_id), match_status ('auto' | 'flagged_geo' |
    'flagged_multi' | 'none'), auto_harbor_id, geo_flag_detail.
    """
    uei_ix = ids[ids["id_type"] == "uei"].groupby("id_value")
    duns_ix = ids[ids["id_type"] == "duns"].groupby("id_value")
    uei_keys, duns_keys = set(uei_ix.groups), set(duns_ix.groups)

    rows = []
    for _, a in awards.iterrows():
        hits, basis = None, "none"
        if isinstance(a["uei"], str) and a["uei"] in uei_keys:
            hits, basis = uei_ix.get_group(a["uei"]), "uei"
        elif isinstance(a["duns"], str) and a["duns"] in duns_keys:
            hits, basis = duns_ix.get_group(a["duns"]), "duns"
        rec = {"id_basis": basis}
        if hits is None:
            rec.update(
                id_harbors=pd.NA,
                id_entities=pd.NA,
                id_roles=pd.NA,
                id_confidence=pd.NA,
                n_id_harbors=0,
                id_harbor_id=pd.NA,
                geo=pd.NA,
                match_status="none",
                auto_harbor_id=pd.NA,
                geo_flag_detail=pd.NA,
            )
            rows.append(rec)
            continue
        hits = hits.drop_duplicates("cw_row")
        harbors = sorted(hits["harbor_id"].unique())
        rec.update(
            id_harbors=";".join(harbors),
            id_entities=";".join(hits["entity_name"].unique()),
            id_roles=";".join(sorted(hits["entity_role"].unique())),
            id_confidence=";".join(sorted(hits["match_confidence"].unique())),
            n_id_harbors=len(harbors),
        )
        if len(harbors) > 1:
            rec.update(
                id_harbor_id=pd.NA,
                geo=pd.NA,
                match_status="flagged_multi",
                auto_harbor_id=pd.NA,
                geo_flag_detail="entity in several harbors",
            )
        else:
            h = hits.iloc[0]
            g = geo_check(a, h["state"], h["county_fips"])
            ok = g == "agree"
            rec.update(
                id_harbor_id=harbors[0],
                geo=g,
                match_status="auto" if ok else "flagged_geo",
                auto_harbor_id=harbors[0] if ok else pd.NA,
                geo_flag_detail=pd.NA
                if ok
                else (
                    f"harbor {h['state']}/{h['county_fips']} vs recipient "
                    f"{a['recipient_state']}/{a['recipient_county']}, "
                    f"pop {a['pop_state']}/{a['pop_county']}"
                ),
            )
        rows.append(rec)
    return pd.concat([awards.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def match_all_versions(awards: pd.DataFrame, cw: pd.DataFrame) -> pd.DataFrame:
    """Long table: match result for every version (column ``version``)."""
    out = []
    for v in VERSIONS:
        m = match_awards(awards, crosswalk_ids(cw, v))
        m.insert(0, "version", v)
        out.append(m)
    return pd.concat(out, ignore_index=True)


# --- Scoring against the truth set -----------------------------------------


def score(matches: pd.DataFrame, truth: pd.DataFrame, gate_geo: bool = True) -> pd.Series:
    """Recall and precision of auto-matching against the truth set.

    truth columns: award_id, award_source, label ('sample_harbor' |
    'other_harbor' | 'not_harbor' | 'unclear'), harbor_id.
    Recall = share of sample_harbor awards whose assigned harbor equals the
    true harbor (count and dollars). Precision = share of assigned awards
    whose harbor is correct. ``gate_geo=False`` scores the ID-only assignment.
    Unclear awards are excluded from both and counted separately.
    """
    col = "auto_harbor_id" if gate_geo else "id_harbor_id"
    m = matches.drop(columns=["label", "true_harbor_id"], errors="ignore").merge(
        truth[["award_id", "award_source", "label", "harbor_id"]].rename(
            columns={"harbor_id": "true_harbor_id"}
        ),
        on=["award_id", "award_source"],
        how="left",
        validate="one_to_one",
    )
    if m["label"].isna().any():
        missing = m.loc[m["label"].isna(), "award_id"].head(5).tolist()
        raise ValueError(f"awards without a truth label, e.g. {missing}")
    amt = m["amount_nominal"].fillna(0)
    pos = m["label"] == "sample_harbor"
    assigned = m[col].notna() & (m["label"] != "unclear")
    correct = m[col].notna() & (m[col] == m["true_harbor_id"])
    return pd.Series(
        {
            "n_truth_sample": int(pos.sum()),
            "usd_truth_sample": float(amt[pos].sum()),
            "n_correct": int((pos & correct).sum()),
            "usd_correct": float(amt[pos & correct].sum()),
            "recall_n": (pos & correct).sum() / pos.sum() if pos.sum() else float("nan"),
            "recall_usd": amt[pos & correct].sum() / amt[pos].sum()
            if amt[pos].sum()
            else float("nan"),
            "n_assigned": int(assigned.sum()),
            "usd_assigned": float(amt[assigned].sum()),
            "precision_n": (assigned & correct).sum() / assigned.sum()
            if assigned.sum()
            else float("nan"),
            "precision_usd": (
                amt[assigned & correct].sum() / amt[assigned].sum()
                if amt[assigned].sum()
                else float("nan")
            ),
            "n_unclear": int((m["label"] == "unclear").sum()),
        }
    )


# Owner-type stratum of each pilot harbor, as in the T1.2 sample table
# (harbor_entity_crosswalk_notes.md, "Sample selection rule").
OWNER_TYPE: dict[str, str] = {
    "CA-humboldt-bay": "mixed/private",
    "CA-crescent-city": "port/harbor district",
    "CA-trinidad": "tribal",
    "CA-san-diego-bay": "port/harbor district",
    "CA-los-angeles-long-beach": "city (incl. port dept)",
    "CA-morro-bay": "city (incl. port dept)",
    "CA-santa-cruz": "port/harbor district",
    "CA-channel-islands": "county",
    "CA-dana-point": "county",
    "CA-huntington-harbour": "mixed/private",
    "OR-newport": "port/harbor district",
    "OR-charleston": "port/harbor district",
    "OR-winchester-bay": "county",
    "OR-depoe-bay": "city (incl. port dept)",
    "OR-warrenton": "city (incl. port dept)",
    "WA-westport": "port/harbor district",
    "WA-la-conner": "port/harbor district",
    "WA-la-push": "tribal",
    "WA-seattle": "port/harbor district",
    "WA-bay-center": "port/harbor district",
}


def apply_truth_view(truth: pd.DataFrame, view: str = "site") -> pd.DataFrame:
    """Truth labels under a harbor-attribution view.

    ``site`` (primary): only projects at the named sample harbor count.
    ``owner``: harbor-related projects at a sample owner's other facilities
    (scope ``sample_owner_other_facility``) also count for that owner's harbor.
    The owner's harbor is taken from the crosswalk via ``owner_harbor_id``.
    """
    t = truth.copy()
    if view == "owner":
        m = t["scope"] == "sample_owner_other_facility"
        t.loc[m, "label"] = "sample_harbor"
        t.loc[m, "harbor_id"] = t.loc[m, "owner_harbor_id"]
    elif view != "site":
        raise ValueError(view)
    return t


def score_by(
    matches: pd.DataFrame, truth: pd.DataFrame, by: str, gate_geo: bool = True
) -> pd.DataFrame:
    """``score`` within groups of a column present in ``matches``."""
    out = {}
    for k, g in matches.groupby(by, dropna=False):
        ids = g[["award_id", "award_source"]]
        t = truth.merge(ids, on=["award_id", "award_source"])
        out[k] = score(g, t, gate_geo=gate_geo)
    return pd.DataFrame(out).T


def apply_overrides(matches: pd.DataFrame, overrides: pd.DataFrame) -> pd.DataFrame:
    """Final harbor after manual overrides (``final_harbor_id``).

    Overrides with action ``assign`` set the harbor; ``unassign`` clears it.
    Auto-match rates are always measured before this step.
    """
    m = matches.copy()
    m["final_harbor_id"] = m["auto_harbor_id"]
    o = overrides.set_index(["award_id", "award_source"])
    for (aid, src), r in o.iterrows():
        sel = (m["award_id"] == aid) & (m["award_source"] == src)
        m.loc[sel, "final_harbor_id"] = r["harbor_id"] if r["action"] == "assign" else pd.NA
    return m


# --- Main -------------------------------------------------------------------


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    primes = pd.read_csv(PILOT_DIR / "prime_awards.csv", dtype=str, low_memory=False)
    subs = pd.read_csv(PILOT_DIR / "subawards.csv", dtype=str, low_memory=False)
    sa = pd.read_csv(SUBAPP_PATH, dtype=str, low_memory=False)
    cw = load_crosswalk()
    return primes, subs, sa, cw


def run(out_dir: Path | None = None) -> dict:
    out_dir = out_dir or OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    primes, subs, sa, cw = load_inputs()
    counties = sample_counties(cw)
    uni = review_universe(primes, subs, counties)
    sau = subapplicant_universe(sa, counties)
    uni.to_csv(out_dir / "review_universe.csv", index=False)
    awards_m = match_all_versions(uni, cw)
    awards_m.to_csv(out_dir / "award_matches.csv", index=False)
    sa_m = match_all_versions(sau, cw)
    sa_m.to_csv(out_dir / "subapplicant_matches.csv", index=False)
    summary = {
        "sample_counties": len(counties),
        "review_universe": {
            "n": len(uni),
            "usd_nominal": round(float(uni["amount_nominal"].sum()), 2),
            "by_source": uni["award_source"].value_counts().to_dict(),
            "dropped_duplicate_subaward_reports": uni.attrs.get("dropped_duplicates", 0),
        },
        "subapplicant_universe": {"n": len(sau)},
        "match_status": {
            v: awards_m.loc[awards_m["version"] == v, "match_status"].value_counts().to_dict()
            for v in VERSIONS
        },
    }
    (out_dir / "match_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args(argv)
    print(json.dumps(run(args.out_dir), indent=2))


if __name__ == "__main__":
    main()
