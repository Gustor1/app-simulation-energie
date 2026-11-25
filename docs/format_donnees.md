# Où sont les données, sous quel format, et comment brancher des données de l'entreprise

## 1. En bref

Le simulateur lit **trois sortes d'entrées**, rangées à trois endroits différents.

| Quoi | Où | Format | Qui l'écrit |
|---|---|---|---|
| **Le scénario** : période, client, offres, PV, batterie, pénalités, tous mes choix chiffrés | `scenarios/*.yaml` | YAML (texte) | à la main |
| **Les données publiques** : prix spot, rayonnement, températures, courbes Enedis open data | `data/cache/*.json` | JSON brut des API | automatique, au premier lancement |
| **Les données fournies en fichier** : courbe de charge d'un client, et en option prix ou production PV | `data/…/*.csv` + un fichier `*.mapping.yaml` | CSV + YAML | à la main |

Deux choses ne sont pas dans des fichiers de données :
- **les prix d'achat du PV et des batteries**, écrits dans le code ([src/simu/economics.py](../src/simu/economics.py), tables `PV_PRICES` et `BATTERY_PRICES`, tirées de `taches/2`) ;
- **les clients inventés**, décrits dans le YAML par une liste d'appareils (`site.adapter: bottom_up`) : la courbe est recalculée à chaque lancement, elle n'est stockée nulle part.

Les résultats vont dans le dossier donné par `--out` : `resultats.csv` (toutes les grandeurs au pas de 15 min) et les graphiques PNG.

## 2. Le détail, fichier par fichier

### Scénarios : `scenarios/*.yaml`

Un fichier par cas étudié. C'est le **seul fichier à modifier** pour changer une hypothèse.

| Bloc | Contenu | Exemple |
|---|---|---|
| `period` | dates et fuseau | `{start: 2025-01-01, end: 2025-12-31, timezone: Europe/Paris}` |
| `site` | d'où vient la consommation | `adapter: bottom_up` (appareils inventés), `enedis_open` (courbe moyenne Enedis) ou `csv_generic` (votre fichier) |
| `market.prices` | d'où vient le prix spot | `adapter: energy_charts` (API) ou `csv_generic` |
| `market.offers` | contrats comparés ; **le premier** sert au calcul de rentabilité | `{type: spot, import_surcharge_eur_mwh: 50}`, `{type: fixed, price_eur_mwh: 80}`, `{type: bloc_spot, bloc_kw: 300, bloc_price_eur_mwh: 80}` |
| `pv` | puissance et source du soleil | `{peak_kw: 500, source: odre_irradiance, region: 44, lat: 48.58, lon: 7.75}` |
| `battery` | taille et caractéristiques | `{capacity_kwh: 1000, c_rate: 0.5, round_trip_efficiency: 0.90}` |
| `strategy` | pilotage de la batterie | `{type: price_threshold, peak_limit_kw: 650}` |
| `grid` | puissance souscrite et pénalités | `{subscribed_kw: 650, penalty_eur_per_hour: 12.41}` |

Les chemins de fichiers écrits dans un scénario se lisent **à partir du dossier du scénario**.

### Données publiques : `data/cache/` (111 fichiers, ≈ 28 Mo)

Ce sont des **copies brutes des réponses des API** : un fichier JSON par appel, nommé d'après l'URL et un code de hachage, par exemple `price_….json` ou `lines_….json`.

| Préfixe | Source | Donnée |
|---|---|---|
| `price_` | Energy-Charts (Fraunhofer) | prix spot France |
| `public_power_`, `installed_power_` | Energy-Charts | production solaire nationale |
| `json_` | ODRÉ (RTE) | rayonnement, températures, éCO2mix régional |
| `lines_` | Enedis open data | courbes de charge moyennes par secteur |

