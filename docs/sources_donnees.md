# Sources de données – constats des tests (24/11/2026)

## Prix spot – Energy-Charts `price?bzn=FR`
- Licence CC BY 4.0 ; l'API cite « Bundesnetzagentur | SMARD.de ».
- **Pas de 15 min depuis le 01/10/2025** ; horaire avant. L'adaptateur répète la valeur horaire sur 4 quarts d'heure.
- Horodatage UTC (`unix_seconds`) = début du pas. Une requête `start=J&end=J` couvre le jour J en heure de Paris.

## Production solaire – Energy-Charts `public_power?country=fr`
- **Fonctionne** (testé). Filière `Solar`, en MW.
- Pas horaire sur une partie de 2025 (ex. juin et novembre 2025), 15 min en 2026.

## Production solaire – RTE éCO2mix via ODRÉ
- `eco2mix-national-cons-def` : historique consolidé, **jusqu'au 31/08/2026**. Champ `solaire` (MW) renseigné aux demi-heures seulement (vide à :15 et :45) → interpolation linéaire.
- `eco2mix-national-tr` : temps réel, **depuis le 01/09/2026 seulement**.
- Endpoint utilisé : `exports/json` (pas de limite de 100 lignes).

## Puissance solaire installée (dénominateur du facteur de charge)

| Source | Endpoint / jeu | 2024 | 2025 | Pas |
|---|---|---|---|---|
| Energy-Charts | `installed_power?country=fr&time_step=yearly`, filière `Solar AC` (GW) | 22 860 MW | 28 250 MW | annuel (`monthly` → 404) |
| RTE (ODRÉ) | `parc-prod-par-filiere`, champ `parc_solaire` (MW) | 24 496 MW | 30 437 MW | annuel |

- Les deux sources diffèrent d'environ **7 %** en 2025 : chaque adaptateur utilise par défaut la puissance de **sa propre** source (même périmètre que la production).
- **Aucune valeur 2026** publiée : pour 2026, la valeur 2025 est utilisée avec un avertissement → facteur de charge **surestimé** (le parc croît d'environ 5 GW/an, soit ~+20 %).
- La date de référence de la valeur annuelle (fin d'année ? moyenne ?) n'est pas documentée par l'API Energy-Charts ; pour RTE, il s'agit en principe du parc au 31/12. Une puissance peut être imposée (`installed_mw=...`).

## Année 2025 complète (téléchargée le 24/11/2026)
- Productible PV 2025 : **1 069 kWh/kWc** (Energy-Charts) et **1 068 kWh/kWc** (RTE) ; corrélation 0,99 au quart d'heure.
- Trous : Energy-Charts 20 quarts d'heure (25/10 14 h–15 h ; 10/12 16 h–20 h), RTE 2 (nuit du changement d'heure, dernier pas de l'année).
- Spot 2025 : moyenne 61 €/MWh, 509 h à prix négatif, spread journalier médian 92 €/MWh.

## Réseau
- Energy-Charts applique une **limite de débit** (HTTP 429) quand on enchaîne les requêtes : le client
  respecte `Retry-After`, espace les appels d'1 s et reprend grâce au cache.
- Derrière le proxy de l'entreprise, la vérification TLS échoue avec les certificats de Python : le paquet `truststore` (certificats Windows) est utilisé ; la vérification n'est pas désactivée.
- Cache local : `data/cache/` (non versionné). Une période en cours (jour non terminé) reste en cache telle qu'elle a été lue : supprimer le fichier pour la relire.

## Météo régionale Grand Est (RTE / ODRÉ, vérifié le 24/11/2026)
- `rayonnement-solaire-vitesse-vent-tri-horaires-regionaux` : rayonnement global horizontal `ssrd03h` (W/m²), toutes les 3 h depuis 2016, moyennes régionales du modèle CEPMMT (producteur Weathernews, Licence Ouverte). **La valeur horodatée T (UTC) est la moyenne sur [T − 3 h ; T[** (corrélation 0,93 avec la production réelle du Grand Est, même décalage en été et en hiver). Grand Est 2025 : 1 345 kWh/m².
- `temperature-quotidienne-regionale` : `tmin`, `tmax`, `tmoy` (°C) par jour, mise à jour mensuelle. **Le dernier jour de chaque mois est absent** (12 jours en 2025) : interpolé.
- `eco2mix-regional-cons-def` (champ `solaire`, MW) et `parc-regional-annuel-prod-eolien-solaire` (`parc_installe_solaire`, 2 602 MW en 2025 pour le Grand Est) : production réelle 2025 = 1 068 kWh/kWc. **Anomalie : le 30/06/2025, jusqu'à 3 824 MW publiés** (> parc installé).

## Courbes de charge réelles – Enedis open data (vérifié le 25/11/2026)
- API data-fair sans clé : `https://opendata.enedis.fr/data-fair/api/v1/datasets/<jeu>/lines`
  (filtres `<champ>_eq`, tri `sort=horodate`, pages de 10 000 lignes avec curseur `next`).
  L'ancienne adresse `data.enedis.fr` ne répond plus ; data.gouv.fr renvoie vers la nouvelle.
- `conso-sup36-region` : sites > 36 kVA, pas 30 min, par région (`code_region`), secteur (`S1` à `S4`), plage de
  puissance (`P1` à `P7`) ; de juillet 2023 à septembre 2026 au 25/11/2026.
- `conso-inf36` : sites ≤ 36 kVA, maille nationale, par profil (`RES1`… `PRO5`) et plage de puissance.
- Courbe d'un site moyen = `total_energie_soutiree_wh` ÷ `nb_points_soutirage` (sous-profils additionnés).
