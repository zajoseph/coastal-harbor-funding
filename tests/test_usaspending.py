"""Offline tests for harborfund.ingest.usaspending (no network, synthetic files)."""

import json

import pandas as pd
import pytest

from harborfund import config
from harborfund.ingest import usaspending as us


@pytest.fixture
def cfg():
    return us.load_config()


@pytest.fixture
def inv():
    rows = [
        {
            "program_id": "pidp",
            "fy_start": "2019",
            "harbor_relevance_filter": "all (port program); split later",
        },
        {
            "program_id": "pidp_cpf",
            "fy_start": "2024",
            "harbor_relevance_filter": "all (port program)",
        },
        {
            "program_id": "bric",
            "fy_start": "2020",
            "harbor_relevance_filter": "crosswalk, or keyword regex (harbor|port|marina|dredg); counties",
        },
        {
            "program_id": "pdm_cpf",
            "fy_start": "2022",
            "harbor_relevance_filter": "keyword regex (harbor|seawall)",
        },
        {
            "program_id": "eda_public_works",
            "fy_start": "2010",
            "harbor_relevance_filter": "recipient in crosswalk, or keyword regex (harbor|port|wharf)",
        },
    ]
    return pd.DataFrame(rows).set_index("program_id", drop=False)


def test_config_downloads(cfg):
    names = [d["aln"] for d in cfg["downloads"]]
    assert names == ["20.823", "11.300", "11.307", "97.047"]


def test_window_and_filters(cfg, inv):
    bric = next(d for d in cfg["downloads"] if d["aln"] == "97.047")
    assert us.download_window(bric, cfg, inv) == (2020, 2026)
    eda = next(d for d in cfg["downloads"] if d["aln"] == "11.300")
    assert us.download_window(eda, cfg, inv) == (2010, 2026)
    f = us.build_filters("97.047", 2020, 2026, ["02"])
    assert f["time_period"] == [{"start_date": "2019-10-01", "end_date": "2026-09-30"}]
    assert f["program_numbers"] == ["97.047"]
    plan = us.request_plan(f)
    assert plan["primary"][0][1] == us.SEARCH_ENDPOINT
    assert set(plan["primary"][0][2]["spending_level"]) == {"awards", "transactions", "subawards"}


def test_harbor_regex(inv):
    assert us.harbor_regex(inv, "pidp") is None
    assert us.harbor_regex(inv, "bric") == "harbor|port|marina|dredg"
    assert us.harbor_regex(inv, "unknown") == ""


def test_norm_county_geoid():
    c = pd.Series(["041", "06041", "", "41"], dtype="str")
    s = pd.Series(["06", "06", "06", "53"], dtype="str")
    assert us.norm_county_geoid(c, s).tolist() == ["06041", "06041", "", "53041"]


def test_zcta_to_county():
    z = pd.DataFrame(
        {
            "GEOID_ZCTA5_20": ["95531", "95531", "98101"],
            "GEOID_COUNTY_20": ["06015", "06023", "53033"],
            "AREALAND_PART": ["900", "100", "50"],
        }
    )
    out = us.zcta_to_county(z).set_index("zip5")
    assert out.at["95531", "county_geoid"] == "06015"
    assert bool(out.at["95531", "zcta_multi_county"]) is True
    assert bool(out.at["98101", "zcta_multi_county"]) is False


def test_classify_97047(inv):
    df = pd.DataFrame(index=range(4))
    fy = pd.Series([2021, 2023, 2023, 2023], dtype="Int64")
    text = pd.Series(
        [
            "BRIC harbor seawall project",
            "Pre-Disaster Mitigation congressionally directed spending - seawall",
            "PDM project",
            "mitigation planning",
        ]
    )
    c = us.classify(df, "97.047", fy, text, inv)
    assert c["program_id"].tolist() == ["bric", "pdm_cpf", "pdm_cpf", "bric"]
    assert c["earmark_flag"].tolist() == [False, True, True, False]
    assert c.loc[0, "harbor_kw_flag"]


def test_classify_20823(inv):
    df = pd.DataFrame(index=range(2))
    fy = pd.Series([2024, 2022], dtype="Int64")
    text = pd.Series(["Community Project Funding: dock repair", "Port of Newport terminal"])
    c = us.classify(df, "20.823", fy, text, inv)
    assert c["program_id"].tolist() == ["pidp_cpf", "pidp"]
    assert c["harbor_kw_flag"].all()
    assert c["earmark_candidate_year"].tolist() == [True, False]


