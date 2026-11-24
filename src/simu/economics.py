"""Rentabilité (étape 7) : gain annuel vs CAPEX, temps de retour, scénarios bas / médian / haut.

Prix unitaires : taches/2_prix_unitaires_pv_batteries.md (ordres de grandeur 2025–2026).
Pour une taille intermédiaire, on prend le coût unitaire (€/kWc ou €/kWh) de la classe de
taille la plus proche (échelle logarithmique) : hypothèse simple, à affiner.

Hypothèses (à valider) :
- OPEX PV = 1,5 % du CAPEX par an (fiche : 1–2 % pour 1 MWc, appliqué à toutes les tailles) ;
- OPEX batterie = 0 ;
- durée de vie batterie = min(cycles de vie / cycles par an, ``calendar_life_years``) ;
- durée de vie PV = 25 ans ; pas d'actualisation, pas d'inflation, pas de dégradation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# (taille, coût bas, coût haut) en € pour la taille indiquée
PV_PRICES = [(10, 13_000, 21_000), (100, 60_000, 180_000), (1000, 750_000, 1_200_000)]  # kWc
BATTERY_PRICES = [(10, 6_000, 13_000), (100, 30_000, 55_000), (1000, 250_000, 400_000)]  # kWh

PV_OPEX_RATE = 0.015
PV_LIFE_YEARS = 25


def unit_cost(size: float, table, level: str = "median") -> float:
    """Coût unitaire (€/kWc ou €/kWh) de la classe de taille la plus proche."""
    ref, low, high = min(table, key=lambda row: abs(math.log(size / row[0])))
    total = {"bas": low, "median": (low + high) / 2, "haut": high}[level]
    return total / ref


def capex(pv_kwc: float = 0, battery_kwh: float = 0, level: str = "median") -> dict:
    pv = pv_kwc * unit_cost(pv_kwc, PV_PRICES, level) if pv_kwc else 0.0
    bat = battery_kwh * unit_cost(battery_kwh, BATTERY_PRICES, level) if battery_kwh else 0.0
    return {"pv_eur": pv, "batterie_eur": bat, "total_eur": pv + bat}


@dataclass
class Profitability:
    level: str
    capex_eur: float
    annual_gain_eur: float
    annual_opex_eur: float
    life_years: float

    @property
    def net_annual_eur(self) -> float:
        return self.annual_gain_eur - self.annual_opex_eur

    @property
    def payback_years(self) -> float:
        return self.capex_eur / self.net_annual_eur if self.net_annual_eur > 0 else math.inf

    @property
    def lifetime_balance_eur(self) -> float:
        """Gain net cumulé sur la durée de vie − CAPEX (> 0 : rentable)."""
        return self.net_annual_eur * self.life_years - self.capex_eur


def battery_life_years(cycles_per_year: float, cycle_life: float, calendar_life_years: float = 15) -> float:
    if cycles_per_year <= 0:
        return calendar_life_years
    return min(cycle_life / cycles_per_year, calendar_life_years)


def profitability(
    annual_gain_eur: float,
    pv_kwc: float = 0,
    battery_kwh: float = 0,
    battery_cycles_per_year: float = 0,
    battery_cycle_life: float = 5000,
    calendar_life_years: float = 15,
    level: str = "median",
) -> Profitability:
    c = capex(pv_kwc, battery_kwh, level)
    opex = c["pv_eur"] * PV_OPEX_RATE
    lives = []
    if pv_kwc:
        lives.append(PV_LIFE_YEARS)
    if battery_kwh:
        lives.append(battery_life_years(battery_cycles_per_year, battery_cycle_life, calendar_life_years))
    life = min(lives) if lives else 0
    return Profitability(level, c["total_eur"], annual_gain_eur, opex, life)
