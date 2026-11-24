from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from simu import standard
from simu.models import load_bottom_up as lb

FRIGO = lb.Cyclic("frigo", power_w=400, on_minutes=7, cycles_per_hour=2)
DAY = "2026-11-16"


def daily_kwh(appliances, start=DAY, end=DAY, seed=0):
    load = lb.simulate(appliances, start, end, seed=seed)["load_kw"]
    return standard.daily_energy_kwh(load)


def test_frigo_parametres_du_plan():
    # Calcul à la main : 0,4 kW × (2 × 7 min = 14/60 h) par heure × 24 h = 2,24 kWh/jour.
    # ATTENTION : le plan annonce « ≈ 1 kWh/jour » pour ces paramètres -> incohérence signalée.
    assert daily_kwh([FRIGO]).item() == pytest.approx(2.24)


def test_frigo_aleatoire_mais_energie_constante():
    a = lb.simulate([FRIGO], DAY, DAY, seed=1)["load_kw"]
    b = lb.simulate([FRIGO], DAY, DAY, seed=2)["load_kw"]
    assert not np.allclose(a, b)  # l'instant des cycles change
    assert standard.energy_kwh(a) == pytest.approx(standard.energy_kwh(b))
    pd.testing.assert_series_equal(a, lb.simulate([FRIGO], DAY, DAY, seed=1)["load_kw"])  # reproductible
    # chaque heure : exactement 2 cycles de 7 min à 400 W
    hourly_kwh = a.resample("1h").sum() * standard.DT_H
    assert np.allclose(hourly_kwh, 0.4 * 14 / 60)


def test_appareils_a_horaire_fixe():
    tv = lb.Schedule("tv", 100, [(18, 23)])
    eclairage = lb.Schedule("eclairage", 200, [(7, 9), (17, 23)])
    assert daily_kwh([tv]).item() == pytest.approx(0.5)  # 0,1 kW × 5 h
    assert daily_kwh([eclairage]).item() == pytest.approx(1.6)  # 0,2 kW × 8 h
    load = lb.simulate([tv], DAY, DAY)["load_kw"].tz_convert("Europe/Paris")
    assert np.allclose(load.between_time("18:00", "22:45"), 0.1)
    assert load.between_time("23:00", "17:45").eq(0).all()


def test_marche_quotidienne():
    lave_linge = lb.DailyRun("lave_linge", 2000, 2, earliest_h=8, latest_end_h=22)
    load = lb.simulate([lave_linge], DAY, "2026-11-22", seed=3)["load_kw"]
    assert list(standard.daily_energy_kwh(load)) == pytest.approx([4.0] * 7)  # 2 kW × 2 h
    local = load.tz_convert("Europe/Paris")
    assert local[local > 0].index.hour.min() >= 8
    assert local[local > 0].index.hour.max() < 22


def test_chauffage_degres_jours():
    chauffage = lb.Heating("chauffage", k_kwh_per_degc=2, temperatures={"2026-11-16": 5, "2026-11-17": 16})
    kwh = daily_kwh([chauffage], DAY, "2026-11-17")
    assert list(kwh) == pytest.approx([2 * (20 - 5), 0.0])  # 30 kWh, puis T >= 15 °C -> 0


def test_changement_d_heure():
    # 25/10/2026 : journée de 25 h en heure de Paris
    tv = lb.Schedule("tv", 100, [(18, 23)])
    kwh = daily_kwh([FRIGO, tv], "2026-10-25", "2026-10-25")
    assert kwh.item() == pytest.approx(0.4 * 14 / 60 * 25 + 0.5)
    assert len(lb.simulate([tv], "2026-10-25", "2026-10-25")) == 100  # 25 h × 4


def test_studio_environ_10_kwh_par_jour():
    scenario = yaml.safe_load((Path(__file__).parents[1] / "scenarios" / "studio.yaml").read_text(encoding="utf-8"))
    site = scenario["site"]
    load = lb.simulate(site["appliances"], "2026-11-16", "2026-11-22", seed=site["seed"])["load_kw"]
    kwh = standard.daily_energy_kwh(load)
    # À la main : frigo 2,24 + TV 0,5 + éclairage 1,6 + lave-vaisselle 2 + lave-linge 4 = 10,34 kWh/jour
    assert list(kwh) == pytest.approx([10.34] * 7)
    assert kwh.mean() == pytest.approx(10, rel=0.05)


def test_erreurs_de_configuration():
    with pytest.raises(ValueError, match="fenêtre"):
        lb.simulate([lb.Cyclic("x", 100, 40, 2)], DAY, DAY)
    with pytest.raises(ValueError, match="inconnu"):
        lb.simulate([{"type": "moteur", "name": "x"}], DAY, DAY)
    with pytest.raises(KeyError, match="température"):
        lb.simulate([lb.Heating("c", 1, temperatures={})], DAY, DAY)