- Le dossier n'est **pas versionné** (`.gitignore`). Si on le supprime, tout est retéléchargé au lancement suivant.
- Le simulateur convertit ces JSON lui-même ; on n'a jamais à les ouvrir.
- On ne les remplace pas par des données de l'entreprise : celles-ci passent par un CSV (§ 3).

### Données en fichier : CSV + mapping

L'exemple du dépôt est `data/exemple_bloc_spot.csv`, avec `data/exemple_bloc_spot.mapping.yaml` :

```text
heure;conso_kw;spot_eur_mwh
2026-11-16 00:00;60;40
2026-11-16 01:00;60;40
```

```yaml
sep: ";"
timestamp: {column: heure, timezone: Europe/Paris}
columns:
  load_kw: {column: conso_kw}
  spot_eur_mwh: {column: spot_eur_mwh}
```

Le **mapping** sert à ne jamais retoucher le fichier d'origine. Il dit au simulateur :
- quelle colonne contient l'heure, et dans quel format ;
- quelle colonne contient quoi, et avec quel multiplicateur pour passer dans la bonne unité.

### Format interne (pour info)

Quelle que soit la source, tout est converti en un seul tableau ([src/simu/standard.py](../src/simu/standard.py)) :
- un pas de **15 min** ;
- des heures en **UTC** ;
- chaque valeur est la **moyenne sur le quart d'heure** qui commence à l'heure indiquée.

| Colonne | Unité | Contenu |
|---|---|---|
| `load_kw` | kW | consommation du site |
| `spot_eur_mwh` | €/MWh | prix spot |
| `pv_cf` | kW par kWc (0 à 1) | facteur de charge PV |
| `irradiance_wm2` | W/m² | rayonnement |

Un fichier horaire ou à 30 min est automatiquement réparti sur les quarts d'heure.

## 3. Brancher les données confidentielles de l'entreprise

### Rangement conseillé

```text
data/prive/                           ← ignoré par git : rien ne part sur GitHub
  client_A/
    courbe_2025.csv                   ← le fichier tel qu'exporté (Linky, Enedis, GTB…), non modifié
    courbe_2025.mapping.yaml          ← dit comment lire ce fichier
scenarios/prive/                      ← ignoré par git
  client_A.yaml                       ← copie d'un scénario existant, avec le bloc site remplacé
results/                              ← ignoré par git
```

- `data/prive/`, `scenarios/prive/` et `results/` sont dans `.gitignore`. Mettre ailleurs un fichier confidentiel risquerait de le publier au prochain commit.
- La courbe de charge **reste sur le PC**. Les seuls appels réseau servent à récupérer les prix, le soleil et les températures publics de la période.

### Ce que doit contenir le CSV

| Exigence | Pourquoi |
|---|---|
| Une colonne date-heure et une colonne de consommation | le reste du fichier est ignoré |
| Pas de temps **régulier** : 10, 15, 30 ou 60 min | converti au quart d'heure |
| **Une année complète** de préférence | sinon le gain est extrapolé à l'année (× 365 / nombre de jours), ce qui ignore les saisons |
| Une **puissance moyenne** (W ou kW) | voir le piège des kWh ci-dessous |
| Pas de trous, ou des trous courts | voir « Trous » ci-dessous |

**Piège n° 1 : les unités**

Le simulateur attend une **puissance en kW**. On règle `factor` dans le mapping :

| Le fichier donne… | `factor` |
|---|---|
| des kW | `1` (ou rien) |
| des W (cas des exports Enedis « courbe de charge ») | `0.001` |
| des **kWh par pas de 30 min** | `2` (kWh ÷ 0,5 h = kW) |
| des kWh par pas de 15 min | `4` |
| des kWh par pas de 10 min | `6` |
| des kWh par heure | `1` |
| des Wh par pas de 30 min | `0.002` |

Un index de compteur cumulé (valeur qui ne fait que monter) n'est **pas** pris en charge : il faut d'abord calculer les différences.

**Piège n° 2 : l'heure**

