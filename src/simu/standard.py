"""Format interne standard.

DataFrame pandas, index horodaté en UTC au pas de 15 min, colonnes parmi :

| colonne          | unité        | contenu                              |
|------------------|--------------|--------------------------------------|
| load_kw          | kW           | consommation du site                 |
| pv_cf            | kW/kWc (0-1) | facteur de charge PV                 |
| irradiance_wm2   | W/m²         | rayonnement (option site précis)     |
| spot_eur_mwh     | €/MWh        | prix de marché                       |

Chaque valeur est la moyenne sur le pas [t, t + 15 min[ (horodatage = début du pas).
"""

from __future__ import annotations

import pandas as pd

FREQ = "15min"
STEP = pd.Timedelta(FREQ)
DT_H = 0.25  # durée d'un pas en heures

COLUMNS = {
    "load_kw": "kW",
    "pv_cf": "kW/kWc",
    "irradiance_wm2": "W/m²",
    "spot_eur_mwh": "€/MWh",
}


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Vérifie qu'un DataFrame respecte le format standard ; le renvoie tel quel."""
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("l'index doit être un DatetimeIndex")
    if df.index.tz is None or str(df.index.tz) != "UTC":
        raise ValueError(f"l'index doit être en UTC (trouvé : {df.index.tz})")
    if not df.index.is_monotonic_increasing or df.index.has_duplicates:
        raise ValueError("l'index doit être croissant et sans doublon")
    if len(df) > 1:
        steps = df.index.to_series().diff().dropna().unique()
        if len(steps) != 1 or steps[0] != STEP:
            raise ValueError(f"le pas doit être de {FREQ} (trouvé : {list(steps)[:3]})")
    unknown = set(df.columns) - set(COLUMNS)
    if unknown:
        raise ValueError(f"colonnes hors format standard : {sorted(unknown)}")
    return df


def to_15min(s: pd.Series, max_step: str = "1h") -> pd.Series:
    """Ramène une série (valeurs moyennes par intervalle, index UTC régulier) au pas de 15 min.

    - pas plus long (ex. 1 h) : la valeur est répétée sur chaque quart d'heure
      (conserve l'énergie et le prix moyen de l'intervalle) ;
    - pas plus court : moyenne sur chaque quart d'heure ;
    - pas mixte (ex. horaire puis 15 min) : chaque valeur couvre l'intervalle
      jusqu'au point suivant, dans la limite de ``max_step`` (au-delà : trou -> NaN).
    """
    max_step = pd.Timedelta(max_step)
    s = s.sort_index()
    s = s[~s.index.duplicated(keep="first")]
    if len(s) < 2:
        return s
    diffs = s.index.to_series().diff().dropna()
    if (diffs < STEP).any():
        s = s.resample(FREQ).mean()
        diffs = s.index.to_series().diff().dropna()
    # durée couverte par chaque point : jusqu'au suivant, sans dépasser max_step ;
    # le dernier point couvre le pas du point précédent.
    duration = s.index.to_series().diff().shift(-1)
    duration.iloc[-1] = diffs.iloc[-1]
    duration = duration.clip(upper=max(max_step, STEP))
    grid = pd.date_range(s.index[0], s.index[-1] + duration.iloc[-1] - STEP, freq=FREQ)
    values = s.reindex(grid, method="ffill")
    covered_until = (s.index.to_series() + duration).reindex(grid, method="ffill")
    return values.where(grid.to_series() < covered_until)


def energy_kwh(power_kw: pd.Series) -> float:
    """E = Σ P × Δt (kWh) pour une série de puissance en kW au pas standard."""
    return float(power_kw.sum() * DT_H)


def daily_energy_kwh(power_kw: pd.Series, tz: str = "Europe/Paris") -> pd.Series:
    """Énergie par jour local (kWh)."""
    return power_kw.tz_convert(tz).resample("D").sum() * DT_H
