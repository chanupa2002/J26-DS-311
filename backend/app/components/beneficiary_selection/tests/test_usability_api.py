from fastapi.testclient import TestClient

from app.components.beneficiary_selection import geography
from app.components.beneficiary_selection.glossary import GLOSSARY
from app.components.beneficiary_selection import model_api


def test_geography_mapping_is_complete_and_consistent():
    assert len(geography.PROVINCES) == 9
    assert len(geography.DISTRICTS) == 25
    assert all(geography.validate_pair(row["province_code"], row["code"]) for row in geography.DISTRICTS)
    assert not geography.validate_pair(99, 1)
    assert not geography.validate_pair(2, 1)


def test_glossary_has_complete_i18n_ready_entries():
    assert len(GLOSSARY) >= 15
    assert len({entry["id"] for entry in GLOSSARY}) == len(GLOSSARY)
    for entry in GLOSSARY:
        assert entry["plain_label"].strip()
        assert entry["technical_term"].strip()
        assert entry["short"].strip()
        assert entry["popover"].strip()
        assert entry["method_text"].strip()


def test_geography_glossary_distribution_coverage_contracts():
    client = TestClient(model_api.create_app(force_synthetic=True))
    for path in ("/geography", "/glossary", "/distribution", "/coverage"):
        response = client.get(path)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["research_label"] == model_api.LABEL
        assert body["data_mode"] == "SYNTHETIC"
        assert "data_manifest_sha256" in body
    geo = client.get("/geography").json()
    assert len(geo["provinces"]) == 9
    assert len(geo["districts"]) == 25
    assert all("households_n" in district for district in geo["districts"])
    assert client.get("/glossary").json()["entries"]
    assert client.get("/distribution").json()["expected_vulnerability_histogram"]


def test_location_filters_reject_unknown_and_mismatched_codes():
    client = TestClient(model_api.create_app(force_synthetic=True))
    assert client.get("/households", params={"province": "99"}).status_code == 422
    assert client.get("/households", params={"district": "99"}).status_code == 422
    assert client.get("/households", params={"province": "2", "district": "1"}).status_code == 422
    assert client.get("/households", params={"province": "1", "district": "1"}).status_code == 200


def _assessment_payload():
    return {
        "roster_ages": [35, 12, 68], "bedrooms": 2,
        "wall_code": 1, "floor_code": 1, "roof_code": 1,
        "tenure_code": 1, "toilet_code": 1, "toilet_shared": 0,
        "monthly_income": 50000,
        "assets": {field: (1 if field in model_api.ASSET_FIELDS[:13] else 1) for field in model_api.ASSET_FIELDS},
        "food_answers": [2, 2, 2, 2, 2, 2, 2, 2],
    }


def test_assessment_endpoints_keep_unknowns_and_return_explanatory_context():
    client = TestClient(model_api.create_app(force_synthetic=True))
    payload = _assessment_payload()
    payload["food_answers"][2] = 3
    payload["toilet_code"] = 5
    derived = client.post("/assess/derive", json=payload)
    assert derived.status_code == 200, derived.text
    domains = derived.json()["domains"]
    assert domains["food"]["degree"] is None
    assert domains["sanitation"]["degree"] is None
    assert derived.json()["preview"]["persons_per_bedroom"] == 1.5
    assert derived.json()["preview"]["dependency_ratio"] == 2.0
    scored = client.post("/assess/score", json=payload)
    assert scored.status_code == 200, scored.text
    body = scored.json()
    assert body["comparison_group"]
    assert body["evidence_n_total"] > 0
    assert body["node_posteriors"]["vulnerability"]
    assert "data_manifest_sha256" in body
