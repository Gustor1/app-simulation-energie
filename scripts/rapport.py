"""Génère les graphiques et les chiffres du rapport de tests (docs/rapport/).

Usage : python scripts/rapport.py
Sorties : docs/rapport/fig/*.png, docs/rapport/chiffres.json
Le texte d'interprétation est dans docs/rapport/RAPPORT.md (rédigé à partir de ces sorties).
"""

from __future__ import annotations

import json
import math
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from simu import economics, plots, scenario, simulate, standard
from simu.adapters import csv_generic, energy_charts, rte_eco2mix
from simu.models import load_bottom_up as lb
from simu.models import market, pv
from simu.models.battery import Battery
from simu.plots import C, TZ, _n, save
from simu.strategies.rules import PeakShaving, PriceThreshold, SurplusPV

warnings.filterwarnings("ignore", category=UserWarning)
ROOT = Path(__file__).parents[1]
OUT = ROOT / "docs" / "rapport"
FIG = OUT / "fig"
N = {}  # chiffres clés


def fig(name, f):
    save(f, FIG / f"{name}.png")
    print("  ", name)


def eur(x):
    return round(float(x), 2)


# =====================================================================================
# Étape 0 – données
# =====================================================================================
print("Étape 0")
csv_df = csv_generic.load(ROOT / "data" / "exemple_bloc_spot.csv", ROOT / "data" / "exemple_bloc_spot.mapping.yaml")
f, ax = plt.subplots(figsize=(10, 3.5))
raw = pd.read_csv(ROOT / "data" / "exemple_bloc_spot.csv", sep=";")
raw_t = pd.to_datetime(raw["heure"]).dt.tz_localize(TZ)
ax.plot(raw_t, raw["conso_kw"], "o", color=C["grid"], label="CSV d'origine (1 valeur / heure, heure de Paris)")
ax.plot(csv_df.index, csv_df["load_kw"], drawstyle="steps-post", color=C["load"], label="format standard (15 min, UTC)")
ax.set_ylabel("kW")
ax.set_title("Lecture d'un CSV quelconque : horaire -> pas de 15 min, heure locale -> UTC")
ax.legend()
plots._time_axis(ax, 1)
fig("e0_csv_generique", f)

spot = energy_charts.load_spot("2025-01-01", "2025-12-31")["spot_eur_mwh"]
cf_ec = energy_charts.load_pv_cf("2025-01-01", "2025-12-31")["pv_cf"]
cf_rte = rte_eco2mix.load_pv_cf("2025-01-01", "2025-12-31")["pv_cf"]
fig("e0_spot_2025", plots.spot_overview(spot, "Prix spot France 2025 (Energy-Charts)"))
fig("e0_spread_2025", plots.daily_spread(spot, "Spread journalier 2025 (max − min du jour)"))
both = pd.DataFrame({"Energy-Charts": cf_ec, "RTE éCO2mix": cf_rte})
fig("e0_pv_profils", plots.pv_profiles(both, "Facteur de charge PV France 2025"))

f, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4))
ok = both.dropna()
a1.scatter(ok["RTE éCO2mix"], ok["Energy-Charts"], s=1, alpha=0.2, color=C["pv"])
a1.plot([0, 0.8], [0, 0.8], color="black", lw=0.8, ls="--")
a1.set_xlabel("RTE (kW/kWc)")
a1.set_ylabel("Energy-Charts (kW/kWc)")
a1.set_title(f"Mêmes quarts d'heure, 2 sources (corrélation {ok.corr().iloc[0, 1]:.3f})")
years = list(range(2019, 2026))
ec_cap, rte_cap = energy_charts.installed_solar_mw(), rte_eco2mix.installed_solar_mw()
x = np.arange(len(years))
a2.bar(x - 0.2, [ec_cap[y] / 1000 for y in years], 0.4, label="Energy-Charts (Solar AC)", color=C["pv"])
a2.bar(x + 0.2, [rte_cap[y] / 1000 for y in years], 0.4, label="RTE (parc_solaire)", color=C["pv_self"])
a2.set_xticks(x)
a2.set_xticklabels(years)
a2.set_ylabel("GW installés")
a2.set_title("Puissance solaire installée en France")
a2.legend()
fig("e0_pv_sources", f)

