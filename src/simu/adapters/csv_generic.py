"""Adaptateur CSV générique : n'importe quel CSV -> format standard, via un mapping.

Exemple de mapping (dict Python ou fichier YAML) :

```yaml
sep: ";"            # séparateur (défaut ",")
decimal: ","        # séparateur décimal (défaut ".")
timestamp:
  column: Horodate
  format: "%d/%m/%Y %H:%M"   # optionnel (sinon détection pandas)
  timezone: Europe/Paris     # fuseau des horodatages sans fuseau (défaut UTC)
  label: start               # start : horodatage = début du pas ; end : fin du pas
columns:
  load_kw:                   # colonne standard
    column: "Puissance (W)"  # colonne du CSV
    factor: 0.001            # multiplicateur d'unité (W -> kW)
  spot_eur_mwh:
    column: Prix
```

Les valeurs sont supposées être des moyennes sur le pas ; elles sont ramenées au pas
de 15 min (répétition si pas plus long, moyenne si pas plus court).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from simu import standard


def read_mapping(mapping: dict | str | Path) -> dict:
    if isinstance(mapping, (str, Path)):
        with open(mapping, encoding="utf-8") as f:
            return yaml.safe_load(f)
    return dict(mapping)


def load(path: str | Path, mapping: dict | str | Path) -> pd.DataFrame:
    """Lit ``path`` et renvoie un DataFrame au format standard selon ``mapping``."""
    m = read_mapping(mapping)
    ts = m.get("timestamp") or {}
    columns = m.get("columns") or {}
    if "column" not in ts:
        raise ValueError("mapping : 'timestamp.column' est obligatoire")
    if not columns:
        raise ValueError("mapping : 'columns' doit associer au moins une colonne standard")
    unknown = set(columns) - set(standard.COLUMNS)
    if unknown:
        raise ValueError(f"mapping : colonnes standard inconnues {sorted(unknown)} ; attendues {list(standard.COLUMNS)}")

    raw = pd.read_csv(path, sep=m.get("sep", ","), decimal=m.get("decimal", "."), encoding=m.get("encoding", "utf-8"))
    missing = [c for c in [ts["column"], *(spec["column"] for spec in columns.values())] if c not in raw.columns]
    if missing:
        raise KeyError(f"colonnes absentes du CSV : {missing} (présentes : {list(raw.columns)})")

    index = pd.to_datetime(raw[ts["column"]], format=ts.get("format"))
    if index.dt.tz is None:
        index = index.dt.tz_localize(ts.get("timezone", "UTC"), ambiguous="infer", nonexistent="raise")
    index = pd.DatetimeIndex(index.dt.tz_convert("UTC"))

    out = {}
    for name, spec in columns.items():
        values = pd.to_numeric(raw[spec["column"]], errors="coerce") * float(spec.get("factor", 1.0))
        s = pd.Series(values.values, index=index, name=name)
        if ts.get("label", "start") == "end":
            step = s.index.to_series().diff().dropna().mode().iloc[0]
            s.index = s.index - step
        out[name] = standard.to_15min(s)
    return standard.validate(pd.DataFrame(out))
