"""Offline tests for harborfund.ingest.sam (T2.1). No network: requests.get is faked."""

import json

import pandas as pd
import pytest

from harborfund import config
from harborfund.ingest import sam

KEY = "SECRETKEY123"


def cw_frame(n_uei=12):
    ueis = [f"UEI{i:09d}" for i in range(n_uei)]
    rows = [
        {"harbor_id": f"H-{i}", "state": "WA", "entity_name": f"Port {i}", "uei": u}
        for i, u in enumerate(ueis)
    ]
    rows[0]["uei"] = f"{ueis[0]};{ueis[1]}"  # duplicate across rows -> asked once
    rows += [
        {"harbor_id": "H-x", "state": "CA", "entity_name": "Noyo Harbor District", "uei": ""},
        {"harbor_id": "H-y", "state": "CA", "entity_name": "Noyo Harbor District", "uei": ""},
        {
            "harbor_id": "H-z",
            "state": "OR",
            "entity_name": "Salmon Harbor Marina, LLC (x)",
            "uei": "",
        },
    ]
    df = pd.DataFrame(rows)
    df["entity_role"] = "owner"
    return df


def entity(uei, status="Active", name="PORT"):
    return {
        "entityRegistration": {
            "ueiSAM": uei,
            "legalBusinessName": name,
            "registrationStatus": status,
            "registrationDate": "2020-01-01",
            "registrationExpirationDate": "2027-01-01",
        },
        "coreData": {"physicalAddress": {"stateOrProvinceCode": "WA", "city": "X"}},
    }


