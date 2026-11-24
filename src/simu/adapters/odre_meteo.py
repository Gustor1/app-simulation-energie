"""Adaptateur météo régionale – portail ODRÉ (open data RTE et gestionnaires de réseaux), sans clé.

Jeux de données (Licence Ouverte Etalab ; producteur Weathernews France) :
- ``rayonnement-solaire-vitesse-vent-tri-horaires-regionaux`` : rayonnement solaire global
  horizontal ``ssrd03h`` (W/m²), moyenne régionale, toutes les 3 h, depuis 2016. Valeurs issues
  du modèle du CEPMMT (ECMWF).
- ``temperature-quotidienne-regionale`` : température moyenne quotidienne ``tmoy`` (°C), mise à jour mensuelle.

Convention horaire (vérifiée le 24/11/2026 sur 2025, Grand Est) : la valeur horodatée T (UTC) est la
**moyenne du rayonnement sur les 3 heures précédentes [T − 3 h ; T[**, la convention habituelle des
cumuls du CEPMMT. Elle est confirmée par la corrélation avec la production solaire réelle du Grand Est
(éCO2mix régional) : 0,93, avec le même décalage l'hiver et l'été (donc horodatage bien en UTC).

Passage au pas de 15 min (voir ``disaggregate``) : indice de clarté par bloc, interpolé, multiplié par
la hauteur du soleil calculée pour ``lat``/``lon`` ; énergie conservée jour par jour. Le rayonnement est
donc nul la nuit, et sans marches aux frontières des blocs. Les quelques W/m² que la source attribue à des
blocs de nuit (décalage d'environ 30 min de la donnée) sont reportés sur les heures de jour du même jour UTC.

Codes INSEE des régions : 44 = Grand Est (Strasbourg), 11 = Île-de-France, etc.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from simu import standard
from simu.adapters._http import DEFAULT_CACHE_DIR, get_json
from simu.adapters._period import chunks, day_bounds_utc

BASE_URL = "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets"
IRRADIANCE_DATASET = "rayonnement-solaire-vitesse-vent-tri-horaires-regionaux"
TEMPERATURE_DATASET = "temperature-quotidienne-regionale"
STRASBOURG = {"lat": 48.58, "lon": 7.75}
BLOCK = pd.Timedelta("3h")


def solar_elevation_sin(index_utc: pd.DatetimeIndex, lat: float, lon: float) -> np.ndarray:
    """sin(hauteur du soleil) à chaque instant (formules approchées : déclinaison + équation du temps)."""
    t = index_utc.tz_convert("UTC")
    doy = t.dayofyear.to_numpy()
    hours = t.hour.to_numpy() + t.minute.to_numpy() / 60
    decl = np.radians(23.44) * np.sin(2 * np.pi * (284 + doy) / 365)
    b = 2 * np.pi * (doy - 81) / 364
    eot_min = 9.87 * np.sin(2 * b) - 7.53 * np.cos(b) - 1.5 * np.sin(b)
    solar_time = hours + lon / 15 + eot_min / 60
    hour_angle = np.radians(15 * (solar_time - 12))
    phi = np.radians(lat)
    return np.sin(phi) * np.sin(decl) + np.cos(phi) * np.cos(decl) * np.cos(hour_angle)


def parse_irradiance(records: list[dict]) -> pd.Series:
    """Enregistrements ODRÉ -> série tri-horaire (W/m², moyenne sur [T − 3 h ; T[) indexée par T (UTC)."""
    if not records:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC"), name="ssrd03h")
    s = pd.Series({pd.Timestamp(r["date"]): r["ssrd03h"] for r in records}, dtype=float, name="ssrd03h")
    s.index = pd.DatetimeIndex(s.index).tz_convert("UTC")
    return s.sort_index()


MIN_SUN = 0.05  # sin(hauteur) moyen minimal d'un bloc pour estimer son indice de clarté (≈ 3°)


def disaggregate(block_means: pd.Series, lat: float, lon: float) -> pd.Series:
    """Blocs de 3 h (moyenne sur [T − 3 h ; T[, indexés par T, alignés sur 0 h, 3 h… UTC) -> pas de 15 min.

    1. indice de clarté de chaque bloc : kt = moyenne mesurée ÷ moyenne de sin(hauteur du soleil) ;
    2. kt interpolé linéairement entre les centres des blocs (pas de marches aux frontières) ;
    3. rayonnement = kt × sin(hauteur) (nul la nuit) ;
    4. chaque jour UTC est recalé pour conserver exactement l'énergie des blocs du jour.
    """
    by_start = block_means.copy()
    by_start.index = by_start.index - BLOCK
    grid = pd.date_range(by_start.index.min(), block_means.index.max(), freq=standard.FREQ, inclusive="left")
    sun = np.clip(solar_elevation_sin(grid + standard.STEP / 2, lat, lon), 0, None)
    block_of = grid.floor(BLOCK)
    mean = by_start.reindex(block_of).to_numpy()
    sun_mean = pd.Series(sun, index=grid).groupby(block_of).mean()
    kt = (by_start.reindex(sun_mean.index) / sun_mean).where(sun_mean > MIN_SUN)
    kt.index = kt.index + BLOCK / 2  # centre du bloc
    kt_grid = (kt.reindex(kt.index.union(grid + standard.STEP / 2))
                 .interpolate(method="time", limit_direction="both")
                 .reindex(grid + standard.STEP / 2).to_numpy())
    g = pd.Series(np.nan_to_num(kt_grid) * sun, index=grid)
    g[np.isnan(mean)] = np.nan
    day = grid.floor("D")
    target = pd.Series(mean * standard.DT_H, index=grid).groupby(day).sum(min_count=1)
    got = (g * standard.DT_H).groupby(day).sum(min_count=1)
    scale = (target / got).where(got > 1e-9, 1.0)
    return g * scale.reindex(day).to_numpy()


def load_irradiance(start, end, region: str | int = 44, lat: float | None = None, lon: float | None = None,
                    cache_dir: Path | str | None = DEFAULT_CACHE_DIR) -> pd.DataFrame:
    """Rayonnement global horizontal (W/m²) au pas de 15 min, colonne standard ``irradiance_wm2``.

    ``lat``/``lon`` : point utilisé pour la forme intra-bloc (défaut : Strasbourg).
    """
    lat = STRASBOURG["lat"] if lat is None else lat
    lon = STRASBOURG["lon"] if lon is None else lon
    parts = []
    for c0, c1 in chunks(start, end, days=92):
        t0, t1 = day_bounds_utc(c0, c1)
        where = (f"code_insee_region='{region}' AND date > '{t0.isoformat()}' "
                 f"AND date <= '{(t1 + BLOCK).isoformat()}'")
        records = get_json(f"{BASE_URL}/{IRRADIANCE_DATASET}/exports/json",
                           {"where": where, "select": "date,ssrd03h", "order_by": "date"}, cache_dir=cache_dir, timeout=120)
        parts.append(parse_irradiance(records))
    blocks = pd.concat(parts)
    blocks = blocks[~blocks.index.duplicated(keep="first")].sort_index()
    if blocks.empty:
        raise ValueError(f"aucun rayonnement pour la région {region} entre {start} et {end}")
    s = disaggregate(blocks, lat, lon)
    t0, t1 = day_bounds_utc(start, end)
    s = s[(s.index >= t0) & (s.index < t1)]
    full = pd.date_range(t0, t1, freq=standard.FREQ, inclusive="left")
    return standard.validate(s.reindex(full).rename("irradiance_wm2").to_frame())


def load_temperature(start, end, region: str | int = 44, cache_dir: Path | str | None = DEFAULT_CACHE_DIR,
                     max_gap_days: int = 2) -> pd.Series:
    """Température moyenne quotidienne (°C) de la région, indexée par date (jour local)."""
    parts = []
    margin = pd.Timedelta(days=max_gap_days + 1)  # marge pour interpoler un jour absent en bord de période
    for c0, c1 in chunks(pd.Timestamp(start) - margin, pd.Timestamp(end) + margin, days=366):
        where = f"code_insee_region={int(region)} AND date >= '{c0}' AND date <= '{c1}'"
        parts += get_json(f"{BASE_URL}/{TEMPERATURE_DATASET}/exports/json",
                          {"where": where, "select": "date,tmoy", "order_by": "date"}, cache_dir=cache_dir, timeout=120)
    s = pd.Series({pd.Timestamp(r["date"][:10]): r["tmoy"] for r in parts}, dtype=float, name="tmoy")
    expected = pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="D")
    wide = pd.date_range(pd.Timestamp(start) - margin, pd.Timestamp(end) + margin, freq="D")
    s = s.reindex(wide)
    missing = s.reindex(expected)[s.reindex(expected).isna()].index
    if len(missing):
        # jours isolés absents du jeu (constaté : ex. 31/01/2025) -> interpolation si trou ≤ 2 jours
        filled = s.interpolate(limit=max_gap_days, limit_area="inside")
        if filled.isna().any():
            first = filled[filled.isna()].index[0].date()
            raise ValueError(f"température manquante (ex. {first}) : trou > {max_gap_days} jours ou en bord de période ; "
                             "le jeu ODRÉ est mis à jour mensuellement")
        warnings.warn(f"températures : {len(missing)} jours absents interpolés ({', '.join(str(d.date()) for d in missing[:5])}"
                      f"{'…' if len(missing) > 5 else ''})", stacklevel=2)
        s = filled
    s = s.reindex(expected)
    s.index = s.index.date
    return s
