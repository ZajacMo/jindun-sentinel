"""Tests for the API contract.

The API is the only thing the front end and the agent talk to, so these tests
pin the *contract*: which codes the endpoints answer with, which payload
fields exist, and — most importantly — that a resource which does not exist by
construction is reported differently from a request that is wrong.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_reports_the_served_countries(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["countries"] == ["CN", "US"]


def test_country_list_carries_the_profile_and_the_capabilities(client: TestClient) -> None:
    response = client.get("/api/v1/countries")
    assert response.status_code == 200
    countries = {item["code"]: item for item in response.json()["countries"]}

    assert countries["CN"]["profile"] == "mbsed"
    assert countries["CN"]["capabilities"]["spillover_network"] is True

    assert countries["US"]["profile"] == "official_index"
    assert countries["US"]["capabilities"]["spillover_network"] is False
    assert countries["US"]["capabilities"]["market_decomposition"] is False
    assert countries["US"]["capabilities"]["regime"] is True


def test_index_carries_the_profile_and_the_capabilities(client: TestClient) -> None:
    response = client.get("/api/v1/countries/US/index")
    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"] == "official_index"
    assert payload["capabilities"]["market_attribution"] is False


def test_a_missing_run_is_a_404_with_a_message(client: TestClient) -> None:
    response = client.get("/api/v1/countries/ZZ/index")
    assert response.status_code == 404
    assert "ZZ" in response.json()["detail"]


def test_the_default_estimator_is_served_when_none_is_asked_for(client: TestClient) -> None:
    response = client.get("/api/v1/countries/CN/spillover")
    assert response.status_code == 200
    payload = response.json()
    assert payload["method"] == "paper_equation"
    assert payload["default_method"] == "paper_equation"
    assert payload["available_methods"] == ["legacy_appendix", "paper_equation"]
    assert payload["nodes"] == ["equity", "bond"]


def test_the_requested_estimator_is_served(client: TestClient) -> None:
    response = client.get("/api/v1/countries/CN/spillover?method=legacy_appendix")
    assert response.status_code == 200
    payload = response.json()
    assert payload["method"] == "legacy_appendix"
    assert payload["horizon"] == 2


def test_an_unpublished_estimator_is_refused_with_the_available_ones(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/countries/CN/spillover?method=dy_generalised")
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["reason"] == "unknown_method"
    assert detail["available_methods"] == ["legacy_appendix", "paper_equation"]


def test_an_unpublished_horizon_is_refused(client: TestClient) -> None:
    response = client.get("/api/v1/countries/CN/spillover?horizon=5")
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["reason"] == "unknown_horizon"
    assert detail["available_horizons"] == [10]


def test_an_economy_without_a_network_is_reported_as_not_applicable(
    client: TestClient,
) -> None:
    """An official-index economy has no network by construction.

    It must not be reported the same way as a request that is simply wrong,
    and it must not be reported as a server error either.
    """
    response = client.get("/api/v1/countries/US/spillover")
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["reason"] == "not_applicable"
    assert detail["profile"] == "official_index"


def test_the_global_network_serves_the_same_estimator_choice(client: TestClient) -> None:
    response = client.get("/api/v1/global/spillover?method=legacy_appendix")
    assert response.status_code == 200
    payload = response.json()
    assert payload["method"] == "legacy_appendix"
    assert payload["available_methods"] == ["legacy_appendix", "paper_equation"]


def test_the_messages_endpoint_serves_every_locale(client: TestClient) -> None:
    catalogues: dict[str, dict] = {}
    for locale in ("en-US", "zh-CN", "zh-TW", "ja-JP"):
        response = client.get(f"/api/v1/messages?locale={locale}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["locale"] == locale
        catalogues[locale] = payload["messages"]

    # Every locale must carry exactly the same keys.  A missing translation
    # has to show up as a missing key rather than as a silent fallback to
    # another language.
    reference = set(catalogues["en-US"])
    for locale, catalogue in catalogues.items():
        assert set(catalogue) == reference, locale
        assert catalogue["app.name"], locale

    # The product name is a proper noun in English and Japanese and is
    # translated in the two Chinese catalogues.
    assert catalogues["en-US"]["app.name"] == "JinDun Sentinel"
    assert catalogues["zh-CN"]["app.name"] == "金盾哨兵"
    assert catalogues["zh-TW"]["app.name"] == "金盾哨兵"
    assert catalogues["ja-JP"]["app.name"] == "JinDun Sentinel"


def test_the_messages_endpoint_can_render_a_single_key(client: TestClient) -> None:
    response = client.get("/api/v1/messages?locale=zh-CN&key=nav.spillover")
    assert response.status_code == 200
    payload = response.json()
    assert payload["found"] is True
    assert payload["text"] == "溢出效应"


def test_the_quality_report_is_served(client: TestClient) -> None:
    response = client.get("/api/v1/countries/CN/data-quality")
    assert response.status_code == 200
    payload = response.json()
    assert payload["passed"] is True
    assert payload["counts"]["total"] == 1


def test_the_run_metadata_names_the_artefact_root(client: TestClient) -> None:
    response = client.get("/api/v1/run-metadata")
    assert response.status_code == 200
    assert response.json()["countries"] == ["CN", "US"]
