"""Étapes 3 à 7 : PV, batterie (règle simple, prix), peak shaving, rentabilité. Cas calculés à la main."""

import math

import numpy as np
import pandas as pd
import pytest

from simu import economics, simulate
from simu.models import market, pv
from simu.models.battery import Battery
from simu.strategies.rules import PeakShaving, PriceThreshold, SurplusPV

ETA = math.sqrt(0.9)


def day_index(day="2026-06-01"):
    return pd.date_range(day, periods=96, freq="15min", tz="Europe/Paris").tz_convert("UTC")


def by_hour(values_by_hour: dict, idx=None, default=0.0):
    """Série au pas de 15 min : {(h0, h1): valeur} en heure locale."""
    idx = day_index() if idx is None else idx
    hour = idx.tz_convert("Europe/Paris").hour
    s = pd.Series(default, index=idx)
    for (h0, h1), v in values_by_hour.items():
        s[(hour >= h0) & (hour < h1)] = v
    return s


# --- Étape 3 : PV ----------------------------------------------------------------------


def test_conversion_rayonnement_exemples_du_plan():
    # 1000 J/cm² = 10⁷ J/m² = 2,78 kWh/m² sur 4 h -> 0,69 kW/m² × 0,2 = 0,14 kW/m²
    assert pv.irradiation_j_cm2_to_kwh_m2(1000) == pytest.approx(2.778, abs=1e-3)
    assert pv.irradiation_to_electric_kw_m2(1000) == pytest.approx(0.14, abs=0.005)
    assert pv.irradiation_to_electric_kw_m2(1700) == pytest.approx(0.24, abs=0.005)


def test_pv_depuis_facteur_de_charge_et_rayonnement():
    cf = pd.Series([0.0, 0.5, 1.0], index=day_index()[:3])
    assert list(pv.power_from_cf(cf, 10)) == [0, 5, 10]
    irr = pd.Series([0.0, 500.0, 1000.0, 1400.0], index=day_index()[:4])
    # 100 m² × 20 % : 500 W/m² -> 10 kW ; 1400 W/m² × 0,2 = 280 W/m² plafonné à 250 -> 25 kW
    assert list(pv.power_from_irradiance(irr, 100, 0.2)) == [0, 10, 20, 25]


def test_pv_seul_autoconsommation_et_surplus():
    load = by_hour({}, default=1.0)  # 1 kW toute la journée = 24 kWh
    prod = by_hour({(10, 14): 3.0})  # 3 kW de 10 h à 14 h = 12 kWh
    r = simulate.run(load, prod)
    simulate.check_balance(r)
    s = simulate.summary(r)
    assert s["pv_autoconso_directe_kwh"] == pytest.approx(4)  # 1 kW × 4 h
    assert s["pv_revendu_kwh"] == pytest.approx(8)  # 2 kW × 4 h
    assert s["achat_reseau_kwh"] == pytest.approx(20)  # 24 − 4
    assert s["taux_autoconso"] == pytest.approx(4 / 12)


def test_revente_au_prix_de_rachat():
    load = by_hour({}, default=1.0)
    prod = by_hour({(10, 14): 3.0})
    grid = simulate.run(load, prod)["grid_kw"]
    spot = by_hour({}, default=100.0)
    c = market.cost(grid, spot, {"type": "spot", "export_price_eur_mwh": 11})
    # achat 20 kWh × 0,10 = 2,00 € ; revente 8 kWh × 0,011 = 0,088 €
    assert c.total_eur == pytest.approx(2.0 - 0.088)


def test_surcout_sur_les_kwh_achetes():
    load = by_hour({}, default=1.0)
    prod = by_hour({(10, 14): 3.0})
    grid = simulate.run(load, prod)["grid_kw"]
    spot = by_hour({}, default=100.0)
    c = market.cost(grid, spot, {"type": "spot", "export_price_eur_mwh": 0, "import_surcharge_eur_mwh": 50})
    # 20 kWh achetés × (0,10 + 0,05) ; surplus non payé
    assert c.total_eur == pytest.approx(20 * 0.15)


# --- Étape 4 : batterie règle simple --------------------------------------------------


