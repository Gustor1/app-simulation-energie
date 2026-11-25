# Rapport de tests – Simulateur énergie (étapes 0 à 8, simulation Strasbourg : particulier, bureaux, hôpital, usine)

*25/11/2026 – branche `etapes-0-2`. Données réelles 2025 : prix spot (Energy-Charts), production PV et météo
(RTE éCO2mix, RTE/ODRÉ). Clients **fictifs** (bottom-up) : studio, PME de bureaux, hôpital, usine.*

Régénérer les graphiques et les chiffres : `python scripts/rapport.py` (≈ 25 s, données en cache).
Chiffres bruts : [chiffres.json](chiffres.json).

---

## Mes choix (valeurs qui manquaient)

Plusieurs valeurs n'étaient données ni par le plan ni par le PowerPoint. Plutôt que de laisser la simulation
incomplète, **j'en ai choisi une pour chacune**, d'après une source publique quand il y en a une.
- **Où ils s'appliquent :** dans la **simulation de Strasbourg** (studio, PME, hôpital, usine). Les étapes 1 à 8
  gardent les paramètres du plan, car elles servent à vérifier les formules.
- **Comment les changer :** chaque valeur tient en une ligne du fichier de scénario (`scenarios/*_strasbourg.yaml`).

| Sujet | Mon choix | Pourquoi, en simple |
|---|---|---|
| **Frigo** | 400 W, 7 min, **1 fois par heure** → 1,12 kWh/jour | Le plan annonce « ≈ 1 kWh/jour », mais ses paramètres (2 fois par heure) donnent 2,24 kWh/jour, le double d'un frigo courant. J'ai gardé le résultat annoncé, plus réaliste, et ajusté le nombre de cycles. |
| **Chauffage du studio** | k = 0,5 kWh par °C et par jour → 1 450 kWh/an | Le PowerPoint donne la formule mais pas k. Avec 0,5, le chauffage fait environ 30 % de la consommation du studio, un ordre de grandeur plausible pour un petit logement bien isolé. |
| **Acheminement et taxes, particulier** | **+ 75 €/MWh** sur chaque kWh acheté (hors TVA) | Une facture ne contient pas que l'énergie : on paie aussi le transport sur le réseau (TURPE, ≈ 45 €/MWh) et une taxe, l'accise (≈ 31 €/MWh en 2026). Chaque kWh produit soi-même évite ces frais. Les ignorer sous-estimait le gain des panneaux et de la batterie. |
| **Acheminement et taxes, professionnel** | **+ 50 €/MWh** | Mêmes postes, mais moins chers par kWh pour un professionnel. C'est un ordre de grandeur. |
| **Revente du surplus** | particulier : **11 €/MWh** (1,1 c€/kWh) ; professionnel : **prix spot** | Particulier (≤ 9 kWc) : tarif d'obligation d'achat EDF OA depuis juin 2026. Professionnel : surplus vendu au marché par un intermédiaire (agrégateur). |
| **Pénalité de dépassement** | **12,41 € par heure** passée au-dessus de la puissance souscrite | C'est la règle réelle (CMDPS) des clients « C4 » (36 à 250 kVA) : on paie selon la **durée** du dépassement. Elle remplace mes 10 €/kW/mois, qui étaient inventés. L'hôpital et l'usine dépassent 250 kVA et relèvent en réalité d'une autre formule ; j'applique la même par simplicité. |
| **Courbes de consommation** | deux versions : inventée appareil par appareil (bottom-up), et **réelle** (open data Enedis) | Le PowerPoint demande les deux (« Opensource » et « bottom-up »). Les courbes réelles Enedis sont celles d'un **site moyen** de chaque secteur : la forme est réelle, mais les pointes d'un vrai site sont gommées (§ Courbes réelles). |

