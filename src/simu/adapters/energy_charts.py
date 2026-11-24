"""Adaptateur Energy-Charts (Fraunhofer ISE) – https://api.energy-charts.info/

Données sous licence CC BY 4.0 (citer « Energy-Charts / Fraunhofer ISE »,
et pour les prix « Bundesnetzagentur | SMARD.de » comme indiqué par l'API).

- ``load_spot``  : prix day-ahead (€/MWh) -> colonne ``spot_eur_mwh``.
  Pas de 15 min depuis le 1er octobre 2025, horaire avant (répété sur 4 quarts d'heure).
- ``load_pv_cf`` : production solaire France (``public_power``, MW) ÷ puissance installée
  (``installed_power``, filière « Solar AC », GW, valeur ANNUELLE) -> colonne ``pv_cf``.
  Pas de 15 min en 2026, horaire sur une partie de 2025.
- ``load``       : les deux réunis.

Constatés le 24/11/2026 : l'endpoint ``installed_power`` n'existe qu'en ``time_step=yearly``
(``monthly`` -> 404) et la dernière année publiée est 2025.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd

from simu import standard
from simu.adapters._http import DEFAULT_CACHE_DIR, get_json
from simu.adapters._period import capacity_for_index, chunks, day_bounds_utc

BASE_URL = "https://api.energy-charts.info"
SOLAR_NAME = "Solar"
INSTALLED_SOLAR_NAME = "Solar AC"


def parse_price(payload: dict) -> pd.Series:
    """JSON de ``/price`` -> série €/MWh indexée en UTC."""
    index = pd.to_datetime(payload["unix_seconds"], unit="s", utc=True)
    return pd.Series(payload["price"], index=index, name="spot_eur_mwh", dtype=float)


def parse_public_power(payload: dict, name: str = SOLAR_NAME) -> pd.Series:
    """JSON de ``/public_power`` -> série de production (MW) de la filière ``name``."""
    index = pd.to_datetime(payload["unix_seconds"], unit="s", utc=True)
    for production_type in payload["production_types"]:
        if production_type["name"] == name:
            return pd.Series(production_type["data"], index=index, name=name, dtype=float)
    names = [p["name"] for p in payload["production_types"]]
    raise KeyError(f"filière {name!r} absente de public_power (disponibles : {names})")


def parse_installed_power(payload: dict, name: str = INSTALLED_SOLAR_NAME) -> dict[int, float]:
    """JSON de ``/installed_power?time_step=yearly`` -> {année: MW}."""
    for production_type in payload["production_types"]:
        if production_type["name"] == name:
            return {
                int(year): float(gw) * 1000
                for year, gw in zip(payload["time"], production_type["data"])
                if gw is not None
            }
    raise KeyError(f"filière {name!r} absente de installed_power")


def _fetch(endpoint: str, params: dict, start, end, cache_dir, parser) -> pd.Series:
    parts = []
    for c0, c1 in chunks(start, end):
        payload = get_json(f"{BASE_URL}/{endpoint}", {**params, "start": c0, "end": c1}, cache_dir=cache_dir)
        parts.append(parser(payload))
    s = pd.concat(parts).sort_index()
    s = s[~s.index.duplicated(keep="first")]
    t0, t1 = day_bounds_utc(start, end)
    s = standard.to_15min(s)
    return s[(s.index >= t0) & (s.index < t1)]


def load_spot(start, end, bzn: str = "FR", cache_dir: Path | str | None = DEFAULT_CACHE_DIR) -> pd.DataFrame:
    """Prix spot day-ahead de la zone ``bzn`` du jour ``start`` au jour ``end`` inclus."""
    s = _fetch("price", {"bzn": bzn}, start, end, cache_dir, parse_price)
    return standard.validate(s.rename("spot_eur_mwh").to_frame())


def installed_solar_mw(country: str = "fr", cache_dir: Path | str | None = DEFAULT_CACHE_DIR) -> dict[int, float]:
    payload = get_json(
        f"{BASE_URL}/installed_power", {"country": country, "time_step": "yearly"}, cache_dir=cache_dir
    )
    return parse_installed_power(payload)


def load_pv_cf(
    start,
    end,
    country: str = "fr",
    installed_mw: float | None = None,
    cache_dir: Path | str | None = DEFAULT_CACHE_DIR,
) -> pd.DataFrame:
    """Facteur de charge PV national = production solaire ÷ puissance installée.

    ``installed_mw`` : puissance installée imposée (MW) ; sinon valeur annuelle Energy-Charts.
    """
    production = _fetch("public_power", {"country": country}, start, end, cache_dir, parse_public_power)
    if installed_mw is not None:
        capacity = pd.Series(float(installed_mw), index=production.index)
    else:
        capacity = capacity_for_index(production.index, installed_solar_mw(country, cache_dir), "Energy-Charts")
    cf = (production / capacity).clip(lower=0)
    if (cf > 1).any():
        warnings.warn("pv_cf > 1 : puissance installée sous-estimée ?", stacklevel=2)
    return standard.validate(cf.rename("pv_cf").to_frame())


def load(start, end, bzn: str = "FR", country: str = "fr", installed_mw: float | None = None,
         cache_dir: Path | str | None = DEFAULT_CACHE_DIR) -> pd.DataFrame:
    """Prix spot + facteur de charge PV, format standard."""
    spot = load_spot(start, end, bzn=bzn, cache_dir=cache_dir)
    pv = load_pv_cf(start, end, country=country, installed_mw=installed_mw, cache_dir=cache_dir)
    return standard.validate(spot.join(pv, how="outer"))
