# Tâche 7 – Cahier des charges : simulation usage, solaire, batterie

*Version 3 – 25/11/2026. Mise à jour d'après le simulateur construit et testé (branche `etapes-0-2`).
Résultats détaillés, graphiques et interprétation : `docs/rapport/RAPPORT.md`.*

## 0. Choix retenus (valeurs absentes du plan et du PowerPoint, à valider)
| Sujet | Choix | Raison |
|---|---|---|
| Frigo | 400 W, 7 min, 1 cycle/h -> 1,12 kWh/jour | le plan annonce 1 kWh/jour ; 2 cycles/h donnaient 2,24 kWh/jour |
| Chauffage | k = 0,5 kWh/°C/jour -> 1 450 kWh/an pour le studio | ordre de grandeur d'un petit logement isolé |
| Acheminement + taxes | + 75 €/MWh (particulier), + 50 €/MWh (pro), hors TVA | **estimation** : accise ≈ 31 €/MWh (sources contradictoires) + TURPE ≈ 45 €/MWh (non sourcé) ; à remplacer par une vraie facture |
| Revente du surplus | 11 €/MWh (particulier, EDF OA ≤ 9 kWc 2026) ; spot (pro) | tarifs publics 2026 |
| Pénalité de dépassement | 12,41 € par heure au-dessus de la puissance souscrite | règle CMDPS C4, **vérifiée** dans la grille Enedis TURPE 7 (12,79 €/h depuis le 01/08/2026, 12,41 avant) ; remplace 10 €/kW/mois inventés |

Ces choix ne s'appliquent qu'à la simulation de Strasbourg ; chacun se modifie en une ligne de scénario YAML.

## 1. But
Simuler l'**énergie** et les **coûts** d'une installation client (**conso + PV + batterie**) avec achat/vente au
**prix de marché**, pour répondre à la question : **une batterie (avec ou sans PV) est-elle rentable chez un client ?**

Ce n'est pas un outil de prévision : la météo et les prix du lendemain sont supposés connus.

> **Contexte expérimental :** pas encore de données de l'entreprise. Les clients sont **inventés** (courbes
> bottom-up décrites dans des scénarios YAML). La météo, la production solaire et les prix du marché sont **réels** (2025).

## 2. Entrées