loc_spot = spot.tz_convert(TZ)
spread = loc_spot.resample("D").max() - loc_spot.resample("D").min()
N["e0"] = {
    "spot_moyen": eur(spot.mean()),
    "spot_min": eur(spot.min()),
    "spot_max": eur(spot.max()),
    "heures_negatives": float((spot < 0).sum() * standard.DT_H),
    "heures_negatives_ou_nulles": float((spot <= 0).sum() * standard.DT_H),
    "spread_median": eur(spread.median()),
    "spread_moyen": eur(spread.mean()),
    "jours_spread_80_180": float(((spread >= 80) & (spread <= 180)).mean()),
    "jours_spread_sup_180": float((spread > 180).mean()),
    "jours_spread_inf_80": float((spread < 80).mean()),
    "productible_ec": eur(cf_ec.sum() * standard.DT_H),
    "productible_rte": eur(cf_rte.sum() * standard.DT_H),
    "cf_max_ec": eur(cf_ec.max()),
    "pv_trous_ec": int(cf_ec.isna().sum()),
    "pv_trous_rte": int(cf_rte.isna().sum()),
    "correlation": eur(ok.corr().iloc[0, 1]),
    "spread_hiver_median": eur(spread[spread.index.month.isin([12, 1, 2])].median()),
    "spread_ete_median": eur(spread[spread.index.month.isin([6, 7, 8])].median()),
}

# =====================================================================================
# Étape 1 – conso bottom-up
# =====================================================================================
print("Étape 1")
studio_cfg = scenario.read(ROOT / "scenarios" / "studio_pv_batterie.yaml")
appliances = studio_cfg["site"]["appliances"]
frigo = lb.Cyclic("frigo", 400, 7, 2)
clock = lb.minute_clock("2025-06-02", "2025-06-02", TZ)
minutes = pd.Series(frigo.minutes_w(clock, np.random.default_rng(1)), index=clock)
q = lb.simulate([frigo], "2025-06-02", "2025-06-02", seed=1)["load_kw"].tz_convert(TZ) * 1000
f, ax = plt.subplots(figsize=(10, 3.5))
w0, w1 = pd.Timestamp("2025-06-02 08:00", tz=TZ), pd.Timestamp("2025-06-02 11:00", tz=TZ)
mm = minutes[(minutes.index >= w0) & (minutes.index < w1)]
qq = q[(q.index >= w0) & (q.index < w1)]
ax.fill_between(mm.index, mm, step="post", color=C["neutral"], alpha=0.5, label="à la minute (2 cycles de 7 min / h)")
ax.plot(qq.index, qq, drawstyle="steps-post", color=C["load"], lw=2, label="moyenne 15 min (format standard)")
ax.axhline(400 * 14 / 60, color=C["grid"], ls="--", lw=1, label="moyenne horaire 93 W")
ax.set_ylabel("W")
ax.set_title("Réfrigérateur : 400 W, 7 min, 2×/h -> 2,24 kWh/jour (le plan annonce ≈ 1)")
ax.legend(loc="upper right", fontsize=8)
plots._time_axis(ax, 1)
fig("e1_frigo", f)

by = lb.simulate_appliances(appliances, "2025-06-02", "2025-06-08", seed=42)
studio_week = lb.simulate(appliances, "2025-06-02", "2025-06-08", seed=42)
r_studio_week = simulate.run(studio_week["load_kw"])
fig("e1_studio_semaine", plots.load_curve(r_studio_week, "2025-06-02", 7, "Studio fictif (bottom-up)", by=by))
per_app = by.sum() * standard.DT_H / 7
f, ax = plt.subplots(figsize=(9, 3.5))
ax.barh(per_app.index, per_app, color=[C["load"], C["spot"], C["pv"], C["bat"], C["grid_after"]])
for i, v in enumerate(per_app):
    ax.text(v, i, f" {v:.2f} kWh", va="center")
ax.set_xlabel("kWh / jour")
ax.set_title(f"Studio : {per_app.sum():.2f} kWh/jour (cible ≈ 10)")
fig("e1_studio_par_appareil", f)

pme_cfg = scenario.read(ROOT / "scenarios" / "pme_bureaux.yaml")
pme_by = lb.simulate_appliances(pme_cfg["site"]["appliances"], "2025-06-16", "2025-06-22", seed=7)
pme_week = simulate.run(pme_by.sum(axis=1).rename("load_kw"))
fig("e1_pme_semaine", plots.load_curve(pme_week, "2025-06-16", 7, "PME de bureaux fictive (bottom-up)", by=pme_by))
N["e1"] = {"studio_kwh_jour": eur(per_app.sum()), "par_appareil": {k: eur(v) for k, v in per_app.items()}}

