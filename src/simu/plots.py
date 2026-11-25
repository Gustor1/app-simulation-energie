"""Graphiques (étape 8) : les 7 graphiques de PLAN_SIMULATION.md §4.6, et quelques autres.

Toutes les fonctions prennent des résultats de ``simu.simulate.run`` et renvoient une
figure matplotlib ; ``save(fig, path)`` l'enregistre en PNG.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from simu.standard import DT_H  # noqa: E402

TZ = "Europe/Paris"
C = {
    "load": "#33415c",
    "pv": "#f2a900",
    "pv_self": "#e07a00",
    "bat": "#2a9d8f",
    "export": "#8ab17d",
    "grid": "#c0392b",
    "grid_after": "#2c7fb8",
    "spot": "#6a4c93",
    "neutral": "#999999",
}
plt.rcParams.update(
    {
        "figure.dpi": 110,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "legend.frameon": False,
    }
)


def _n(x: float) -> str:
    """Nombre entier, espace fine comme séparateur de milliers."""
    return f"{x:,.0f}".replace(",", "\u202f")


def save(fig, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def local(df):
    return df.tz_convert(TZ)


def _time_axis(ax, span_days: float):
    if span_days <= 2:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Hh", tz=TZ))
    elif span_days <= 14:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%a %d/%m", tz=TZ))
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b", tz=TZ))


def _period_energy(series_kw: pd.DataFrame, freq: str) -> pd.DataFrame:
    return local(series_kw).resample(freq).sum() * DT_H


def _freq_for(index) -> tuple[str, str]:
    days = (index[-1] - index[0]).days + 1
    return ("D", "jour") if days <= 62 else ("MS", "mois")


# --- 1. Utilisation du solaire --------------------------------------------------------


def solar_use(r: pd.DataFrame, title="Utilisation du solaire"):
    freq, label = _freq_for(r.index)
    e = _period_energy(r[["pv_self_kw", "pv_to_battery_kw", "pv_export_kw"]], freq)
    fig, ax = plt.subplots(figsize=(10, 4))
    x = e.index.strftime("%d/%m" if freq == "D" else "%b")
    bottom = np.zeros(len(e))
    for col, name, color in [
        ("pv_self_kw", "autoconsommé directement", C["pv_self"]),
        ("pv_to_battery_kw", "stocké en batterie", C["bat"]),
        ("pv_export_kw", "revendu au réseau", C["export"]),
    ]:
        ax.bar(x, e[col], bottom=bottom, color=color, label=name, width=0.8)
        bottom += e[col].to_numpy()
    total = r["pv_kw"].sum() * DT_H
    used = total - r["pv_export_kw"].sum() * DT_H
    ax.set_title(f"{title} – {_n(total)} kWh produits, {used / total:.0%} utilisés sur place" if total else title)
    ax.set_ylabel(f"kWh par {label}")
    ax.legend(loc="upper left")
    if len(x) > 20:
        ax.set_xticks(range(0, len(x), max(1, len(x) // 15)))
    return fig


# --- 2. Utilisation de la batterie ----------------------------------------------------


def battery_use(r: pd.DataFrame, start=None, days: int = 7, title="Utilisation de la batterie"):
    w = _window(r, start, days)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True, gridspec_kw={"height_ratios": [1, 1.3]})
    ax1.fill_between(w.index, w["soc"] * 100, color=C["bat"], alpha=0.35, step="post")
    ax1.plot(w.index, w["soc"] * 100, color=C["bat"], drawstyle="steps-post")
    ax1.set_ylabel("SOC (%)")
    ax1.set_ylim(0, 100)
    ax1.set_title(title)
    ax2.bar(w.index, w["pv_to_battery_kw"], width=DT_H / 24, color=C["pv"], label="charge depuis le PV", align="edge")
    ax2.bar(w.index, w["grid_to_battery_kw"], width=DT_H / 24, bottom=w["pv_to_battery_kw"], color=C["grid_after"],
            label="charge depuis le réseau", align="edge")
    ax2.bar(w.index, -w["bat_discharge_kw"], width=DT_H / 24, color=C["grid"], label="décharge", align="edge")
    if w["spot_eur_mwh"].notna().any():
        ax3 = ax2.twinx()
        ax3.plot(w.index, w["spot_eur_mwh"], color=C["spot"], lw=1, alpha=0.8, drawstyle="steps-post", label="spot")
        ax3.set_ylabel("spot (€/MWh)", color=C["spot"])
        ax3.grid(False)
    ax2.axhline(0, color="black", lw=0.6)
    ax2.set_ylabel("kW (+ charge / − décharge)")
    ax2.legend(loc="upper left", ncol=3)
    _time_axis(ax2, days)
    return fig


# --- 3. Courbe de charge brute -------------------------------------------------------


def load_curve(r: pd.DataFrame, start=None, days: int = 7, title="Courbe de charge brute du site", by=None):
    """Semaine type + profil journalier moyen. ``by`` : DataFrame kW par appareil (empilé)."""
    w = _window(r, start, days)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4), gridspec_kw={"width_ratios": [2.2, 1]})
    if by is not None:
        bw = by.loc[w.index]
        ax1.stackplot(bw.index, bw.T.to_numpy(), labels=bw.columns, step="post", alpha=0.85)
        ax1.legend(loc="upper left", ncol=3, fontsize=8)
    else:
        ax1.fill_between(w.index, w["load_kw"], step="post", color=C["load"], alpha=0.8)
    ax1.set_ylabel("kW")
    ax1.set_title(f"{title} – {days} jours")
    _time_axis(ax1, days)
    loc = local(r["load_kw"])
    profile = loc.groupby(loc.index.hour + loc.index.minute / 60).agg(["mean", lambda s: s.quantile(0.1), lambda s: s.quantile(0.9)])
    profile.columns = ["moyenne", "p10", "p90"]
    ax2.fill_between(profile.index, profile["p10"], profile["p90"], color=C["load"], alpha=0.2, label="10 %–90 % des jours")
    ax2.plot(profile.index, profile["moyenne"], color=C["load"], label="moyenne")
    ax2.set_xlabel("heure")
    ax2.set_xticks(range(0, 25, 6))
    ax2.set_title("Profil journalier")
    ax2.legend(loc="upper left", fontsize=8)
    return fig


# --- 4. Courbe de charge achetée ------------------------------------------------------


def grid_curve(before: pd.DataFrame, after: pd.DataFrame, start=None, days: int = 7,
               title="Ce qu'on achète au réseau", limit_kw: float | None = None):
    b, a = _window(before, start, days), _window(after, start, days)
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(b.index, b["grid_kw"], color=C["grid"], lw=1, drawstyle="steps-post", label="sans équipement", alpha=0.7)
    ax.plot(a.index, a["grid_kw"], color=C["grid_after"], lw=1.3, drawstyle="steps-post", label="avec équipement")
    ax.fill_between(a.index, a["grid_kw"], where=a["grid_kw"] < 0, color=C["export"], alpha=0.5, step="post", label="revente")
    if limit_kw is not None:
        ax.axhline(limit_kw, color="black", ls="--", lw=1, label=f"puissance souscrite {limit_kw:g} kW")
    ax.axhline(0, color="black", lw=0.6)
    ax.set_ylabel("kW (> 0 achat, < 0 revente)")
    ax.set_title(title)
    ax.legend(loc="upper left", ncol=4)
    _time_axis(ax, days)
    return fig


# --- 5. Coût de l'énergie -------------------------------------------------------------


def energy_cost(before: pd.DataFrame, after: pd.DataFrame, export_price_eur_mwh: float | None = None,
                title=None, import_surcharge_eur_mwh: float = 0.0):
    freq, label = _freq_for(before.index)
    if title is None:
        title = ("Coût de l'énergie (achat − revente, au spot)" if not import_surcharge_eur_mwh
                 else f"Coût (spot + {_n(import_surcharge_eur_mwh)} €/MWh d'acheminement et taxes, − revente)")

    def cost(r):
        imp = r["grid_import_kw"] * DT_H * (r["spot_eur_mwh"] + import_surcharge_eur_mwh) / 1000
        exp_price = r["spot_eur_mwh"] if export_price_eur_mwh is None else export_price_eur_mwh
        exp = r["grid_export_kw"] * DT_H * exp_price / 1000
        return local(imp - exp).resample(freq).sum()

    cb, ca = cost(before), cost(after)
    x = np.arange(len(cb))
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(x - 0.2, cb, width=0.4, color=C["grid"], label=f"sans équipement : {_n(cb.sum())} €")
    ax.bar(x + 0.2, ca, width=0.4, color=C["grid_after"], label=f"avec équipement : {_n(ca.sum())} €")
    ax.set_xticks(x)
    ax.set_xticklabels(cb.index.strftime("%d/%m" if freq == "D" else "%b"))
    ax.set_ylabel(f"€ par {label}")
    ax.set_title(f"{title} – économie {_n(cb.sum() - ca.sum())} €")
    ax.legend(loc="upper right")
    return fig


# --- 6 et 7. Coût batterie / panneaux : flux cumulés -----------------------------------


def investment(annual_gain_eur: float, capex_by_level: dict, annual_opex_by_level: dict | None = None,
               life_years: float = 15, title="Coût de l'équipement et retour sur investissement"):
    """Trésorerie cumulée (−CAPEX + gains nets) pour les niveaux de prix bas / médian / haut."""
    annual_opex_by_level = annual_opex_by_level or {}
    years = np.arange(0, int(np.ceil(life_years)) + 1)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4), gridspec_kw={"width_ratios": [1, 2]})
    levels = list(capex_by_level)
    colors = {"bas": "#8ab17d", "median": "#e9c46a", "haut": "#e76f51"}
    ax1.bar(levels, [capex_by_level[k] for k in levels], color=[colors.get(k, C["neutral"]) for k in levels])
    for i, k in enumerate(levels):
        ax1.text(i, capex_by_level[k], f"{_n(capex_by_level[k])} €", ha="center", va="bottom", fontsize=9)
    ax1.set_title("Investissement (CAPEX)")
    ax1.set_ylabel("€")
    for k in levels:
        net = annual_gain_eur - annual_opex_by_level.get(k, 0)
        cash = -capex_by_level[k] + net * years
        ax2.plot(years, cash, marker="o", ms=3, color=colors.get(k, C["neutral"]), label=f"prix {k}")
        if net > 0 and capex_by_level[k] / net <= years[-1]:
            ax2.axvline(capex_by_level[k] / net, color=colors.get(k, C["neutral"]), ls=":", lw=1)
    ax2.axhline(0, color="black", lw=0.8)
    ax2.set_xlabel("années")
    ax2.set_ylabel("trésorerie cumulée (€)")
    ax2.set_title(f"{title}\n(gain annuel {_n(annual_gain_eur)} €, durée de vie {life_years:.0f} ans)")
    ax2.legend(loc="upper left")
    return fig


# --- graphiques complémentaires -------------------------------------------------------


def spot_overview(spot: pd.Series, title="Prix spot France"):
    loc = local(spot)
    daily = loc.resample("D").agg(["min", "max", "mean"])
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4), gridspec_kw={"width_ratios": [2, 1]})
    ax1.fill_between(daily.index, daily["min"], daily["max"], color=C["spot"], alpha=0.25, label="min–max du jour")
    ax1.plot(daily.index, daily["mean"], color=C["spot"], lw=1, label="moyenne du jour")
    ax1.axhline(0, color="black", lw=0.6)
    ax1.set_ylabel("€/MWh")
    ax1.set_title(title)
    ax1.legend(loc="upper left")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b", tz=TZ))
    for season, months, color in [("hiver", [12, 1, 2], "#2c7fb8"), ("été", [6, 7, 8], "#f2a900")]:
        s = loc[loc.index.month.isin(months)]
        if len(s):
            p = s.groupby(s.index.hour).mean()
            ax2.plot(p.index, p, color=color, marker="o", ms=3, label=season)
    ax2.set_xlabel("heure")
    ax2.set_title("Profil horaire moyen")
    ax2.legend()
    return fig


def daily_spread(spot: pd.Series, title="Spread journalier (max − min)"):
    loc = local(spot)
    spread = loc.resample("D").max() - loc.resample("D").min()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 3.8), gridspec_kw={"width_ratios": [2, 1]})
    ax1.bar(spread.index, spread, width=1, color=C["spot"], alpha=0.8)
    ax1.axhspan(80, 180, color="#e9c46a", alpha=0.25, label="fourchette 80–180 €/MWh (plan)")
    ax1.set_ylabel("€/MWh")
    ax1.set_title(f"{title} – médiane {spread.median():.0f} €/MWh")
    ax1.legend(loc="upper left")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b", tz=TZ))
    ax2.hist(spread.dropna(), bins=30, color=C["spot"], alpha=0.8)
    ax2.axvspan(80, 180, color="#e9c46a", alpha=0.25)
    ax2.set_xlabel("spread (€/MWh)")
    ax2.set_ylabel("nombre de jours")
    ax2.set_title("Répartition")
    return fig


def pv_profiles(pv_cf: pd.DataFrame, title="Facteur de charge PV national par mois"):
    """``pv_cf`` : DataFrame d'une ou plusieurs colonnes (sources)."""
    loc = local(pv_cf)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4))
    cmap = plt.get_cmap("viridis")
    first = loc.columns[0]
    for m in range(1, 13):
        s = loc[loc.index.month == m][first]
        if len(s):
            p = s.groupby(s.index.hour + s.index.minute / 60).mean()
            ax1.plot(p.index, p, color=cmap((m - 1) / 11), label=pd.Timestamp(2025, m, 1).strftime("%b"))
    ax1.set_xlabel("heure locale")
    ax1.set_ylabel("kW / kWc")
    ax1.set_title(f"{title} ({first})")
    ax1.legend(ncol=2, fontsize=7)
    monthly = loc.resample("MS").sum() * DT_H
    x = np.arange(len(monthly))
    width = 0.8 / len(monthly.columns)
    for i, col in enumerate(monthly.columns):
        ax2.bar(x + i * width, monthly[col], width=width, label=f"{col} : {monthly[col].sum():.0f} kWh/kWc/an")
    ax2.set_xticks(x + width * (len(monthly.columns) - 1) / 2)
    ax2.set_xticklabels(monthly.index.strftime("%b"))
    ax2.set_ylabel("kWh / kWc")
    ax2.set_title("Productible mensuel")
    ax2.legend(fontsize=8)
    return fig


