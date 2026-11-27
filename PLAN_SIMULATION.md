# Plan de construction – Simulateur énergie (PV + batterie + marché)

> Projet d'alternance – tuteur : D. Wagner – point du 23/11/2026
> Dernière mise à jour : 24/11/2026
> **Priorité : terminer les tâches demandées (section 3) avant de coder la simulation (section 6).**
> **Contexte expérimental :** pas de données de l'entreprise pour l'instant. Client, site et contexte sont **inventés** (courbe bottom-up + scénario YAML) ; seuls les prix spot et la production PV sont des données réelles (Energy-Charts / RTE). Les données clients réelles viendront plus tard via un adaptateur.

---

## 1. Objectif du projet

Ce n'est **pas** un système de prédiction : c'est un **simulateur technico-économique**.

> *« Simuler énergie et coûts d'une installation client : PV + batterie + achat/vente au prix de marché. »*
> Question à laquelle il répond : **une batterie (avec ou sans PV) est-elle rentable chez un client ?**

- Hypothèse : on connaît la météo (et les prix) du lendemain → pas de modèle de prévision à construire.
- Langage : **Python** (data / IA, cohérent avec l'alternance).
- Esprit : outil **général et open source** ; on y branche les données de n'importe quel client, c'est le **format des données qui s'adapte** (voir section 5).
- Pas de temps : **15 min** (96 points/jour).
- Piste ultérieure (hors périmètre initial) : couche IA de prévision (conso, PV, prix) et pilotage optimisé de la batterie.

---

## 2. Rappel des notions (cours du point + Fiche cours énergie)

- Puissance : `P = f(t)` en W ; **1 W = 1 J/s**.
- Courbe de charge : `P(tᵢ)`, `tᵢ ∈ [0 h ; 23 h45]`, pas Δt = 15 min.
- Énergie sur une journée : `E = Σᵢ P(i) · Δt` [kWh] (si P en kW et Δt en h).
- **1 kWh = 1000 W × 3600 s = 3,6 MJ.**
- Énergie potentielle : `Ep = m·g·h` ; centrale hydraulique : variation d'Ep → travail mécanique → énergie électrique.
  - Exemple : 1000 m³/s tombant de 10 m → **100 MW** (rendement 100 %) ; 15 min → 25 MWh. 10 centrales hydrauliques ≈ 1 centrale nucléaire.
- Ordres de grandeur retenus :

| Élément | Valeur |
|---|---|
| Éolienne | 1 à 10 MW |
| Panneaux parking | 0,25 MW |
| Panneaux toit du COM | 2 MW |
| Habitant (moyenne) | 0,5 kW |
| Studio d'Eliott | ≈ 4300 kWh/an ≈ 10 kWh/jour ≈ 2,5 €/jour |
| Voiture électrique | batterie 77 kWh, moteur 200 kW, 15–20 kWh/100 km, ≈ 10 kW à 50 km/h |
| Être humain (endurance) | 150 W |
| Diesel | 1 L ≈ 10 kWh ; 6 L/100 km ≈ 60 kWh/100 km (rendement ≈ 30 %) |

- Facturation : on facture l'**énergie (kWh)** ; les **gros clients** paient aussi les **dépassements de puissance** (puissance souscrite).
- L'énergie a un **prix** : prix spot (éCO2mix RTE, Energy-Charts).

---

## 3. Tâches demandées par le tuteur (PRIORITAIRE)

| # | Tâche | Échéance | Statut |
|---|---|---|---|
| 1 | Descriptif et analyse des offres « bloc + spot » | 27/11 | 🟡 base dans le docx, à approfondir |
| 2 | Prix unitaires batteries (10 kWh, 100 kWh, 1 MWh) et PV (10 kW, 100 kW, 1 MW) | 27/11 | ✅ fait (`descriptif + prix unitaire.docx`) |
| 3 | Zoom sur le **spread** du prix intraday + article montrant que les gros clients ont intérêt à coupler batterie + PV + autoconsommation | 27/11 | 🟡 brouillon dans `taches/3_…md`, à valider avec de vraies données |
| 4 | Chapitre « Puissance et Énergie » (1 page : énergie, puissance, W, Wh, J) | 27/11 | ✅ fait (`Fiche cours energie.docx`) |
| 5 | Source pour modéliser la **courbe de charge de la batterie** | 04/12 | 🟡 brouillon dans `taches/5_…md` |
| 6 | Sources pour simuler la **courbe de charge client** | 04/12 | 🟡 brouillon dans `taches/6_…md` |
| 7 | Rédiger le **cahier des charges** de la simulation (usage, solaire, batterie) | 04/12 | 🟡 brouillon dans `taches/7_…md`, à valider par le tuteur |

### Ordre conseillé

**Phase 1 – d'ici le 27/11 : le marché**
1. *Bloc + spot* : formaliser `coût = bloc × prix_fixe + (conso − bloc) × spot` (revente de l'excédent au spot) et ajouter **un exemple chiffré sur une journée** (servira de test plus tard).
2. *Spread intraday* : récupérer de vraies données spot (Energy-Charts / RTE), calculer le spread jour par jour, tracer un graphique, confirmer la fourchette 80–180 €/MWh avec des chiffres. Chercher l'article sur l'intérêt du couplage batterie + PV + autoconsommation pour les gros clients.
3. Relire le chapitre Puissance et Énergie (déjà prêt).

**Phase 2 – d'ici le 04/12 : sources de modélisation**
4. *Courbe de charge client* : pistes = profils types Enedis (open data), données Linky, jeux de données open source, **approche bottom-up** (recommandée pour démarrer).
5. *Modèle de batterie* – paramètres à sourcer :
   - capacité (kWh) ; puissance max charge/décharge (C-rate, ex. 0,5 C) ;
   - rendement aller-retour (≈ 90 %) ; SOC min/max ;
   - nombre de cycles de vie (3 000–7 000) pour amortir le coût.
6. *Production PV* — deux approches :
   - **Principale (alignée avec les prix spot)** : facteur de charge PV réel = production solaire France ÷ puissance installée, via **Energy-Charts** (API) ou **RTE éCO2mix** (ODRÉ). Mêmes horodatages que les prix, donc cohérent pour l'arbitrage batterie. Limite : profil national lissé, pas un site précis.
   - **Option, site précis** (orientation, inclinaison) : Open-Meteo, PVGIS ou NASA POWER.

**Phase 3 – 04/12 : cahier des charges**
7. Rédiger à partir des phases 1 et 2 : entrées, sorties, hypothèses, formules, structure du programme, cas de test.

**Phase 4 – après validation du tuteur : coder** (section 6).

---

## 4. Contenu du simulateur (spécifié par le tuteur)

### 4.1 Briques

| Brique | Rôle | Source / modèle |
|---|---|---|
| Courbe de charge client | `P_load(t)` usine / bureaux / hôpital / particulier | open source, ou simulation **bottom-up** |
| Production PV | `P_pv(t)` | rayonnement météo réel × surface × rendement |
| Batterie | `SOC(t)`, `P_bat(t)` | stocke surplus solaire et/ou électricité pas chère ; restitue quand le prix est haut |
| Prix de marché | `spot(t)` €/MWh | RTE éCO2mix, Energy-Charts |
| Bilan économique | coûts, gains, ROI | prix unitaires du docx |

### 4.2 Courbe de charge bottom-up (addition d'usages avec part d'aléa)

| Appareil | Modèle |
|---|---|
| Réfrigérateur | 400 W, 7 min, 2×/heure, 24 h → ≈ 1 kWh/jour |
| TV | 100 W de 18 h à 23 h |
| Lave-vaisselle | 1 kW pendant 2 h |
| Lave-linge | 2 kW pendant 2 h |
| Éclairage | 200 W de 7 h à 9 h et de 17 h à 23 h |
| Chauffage | `P` constante ; `E_chauffage = k × (20 °C − T_moyenne_jour)` si T < 15 °C |
| … | à compléter |

### 4.3 Production solaire

- Pmax du panneau : **250 W/m²** ; rendement ≈ 20 %.
- Chaîne de conversion (données météo réelles) :
  `J/cm² → J/m² → kWh/m² (÷ 3,6·10⁶) → ramené à l'heure (sur 4 h) → kW/m² moyen → × rendement → P élec (kW/m²)`
  - Exemple : 1000 J/cm² = 10⁷ J/m² → 2,78 kWh/m² sur 4 h → 0,69 kW/m² → × 0,2 = **0,14 kW/m²**.
  - Exemple : 1700 J/cm² = 1,7·10⁷ J/m² → 4,72 kWh/m² → 1,18 kW/m² → × 0,2 = **0,24 kW/m²**.
- Règle : ce qui peut être autoconsommé l'est ; le reste est stocké dans la batterie **tant qu'il y a de la place**, puis revendu.

### 4.4 Marché

- **Offre « Bloc + Spot »** : une partie de la conso est achetée à prix fixe à l'avance (bloc, budget sécurisé) ; le reste suit le spot heure par heure. Conso > bloc → achat au spot ; conso < bloc → revente de l'excédent au spot.
- **Spread intraday/journalier** : écart entre heures creuses (nuit ou pic solaire d'après-midi, parfois < 0 €/MWh) et pointes (soir 18 h–21 h, souvent > 150 €/MWh). Spread moyen fréquent : **80 à 180 €/MWh**.
- **Intérêt du couplage PV + batterie + autoconsommation** :
  - stocker le surplus solaire plutôt que de le revendre à bas prix ;
  - charger quand le spot est bas/négatif, décharger quand il explose (arbitrage) ;
  - **peak shaving** : écrêter les pointes pour éviter les pénalités de dépassement de puissance souscrite.
- Réseau : production = consommation à chaque instant (l'électricité ne se stocke pas). Facture pro = énergie (kWh, prix spot) + puissance souscrite (kW).

### 4.5 Prix unitaires (ordres de grandeur 2025–2026, issus du docx)

| Équipement | Taille | Coût estimé | Repères |
|---|---|---|---|
| PV | 10 kWc | 13 000 – 21 000 € | ~1 100 kWh/kWc/an ; rachat surplus faible (≈ 1,1 c€/kWh) |
| PV | 100 kWc | 60 000 – 180 000 € HT | ~500 m² ; moyen 80–100 k€ HT en toiture simple |
| PV | 1 MWc | 750 000 – 1 200 000 € HT | ~0,8–1,0 €/Wc ; OPEX ≈ 1–2 % du CAPEX/an |
| Batterie | 10 kWh | 6 000 – 13 000 € | résidentiel / petit tertiaire ; 3 000–7 000 cycles |
| Batterie | 100 kWh | 30 000 – 55 000 € | tertiaire / PME ; ≈ 300–500 €/kWh installé (LFP) |
| Batterie | 1 MWh | 250 000 – 400 000 € | industriel ; ≈ 250–400 €/kWh ; dégressif |

> À vérifier : l'écart de prix du 10 kWc (1,3–2,1 €/Wc) paraît élevé par rapport au 1 MWc (0,8–1,0 €/Wc). Cohérent avec l'effet d'échelle, mais à sourcer.

### 4.6 Sorties attendues (graphiques)

1. Utilisation du solaire
2. Utilisation de la batterie
3. Courbe de charge **brute** du local
4. Courbe de charge de **ce qu'on achète** (réseau)
5. Coût de l'énergie
6. Coût de la batterie
7. Coût des panneaux

---

## 5. Architecture « générale / open source »

### Principe : format interne standard + adaptateurs

```
 Données client (Linky, CSV usine, Enedis…)  ──► [Adaptateur] ─┐
 Météo (Open-Meteo, PVGIS…)                  ──► [Adaptateur] ─┼─► Format standard ─► Simulateur ─► Résultats
 Prix spot (RTE, Energy-Charts…)             ──► [Adaptateur] ─┘   (DataFrame)         (cœur)      (CSV, graphes)
```

Le cœur ne connaît qu'**un seul format** ; ce sont les adaptateurs qui convertissent les données (renommer, convertir les unités, rééchantillonner à 15 min).

### Format standard

DataFrame pandas indexé par horodatage (pas de 15 min, UTC) :

| Colonne | Unité | Contenu |
|---|---|---|
| `load_kw` | kW | consommation du site |
| `pv_cf` | kW/kWc (0–1) | facteur de charge PV (Energy-Charts / RTE) — **ou** |
| `irradiance_wm2` | W/m² | rayonnement solaire (option site précis ; l'un des deux suffit) |
| `spot_eur_mwh` | €/MWh | prix de marché |

### Configuration d'un scénario (YAML)

```yaml
site:
  load: data/client_hopital.csv
  adapter: linky          # ou csv_generic, enedis_profile, bottom_up
pv:
  peak_kw: 100
  efficiency: 0.20
battery:
  capacity_kwh: 100
  max_power_kw: 50
  round_trip_efficiency: 0.90
market:
  prices: data/spot_2025.csv
  offer: bloc_spot        # bloc_kw: 30, bloc_price: 85
strategy: price_threshold
```

Lancement : `python -m simu run scenario.yaml`.

### Arborescence cible

```
app-simulation-energie/
  pyproject.toml           # package installable (pip install -e .)
  README.md
  LICENSE                  # MIT ou Apache 2.0 (à valider avec le tuteur)
  src/simu/
    adapters/              # 1 fichier par source, même interface : load(path) -> DataFrame standard
                           #   ex. energy_charts.py (prix + PV), rte_eco2mix.py (ODRÉ), csv_generic.py
    models/                # pv.py, battery.py, market.py, load_bottom_up.py
    strategies/            # surplus_pv, price_threshold, (optimisation)
    economics.py           # coûts, gains, ROI
    cli.py
  scenarios/               # exemples YAML
  data/                    # données ouvertes d'exemple
  tests/                   # cas calculés à la main
  docs/                    # cahier des charges, notes
```

---

## 6. Plan de développement (APRÈS les tâches de la section 3)

Bilan à chaque pas (P_grid > 0 = achat) :
`P_grid = P_load − P_pv + P_bat_charge − P_bat_discharge`

| Étape | Contenu | Validation |
|---|---|---|
| 0 | Squelette du package, format standard, adaptateur CSV générique + mapping YAML | lecture d'un CSV quelconque |
| 1 | Conso seule (bottom-up) | ≈ 10 kWh/jour pour un studio ; frigo = 1 kWh/jour |
| 2 | Coût sans équipement : au spot, puis bloc + spot | exemple chiffré de la section 3 |
| 3 | PV seul : autoconsommation + surplus revendu | conversion J/cm² → kW/m² (exemples 4.3) |
| 4 | Batterie « règle simple » (surplus PV, décharge si déficit) | SOC dans les bornes ; énergie conservée |
| 5 | Batterie « prix » (seuil bas/haut, hypothèse prix du lendemain connus) | gain > étape 4 les jours à fort spread |
| 6 | Peak shaving (puissance souscrite, pénalités) | pointes écrêtées |
| 7 | Rentabilité : gain annuel vs CAPEX (scénarios bas / médian / haut), temps de retour | cohérence avec fourchettes de prix |
| 8 | Graphiques (les 7 de la section 4.6) + export CSV | – |
| 9 *(option)* | Optimisation (programmation linéaire / dynamique), puis prévision IA | – |

Premier périmètre : **un seul adaptateur** (CSV générique) + courbe bottom-up ; les adaptateurs Linky / Enedis viennent ensuite.

---

## 7. Sources et ressources

- Prix spot : éCO2mix – RTE ; Energy-Charts (Fraunhofer ISE)
- **API Energy-Charts** (gratuite, sans clé, JSON, CC BY 4.0) : `https://api.energy-charts.info/` — endpoints `price?bzn=FR&start=…&end=…` (prix day-ahead, pas de 15 min, testé ✅), `public_power?country=fr&…` (production par filière dont solaire, **à vérifier**, test non concluant).
- **API RTE éCO2mix** via le portail ODRÉ (sans clé) : `https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/eco2mix-national-tr/records` (testé ✅ ; champs `consommation`, `solaire`, `eolien`, `nucleaire`… en MW, pas de 15 min). Pour l'historique consolidé, chercher le jeu `eco2mix-national-cons-def`. L'API officielle `data.rte-france.com` demande un compte + OAuth : inutile pour démarrer.
- Rayonnement / météo (option site précis) : Open-Meteo, PVGIS, NASA POWER
- Profils de consommation : Enedis open data, données Linky
- Documents du projet : `2026 11 Point Eliott Le.pptx`, `descriptif + prix unitaire.docx`, `Fiche cours energie.docx`, `tache a faire.png`

## 8. Questions ouvertes pour le tuteur

- « Open source » : publier le code, ou seulement utiliser des données ouvertes ? (licence)
- Types de clients prioritaires : particulier, tertiaire, industriel ?
- Niveau d'ambition : règles simples, optimisation, ou prévision IA ?
- Format des données clients réelles attendues (Linky ? CSV maison ?).