# =====================================================================================
# Étape 2 – coût sans équipement
# =====================================================================================
print("Étape 2")
idx = pd.date_range("2026-11-16", periods=96, freq="15min", tz=TZ)
h = idx.hour
load_ex = pd.Series(60.0, index=idx).mask(h >= 6, 140.0).mask(h >= 18, 160.0)
spot_ex = pd.Series(40.0, index=idx).mask(h >= 6, 70.0).mask(h >= 18, 150.0)
f, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4), gridspec_kw={"width_ratios": [2, 1]})
a1.fill_between(idx, load_ex, 100, where=load_ex > 100, step="post", color=C["grid"], alpha=0.35, label="acheté au spot")
a1.fill_between(idx, load_ex, 100, where=load_ex < 100, step="post", color=C["export"], alpha=0.5, label="revendu au spot")
a1.plot(idx, load_ex, drawstyle="steps-post", color=C["load"], label="conso")
a1.axhline(100, color="black", ls="--", label="bloc 100 kW à 80 €/MWh")
a1.set_ylabel("kW")
a3 = a1.twinx()
a3.plot(idx, spot_ex, drawstyle="steps-post", color=C["spot"], lw=1.2)
a3.set_ylabel("spot (€/MWh)", color=C["spot"])
a3.grid(False)
a1.legend(loc="upper left", fontsize=8)
a1.set_title("Journée d'exemple de la fiche bloc + spot")
plots._time_axis(a1, 1)
lu, su = load_ex.tz_convert("UTC"), spot_ex.tz_convert("UTC")
vals = {"spot pur": market.cost_spot(lu, su).total_eur, "bloc + spot": market.cost_bloc_spot(lu, su, 100, 80).total_eur,
        "prix fixe 80": market.cost_fixed(lu, 80).total_eur}
a2.bar(vals.keys(), vals.values(), color=[C["spot"], C["grid_after"], C["neutral"]])
for i, v in enumerate(vals.values()):
    a2.text(i, v, f"{v:.0f} €", ha="center", va="bottom")
a2.set_title("Coût de la journée")
fig("e2_exemple_270", f)

# PME : coût mensuel par offre, sans équipement
pme_inputs = scenario.build_inputs(pme_cfg)
pme_load, pme_spot, pme_cf = pme_inputs["load_kw"], pme_inputs["spot_eur_mwh"], pme_inputs["pv_cf"]
offers = {"spot pur": {"type": "spot"}, "prix fixe 80 €/MWh": {"type": "fixed", "price_eur_mwh": 80},
          "bloc 30 kW à 80 + spot": {"type": "bloc_spot", "bloc_kw": 30, "bloc_price_eur_mwh": 80}}
monthly = {}
for name, o in offers.items():
    per_month = []
    for m in range(1, 13):
        mask = pme_load.index.tz_convert(TZ).month == m
        per_month.append(market.cost(pme_load[mask], pme_spot[mask], o).total_eur)
    monthly[name] = per_month
mdf = pd.DataFrame(monthly, index=pd.date_range("2025-01-01", periods=12, freq="MS").strftime("%b"))
f, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4), gridspec_kw={"width_ratios": [2, 1]})
mdf.plot.bar(ax=a1, color=[C["spot"], C["neutral"], C["grid_after"]], width=0.8)
a1.set_ylabel("€ / mois")
a1.set_title("PME fictive : coût mensuel de l'énergie selon l'offre (2025)")
a1.tick_params(axis="x", rotation=0)
spot_m = pme_spot.tz_convert(TZ).resample("MS").mean()
a2.plot(range(12), spot_m.to_numpy(), marker="o", color=C["spot"])
a2.axhline(80, color=C["neutral"], ls="--", label="prix fixe 80")
a2.set_xticks(range(12))
a2.set_xticklabels(mdf.index, fontsize=8)
a2.set_title("Spot moyen mensuel (€/MWh)")
a2.legend()
fig("e2_pme_offres", f)
pme_tot = {k: eur(sum(v)) for k, v in monthly.items()}
pme_load_weighted = float((pme_load * pme_spot).sum() / pme_load.sum())
N["e2"] = {"exemple": {k: eur(v) for k, v in vals.items()}, "pme_annuel": pme_tot,
           "pme_conso_mwh": eur(pme_load.sum() * standard.DT_H / 1000), "pme_prix_moyen_pondere": eur(pme_load_weighted)}

# =====================================================================================
# Étape 3 – PV
# =====================================================================================
print("Étape 3")
f, ax = plt.subplots(figsize=(8, 3.3))
ex = {f"{j} J/cm²": pv.irradiation_to_electric_kw_m2(j) for j in (1000, 1700)}
ax.bar(ex.keys(), ex.values(), color=C["pv"])
for i, (k, v) in enumerate(ex.items()):
    ax.text(i, v, f"{v:.3f} kW/m²", ha="center", va="bottom")
ax.set_ylabel("kW électrique / m²")
ax.set_title("Conversion rayonnement -> puissance (4 h, rendement 20 %) : 0,14 et 0,24 attendus")
fig("e3_conversion", f)

