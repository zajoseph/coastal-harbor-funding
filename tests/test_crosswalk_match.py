"""Offline tests for harborfund.link.crosswalk_match (T1.3)."""

import pandas as pd
import pytest

from harborfund.link import crosswalk_match as cm


@pytest.fixture
def cw():
    return pd.DataFrame(
        {
            "harbor_id": ["H-a", "H-b", "H-b", "H-c"],
            "state": ["WA", "CA", "CA", "CA"],
            "county_fips": ["53027", "06037", "06037", "06023"],
            "entity_name": ["Port A", "Harbor Dept B", "City B", "District C"],
            "entity_role": ["owner", "owner", "parent_government", "owner"],
            "entity_type": ["port_district", "city_department", "city", "harbor_district"],
            "uei": ["UEIA00000001", "UEIB00000001;UEIB00000002", "UEICITYB0001", ""],
            "legacy_duns": ["045334851", "", "37848012", "184473049"],
            "match_confidence": ["high", "high", "low", "high"],
        }
    )


def award(**kw):
    base = {
        "award_id": "X",
        "award_source": "prime",
        "program_id": "pidp",
        "fy": 2024,
        "amount_nominal": 100.0,
        "recipient_name": "R",
        "uei": pd.NA,
        "duns": pd.NA,
        "recipient_state": "WA",
        "recipient_county": "53027",
        "pop_state": "WA",
        "pop_county": "53027",
        "pop_city": "",
        "description": "",
        "harbor_kw_flag": True,
        "earmark_candidate_year": False,
        "geo_match_basis": "both",
        "prime_award_id": pd.NA,
    }
    base.update(kw)
    return base


def test_norm_duns_pads_and_rejects():
    s = cm.norm_duns(pd.Series(["37848012", "045334851.0", "abc", None, ""]))
    assert s.tolist()[:2] == ["037848012", "045334851"]
    assert s.iloc[2:].isna().all()


def test_crosswalk_ids_splits_lists_and_filters_versions(cw):
    ids = cm.crosswalk_ids(cw)
    assert set(ids.loc[ids.harbor_id == "H-b", "id_value"]) >= {"UEIB00000001", "UEIB00000002"}
    assert "037848012" in set(ids["id_value"])  # DUNS zero-padded
    v = cm.crosswalk_ids(cw, "own_op")
    assert "UEICITYB0001" not in set(v["id_value"])  # parent row dropped
    v = cm.crosswalk_ids(cw, "own_op_parent_nolow")
    assert "UEICITYB0001" not in set(v["id_value"])  # low row dropped
    assert "UEICITYB0001" in set(cm.crosswalk_ids(cw, "own_op_parent")["id_value"])


def test_uei_match_with_location_agreement_is_auto(cw):
    a = pd.DataFrame([award(uei="UEIA00000001")])
    m = cm.match_awards(a, cm.crosswalk_ids(cw))
    assert m.loc[0, "match_status"] == "auto"
    assert m.loc[0, "auto_harbor_id"] == "H-a"
    assert m.loc[0, "id_basis"] == "uei"


def test_uei_match_with_wrong_location_is_flagged_not_assigned(cw):
    # the Eureka case: Port A's UEI on an award performed in another state
    a = pd.DataFrame(
        [
            award(
                uei="UEIA00000001",
                recipient_state="CA",
                recipient_county="06023",
                pop_state="CA",
                pop_county="06023",
            )
        ]
    )
    m = cm.match_awards(a, cm.crosswalk_ids(cw))
    assert m.loc[0, "match_status"] == "flagged_geo"
    assert pd.isna(m.loc[0, "auto_harbor_id"])
    assert m.loc[0, "id_harbor_id"] == "H-a"
    assert m.loc[0, "geo"] == "disagree"


def test_duns_used_only_when_uei_misses(cw):
    a = pd.DataFrame(
        [
            award(
                award_id="d1",
                uei="NOTINCW00001",
                duns="184473049",
                recipient_state="CA",
                recipient_county="06023",
                pop_state="CA",
                pop_county="06023",
            ),
            award(award_id="d2", uei="UEIA00000001", duns="184473049"),
        ]
    )
    m = cm.match_awards(a, cm.crosswalk_ids(cw))
    assert m.loc[0, "id_basis"] == "duns" and m.loc[0, "auto_harbor_id"] == "H-c"
    assert m.loc[1, "id_basis"] == "uei" and m.loc[1, "auto_harbor_id"] == "H-a"