| Entrée | Unité, pas | Source retenue (API publiques, sans clé) |
|---|---|---|
| Courbe de charge du client `load_kw` | kW, 15 min | bottom-up (appareils + aléa), **open data Enedis** (courbe réelle d'un site moyen par secteur, `opendata.enedis.fr`) ou fichier CSV du client |
| Prix spot `spot_eur_mwh` | €/MWh, 15 min (horaire avant oct. 2025) | **Energy-Charts** `price?bzn=FR` |
| Rayonnement solaire `irradiance_wm2` (site) | W/m², 3 h → 15 min | **RTE / ODRÉ** `rayonnement-solaire-vitesse-vent-tri-horaires-regionaux` (par région) |
| Température moyenne du jour (chauffage) | °C, jour | **RTE / ODRÉ** `temperature-quotidienne-regionale` |
| Production PV « profil national » `pv_cf` (variante) | kW/kWc, 15 min | Energy-Charts `public_power` ÷ `installed_power`, ou RTE éCO2mix |
| Paramètres PV | kWc, rendement 20 %, Pmax 250 W/m² | scénario |
| Paramètres batterie | capacité, C-rate 0,5, rendement 90 %, SOC 10–90 %, 5 000 cycles | scénario (tâche 5) |
| Offre d'achat | spot, prix fixe, bloc + spot ; prix de revente ; surcoût par kWh acheté | scénario (tâche 1) |
| Puissance souscrite et pénalité | kW ; €/heure de dépassement (ou €/kW/mois) | scénario (**choix 12,41 €/h à valider**) |
| Prix unitaires PV / batterie | € (bas / médian / haut) | tâche 2 |

## 3. Calculs (au pas de 15 min, Δt = 0,25 h)
- **Énergie :** `E = Σ P × Δt`.
- **Conso bottom-up :** somme d'appareils simulés à la minute puis moyennés au 1/4 h : cycles (frigo),
  plages horaires (TV, éclairage, bureaux), marche quotidienne à heure aléatoire (lave-linge, four),
  jours de la semaine actifs ; **chauffage** `E_jour = k × (20 − T_moy)` si `T_moy < 15 °C`, avec la température réelle.
- **PV d'après le rayonnement** (chaîne du point du 23/11) : surface = kWc ÷ 250 W/m² ;
  `P = rayonnement × 20 % × surface`, plafonné à 250 W/m². Le rayonnement tri-horaire est réparti au 1/4 h
  selon la hauteur du soleil, en conservant l'énergie du jour.
- **Bilan par pas :** `P_réseau = P_load − P_pv + P_charge − P_décharge` (> 0 = achat).
  Priorité : autoconsommer, puis stocker s'il reste de la place, puis revendre.
- **Batterie :** `E(t+1) = E(t) + (η_c·P_charge − P_décharge/η_d)·Δt`, `η_c = η_d = √0,9` ;
  `SOC_min ≤ SOC ≤ SOC_max` ; `P ≤ C-rate × capacité` ; jamais de charge et de décharge simultanées.
- **Pilotage de la batterie** (règles simples) :
  1. *surplus PV* : stocke le surplus, restitue pour couvrir la conso ;
  2. *prix* : chaque jour, charge sur les quarts d'heure les moins chers et décharge sur les plus chers, si l'écart
     couvre les pertes. Le surplus solaire attendu (météo connue) réduit d'autant les achats ; la charge ne dépasse jamais la puissance souscrite ;
  3. *écrêtage (peak shaving)* : décharge au-dessus de la puissance souscrite ;
  4. *prix + écrêtage* : écrêtage prioritaire, arbitrage sans toucher à une réserve (30 % de la capacité utile).
- **Coût :** `Σ P_réseau × Δt × prix`, selon l'offre ; bloc + spot :
  `Σ [bloc × prix_bloc + (P − bloc) × spot] × Δt` ; revente au spot ou à un prix fixe ; surcoût optionnel par kWh acheté.
- **Pénalités :** `€/h × heures passées au-dessus de la puissance souscrite` (règle CMDPS C4) ; variante `€/kW × dépassement maximal du mois`.
- **Surcoût par kWh acheté** (acheminement + taxes) : ajouté au prix de chaque kWh soutiré ; la règle « prix » en tient compte (il est payé aussi sur les pertes de la batterie).
- **Rentabilité :** gain annuel = coût sans équipement − coût avec (énergie + pénalités), attribué au PV puis à la batterie ;
  temps de retour = CAPEX ÷ (gain − OPEX) ; durée de vie de la batterie = min(5 000 cycles ÷ cycles/an, 15 ans) ; PV 25 ans, OPEX 1,5 %/an.

## 4. Hypothèses
- Météo et prix du lendemain connus ; aucune prévision.
- Une seule année (2025) répétée sur la durée de vie : pas d'actualisation, d'inflation ni de dégradation.
- Rayonnement **régional** sur surface **horizontale** (pas d'inclinaison ni d'orientation des panneaux).
- Coût de l'énergie seul par défaut : **acheminement (TURPE) et taxes non inclus** (paramètre prévu).
- Prix unitaires : fourchettes 2025–2026 de la tâche 2, classe de taille la plus proche (10 / 100 / 1000).

## 5. Sorties
- **Les 7 graphiques demandés** : utilisation du solaire, utilisation de la batterie, courbe de charge brute, courbe de
  charge achetée, coût de l'énergie, coût de la batterie, coût des panneaux. Ils sont produits par
  `python -m simu run scenario.yaml --out dossier`.
- **Export CSV** de toutes les grandeurs au 1/4 h.
- **Indicateurs :** conso, production, autoconsommation, autoproduction, cycles, coût par offre avec/sans équipement,
  pénalités, gain annuel, CAPEX, temps de retour (prix bas / médian / haut).

## 6. Architecture
Package Python installable (`pip install -e .`), licence MIT provisoire.
- **Format interne standard** : DataFrame, index UTC au pas de 15 min, colonnes `load_kw`, `pv_cf` ou
  `irradiance_wm2`, `spot_eur_mwh`.
- **Adaptateurs**, un par source : CSV générique + mapping YAML, Energy-Charts, RTE éCO2mix (national ou régional),
  météo ODRÉ. Chacun gère le cache local, les nouvelles tentatives et les limites de débit des API.
- **Modèles** (conso, PV, batterie, marché), **stratégies**, **moteur** pas à pas avec contrôles, **économie**, **graphiques**.
- **Scénario YAML** : période, site, marché (prix + offres), PV, batterie, stratégie, contrat réseau.

## 7. Validation (tests automatiques : 60, tous passants)

| Cas de test | Attendu | Obtenu |
|---|---|---|
| Frigo seul (400 W, 7 min, 2×/h) | ≈ 1 kWh/jour | 2,24 kWh/jour : paramètres incohérents avec la valeur attendue -> **choix 1 cycle/h (1,12 kWh/jour)** |
| Studio | ≈ 10 kWh/jour | 10,34 kWh/jour (sans chauffage) |
| Conversion solaire | 0,14 et 0,24 kW/m² | 0,139 et 0,236 ✅ |
| Exemple bloc + spot (tâche 1) | 270 € | 270 € ✅ (spot pur 276 €, prix fixe 240 €) |
| Batterie : SOC dans les bornes, énergie conservée | oui | oui, écart < 10⁻¹³ kWh sur un an ✅ |
| Batterie « prix » meilleure que « surplus PV » les jours à fort spread | oui | ✅ |
| Écrêtage des pointes | pointe ≤ puissance souscrite | ✅ |
| Pénalité à l'heure | 2 h de dépassement × 12,41 € = 24,82 € | ✅ |
| Surcoût et arbitrage | arbitrage abandonné si 0,9 × haut − bas < 0,1 × surcoût | ✅ |
| **PV par rayonnement vs production réelle** (Grand Est 2025) | proche | 1 076 kWh/kWc modélisés / **1 068 mesurés par RTE** ✅ |

## 8. Principaux résultats (2025, clients fictifs à Strasbourg)
- Spread journalier médian **92 €/MWh** ; 64 % des jours entre 80 et 180 €/MWh ; 509 h à prix négatif.
Avec les choix du § 0 :
- **PV rentable chez les professionnels** : retour au prix d'achat médian de 10 ans (hôpital), 13 ans (usine), 16 ans (PME),
  pour 25 ans de vie. **Pas chez le particulier** (32 ans au mieux).
- **Batterie** : non rentable en arbitrage seul. En cumulant arbitrage + écrêtage, elle n'est rentable qu'au prix d'achat bas :
  - hôpital : 11 / 15 / 19 ans (prix bas / médian / haut) ;
  - usine : 13 / 17 / 21 ans, pour ≈ 15 ans de vie.
  Il faudrait une pénalité d'au moins ≈ 25 €/h pour que celle de l'usine soit rentable au prix médian.
- **Avec les vraies courbes Enedis** (site moyen du secteur, pointes gommées) : PV toujours rentable chez les pros,
  batterie rentable nulle part. Seule la courbe d'un vrai client permet de trancher pour la batterie.

### Zoom : le spread intraday (tâche 3)
**Spread** = prix le plus haut − prix le plus bas d'une même journée. C'est ce que gagne une batterie qui achète au
plus bas et restitue au plus haut (arbitrage). Calculé sur les **vrais prix spot France 2025** (Energy-Charts, 365 jours) :

| Indicateur 2025 | Valeur |
|---|---|
| Prix spot moyen | 61 €/MWh (de −118 à +473 €/MWh) |
| Spread journalier médian / moyen | **92 / 95 €/MWh** |
| Jours avec un spread entre 80 et 180 €/MWh (fourchette du plan) | **64 %** ; 35 % sous 80 ; 1 % au-dessus de 180 |
| Spread médian hiver / été | 79 / 100 €/MWh : le solaire creuse les prix de midi l'été |
| Heures à prix négatif / nul | 509 h / 233 h, sur 97 jours ; 87 % entre 10 h et 17 h ; surtout d'avril à juin |
| Jour record | lundi 20/01/2025 : 359 €/MWh de spread, 473 €/MWh à 18 h (froid, peu de vent, gaz appelé) |

**Ce que ça veut dire pour la batterie.**
- Un kWh restitué perd 10 % à l'aller-retour, et use la batterie d'environ 0,10 €/kWh, soit 100 €/MWh (fiche tâche 5).
- Un spread de 92 €/MWh ne couvre donc pas à lui seul ces pertes et cette usure : **l'arbitrage seul n'est pas rentable**,
  ce que confirme la simulation.
- Les études citées en tâche 3 (Applied Energy 2019 et 2025, CRE 2026, Modo Energy) concluent que la batterie devient
  intéressante **chez les gros clients** qui **cumulent** autoconsommation solaire, arbitrage et écrêtage des pointes.
  C'est ce que montre aussi la simulation : le cumul est le meilleur pilotage, et les pénalités de dépassement décident
  de la rentabilité.

## 9. Livrables
Package Python, 12 scénarios d'exemple (dont 4 avec les vraies courbes Enedis), tests automatiques, README, rapport de tests avec graphiques légendés
(`docs/rapport/RAPPORT.md`), note sur les sources de données (`docs/sources_donnees.md`).

## 10. Questions au tuteur
1. **Pénalités** : la règle C4 à 12,41 €/h convient-elle ? Quelle formule pour les gros clients en HTA (hôpital, usine) ? C'est la donnée qui décide de la rentabilité des batteries.
2. **Acheminement + taxes** : 75 €/MWh (particulier) et 50 €/MWh (pro) sont-ils réalistes pour vos clients ?
3. **Revente du surplus** d'un client pro : spot via agrégateur, comme supposé ?
4. **Frigo** à 1 cycle/h et **k = 0,5** pour le chauffage : d'accord ?
5. **Courbe de charge d'un vrai client** (format Linky ? CSV ?) : les courbes Enedis open data donnent la forme moyenne d'un secteur, mais pas les pointes d'un site.
6. « Open source » : publier le code, ou seulement utiliser des données ouvertes ? (licence)
7. Suite : optimisation du pilotage de la batterie (programmation linéaire), puis prévision ?
