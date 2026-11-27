"""Stratégies de pilotage (règles simples, pas d'optimisation).

Une stratégie est une fonction ``(contexte) -> consigne batterie en kW`` (> 0 charge,
< 0 décharge). Le modèle de batterie borne ensuite la consigne (P_max, SOC).

Contexte : ``net_kw`` = conso − PV (> 0 : déficit, < 0 : surplus), ``spot``, ``energy_kwh``,
``battery``, et les paramètres préparés par ``prepare`` (seuils de prix du jour…).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from simu.standard import DT_H


class SurplusPV:
    """Étape 4 : charge avec le surplus PV, décharge pour couvrir le déficit. Jamais de charge réseau."""

    name = "surplus_pv"

    def prepare(self, inputs: pd.DataFrame, battery) -> None:
        pass

    def __call__(self, i: int, net_kw: float, spot: float, energy_kwh: float, battery) -> float:
        return -net_kw


class PriceThreshold:
    """Étape 5 : prix du lendemain connus -> seuils bas / haut par jour.

    Chaque jour (heure locale), seuil haut = prix à partir duquel les quarts d'heure les plus chers
    suffisent à vider la batterie (en tenant compte de la conso à couvrir : la décharge ne dépasse
    pas le déficit, sauf ``allow_export``) ; seuil bas = prix en dessous duquel les quarts d'heure
    les moins chers suffisent à la remplir (en tenant compte de P_max et de ``grid_limit_kw``).
    - surplus PV : toujours stocké ;
    - spot ≤ seuil bas  : charge depuis le réseau à P_max ;
    - spot ≥ seuil haut : décharge pour couvrir la conso (et revend si ``allow_export``) ;
    - sinon : on garde l'énergie pour les heures chères.
    L'arbitrage réseau n'est fait que si le spread du jour couvre les pertes et l'usure :
    haut × η_aller-retour − bas > ``min_margin_eur_mwh``.
    ``grid_limit_kw`` : la charge depuis le réseau ne fait jamais dépasser cette puissance
    soutirée (ex. la puissance souscrite).
    ``anticipate_pv`` (défaut : oui) : la météo du lendemain étant connue, la quantité achetée au
    réseau pour remplir la batterie est diminuée du surplus solaire attendu dans la journée.
    ``peak_limit_kw`` (optionnel) : cumul avec l'écrêtage des pointes ; au-dessus de cette puissance,
    la batterie décharge en priorité. ``peak_reserve_kwh`` : énergie que l'arbitrage laisse en
    réserve pour ces pointes. ``surcharge_eur_mwh`` : surcoût par kWh acheté (acheminement, taxes),
    payé aussi sur les pertes de la batterie : il rend l'arbitrage un peu plus exigeant.
    """

    name = "price_threshold"

    def __init__(self, allow_export: bool = False, min_margin_eur_mwh: float = 0.0, tz: str = "Europe/Paris",
                 grid_limit_kw: float | None = None, anticipate_pv: bool = True,
                 peak_limit_kw: float | None = None, peak_reserve_kwh: float = 0.0, surcharge_eur_mwh: float = 0.0):
        self.surcharge_eur_mwh = surcharge_eur_mwh
        self.grid_limit_kw = grid_limit_kw
        self.peak_limit_kw = peak_limit_kw
        self.peak_reserve_kwh = peak_reserve_kwh
        self.anticipate_pv = anticipate_pv
        self.allow_export = allow_export
        self.min_margin_eur_mwh = min_margin_eur_mwh
        self.tz = tz

    @staticmethod
    def _threshold(price: np.ndarray, capacity_kw: np.ndarray, energy_needed_kwh: float, cheapest: bool) -> float:
        """Prix du dernier quart d'heure retenu quand on parcourt les prix du plus favorable au moins
        favorable en cumulant ``capacity_kw × Δt`` jusqu'à ``energy_needed_kwh``."""
        usable = capacity_kw > 1e-9
        if not usable.any():  # aucun pas utilisable : seuil jamais atteint
            return -np.inf if cheapest else np.inf
        p, c = price[usable], capacity_kw[usable]
        order = np.argsort(p if cheapest else -p, kind="stable")
        reached = np.cumsum(c[order] * DT_H) >= energy_needed_kwh - 1e-9
        k = int(np.argmax(reached)) if reached.any() else len(order) - 1
        return float(p[order][k])

    def prepare(self, inputs: pd.DataFrame, battery) -> None:
        # Récupère les prix et calcule la puissance nette à fournir par le réseau (charge moins PV).
        spot = inputs["spot_eur_mwh"]
        net = (inputs["load_kw"] - inputs["pv_kw"]).to_numpy()
        # La puissance nominale maximale de charge/décharge est fixée par la batterie.
        p_max = battery.p_max_kw
        # Capacité de décharge par pas : déficit du site, sauf si l'export batterie est autorisé.
        dis_cap = np.full(len(net), p_max) if self.allow_export else np.clip(net, 0, p_max)
        # Capacité de charge réseau : puissance batterie, réduite si la limite réseau serait dépassée.
        if self.grid_limit_kw is not None:
            ch_cap = np.clip(self.grid_limit_kw - net, 0, p_max)
        else:
            ch_cap = np.full(len(net), p_max)
        # Lorsqu'il y a déjà du surplus PV, ce pas ne compte pas comme occasion de charge réseau.
        ch_cap[net < 0] = 0  # les heures de surplus PV ne servent pas à charger depuis le réseau
        # Calcule le surplus PV utilisable par la batterie à chaque pas.
        surplus = np.clip(-net, 0, p_max)  # surplus PV stockable à chaque pas (kW)
        # Regroupe les pas par journée locale : les seuils bas/haut sont recalculés chaque jour.
        day = spot.index.tz_convert(self.tz).normalize()
        # Initialise les seuils : aucun prix ne déclenchera une action tant que le seuil n'est pas calculé.
        low = np.full(len(net), -np.inf)
        high = np.full(len(net), np.inf)
        # Convertit les séries en tableaux pour le calcul des seuils.
        price = spot.to_numpy()
        for d in day.unique():
            # Sélectionne tous les quarts d'heure appartenant à la journée locale courante.
            m = np.asarray(day == d)
            # météo du lendemain connue : on n'achète au réseau que ce que le surplus solaire du jour ne remplira pas
            pv_fill_kwh = float(surplus[m].sum() * DT_H * battery.eta) if self.anticipate_pv else 0.0
            # Énergie à acheter pour remplir la batterie après apport solaire prévu et pertes de charge.
            grid_kwh = max(0.0, battery.usable_kwh - pv_fill_kwh) / battery.eta
            if grid_kwh > 1e-6:
                # Seuil bas : prix jusqu'auquel les pas les moins chers permettent de charger l'énergie visée.
                low[m] = self._threshold(price[m], ch_cap[m], grid_kwh, cheapest=True)
            # Seuil haut : prix des pas les plus chers nécessaires pour restituer l'énergie utilisable.
            high[m] = self._threshold(price[m], dis_cap[m], battery.usable_kwh * battery.eta, cheapest=False)
        # surcoût s par kWh acheté : on paie (bas + s) par kWh chargé, on évite (haut + s) par kWh restitué
        eta_rt = battery.round_trip_efficiency
        # Marque les journées où l'écart de prix compense le rendement, le surcoût et la marge minimale.
        worth = high * eta_rt - low - (1 - eta_rt) * self.surcharge_eur_mwh > self.min_margin_eur_mwh
        # Mémorise les seuils et ce verdict pour que __call__ prenne une décision à chaque pas.
        self.low, self.high, self.worth = low, high, worth

    def __call__(self, i: int, net_kw: float, spot: float, energy_kwh: float, battery) -> float:
        # Une consigne négative décharge : le surplus PV est donc absorbé en premier.
        if net_kw < 0:
            return -net_kw  # surplus PV
        # Si la puissance nette dépasse le seuil, décharge d'abord pour écrêter la pointe.
        if self.peak_limit_kw is not None and net_kw > self.peak_limit_kw:
            return -(net_kw - self.peak_limit_kw)  # écrêtage prioritaire, réserve comprise
        # Si le prix est bas et l'arbitrage rentable, demande une charge depuis le réseau.
        if self.worth[i] and spot <= self.low[i]:
            if self.grid_limit_kw is not None:
                # Limite la charge pour que la puissance soutirée reste sous la limite réseau.
                return max(0.0, min(battery.p_max_kw, self.grid_limit_kw - net_kw))
            # Sans limite réseau configurée, demande la puissance maximale de la batterie.
            return battery.p_max_kw
        # Si le prix est haut, décharge pour couvrir le site sans exporter par défaut.
        if spot >= self.high[i]:
            want = battery.p_max_kw if self.allow_export else net_kw
            # Convertit l'énergie au-dessus du SOC mini et de la réserve en puissance faisable ce quart d'heure.
            available_kw = max(0.0, energy_kwh - battery.e_min - self.peak_reserve_kwh) * battery.eta / DT_H
            # N'épuise pas la réserve prévue pour les pointes; le signe négatif signifie décharger.
            return -min(want, available_kw)  # l'arbitrage ne touche pas à la réserve d'écrêtage
        # Entre les seuils, ne charge ni ne décharge : la fonction renvoie une consigne nulle.
        return 0.0