def test_batterie_un_pas():
    b = Battery(10)  # P_max = 0,5 C = 5 kW ; E_min = 1, E_max = 9 kWh
    assert b.p_max_kw == 5
    pc, pd_, e = b.step(1.0, 4.0)
    assert (pc, pd_) == (4.0, 0.0) and e == pytest.approx(1 + ETA * 4 * 0.25)
    pc, pd_, e = b.step(1.0, 50.0)  # consigne bornée à P_max
    assert pc == 5.0
    pc, pd_, e = b.step(1.0, -3.0)  # vide : pas de décharge sous SOC_min
    assert pd_ == 0 and e == 1.0


def test_batterie_surplus_pv_rendement_aller_retour():
    # surplus de 4 kW pendant 2 h (10 h–12 h) puis déficit de 2 kW de 18 h à 22 h
    load = by_hour({(18, 22): 2.0})
    prod = by_hour({(10, 12): 4.0})
    b = Battery(10)
    r = simulate.run(load, prod, b, SurplusPV())
    simulate.check_balance(r, b)  # bilan, SOC dans les bornes, énergie conservée
    s = simulate.summary(r, b)
    # 8 kWh chargés -> 8 × 0,9487 = 7,59 kWh stockés (< 8 kWh utiles) -> 7,59 × 0,9487 = 7,2 kWh restitués
    assert s["charge_kwh"] == pytest.approx(8)
    assert s["decharge_kwh"] == pytest.approx(8 * 0.9)
    assert s["achat_reseau_kwh"] == pytest.approx(8 - 7.2)
    assert s["pertes_batterie_kwh"] == pytest.approx(0.8)
    assert s["revente_reseau_kwh"] == pytest.approx(0)
    assert r["soc"].between(0.1 - 1e-9, 0.9 + 1e-9).all()


def test_batterie_pleine_le_surplus_est_revendu():
    load = by_hour({}, default=0.0)
    prod = by_hour({(8, 16): 5.0})  # 40 kWh de surplus
    b = Battery(10)
    r = simulate.run(load, prod, b, SurplusPV())
    simulate.check_balance(r, b)
    assert r["energy_kwh"].max() == pytest.approx(9)  # SOC max = 90 %
    s = simulate.summary(r, b)
    assert s["charge_kwh"] == pytest.approx(8 / ETA)
    assert s["pv_revendu_kwh"] == pytest.approx(40 - 8 / ETA)


# --- Étape 5 : batterie « prix » ------------------------------------------------------


def test_strategie_prix_gagne_les_jours_a_fort_spread():
    load = by_hour({}, default=2.0)
    spot = by_hour({(0, 6): 20.0, (18, 22): 200.0}, default=80.0)
    b = Battery(10)
    base = market.cost_spot(load, spot).total_eur
    simple = simulate.run(load, None, b, SurplusPV(), spot)
    prix = simulate.run(load, None, b, PriceThreshold(), spot)
    simulate.check_balance(prix, b)
    gain_simple = base - market.cost_spot(simple["grid_kw"], spot).total_eur
    gain_prix = base - market.cost_spot(prix["grid_kw"], spot).total_eur
    # sans PV, la règle simple ne fait rien ; la règle prix charge 8/η = 8,43 kWh à 20 €/MWh
    # et restitue 8 × η = 7,59 kWh à 200 €/MWh : 1,518 − 0,169 = 1,349 €
    assert gain_simple == pytest.approx(0)
    assert gain_prix == pytest.approx(8 * ETA * 0.200 - 8 / ETA * 0.020, rel=1e-6)
    assert gain_prix > gain_simple


def test_strategie_prix_ne_charge_pas_sans_spread():
    load = by_hour({}, default=2.0)
    spot = by_hour({}, default=80.0)  # prix plat : le spread ne couvre pas les pertes
    r = simulate.run(load, None, Battery(10), PriceThreshold(), spot)
    assert r["grid_to_battery_kw"].sum() == 0


def test_strategie_prix_vide_la_batterie_meme_si_la_conso_est_faible():
    # conso 1 kW : vider 8 kWh utiles (7,59 kWh restitués) demande 31 quarts d'heure de décharge.
    # Prix tous différents l'après-midi (200, 199.9, …) : la règle doit descendre assez bas
    # dans le classement des prix pour vider la batterie, pas s'arrêter aux 7 plus chers.
    idx = day_index()
    load = pd.Series(1.0, index=idx)
    hour = idx.tz_convert("Europe/Paris").hour
    spot = pd.Series(80.0, index=idx)
    spot[hour < 6] = 20.0
    pm = hour >= 12
    spot[pm] = 200.0 - 0.1 * np.arange(pm.sum())
    r = simulate.run(load, None, Battery(10), PriceThreshold(), spot)
    s = simulate.summary(r, Battery(10))
    assert s["decharge_kwh"] == pytest.approx(8 * ETA, rel=1e-6)
    assert s["charge_depuis_reseau_kwh"] == pytest.approx(8 / ETA, rel=1e-6)