pv100 = pv.power_from_cf(pme_cf, 100)
r_pv = simulate.run(pme_load, pv100, spot_eur_mwh=pme_spot)
r_none = simulate.run(pme_load, spot_eur_mwh=pme_spot)
for day, name in [("2025-06-18", "ete_semaine"), ("2025-06-21", "ete_samedi"), ("2025-01-15", "hiver")]:
    w = plots._window(r_pv, day, 1)
    f, ax = plt.subplots(figsize=(9, 3.5))
    ax.fill_between(w.index, w["pv_self_kw"], step="post", color=C["pv_self"], alpha=0.8, label="PV autoconsommé")
    ax.fill_between(w.index, w["pv_self_kw"], w["pv_kw"], step="post", color=C["export"], alpha=0.7, label="PV revendu")
    ax.plot(w.index, w["load_kw"], drawstyle="steps-post", color=C["load"], label="conso")
    ax.plot(w.index, w["grid_kw"], drawstyle="steps-post", color=C["grid_after"], lw=1, ls="--", label="réseau")
    ax.axhline(0, color="black", lw=0.6)
    ax.set_ylabel("kW")
    ax.set_title(f"PME + 100 kWc – {pd.Timestamp(day).strftime('%A %d/%m/%Y')}")
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    plots._time_axis(ax, 1)
    fig(f"e3_pv_jour_{name}", f)
fig("e3_pv_mensuel", plots.solar_use(r_pv, "PME + 100 kWc : utilisation du solaire"))

sizes = [10, 25, 50, 75, 100, 150, 200, 300, 400]
rows = []
for kwc in sizes:
    r = simulate.run(pme_load, pv.power_from_cf(pme_cf, kwc), spot_eur_mwh=pme_spot)
    s = simulate.summary(r)
    gain = market.cost_spot(r_none["grid_kw"], pme_spot).total_eur - market.cost_spot(r["grid_kw"], pme_spot).total_eur
    capex = economics.capex(pv_kwc=kwc)["pv_eur"]
    no_pay = {"type": "spot", "export_price_eur_mwh": 0}
    gain0 = market.cost(r_none["grid_kw"], pme_spot, no_pay).total_eur - market.cost(r["grid_kw"], pme_spot, no_pay).total_eur
    rows.append({"kwc": kwc, "autoconso": s["taux_autoconso"], "autoproduction": s["taux_autoproduction"], "gain": gain, "gain_sans_revente": gain0,
                 "capex": capex, "retour": capex / (gain - capex * economics.PV_OPEX_RATE) if gain > capex * economics.PV_OPEX_RATE else math.inf})
sz = pd.DataFrame(rows)
f, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4))
a1.plot(sz["kwc"], sz["autoconso"] * 100, marker="o", color=C["pv_self"], label="autoconsommation (part du PV utilisée)")
a1.plot(sz["kwc"], sz["autoproduction"] * 100, marker="o", color=C["bat"], label="autoproduction (part de la conso couverte)")
a1.set_xlabel("puissance PV (kWc)")
a1.set_ylabel("%")
a1.set_title("PME : dimensionnement du PV (sans batterie)")
a1.legend()
a2.plot(sz["kwc"], sz["gain"], marker="o", color=C["grid_after"], label="surplus revendu au spot")
a2.plot(sz["kwc"], sz["gain_sans_revente"], marker="o", color=C["grid"], label="surplus non payé")
a2.set_xlabel("puissance PV (kWc)")
a2.set_ylabel("économie annuelle (€)")
a2.set_title("Économie annuelle sur l'énergie (spot 2025)")
a2.legend()
fig("e3_dimensionnement_pv", f)
s_pv = simulate.summary(r_pv)
N["e3"] = {"conversion": {k: round(v, 4) for k, v in ex.items()}, "pme_pv100": {k: eur(v) for k, v in s_pv.items()},
           "dimensionnement": sz.round(3).to_dict("records"),
           "valeur_pv_autoconso_eur_mwh": eur((r_pv["pv_self_kw"] * pme_spot).sum() / r_pv["pv_self_kw"].sum()),
           "valeur_pv_revendu_eur_mwh": eur((r_pv["pv_export_kw"] * pme_spot).sum() / max(r_pv["pv_export_kw"].sum(), 1e-9))}

