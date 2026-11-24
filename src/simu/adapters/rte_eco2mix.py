"""Adaptateur RTE éCO2mix via le portail ODRÉ (sans clé) – https://odre.opendatasoft.com/

Jeux de données (constatés le 24/11/2026) :
- ``eco2mix-national-cons-def`` : historique consolidé/définitif, jusqu'au 31/08/2026.
  Pas de 15 min, mais les champs ``solaire`` et ``consommation`` ne sont renseignés
  qu'aux demi-heures (valeurs vides à :15 et :45) -> interpolation linéaire.
- ``eco2mix-national-tr`` : temps réel, depuis le 01/09/2026 seulement.

Puissance installée : jeu ``parc-prod-par-filiere``, champ ``parc_solaire`` (MW, valeur
ANNUELLE ; dernière année publiée : 2025, 30 437 MW). Energy-Charts donne 28 250 MW
pour 2025 (« Solar AC ») : les deux sources diffèrent d'environ 7 %.

Sortie : colonne ``pv_cf`` = solaire (MW) ÷ parc solaire (MW).
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd

from simu import standard
from simu.adapters._http import DEFAULT_CACHE_DIR, get_json
from simu.adapters._period import capacity_for_index, chunks, day_bounds_utc

BASE_URL = "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets"
DEFAULT_DATASET = "eco2mix-national-cons-def"


def parse_records(records: list[dict], field: str = "solaire") -> pd.Series:
    """Liste d'enregistrements ODRÉ (``date_heure`` ISO + champ) -> série UTC."""
    if not records:
        return pd.Series(dtype=float, name=field, index=pd.DatetimeIndex([], tz="UTC"))
    df = pd.DataFrame(records)
    index = pd.to_datetime(df["date_heure"], utc=True)
    return pd.Series(pd.to_numeric(df[field]).values, index=index, name=field, dtype=float)


def parse_capacity(records: list[dict], field: str = "parc_solaire") -> dict[int, float]:
    """Enregistrements de ``parc-prod-par-filiere`` -> {année: MW}."""
    out = {}
    for record in records:
        value = record.get(field)
        if value is None:
            continue
        if isinstance(value, str):  # certains champs sont publiés avec une virgule décimale
            value = value.replace(",", ".")
        out[int(record["annee"])] = float(value)
    return out


def _export(dataset: str, where: str, select: str, cache_dir) -> list[dict]:
    """Endpoint ``exports/json`` : pas de limite de 100 lignes ni de pagination."""
    return get_json(
        f"{BASE_URL}/{dataset}/exports/json",
        {"where": where, "select": select, "order_by": "date_heure"},
        cache_dir=cache_dir,
        timeout=120,
    )


def load_series(start, end, field: str = "solaire", dataset: str = DEFAULT_DATASET,
                cache_dir: Path | str | None = DEFAULT_CACHE_DIR) -> pd.Series:
    """Champ éCO2mix (MW) du jour ``start`` au jour ``end`` inclus, au pas de 15 min."""
    parts = []
    for c0, c1 in chunks(start, end):
        t0, t1 = day_bounds_utc(c0, c1)
        t1 = t1 + pd.Timedelta("30min")  # point suivant, pour interpoler le dernier quart d'heure
        where =f"date_heure >= '{t0.isoformat()}' AND date_heure < '{t1.isoformat()}'"
        parts.append(parse_records(_export(dataset, where, f"date_heure,{field}", cache_dir), field))
    s = pd.concat(parts).sort_index()
    s = s[~s.index.duplicated(keep="first")]
    if s.empty:
        raise ValueError(f"{dataset} : aucune donnée entre {start} et {end}")
    s = standard.to_15min(s.interpolate(method="time", limit=1, limit_area="inside"))
    t0, t1 = day_bounds_utc(start, end)
    return s[(s.index >= t0) & (s.index < t1)]


def installed_solar_mw(cache_dir: Path | str | None = DEFAULT_CACHE_DIR) -> dict[int, float]:
    payload = get_json(
        f"{BASE_URL}/parc-prod-par-filiere/exports/json", {"select": "annee,parc_solaire"}, cache_dir=cache_dir
    )
    return parse_capacity(payload)


def load_pv_cf(start, end, installed_mw: float | None = None, dataset: str = DEFAULT_DATASET,
               cache_dir: Path | str | None = DEFAULT_CACHE_DIR) -> pd.DataFrame:
    """Facteur de charge PV national (format standard, colonne ``pv_cf``)."""
    production = load_series(start, end, "solaire", dataset, cache_dir)
    if installed_mw is not None:
        capacity = pd.Series(float(installed_mw), index=production.index)
    else:
        capacity = capacity_for_index(production.index, installed_solar_mw(cache_dir), "RTE (ODRÉ)")
    cf = (production / capacity).clip(lower=0)
    if (cf > 1).any():
        warnings.warn("pv_cf > 1 : puissance installée sous-estimée ?", stacklevel=2)
    return standard.validate(cf.rename("pv_cf").to_frame())


load = load_pv_cf