def test_state_only_location_is_flagged(cw):
    a = pd.DataFrame([award(uei="UEIA00000001", recipient_county="53033", pop_county="53033")])
    m = cm.match_awards(a, cm.crosswalk_ids(cw))
    assert m.loc[0, "geo"] == "state_only" and m.loc[0, "match_status"] == "flagged_geo"


def test_entity_in_two_harbors_is_flagged_multi(cw):
    cw2 = pd.concat([cw, cw.iloc[[0]].assign(harbor_id="H-z")], ignore_index=True)
    a = pd.DataFrame([award(uei="UEIA00000001")])
    m = cm.match_awards(a, cm.crosswalk_ids(cw2))
    assert m.loc[0, "match_status"] == "flagged_multi" and m.loc[0, "n_id_harbors"] == 2


def test_score_recall_precision():
    matches = pd.DataFrame(
        {
            "award_id": ["1", "2", "3", "4", "5"],
            "award_source": "prime",
            "amount_nominal": [10.0, 30.0, 5.0, 1.0, 2.0],
            "auto_harbor_id": ["H-a", pd.NA, "H-a", pd.NA, "H-b"],
            "id_harbor_id": ["H-a", "H-a", "H-a", pd.NA, "H-b"],
        }
    )
    truth = pd.DataFrame(
        {
            "award_id": ["1", "2", "3", "4", "5"],
            "award_source": "prime",
            "label": ["sample_harbor", "sample_harbor", "not_harbor", "not_harbor", "unclear"],
            "harbor_id": ["H-a", "H-b", "", "", ""],
        }
    )
    s = cm.score(matches, truth)
    assert s.n_truth_sample == 2 and s.n_correct == 1
    assert s.recall_n == pytest.approx(0.5) and s.recall_usd == pytest.approx(10 / 40)
    assert s.n_assigned == 2  # unclear award excluded
    assert s.precision_n == pytest.approx(0.5)
    assert s.n_unclear == 1
    s2 = cm.score(matches, truth, gate_geo=False)  # ID-only: award 2 goes to the wrong harbor
    assert s2.n_correct == 1 and s2.n_assigned == 3


def test_score_requires_complete_truth():
    m = pd.DataFrame(
        {
            "award_id": ["1"],
            "award_source": ["prime"],
            "amount_nominal": [1.0],
            "auto_harbor_id": [pd.NA],
            "id_harbor_id": [pd.NA],
        }
    )
    t = pd.DataFrame(columns=["award_id", "award_source", "label", "harbor_id"])
    with pytest.raises(ValueError):
        cm.score(m, t)


def test_truth_owner_view_moves_other_facilities():
    t = pd.DataFrame(
        {
            "award_id": ["1", "2"],
            "award_source": "prime",
            "label": ["other_harbor", "other_harbor"],
            "harbor_id": ["", ""],
            "scope": ["sample_owner_other_facility", "other_entity"],
            "owner_harbor_id": ["H-a", ""],
        }
    )
    o = cm.apply_truth_view(t, "owner")
    assert o.loc[0, "label"] == "sample_harbor" and o.loc[0, "harbor_id"] == "H-a"
    assert o.loc[1, "label"] == "other_harbor"


def test_apply_overrides():
    m = pd.DataFrame(
        {"award_id": ["1", "2"], "award_source": "prime", "auto_harbor_id": ["H-a", pd.NA]}
    )
    o = pd.DataFrame(
        {
            "award_id": ["1", "2"],
            "award_source": "prime",
            "harbor_id": ["", "H-c"],
            "action": ["unassign", "assign"],
        }
    )
    f = cm.apply_overrides(m, o)
    assert pd.isna(f.loc[0, "final_harbor_id"]) and f.loc[1, "final_harbor_id"] == "H-c"


def test_subapplicant_universe_uses_benefiting_and_zip_counties():
    sa = pd.DataFrame(
        {
            "subapplicationIdentifier": ["a", "b", "c", "d"],
            "program_id": "bric",
            "fiscalYear": ["2021", "2021", "2009", "2022"],
            "id_award": "",
            "subapplicantName": "X",
            "subapplicantUei": ["U1", "", "", ""],
            "subapplicantStateAbbreviation": "WA",
            "subapplicantCity": "",
            "zip_county_fips": ["", "53027", "53027", "53001"],
            "coastal_county_fips": ["53027;53049", "", "53027", ""],
            "subapplicationTitle": "",
            "federalShareAmount": "1",
            "status": "",
            "selectionStatus": "",
        }
    )
    u = cm.subapplicant_universe(sa, {"53027"})
    assert u["award_id"].tolist() == ["a", "b"]  # c before FY2010, d outside