# =====================================================================================
# Étape 4 – batterie règle simple (studio + PV, PME + PV)
# =====================================================================================
print("Étape 4")
studio_inputs = scenario.build_inputs(studio_cfg)
st_load, st_spot, st_cf = studio_inputs["load_kw"], studio_inputs["spot_eur_mwh"], studio_inputs["pv_cf"]
st_pv = pv.power_from_cf(st_cf, 3)
bat5 = Battery(5)
r_st_none = simulate.run(st_load, spot_eur_mwh=st_spot)
r_st_pv = simulate.run(st_load, st_pv, spot_eur_mwh=st_spot)
r_st_bat = simulate.run(st_load, st_pv, bat5, SurplusPV(), st_spot)
simulate.check_balance(r_st_bat, bat5)
fig("e4_studio_batterie_semaine", plots.battery_use(r_st_bat, "2025-06-02", 7, "Studio 3 kWc + 5 kWh, règle « surplus PV » – juin"))
fig("e4_studio_batterie_hiver", plots.battery_use(r_st_bat, "2025-01-13", 7, "Studio 3 kWc + 5 kWh, règle « surplus PV » – janvier"))
s_st = {n: simulate.summary(r, b) for n, r, b in [("sans", r_st_none, None), ("pv", r_st_pv, None), ("pv_bat", r_st_bat, bat5)]}
fig("e4_studio_bilan", plots.energy_flows(s_st["pv"], s_st["pv_bat"], "Studio 3 kWc : sans batterie / avec 5 kWh (2025)"))
# vérification de conservation
f, ax = plt.subplots(figsize=(9, 3.4))
e_check = bat5.e_init() + (bat5.eta * r_st_bat["bat_charge_kw"] - r_st_bat["bat_discharge_kw"] / bat5.eta).cumsum() * standard.DT_H
err = (e_check - r_st_bat["energy_kwh"]).abs()
ax.plot(r_st_bat.index, r_st_bat["soc"] * 100, color=C["bat"], lw=0.5)
ax.axhline(10, color=C["grid"], ls="--", lw=1, label="SOC min 10 %")
ax.axhline(90, color=C["grid"], ls="--", lw=1, label="SOC max 90 %")
ax.set_ylim(0, 100)
ax.set_ylabel("SOC (%)")
ax.set_title(f"SOC sur l'année : min {r_st_bat['soc'].min():.1%}, max {r_st_bat['soc'].max():.1%} ; écart de conservation max {err.max():.1e} kWh")
ax.legend(loc="lower left")
ax.xaxis.set_major_formatter(plots.mdates.DateFormatter("%b", tz=TZ))
fig("e4_soc_annee", f)

st_offer = studio_cfg["market"]["offers"][0]
cost_st = {n: market.cost(r["grid_kw"], st_spot, st_offer).total_eur for n, r in
           [("sans", r_st_none), ("pv", r_st_pv), ("pv_bat", r_st_bat)]}
N["e4"] = {"studio": {k: {kk: eur(vv) for kk, vv in v.items()} for k, v in s_st.items()},
           "studio_cout": {k: eur(v) for k, v in cost_st.items()},
           "conservation_ecart_max_kwh": float(err.max()),
           "soc_min": eur(r_st_bat["soc"].min()), "soc_max": eur(r_st_bat["soc"].max())}

# =====================================================================================
# Étape 5 – batterie « prix » (PME, 100 kWh) ; comparaison des stratégies
# =====================================================================================
print("Étape 5")
bat100 = Battery(100)
sub_kw = pme_cfg["grid"]["subscribed_kw"]
pen_eur = pme_cfg["grid"]["penalty_eur_per_kw"]
variants = {
    "PV seul": (pv100, None, None),
    "PV + batterie, surplus PV": (pv100, bat100, SurplusPV()),
    "PV + batterie, prix": (pv100, bat100, PriceThreshold(grid_limit_kw=sub_kw)),
    "PV + batterie, prix sans limite": (pv100, bat100, PriceThreshold()),
    "batterie seule, prix": (None, bat100, PriceThreshold(grid_limit_kw=sub_kw)),
    "batterie seule, surplus PV": (None, bat100, SurplusPV()),
    "batterie seule, peak shaving": (None, bat100, PeakShaving(limit_kw=sub_kw, margin_kw=5)),
    "PV + batterie, peak shaving": (pv100, bat100, PeakShaving(limit_kw=sub_kw, margin_kw=5)),
}
base_energy = market.cost_spot(pme_load, pme_spot).total_eur
base_pen = market.overrun_penalty(pme_load, sub_kw, pen_eur)
results = {}
for name, (p, b, strat) in variants.items():
    r = simulate.run(pme_load, p, b, strat, pme_spot)
    simulate.check_balance(r, b)
    s = simulate.summary(r, b)
    energy = market.cost_spot(r["grid_kw"], pme_spot).total_eur
    pen = market.overrun_penalty(r["grid_kw"], sub_kw, pen_eur)
    results[name] = {"r": r, "s": s, "energy": energy, "pen": pen,
                     "gain_energie": base_energy - energy, "gain_penalites": base_pen["penalite_eur"] - pen["penalite_eur"]}
# gain marginal de la batterie = (PV + batterie) − (PV seul)
f, ax = plt.subplots(figsize=(11, 4.2))
names = list(results)
ge = [results[n]["gain_energie"] for n in names]
gp = [results[n]["gain_penalites"] for n in names]
y = np.arange(len(names))
ax.barh(y - 0.2, ge, 0.4, color=C["grid_after"], label="économie sur l'énergie (spot)")
ax.barh(y + 0.2, gp, 0.4, color=C["bat"], label="économie sur les pénalités (négatif = pénalités en plus)")
for i, n in enumerate(names):
    tot = ge[i] + gp[i]
    ax.text(max(ge[i], gp[i], 0), i, f"   total {_n(tot)} €", va="center", fontsize=9, fontweight="bold")