class PeakShaving:
    """Étape 6 : écrête la puissance soutirée au-dessus de ``limit_kw`` (puissance souscrite).

    - déficit > limite : décharge de l'excédent ;
    - surplus PV : stocké ;
    - sinon, si la batterie n'est pas pleine : recharge depuis le réseau sans dépasser
      ``limit_kw − margin_kw`` (et seulement quand spot ≤ ``max_charge_spot`` si renseigné).
    """

    name = "peak_shaving"

    def __init__(self, limit_kw: float, margin_kw: float = 0.0, max_charge_spot: float | None = None):
        self.limit_kw = limit_kw
        self.margin_kw = margin_kw
        self.max_charge_spot = max_charge_spot

    def prepare(self, inputs: pd.DataFrame, battery) -> None:
        pass

    def __call__(self, i: int, net_kw: float, spot: float, energy_kwh: float, battery) -> float:
        if net_kw > self.limit_kw:
            return -(net_kw - self.limit_kw)
        if net_kw < 0:
            return -net_kw
        if self.max_charge_spot is not None and not (spot <= self.max_charge_spot):
            return 0.0
        return max(0.0, self.limit_kw - self.margin_kw - net_kw)


def from_config(spec) -> object:
    if spec is None:
        return None
    if isinstance(spec, str):
        spec = {"type": spec}
    spec = dict(spec)
    kind = spec.pop("type")
    classes = {"surplus_pv": SurplusPV, "price_threshold": PriceThreshold, "peak_shaving": PeakShaving}
    if kind not in classes:
        raise ValueError(f"stratégie inconnue {kind!r} ; disponibles : {list(classes)}")
    return classes[kind](**spec)


__all__ = ["SurplusPV", "PriceThreshold", "PeakShaving", "from_config", "np"]
