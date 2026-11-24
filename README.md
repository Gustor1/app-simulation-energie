# simu-energie

Simulateur technico-économique : consommation + PV + batterie + achat/vente au prix de marché.
Question : **une batterie (avec ou sans PV) est-elle rentable chez un client ?**

Projet expérimental : client et site inventés (courbe de charge bottom-up, scénario YAML) ;
prix spot et production PV réels (Energy-Charts, RTE éCO2mix).

## Installation

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows ; source .venv/bin/activate sous Linux/macOS
pip install -e ".[dev]"
```

## Format standard

DataFrame pandas, index UTC au pas de 15 min, colonnes `load_kw` (kW), `pv_cf` (kW/kWc),
`irradiance_wm2` (W/m²), `spot_eur_mwh` (€/MWh). Voir `src/simu/standard.py`.

## Adaptateurs (`src/simu/adapters/`)

| Module | Données | Fonction |
|---|---|---|
| `csv_generic` | n'importe quel CSV + mapping YAML | `load(path, mapping)` |
| `energy_charts` | prix spot, facteur de charge PV France | `load_spot`, `load_pv_cf`, `load` |
| `rte_eco2mix` | facteur de charge PV France (ODRÉ) | `load_pv_cf` |

## Modules

| Module | Rôle |
|---|---|
| `models/load_bottom_up.py` | courbe de charge par appareils (cycles, horaires, marches quotidiennes, chauffage) |
| `models/pv.py` | PV par facteur de charge ou par rayonnement |
| `models/battery.py` | batterie (SOC, rendement, C-rate, bornes, coût d'usure) |
| `strategies/rules.py` | pilotage : `surplus_pv`, `price_threshold`, `peak_shaving` |
| `simulate.py` | bilan pas à pas `P_grid = P_load − P_pv + P_charge − P_décharge`, vérifications |
| `models/market.py` | coûts (spot, fixe, bloc + spot, revente, surcoût par kWh acheté, pénalités) |
| `economics.py` | CAPEX, OPEX, durée de vie, temps de retour |
| `plots.py` | graphiques |
| `scenario.py`, `cli.py` | scénario YAML et ligne de commande |

Les réponses des API sont mises en cache dans `data/cache/`. Constats sur les sources : `docs/sources_donnees.md`.

## Lancer un scénario

```bash
python -m simu run scenarios/exemple_bloc_spot.yaml   # exemple chiffré de la fiche bloc + spot (270 €)
python -m simu run scenarios/studio.yaml              # studio bottom-up + prix spot réels
```

```bash
python -m simu run scenarios/pme_bureaux.yaml --out results/pme --week 2025-06-16
# -> bilan, coûts, pénalités, rentabilité + results/pme/resultats.csv + 7 graphiques PNG
```

État actuel (étapes 0 à 8) : conso (bottom-up ou CSV), PV (facteur de charge national), batterie
(règles « surplus PV », « prix », « peak shaving »), coûts (spot, fixe, bloc + spot, pénalités de
dépassement), rentabilité (scénarios de prix bas / médian / haut), graphiques et export CSV.

**Rapport de tests avec graphiques et interprétation : [docs/rapport/RAPPORT.md](docs/rapport/RAPPORT.md)**
(régénérer : `python scripts/rapport.py`).

## Tests

```bash
pytest            # tests hors ligne
pytest -m network # appels réels aux API
```

## Données et licence

Code : licence MIT (provisoire, à valider).
Données Energy-Charts : CC BY 4.0 (Fraunhofer ISE ; prix : Bundesnetzagentur | SMARD.de).
Données RTE éCO2mix : via ODRÉ (Open Data Réseaux Énergies).
