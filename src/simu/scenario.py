"""Lecture d'un scénario YAML et exécution.

Structure (voir ``scenarios/``) :

```yaml
period: {start: 2025-01-01, end: 2025-12-31, timezone: Europe/Paris}
site:                         # courbe de charge
  adapter: bottom_up          # appliances: [...], seed: 42
  # adapter: csv_generic      # load: chemin.csv, mapping: chemin.yaml (ou dict)
market:
  prices:
    adapter: energy_charts    # bzn: FR
    # adapter: csv_generic    # path: ..., mapping: ...
  offers:                     # la PREMIÈRE offre sert au calcul de rentabilité
    - {type: spot}
    - {type: fixed, price_eur_mwh: 80}
    - {type: bloc_spot, bloc_kw: 30, bloc_price_eur_mwh: 85}
pv: {peak_kw: 100, source: energy_charts}           # optionnel (ou rte_eco2mix, csv_generic)
battery: {capacity_kwh: 100, c_rate: 0.5}          # optionnel (paramètres de models/battery.py)
strategy: {type: price_threshold}                  # surplus_pv (défaut), price_threshold, peak_shaving
grid: {subscribed_kw: 60, penalty_eur_per_hour: 12.41}  # optionnel : pénalités (ou penalty_eur_per_kw)
```

Les chemins relatifs sont résolus par rapport au dossier du fichier YAML.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import yaml

from simu import economics, simulate, standard
from simu.adapters import csv_generic, enedis_open, energy_charts, odre_meteo, rte_eco2mix
from simu.models import load_bottom_up, market, pv
from simu.models.battery import Battery
from simu.strategies import rules


def _n(x: float) -> str:
    return f"{x:,.0f}".replace(",", "\u202f")

DEFAULT_MAX_PV_GAP_HOURS = 1.0  # trous de PV ≤ max_gap_hours : interpolés ; au-delà : erreur


def read(path: str | Path) -> dict:
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    config["_dir"] = path.parent
    return config


def _path(config: dict, value):
    if isinstance(value, dict) or value is None:
        return value
    p = Path(value)
    return p if p.is_absolute() else Path(config.get("_dir", ".")) / p


def _period(config: dict):
    period = config["period"]
    return period["start"], period["end"], period.get("timezone", "Europe/Paris")


def load_site(config: dict) -> pd.DataFrame:
    site = config["site"]
    start, end, tz = _period(config)
    adapter = site.get("adapter", "bottom_up")
    if adapter == "bottom_up":
        appliances = [_resolve_temperatures(a, start, end) for a in site["appliances"]]
        return load_bottom_up.simulate(appliances, start, end, tz=tz, seed=site.get("seed", 0))
    if adapter == "csv_generic":
        df = csv_generic.load(_path(config, site["load"]), _path(config, site["mapping"]))
        return df[["load_kw"]]
    if adapter == "enedis_open":
        # courbe réelle d'un site moyen du segment (open data Enedis), mise à l'échelle de annual_kwh
        opts = {k: site[k] for k in ("dataset", "region", "sector", "power_range", "profile", "annual_kwh") if k in site}
        return enedis_open.load_profile(start, end, tz=tz, **opts)
    raise ValueError(f"adaptateur de site inconnu : {adapter!r} (disponibles : bottom_up, csv_generic, enedis_open)")


def _resolve_temperatures(appliance, start, end):
    """Chauffage : ``temperatures: {source: odre, region: 44}`` -> températures réelles quotidiennes."""
    if isinstance(appliance, dict) and isinstance(appliance.get("temperatures"), dict)             and appliance["temperatures"].get("source") == "odre":
        region = appliance["temperatures"].get("region", 44)
        return {**appliance, "temperatures": odre_meteo.load_temperature(start, end, region).to_dict()}
    return appliance


def load_prices(config: dict) -> pd.DataFrame:
    prices = config["market"]["prices"]
    start, end, _ = _period(config)
    adapter = prices.get("adapter", "energy_charts")
    if adapter == "energy_charts":
        return energy_charts.load_spot(start, end, bzn=prices.get("bzn", "FR"))
    if adapter == "csv_generic":
        df = csv_generic.load(_path(config, prices["path"]), _path(config, prices["mapping"]))
        return df[["spot_eur_mwh"]]
    raise ValueError(f"adaptateur de prix inconnu : {adapter!r} (disponibles : energy_charts, csv_generic)")


def load_pv_cf(config: dict) -> pd.DataFrame:
    """Donnée solaire : ``pv_cf`` (facteur de charge) ou ``irradiance_wm2`` (rayonnement), selon la source.

    - energy_charts : facteur de charge national ;
    - rte_eco2mix   : facteur de charge national, ou régional avec ``region: 44`` ;
    - odre_irradiance : rayonnement régional réel (``region``, ``lat``, ``lon``) -> chaîne du plan §4.3 ;
    - csv_generic   : fichier du client.
    """
    pv_cfg = config["pv"]
    start, end, _ = _period(config)
    source = pv_cfg.get("source", "energy_charts")
    if source == "energy_charts":
        return energy_charts.load_pv_cf(start, end, installed_mw=pv_cfg.get("installed_mw"))
    if source == "rte_eco2mix":
        return rte_eco2mix.load_pv_cf(start, end, installed_mw=pv_cfg.get("installed_mw"), region=pv_cfg.get("region"))
    if source == "odre_irradiance":
        return odre_meteo.load_irradiance(start, end, pv_cfg.get("region", 44), pv_cfg.get("lat"), pv_cfg.get("lon"))
    if source == "csv_generic":
        df = csv_generic.load(_path(config, pv_cfg["path"]), _path(config, pv_cfg["mapping"]))
        return df[[c for c in ("pv_cf", "irradiance_wm2") if c in df]]
    raise ValueError(f"source PV inconnue : {source!r} (energy_charts, rte_eco2mix, odre_irradiance, csv_generic)")


def pv_power(config: dict, inputs: pd.DataFrame) -> pd.Series:
    """Production PV (kW) à partir du facteur de charge ou du rayonnement."""
    pv_cfg = config["pv"]
    if "irradiance_wm2" in inputs:
        return pv.power_from_irradiance_kwc(inputs["irradiance_wm2"], pv_cfg["peak_kw"],
                                            pv_cfg.get("efficiency", 0.20), pv_cfg.get("pmax_w_m2", 250.0))
    return pv.power_from_cf(inputs["pv_cf"], pv_cfg["peak_kw"])


def _strategy_type(config: dict):
    s = config.get("strategy")
    return s if isinstance(s, str) or s is None else s.get("type")


def build_inputs(config: dict) -> pd.DataFrame:
    """Données d'entrée au format standard, restreintes à la période du scénario."""
    df = load_site(config)
    offers = config["market"].get("offers", [])
    needs_spot = any(o.get("type") != "fixed" for o in offers) or _strategy_type(config) == "price_threshold"
    if needs_spot:
        df = df.join(load_prices(config), how="left")
    if config.get("pv"):
        solar = load_pv_cf(config)
        df = df.join(solar, how="left")
        col = solar.columns[0]
        missing = int(df[col].isna().sum())
        if missing:
            max_gap_h = float(config["pv"].get("max_gap_hours", DEFAULT_MAX_PV_GAP_HOURS))
            steps = int(max_gap_h / standard.DT_H)
            cf = df[col]
            gap_id = cf.notna().cumsum()
            gap_len = cf.isna().groupby(gap_id).transform("sum")
            filled = cf.interpolate(limit_direction="both")
            df[col] = cf.where(cf.notna() | (gap_len > steps), filled)
            left = int(df[col].isna().sum())
            if left:
                raise ValueError(f"{col} manquant sur {left} pas (trous > {max_gap_h:g} h ; voir pv.max_gap_hours)")
            warnings.warn(f"{col} : {missing} pas manquants interpolés (trous ≤ {max_gap_h:g} h)", stacklevel=2)
    return standard.validate(df)


