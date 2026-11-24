"""Adaptateurs Energy-Charts et RTE (ODRÉ).

- Tests hors ligne : vraies réponses des API enregistrées dans ``tests/fixtures`` (réduites).
- Tests réseau (``pytest -m network``) : appel réel + vérification du cache local.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from simu import standard
from simu.adapters import _http, energy_charts, rte_eco2mix

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def no_throttle(monkeypatch):
    monkeypatch.setattr(_http, "MIN_INTERVAL_S", 0.0)


@pytest.fixture
def fake_api(monkeypatch):
    def fake_get_json(url, params=None, **kwargs):
        if url.endswith("/price"):
            return fixture("ec_price_2025-09-30_2025-10-01.json")
        if url.endswith("/public_power"):
            return fixture("ec_public_power_2025-06-01.json")
        if url.endswith("/installed_power"):
            return fixture("ec_installed_power.json")
        if "parc-prod-par-filiere" in url:
            return fixture("odre_parc.json")
        if "eco2mix-national-cons-def" in url:
            return fixture("odre_cons_def_2025-06-01.json")
        raise AssertionError(f"URL inattendue : {url}")

    monkeypatch.setattr(energy_charts, "get_json", fake_get_json)
    monkeypatch.setattr(rte_eco2mix, "get_json", fake_get_json)


def test_energy_charts_prix_horaire_puis_15min(fake_api):
    df = energy_charts.load_spot("2025-09-30", "2025-10-01")
    standard.validate(df)
    assert len(df) == 2 * 96
    assert df["spot_eur_mwh"].notna().all()
    # 30/09 (horaire) : 1re heure répétée sur 4 quarts d'heure ; 01/10 : vraies valeurs au quart d'heure
    assert df["spot_eur_mwh"].iloc[:4].nunique() == 1
    assert df.index[0] == pd.Timestamp("2025-09-29 22:00", tz="UTC")  # minuit heure de Paris


def test_energy_charts_facteur_de_charge_pv(fake_api):
    df = energy_charts.load_pv_cf("2025-06-01", "2025-06-01")
    standard.validate(df)
    assert len(df) == 96
    cf = df["pv_cf"]
    assert cf.between(0, 1).all()
    assert cf.iloc[0] == 0  # minuit
    # production MW ÷ 28 250 MW (Solar AC 2025)
    raw = energy_charts.parse_public_power(fixture("ec_public_power_2025-06-01.json"))
    assert cf.max() == pytest.approx(raw.max() / 28_250)


def test_energy_charts_puissance_installee_imposee(fake_api):
    df = energy_charts.load_pv_cf("2025-06-01", "2025-06-01", installed_mw=30_000)
    raw = energy_charts.parse_public_power(fixture("ec_public_power_2025-06-01.json"))
    assert df["pv_cf"].max() == pytest.approx(raw.max() / 30_000)


def test_rte_facteur_de_charge_pv_interpole_les_quarts_d_heure(fake_api):
    df = rte_eco2mix.load_pv_cf("2025-06-01", "2025-06-01")
    standard.validate(df)
    assert len(df) == 96
    assert df["pv_cf"].notna().all()
    s = df["pv_cf"] * 30_437  # parc solaire RTE 2025 (MW)
    # valeur à :15 = moyenne de :00 et :30 (interpolation linéaire)
    t = pd.Timestamp("2025-06-01 10:00", tz="UTC")
    assert s[t + pd.Timedelta("15min")] == pytest.approx((s[t] + s[t + pd.Timedelta("30min")]) / 2)


def test_cache_http(tmp_path, monkeypatch):
    calls = []

    class FakeResponse:
        status_code = 200
        headers = {}

        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": 1}

    class FakeSession:
        def get(self, url, params=None, timeout=None):
            calls.append(url)
            return FakeResponse()

    monkeypatch.setattr(_http, "_session", lambda: FakeSession())
    assert _http.get_json("https://x/y", {"a": 1}, cache_dir=tmp_path) == {"ok": 1}
    assert _http.get_json("https://x/y", {"a": 1}, cache_dir=tmp_path) == {"ok": 1}
    assert len(calls) == 1  # 2e appel servi par le cache
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_retries_puis_erreur(tmp_path, monkeypatch):
    import requests

    class FailingSession:
        n = 0

        def get(self, *a, **k):
            FailingSession.n += 1
            raise requests.Timeout("timeout")

    monkeypatch.setattr(_http, "_session", lambda: FailingSession())
    with pytest.raises(ConnectionError):
        _http.get_json("https://x/y", cache_dir=tmp_path, retries=3, backoff_s=0)
    assert FailingSession.n == 3
    assert not list(tmp_path.glob("*.json"))  # rien en cache après un échec


def test_limite_de_debit_429_puis_succes(tmp_path, monkeypatch):
    import requests

    sleeps = []
    monkeypatch.setattr(_http.time, "sleep", lambda s: sleeps.append(s))

    class Response:
        def __init__(self, code):
            self.status_code = code
            self.headers = {"Retry-After": "7"} if code == 429 else {}

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(str(self.status_code))

        def json(self):
            return {"ok": 1}

    codes = iter([429, 200])

    class Session:
        def get(self, *a, **k):
            return Response(next(codes))

    monkeypatch.setattr(_http, "_session", lambda: Session())
    assert _http.get_json("https://x/z", cache_dir=tmp_path) == {"ok": 1}
    assert 7 in sleeps  # Retry-After respecté


# --- réseau --------------------------------------------------------------------------


@pytest.mark.network
def test_reseau_energy_charts_prix_et_pv(tmp_path):
    df = energy_charts.load("2026-06-01", "2026-06-02", cache_dir=tmp_path)
    standard.validate(df)
    assert len(df) == 2 * 96
    assert df.notna().all().all()
    assert df["pv_cf"].max() > 0.2
    assert len(list(tmp_path.glob("*.json"))) == 3  # prix, production, puissance installée
    # 2e lecture : uniquement depuis le cache
    again = energy_charts.load("2026-06-01", "2026-06-02", cache_dir=tmp_path)
    pd.testing.assert_frame_equal(df, again)


@pytest.mark.network
def test_reseau_rte_pv(tmp_path):
    df = rte_eco2mix.load_pv_cf("2025-06-01", "2025-06-02", cache_dir=tmp_path)
    standard.validate(df)
    assert len(df) == 2 * 96
    assert df["pv_cf"].notna().all()
    assert 0.2 < df["pv_cf"].max() <= 1
