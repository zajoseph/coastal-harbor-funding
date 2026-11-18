"""Offline tests for the T2.5a ingest helpers (no network)."""

import pandas as pd

from harborfund.ingest import applicants, openfema


def _rows():
    # Shapes copied from real HmaSubapplications v2 records (2026-11-18).
    return pd.DataFrame(
        {
            "subapplicationIdentifier": [
                "EMF-2020-BR-143-0016",
                "PDMC-PJ-09-CA-2015-003",
                "EMS-2026-PD-001-0001",
                "LPDM-PJ-10-OR-2024-001",
                "LPDM-PJ-09-CA-2010-002",
                "DR-4308-0030-R",
                "EMT-2022-FM-003-0017",
            ],
            "program": [
                openfema.BRIC,
                openfema.PDM,
                openfema.PDM,
                openfema.PDM_CDS,
                openfema.LPDM,
                "Hazard Mitigation Grant Program",
                "Flood Mitigation Assistance",
            ],
            "fiscalYear": pd.array([2020, 2015, 2026, 2024, 2010, 2017, 2022], dtype="Int64"),
            "subapplicantStateAbbreviation": ["CA", "CA", "WA", "OR", "CA", "CA", "TX"],
            "benefitingCounties": [
                "Humboldt",
                None,
                None,
                "CLATSOP; WARREN",
                "SAN MATEO; PLEASANTS",
                "Inyo",
                None,
            ],
            "subapplicantZipCode": ["95501", "95060", "98569", "97146", None, None, None],
        }
    )


def test_program_mapping():
    pid = openfema.hma_program_id(_rows())
    assert pid.tolist() == [
        "bric",
        "pdm_competitive",
        "pdm_cpf",
        "pdm_cpf",
        "lpdm_legacy",
        "",
        "",
    ]


def test_id_code():
    x = openfema.id_code(_rows()["subapplicationIdentifier"])
    assert x.loc[0, "id_code"] == "BR" and x.loc[0, "id_round_fy"] == 2020
    assert x.loc[0, "id_award"] == "EMF-2020-BR-143"
    assert x.loc[1, "id_code"] == "" and x.loc[1, "id_family"] == "PDMC"


def test_county_flags_state_scoped():
    coastal = openfema.load_coastal_counties()
    f = openfema.county_flags(_rows(), coastal)
    assert f.loc[0, "any_coastal_county"]  # Humboldt, CA
    assert f.loc[3, "any_coastal_county"]  # Clatsop, OR
    assert f.loc[3, "counties_other"] == "WARREN"  # stray out-of-state name kept aside
    assert f.loc[4, "any_coastal_county"]  # San Mateo, CA
    assert not f.loc[5, "any_coastal_county"]  # Inyo is inland
    assert f.loc[1, "n_benefiting_counties"] == 0


def test_pacific_extract_filters():
    df = _rows()
    for c in ["subapplicantName", "subapplicantUei", "subapplicationTitle", "status"]:
        df[c] = None
    out = openfema.pacific_extract(df)
    assert set(out["program_id"]) == {"bric", "pdm_competitive", "pdm_cpf", "lpdm_legacy"}
    assert "TX" not in set(out["subapplicantStateAbbreviation"])


def test_applicant_file_list():
    names = [f.name for f in applicants.FILES]
    assert len(names) == len(set(names))
    assert {"pidp_fy19_26", "tiger2009_build2025", "infra_fy26", "fastlane_fy16"} <= set(names)
    for f in applicants.FILES:
        assert f.url.startswith("https://")
        assert f.url.rsplit(".", 1)[-1].lower() in {"xlsx", "pdf"}
    assert applicants.filename(applicants.FILES[0].url) == "FY19-26 PIDP Eligible Applicants.xlsx"


def test_page_last_updated():
    html = '<div class="x">Last updated: Tuesday, October 27, 2026</div>'
    assert applicants.page_last_updated(html) == "Tuesday, October 27, 2026"
