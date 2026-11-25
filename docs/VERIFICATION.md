# Vérification : demandes du point du 23/11/2026 et liste des tâches

*25/11/2026. Chaque ligne du PowerPoint « Point Eliott Le » et de la liste des tâches, avec son état et où la trouver.*

✅ fait · 🟡 fait avec une réserve · ❓ question ouverte pour le tuteur

## PowerPoint

### Slide 2 – Courbe de charge et énergie
| Demande | État | Où |
|---|---|---|
| P = f(t) en W, pas de 15 min de 0 h à 23 h 45 | ✅ | format standard au 1/4 h (`src/simu/standard.py`) ; tâche 4 § 2 |
| Énergie du jour = Σ P(i) × Δt en kWh | ✅ | `standard.energy_kwh`, testé ; tâche 4 § 2 |
| 1 W = 1 J/s ; 1 kWh = 3 600 000 J | ✅ | tâche 4 § 1 |

### Slide 3 – Chapitre puissance et énergie
| Demande | État | Où |
|---|---|---|
| 1 page sur énergie, puissance, W, Wh, J | ✅ | tâche 4 |
| Barrage : 1 000 m³/s, 10 m de chute → 100 MW | ✅ | tâche 4 § 3 |
| Ordres de grandeur : éolienne, PV parking et toit, habitant, studio, voiture, humain, diesel | ✅ | tâche 4 § 6 (chacun vérifié) |
| Illustrer avec des ordres de grandeur nationaux (éCO2mix) | ✅ | tâche 4 § 6 : 444 TWh, 30 à 88 GW, 0,74 kW/habitant en 2025 (vraies données RTE) |

### Slide 4 – Facturation et prix
| Demande | État | Où |
|---|---|---|
| Facturation de l'énergie en kWh | ✅ | `models/market.py` : spot, prix fixe, bloc + spot |
| Gros clients : dépassements de puissance facturés | ✅ | pénalité CMDPS C4 (12,41 €/h, vérifiée dans la grille Enedis) ; 🟡 la formule HTA des très gros clients n'est pas modélisée |
| Prix spot : RTE éCO2mix, Energy-Charts | ✅ | adaptateurs `energy_charts` et `rte_eco2mix` ; vrais prix 2025 au 1/4 h |

### Slide 5 – Simulation
| Demande | État | Où |
|---|---|---|
| Calculer la rentabilité d'une batterie chez un client | ✅ | `economics.py` ; rapport § 7, § Strasbourg, § Hôpital et usine |
| Courbes de charge usine / bureaux / hôpital / particulier | ✅ | 4 scénarios inventés `*_strasbourg.yaml` + 4 avec la vraie courbe Enedis du secteur `*_strasbourg_enedis.yaml` |
| Open source | ✅ | vraies courbes de charge open data Enedis (adaptateur `enedis_open`, rapport § Courbes réelles) ; ❓ publier aussi le code (licence MIT provisoire) ? |
| Bottom-up : somme d'appareils avec heures aléatoires | ✅ | `models/load_bottom_up.py`, testé |
| Réfrigérateur 400 W, 7 min, 2×/h, ≈ 1 kWh/jour | 🟡 | les paramètres donnent 2,24 kWh/jour : choix 1×/h (1,12 kWh/jour) pour Strasbourg |
| TV, lave-vaisselle, lave-linge, éclairage | ✅ | valeurs exactes du point, testées (studio ≈ 10 kWh/jour) |
| Chauffage à puissance constante, E = k × (20 − T moyenne) si T < 15 °C | ✅ | avec la vraie température du Grand Est ; 🟡 k = 0,5 choisi |
| PV : courbe de production d'après le rayonnement solaire | ✅ | rayonnement réel RTE/ODRÉ ; validé : 1 076 kWh/kWc contre 1 068 mesurés par RTE |
| Autoconsommer, puis stocker tant qu'il y a de la place | ✅ | `simulate.py`, bilan vérifié à chaque pas |
| Météo du lendemain connue | ✅ | la règle « prix » tient compte du soleil du jour (`anticipate_pv`) |
| Batterie : stocke le surplus solaire | ✅ | règles « surplus PV » et « prix » |
| Batterie : stocke si le prix est intéressant, restitue si le prix est haut | ✅ | règle « prix » (seuils journaliers) ; en plus : écrêtage des pointes |
| 7 graphiques : solaire, batterie, courbe brute, courbe achetée, coût énergie, coût batterie, coût panneaux | ✅ | `python -m simu run <scénario> --out <dossier>` ; dans le rapport pour studio, PME, hôpital et usine |

### Slide 6 – Pour la simulation
| Demande | État | Où |
|---|---|---|
| Pmax 250 W/m² | ✅ | `models/pv.py` |
| Données météo réelles | ✅ | rayonnement et température RTE/ODRÉ, Grand Est 2025 |
| Conversion J/cm² → kW/m² → kW électrique (1 000 et 1 700 J/cm² sur 4 h, rendement 20 %) | ✅ | testé : 0,139 et 0,236 kW/m², soit les 0,14 et 0,24 du tableau |

### Slide 7 – But du projet
| Demande | État | Où |
|---|---|---|
| Simuler énergie et coûts : client + PV + batterie, achat/vente au prix du marché | ✅ | package `simu`, 12 scénarios, 60 tests |
| Fichiers des tâches 1 à 7 | ✅ | dossier `taches/` (voir ci-dessous) |

## Liste des tâches
| Tâche | État | Où |
|---|---|---|
| 1. Descriptif et analyse des offres « bloc + spot » | ✅ | tâche 1 ; exemple chiffré reproduit par le code (270 €) |
| 2. Prix unitaires batteries 10 kWh / 100 kWh / 1 MWh et PV 10 kW / 100 kW / 1 MW | 🟡 | tâche 2 ; utilisés dans `economics.py`. **La fiche ne cite aucune source** |
| 3. Zoom sur le spread dans le cahier des charges + articles sur l'intérêt du couplage chez les gros clients | ✅ | tâche 3 (articles) ; spread recalculé sur 2025 et zoom ajouté dans la tâche 7 |
| 4. Sources pour modéliser la courbe de charge des batteries | ✅ | tâche 5 ; modèle programmé et testé |
| 5. Sources pour simuler la courbe de charge client | ✅ | tâche 6 ; bottom-up **et** open data Enedis programmés |
| 6. Cahier des charges simulation usage, solaire, batterie | ✅ | tâche 7, version 3 |
| 7. Chapitre puissance et énergie | ✅ | tâche 4 |

## Ce qui reste ouvert (à présenter comme tel)
1. **Valeurs choisies à valider** : frais de réseau et taxes (estimation), k du chauffage, frigo, revente du surplus pro (rapport, « Mes choix »).
2. **Formule de pénalité HTA** pour l'hôpital et l'usine.
3. **Courbe de charge d'un vrai client** : les courbes Enedis sont des moyennes de secteur, sans les pointes d'un site.
4. **Sources de la fiche prix** (tâche 2).
5. **Open source** : publier le code ou non.
6. Suite possible : optimisation du pilotage de la batterie (au lieu de règles simples).