**Fiabilité de ces valeurs :**
- **Pénalité : vérifiée** dans la [grille officielle Enedis TURPE 7](https://www.enedis.fr/sites/default/files/documents/pdf/brochure-tarifaire-turpe-7.pdf).
  Elle donne « CMDPS = 12,79 × h » (h = heures de dépassement) au 01/08/2026. Les 12,41 €/h sont la valeur de l'année
  précédente (12,79 ÷ 1,0304, hausse d'août 2026), qui correspond à 2025, l'année simulée. Pour la HTA, la grille donne une autre
  formule, 0,04 × b × √(Σ dépassements² par pas de 10 min), **non modélisée**.
- **Revente à 1,1 c€/kWh : plusieurs sites concordent**, mais je n'ai pas lu l'arrêté lui-même.
- **Accise ≈ 31 €/MWh : sources contradictoires** (30,85 selon EDF, 25,19 hors majoration selon le BOFiP).
- **Acheminement ≈ 45 €/MWh (particulier) et 50 €/MWh au total (pro) : estimations de ma part, sans source.**
  Les coefficients officiels sont dans des tableaux-images de la grille Enedis que je n'ai pas pu lire. À remplacer par la valeur d'une vraie facture.

Autres sources consultées : [Selectra, dépassement de puissance](https://entreprises.selectra.info/energie/electricite/compteurs/puissance/depassement),
[EDF, taxes sur l'électricité](https://www.edf.fr/entreprises/faq-entreprises/facture/les-taxes-evolutions-tarifaires-en-electricite/quelles-sont-les-taxes-applicables-sur-l-electricite),
[tarif de rachat EDF OA 2026](https://www.les-energies-renouvelables.eu/conseils/photovoltaique/tarif-rachat-electricite-photovoltaique/).

**Ce que ces choix changent :**
- **Les panneaux deviennent rentables chez les professionnels**, car ils évitent aussi l'acheminement et les taxes :
  - hôpital : 5 à 17 ans de retour ;
  - usine : 9 à 16 ans ;
  - PME : 7 à 27 ans, pour 25 ans de durée de vie.
- **La batterie de l'usine devient moins rentable** : 13 à 21 ans de retour au lieu de 9 à 15, pour 15 ans de durée de vie. La vraie règle de
  pénalité coûte moins cher que ma règle inventée pour ses pointes courtes.
- La batterie de l'hôpital est rentable au prix d'achat bas et tout juste au prix médian.
- **Rien n'est rentable chez le particulier**, même avec acheminement et taxes.

---

## En bref

| Question | Réponse sur 2025 (clients fictifs) |
|---|---|
| Les tests passent-ils ? | **60 / 60** (dont 4 qui interrogent les vraies API) |
| Le spread 80–180 €/MWh du plan est-il confirmé ? | **Oui en grande partie** : médiane 92 €/MWh, 64 % des jours entre 80 et 180 ; mais 35 % des jours sont **sous** 80 |
| Une batterie est-elle rentable **sur l'énergie seule (spot)** ? | **Non** dans nos cas : temps de retour 16 à 30 ans pour une durée de vie d'environ 15 ans |
| Qu'est-ce qui peut la rendre rentable ? | **Les pénalités de dépassement** (peak shaving) et **les coûts évités sur chaque kWh acheté** (acheminement + taxes, comptés dans la simulation de Strasbourg). Ce sont eux qui décident, pas le spread |
| La simulation du PowerPoint (Strasbourg, météo réelle) ? | **Faite** : PV d'après le rayonnement réel du Grand Est (1 076 kWh/kWc modélisés contre 1 068 mesurés par RTE), chauffage d'après la température réelle. Mêmes conclusions de rentabilité (voir § Strasbourg) |
| Et chez un client à fortes pointes (usine, hôpital) ? | **Seulement au prix d'achat bas** avec mes choix (pénalité réelle C4 de 12,41 €/h, + 50 €/MWh d'acheminement et taxes). La batterie de l'hôpital met 11 / 15 / 19 ans à se rembourser, celle de l'usine 13 / 17 / 21 ans, pour ≈ 15 ans de vie. **Le résultat dépend fortement du montant de la pénalité** (§ Hôpital et usine) |
| Le PV est-il rentable ? | **Oui chez les professionnels** dès qu'on compte acheminement et taxes. À Strasbourg, au prix d'achat médian : hôpital 10 ans, usine 13 ans, PME 16 ans, pour 25 ans de vie. **Non pour le studio** (32 ans au mieux) |

⚠️ **Lecture importante :**
- **Étapes 1 à 8 :** le coût d'achat simulé est **uniquement le prix de l'énergie** (spot, fixe ou bloc + spot),
  comme dans la fiche bloc + spot.
- **Ce qui manque :** une vraie facture contient aussi l'**acheminement (TURPE)** et des **taxes**, payés sur
  chaque kWh soutiré et donc évités par l'autoconsommation. Sans eux, les gains sont **sous-estimés**.
- **Simulation de Strasbourg :** ils sont comptés, avec les valeurs de « Mes choix » (paramètre
  `import_surcharge_eur_mwh`). La sensibilité à ce montant est au § 7.

---

## Petit lexique (pour lire les graphiques)

| Terme | Signification |
|---|---|
| **kW / kWh** | puissance (à un instant) / énergie (puissance × durée). 1 kW pendant 1 h = 1 kWh |
| **€/MWh** | prix de l'électricité ; 100 €/MWh = 0,10 €/kWh |
| **Spot** | prix du marché de gros, différent pour chaque quart d'heure, connu la veille |
| **Spread** | écart entre le prix le plus haut et le plus bas d'une journée |
| **kWc** | « kilowatt-crête » : puissance maximale d'une installation de panneaux |
| **SOC** | niveau de charge de la batterie, en % (gardé ici entre 10 et 90 %) |
| **Autoconsommation** | part de la production solaire consommée sur place |
| **Autoproduction** | part de la consommation couverte par le solaire |
| **Puissance souscrite** | puissance maximale prévue au contrat ; la dépasser coûte une pénalité |
| **Peak shaving** | utiliser la batterie pour « raboter » les pics de consommation |
| **Bloc + spot** | contrat où une partie de l'énergie est achetée d'avance à prix fixe, le reste au prix du marché |

---

## Étape 0 – Données et format standard

### Tests

| Test | Ce qu'il vérifie | Résultat |
|---|---|---|
| `test_csv_quelconque_avec_mapping_yaml` | CSV « à la française » (`;`, virgule décimale, heure de Paris, W) → format standard | ✅ |
| `test_horodatage_en_fin_de_pas_et_plusieurs_colonnes` | horodatage en fin de pas (type Linky), 2 colonnes | ✅ |
| `test_mapping_invalide` | messages d'erreur clairs si le mapping est faux | ✅ |
| `test_horaire_vers_15min_…`, `test_5min_…`, `test_pas_mixte_…`, `test_trou_reste_vide` | conversion de pas, énergie conservée, trous non bouchés en silence | ✅ |
| `test_energy_charts_prix_horaire_puis_15min` | prix réels du 30/09/2025 (horaire) et du 01/10/2025 (15 min) | ✅ |
| `test_energy_charts_facteur_de_charge_pv`, `test_rte_…` | facteur de charge PV = production ÷ puissance installée | ✅ |
| `test_cache_http`, `test_retries_puis_erreur`, `test_limite_de_debit_429_puis_succes` | cache, nouvelles tentatives, respect de la limite de débit | ✅ |
| `test_reseau_energy_charts_prix_et_pv`, `test_reseau_rte_pv` | appel réel aux API | ✅ |

![CSV générique](fig/e0_csv_generique.png)

> 📊 **Comment lire :** Une journée de consommation fictive lue depuis un fichier CSV. Les points rouges sont les valeurs du fichier (une par heure) ; la ligne bleu foncé est ce que le simulateur en fait (une valeur tous les quarts d'heure). Les deux se superposent : la conversion ne déforme pas les données.


**Interprétation.** Le CSV horaire en heure de Paris devient bien 4 quarts d'heure par heure en
UTC (minuit à Paris = 23 h UTC en novembre). Le cœur du simulateur ne verra jamais que ce format.

### Prix spot 2025

![Prix spot 2025](fig/e0_spot_2025.png)

> 📊 **Comment lire :** Prix de l'électricité sur le marché de gros français en 2025 (« spot », en € par MWh). À gauche, chaque jour : la bande violette va du prix le plus bas au plus haut du jour, la ligne donne la moyenne. À droite, le prix moyen à chaque heure de la journée, en hiver (bleu) et en été (jaune) : l'été, le prix s'effondre en milieu de journée à cause du solaire.

![Spread 2025](fig/e0_spread_2025.png)

> 📊 **Comment lire :** Le « spread » est l'écart entre le prix le plus haut et le plus bas d'une même journée : c'est ce qu'une batterie peut gagner en achetant au creux et en revendant au pic. À gauche, une barre par jour de 2025 ; à droite, combien de jours tombent dans chaque tranche d'écart. La bande jaune est la fourchette 80–180 €/MWh annoncée dans le plan.


| Indicateur 2025 | Valeur |
|---|---|
| Spot moyen | **61,1 €/MWh** (min −118, max 473) |
| Heures à prix négatif (< 0) sur l'année | **509 h**, réparties sur 97 jours (détail plus bas) |
| Heures à prix exactement nul (= 0) | **233 h** (soit 742 h à prix ≤ 0) |
| Spread journalier (max − min) | médiane **92 €/MWh**, moyenne 95 |
| Jours avec un spread entre 80 et 180 €/MWh | **64 %** (35 % en dessous, 1 % au-dessus) |
| Spread médian hiver / été | 79 / 100 €/MWh |

**Interprétation.**
- La fourchette « 80 à 180 €/MWh » du plan (tâche 3) est **confirmée pour deux jours sur trois**,
  mais elle est plutôt basse que haute : la moitié des jours est sous 92 €/MWh et seul 1 % dépasse 180.
- Le profil horaire est en **« canard »** : prix bas, voire négatifs, en milieu de journée l'été (le
  solaire inonde le marché) et pics le matin et le soir. C'est exactement le creux que le PV
  subit et que la batterie peut exploiter.
- Le spread est plus grand **l'été** (100) que l'hiver (79) : il est porté par le solaire.

### Zoom : le jour record du lundi 20 janvier 2025 (spread de 359 €/MWh)

Ce sont bien des **données réelles** : les prix day-ahead (fixés la veille) de la zone de prix France,
récupérés par l'API Energy-Charts (source citée par l'API : Bundesnetzagentur | SMARD.de). Le pic visible en janvier sur le graphique du spread est
**un seul jour**, le lundi 20/01/2025 : de **114 €/MWh à 3 h** à **473 €/MWh de 18 h à 19 h**.
Les 5 jours suivants du classement ont tous un spread inférieur à 200 €/MWh. Trois d'entre eux sont des
jours à prix très négatifs (1er mai, 6 avril, 22 juin : jusqu'à −118 €/MWh), pas des jours à prix très hauts.

![Jour record](fig/e0_jour_record.png)

> 📊 **Comment lire :** À gauche, le prix heure par heure le 20/01/2025, en France (violet) et en
> Allemagne (pointillés rouges). Au centre et à droite, pour chaque jour autour du 20/01 : la
> production des éoliennes (barres, la rouge = le 20/01) et la consommation (ligne, axe de droite),
> en France puis en Allemagne. Le 20/01, il n'y a presque pas de vent alors que la consommation est forte.

| 20/01/2025 | Ce jour-là | Moyenne de janvier |
|---|---|---|
| Vent en France | **1,8 GW** | 7,7 GW |
| Vent en Allemagne | **4,9 GW** | 20,7 GW |
| Consommation France | **74 GW** | 66 GW |
| Consommation Allemagne | 63 GW | 59 GW |
| Centrales à gaz en France | **7,4 GW** | 4,0 GW |
| Prix France / Allemagne à 18 h | **473 / 473 €/MWh** | – |

**Pourquoi ce pic ?** Ce que les données montrent :
1. **Froid, pas de vent et nuit tombée :** un lundi d'hiver, avec une consommation élevée en France et en Allemagne, et
   des éoliennes presque à l'arrêt **des deux côtés du Rhin** (4 fois moins de vent que d'habitude en
   Allemagne). À 18 h, le solaire est à zéro. Les Allemands appellent ce type de situation
   *Dunkelflaute* (« calme sombre »).
2. **Le prix européen tire le prix français :** les marchés européens sont couplés. À 18 h, la
   France et l'Allemagne ont **exactement le même prix (473,28 €)**, alors que la France est
   **exportatrice** (5,4 GW d'exports en moyenne ce jour-là). Quand les lignes d'interconnexion sont saturées, les prix
   se séparent : à 17 h, 583 € en Allemagne contre 276 € en France.
3. **Les centrales les plus chères fixent le prix :** sur ce marché, le prix de l'heure est celui de la
   dernière centrale appelée pour satisfaire la demande. Pour passer la pointe de 18 h, il faut appeler des
   centrales coûteuses : le gaz produit presque deux fois plus que d'habitude en France ce jour-là.

*Limite :* les données confirment le vent, la consommation, le gaz et le couplage des prix. Je n'ai pas
vérifié les autres causes possibles (indisponibilités de centrales, prix du gaz ce jour-là).

**Pour le projet :** un tel jour est idéal pour une batterie (acheter à 114 €, revendre à 473 €), mais
il est **unique dans l'année**. On ne peut pas bâtir une rentabilité sur ce genre d'événement.

### Zoom : les heures à prix négatif ou nul

**Comment est compté « 509 h » :** les prix sont publiés par quart d'heure (par heure avant octobre 2025). J'additionne
tous les quarts d'heure de 2025 où le prix est **strictement négatif**, puis je convertis en heures
(4 quarts d'heure = 1 h). Ces 509 h ne sont **pas consécutives** : elles sont réparties sur **97 jours
différents**. S'y ajoutent **233 h à prix exactement nul**.

![Heures négatives](fig/e0_heures_negatives.png)

> 📊 **Comment lire :** Les heures à prix négatif de 2025, découpées de quatre façons. En haut à gauche,
> par mois (bleu : prix négatif ; gris : prix exactement nul). En haut à droite, par heure de la journée.
> En bas à gauche, par niveau de prix : la grande majorité est juste sous zéro. En bas à droite, par jour
> de la semaine (rouge : week-end).

| Question | Réponse (2025) |
|---|---|
| **Quels mois ?** | **avril à juin** (353 h sur 509) puis août–septembre (123 h) ; **aucune** de novembre à février |
| **Quelles heures ?** | **87 %** entre 10 h et 17 h, pic vers 14 h ; seulement 36 h la nuit |
| **Quels jours ?** | **49 %** le samedi ou le dimanche (alors que le week-end ne représente que 28 % des jours) ; le prix le plus bas est tombé un **jour férié** (jeudi 1er mai, −118 €/MWh) |
| **Quel niveau ?** | **très faible la plupart du temps** : prix médian −0,06 €/MWh ; 282 h entre −0,1 et 0 €/MWh ; seulement **108 h sous −5 €/MWh** et 17 h sous −50 €/MWh |
| **Jours les plus touchés** | 05/06 (16 h), 05/08 (14 h), 07/09 (13 h), 25/05 et 03/06 (10 h) |

**Pourquoi ?** Un prix négatif veut dire que des producteurs **paient pour continuer à produire**.
Cela arrive quand la production qu'on ne peut ou ne veut pas arrêter dépasse ce que le marché absorbe :
- **beaucoup de soleil** (milieu de journée, printemps–été) : le parc solaire français a gagné
  environ 5 GW en un an (voir § PV) ;
- **peu de consommation** : week-ends, jours fériés, pas de chauffage au printemps ;
- **des centrales qu'on ne peut pas ou ne veut pas arrêter** : le nucléaire et l'hydraulique au fil de l'eau
  ne peuvent pas baisser autant ni aussi vite que nécessaire ; selon leur contrat de soutien, certains
  producteurs renouvelables n'ont pas intérêt à s'arrêter *(mécanismes non vérifiés en détail ici)* ;
- **des voisins dans la même situation** (Allemagne, Espagne : beaucoup de solaire aussi), donc
  l'export ne suffit pas à écouler le surplus.

*Hypothèses non vérifiées dans les données :* les 282 h « à peine négatives » (entre −0,1 et 0) viennent
probablement d'offres placées juste sous zéro par certains producteurs ; le creux de juillet (7 h seulement)
n'est pas expliqué ici (consommation de climatisation ? moins de nucléaire disponible ?). Il faudrait regarder les données de production en détail.

**Pour le projet :** les prix négatifs tombent **exactement quand les panneaux produisent le plus**.
1. Le surplus solaire revendu au spot ne vaut presque rien à ces heures-là (14 €/MWh en moyenne pour la PME, § 3).
2. Une batterie peut s'y **charger gratuitement, voire en étant payée**, pour restituer le soir.
3. Mais en volume, ces heures restent rares (≈ 6 % de l'année) et souvent à peine négatives.

### Production PV : deux sources comparées

![Profils PV](fig/e0_pv_profils.png)

> 📊 **Comment lire :** À gauche, la production moyenne d'1 kWc de panneaux (kWc = puissance maximale) au cours d'une journée, mois par mois : 0,5 veut dire que le panneau produit la moitié de sa puissance maximale. À droite, l'énergie produite chaque mois par 1 kWc, selon deux sources de données (bleu et orange) : elles donnent presque la même chose.

![Sources PV](fig/e0_pv_sources.png)

> 📊 **Comment lire :** Comparaison des deux sources de données solaires. À gauche, chaque point est un quart d'heure de 2025 : s'il est sur la diagonale, les deux sources sont d'accord, ce qui est presque toujours le cas. À droite, la puissance solaire installée en France chaque année selon chaque source : elles diffèrent d'environ 7 %.


| Indicateur 2025 | Energy-Charts | RTE éCO2mix |
|---|---|---|
| Productible (kWh/kWc/an) | **1 069** | **1 068** |
| Puissance installée 2025 | 28,25 GW | 30,44 GW |
| Quarts d'heure manquants | 20 (dont 4 h le 10/12) | 2 |

**Interprétation.**
- Les deux sources donnent **le même productible annuel** (écart < 0,1 %) et une corrélation de
  0,99 au quart d'heure, alors que leurs puissances installées diffèrent de 7 %. Leurs
  périmètres sont donc cohérents entre eux. 1 069 kWh/kWc est proche des ~1 100 de la fiche prix : bon
  signe pour le modèle « facteur de charge national ».
- Limite : c'est un profil **national lissé** ; un site réel aura des journées plus « en dents de scie ».
- Les trous de données sont traités **explicitement** : interpolés s'ils durent ≤ 1 h, sinon le calcul
  s'arrête. Les scénarios 2025 autorisent 4 h (`max_gap_hours: 4`) pour le trou du 10/12 entre 16 h et 20 h, presque
  tout après le coucher du soleil.

---

## Étape 1 – Consommation bottom-up

| Test | Attendu | Obtenu |
|---|---|---|
| `test_frigo_parametres_du_plan` | ≈ 1 kWh/jour (plan) | **2,24 kWh/jour** ⚠️ voir ci-dessous |
| `test_frigo_aleatoire_mais_energie_constante` | aléa sur l'heure des cycles, énergie identique | ✅ |
| `test_appareils_a_horaire_fixe` | TV 0,5 kWh, éclairage 1,6 kWh | ✅ |
| `test_marche_quotidienne` | lave-linge 4 kWh/jour, dans sa plage horaire | ✅ |
| `test_chauffage_degres_jours` | k = 2, T = 5 °C → 30 kWh ; T ≥ 15 °C → 0 | ✅ |
| `test_changement_d_heure` | journée de 25 h correctement comptée | ✅ |
| `test_studio_environ_10_kwh_par_jour` | ≈ 10 kWh/jour | **10,34 kWh/jour** ✅ |
| `test_jours_ouvres` | appareil actif du lundi au vendredi seulement | ✅ |

![Frigo](fig/e1_frigo.png)

> 📊 **Comment lire :** Consommation simulée d'un réfrigérateur pendant 3 heures. En gris, son fonctionnement minute par minute (400 W pendant 7 min, 2 fois par heure) ; en bleu foncé, la moyenne par quart d'heure utilisée par le simulateur. La moyenne (93 W en continu) donne 2,24 kWh par jour, et non les 1 kWh annoncés dans le plan.


**Interprétation – incohérence à trancher.** 400 W × (2 × 7 min) par heure × 24 h =
0,4 × 14/60 × 24 = **2,24 kWh/jour**, pas 1. Soit la conso visée (≈ 1 kWh/jour, plus réaliste pour
un frigo récent) est la bonne et il faut ~3 min de marche par cycle, ou 200 W ; soit les
paramètres sont bons et la conso est de 2,24. **J'ai gardé les paramètres du plan** en attendant ta décision.

![Studio semaine](fig/e1_studio_semaine.png)

> 📊 **Comment lire :** Consommation simulée d'un studio pendant une semaine, appareil par appareil (une couleur par appareil, empilées). À droite, la journée « moyenne » : la ligne est la moyenne, la bande grise contient 80 % des jours. Les pics du soir viennent du lave-vaisselle, ceux de la journée du lave-linge.

![Studio par appareil](fig/e1_studio_par_appareil.png)

> 📊 **Comment lire :** Énergie consommée par jour par chaque appareil du studio. Le total, 10,34 kWh/jour, correspond aux ≈ 10 kWh attendus. Le lave-linge et le lave-vaisselle pèsent plus de la moitié, parce que j'ai supposé qu'ils tournent tous les jours.


**Interprétation.** Le studio atteint 10,34 kWh/jour, mais c'est en partie **par construction** :
j'ai supposé un lave-linge et un lave-vaisselle tous les jours (6 kWh à eux deux, soit 58 % du
total). Avec un frigo à 1 kWh et des machines 3 fois par semaine, on tomberait vers 6–7 kWh/jour.
La courbe est très « en marches d'escalier » : c'est la limite du bottom-up simple (pas d'aléa
sur les puissances, pas de foisonnement).

![PME semaine](fig/e1_pme_semaine.png)

> 📊 **Comment lire :** Consommation simulée d'une PME de bureaux inventée pendant une semaine de juin (une couleur par usage). On voit le socle permanent (serveurs, froid), la journée de bureau en semaine, le pic de la cantine à midi et la recharge des véhicules. Le week-end, il ne reste que le socle.


**Interprétation.** Pour tester batterie et PV sur un client où ils ont du sens, j'ai **inventé**
une PME de bureaux : talon 15 kW (serveurs, froid), 45 kW de 8 h à 19 h en semaine, cantine 30 kW
à midi, recharge de véhicules 22 kW pendant 2 h à une heure aléatoire. Total : **288 MWh/an, pointe
112 kW**. Ce profil est à remplacer par une vraie courbe dès qu'on en aura une.

---

## Étape 2 – Coût sans équipement

| Test | Attendu | Obtenu |
|---|---|---|
| `test_bloc_spot_exemple_270_eur` | bloc 192 € + spot 78 € = **270 €** ; 90 €/MWh | ✅ (revente nuit −9,6 €, achat 87,6 €) |
| `test_comparaison_spot_pur_et_prix_fixe` | 276 € / 240 € | ✅ |
| `test_revente_au_spot_quand_puissance_negative` | la revente diminue le coût | ✅ |
| `test_prix_manquant_refuse` | refus de calculer s'il manque un prix | ✅ |
| `test_scenario_exemple_bloc_spot_via_csv`, `test_cli` | même résultat via YAML + CSV + ligne de commande | ✅ |

![Exemple 270 €](fig/e2_exemple_270.png)

> 📊 **Comment lire :** Exemple de la fiche « bloc + spot ». Le client achète d'avance 100 kW à prix fixe (pointillés). Quand il consomme plus (zone rouge), il achète le reste au prix du marché ; quand il consomme moins (zone verte), il revend l'excédent. La ligne violette est le prix du marché (axe de droite). À droite, le coût de la journée selon trois contrats : on retrouve les 270 € de la fiche.


*(Ligne violette : prix spot, axe de droite.)*

**Interprétation.** Le cas de référence de la fiche est retrouvé **exactement**, par les trois
chemins (fonction, scénario, ligne de commande).

![PME offres](fig/e2_pme_offres.png)

> 📊 **Comment lire :** À gauche, la facture d'énergie de la PME mois par mois selon trois contrats : prix du marché seul (violet), prix fixe à 80 €/MWh (gris), ou mélange des deux (bleu). À droite, le prix moyen du marché chaque mois, comparé au prix fixe de 80. En 2025, le marché a presque toujours été moins cher que le fixe.


| PME, 2025 | Coût annuel de l'énergie |
|---|---|
| Spot pur | **16 860 €** (58,6 €/MWh pondéré par la conso) |
| Bloc 30 kW à 80 €/MWh + spot | 21 834 € |
| Prix fixe 80 €/MWh | 23 019 € |

**Interprétation.**
- En 2025, le spot (61 €/MWh en moyenne) est **sous** le prix fixe de 80 €/MWh que j'ai pris pour
  le bloc : le bloc coûte donc plus cher que le spot pur. C'est l'assurance que l'on paie pour un
  budget sécurisé. Le prix de 80 €/MWh est une hypothèse de la fiche, pas un vrai prix de marché à terme.
- Point utile pour la suite : **le gain d'un équipement est identique en spot pur et en bloc + spot**.
  Le bloc ajoute un terme constant (bloc × (prix bloc − spot)) qui ne dépend pas de la conso. La
  batterie et le PV agissent seulement sur la part au spot.
- Les mois d'été coûtent moins, à cause d'un spot bas en mai–juin.

---

## Étape 3 – PV seul

| Test | Attendu | Obtenu |
|---|---|---|
| `test_conversion_rayonnement_exemples_du_plan` | 1000 J/cm² → 0,14 ; 1700 → 0,24 kW/m² | **0,139 / 0,236** ✅ |
| `test_pv_depuis_facteur_de_charge_et_rayonnement` | P = cf × kWc ; plafond 250 W/m² | ✅ |
| `test_pv_seul_autoconsommation_et_surplus` | 4 kWh autoconsommés, 8 revendus, 20 achetés | ✅ |
| `test_revente_au_prix_de_rachat` | surplus payé 1,1 c€/kWh | ✅ |
| `test_surcout_sur_les_kwh_achetes` | surcoût appliqué aux seuls kWh achetés | ✅ |

![Conversion](fig/e3_conversion.png)

> 📊 **Comment lire :** Vérification d'un calcul du plan : on convertit une quantité de soleil reçue en 4 heures (en J/cm²) en électricité produite par m² de panneau, avec un rendement de 20 %. Les deux barres doivent valoir 0,14 et 0,24 kW/m², ce qui est le cas.

![PV jour été semaine](fig/e3_pv_jour_ete_semaine.png)

> 📊 **Comment lire :** Un mercredi de juin à la PME, avec 100 kWc de panneaux. La ligne foncée est la consommation ; en orange, l'électricité solaire consommée sur place ; en vert, le surplus revendu ; en pointillés bleus, ce qui est acheté au réseau (sous zéro = revendu). En semaine, presque tout le solaire est consommé sur place.

![PV jour été samedi](fig/e3_pv_jour_ete_samedi.png)

> 📊 **Comment lire :** Même graphique pour un samedi de juin : les bureaux sont fermés, la consommation est faible et presque toute la production solaire part en vert, c'est-à-dire revendue au réseau, souvent à un prix très bas ce jour-là.

![PV jour hiver](fig/e3_pv_jour_hiver.png)

> 📊 **Comment lire :** Même graphique pour un jour de janvier : la production solaire est faible et courte. Elle ne couvre qu'une petite partie de la consommation et il n'y a aucun surplus.

![PV mensuel](fig/e3_pv_mensuel.png)

> 📊 **Comment lire :** Ce que deviennent, mois par mois, les kWh produits par les 100 kWc de la PME : consommés directement (orange), stockés en batterie (ici aucun, car il n'y a pas de batterie dans ce cas) ou revendus (vert). La production est 4 fois plus forte en été qu'en hiver.


| PME + 100 kWc (2025) | Valeur |
|---|---|
| Production | 106 947 kWh |
| Autoconsommation (part du PV utilisée sur place) | **87 %** |
| Autoproduction (part de la conso couverte par le PV) | **32 %** |
| Valeur moyenne d'un kWh PV autoconsommé / revendu | **39 €/MWh / 14 €/MWh** (spot moyen 61) |

**Interprétation.**
- En semaine, le PV est presque entièrement absorbé par les bureaux ; **le surplus apparaît le
  week-end** (samedi : quasiment tout est revendu).
- **Effet de cannibalisation :** un kWh solaire vaut en moyenne 39 €/MWh au spot, contre 61 pour un
  kWh moyen, parce que le solaire produit aux heures où le prix est bas. Le surplus revendu ne vaut
  que 14 €/MWh, car il tombe surtout les week-ends ensoleillés à prix négatif ou nul.

![Dimensionnement PV](fig/e3_dimensionnement_pv.png)

> 📊 **Comment lire :** Que se passe-t-il si on pose plus ou moins de panneaux sur la PME ? À gauche : la part du solaire consommée sur place (orange) baisse quand on en pose beaucoup, tandis que la part de la consommation couverte par le solaire (vert) monte. À droite : l'économie annuelle. Si le surplus est revendu au prix du marché, elle croît en ligne droite ; s'il n'est pas payé (rouge), les grandes installations rapportent beaucoup moins.


**Interprétation.** Au-delà de ~50 kWc, l'autoconsommation baisse : le PV dépasse la conso le midi.
Si le surplus est revendu au spot, le gain est **strictement proportionnel** aux kWc, car un kWh
autoconsommé et un kWh revendu valent alors la même chose. Si le surplus n'est pas payé, la
courbe rouge s'aplatit : 400 kWc rapportent 9 000 € au lieu de 15 400 €. **Le contrat de
revente (et le TURPE évité) décide du bon dimensionnement.**

---

## Étape 4 – Batterie « règle simple » (stocker le surplus PV)

| Test | Attendu | Obtenu |
|---|---|---|
| `test_batterie_un_pas` | E += η·P·Δt ; P bornée à 0,5 C ; pas de décharge sous SOC min | ✅ |
| `test_batterie_surplus_pv_rendement_aller_retour` | 8 kWh chargés → 7,2 kWh restitués (90 %) | ✅ |
| `test_batterie_pleine_le_surplus_est_revendu` | SOC plafonné à 90 %, le reste est revendu | ✅ |
| `check_balance` (appelé à chaque simulation) | bilan P_grid, SOC dans les bornes, énergie conservée | ✅ sur toutes les simulations annuelles |

![Batterie studio été](fig/e4_studio_batterie_semaine.png)

> 📊 **Comment lire :** Une semaine de juin pour le studio équipé de 3 kWc de panneaux et d'une batterie de 5 kWh. En haut, le niveau de charge de la batterie (en %, de 10 à 90 %). En bas : barres jaunes = la batterie se charge avec le soleil, barres rouges = elle restitue l'énergie le soir ; la ligne violette est le prix du marché. Elle se remplit le jour et se vide le soir, presque chaque jour.

![Batterie studio hiver](fig/e4_studio_batterie_hiver.png)

> 📊 **Comment lire :** Même graphique pour une semaine de janvier : le soleil suffit à peine pour la consommation de la journée, la batterie reste presque vide. En hiver, elle sert peu.

![SOC année](fig/e4_soc_annee.png)

> 📊 **Comment lire :** Niveau de charge de la batterie du studio sur toute l'année. Il ne sort jamais des limites fixées (10 % et 90 %, pointillés rouges). C'est un test de bon fonctionnement du modèle de batterie. Elle est surtout utilisée d'avril à septembre.

![Bilan studio](fig/e4_studio_bilan.png)

> 📊 **Comment lire :** Bilan d'une année pour le studio avec ses panneaux, sans batterie (rouge) puis avec batterie (bleu), en kWh. La batterie fait passer les achats au réseau d'environ 2 700 à 1 450 kWh et réduit fortement la revente du surplus. Elle perd environ 140 kWh par an (rendement de 90 %).


| Studio, 3 kWc (2025) | Sans batterie | Avec 5 kWh |
|---|---|---|
| Autoconsommation | 33 % | **77 %** |
| Autoproduction | 28 % | **62 %** |
| Achat réseau | 2 728 kWh | 1 449 kWh |
| Cycles / an ; pertes | – | 337 ; 142 kWh |
| Coût énergie (spot, surplus à 1,1 c€) | 191 € | 109 € |

**Interprétation.**
- Le modèle de batterie est **physiquement cohérent** : SOC toujours entre 10 et 90 %, énergie
  conservée à 4·10⁻¹⁴ kWh près sur l'année, pertes de 10 % retrouvées.
- L'été, la batterie se remplit chaque jour et se vide le soir : c'est le cas d'usage idéal.
  L'hiver, elle se remplit à peine : le PV couvre déjà difficilement la conso.
- La batterie **double l'autoconsommation** du studio. En euros, elle ne fait pourtant gagner que
  **83 €/an**, car on ne compte que le prix de l'énergie (~70 €/MWh en moyenne pour le studio).

---

## Étape 5 – Batterie « prix » (prix du lendemain connus)

| Test | Attendu | Obtenu |
|---|---|---|
| `test_strategie_prix_gagne_les_jours_a_fort_spread` | gain 1,349 € > règle simple (0 €) | ✅ |
| `test_strategie_prix_ne_charge_pas_sans_spread` | pas d'achat pour stocker si le spread ne couvre pas les pertes | ✅ |
| `test_strategie_prix_vide_la_batterie_meme_si_la_conso_est_faible` | décharge complète même à 1 kW de conso | ✅ |
| `test_strategie_prix_respecte_la_limite_reseau` | la charge ne dépasse pas la puissance souscrite | ✅ |
| `test_strategie_prix_anticipe_le_surplus_solaire` | si le soleil du jour suffit à remplir la batterie, rien n'est acheté au réseau | ✅ |

**Règle utilisée :** chaque jour, on charge depuis le réseau sur les quarts d'heure les moins chers
et on décharge sur les plus chers, en choisissant juste assez de quarts d'heure pour remplir puis
vider la batterie. On le fait seulement si le spread du jour couvre les pertes. Le surplus PV est toujours stocké.
**La météo du lendemain étant connue** (hypothèse du PowerPoint), on n'achète au réseau que ce que le surplus solaire
attendu ne remplira pas. Cette anticipation, ajoutée après la simulation de Strasbourg, rapporte 6 à 11 % de plus et réduit
d'environ 20 % les achats faits pour remplir la batterie.

![Semaine prix mars](fig/e5_semaine_prix.png)

> 📊 **Comment lire :** Une semaine de mars à la PME (100 kWc + batterie 100 kWh) pilotée selon les prix. En haut, le niveau de charge de la batterie. En bas : barres bleues = charge depuis le réseau quand le prix (ligne violette) est bas ; barres rouges = décharge quand il est haut ; barres jaunes = charge avec le surplus solaire. La batterie fait environ un « plein puis vidange » par jour.

![Semaine prix juin](fig/e5_semaine_prix_ete.png)

> 📊 **Comment lire :** Même graphique pour une semaine de juin : la batterie se charge en milieu de journée, quand le prix est au plus bas (souvent proche de zéro grâce au solaire), et se vide le matin et le soir, quand il remonte.


**Interprétation.** La batterie fait environ un cycle par jour : elle se charge **la nuit** ou **au
creux de midi** (prix bas ou négatifs) et se décharge **le matin et le soir**. En juin, la
charge de midi coïncide avec le creux solaire : stocker l'énergie solaire, c'est aussi acheter le kWh le moins cher de la journée.

![Stratégies](fig/e5_strategies.png)

> 📊 **Comment lire :** Économie annuelle de la PME selon l'équipement installé et la façon de piloter la batterie. Barre bleue = économie sur l'achat d'électricité ; barre verte = économie sur les pénalités payées quand on dépasse la puissance prévue au contrat (négative = on en paie plus). Le total est écrit à droite. Le pilotage selon les prix rapporte le plus sur l'énergie ; le pilotage « écrêter les pointes » (peak shaving) supprime toutes les pénalités.


| PME, économie annuelle vs « rien » | Énergie | Pénalités | Total | Cycles/an |
|---|---|---|---|---|
| PV 100 kWc seul | 3 841 € | 2 179 € | 6 020 € | – |
| PV + batterie, surplus PV | 4 185 € | 2 179 € | 6 364 € | 84 |
| **PV + batterie, prix** | **5 593 €** | 2 179 € | **7 772 €** | 337 |
| PV + batterie, prix **sans limite de puissance** | 5 588 € | **−1 308 €** | 4 280 € | 337 |
| Batterie seule, prix | 1 828 € | 0 € | 1 828 € | 345 |
| Batterie seule, surplus PV | 0 € | 0 € | 0 € | 0 |
| **Batterie seule, peak shaving** | 6 € | **2 640 €** | 2 646 € | 39 |
| PV + batterie, peak shaving | 3 839 € | 2 640 € | 6 479 € | 1 |

![Gain vs spread](fig/e5_gain_vs_spread.png)

> 📊 **Comment lire :** Chaque point est un jour de 2025, pour la PME avec une batterie seule pilotée selon les prix. En abscisse, l'écart entre le prix le plus haut et le plus bas du jour ; en ordonnée, ce que la batterie a fait gagner ce jour-là (couleur = mois). Plus l'écart est grand, plus le gain est élevé ; il dépasse rarement 15 € par jour. Les quelques points sous zéro sont des jours où la règle simple s'est trompée et a perdu un peu d'argent.


**Interprétation.**
- **Validation de l'étape :** sur les jours à fort spread (quart supérieur), la règle « prix »
  rapporte **7,40 €/jour** contre 0 € pour la règle simple (batterie seule) ; le gain croît
  nettement avec le spread. ✅
- Sur une PME qui autoconsomme déjà 87 % de son PV, la règle « surplus PV » n'apporte presque
  rien (+344 €) : il n'y a pas de surplus à stocker en semaine. **C'est l'arbitrage de prix qui fait travailler la batterie.**
- ⚠️ **Découverte :** si on laisse la batterie se charger depuis le réseau sans limite, la pointe passe de 112
  à **136 kW** et les pénalités augmentent (−1 308 €). Il faut toujours brider la charge par la
  puissance souscrite. C'est maintenant le comportement par défaut dès qu'un scénario déclare une puissance souscrite.
- 5 % des jours, la règle perd un peu d'argent : elle ne regarde que les seuils de prix, pas
  **l'ordre** des heures (elle peut décharger le matin à un prix « haut » puis manquer d'énergie pour un soir encore plus cher).
  Une optimisation (étape 9) ferait mieux.
- Première version de la règle (corrigée pendant les tests) : elle visait les 7 quarts d'heure les plus chers en
  supposant une décharge à 50 kW, alors que la PME ne consomme que ~15 kW le soir. La batterie ne
  se vidait jamais. La correction a fait passer le gain de 1 207 à **1 828 €/an** (+51 %).

---

## Étape 6 – Peak shaving

| Test | Attendu | Obtenu |
|---|---|---|
| `test_peak_shaving_ecrete_les_pointes` | pointe 30 → 20 kW ; recharge sous 18 kW ; pénalité 100 € → 0 € | ✅ |

![Monotone](fig/e6_monotone.png)

> 📊 **Comment lire :** Les 8 760 heures de l'année, classées de la plus forte à la plus faible puissance achetée au réseau. Le pointillé est la puissance prévue au contrat (90 kW) ; tout ce qui dépasse est pénalisé. Rouge : sans équipement, la PME dépasse quelques centaines d'heures par an. Bleu : la batterie écrête exactement à 90 kW. Vert : une batterie chargée sans limite crée une pointe encore plus haute (136 kW).

![Jour de pointe](fig/e6_jour_pointe.png)

> 📊 **Comment lire :** Les deux jours où la PME consomme le plus. Rouge : puissance achetée sans équipement ; bleu : avec une batterie qui écrête les pointes ; pointillés : puissance prévue au contrat (90 kW). La courbe bleue ne dépasse jamais le pointillé : la batterie fournit le complément pendant les pics de midi et se recharge ensuite, quand la consommation baisse.

![SOC peak shaving](fig/e6_soc_peak_shaving.png)

> 📊 **Comment lire :** Même période, vue depuis la batterie : en haut son niveau de charge, en bas ses charges (bleu) et décharges (rouge). Elle ne se décharge que pendant les pics, puis se recharge doucement. Elle travaille peu, ce qui ménage son usure.


**Interprétation.**
- La pointe annuelle passe de **112 à 90 kW**, exactement la puissance souscrite, et la pénalité de
  2 640 € à **0 €**. La batterie ne fait que 39 cycles par an : elle s'use très peu.
- La monotone montre que la PME ne dépasse 90 kW que **~500 h/an** (cantine + recharge des véhicules) :
  des pointes courtes, idéales pour une batterie.
- ⚠️ **La pénalité de 10 €/kW/mois est inventée** et la règle de calcul (dépassement maximal du mois) est
  simplifiée. Comme le gain du peak shaving en dépend entièrement, il faut une vraie grille tarifaire avant de conclure.
  Dans la simulation de Strasbourg, je l'ai remplacée par la règle réelle du tarif C4, 12,41 € par heure de
  dépassement (voir « Mes choix »).

---

## Étape 7 – Rentabilité

| Test | Attendu | Obtenu |
|---|---|---|
| `test_capex_et_cout_usure` | fiche 5 : 100 kWh, 40 000 €, 5 000 cycles, 80 % → 0,10 €/kWh | ✅ |
| `test_temps_de_retour` | CAPEX 9 500 €, gain 950 €/an → 10 ans ; vie plafonnée à 15 ans | ✅ |

**Hypothèses :** prix unitaires de la fiche 2 (bas / médian / haut), durée de vie de la batterie = min(5 000
cycles, 15 ans), PV 25 ans, OPEX du PV 1,5 %/an, sans actualisation ni dégradation, année 2025 répétée.

![Temps de retour](fig/e7_temps_de_retour.png)

> 📊 **Comment lire :** Nombre d'années nécessaires pour que les économies remboursent l'achat de l'équipement, selon que l'équipement est payé au prix bas (vert), moyen (jaune) ou haut (rouge) des fourchettes du devis. Le trait noir est la durée de vie de l'équipement : si la barre le dépasse, l'équipement meurt avant d'être remboursé. La plupart des barres le dépassent.


| Cas (2025, énergie au spot) | Retour prix bas / médian / haut | Durée de vie | Rentable ? |
|---|---|---|---|
| PME : PV 100 kWc | 12 / 28 / 54 ans | 25 ans | **seulement au prix bas** |
| PME : batterie 100 kWh seule, arbitrage | 16 / 23 / 30 ans | 14,5 ans | **non** |
| PME : batterie 100 kWh seule, peak shaving | 11 / 16 / 21 ans | 15 ans | **limite** (bas : oui) |
| PME : batterie ajoutée au PV, arbitrage | 17 / 24 / 31 ans | 14,8 ans | non |
| Studio : PV 3 kWc | jamais (médian) | 25 ans | non (au spot) |
| Studio : batterie 5 kWh ajoutée | 36 / 58 / 79 ans | 14,8 ans | non (au spot) |

![Taille batterie](fig/e7_taille_batterie.png)

> 📊 **Comment lire :** Pour la PME, batterie seule pilotée selon les prix, de 25 à 400 kWh. Ligne bleue : ce qu'elle fait gagner par an. Zone rouge : ce qu'elle coûte par an (prix d'achat réparti sur sa durée de vie, du moins cher au plus cher). La ligne bleue reste toujours sous la zone rouge : quelle que soit la taille, la batterie coûte plus qu'elle ne rapporte.

![Usure vs spread](fig/e7_usure_vs_spread.png)

> 📊 **Comment lire :** Chaque fois qu'une batterie se charge puis se vide, elle s'use : cela « coûte » environ 75 à 140 € par MWh restitué (traits verticaux, selon son prix d'achat). L'histogramme montre, pour chaque jour de 2025, ce que rapporte un cycle « acheter au plus bas, revendre au plus haut » (pertes comprises). Seuls les jours à droite des traits sont rentables, soit environ un quart des jours.


**Interprétation.**
- **Arbitrage seul : non rentable en 2025.** Le coût d'usure d'un kWh déchargé (CAPEX ÷ kWh
  restituables sur la vie) vaut **106 €/MWh** au prix médian, alors que le spread journalier × 90 % ne le
  dépasse que **24 % des jours**. Quelle que soit la taille, le gain annuel reste sous le coût annualisé.
- Au-delà de 200 kWh, le gain **baisse** (400 kWh rapportent moins que 200 kWh) : la règle charge
  sur trop de quarts d'heure pas assez bon marché, sous la contrainte de puissance souscrite. Une
  batterie plus grande ne peut pas faire moins bien avec un pilotage optimal : c'est une **limite de la règle simple**.
- **Ce qui peut rendre la batterie rentable : les pénalités de puissance**, avec peu de cycles et un fort
  gain par kWh, mais elles reposent ici sur une hypothèse inventée.

![Sensibilité surcoût](fig/e7_sensibilite_surcout.png)

> 📊 **Comment lire :** Sur une vraie facture, chaque kWh acheté coûte aussi des frais de réseau et des taxes, ignorés par défaut dans ce rapport. En abscisse, le montant de ces frais par MWh. À gauche, le gain annuel ; à droite, le nombre d'années pour rembourser (sous les traits noirs = rentable). Plus ces frais sont élevés, plus les panneaux deviennent rentables. Seule la batterie qui spécule sur les prix (vert) y perd, car elle achète plus de kWh qu'elle n'en rend.


**Interprétation de la sensibilité** (surcoût ajouté à chaque kWh acheté : acheminement + taxes) :
- **PV de la PME :** dès 50 €/MWh de surcoût évité, le retour tombe à 18 ans ; à 100 €/MWh, à **10,5 ans**. Le PV
  devient clairement rentable : ce sont ces coûts évités qui font sa valeur, plus que le spot.
- **Batterie du studio, ajoutée au PV :** à 200 €/MWh (ordre de grandeur d'un particulier, à vérifier), retour d'environ **14 ans**,
  soit à peu près sa durée de vie. C'est à la limite.
- **Batterie seule en arbitrage :** son gain **diminue** quand le surcoût augmente. Elle achète
  plus de kWh au réseau qu'elle n'en restitue (pertes de 10 %), et chaque kWh acheté supporte le surcoût. L'arbitrage pur
  est pénalisé par les tarifs de réseau.

---

## Étape 8 – Les 7 graphiques du plan (commande `python -m simu run … --out`)

Générés automatiquement pour la PME (PV 100 kWc + batterie 100 kWh, règle prix) ; même jeu pour le
studio dans [fig/e8_studio](fig/e8_studio). Export CSV de tous les pas : `results/pme/resultats.csv`.

### 1. Utilisation du solaire

![Utilisation du solaire](fig/e8_pme/1_utilisation_solaire.png)

> 📊 **Comment lire :** Ce que deviennent chaque mois les kWh produits par les 100 kWc de la PME, maintenant avec batterie : consommés directement (orange), stockés dans la batterie (vert foncé) ou revendus (vert clair). Le titre donne la production totale et la part utilisée sur place.


### 2. Utilisation de la batterie

![Utilisation de la batterie](fig/e8_pme/2_utilisation_batterie.png)

> 📊 **Comment lire :** Une semaine de juin de la batterie de la PME. En haut, son niveau de charge ; en bas, ses charges depuis le soleil (jaune) ou le réseau (bleu) et ses décharges (rouge), avec le prix du marché (ligne violette, axe de droite).


### 3. Courbe de charge brute

![Courbe de charge brute](fig/e8_pme/3_courbe_de_charge_brute.png)

> 📊 **Comment lire :** Consommation de la PME, avant tout équipement. À gauche, une semaine de juin ; à droite, la journée moyenne de l'année (ligne) et la plage dans laquelle se trouvent 80 % des jours (bande grise).


### 4. Ce qu'on achète au réseau

![Ce qu'on achète au réseau](fig/e8_pme/4_courbe_achetee.png)

> 📊 **Comment lire :** Ce que la PME achète au réseau pendant une semaine de juin, sans équipement (rouge) et avec panneaux et batterie (bleu). Sous zéro (zone verte), elle revend. Le pointillé est la puissance prévue au contrat. Avec l'équipement, les achats de la journée sont fortement réduits et ne dépassent plus le pointillé, et le week-end la PME revend.


### 5. Coût de l'énergie

![Coût de l'énergie](fig/e8_pme/5_cout_energie.png)

> 📊 **Comment lire :** Facture d'électricité de la PME, mois par mois, sans équipement (rouge) et avec panneaux et batterie (bleu). Le titre donne l'économie sur l'année et la légende les totaux annuels. Seul le prix de l'énergie est compté, sans frais de réseau ni taxes.


### 6. Coût de la batterie

![Coût de la batterie](fig/e8_pme/6_cout_batterie.png)

> 📊 **Comment lire :** La batterie de 100 kWh seule. À gauche, son prix d'achat selon trois devis (bas, moyen, haut). À droite, l'argent cumulé au fil des années : on part du prix d'achat (négatif) et on ajoute chaque année ce qu'elle fait gagner en plus des panneaux. Si la ligne croise zéro avant la fin (15 ans), la batterie est remboursée ; ici, jamais.


### 7. Coût des panneaux

![Coût des panneaux](fig/e8_pme/7_cout_panneaux.png)

> 📊 **Comment lire :** Même lecture pour les 100 kWc de panneaux, sur 25 ans. La ligne verte (prix d'achat bas) croise zéro au bout d'environ 12 ans : remboursé, puis bénéficiaire. Au prix moyen et au prix haut, les panneaux ne sont pas remboursés en 25 ans, si l'on ne compte que le prix de l'énergie.


**Interprétation.** L'économie mensuelle est assez régulière en euros (≈ 300 à 700 €/mois). L'hiver,
c'est surtout la batterie qui arbitre des prix élevés ; l'été, c'est le PV. En proportion, elle est
bien plus forte l'été (juillet : −55 %) que l'hiver (janvier : −20 %). Les graphiques 6 et 7 séparent bien les deux investissements. La batterie,
évaluée **en plus** du PV, ne rentre pas dans ses frais sur 15 ans, même au prix bas.
Le PV (gain de 6 020 €/an, pénalités évitées comprises) n'est rentable qu'au prix bas (retour
en 12 ans) ; au prix médian il finit à −14 500 € au bout de 25 ans (toujours sans acheminement ni taxes évités).

---

## Simulation Strasbourg / Grand Est (demandée au point du 23/11, slides 5 et 6)

C'est la simulation décrite dans le PowerPoint : **conso bottom-up (avec chauffage selon la température
réelle) + panneaux calculés d'après le rayonnement solaire réel + batterie + achat/vente au prix du marché**,
pour un client situé à **Strasbourg**, sur toute l'année 2025.

| Donnée | Source (API, sans clé) |
|---|---|
| Rayonnement solaire global, Grand Est, toutes les 3 h | RTE / ODRÉ : `rayonnement-solaire-vitesse-vent-tri-horaires-regionaux` |
| Température moyenne quotidienne, Grand Est | RTE / ODRÉ : `temperature-quotidienne-regionale` |
| Production solaire réelle du Grand Est (pour valider) | RTE éCO2mix régional : `eco2mix-regional-cons-def` + parc régional |
| Prix spot France (Strasbourg est dans la zone de prix France) | Energy-Charts : `price?bzn=FR` |

Lancer : `python -m simu run scenarios/studio_strasbourg.yaml --out results/studio_strasbourg`
(idem avec `pme_strasbourg.yaml`).

### Tests ajoutés

| Test | Ce qu'il vérifie | Résultat |
|---|---|---|
| `test_hauteur_du_soleil_strasbourg` | hauteur du soleil à midi le 21/06 (≈ 65°) et le 21/12 (≈ 18°), nuit < 0 | ✅ |
| `test_repartition_conserve_l_energie_du_jour` | les blocs de 3 h passés au 1/4 h gardent exactement l'énergie du jour | ✅ |
| `test_repartition_nulle_la_nuit_et_sans_marche` | rayonnement nul la nuit, pas de marche entre deux blocs, montée régulière le matin | ✅ |
| `test_lecture_rayonnement_et_format_standard` | lecture de l'API → format standard, maximum vers midi | ✅ |
| `test_temperature_jour_absent_interpole` | un jour absent du jeu (ex. 31/01) est interpolé et signalé | ✅ |
| `test_pv_par_rayonnement_chaine_du_plan` | 100 kWc = 400 m² ; 1000 W/m² × 20 % × 400 m² = 80 kW ; exemple 1000 J/cm² | ✅ |

### Du rayonnement à la production des panneaux

![Rayonnement](fig/st_rayonnement_jour.png)

> 📊 **Comment lire :** La donnée publiée (zones jaunes) est une moyenne du soleil reçu toutes les 3 heures,
> trop grossière pour une simulation au quart d'heure. La courbe orange est ce que le simulateur en fait :
> la même énergie, répartie selon la hauteur du soleil à Strasbourg (nulle la nuit, maximale à midi).
> À gauche, une journée d'été ensoleillée ; à droite, une journée d'hiver.

**Méthode (chaîne du PowerPoint, slide 6) :** rayonnement (W/m²) × rendement 20 % × surface, avec
surface = kWc ÷ Pmax 250 W/m² (100 kWc = 400 m²), plafonné à 250 W/m². Rayonnement sur une surface
**horizontale** : inclinaison et orientation des panneaux ne sont pas modélisées.

**Points vérifiés sur les données :**
- La valeur horodatée T est la **moyenne sur les 3 heures précédentes**, en UTC. C'est la convention du
  modèle météo du CEPMMT (ECMWF), confirmée par la corrélation avec la production réelle, identique l'été et l'hiver.
- La source attribue quelques W/m² à des blocs de nuit, signe d'un décalage d'environ 30 min. La méthode les
  reporte sur les heures de jour du même jour, sans perdre d'énergie.

![Validation PV](fig/st_validation_pv.png)

> 📊 **Comment lire :** À gauche, l'énergie produite chaque mois par 1 kWc de panneaux : calculée par le
> simulateur à partir du rayonnement (orange), mesurée par RTE sur l'ensemble des installations du Grand Est
> (vert) et sur toute la France (gris). À droite, une semaine de juin quart d'heure par quart d'heure :
> le modèle (orange) suit bien la production réelle (vert) jour après jour, nuages compris.

| 2025 | Modèle (rayonnement) | Réel Grand Est (RTE) | Réel France |
|---|---|---|---|
| Production annuelle par kWc | **1 076 kWh** | **1 068 kWh** | 1 069 kWh |
| Corrélation au 1/4 h avec le réel Grand Est | 0,93 | – | 0,94 |

**Interprétation.**
- **Sur l'année, le modèle tombe juste à 1 % près.** La chaîne du PowerPoint, avec Pmax 250 W/m² et un rendement de 20 %, est donc
  réaliste sans autre correction. Le fait que le facteur 0,2 × 4 m²/kWc = 0,8 corresponde aux pertes réelles est sans doute en partie
  une coïncidence, mais le résultat est là.
- **Par mois, il y a un biais saisonnier** : le modèle surestime le printemps et l'été (mai : +23 %) et sous-estime
  l'automne (octobre : −22 %). C'est cohérent avec un rayonnement **horizontal** : les vrais panneaux sont inclinés
  et captent mieux le soleil bas d'automne. Une correction d'inclinaison serait la prochaine amélioration.
- Au quart d'heure, le profil national réel colle un peu mieux (0,94) que le modèle (0,93) : le rayonnement
  est une moyenne régionale de modèle météo, publiée toutes les 3 h.
- ⚠️ **Anomalie dans la source RTE :** le **30/06/2025**, éCO2mix régional publie jusqu'à **3 824 MW** de solaire
  dans le Grand Est, pour un parc de **2 602 MW**. C'est impossible ; ce jour est exclu des corrélations.
- Les températures ODRÉ n'ont **pas de valeur pour le dernier jour de chaque mois** (31/01, 28/02…) : ces
  12 jours sont interpolés, et un avertissement le signale.

### Chauffage d'après la température réelle

![Température et chauffage](fig/st_temperature_chauffage.png)

> 📊 **Comment lire :** La ligne bleue est la température moyenne de chaque jour de 2025 dans le Grand Est
> (axe de droite) ; le pointillé marque 15 °C. Les barres rouges sont la consommation de chauffage du studio
> chaque jour (axe de gauche). Elles n'existent que les jours sous 15 °C et grandissent quand il fait froid :
> c'est la formule du PowerPoint, E = k × (20 °C − température).

| 2025, Grand Est | Valeur |
|---|---|
| Température moyenne quotidienne | de −2,8 °C à 28,6 °C |
| Jours sous 15 °C (chauffage) | 237 |
| Σ (20 − T) sur ces jours | 2 900 °C·jour |
| Chauffage du studio avec k = 0,5 kWh/°C/jour | **1 450 kWh/an** |

**k = 0,5 est mon choix** (voir « Mes choix ») : le PowerPoint ne donne pas de valeur.
- **Consommation du studio :** avec le chauffage et le frigo à 1,12 kWh/jour, il consomme **4 816 kWh/an (13,2 kWh/jour)**,
  un peu au-dessus des 4 300 kWh/an du PowerPoint.
- **D'où vient l'écart :** les machines tournent tous les jours dans le modèle, ce qui est sans doute trop.

![Studio janvier conso](fig/st_studio_conso_hiver.png)

> 📊 **Comment lire :** La consommation du studio pendant une semaine de janvier, appareil par appareil
> (couleurs empilées). Le chauffage forme un socle permanent, plus épais les jours froids, auquel s'ajoutent
> les pics des machines et de l'éclairage. À droite, la journée moyenne de cette semaine.

### Résultats

Avec les valeurs de « Mes choix » : spot + 75 €/MWh (studio) ou + 50 €/MWh (PME) sur chaque kWh acheté,
surplus du studio racheté 11 €/MWh, pénalité de 12,41 € par heure de dépassement pour la PME.

| 2025, Strasbourg | Studio (3 kWc + 5 kWh) | PME de bureaux (100 kWc + 100 kWh) |
|---|---|---|
| Consommation | 4 816 kWh (dont 1 450 de chauffage) | 287 739 kWh |
| Production PV | 3 229 kWh | 107 621 kWh |
| Autoconsommation / autoproduction | 70 % / 44 % | 90 % / 33 % |
| Cycles de batterie par an | 360 | 339 |
| Coût de l'énergie + acheminement et taxes, sans → avec équipement | 712 € → 380 € | 31 247 € → 21 245 € |
| Pénalités de dépassement, sans → avec | – | 1 834 € → 580 € |
| Gain annuel dû au PV | 181 € | 9 381 € (dont pénalités évitées) |
| Gain annuel dû à la batterie (en plus du PV) | 151 € | 1 875 € |
| Retour du PV, prix bas / médian / haut (durée de vie 25 ans) | 32 / 49 / 73 ans | **7 / 16** / 27 ans |
| Retour de la batterie, prix bas / médian / haut (durée de vie ≈ 14 ans) | 20 / 31 / 43 ans | 16 / 23 / 29 ans |

**Interprétation.**
- **Le PV de la PME devient rentable** au prix d'achat bas (7 ans) et médian (16 ans) : chaque kWh autoconsommé évite
  le spot **et** les 50 €/MWh d'acheminement et taxes. Au spot seul, il fallait 13 ans au prix bas et 32 au prix médian.
- **La batterie de la PME ne l'est toujours pas** (16 ans au mieux pour ≈ 15 ans de vie) : elle ne fait que
  déplacer des kWh, et ne gagne donc l'acheminement et les taxes que sur l'énergie solaire stockée.
- **Pour le studio, rien n'est rentable**, même avec 75 €/MWh d'acheminement et taxes évités. Les 3 kWc sont chers par kWc
  (prix de la classe 10 kWc), et l'été une grande partie du soleil est revendue 1,1 c€/kWh seulement.
- Le chauffage d'hiver rend la batterie utile **même sans soleil** : elle se charge la nuit, quand le prix est plus bas, et
  restitue au pic du soir (graphique ci-dessous).

![Studio hiver batterie](fig/st_studio_hiver_batterie.png)

> 📊 **Comment lire :** La batterie du studio pendant une semaine de janvier. En haut, son niveau de charge ;
> en bas, ses charges depuis le réseau (bleu) ou le soleil (jaune, très faibles en hiver) et ses décharges (rouge),
> avec le prix du marché (ligne violette). Elle se remplit chaque nuit quand le prix est bas et se vide le soir
> quand il est haut : en hiver, c'est le prix et non le soleil qui la fait travailler.

### Les 7 graphiques du PowerPoint – studio de Strasbourg

#### 1. Utilisation du solaire

![](fig/st_studio/1_utilisation_solaire.png)

> 📊 **Comment lire :** Ce que deviennent chaque mois les kWh produits par les 3 kWc du studio : consommés
> directement (orange), stockés dans la batterie (vert foncé) ou revendus (vert clair). L'été, une grande partie est
> revendue car le studio consomme peu en journée.

#### 2. Utilisation de la batterie

![](fig/st_studio/2_utilisation_batterie.png)

> 📊 **Comment lire :** Une semaine de juin. En haut, le niveau de charge de la batterie ; en bas, ses charges
> (jaune = soleil, bleu = réseau) et décharges (rouge), avec le prix du marché (violet). L'été, elle se remplit
> surtout avec le soleil de midi et se vide le soir.

#### 3. Courbe de charge brute

![](fig/st_studio/3_courbe_de_charge_brute.png)

> 📊 **Comment lire :** La consommation du studio, sans équipement, pendant une semaine de juin (à gauche) et
> la journée moyenne de l'année (à droite, avec la plage où se trouvent 80 % des jours). En été, il n'y a pas de chauffage.

#### 4. Ce qu'on achète au réseau

![](fig/st_studio/4_courbe_achetee.png)

> 📊 **Comment lire :** La puissance achetée au réseau pendant une semaine de juin, sans équipement (rouge) et
> avec panneaux + batterie (bleu). Sous zéro (vert), le studio revend son surplus solaire. Avec l'équipement, les
> achats du soir diminuent fortement (la batterie, remplie par le soleil, les couvre). Les pics bleus restants
> sont des soirées où la batterie de 5 kWh est déjà vide quand le lave-vaisselle démarre. En juin, elle ne se
> recharge pas au réseau la nuit : le soleil du lendemain suffit.

#### 5. Coût de l'énergie

![](fig/st_studio/5_cout_energie.png)

> 📊 **Comment lire :** La facture d'énergie du studio mois par mois, sans (rouge) et avec équipement (bleu).
> L'hiver coûte le plus cher à cause du chauffage et des prix élevés. Chaque kWh acheté est compté au prix du
> marché plus 75 €/MWh d'acheminement et taxes ; le surplus est revendu 1,1 c€/kWh. Le titre donne l'économie sur l'année.

#### 6. Coût de la batterie

![](fig/st_studio/6_cout_batterie.png)

> 📊 **Comment lire :** À gauche, le prix de la batterie de 5 kWh selon trois devis. À droite, l'argent cumulé
> au fil des ans : on part du prix payé et on ajoute chaque année ce que la batterie fait gagner. Si la ligne
> ne repasse pas au-dessus de zéro avant la fin, la batterie n'est pas remboursée ; c'est le cas ici.

#### 7. Coût des panneaux

![](fig/st_studio/7_cout_panneaux.png)

> 📊 **Comment lire :** Même lecture pour les 3 kWc de panneaux sur 25 ans. Le gain (≈ 181 €/an) est trop faible face au prix des
> panneaux : aucune ligne ne repasse au-dessus de zéro en 25 ans.

### Les 7 graphiques du PowerPoint – PME de Strasbourg

#### 1. Utilisation du solaire

![](fig/st_pme/1_utilisation_solaire.png)

> 📊 **Comment lire :** Ce que deviennent chaque mois les kWh produits par les 100 kWc de la PME :
> consommés directement (orange), stockés (vert foncé) ou revendus (vert clair). Presque tout est consommé
> sur place, car les bureaux consomment en journée.

#### 2. Utilisation de la batterie

![](fig/st_pme/2_utilisation_batterie.png)

> 📊 **Comment lire :** Une semaine de juin. En haut, le niveau de charge de la batterie de 100 kWh ; en bas,
> ses charges (jaune = soleil, bleu = réseau) et décharges (rouge), avec le prix du marché (violet). Elle fait
> environ un cycle par jour, en achetant aux heures creuses et en restituant aux heures chères.

#### 3. Courbe de charge brute

![](fig/st_pme/3_courbe_de_charge_brute.png)

> 📊 **Comment lire :** La consommation de la PME sans équipement : une semaine de juin à gauche (journées de
> bureau, pics de cantine, week-end au minimum) et la journée moyenne de l'année à droite.

#### 4. Ce qu'on achète au réseau

![](fig/st_pme/4_courbe_achetee.png)

> 📊 **Comment lire :** La puissance achetée au réseau sur une semaine de juin, sans équipement (rouge) et avec
> panneaux + batterie (bleu) ; sous zéro (vert), la PME revend. Le pointillé est la puissance prévue au contrat
> (90 kW) : la dépasser coûte une pénalité.

#### 5. Coût de l'énergie

![](fig/st_pme/5_cout_energie.png)

> 📊 **Comment lire :** La facture d'énergie de la PME mois par mois, sans (rouge) et avec équipement (bleu).
> Chaque kWh acheté est compté au prix du marché plus 50 €/MWh d'acheminement et taxes. Le titre donne l'économie
> annuelle, hors pénalités.

#### 6. Coût de la batterie

![](fig/st_pme/6_cout_batterie.png)

> 📊 **Comment lire :** À gauche, le prix de la batterie de 100 kWh selon trois devis ; à droite, l'argent
> cumulé au fil des ans, en partant du prix payé et en ajoutant le gain apporté par la batterie en plus des panneaux.
> Aucune ligne ne repasse au-dessus de zéro en ≈ 15 ans : la batterie n'est pas remboursée.

#### 7. Coût des panneaux

![](fig/st_pme/7_cout_panneaux.png)

> 📊 **Comment lire :** Même lecture pour les 100 kWc de panneaux, sur 25 ans. Les panneaux sont remboursés vers 7 ans au prix bas
> (ligne verte) et vers 16 ans au prix médian (jaune). Au prix haut (rouge), ils ne le sont pas avant la fin de leur vie.

---

## Hôpital et usine à Strasbourg (clients demandés slide 5)

Le PowerPoint cite quatre types de clients : **usine, bureaux, hôpital, particulier**. Les bureaux (PME) et le
particulier (studio) sont traités plus haut ; voici l'hôpital et l'usine, avec la même météo réelle de
Strasbourg 2025 (PV d'après le rayonnement RTE/ODRÉ) et les prix spot réels.

**Courbes de charge :** inventées en bottom-up, comme les autres clients. La même simulation avec les **vraies
courbes Enedis** du secteur est au § « Courbes de charge réelles (open data Enedis) ».

| Client fictif | Composition | Conso / pointe | Équipement simulé |
|---|---|---|---|
| **Hôpital** | socle 24 h/24 150 kW (blocs, imagerie, ventilation), services de jour 7 h–19 h, activité programmée en semaine, cuisine aux repas, groupes froid en cycles, stérilisation 3 h/jour ouvré | 2 371 MWh/an, pointe 500 kW | PV 250 kWc, batterie 250 kWh, puissance souscrite 400 kW |
| **Usine** | veille 60 kW, 2 × 8 (5 h–21 h) du lundi au vendredi 400 kW, maintenance le samedi matin, compresseur en cycles, four électrique 300 kW pendant 3 h/jour ouvré | 2 609 MWh/an, pointe 790 kW | PV 500 kWc, batterie 1 MWh, puissance souscrite 650 kW |

![Hôpital semaine](fig/pro_hopital_semaine.png)

> 📊 **Comment lire :** Consommation simulée de l'hôpital pendant une semaine de juin, usage par usage (couleurs
> empilées). Le socle bleu ne s'arrête jamais (un hôpital fonctionne 24 h/24). En journée s'ajoutent les services,
> l'activité programmée (en semaine seulement), la cuisine aux heures des repas et la stérilisation. À droite,
> la journée moyenne de l'année.

![Usine semaine](fig/pro_usine_semaine.png)

> 📊 **Comment lire :** Consommation simulée de l'usine pendant une semaine de juin. Les blocs orange sont les
> deux équipes de production (5 h–21 h, du lundi au vendredi) ; les pics violets sont le four électrique, qui fait
> dépasser la puissance prévue au contrat ; en vert, la maintenance du samedi matin. Le week-end, il ne reste que la veille.

### Nouveau mode de pilotage : arbitrage + écrêtage des pointes

Avec la règle « prix » seule, la pointe de l'usine (four électrique) n'était **pas du tout écrêtée** : 790 kW
avant comme après, car la batterie avait souvent déjà été vidée pour l'arbitrage. J'ai ajouté le **cumul des
deux usages**, que la fiche de la tâche 3 annonçait comme la clé de la rentabilité :
- dès que la puissance appelée dépasse la puissance souscrite, la batterie décharge **en priorité** ;
- l'arbitrage (acheter bas, restituer haut) ne puise pas dans une **réserve** gardée pour ces pointes (30 % de la capacité utile).

| Test | Ce qu'il vérifie | Résultat |
|---|---|---|
| `test_cumul_prix_et_ecretage_avec_reserve` | pointe de 30 kW écrêtée à 20 kW ; l'arbitrage du soir laisse la réserve intacte | ✅ |

![Stratégies](fig/pro_strategies.png)

> 📊 **Comment lire :** Pour chaque client, ce que la batterie fait gagner par an en plus des panneaux, selon la façon de la
> piloter : « prix seul » (acheter bas, restituer haut), « écrêtage seul » (ne servir qu'à raboter les pointes),
> ou les deux à la fois. Sous chaque montant, le nombre de cycles par an (l'usure). Cumuler les deux usages
> rapporte le plus pour les trois clients ; pour l'usine, à peine plus que « prix seul ».

| Gain annuel de la batterie | Prix seul | Écrêtage seul | **Prix + écrêtage** |
|---|---|---|---|
| PME (100 kWh) | 1 875 € (339 cycles) | 575 € (4 cycles) | **1 994 €** (259 cycles) |
| Hôpital (250 kWh) | 5 066 € (334 cycles) | 3 684 € (36 cycles) | **7 073 €** (258 cycles) |
| Usine (1 MWh) | 18 551 € (326 cycles) | 5 540 € (36 cycles) | **18 744 €** (258 cycles) |

**Interprétation.**
- Pour l'hôpital, **le cumul rapporte 40 % de plus** que l'arbitrage seul.
- Pour l'usine, le cumul ne rapporte presque rien de plus (+ 1 %). Avec la pénalité à l'heure (« Mes choix »),
  l'usine paie 9 571 €/an sans batterie, contre 16 800 € avec mon ancienne règle inventée.
  - L'arbitrage seul raccourcit déjà les dépassements et fait tomber cette pénalité à 5 026 € ;
  - le cumul la supprime presque (43 €), mais perd un peu d'arbitrage à cause de la réserve.
- « Écrêtage seul » use très peu la batterie (36 cycles/an) ; « prix seul » la fait cycler presque chaque jour.
  Le cumul est un compromis : ~260 cycles par an, soit environ 19 ans de cycles, plafonnés à 15 ans d'âge.
- Pour la PME, l'écrêtage seul rapporte peu **en plus des panneaux**, car le PV supprime déjà une partie des pointes de midi.
- Les scénarios hôpital et usine utilisent ce cumul. La PME garde la règle « prix seul » pour que ses chiffres
  plus haut restent valables, mais le cumul lui rapporterait aussi un peu plus (1 994 € au lieu de 1 875 €).

![Monotone usine](fig/pro_usine_monotone.png)

> 📊 **Comment lire :** Les heures de l'année classées de la plus forte à la plus faible puissance achetée par
> l'usine. Le pointillé est la puissance prévue au contrat (650 kW). Sans équipement (rouge), l'usine la dépasse
> environ 770 h/an (le four). Avec la batterie pilotée « prix seul » (bleu), la pointe reste à 790 kW, mais les
> dépassements tombent à environ 400 h ; avec le cumul prix + écrêtage (vert), il n'en reste que quelques heures.

![Batterie usine](fig/pro_usine_batterie_semaine.png)

> 📊 **Comment lire :** La batterie de l'usine pendant une semaine de février. En haut, son niveau de charge ;
> en bas, ses charges depuis le réseau (bleu) aux heures bon marché, et ses décharges (rouge). Les grandes
> barres rouges d'environ 450 kW le matin correspondent au four électrique : la batterie fournit ce qui dépasse
> la puissance prévue au contrat. Les petites décharges du soir sont de l'arbitrage sur les prix hauts.

### Rentabilité

| 2025, Strasbourg | Hôpital | Usine |
|---|---|---|
Avec les valeurs de « Mes choix » : spot + 50 €/MWh d'acheminement et taxes, surplus revendu au spot, pénalité de
12,41 € par heure de dépassement.

| 2025, Strasbourg | Hôpital | Usine |
|---|---|---|
| Production PV / autoconsommation / autoproduction | 269 MWh / 100 % / 11 % | 538 MWh / 94 % / 18 % |
| Coût de l'énergie + acheminement et taxes, sans → avec équipement | 257 823 € → 232 059 € | 298 151 € → 243 501 € |
| Pénalités de dépassement, sans → avec | 14 966 € → 199 € | 9 571 € → 43 € |
| Gain annuel dû au PV / à la batterie | 33 459 € / 7 073 € | 45 434 € / 18 744 € |
| Retour du PV, prix bas / médian / haut (vie 25 ans) | **5 / 10 / 17 ans** | **9 / 13 / 16 ans** |
| Retour de la batterie, prix bas / médian / haut (vie 15 ans) | **11** / 15 / 19 ans | **13** / 17 / 21 ans |

**Interprétation.**
- **Les panneaux sont rentables chez les deux clients, à tous les niveaux de prix.** Presque toute leur production
  est consommée sur place et évite le spot **et** l'acheminement et les taxes.
- **La batterie n'est rentable qu'au prix d'achat bas** : 11 ans pour l'hôpital, 13 ans pour l'usine, pour 15 ans de vie.
  L'hôpital est tout juste à l'équilibre au prix médian (15 ans).
- **Pourquoi l'usine a perdu sa rentabilité.** Avec mon ancienne pénalité inventée (10 €/kW/mois), sa batterie se
  remboursait en 9 à 15 ans. La règle réelle du tarif C4 (12,41 € par heure) coûte moins cher pour des pointes
  courtes et régulières comme celles du four. Le graphique suivant montre l'effet du montant de la pénalité.

![Sensibilité pénalité](fig/pro_sensibilite_penalite.png)

> 📊 **Comment lire :** Nombre d'années pour rembourser la batterie (au prix d'achat médian) selon le montant de la pénalité,
> de 0 à 100 € par heure passée au-dessus de la puissance prévue au contrat. Le trait vertical gris marque la valeur retenue
> (12,41 €/h). Sous le pointillé horizontal (15 ans, la durée de vie), la batterie est rentable. Il faut au moins
> 25 €/h pour l'usine et 50 €/h pour la PME.

| Retour de la batterie (prix médian) selon la pénalité | 0 €/h | 5 | **12,41** | 25 | 50 | 100 |
|---|---|---|---|---|---|---|
| PME | 30 ans | 26 | **21** | 16,5 | 11 | 7 |
| Hôpital | 31 ans | 22 | **15** | 10 | 6 | 3 |
| Usine | 24 ans | 21 | **17** | 13 | 9 | 6 |

**Conclusion pour la question du projet** (« une batterie est-elle rentable chez un client ? ») : sur le
seul arbitrage des prix de 2025, **non**. Chez un client **à fortes pointes de puissance** (usine, hôpital), en
**cumulant** arbitrage et écrêtage, elle est **tout juste rentable** au prix d'achat bas avec la pénalité réelle du tarif C4.
Elle le devient nettement si les pénalités sont plus fortes : c'est le cas des gros clients raccordés en HTA, que je n'ai pas modélisés.
**Le PV, lui, est rentable chez tous les professionnels** dès qu'on compte l'acheminement et les taxes évités.
Il faut maintenant **confirmer la grille tarifaire réelle**, en particulier la formule HTA pour l'hôpital et l'usine.

### Les 7 graphiques du PowerPoint – hôpital

#### 1. Utilisation du solaire

![](fig/pro_hopital/1_utilisation_solaire.png)

> 📊 **Comment lire :** Ce que deviennent chaque mois les kWh produits par les 250 kWc de l'hôpital. Tout est
> consommé directement (orange) : l'hôpital consomme bien plus que ce que les panneaux produisent, même à midi l'été.

#### 2. Utilisation de la batterie

![](fig/pro_hopital/2_utilisation_batterie.png)

> 📊 **Comment lire :** Une semaine de juin pour la batterie de 250 kWh : en haut son niveau de charge, en bas ses
> charges depuis le réseau (bleu) aux heures bon marché et ses décharges (rouge) aux heures chères ou pendant les
> pics de consommation de midi. La ligne violette est le prix du marché.

#### 3. Courbe de charge brute

![](fig/pro_hopital/3_courbe_de_charge_brute.png)

> 📊 **Comment lire :** La consommation de l'hôpital sans équipement : une semaine de juin (à gauche) et la
> journée moyenne de l'année (à droite, avec la plage où se trouvent 80 % des jours). Elle ne descend jamais sous ~150 kW.

#### 4. Ce qu'on achète au réseau

![](fig/pro_hopital/4_courbe_achetee.png)

> 📊 **Comment lire :** La puissance achetée par l'hôpital pendant une semaine de juin, sans équipement (rouge) et
> avec panneaux + batterie (bleu). Le pointillé est la puissance prévue au contrat (400 kW). Les panneaux creusent
> les achats en journée, et la batterie rabote la plupart des pics au-dessus du pointillé. Les creux bleus en fin de
> soirée sont des moments où la batterie restitue son énergie, quand le prix du marché est haut.

#### 5. Coût de l'énergie

![](fig/pro_hopital/5_cout_energie.png)

> 📊 **Comment lire :** La facture d'énergie de l'hôpital mois par mois, sans (rouge) et avec équipement (bleu), acheminement et taxes
> compris (50 €/MWh), hors pénalités. L'écart est plus grand au printemps et en été, grâce aux panneaux.

#### 6. Coût de la batterie

![](fig/pro_hopital/6_cout_batterie.png)

> 📊 **Comment lire :** À gauche, le prix de la batterie de 250 kWh selon trois devis ; à droite, l'argent cumulé
> au fil des années (prix payé, puis gain annuel ajouté). La ligne verte (prix bas) repasse au-dessus de zéro
> vers 11 ans, la jaune (prix médian) tout juste à 15 ans, la fin de sa vie ; la rouge ne le fait pas.

#### 7. Coût des panneaux

![](fig/pro_hopital/7_cout_panneaux.png)

> 📊 **Comment lire :** Même lecture pour les 250 kWc de panneaux, sur 25 ans. Ils sont remboursés vers 5 ans au prix bas, 10 ans au
> prix médian et 17 ans au prix haut, bien avant la fin de leur vie.

### Les 7 graphiques du PowerPoint – usine

#### 1. Utilisation du solaire

![](fig/pro_usine/1_utilisation_solaire.png)

> 📊 **Comment lire :** Ce que deviennent chaque mois les kWh produits par les 500 kWc de l'usine : presque tout
> est consommé directement (orange) ; une petite partie, produite le week-end quand l'usine est à l'arrêt,
> est stockée (vert foncé) ou revendue (vert clair).

#### 2. Utilisation de la batterie

![](fig/pro_usine/2_utilisation_batterie.png)

> 📊 **Comment lire :** Une semaine de juin pour la batterie de 1 MWh : niveau de charge en haut ; en bas,
> charges (jaune = soleil, bleu = réseau) et décharges (rouge), avec le prix du marché (violet). Les grosses
> décharges du matin rabotent la pointe du four ; celles du soir profitent des prix hauts.

#### 3. Courbe de charge brute

![](fig/pro_usine/3_courbe_de_charge_brute.png)

> 📊 **Comment lire :** La consommation de l'usine sans équipement : une semaine de juin (à gauche : deux équipes,
> pics du four, week-end au minimum) et la journée moyenne de l'année (à droite).

#### 4. Ce qu'on achète au réseau

![](fig/pro_usine/4_courbe_achetee.png)

> 📊 **Comment lire :** La puissance achetée par l'usine pendant une semaine de juin, sans équipement (rouge) et
> avec panneaux + batterie (bleu). Le pointillé est la puissance prévue au contrat (650 kW). Avec l'équipement,
> la courbe bleue reste presque toujours sous le pointillé.

#### 5. Coût de l'énergie

![](fig/pro_usine/5_cout_energie.png)

> 📊 **Comment lire :** La facture d'énergie de l'usine mois par mois, sans (rouge) et avec équipement (bleu), acheminement et taxes
> compris (50 €/MWh), hors pénalités. Le titre donne l'économie sur l'année.

#### 6. Coût de la batterie

![](fig/pro_usine/6_cout_batterie.png)

> 📊 **Comment lire :** À gauche, le prix de la batterie de 1 MWh selon trois devis ; à droite, l'argent cumulé
> au fil des années. Seule la ligne verte (prix bas) repasse au-dessus de zéro, vers 13 ans, avant la fin de
> sa vie (15 ans). Aux prix médian et haut, la batterie n'est pas remboursée.

#### 7. Coût des panneaux

![](fig/pro_usine/7_cout_panneaux.png)

> 📊 **Comment lire :** Même lecture pour les 500 kWc de panneaux, sur 25 ans. Les trois lignes repassent au-dessus de zéro, vers 9, 13 et
> 16 ans : les panneaux sont remboursés bien avant la fin de leur vie, à tous les niveaux de prix.

---

## Courbes de charge réelles (open data Enedis)

La slide 5 du PowerPoint demande des courbes de charge **open source** en plus de la simulation bottom-up.
Enedis publie gratuitement, au pas de 30 min, la consommation réelle de **segments de clients**, sur
[opendata.enedis.fr](https://opendata.enedis.fr) (API sans clé, adaptateur `enedis_open`) :

| Client | Segment Enedis utilisé (2025) |
|---|---|
| Studio | particuliers, option base, 3 à 6 kVA, France entière (pas de détail par région sous 36 kVA) |
| PME de bureaux | tertiaire, 36 à 120 kVA, Grand Est |
| Hôpital | tertiaire, 250 à 1 000 kVA, Grand Est (il n'existe pas de catégorie « hôpital ») |
| Usine | industrie, 250 à 1 000 kVA, Grand Est |

**Méthode.**
- Pour chaque demi-heure : énergie consommée par tout le segment ÷ nombre de sites = courbe d'un **site moyen**.
- La courbe est ensuite mise à l'échelle de la consommation annuelle du client : même énergie que la courbe inventée
  (4 300 kWh/an pour le studio, comme dans le PowerPoint).
- On garde donc la **forme réelle** de la consommation, pas son niveau.
- Équipement, prix, choix et pilotage sont identiques aux scénarios `*_strasbourg.yaml` ; seule la consommation change
  (scénarios `*_strasbourg_enedis.yaml`).

| Test | Ce qu'il vérifie | Résultat |
|---|---|---|
| `test_enedis_open_site_moyen_tous_profils_confondus` | (100 000 + 20 000) Wh pour 12 sites en 30 min → 20 kW par site | ✅ |
| `test_enedis_open_vraie_courbe_industrie_grand_est` | vraie API : 96 quarts d'heure sans trou, 365 000 kWh/an → 1 000 kWh sur un jour | ✅ |

![Comparaison journée](fig/reel_comparaison_jour.png)

> 📊 **Comment lire :** Pour chaque client, la consommation d'une journée de semaine moyenne : en rouge la courbe inventée
> appareil par appareil, en bleu la vraie courbe Enedis du même secteur, ramenée à la même consommation sur l'année.
> Les deux ont les mêmes heures d'activité, mais la vraie courbe consomme beaucoup plus la nuit et monte plus doucement.

![Comparaison semaine](fig/reel_comparaison_semaine.png)

> 📊 **Comment lire :** Une semaine de janvier quart d'heure par quart d'heure. La courbe inventée (rouge) est en créneaux
> avec des pics, la vraie courbe (bleu) est lisse, car elle additionne des centaines de sites dont les pics ne tombent pas
> au même moment. La légende donne la pointe de l'année : elle est bien plus basse avec la vraie courbe.

**Ce que les vraies courbes apprennent sur mes profils inventés.**
- **La nuit et le week-end, un vrai site consomme beaucoup plus** que dans mes profils : environ 240 kW la nuit pour
  l'industrie au lieu de 75 kW, et l'activité continue le samedi. Mes profils concentraient trop la consommation en journée.
- **Les pointes sont bien plus basses** (usine 558 kW au lieu de 790 ; PME 69 kW au lieu de 112). C'est en partie un
  artefact : une moyenne de centaines de sites gomme les pointes d'un site réel.

| 2025, Strasbourg (inventée → réelle) | Studio | PME | Hôpital | Usine |
|---|---|---|---|---|
| Pointe annuelle | 4,0 → 1,1 kW | 112 → 69 kW | 500 → 428 kW | 790 → 558 kW |
| Pénalités sans équipement | – | 1 834 → 0 € | 14 966 → 1 378 € | 9 571 → 0 € |
| Autoconsommation du PV | 70 → 78 % | 90 → 94 % | 100 → 100 % | 94 → 98 % |
| Gain annuel dû au PV | 181 → 224 € | 9 381 → 8 186 € | 33 459 → 23 634 € | 45 434 → 43 328 € |
| Gain annuel dû à la batterie | 151 → 125 € | 1 875 → 2 143 € | 7 073 → 3 656 € | 18 744 → 13 723 € |
| Retour du PV, prix bas / médian / haut (25 ans) | 32 / 49 / 73 → 24 / 35 / 49 ans | 7 / 16 / 27 → 8 / 19 / 33 ans | 5 / 10 / 17 → 7 / 16 / 27 ans | 9 / 13 / 16 → 10 / 14 / 17 ans |
| Retour de la batterie, prix bas / médian / haut (≈ 15 ans) | 20 / 31 / 43 → 24 / 38 / 52 ans | 16 / 23 / 29 → 14 / 20 / 26 ans | 11 / 15 / 19 → 21 / 29 / 38 ans | 13 / 17 / 21 → 18 / 24 / 29 ans |

**Interprétation.**
- **Le PV reste rentable chez les trois professionnels**, avec des retours proches. Il dépend surtout de la part du soleil
  consommée sur place, qui est la même, ou meilleure, avec les vraies courbes.
- **La batterie n'est plus rentable nulle part** avec les vraies courbes. Les pointes d'un site moyen étant gommées, il n'y
  a presque plus de pénalités à éviter, et il ne reste que l'arbitrage, qui ne suffit pas.
- **La vérité pour un vrai client est entre les deux.** Un vrai site a des pointes, comme ma courbe inventée, mais aussi
  une consommation de nuit, comme la courbe Enedis. **Seule la vraie courbe d'un client** (son compteur, ou un CSV via
  l'adaptateur générique) permet de trancher pour la batterie.

**Les 7 graphiques du PowerPoint** existent aussi pour chaque client avec la vraie courbe. Ils se lisent comme ceux
plus haut : [studio](fig/reel_studio/), [PME](fig/reel_pme/), [hôpital](fig/reel_hopital/), [usine](fig/reel_usine/).
On les obtient avec `python -m simu run scenarios/usine_strasbourg_enedis.yaml --out results/usine_reel`.

---

## Limites connues (à garder en tête en lisant les chiffres)

1. **Clients inventés** (studio, PME, hôpital, usine ; jours fériés non modélisés).
   - Pénalité de dépassement : règle C4 du TURPE (12,41 €/h), appliquée aussi à l'hôpital et à l'usine, qui relèvent en réalité de la HTA.
   - C'est elle qui décide de la rentabilité des batteries à fortes pointes.
2. **Acheminement et taxes :**
   - comptés seulement dans la simulation de Strasbourg, avec des **ordres de grandeur** (75 / 50 €/MWh) ;
   - pas dans les étapes 1 à 8 (§ 7) ;
   - abonnement et TVA ne sont jamais comptés.
3. Une seule année (2025), répétée sur toute la durée de vie : pas d'actualisation, pas d'inflation, pas de dégradation.
4. PV : profil national, ou rayonnement **régional** (Grand Est) sur surface horizontale : ni inclinaison ni orientation des panneaux.
5. Règles de pilotage simples, non optimales : chronologie des prix ignorée, batterie > 200 kWh mal exploitée en arbitrage seul, réserve d'écrêtage fixée à 30 % sans optimisation.
8. Courbes réelles Enedis = **site moyen** d'un segment (des centaines de sites additionnés) : forme réelle, mais pointes gommées ; pas de catégorie « hôpital » (tertiaire), et pas de maille régionale pour les particuliers.
9. Chauffage : k = 0,5 kWh/°C/jour choisi, pas mesuré ; hôpital et usine supposés chauffés autrement qu'à l'électricité.
6. Coût unitaire pris dans la classe de taille la plus proche (10 / 100 / 1000) : marches d'escalier entre les tailles.
7. Écart de prix du PV : le médian de la fiche pour 100 kWc (120 k€) est au-dessus du « coût moyen 80–100 k€ en toiture simple » cité dans la même fiche.

## Choix à faire valider (voir « Mes choix » en tête du rapport)

- **Pénalités :** règle C4 confirmée par la grille Enedis (12,41 €/h en 2025, 12,79 €/h depuis août 2026). Reste à modéliser la **formule HTA** pour l'hôpital et l'usine. **C'est la donnée qui décide de la rentabilité des batteries** chez les clients à fortes pointes.
- **Acheminement et taxes :** confirmer 75 €/MWh (particulier) et 50 €/MWh (pro) avec la grille officielle.
- **Revente du surplus :** 11 €/MWh pour le particulier (EDF OA), spot pour le pro.
- **Frigo** à 1 fois par heure et **chauffage** k = 0,5 : à confirmer.
- **Courbe de charge d'un vrai client** (CSV, Linky) : les courbes Enedis donnent la forme moyenne d'un secteur, mais pas les pointes d'un site, qui décident de la rentabilité de la batterie.
- Valider l'ajout de `import_surcharge_eur_mwh`, `export_price_eur_mwh`, `grid` (dont `penalty_eur_per_hour`), `strategy` (dont `peak_limit_kw`, `peak_reserve_kwh`, `anticipate_pv`) et des sources `odre_irradiance` / `rte_eco2mix` régional au format YAML.
