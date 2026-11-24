"""Batterie – modèle simple de taches/5_modele_courbe_charge_batterie.md.

À chaque pas Δt :  E(t+1) = E(t) + (η_c · P_charge − P_décharge / η_d) · Δt
Contraintes : SOC_min ≤ SOC ≤ SOC_max ; 0 ≤ P ≤ P_max = C-rate × capacité ;
pas de charge et de décharge simultanées.
Les puissances P_charge / P_décharge sont côté réseau (AC).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from simu.standard import DT_H


@dataclass
class Battery:
    capacity_kwh: float
    c_rate: float = 0.5
    round_trip_efficiency: float = 0.90
    soc_min: float = 0.10
    soc_max: float = 0.90
    soc_init: float | None = None  # défaut : SOC_min (batterie vide au départ)
    cycle_life: float = 5000
    max_power_kw: float | None = None  # si renseigné, remplace C-rate × capacité

    def __post_init__(self):
        if not 0 <= self.soc_min < self.soc_max <= 1:
            raise ValueError("il faut 0 ≤ soc_min < soc_max ≤ 1")
        if not 0 < self.round_trip_efficiency <= 1:
            raise ValueError("rendement aller-retour dans ]0 ; 1]")

    @property
    def p_max_kw(self) -> float:
        return self.max_power_kw if self.max_power_kw is not None else self.c_rate * self.capacity_kwh

    @property
    def eta(self) -> float:
        """Rendement de charge = rendement de décharge = √(rendement aller-retour)."""
        return math.sqrt(self.round_trip_efficiency)

    @property
    def e_min(self) -> float:
        return self.soc_min * self.capacity_kwh

    @property
    def e_max(self) -> float:
        return self.soc_max * self.capacity_kwh

    @property
    def usable_kwh(self) -> float:
        return self.e_max - self.e_min

    def e_init(self) -> float:
        return (self.soc_init if self.soc_init is not None else self.soc_min) * self.capacity_kwh

    def step(self, energy_kwh: float, request_kw: float) -> tuple[float, float, float]:
        """Applique une consigne (> 0 charge, < 0 décharge), bornée par P_max et le SOC.

        Renvoie (P_charge, P_décharge, nouvelle énergie stockée).
        """
        if request_kw > 0:
            p = min(request_kw, self.p_max_kw, max(0.0, self.e_max - energy_kwh) / (self.eta * DT_H))
            return p, 0.0, energy_kwh + self.eta * p * DT_H
        if request_kw < 0:
            p = min(-request_kw, self.p_max_kw, max(0.0, energy_kwh - self.e_min) * self.eta / DT_H)
            return 0.0, p, energy_kwh - p / self.eta * DT_H
        return 0.0, 0.0, energy_kwh

    def wear_cost_eur_kwh(self, capex_eur: float) -> float:
        """Coût d'usure par kWh déchargé = CAPEX / (cycles × capacité × profondeur de décharge)."""
        return capex_eur / (self.cycle_life * self.capacity_kwh * (self.soc_max - self.soc_min))
