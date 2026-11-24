"""Étape 2 : coût sans équipement. Cas de référence : taches/1_offre_bloc_spot.md (270 €)."""

from pathlib import Path

import pandas as pd
import pytest

from simu import cli, scenario
from simu.models import market

ROOT = Path(__file__).parents[1]


def journee_exemple():
    """Journée de la fiche : nuit 0–6 h 60 kW / 40 €, jour 6–18 h 140 kW / 70 €, soir 18–24 h 160 kW / 150 €."""
    idx = pd.date_range("2026-11-16", periods=96, freq="15min", tz="Europe/Paris")
    hour = idx.hour
    load = pd.Series(60.0, index=idx).mask(hour >= 6, 140.0).mask(hour >= 18, 160.0)
    spot = pd.Series(40.0, index=idx).mask(hour >= 6, 70.0).mask(hour >= 18, 150.0)
    return load.tz_convert("UTC"), spot.tz_convert("UTC")


def test_bloc_spot_exemple_270_eur():
    load, spot = journee_exemple()
    c = market.cost_bloc_spot(load, spot, bloc_kw=100, bloc_price_eur_mwh=80)
    assert c.energy_kwh == pytest.approx(3000)
    assert c.details["bloc_kwh"] == pytest.approx(2400)
    assert c.details["bloc_eur"] == pytest.approx(192)  # 2400 kWh × 0,080 €/kWh
    assert c.details["spot_revente_eur"] == pytest.approx(-9.6)  # nuit : −240 kWh × 0,040
    assert c.details["spot_achat_eur"] == pytest.approx(33.6 + 54)  # jour + soir
    assert c.details["spot_eur"] == pytest.approx(78)
    assert c.total_eur == pytest.approx(270)
    assert c.eur_per_mwh == pytest.approx(90)


def test_comparaison_spot_pur_et_prix_fixe():
    load, spot = journee_exemple()
    assert market.cost_spot(load, spot).total_eur == pytest.approx(276)  # 14,4 + 117,6 + 144
    assert market.cost_fixed(load, 80).total_eur == pytest.approx(240)  # 3000 kWh × 0,080


def test_revente_au_spot_quand_puissance_negative():
    idx = pd.date_range("2026-11-16", periods=4, freq="15min", tz="UTC")
    p = pd.Series([-4.0, -4.0, 4.0, 4.0], index=idx)
    spot = pd.Series([100.0, 100.0, 50.0, 50.0], index=idx)
    # vente 2 kWh × 0,10 = −0,20 € ; achat 2 kWh × 0,05 = +0,10 €
    assert market.cost_spot(p, spot).total_eur == pytest.approx(-0.10)


def test_prix_manquant_refuse():
    load, spot = journee_exemple()
    with pytest.raises(ValueError, match="manquant"):
        market.cost_spot(load, spot.iloc[:-1])


def test_scenario_exemple_bloc_spot_via_csv():
    config = scenario.read(ROOT / "scenarios" / "exemple_bloc_spot.yaml")
    res = scenario.run(config)
    assert len(res.inputs) == 96
    totals = {c.offer: c.total_eur for c in res.costs_before}
    assert totals == pytest.approx({"spot": 276, "fixed": 240, "bloc_spot": 270})


@pytest.mark.network
def test_reseau_scenario_studio_prix_reels():
    config = scenario.read(ROOT / "scenarios" / "studio.yaml")
    res = scenario.run(config)
    assert len(res.inputs) == 7 * 96
    assert res.inputs["spot_eur_mwh"].notna().all()
    assert res.inputs["load_kw"].sum() * 0.25 == pytest.approx(7 * 10.34)
    assert {c.offer for c in res.costs_before} == {"spot", "fixed", "bloc_spot"}


def test_cli(capsys):
    assert cli.main(["run", str(ROOT / "scenarios" / "exemple_bloc_spot.yaml")]) == 0
    out = capsys.readouterr().out
    assert "3000.00 kWh" in out
    assert "270.00 €" in out
