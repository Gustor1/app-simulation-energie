"""Coût de l'énergie achetée au réseau selon l'offre (taches/1_offre_bloc_spot.md).

Toutes les fonctions prennent la puissance soutirée au réseau ``p_grid_kw`` (kW, > 0 = achat,
< 0 = revente) au pas standard. Sans équipement, ``p_grid_kw = load_kw``.

- spot pur    : Coût = Σ P(t) × Δt × spot(t)
- prix fixe   : Coût = Σ P(t) × Δt × prix_fixe
- bloc + spot : Coût = Σ [ bloc(t) × prix_bloc + (P(t) − bloc(t)) × spot(t) ] × Δt
                (le terme spot est négatif quand la conso est sous le bloc : revente au spot)

Prix en €/MWh, énergie en kWh -> division par 1000.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from simu.standard import DT_H


@dataclass
class Cost:
    offer: str
    energy_kwh: float  # énergie nette soutirée au réseau
    total_eur: float
    details: dict = field(default_factory=dict)

    @property
    def eur_per_mwh(self) -> float:
        return self.total_eur / self.energy_kwh * 1000 if self.energy_kwh else float("nan")


def _check(p_grid_kw: pd.Series, spot: pd.Series | None = None) -> None:
    if p_grid_kw.isna().any():
        raise ValueError("puissance réseau manquante (NaN)")
    if spot is not None:
        spot = spot.reindex(p_grid_kw.index)
        if spot.isna().any():
            missing = spot[spot.isna()].index
            raise ValueError(f"prix spot manquant sur {len(missing)} pas (ex. {missing[0]})")


def cost_spot(p_grid_kw: pd.Series, spot_eur_mwh: pd.Series) -> Cost:
    _check(p_grid_kw, spot_eur_mwh)
    eur = p_grid_kw * DT_H * spot_eur_mwh.reindex(p_grid_kw.index) / 1000
    return Cost("spot", float(p_grid_kw.sum() * DT_H), float(eur.sum()))


def cost_fixed(p_grid_kw: pd.Series, price_eur_mwh: float) -> Cost:
    _check(p_grid_kw)
    energy = float(p_grid_kw.sum() * DT_H)
    return Cost("fixed", energy, energy * price_eur_mwh / 1000, {"price_eur_mwh": price_eur_mwh})


def cost_bloc_spot(
    p_grid_kw: pd.Series, spot_eur_mwh: pd.Series, bloc_kw: float | pd.Series, bloc_price_eur_mwh: float
) -> Cost:
    _check(p_grid_kw, spot_eur_mwh)
    spot = spot_eur_mwh.reindex(p_grid_kw.index)
    bloc = bloc_kw.reindex(p_grid_kw.index) if isinstance(bloc_kw, pd.Series) else pd.Series(float(bloc_kw), index=p_grid_kw.index)
    gap_kw = p_grid_kw - bloc
    bloc_eur = float((bloc * DT_H).sum() * bloc_price_eur_mwh / 1000)
    spot_step_eur = gap_kw * DT_H * spot / 1000
    details = {
        "bloc_kwh": float((bloc * DT_H).sum()),
        "bloc_eur": bloc_eur,
        "spot_eur": float(spot_step_eur.sum()),
        "spot_achat_eur": float(spot_step_eur[gap_kw > 0].sum()),
        "spot_revente_eur": float(spot_step_eur[gap_kw < 0].sum()),  # négatif = recette
        "ecart_achete_kwh": float((gap_kw.clip(lower=0) * DT_H).sum()),
        "ecart_revendu_kwh": float((-gap_kw.clip(upper=0) * DT_H).sum()),
    }
    return Cost("bloc_spot", float(p_grid_kw.sum() * DT_H), bloc_eur + details["spot_eur"], details)


def overrun_penalty(
    p_grid_kw: pd.Series, subscribed_kw: float, eur_per_kw: float, tz: str = "Europe/Paris"
) -> dict:
    """Pénalité de dépassement de la puissance souscrite.

    Hypothèse simplifiée (à valider) : chaque mois, pénalité = €/kW × dépassement maximal du mois
    (sur les moyennes 15 min). Les vrais tarifs (TURPE, CMDPS) sont plus détaillés.
    """
    monthly_peak = p_grid_kw.tz_convert(tz).resample("MS").max()
    overrun = (monthly_peak - subscribed_kw).clip(lower=0)
    return {
        "pointe_kw": float(p_grid_kw.max()),
        "depassement_max_kw": float(overrun.max()),
        "mois_en_depassement": int((overrun > 0).sum()),
        "penalite_eur": float(overrun.sum() * eur_per_kw),
        "pas_en_depassement": int((p_grid_kw > subscribed_kw + 1e-9).sum()),
    }


def cost(p_grid_kw: pd.Series, spot_eur_mwh: pd.Series | None, offer: dict) -> Cost:
    """Coût pour une offre décrite comme dans le scénario YAML (``type`` + paramètres).

    ``export_price_eur_mwh`` (optionnel) : l'énergie injectée est payée à ce prix fixe
    (ex. 11 €/MWh, rachat du surplus) au lieu du spot / du prix de l'offre.
    ``import_surcharge_eur_mwh`` (optionnel, défaut 0) : coût ajouté à chaque kWh SOUTIRÉ
    (acheminement, taxes…), que l'autoconsommation évite. Aucune valeur par défaut n'est
    supposée : à renseigner selon le contrat du client.
    """
    surcharge = offer.get("import_surcharge_eur_mwh")
    if surcharge:
        base = cost(p_grid_kw, spot_eur_mwh, {k: v for k, v in offer.items() if k != "import_surcharge_eur_mwh"})
        import_kwh = float(p_grid_kw.clip(lower=0).sum() * DT_H)
        extra = import_kwh * surcharge / 1000
        return Cost(base.offer, base.energy_kwh, base.total_eur + extra, {**base.details, "surcout_import_eur": extra})
    kind = offer.get("type")
    export_price = offer.get("export_price_eur_mwh")
    if export_price is not None:
        if kind == "bloc_spot":
            raise ValueError("export_price_eur_mwh non géré avec bloc_spot (l'excédent est revendu au spot)")
        base = cost(p_grid_kw.clip(lower=0), spot_eur_mwh, {k: v for k, v in offer.items() if k != "export_price_eur_mwh"})
        export_kwh = float((-p_grid_kw.clip(upper=0)).sum() * DT_H)
        revenue = export_kwh * export_price / 1000
        details = {**base.details, "achat_eur": base.total_eur, "revente_kwh": export_kwh, "revente_eur": revenue}
        return Cost(base.offer, float(p_grid_kw.sum() * DT_H), base.total_eur - revenue, details)
    if kind == "spot":
        return cost_spot(p_grid_kw, spot_eur_mwh)
    if kind == "fixed":
        return cost_fixed(p_grid_kw, offer["price_eur_mwh"])
    if kind == "bloc_spot":
        return cost_bloc_spot(p_grid_kw, spot_eur_mwh, offer["bloc_kw"], offer["bloc_price_eur_mwh"])
    raise ValueError(f"offre inconnue {kind!r} ; attendues : spot, fixed, bloc_spot")