@dataclass
class Results:
    config: dict
    inputs: pd.DataFrame
    before: pd.DataFrame  # sans équipement
    after: pd.DataFrame  # avec équipement
    costs_before: list
    costs_after: list
    battery: Battery | None
    penalty_before: dict | None = None
    penalty_after: dict | None = None
    profitability: list = field(default_factory=list)

    @property
    def summary_before(self) -> dict:
        return simulate.summary(self.before)

    @property
    def summary_after(self) -> dict:
        return simulate.summary(self.after, self.battery)

    @property
    def annual_factor(self) -> float:
        days = (self.inputs.index[-1] - self.inputs.index[0] + standard.STEP) / pd.Timedelta(days=1)
        return 365 / days


def run(config: dict) -> Results:
    inputs = build_inputs(config)
    spot = inputs["spot_eur_mwh"] if "spot_eur_mwh" in inputs else None
    pv_kw = pv_power(config, inputs) if config.get("pv") else None
    battery = Battery(**config["battery"]) if config.get("battery") else None
    strategy_cfg = config.get("strategy") or ("surplus_pv" if battery else None)
    if isinstance(strategy_cfg, str):
        strategy_cfg = {"type": strategy_cfg}
    if strategy_cfg and strategy_cfg["type"] == "price_threshold" and config.get("grid"):
        # par défaut, la charge depuis le réseau respecte la puissance souscrite
        strategy_cfg = {"grid_limit_kw": config["grid"]["subscribed_kw"], **strategy_cfg}
    if strategy_cfg and strategy_cfg["type"] == "price_threshold":
        # le surcoût par kWh acheté (1re offre) entre dans le calcul « l'arbitrage vaut-il le coup ? »
        surcharge = config["market"]["offers"][0].get("import_surcharge_eur_mwh", 0)
        strategy_cfg = {"surcharge_eur_mwh": surcharge, **strategy_cfg}
    strategy = rules.from_config(strategy_cfg)

    before = simulate.run(inputs["load_kw"], None, None, None, spot)
    after = simulate.run(inputs["load_kw"], pv_kw, battery, strategy, spot)
    simulate.check_balance(after, battery)

    offers = config["market"]["offers"]
    res = Results(
        config, inputs, before, after,
        [market.cost(before["grid_kw"], spot, o) for o in offers],
        [market.cost(after["grid_kw"], spot, o) for o in offers],
        battery,
    )

    extra_before = extra_after = 0.0
    grid_cfg = config.get("grid")
    if grid_cfg:
        tz = _period(config)[2]
        res.penalty_before = market.grid_penalty(before["grid_kw"], grid_cfg, tz)
        res.penalty_after = market.grid_penalty(after["grid_kw"], grid_cfg, tz)
        extra_before, extra_after = res.penalty_before["penalite_eur"], res.penalty_after["penalite_eur"]

    if pv_kw is not None or battery is not None:
        k = res.annual_factor
        gain = ((res.costs_before[0].total_eur + extra_before) - (res.costs_after[0].total_eur + extra_after)) * k
        cycles = res.summary_after.get("cycles_equivalents", 0) * k
        for level in ("bas", "median", "haut"):
            res.profitability.append(
                economics.profitability(
                    gain,
                    pv_kwc=config["pv"]["peak_kw"] if config.get("pv") else 0,
                    battery_kwh=battery.capacity_kwh if battery else 0,
                    battery_cycles_per_year=cycles,
                    battery_cycle_life=battery.cycle_life if battery else 5000,
                    level=level,
                )
            )
    return res