class FakeResp:
    def __init__(self, payload, status=200):
        self.status_code = status
        self.content = json.dumps(payload).encode()
        self.text = self.content.decode()
        self._p = payload

    def json(self):
        return self._p


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(sam, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(sam, "OUT_DIR", tmp_path / "out")
    monkeypatch.setattr(config, "MANIFEST_PATH", tmp_path / "manifest.csv")
    monkeypatch.setenv("SAM_API_KEY", KEY)
    monkeypatch.setattr(sam.time, "sleep", lambda s: None)
    return tmp_path


def fake_sam(registered, expired=(), log=None):
    """Fake requests.get: UEI batches return registered UEIs; status=E returns expired ones."""
    import urllib.parse

    def get(url, headers=None, timeout=None):
        if log is not None:
            log.append(url)
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        if "ueiSAM" in q:
            asked = q["ueiSAM"].strip("[]").split("~")
            pool = expired if q.get("registrationStatus") == "E" else registered
            st = "Expired" if q.get("registrationStatus") == "E" else "Active"
            return FakeResp(
                {"totalRecords": 0, "entityData": [entity(u, st) for u in asked if u in pool]}
            )
        if q.get("legalBusinessName", "").startswith("Noyo"):
            return FakeResp({"totalRecords": 1, "entityData": [entity("NOYO00000001")]})
        return FakeResp({"totalRecords": 0, "entityData": []})

    return get


def test_plan_batches_dedupes_and_names():
    plan = sam.build_plan(cw_frame(12))
    kinds = [r["kind"] for r in plan]
    assert kinds == ["uei", "uei", "name", "name"]
    assert len(plan[0]["ueis"]) == 10 and len(plan[1]["ueis"]) == 2  # 12 unique UEIs
    assert plan[0]["params"]["ueiSAM"].startswith("[UEI000000000~UEI000000001~")
    names = {(r["name"], r["state"]) for r in plan if r["kind"] == "name"}
    assert names == {("Noyo Harbor District", "CA"), ("Salmon Harbor Marina", "OR")}
    assert len({r["key"] for r in plan}) == len(plan)


def test_name_override_and_forbidden_chars():
    row = pd.Series(
        {
            "harbor_id": "CA-dana-point",
            "entity_name": "County of Orange (OC Community Resources / Dana Point Harbor)",
            "state": "CA",
        }
    )
    assert sam.search_names(row) == ["County of Orange"]
    row2 = pd.Series({"harbor_id": "H", "entity_name": "A & B {Port}", "state": "WA"})
    assert sam.search_names(row2) == ["A  B Port"]


def test_fetch_budget_cache_and_no_key_on_disk(sandbox, monkeypatch):
    import requests

    log = []
    cw = cw_frame(12)
    registered = {f"UEI{i:09d}" for i in range(10)}  # UEI..10, ..11 missing
    monkeypatch.setattr(requests, "get", fake_sam(registered, expired={"UEI000000010"}, log=log))
    used = sam.fetch(cw, max_requests=3, key_header=False, run_date="2026-11-24")
    assert used == 3
    used2 = sam.fetch(cw, max_requests=10, key_header=False, run_date="2026-11-25")
    # step 1 (2) + names (2) answered; then one expired re-check for the 2 missing UEIs
    assert used + used2 == 5
    assert sum("registrationStatus=E" in u for u in log) == 1
    assert "[" in log[0] and "~" in log[0]  # brackets/tildes kept literal
    for p in (sandbox / "raw").rglob("*"):
        if p.is_file():
            assert KEY not in p.read_text()
    man = (sandbox / "manifest.csv").read_text()
    assert KEY not in man and man.count("sam_entity_api") == 5
    assert sam.fetch(cw, max_requests=10, key_header=False, run_date="2026-11-26") == 0


def test_process_and_apply(sandbox, monkeypatch):
    import requests

    cw = cw_frame(12)
    registered = {f"UEI{i:09d}" for i in range(10)}
    monkeypatch.setattr(requests, "get", fake_sam(registered, expired={"UEI000000010"}))
    sam.fetch(cw, max_requests=20, key_header=False, run_date="2026-11-24")
    summary = sam.process(cw)
    assert summary["by_status"] == {"active": 10, "expired": 1, "none_found": 1}
    st = pd.read_csv(sandbox / "out" / "sam_status.csv", dtype=str, keep_default_na=False)
    names = pd.read_csv(
        sandbox / "out" / "sam_name_candidates.csv", dtype=str, keep_default_na=False
    )
    queries = pd.read_csv(
        sandbox / "out" / "sam_name_queries.csv", dtype=str, keep_default_na=False
    )
    out = sam.apply_status(cw, st, names, queries)
    r0 = out.iloc[0]
    assert r0["sam_status"] == "active" and "other UEIs: UEI000000001=active" in r0["sam_source"]
    assert out.loc[out.uei == "UEI000000010", "sam_status"].item() == "expired"
    assert out.loc[out.uei == "UEI000000011", "sam_status"].item() == "none_found"
    noyo = out[out.entity_name == "Noyo Harbor District"]
    assert set(noyo.sam_status) == {"name_candidates_review"}
    assert set(noyo.uei) == {""}  # name hits are never copied into the crosswalk
    assert out.loc[out.harbor_id == "H-z", "sam_status"].item() == "none_found"
    assert (out.sam_checked_date.str.len() == 10).all()


def test_unanswered_rows_stay_unchanged(sandbox):
    cw = cw_frame(3)
    cw["sam_status"] = "not_checked"
    empty = pd.DataFrame(columns=["uei", "sam_status", "checked_utc", "source_file"])
    q = pd.DataFrame(
        columns=[
            "query_name",
            "query_state",
            "records",
            "total_records",
            "checked_utc",
            "source_file",
        ]
    )
    out = sam.apply_status(cw, empty, pd.DataFrame(), q)
    assert set(out.sam_status) == {"not_checked"}


def test_http_error_stops_and_is_not_cached(sandbox, monkeypatch):
    import requests

    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResp({"error": "limit"}, 429))
    assert sam.fetch(cw_frame(3), max_requests=10, key_header=False, run_date="2026-11-24") == 1
    assert sam.cached_responses() == {}