ax.set_yticks(y)
ax.set_yticklabels(names)
ax.invert_yaxis()
ax.axvline(0, color="black", lw=0.7)
ax.set_xlabel("€ / an (2025) par rapport à « rien »")
ax.set_title("PME : économie annuelle selon l'équipement et la stratégie")
ax.set_xlim(min(min(gp), 0) * 1.1, max(ge) * 1.35)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2)
fig("e5_strategies", f)

# gain journalier vs spread (batterie seule, prix vs surplus)
r_price_only = results["batterie seule, prix"]["r"]


def daily_cost(r):
    return (r["grid_kw"] * standard.DT_H * r["spot_eur_mwh"] / 1000).tz_convert(TZ).resample("D").sum()


d_base = (pme_load * standard.DT_H * pme_spot / 1000).tz_convert(TZ).resample("D").sum()
d_gain = d_base - daily_cost(r_price_only)
f, ax = plt.subplots(figsize=(9, 4))
sc = ax.scatter(spread.reindex(d_gain.index), d_gain, s=10, c=d_gain.index.month, cmap="twilight", alpha=0.8)
ax.axhline(0, color="black", lw=0.6)
ax.set_xlabel("spread du jour (€/MWh)")
ax.set_ylabel("gain du jour (€)")
ax.set_title("Batterie 100 kWh seule, règle « prix » : gain journalier selon le spread")
plt.colorbar(sc, ax=ax, label="mois")
fig("e5_gain_vs_spread", f)
fig("e5_semaine_prix", plots.battery_use(results["PV + batterie, prix"]["r"], "2025-03-17", 7,
                                         "PME : PV 100 kWc + batterie 100 kWh, règle « prix » – mars"))
fig("e5_semaine_prix_ete", plots.battery_use(results["PV + batterie, prix"]["r"], "2025-06-16", 7,
                                             "PME : PV 100 kWc + batterie 100 kWh, règle « prix » – juin"))
high_spread_days = spread[spread > spread.quantile(0.75)].index
d_gain_surplus = d_base - daily_cost(results["batterie seule, surplus PV"]["r"])
N["e5"] = {n: {"gain_energie": eur(v["gain_energie"]), "gain_penalites": eur(v["gain_penalites"]),
               "pointe_kw": eur(v["pen"]["pointe_kw"]), "penalite": eur(v["pen"]["penalite_eur"]),
               "cycles": eur(v["s"].get("cycles_equivalents", 0)), "pertes_kwh": eur(v["s"].get("pertes_batterie_kwh", 0)),
               "charge_reseau_kwh": eur(v["s"]["charge_depuis_reseau_kwh"]), "decharge_kwh": eur(v["s"]["decharge_kwh"])}
           for n, v in results.items()}
N["e5"]["base"] = {"energie": eur(base_energy), "penalite": eur(base_pen["penalite_eur"]), "pointe_kw": eur(base_pen["pointe_kw"]),
                   "mois_depassement": base_pen["mois_en_depassement"]}
N["e5"]["jours_fort_spread"] = {"gain_prix_moyen": eur(d_gain.reindex(high_spread_days).mean()),
                                "gain_surplus_moyen": eur(d_gain_surplus.reindex(high_spread_days).mean()),
                                "gain_prix_moyen_tous": eur(d_gain.mean()),
                                "part_jours_gain_negatif": eur((d_gain < -0.01).mean())}

# =====================================================================================
# Étape 6 – peak shaving
# =====================================================================================
print("Étape 6")
fig("e6_monotone", plots.duration_curve({
    "sans équipement": pme_load,
    "batterie, peak shaving": results["batterie seule, peak shaving"]["r"]["grid_kw"],
    "PV + batterie, prix sans limite": results["PV + batterie, prix sans limite"]["r"]["grid_kw"],
}, limit_kw=sub_kw, title="PME : monotone de puissance soutirée (2025)"))
peak_day = pme_load.tz_convert(TZ).idxmax().strftime("%Y-%m-%d")
fig("e6_jour_pointe", plots.grid_curve(r_none, results["batterie seule, peak shaving"]["r"], peak_day, 2,
                                       title=f"Peak shaving autour du jour de pointe ({peak_day})", limit_kw=sub_kw))
fig("e6_soc_peak_shaving", plots.battery_use(results["batterie seule, peak shaving"]["r"], peak_day, 2,
                                             "Batterie en peak shaving : décharge pendant les pointes"))

# =====================================================================================
# Étape 7 – rentabilité
# =====================================================================================
print("Étape 7")
k = 1.0  # année complète


def profit(name, pv_kwc, bat_kwh, gain, cycles):
    return {lvl: economics.profitability(gain, pv_kwc=pv_kwc, battery_kwh=bat_kwh, battery_cycles_per_year=cycles,
                                         level=lvl) for lvl in ("bas", "median", "haut")}


