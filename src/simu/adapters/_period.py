"""Découpage d'une période en morceaux (requêtes plus courtes = moins de timeouts)."""

from __future__ import annotations

import warnings

import pandas as pd

LOCAL_TZ = "Europe/Paris"


def day_bounds_utc(start, end, tz: str = LOCAL_TZ) -> tuple[pd.Timestamp, pd.Timestamp]:
    """[start 00:00 local ; (end + 1 jour) 00:00 local[ en UTC. ``end`` est inclus."""
    t0 = pd.Timestamp(start).tz_localize(tz) if pd.Timestamp(start).tz is None else pd.Timestamp(start)
    t1 = pd.Timestamp(end).tz_localize(tz) if pd.Timestamp(end).tz is None else pd.Timestamp(end)
    return t0.normalize().tz_convert("UTC"), (t1.normalize() + pd.Timedelta(days=1)).tz_convert("UTC")


def chunks(start, end, days: int = 31) -> list[tuple[str, str]]:
    """Liste de (début, fin) inclusifs au format AAAA-MM-JJ."""
    d0, d1 = pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()
    if d1 < d0:
        raise ValueError("end doit être >= start")
    out = []
    while d0 <= d1:
        stop = min(d0 + pd.Timedelta(days=days - 1), d1)
        out.append((d0.strftime("%Y-%m-%d"), stop.strftime("%Y-%m-%d")))
        d0 = stop + pd.Timedelta(days=1)
    return out


def capacity_for_index(index: pd.DatetimeIndex, by_year: dict[int, float], source: str) -> pd.Series:
    """Puissance installée (MW) associée à chaque horodatage, d'après une valeur par année.

    Année absente -> dernière année disponible, avec un avertissement.
    """
    if not by_year:
        raise ValueError(f"aucune puissance installée disponible ({source})")
    last = max(by_year)
    years = pd.Series(index.tz_convert(LOCAL_TZ).year, index=index)
    missing = sorted(set(years) - set(by_year))
    if missing:
        warnings.warn(
            f"{source} : puissance installée absente pour {missing}, "
            f"valeur de {last} utilisée ({by_year[last]:.0f} MW) -> facteur de charge surestimé",
            stacklevel=3,
        )
    return years.map(lambda y: by_year.get(y, by_year[last])).astype(float)