| Réglage du mapping | À quoi il sert |
|---|---|
| `timezone: Europe/Paris` | quand les heures du fichier sont des heures légales françaises (cas courant) ; le changement d'heure est géré |
| `label: end` | quand l'heure indique la **fin** du pas (« 00:30 » = consommation de 00:00 à 00:30). C'est le cas des exports Enedis. Par défaut, `start` |
| `format: "%d/%m/%Y %H:%M"` | pour une date à la française (31/12/2025 23:30) |
| `sep: ";"`, `decimal: ","` | pour un CSV ouvert et réenregistré avec Excel en français |

**Trous** (relevés manquants)

Par défaut, un trou **arrête** la simulation, avec un message qui dit où il est. Le simulateur ne comble jamais rien sans qu'on le lui demande.

Pour combler automatiquement les petits trous (interpolation linéaire), ajouter `max_gap_hours: 2` dans le bloc `site`. Les trous plus longs restent une erreur.

### Exemple complet : export Enedis d'un client

Le fichier tel que téléchargé, `data/prive/client_A/courbe_2025.csv` :

```text
Horodate;Valeur
01/01/2025 00:30;41250
01/01/2025 01:00;40980
...
```

Le mapping, `data/prive/client_A/courbe_2025.mapping.yaml` :

```yaml
sep: ";"
timestamp:
  column: Horodate
  format: "%d/%m/%Y %H:%M"
  timezone: Europe/Paris
  label: end          # Enedis : l'heure est la fin du pas de 30 min
columns:
  load_kw: {column: Valeur, factor: 0.001}   # W -> kW
```

Le scénario, `scenarios/prive/client_A.yaml` : on copie par exemple `scenarios/usine_strasbourg.yaml` et on ne remplace que le bloc `site`.

```yaml
period: {start: 2025-01-01, end: 2025-12-31, timezone: Europe/Paris}
site:
  adapter: csv_generic
  load: ../../data/prive/client_A/courbe_2025.csv
  mapping: ../../data/prive/client_A/courbe_2025.mapping.yaml
  max_gap_hours: 2          # optionnel
market: ...                 # inchangé, ou les prix du vrai contrat du client
pv: ...                     # taille étudiée
battery: ...
grid: {subscribed_kw: 250, penalty_eur_per_hour: 12.41}   # la vraie puissance souscrite du client
```

Pour lancer la simulation :

```text
python -m simu run scenarios/prive/client_A.yaml --out results/client_A
```

Le format CSV + mapping a été vérifié le 25/11/2026 sur un faux export de ce type (30 min, W, heure de fin, un trou de 2 h) :
- sans `max_gap_hours`, on obtient l'erreur claire attendue ;
- avec `max_gap_hours: 2`, la simulation tourne jusqu'au bout.

### Les autres valeurs à remplacer par celles du client

Elles se trouvent toutes dans le scénario YAML, pas dans un CSV :

| Valeur | Champ |
|---|---|
| puissance souscrite | `grid.subscribed_kw` |
| pénalité | `grid.penalty_eur_per_hour` ou `penalty_eur_per_kw` |
| prix du contrat | `market.offers` : `price_eur_mwh`, `bloc_kw`, `bloc_price_eur_mwh` |
| acheminement + taxes, d'après une vraie facture | `import_surcharge_eur_mwh` |
| prix de revente | `export_price_eur_mwh` |

Pour utiliser les prix de l'entreprise plutôt que le spot public : `market.prices: {adapter: csv_generic, path: ..., mapping: ...}`, avec une colonne `spot_eur_mwh`.

Pour utiliser une production PV mesurée : `pv: {source: csv_generic, path: ..., mapping: ..., peak_kw: ...}`, avec une colonne `pv_cf` (kW produits ÷ kWc installés) ou `irradiance_wm2`.

Les prix d'achat des équipements (devis réels) se changent dans [src/simu/economics.py](../src/simu/economics.py).
