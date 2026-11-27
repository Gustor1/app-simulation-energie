# Tâche 6 – Sources pour simuler la courbe de charge client

Deux approches possibles, à combiner.

## A. Données ouvertes (Enedis, data.gouv.fr)
| Jeu de données | Contenu | Pas | Limite |
|---|---|---|---|
| [Agrégats ≤ 36 kVA – national](https://www.data.gouv.fr/datasets/agregats-segmentes-de-consommation-electrique-au-pas-1-2-h-des-points-de-soutirage-36kva-maille-nationale-1) | conso agrégée par segment (particuliers, petits pros) | 30 min | agrégat, pas un client individuel |
| [Agrégats > 36 kVA – régional](https://www.data.gouv.fr/datasets/agregats-segmentes-de-consommation-electrique-au-pas-1-2-h-des-points-de-soutirage-36kva-maille-regionale) | conso agrégée des sites plus gros | 30 min | idem |
| [Profil ENT1 > 250 kVA (courbes fictives)](https://www.data.gouv.fr/datasets/courbes-de-charge-fictives-experimentales-profil-ent1-plage-250-kva-1) | courbe de charge type d'un gros site | – | fictive / expérimentale |
| [Coefficients des profils](https://www.data.gouv.fr/fr/datasets/coefficients-des-profils/) | profils types (résidentiel, pro…) | – | coefficients, à mettre à l'échelle |
| [Quartier Bastide 2023-2025](https://www.data.gouv.fr/datasets/consommation-et-production-electrique-du-quartier-bastide-2023-2025) | conso + production d'un quartier | 30 min | quartier, pas un site |

À noter : pas trouvé de jeu ouvert de courbes **individuelles** de particuliers. Les données sont au pas de **30 min** → à rééchantillonner à 15 min (répéter la valeur, ou interpoler).

## B. Simulation bottom-up (méthode du tuteur)
Courbe = somme des appareils avec une part d'aléa (heures de démarrage tirées au hasard).

| Appareil | Modèle |
|---|---|
| Réfrigérateur | 400 W, 7 min, 2×/h, 24 h (≈ 1 kWh/jour) |
| TV | 100 W, 18 h → 23 h |
| Lave-vaisselle | 1 kW pendant 2 h |
| Lave-linge | 2 kW pendant 2 h |
| Éclairage | 200 W, 7–9 h et 17–23 h |
| Chauffage | `E = k × (20 − T_moy)` si T < 15 °C |

Contrôle : un studio doit donner ≈ **10 kWh/jour**.

## Recommandation
- **v1 : bottom-up** pour un particulier (aucune dépendance aux données).
- **Ensuite :** un profil Enedis (≤ 36 kVA ou > 36 kVA) normalisé à l'énergie annuelle du client, pour tertiaire / industriel.
- Pour un **vrai client** : ses données Linky / son CSV, via un adaptateur (voir le plan).

*Noms et contenus des jeux de données issus de la recherche : vérifier sur data.gouv.fr / data.enedis.fr qu'ils sont à jour avant usage.*

✅ **Utilisé (25/11/2026)** : les agrégats ≤ 36 kVA (national) et > 36 kVA (régional, par secteur) sont lus via l'API de
`opendata.enedis.fr` (nouvelle adresse de data.enedis.fr), adaptateur `enedis_open`. Voir le rapport, § Courbes réelles.