cases = {
    "PV 100 kWc seul": (100, 0, results["PV seul"]),
    "Batterie 100 kWh seule (prix)": (0, 100, results["batterie seule, prix"]),
    "Batterie 100 kWh seule (peak shaving)": (0, 100, results["batterie seule, peak shaving"]),
}
# batterie ajoutée à un PV existant : gain marginal
marg = results["PV + batterie, prix"]
pv_only = results["PV seul"]
marg_gain = (marg["gain_energie"] + marg["gain_penalites"]) - (pv_only["gain_energie"] + pv_only["gain_penalites"])
prof = {}
for name, (kwc, kwh, res_) in cases.items():
    prof[name] = profit(name, kwc, kwh, res_["gain_energie"] + res_["gain_penalites"], res_["s"].get("cycles_equivalents", 0))
prof["Batterie ajoutée au PV (prix, gain marginal)"] = profit("m", 0, 100, marg_gain, marg["s"]["cycles_equivalents"])
# studio
st_gain_pv = cost_st["sans"] - cost_st["pv"]
st_gain_bat = cost_st["pv"] - cost_st["pv_bat"]
prof["Studio : PV 3 kWc"] = profit("s", 3, 0, st_gain_pv, 0)
prof["Studio : batterie 5 kWh ajoutée"] = profit("s", 0, 5, st_gain_bat, s_st["pv_bat"]["cycles_equivalents"])

f, ax = plt.subplots(figsize=(11, 4.5))
names = list(prof)
y = np.arange(len(names))
colors = {"bas": "#8ab17d", "median": "#e9c46a", "haut": "#e76f51"}
cap = 60
for j, lvl in enumerate(("bas", "median", "haut")):
    vals_ = [min(prof[n][lvl].payback_years, cap) for n in names]
    ax.barh(y + (j - 1) * 0.27, vals_, 0.27, color=colors[lvl], label=f"prix {lvl}")
    for i, n in enumerate(names):
        p = prof[n][lvl].payback_years
        ax.text(min(p, cap), y[i] + (j - 1) * 0.27, " jamais" if p == math.inf else (f" {p:.0f} ans" if p < cap else f" {p:.0f} ans →"),
                va="center", fontsize=7)
for n_i, n in enumerate(names):
    ax.plot([prof[n]["median"].life_years] * 2, [n_i - 0.45, n_i + 0.45], color="black", lw=1.5)
ax.set_yticks(y)
ax.set_yticklabels(names)
ax.invert_yaxis()
ax.set_xlim(0, cap + 8)
ax.set_xlabel("temps de retour (années) ; trait noir = durée de vie retenue")
ax.set_title("Temps de retour simple (2025, prix spot) – rentable si la barre est à gauche du trait noir")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3)
fig("e7_temps_de_retour", f)

# taille de batterie (seule, règle prix) : gain vs coût annualisé
sizes_b = [25, 50, 100, 200, 400]
rows = []
for kwh in sizes_b:
    b = Battery(kwh)
    r = simulate.run(pme_load, None, b, PriceThreshold(grid_limit_kw=sub_kw), pme_spot)
    s = simulate.summary(r, b)
    g = base_energy - market.cost_spot(r["grid_kw"], pme_spot).total_eur + base_pen["penalite_eur"] - market.overrun_penalty(r["grid_kw"], sub_kw, pen_eur)["penalite_eur"]
    life = economics.battery_life_years(s["cycles_equivalents"], b.cycle_life)
    rows.append({"kwh": kwh, "gain": g, "cycles": s["cycles_equivalents"],
                 **{f"annuite_{l}": economics.capex(battery_kwh=kwh, level=l)["batterie_eur"] / life for l in ("bas", "median", "haut")}})
bs = pd.DataFrame(rows)
f, ax = plt.subplots(figsize=(9, 4))
ax.plot(bs["kwh"], bs["gain"], marker="o", color=C["grid_after"], lw=2, label="gain annuel (énergie + pénalités)")
ax.fill_between(bs["kwh"], bs["annuite_bas"], bs["annuite_haut"], color=C["grid"], alpha=0.15, label="coût annualisé (CAPEX / durée de vie), bas–haut")
ax.plot(bs["kwh"], bs["annuite_median"], color=C["grid"], ls="--", label="coût annualisé médian")
ax.set_xscale("log")
ax.set_xticks(sizes_b)
ax.set_xticklabels(sizes_b)
ax.set_xlabel("capacité batterie (kWh), P = 0,5 C")
ax.set_ylabel("€ / an")
ax.set_title("PME, batterie seule (règle prix) : le gain ne couvre pas le coût")
ax.legend()
fig("e7_taille_batterie", f)