def export_csv(res: Results, path: str | Path) -> Path:
    """Export de toutes les grandeurs par pas (UTC + heure locale)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = res.after.copy()
    out.insert(0, "heure_locale", out.index.tz_convert(_period(res.config)[2]).strftime("%Y-%m-%d %H:%M"))
    out["grid_sans_equipement_kw"] = res.before["grid_kw"]
    out.to_csv(path, index_label="utc", float_format="%.4f")
    return path


def make_plots(res: Results, out_dir: str | Path, week_start=None) -> list[Path]:
    """Les 7 graphiques de PLAN_SIMULATION.md §4.6 (ceux qui ont un sens pour ce scénario)."""
    from simu import plots

    out_dir = Path(out_dir)
    paths = []
    limit = (res.config.get("grid") or {}).get("subscribed_kw")
    if res.after["pv_kw"].sum() > 0:
        paths.append(plots.save(plots.solar_use(res.after), out_dir / "1_utilisation_solaire.png"))
    if res.battery is not None:
        paths.append(plots.save(plots.battery_use(res.after, week_start), out_dir / "2_utilisation_batterie.png"))
    paths.append(plots.save(plots.load_curve(res.after, week_start), out_dir / "3_courbe_de_charge_brute.png"))
    paths.append(plots.save(plots.grid_curve(res.before, res.after, week_start, limit_kw=limit), out_dir / "4_courbe_achetee.png"))
    if res.after["spot_eur_mwh"].notna().all():
        offer = res.config["market"]["offers"][0]  # même offre que les tableaux de rentabilité
        paths.append(plots.save(plots.energy_cost(res.before, res.after, offer.get("export_price_eur_mwh"),
                                                  import_surcharge_eur_mwh=offer.get("import_surcharge_eur_mwh", 0.0)),
                                out_dir / "5_cout_energie.png"))
    if res.profitability:
        gains = component_gains(res)
        levels = ("bas", "median", "haut")
        if res.battery is not None:
            b = gains["batterie"]
            cap = {lvl: economics.capex(battery_kwh=res.battery.capacity_kwh, level=lvl)["batterie_eur"] for lvl in levels}
            title = f"Batterie {res.battery.capacity_kwh:g} kWh : coût et retour" + (" (gain ajouté au PV)" if res.config.get("pv") else "")
            fig = plots.investment(b["gain_eur"], cap, None, b["vie_ans"], title)
            paths.append(plots.save(fig, out_dir / "6_cout_batterie.png"))
        if res.config.get("pv"):
            p = gains["pv"]
            kwc = res.config["pv"]["peak_kw"]
            cap = {lvl: economics.capex(pv_kwc=kwc, level=lvl)["pv_eur"] for lvl in levels}
            opex = {lvl: c * economics.PV_OPEX_RATE for lvl, c in cap.items()}
            fig = plots.investment(p["gain_eur"], cap, opex, economics.PV_LIFE_YEARS, f"Panneaux {kwc:g} kWc : coût et retour")
            paths.append(plots.save(fig, out_dir / "7_cout_panneaux.png"))
    return paths


def component_gains(res: Results) -> dict:
    """Gain annuel attribué à chaque équipement (première offre + pénalités) :
    PV = (rien) − (PV seul) ; batterie = (PV seul ou rien) − (installation complète)."""
    offer = res.config["market"]["offers"][0]
    spot = res.inputs["spot_eur_mwh"] if "spot_eur_mwh" in res.inputs else None
    grid_cfg = res.config.get("grid")
    tz = _period(res.config)[2]

    def total(r):
        c = market.cost(r["grid_kw"], spot, offer).total_eur
        if grid_cfg:
            c += market.grid_penalty(r["grid_kw"], grid_cfg, tz)["penalite_eur"]
        return c

    k = res.annual_factor
    out = {}
    middle = res.before
    if res.config.get("pv"):
        middle = simulate.run(res.inputs["load_kw"], res.after["pv_kw"], None, None, spot)
        out["pv"] = {"gain_eur": (total(res.before) - total(middle)) * k}
    if res.battery is not None:
        cycles = res.summary_after["cycles_equivalents"] * k
        out["batterie"] = {
            "gain_eur": (total(middle) - total(res.after)) * k,
            "cycles_an": cycles,
            "vie_ans": economics.battery_life_years(cycles, res.battery.cycle_life),
        }
    return out
