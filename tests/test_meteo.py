"""Météo régionale ODRÉ (rayonnement, température) et PV par rayonnement."""

import numpy as np
import pandas as pd
import pytest

from simu import standard
from simu.adapters import odre_meteo
from simu.models import pv

STRAS = odre_meteo.STRASBOURG


def test_hauteur_du_soleil_strasbourg():
    # 21 juin, midi solaire à Strasbourg ≈ 11 h 30 UTC : hauteur ≈ 90 − 48,6 + 23,4 = 64,9°
    t = pd.DatetimeIndex(["2025-06-21 11:30", "2025-06-21 23:30", "2025-12-21 11:30"], tz="UTC")
    s = odre_meteo.solar_elevation_sin(t, **STRAS)
    assert np.degrees(np.arcsin(s[0])) == pytest.approx(64.9, abs=1.0)
    assert s[1] < 0  # nuit
    assert np.degrees(np.arcsin(s[2])) == pytest.approx(90 - 48.58 - 23.44, abs=1.0)  # ≈ 18°


def blocs_21_juin():
    # une journée UTC complète : 8 blocs, moyenne sur [T − 3 h ; T[, indexés par T (03:00 … 00:00 le 22)
    ends = pd.date_range("2025-06-21 03:00", "2025-06-22 00:00", freq="3h", tz="UTC")
    return pd.Series([10.0, 70.0, 580.0, 780.0, 716.0, 480.0, 30.0, 5.0], index=ends)


def test_repartition_conserve_l_energie_du_jour():
    blocks = blocs_21_juin()
    out = odre_meteo.disaggregate(blocks, **STRAS)
    assert len(out) == 96
    assert out.sum() * standard.DT_H == pytest.approx(blocks.sum() * 3)  # énergie du jour conservée (Wh/m²)
    assert out.min() >= 0


def test_repartition_nulle_la_nuit_et_sans_marche():
    out = odre_meteo.disaggregate(blocs_21_juin(), **STRAS)
    assert (out["2025-06-21 00:00":"2025-06-21 02:45"] == 0).all()  # 2 h–5 h à Strasbourg : nuit
    assert (out["2025-06-21 20:30":"2025-06-21 23:45"] == 0).all()  # après le coucher (≈ 19 h 35 UTC)
    jumps = out.diff().abs()
    assert jumps.max() < 0.15 * out.max()  # pas de saut brutal d'un quart d'heure à l'autre
    morning = out["2025-06-21 04:00":"2025-06-21 08:45"]
    assert morning.is_monotonic_increasing  # le soleil monte le matin


def test_lecture_rayonnement_et_format_standard(monkeypatch):
    records = [{"date": f"2025-06-21T{h:02d}:00:00+00:00", "ssrd03h": v}
               for h, v in [(0, 0.0), (3, 10.0), (6, 70.0), (9, 580.0), (12, 780.0), (15, 716.0), (18, 480.0), (21, 30.0)]]
    records.append({"date": "2025-06-22T00:00:00+00:00", "ssrd03h": 0.0})
    monkeypatch.setattr(odre_meteo, "get_json", lambda *a, **k: records)
    df = odre_meteo.load_irradiance("2025-06-21", "2025-06-21")
    standard.validate(df)
    assert len(df) == 96  # journée locale (Paris) = 22:00 UTC la veille -> 22:00 UTC
    s = df["irradiance_wm2"]
    assert s.notna().all() and s.min() >= 0
    assert s.idxmax().hour in (10, 11, 12)  # maximum vers midi solaire (≈ 11 h 30 UTC)
    assert s.iloc[0] == 0  # minuit heure locale : nuit


def test_temperature_jour_absent_interpole(monkeypatch):
    rows = [{"date": d, "tmoy": t} for d, t in
            [("2025-01-26", 3.0), ("2025-01-27", 4.0), ("2025-01-28", 5.0), ("2025-01-29", 6.0),
             ("2025-01-30", 7.0), ("2025-02-01", 9.0), ("2025-02-02", 10.0), ("2025-02-03", 11.0), ("2025-02-04", 12.0)]]
    monkeypatch.setattr(odre_meteo, "get_json", lambda *a, **k: rows)
    with pytest.warns(UserWarning, match="2025-01-31"):
        t = odre_meteo.load_temperature("2025-01-30", "2025-02-01")
    assert list(t.values) == pytest.approx([7.0, 8.0, 9.0])  # 31/01 absent du jeu -> interpolé


def test_pv_par_rayonnement_chaine_du_plan():
    # 100 kWc avec Pmax 250 W/m² -> 400 m² ; 1000 W/m² × 20 % × 400 m² = 80 kW
    assert pv.area_for_peak(100) == 400
    irr = pd.Series([0.0, 500.0, 1000.0], index=pd.date_range("2025-06-21", periods=3, freq="15min", tz="UTC"))
    assert list(pv.power_from_irradiance_kwc(irr, 100)) == pytest.approx([0, 40, 80])
    # exemple du plan : 1000 J/cm² sur 4 h -> 694 W/m² moyen -> 0,139 kW/m² électrique
    w_m2 = pv.irradiation_j_cm2_to_kwh_m2(1000) / 4 * 1000
    one_m2 = pv.power_from_irradiance(pd.Series([w_m2]), area_m2=1, efficiency=0.2)
    assert one_m2.iloc[0] == pytest.approx(pv.irradiation_to_electric_kw_m2(1000))