# coût d'usure vs spread
wear = {lvl: Battery(100).wear_cost_eur_kwh(economics.capex(battery_kwh=100, level=lvl)["batterie_eur"]) * 1000 for lvl in ("bas", "median", "haut")}
f, ax = plt.subplots(figsize=(9, 3.6))
ax.hist(spread.dropna() * 0.9, bins=40, color=C["spot"], alpha=0.7, label="spread × rendement 90 % (2025)")
for lvl, v in wear.items():
    ax.axvline(v, color=colors[lvl], lw=2, label=f"coût d'usure {lvl} : {v:.0f} €/MWh")
ax.set_xlabel("€/MWh")
ax.set_ylabel("jours")
ax.set_title("Un cycle d'arbitrage par jour n'est rentable que si le spread dépasse le coût d'usure")
ax.legend(fontsize=8)
fig("e7_usure_vs_spread", f)

# sensibilité : surcoût sur chaque kWh acheté (acheminement + taxes), évité par l'autoconsommation
surcharges = [0, 25, 50, 75, 100, 150, 200]
sens_cases = {
    "PME : PV 100 kWc": (pme_load, pme_spot, r_none, results["PV seul"]["r"], 100, 0, 0, None),
    "PME : batterie 100 kWh seule (prix)": (pme_load, pme_spot, r_none, results["batterie seule, prix"]["r"], 0, 100,
                                            results["batterie seule, prix"]["s"]["cycles_equivalents"], None),
    "Studio : PV 3 kWc": (st_load, st_spot, r_st_none, r_st_pv, 3, 0, 0, 11),
    "Studio : batterie 5 kWh ajoutée au PV": (st_load, st_spot, r_st_pv, r_st_bat, 0, 5, s_st["pv_bat"]["cycles_equivalents"], 11),
}
sens = {}
for name, (ld, sp, r0, r1, kwc, kwh, cyc, exp) in sens_cases.items():
    sens[name] = []
    for sc in surcharges:
        o = {"type": "spot", "import_surcharge_eur_mwh": sc}
        if exp is not None:
            o["export_price_eur_mwh"] = exp
        g = market.cost(r0["grid_kw"], sp, o).total_eur - market.cost(r1["grid_kw"], sp, o).total_eur
        p_ = economics.profitability(g, pv_kwc=kwc, battery_kwh=kwh, battery_cycles_per_year=cyc)
        sens[name].append({"surcout": sc, "gain": g, "retour": p_.payback_years, "vie": p_.life_years})
f, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.2))
for (name, rows_), color in zip(sens.items(), [C["pv_self"], C["bat"], C["pv"], C["grid_after"]]):
    d = pd.DataFrame(rows_)
    a1.plot(d["surcout"], d["gain"], marker="o", color=color, label=name)
    a2.plot(d["surcout"], d["retour"].clip(upper=60), marker="o", color=color, label=name)
a1.set_xlabel("surcoût par kWh acheté (€/MWh)")
a1.set_ylabel("gain annuel (€)")
a1.set_yscale("log")
a1.set_title("Gain annuel selon le surcoût évité")
a2.axhline(15, color="black", ls=":", lw=1, label="durée de vie batterie ~15 ans")
a2.axhline(25, color="black", ls="--", lw=1, label="durée de vie PV 25 ans")
a2.set_xlabel("surcoût par kWh acheté (€/MWh)")
a2.set_ylabel("temps de retour, prix médian (ans, plafonné à 60)")
a2.set_title("Temps de retour selon le surcoût évité")
a2.legend(fontsize=7)
fig("e7_sensibilite_surcout", f)

N["e7_sensibilite"] = {n: [{k: (None if (isinstance(v, float) and math.isinf(v)) else round(v, 1)) for k, v in r.items()} for r in rows_]
                       for n, rows_ in sens.items()}

N["e7"] = {n: {lvl: {"capex": eur(p.capex_eur), "gain_net": eur(p.net_annual_eur), "retour": (None if p.payback_years == math.inf else eur(p.payback_years)),
                     "vie": eur(p.life_years), "bilan": eur(p.lifetime_balance_eur)} for lvl, p in v.items()} for n, v in prof.items()}
N["e7"]["taille_batterie"] = bs.round(1).to_dict("records")
N["e7"]["usure_eur_mwh"] = {k: eur(v) for k, v in wear.items()}
N["e7"]["jours_spread_x09_sup_usure_median"] = eur((spread * 0.9 > wear["median"]).mean())

# =====================================================================================
# Étape 8 – les 7 graphiques du plan, via la commande run
# =====================================================================================
print("Étape 8")
res = scenario.run(pme_cfg)
scenario.export_csv(res, ROOT / "results" / "pme" / "resultats.csv")
for p in scenario.make_plots(res, FIG / "e8_pme", "2025-06-16"):
    print("  ", p.name)
res_st = scenario.run(studio_cfg)
for p in scenario.make_plots(res_st, FIG / "e8_studio", "2025-06-02"):
    print("  ", p.name)

(OUT / "chiffres.json").write_text(json.dumps(N, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
print("OK ->", OUT)
