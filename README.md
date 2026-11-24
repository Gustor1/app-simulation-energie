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

Les réponses des API sont mises en cache dans `data/cache/`. Constats sur les sources : `docs/sources_donnees.md`.

## Lancer un scénario

```bash
python -m simu run scenarios/exemple_bloc_spot.yaml   # exemple chiffré de la fiche bloc + spot (270 €)
python -m simu run scenarios/studio.yaml              # studio bottom-up + prix spot réels
```

État actuel (étapes 0 à 2) : consommation seule (bottom-up ou CSV) et coût d'achat sans équipement
(spot pur, prix fixe, bloc + spot). PV et batterie : étapes suivantes.

## Tests

```bash
pytest            # tests hors ligne
pytest -m network # appels réels aux API
```

## Données et licence

Code : licence MIT (provisoire, à valider).
Données Energy-Charts : CC BY 4.0 (Fraunhofer ISE ; prix : Bundesnetzagentur | SMARD.de).
Données RTE éCO2mix : via ODRÉ (Open Data Réseaux Énergies).