def _write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def test_process_end_to_end(tmp_path, monkeypatch, cfg):
    raw = tmp_path / "raw"
    proc = tmp_path / "processed"
    monkeypatch.setattr(config, "RAW_DIR", raw)
    monkeypatch.setattr(config, "PROCESSED_DIR", proc)
    date = "2026-11-18"
    d = raw / "usaspending" / date / "aln_97.047" / "x"
    _write(
        d / "Assistance_PrimeAwardSummaries_1.csv",
        [
            {
                "assistance_award_unique_key": "A1",
                "cfda_numbers_and_titles": "97.047: BRIC",
                "award_base_action_date": "2021-03-01",
                "award_base_action_date_fiscal_year": "2021",
                "total_obligated_amount": "1000000",
                "recipient_uei": "UEI1",
                "recipient_state_code": "CA",
                "prime_award_summary_recipient_state_fips_code": "06",
                "prime_award_summary_recipient_county_fips_code": "067",
                "prime_award_summary_place_of_performance_state_fips_code": "06",
                "prime_award_summary_place_of_performance_county_fips_code": "",
                "business_types_description": "State Government",
                "prime_award_base_transaction_description": "BRIC FY2020 award",
            },
            {
                "assistance_award_unique_key": "A2",
                "cfda_numbers_and_titles": "97.047: BRIC",
                "award_base_action_date": "2021-03-01",
                "award_base_action_date_fiscal_year": "2021",
                "total_obligated_amount": "5",
                "recipient_uei": "",
                "recipient_state_code": "TX",
                "prime_award_summary_recipient_state_fips_code": "48",
                "prime_award_summary_recipient_county_fips_code": "201",
                "prime_award_summary_place_of_performance_state_fips_code": "48",
                "prime_award_summary_place_of_performance_county_fips_code": "201",
                "business_types_description": "State Government",
                "prime_award_base_transaction_description": "BRIC",
            },
        ],
    )
    _write(
        d / "Assistance_Subawards_1.csv",
        [
            {
                "prime_award_unique_key": "A1",
                "prime_award_cfda_numbers_and_titles": "97.047: BRIC",
                "subaward_amount": "250000",
                "subaward_action_date": "2022-01-15",
                "subaward_action_date_fiscal_year": "2022",
                "subawardee_uei": "SUB1",
                "subawardee_zip_code": "955311234",
                "subawardee_state_code": "CA",
                "sub_place_of_performance_zip": "95531",
                "sub_place_of_perform_state_code": "CA",
                "subaward_description": "Crescent City harbor seawall",
                "prime_awardee_business_types": "State Government",
            },
        ],
    )
    zdir = raw / "census" / date
    zdir.mkdir(parents=True)
    (zdir / "tab20_zcta520_county20_natl.txt").write_text(
        "OID_ZCTA5_20|GEOID_ZCTA5_20|GEOID_COUNTY_20|AREALAND_PART\n1|95531|06015|900\n"
    )
    cfg = {**cfg, "downloads": [d_ for d_ in cfg["downloads"] if d_["aln"] == "97.047"]}
    log = us.process(cfg, date)
    a = pd.read_csv(proc / "usaspending_pilot" / "prime_awards.csv", dtype=str)
    assert a["assistance_award_unique_key"].tolist() == ["A1"]  # TX award dropped
    assert a.loc[0, "in_scope"] == "True"  # state-level BRIC prime kept
    assert a.loc[0, "in_coastal_county"] == "False"  # Sacramento is not coastal
    assert a.loc[0, "recipient_is_state_gov"] == "True"
    s = pd.read_csv(proc / "usaspending_pilot" / "subawards.csv", dtype=str)
    assert s.loc[0, "recipient_county_geoid"] == "06015"
    assert s.loc[0, "in_coastal_county"] == "True"
    assert s.loc[0, "harbor_kw_flag"] == "True"
    assert log["downloads"]["aln_97.047"]["in_scope_rows"]["subawards"] == 1
    assert (
        json.loads((proc / "usaspending_pilot" / "process_log.json").read_text())["subawards"][
            "rows"
        ]
        == 1
    )
