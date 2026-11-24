"""Cœur du simulateur : bilan énergétique pas à pas.

Bilan à chaque pas (P_grid > 0 = achat) :
    P_grid = P_load − P_pv + P_charge − P_décharge
Priorité : autoconsommer, puis stocker (selon la stratégie), puis revendre.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from simu import standard
from simu.models.battery import Battery
from simu.standard import DT_H


def run(
    load_kw: pd.Series,
    pv_kw: pd.Series | None = None,
    battery: Battery | None = None,
    strategy=None,
    spot_eur_mwh: pd.Series | None = None,
) -> pd.DataFrame:
    """Renvoie un DataFrame (index standard) avec toutes les grandeurs par pas (kW, kWh, SOC)."""
    index = load_kw.index
    load = load_kw.to_numpy(dtype=float)
    pv = np.zeros(len(index)) if pv_kw is None else pv_kw.reindex(index).fillna(0).to_numpy(dtype=float)
    spot = (
        np.full(len(index), np.nan) if spot_eur_mwh is None else spot_eur_mwh.reindex(index).to_numpy(dtype=float)
    )
    net = load - pv
    charge = np.zeros(len(index))
    discharge = np.zeros(len(index))
    energy = np.zeros(len(index))  # énergie stockée en FIN de pas

    if battery is not None:
        if strategy is None:
            raise ValueError("une batterie demande une stratégie")
        inputs = pd.DataFrame({"load_kw": load, "pv_kw": pv, "spot_eur_mwh": spot}, index=index)
        strategy.prepare(inputs, battery)
        e = battery.e_init()
        for i in range(len(index)):
            request = strategy(i, net[i], spot[i], e, battery)
            charge[i], discharge[i], e = battery.step(e, request)
            energy[i] = e

    grid = net + charge - discharge
    out = pd.DataFrame(
        {
            "load_kw": load,
            "pv_kw": pv,
            "pv_self_kw": np.minimum(pv, load),  # PV consommé directement
            "bat_charge_kw": charge,
            "bat_discharge_kw": discharge,
            "grid_kw": grid,
            "grid_import_kw": np.clip(grid, 0, None),
            "grid_export_kw": np.clip(-grid, 0, None),
            "spot_eur_mwh": spot,
        },
        index=index,
    )
    surplus = np.clip(pv - load, 0, None)
    out["pv_to_battery_kw"] = np.minimum(charge, surplus)
    out["grid_to_battery_kw"] = charge - out["pv_to_battery_kw"]
    out["pv_export_kw"] = np.clip(surplus - out["pv_to_battery_kw"], 0, None)
    if battery is not None:
        out["energy_kwh"] = energy
        out["soc"] = energy / battery.capacity_kwh
    return out


def summary(result: pd.DataFrame, battery: Battery | None = None) -> dict:
    """Bilans d'énergie (kWh) sur la période."""
    e = {c: float(result[c].sum() * DT_H) for c in result.columns if c.endswith("_kw")}
    s = {
        "conso_kwh": e["load_kw"],
        "pv_kwh": e["pv_kw"],
        "pv_autoconso_directe_kwh": e["pv_self_kw"],
        "pv_vers_batterie_kwh": e["pv_to_battery_kw"],
        "pv_revendu_kwh": e["pv_export_kw"],
        "achat_reseau_kwh": e["grid_import_kw"],
        "revente_reseau_kwh": e["grid_export_kw"],
        "charge_kwh": e["bat_charge_kw"],
        "decharge_kwh": e["bat_discharge_kw"],
        "charge_depuis_reseau_kwh": e["grid_to_battery_kw"],
    }
    s["taux_autoconso"] = (
        (s["pv_kwh"] - s["pv_revendu_kwh"]) / s["pv_kwh"] if s["pv_kwh"] else float("nan")
    )
    s["taux_autoproduction"] = 1 - s["achat_reseau_kwh"] / s["conso_kwh"] if s["conso_kwh"] else float("nan")
    if battery is not None:
        s["cycles_equivalents"] = s["decharge_kwh"] / battery.eta / battery.usable_kwh
        e0 = battery.e_init()
        e_end = float(result["energy_kwh"].iloc[-1])
        s["pertes_batterie_kwh"] = s["charge_kwh"] - s["decharge_kwh"] - (e_end - e0)
    return s


def check_balance(result: pd.DataFrame, battery: Battery | None = None, tol: float = 1e-6) -> None:
    """Vérifie bilan réseau, bornes et conservation de l'énergie ; lève AssertionError sinon."""
    r = result
    lhs = r["grid_kw"]
    rhs = r["load_kw"] - r["pv_kw"] + r["bat_charge_kw"] - r["bat_discharge_kw"]
    assert np.allclose(lhs, rhs, atol=tol), "bilan P_grid faux"
    assert ((r["bat_charge_kw"] > tol) & (r["bat_discharge_kw"] > tol)).sum() == 0, "charge et décharge simultanées"
    if battery is not None:
        assert (r["energy_kwh"] >= battery.e_min - tol).all() and (r["energy_kwh"] <= battery.e_max + tol).all(), "SOC hors bornes"
        assert (r[["bat_charge_kw", "bat_discharge_kw"]] <= battery.p_max_kw + tol).all().all(), "P_max dépassée"
        stored = battery.e_init() + (battery.eta * r["bat_charge_kw"] - r["bat_discharge_kw"] / battery.eta).cumsum() * DT_H
        assert np.allclose(stored, r["energy_kwh"], atol=1e-6), "énergie non conservée"


standard  # noqa: B018  (format d'entrée : voir simu.standard)
