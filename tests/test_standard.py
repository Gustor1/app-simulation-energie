import pandas as pd
import pytest

from simu import standard


def utc_range(start, periods, freq):
    return pd.date_range(start, periods=periods, freq=freq, tz="UTC")


def test_horaire_vers_15min_repete_la_valeur():
    s = pd.Series([10.0, 20.0], index=utc_range("2026-01-01", 2, "1h"))
    out = standard.to_15min(s)
    assert list(out) == [10, 10, 10, 10, 20, 20, 20, 20]
    assert out.index[-1] == pd.Timestamp("2026-01-01 01:45", tz="UTC")
    # l'énergie est conservée : 10 kW × 1 h + 20 kW × 1 h = 30 kWh
    assert standard.energy_kwh(out) == 30


def test_5min_vers_15min_fait_la_moyenne():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], index=utc_range("2026-01-01", 6, "5min"))
    assert list(standard.to_15min(s)) == [2.0, 5.0]


def test_pas_mixte_horaire_puis_15min():
    hourly = pd.Series([1.0, 2.0], index=utc_range("2026-01-01 00:00", 2, "1h"))
    quarter = pd.Series([3.0, 4.0, 5.0], index=utc_range("2026-01-01 02:00", 3, "15min"))
    out = standard.to_15min(pd.concat([hourly, quarter]))
    assert list(out) == [1, 1, 1, 1, 2, 2, 2, 2, 3, 4, 5]


def test_trou_reste_vide():
    idx = pd.DatetimeIndex(["2026-01-01 00:00", "2026-01-01 01:00", "2026-01-01 04:00"], tz="UTC")
    out = standard.to_15min(pd.Series([1.0, 2.0, 3.0], index=idx))
    assert out.loc["2026-01-01 01:45"].item() == 2
    assert out.loc["2026-01-01 02:00":"2026-01-01 03:45"].isna().all()
    assert out.loc["2026-01-01 04:00"].item() == 3


def test_validate_refuse_les_formats_non_standard():
    good = pd.DataFrame({"load_kw": [1.0, 2.0]}, index=utc_range("2026-01-01", 2, "15min"))
    standard.validate(good)
    with pytest.raises(ValueError, match="UTC"):
        standard.validate(good.tz_convert("Europe/Paris"))
    with pytest.raises(ValueError, match="pas"):
        standard.validate(pd.DataFrame({"load_kw": [1.0, 2.0]}, index=utc_range("2026-01-01", 2, "1h")))
    with pytest.raises(ValueError, match="colonnes"):
        standard.validate(good.rename(columns={"load_kw": "conso"}))


def test_energie_par_jour_local():
    # 1 kW constant sur 2 jours locaux (Paris) -> 24 kWh/jour
    idx = pd.date_range("2026-06-01", "2026-06-03", freq="15min", tz="Europe/Paris", inclusive="left")
    s = pd.Series(1.0, index=idx.tz_convert("UTC"))
    assert list(standard.daily_energy_kwh(s)) == [24, 24]
