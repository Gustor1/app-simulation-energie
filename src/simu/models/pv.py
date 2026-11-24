"""Production photovoltaïque (PLAN_SIMULATION.md, section 4.3).

Deux variantes :
- par défaut, facteur de charge national : ``P_pv = pv_cf × kWc`` ;
- site précis, rayonnement : ``P_pv = rayonnement (kW/m²) × surface × rendement``,
  plafonné à ``Pmax`` (250 W/m² de panneau d'après le plan).

Conversion d'un cumul de rayonnement (J/cm²) en puissance électrique moyenne :
``J/cm² × 10⁴ -> J/m² ; ÷ 3,6·10⁶ -> kWh/m² ; ÷ durée (h) -> kW/m² ; × rendement``.
"""

from __future__ import annotations

import pandas as pd

J_PER_KWH = 3.6e6
CM2_PER_M2 = 1e4


def power_from_cf(pv_cf: pd.Series, peak_kw: float) -> pd.Series:
    """Production (kW) d'une installation de ``peak_kw`` kWc à partir du facteur de charge."""
    return (pv_cf * peak_kw).rename("pv_kw")


def irradiation_j_cm2_to_kwh_m2(j_cm2: float) -> float:
    return j_cm2 * CM2_PER_M2 / J_PER_KWH


def irradiation_to_electric_kw_m2(j_cm2: float, hours: float = 4.0, efficiency: float = 0.20) -> float:
    """Cumul de rayonnement sur ``hours`` heures -> puissance électrique moyenne (kW/m²)."""
    return irradiation_j_cm2_to_kwh_m2(j_cm2) / hours * efficiency


def power_from_irradiance(
    irradiance_wm2: pd.Series, area_m2: float, efficiency: float = 0.20, pmax_w_m2: float | None = 250.0
) -> pd.Series:
    """Production (kW) d'un champ de ``area_m2`` m² à partir du rayonnement (W/m²)."""
    w_m2 = irradiance_wm2 * efficiency
    if pmax_w_m2 is not None:
        w_m2 = w_m2.clip(upper=pmax_w_m2)
    return (w_m2 * area_m2 / 1000).rename("pv_kw")


def area_for_peak(peak_kw: float, pmax_w_m2: float = 250.0) -> float:
    """Surface de panneaux (m²) pour une puissance crête donnée : kWc ÷ Pmax (250 W/m² d'après le plan)."""
    return peak_kw / (pmax_w_m2 / 1000)


def power_from_irradiance_kwc(
    irradiance_wm2: pd.Series, peak_kw: float, efficiency: float = 0.20, pmax_w_m2: float = 250.0
) -> pd.Series:
    """Production (kW) d'une installation de ``peak_kw`` kWc d'après le rayonnement (chaîne du plan §4.3).

    Surface = kWc ÷ Pmax ; P = rayonnement × rendement × surface, plafonnée à Pmax par m².
    Rayonnement HORIZONTAL (pas d'inclinaison ni d'orientation des panneaux, pas de pertes de
    température ou d'onduleur) : hypothèse simple. Validée sur le Grand Est 2025 : 1 076 kWh/kWc
    modélisés contre ≈ 1 068 kWh/kWc mesurés par RTE (voir docs/rapport).
    """
    return power_from_irradiance(irradiance_wm2, area_for_peak(peak_kw, pmax_w_m2), efficiency, pmax_w_m2)