def test_strategie_prix_anticipe_le_surplus_solaire():
    # nuit pas chère (20 €/MWh), soir cher (200) ; 4 kW de surplus PV de 10 h à 13 h = 12 kWh,
    # de quoi remplir les 8 kWh utiles : la règle ne doit RIEN acheter au réseau pour la batterie.
    load = by_hour({}, default=1.0)
    prod = by_hour({(10, 13): 5.0})
    spot = by_hour({(0, 6): 20.0, (18, 22): 200.0}, default=80.0)
    r = simulate.run(load, prod, Battery(10), PriceThreshold(), spot)
    assert r["grid_to_battery_kw"].sum() == 0
    assert r["energy_kwh"].max() == pytest.approx(9)  # remplie par le soleil (SOC 90 %)
    # sans anticipation, elle achète la nuit puis revend une partie du surplus solaire
    naive = simulate.run(load, prod, Battery(10), PriceThreshold(anticipate_pv=False), spot)
    assert naive["grid_to_battery_kw"].sum() > 0
    assert naive["pv_export_kw"].sum() > r["pv_export_kw"].sum()


def test_strategie_prix_respecte_la_limite_reseau():
    load = by_hour({}, default=2.0)
    spot = by_hour({(0, 6): 20.0, (18, 22): 200.0}, default=80.0)
    r = simulate.run(load, None, Battery(10), PriceThreshold(grid_limit_kw=4), spot)
    assert r["grid_kw"].max() == pytest.approx(4)  # 2 kW de conso + 2 kW de charge au plus
    libre = simulate.run(load, None, Battery(10), PriceThreshold(), spot)
    assert libre["grid_kw"].max() == pytest.approx(7)  # 2 + P_max 5 kW


# --- Étape 6 : peak shaving -----------------------------------------------------------


def test_peak_shaving_ecrete_les_pointes():
    load = by_hour({(9, 10): 30.0, (14, 15): 28.0}, default=10.0)
    b = Battery(40, soc_init=0.9)  # P_max = 20 kW
    r = simulate.run(load, None, b, PeakShaving(limit_kw=20, margin_kw=2))
    simulate.check_balance(r, b)
    assert load.max() == 30
    assert r["grid_kw"].max() == pytest.approx(20)
    # recharge depuis le réseau sans dépasser 20 − 2 = 18 kW
    assert r.loc[r["grid_to_battery_kw"] > 0, "grid_kw"].max() <= 18 + 1e-9
    pen_avant = market.overrun_penalty(load, 20, eur_per_kw=10)
    pen_apres = market.overrun_penalty(r["grid_kw"], 20, eur_per_kw=10)
    assert pen_avant["penalite_eur"] == pytest.approx(100)  # (30 − 20) kW × 10 €/kW
    assert pen_apres["penalite_eur"] == 0


# --- Étape 7 : rentabilité ------------------------------------------------------------


def test_capex_et_cout_usure():
    assert economics.capex(battery_kwh=10)["total_eur"] == pytest.approx((6000 + 13000) / 2)
    assert economics.capex(pv_kwc=100, level="bas")["total_eur"] == pytest.approx(60_000)
    # fiche 5 : 100 kWh à 40 000 €, 5000 cycles, 80 % -> 0,10 €/kWh
    b = Battery(100, cycle_life=5000)
    assert b.wear_cost_eur_kwh(40_000) == pytest.approx(0.10)


def test_temps_de_retour():
    p = economics.profitability(annual_gain_eur=950, battery_kwh=10, battery_cycles_per_year=300)
    assert p.capex_eur == 9500
    assert p.payback_years == pytest.approx(10)
    assert p.life_years == 15  # 5000 / 300 = 16,7 ans, plafonné à 15 ans calendaires
    assert p.lifetime_balance_eur == pytest.approx(950 * 15 - 9500)
    assert economics.profitability(-10, battery_kwh=10).payback_years == math.inf
    assert np.isclose(economics.battery_life_years(1000, 5000), 5)