def energy_flows(summary_before: dict, summary_after: dict, title="Bilan énergétique annuel",
                 names=("sans équipement", "avec équipement")):
    labels = ["conso", "PV produit", "achat réseau", "revente", "pertes batterie"]
    keys = ["conso_kwh", "pv_kwh", "achat_reseau_kwh", "revente_reseau_kwh", "pertes_batterie_kwh"]
    b = [summary_before.get(k, 0) for k in keys]
    a = [summary_after.get(k, 0) for k in keys]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.bar(x - 0.2, b, 0.4, color=C["grid"], label=names[0])
    ax.bar(x + 0.2, a, 0.4, color=C["grid_after"], label=names[1])
    for xi, v in zip(x + 0.2, a):
        ax.text(xi, v, f"{_n(v)}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("kWh")
    ax.set_title(title)
    ax.legend()
    return fig


def duration_curve(series: dict, limit_kw: float | None = None, title="Monotone de puissance soutirée"):
    fig, ax = plt.subplots(figsize=(9, 3.8))
    colors = [C["grid"], C["grid_after"], C["bat"], C["pv"]]
    for (name, s), color in zip(series.items(), colors):
        v = np.sort(s.to_numpy())[::-1]
        ax.plot(np.arange(len(v)) * DT_H, v, color=color, label=f"{name} (pointe {v[0]:.1f} kW)")
    if limit_kw is not None:
        ax.axhline(limit_kw, color="black", ls="--", lw=1, label=f"puissance souscrite {limit_kw:g} kW")
    ax.set_xlabel("heures de l'année où la puissance est dépassée")
    ax.set_ylabel("kW")
    ax.set_title(title)
    ax.legend()
    return fig


def _window(r: pd.DataFrame, start, days: int) -> pd.DataFrame:
    loc_index = r.index.tz_convert(TZ)
    t0 = pd.Timestamp(start).tz_localize(TZ) if start is not None else loc_index[0].normalize()
    t1 = t0 + pd.Timedelta(days=days)
    mask = (loc_index >= t0) & (loc_index < t1)
    return r[mask]
