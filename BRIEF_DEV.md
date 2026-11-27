# BRIEF_DEV – Simulateur énergie (PV + batterie + marché)

> Brief de démarrage pour le développeur (humain ou modèle). À lire en premier.
> Rédigé le 24/11/2026. Le plan et les fiches dans `taches/` font foi pour le détail.

## 1. Mission

Construire un **simulateur technico-économique** en Python (package open source) : pour un client donné, simuler énergie et coûts avec **conso + PV + batterie + achat/vente au prix de marché**, et répondre à la question : **une batterie (avec ou sans PV) est-elle rentable ?**

Ce n'est **pas** un système de prédiction : on suppose connus la météo et les prix du lendemain.

## 2. Contexte : projet EXPÉRIMENTAL

- Pas de données de l'entreprise pour l'instant.
- Le **client, le site et le contexte sont inventés** : courbe de charge **bottom-up** + scénario décrit en YAML.
- **Données réelles** : prix spot et production PV uniquement (Energy-Charts, RTE éCO2mix).
- Les vraies données clients (Linky, CSV maison) viendront plus tard via un **adaptateur** : l'architecture doit le permettre, sans qu'on les implémente maintenant.

## 3. À lire, dans cet ordre

1. `PLAN_SIMULATION.md` : sections 4 (contenu du simulateur), 5 (architecture, format standard, YAML), 6 (étapes de développement 0 à 9).
2. `taches/7_cahier_des_charges.md` : entrées, calculs, hypothèses, sorties, cas de validation, livrables.
3. Fiches de référence :
   - `taches/1_offre_bloc_spot.md` : formule bloc + spot, exemple chiffré (270 €).
   - `taches/5_modele_courbe_charge_batterie.md` : paramètres batterie (capacité, C-rate, rendement, SOC, cycles).
   - `taches/6_sources_courbe_charge_client.md` : modèle bottom-up (appareils, aléa).
   - `taches/2_prix_unitaires_pv_batteries.md` : prix unitaires PV et batterie.
4. Contexte seulement (pas nécessaire pour coder) : `taches/3_…md` (spread), `taches/4_…md` (puissance et énergie).

Les fichiers `.docx`, `.pptx` et `.png` à la racine sont les documents sources du tuteur ; ne pas les modifier.

## 4. Décisions déjà prises

- **Langage / forme** : Python, package installable (`pip install -e .`), arborescence `src/simu/` du plan (section 5).
- **Format interne standard** : DataFrame pandas, index horodaté **pas de 15 min, UTC**, colonnes `load_kw`, `pv_cf` (facteur de charge, kW/kWc) **ou** `irradiance_wm2`, `spot_eur_mwh`.
- **Adaptateurs** : un fichier par source, même interface `load(...) -> DataFrame standard` (`energy_charts.py`, `rte_eco2mix.py`, `csv_generic.py`).
- **PV par défaut** : `P_pv = pv_cf × kWc`. Variante par rayonnement pour un site précis.
- **Bilan par pas** : `P_grid = P_load − P_pv + P_charge − P_decharge` (> 0 = achat). Énergie : `E = Σ P × Δt`, Δt = 0,25 h.
- **Priorité** : autoconsommer, puis charger la batterie avec le surplus, puis revendre.
- **Scénarios** : décrits en YAML (voir plan, section 5).
- **Licence** : MIT ou Apache 2.0, **à valider avec le tuteur** ; mets MIT provisoirement.

## 5. Sources de données

| Donnée | Source | Statut |
|---|---|---|
| Prix spot FR | Energy-Charts : `https://api.energy-charts.info/price?bzn=FR&start=AAAA-MM-JJ&end=AAAA-MM-JJ` | testé, pas de 15 min, CC BY 4.0 |
| Production solaire FR | Energy-Charts : `public_power?country=fr&start=…&end=…` | **non vérifié**, à tester en premier |
| Production solaire + conso FR | RTE éCO2mix via ODRÉ : `https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/eco2mix-national-tr/records` | testé, MW ; historique complet à identifier (`eco2mix-national-cons-def`) |
| Profils de conso | Enedis open data (data.gouv.fr) | plus tard |

Notes :
- Le facteur de charge PV = production solaire France ÷ puissance installée. **Vérifie d'où vient la puissance installée** (Energy-Charts ou RTE) et documente-la.
- L'API Energy-Charts s'est montrée instable pendant les tests (timeouts) : prévoir **timeouts, retries et un cache local** (fichiers dans `data/`), pour ne pas dépendre du réseau à chaque exécution.
- L'API officielle RTE (`data.rte-france.com`, OAuth) est inutile pour démarrer.

## 6. Périmètre de départ

Commence par les **étapes 0 à 2** de la section 6 du plan :

| Étape | Contenu | Validation (tests) |
|---|---|---|
| 0 | Squelette du package, format standard, adaptateur CSV générique + mapping YAML, adaptateurs Energy-Charts / RTE | lecture d'un CSV quelconque ; prix et PV réels récupérés et mis en cache |
| 1 | Conso seule, bottom-up | frigo ≈ 1 kWh/jour ; studio ≈ 10 kWh/jour |
| 2 | Coût sans équipement : au spot, puis bloc + spot | exemple chiffré de `taches/1_…md` = **270 €** |

**S'arrêter après l'étape 2** et rendre compte. Les étapes suivantes (PV, batterie « règle simple », batterie « prix », peak shaving, rentabilité, graphiques) viennent après accord.

## 7. Règles de travail

- Avance **étape par étape**, un commit par étape, tests inclus (cas calculés à la main, dans `tests/`).
- **Demande avant de changer l'architecture** ou le format standard.
- Ne dis pas qu'une étape est validée si un test échoue ou n'a pas été lancé : indique-le.
- Si une information manque ou semble incohérente dans les fiches (ex. écart de prix du 10 kWc signalé dans le plan), **signale-le** au lieu de l'inventer.
- Ne modifie pas `PLAN_SIMULATION.md` ni `taches/` sans le dire : ce sont les documents de référence tenus à jour par l'organisateur du projet.
- Hypothèses v1 : pas de prévision, pas d'optimisation (programmation linéaire / IA = option, étape 9).

## 8. Questions encore ouvertes (ne bloquent pas la v1)

- Licence (publier le code, ou seulement utiliser des données ouvertes ?).
- Types de clients prioritaires : particulier, tertiaire, industriel.
- Niveau d'ambition final : règles simples, optimisation, ou prévision IA.
- Format des données clients réelles.
