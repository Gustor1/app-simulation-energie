import pandas as pd
import pytest

from simu import standard
from simu.adapters import csv_generic


def test_csv_quelconque_avec_mapping_yaml(tmp_path):
    # CSV « à la française » : point-virgule, virgule décimale, heure locale, puissance en W, pas horaire
    csv = tmp_path / "client.csv"
    csv.write_text(
        "Horodate;Puissance (W);Commentaire\n"
        "01/06/2026 00:00;1000,0;a\n"
        "01/06/2026 01:00;2500,5;b\n",
        encoding="utf-8",
    )
    mapping = tmp_path / "mapping.yaml"
    mapping.write_text(
        'sep: ";"\n'
        'decimal: ","\n'
        "timestamp:\n"
        "  column: Horodate\n"
        '  format: "%d/%m/%Y %H:%M"\n'
        "  timezone: Europe/Paris\n"
        "columns:\n"
        "  load_kw:\n"
        '    column: "Puissance (W)"\n'
        "    factor: 0.001\n",
        encoding="utf-8",
    )
    df = csv_generic.load(csv, mapping)

    standard.validate(df)
    assert list(df.columns) == ["load_kw"]
    assert len(df) == 8
    # 00:00 heure de Paris (été, UTC+2) = 22:00 UTC la veille
    assert df.index[0] == pd.Timestamp("2026-05-31 22:00", tz="UTC")
    assert df["load_kw"].iloc[:4].tolist() == [1.0] * 4
    assert df["load_kw"].iloc[4:].tolist() == [2.5005] * 4
    assert standard.energy_kwh(df["load_kw"]) == pytest.approx(3.5005)


def test_horodatage_en_fin_de_pas_et_plusieurs_colonnes(tmp_path):
    csv = tmp_path / "data.csv"
    csv.write_text(
        "time,kw,price\n"
        "2026-01-01T00:30:00Z,4,50\n"
        "2026-01-01T01:00:00Z,6,70\n",
        encoding="utf-8",
    )
    mapping = {
        "timestamp": {"column": "time", "label": "end"},
        "columns": {"load_kw": {"column": "kw"}, "spot_eur_mwh": {"column": "price"}},
    }
    df = csv_generic.load(csv, mapping)
    assert df.index[0] == pd.Timestamp("2026-01-01 00:00", tz="UTC")
    assert df["load_kw"].tolist() == [4, 4, 6, 6]
    assert df["spot_eur_mwh"].tolist() == [50, 50, 70, 70]


def test_mapping_invalide(tmp_path):
    csv = tmp_path / "x.csv"
    csv.write_text("t,v\n2026-01-01,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="inconnues"):
        csv_generic.load(csv, {"timestamp": {"column": "t"}, "columns": {"conso": {"column": "v"}}})
    with pytest.raises(KeyError, match="absentes"):
        csv_generic.load(csv, {"timestamp": {"column": "t"}, "columns": {"load_kw": {"column": "nope"}}})
