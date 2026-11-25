"""Adaptateur Enedis open data (https://opendata.enedis.fr, API data-fair, sans clé).

Courbes de charge **réelles** agrégées au pas de 30 min, par segment de clients :

- ``conso-sup36-region`` : sites > 36 kVA, par région, secteur d'activité (S1 agriculture, S2 industrie,
  S3 tertiaire) et plage de puissance souscrite (ex. ``P4: ]250-1000] kVA``) ;
- ``conso-inf36`` : sites ≤ 36 kVA, maille nationale, par profil (ex. ``RES1 (+ RES1WE)`` = résidentiel
  option base) et plage de puissance.

Pour chaque demi-heure, la courbe d'un **site moyen** du segment = énergie soutirée totale ÷ nombre de sites
(les sous-profils du segment sont additionnés). Puissance moyenne (kW) = Wh ÷ 1000 ÷ 0,5 h.
Horodate = début de la demi-heure. La courbe peut ensuite être mise à l'échelle de la consommation
annuelle du client (``annual_kwh``) : on garde la **forme** réelle, pas le niveau.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pandas as pd

from simu import standard
from simu.adapters._http import DEFAULT_CACHE_DIR, get_json
from simu.adapters._period import day_bounds_utc

BASE = "https://opendata.enedis.fr/data-fair/api/v1/datasets"
FIELDS = "horodate,profil,nb_points_soutirage,total_energie_soutiree_wh"


def parse_lines(rows: list[dict]) -> pd.Series:
    """Lignes de l'API -> puissance moyenne d'un site (kW), index UTC au pas de 30 min."""
    if not rows:
        return pd.Series(dtype=float, name="load_kw")
    df = pd.DataFrame(rows)
    df["horodate"] = pd.to_datetime(df["horodate"], utc=True)
    g = df.groupby("horodate")[["total_energie_soutiree_wh", "nb_points_soutirage"]].sum()
    g = g[g["nb_points_soutirage"] > 0]
    kw = g["total_energie_soutiree_wh"] / g["nb_points_soutirage"] / 1000 / 0.5
    return kw.sort_index().rename("load_kw")


def fetch(dataset: str, filters: dict, start, end, tz: str = "Europe/Paris",
          cache_dir: Path | str | None = DEFAULT_CACHE_DIR) -> list[dict]:
    """Toutes les lignes du segment entre ``start`` et ``end`` (jours inclus, heure locale)."""
    t0, t1 = day_bounds_utc(start, end, tz)
    params = {"size": 10000, "sort": "horodate", "select": FIELDS,
              "horodate_gte": t0.isoformat(), "horodate_lt": t1.isoformat()}
    params.update({f"{k}_eq": v for k, v in filters.items()})
    url, rows = f"{BASE}/{dataset}/lines", []
    while url:
        page = get_json(url, params, cache_dir=cache_dir, timeout=120)
        rows += page.get("results", [])
        if not page.get("results") or not page.get("next"):
            break
        # l'URL « next » contient tous les filtres + le curseur « after » : on la redécoupe pour le cache
        nxt = urlsplit(page["next"])
        url, params = f"{nxt.scheme}://{nxt.netloc}{nxt.path}", dict(parse_qsl(nxt.query))
    return rows


def load_profile(start, end, *, dataset: str = "conso-sup36-region", region: str | int | None = None,
                 sector: str | None = None, power_range: str | None = None, profile: str | None = None,
                 annual_kwh: float | None = None, tz: str = "Europe/Paris",
                 cache_dir: Path | str | None = DEFAULT_CACHE_DIR) -> pd.DataFrame:
    """Courbe de charge réelle d'un site moyen du segment, au format standard (``load_kw``, pas 15 min).

    ``annual_kwh`` : si donné, la courbe est multipliée pour que l'énergie **sur la période** corresponde
    à ``annual_kwh`` × (durée de la période ÷ 365 jours).
    """
    filters = {}
    if region is not None:
        filters["code_region"] = str(region)
    if sector:
        filters["secteur_activite"] = sector
    if power_range:
        filters["plage_de_puissance_souscrite"] = power_range
    if profile:
        filters["profil"] = profile
    kw = parse_lines(fetch(dataset, filters, start, end, tz, cache_dir))
    if kw.empty:
        raise ValueError(f"Enedis open data : aucune donnée pour {dataset} {filters} du {start} au {end}")
    load = standard.to_15min(kw, max_step="30min")
    if annual_kwh is not None:
        days = (load.index[-1] - load.index[0]).total_seconds() / 86400 + standard.DT_H / 24
        load = load * (annual_kwh * days / 365) / standard.energy_kwh(load)
    return load.rename("load_kw").to_frame()
