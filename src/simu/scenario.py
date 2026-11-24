"""Lecture d'un scénario YAML et exécution (étapes 0 à 2 : conso seule + coût d'achat).

Structure (voir ``scenarios/studio.yaml``) :

```yaml
period: {start: 2026-11-16, end: 2026-11-22, timezone: Europe/Paris}
site:                         # courbe de charge
  adapter: bottom_up          # appliances: [...], seed: 42
  # adapter: csv_generic      # load: chemin.csv, mapping: chemin.yaml (ou dict)
market:
  prices:
    adapter: energy_charts    # bzn: FR
    # adapter: csv_generic    # path: ..., mapping: ...
  offers:
    - {type: spot}
    - {type: fixed, price_eur_mwh: 80}
    - {type: bloc_spot, bloc_kw: 30, bloc_price_eur_mwh: 85}
```

Les chemins relatifs sont résolus par rapport au dossier du fichier YAML.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from simu import standard
from simu.adapters import csv_generic, energy_charts
from simu.models import load_bottom_up, market


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
        return load_bottom_up.simulate(site["appliances"], start, end, tz=tz, seed=site.get("seed", 0))
    if adapter == "csv_generic":
        df = csv_generic.load(_path(config, site["load"]), _path(config, site["mapping"]))
        return df[["load_kw"]]
    raise ValueError(f"adaptateur de site inconnu : {adapter!r} (disponibles : bottom_up, csv_generic)")


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


def build_inputs(config: dict) -> pd.DataFrame:
    """Données d'entrée au format standard, restreintes à la période du scénario."""
    df = load_site(config)
    needs_spot = any(o.get("type") != "fixed" for o in config["market"].get("offers", []))
    if needs_spot:
        df = df.join(load_prices(config), how="left")
    return standard.validate(df)


def run(config: dict) -> tuple[pd.DataFrame, list[market.Cost]]:
    """Étape 2 : sans équipement, la puissance réseau est la consommation."""
    inputs = build_inputs(config)
    p_grid = inputs["load_kw"]
    spot = inputs.get("spot_eur_mwh")
    costs = [market.cost(p_grid, spot, offer) for offer in config["market"]["offers"]]
    return inputs, costs
