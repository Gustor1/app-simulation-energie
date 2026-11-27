# Fiche de conception — utilisation de la batterie (diapo 19)

## Explication simple : que se passe-t-il ?

Imagine que la batterie soit un réservoir d'eau :

- **Le panneau du haut** montre combien le réservoir est rempli.
- **Les barres du bas** montrent ce qui entre ou sort du réservoir à chaque quart d'heure.
- **La ligne violette** montre le prix de l'électricité au même moment.

Quand une barre est au-dessus de zéro, la batterie se **charge**. Quand elle est en dessous, elle se **décharge**. Si le prix est bas, la stratégie peut acheter de l'électricité pour charger; si le prix est haut, elle peut décharger pour éviter d'en acheter. Le soleil peut aussi charger la batterie, même si le prix n'est pas bas.

La lecture d'un exemple se fait donc ainsi :

1. La ligne violette est basse et une barre bleue apparaît : la batterie prend de l'électricité au réseau.
2. Le niveau du panneau du haut monte : l'énergie est maintenant stockée.
3. Plus tard, le prix monte et une barre rouge apparaît : la batterie fournit de l'électricité au site.
4. Le niveau du panneau du haut baisse : l'énergie stockée est utilisée.

Les couleurs veulent dire **d'où vient l'électricité ou dans quel sens elle circule**, pas si le prix est bon ou mauvais : jaune = charge solaire, bleu = charge depuis le réseau, rouge = décharge. La ligne violette est le prix.

### Deux fonctions différentes

Il faut séparer **la décision** du **dessin** :

- `PriceThreshold` décide, à chaque quart d'heure, s'il faut charger ou décharger.
- `Battery.step` vérifie que la batterie peut suivre la consigne : elle ne peut pas dépasser sa puissance ni ses limites de remplissage.
- `plots.battery_use` ne prend aucune décision. Elle dessine les résultats déjà calculés.

Le parcours complet est :

```text
données du scénario
    → stratégie PriceThreshold : demande charge, décharge ou pause
    → Battery.step : applique les limites de la batterie
    → simulate.run : enregistre les résultats de chaque quart d'heure
    → plots.battery_use : transforme ces résultats en graphique
```

Par exemple, la consigne de l'usine limite la puissance à **500 kW**. Si la batterie charge à 500 kW pendant un quart d'heure, elle reçoit 125 kWh côté réseau (`500 kW × 0,25 h`). À cause des pertes, elle stocke un peu moins. Le panneau du haut monte donc, mais la quantité stockée n'est pas simplement égale à la puissance indiquée par la barre.

La règle ne choisit pas seulement « le point le moins cher » et « le point le plus cher ». Elle regarde toute la journée, classe les quarts d'heure par prix, estime combien de temps il faut pour charger puis décharger, et établit un seuil bas et un seuil haut. Elle tient aussi compte du solaire prévu, de la puissance disponible et de la réserve pour les pointes. **La fonction du graphique affiche ensuite ce que la règle a réellement fait.**

## 1. Objet du graphique

Le graphique montre, sur une semaine, **quand la batterie se charge et se décharge**, comment son niveau d'énergie évolue et comment ces actions se situent par rapport au prix spot de l'électricité.

Il s'agit du graphique 2/7 de la diapo 19 : usine fictive de Strasbourg, semaine du **16 au 22 juin 2025**, avec 500 kWc de panneaux et une batterie de 1 000 kWh. La charge positive et la décharge négative sont dessinées dans le panneau inférieur.

## 2. Lecture visuelle

Le graphique comporte deux panneaux partageant le même axe du temps :

| Partie | Données et représentation | Axe vertical |
|---|---|---|
| En haut | Niveau d'énergie de la batterie (`soc`), en courbe en escalier avec une zone remplie turquoise | SOC en % (échelle affichée de 0 à 100 %) |
| En bas | Barres positives pour la charge PV (jaune) et la charge réseau (bleu), barres négatives pour la décharge (rouge) | Puissance batterie en kW ; positif = charge, négatif = décharge |
| Superposé en bas | Prix spot, ligne en escalier violette | Prix spot en €/MWh, axe vertical droit |
| Horizontal | Sept jours, du lundi 16 au dimanche 22 juin | Heure locale Europe/Paris |

Une charge PV et une charge réseau simultanées sont empilées : le bleu commence au-dessus de la barre jaune. La décharge part de zéro vers le bas. La ligne horizontale noire matérialise zéro kW. Chaque pas correspond à 15 minutes.

## 3. Données et paramètres de ce cas

Les paramètres sont ceux de [`scenarios/usine_strasbourg.yaml`](../scenarios/usine_strasbourg.yaml) :

- **Consommation** : profil synthétique bottom-up d'une usine fictive, avec une graine aléatoire fixe (`seed: 23`).
- **Photovoltaïque** : 500 kWc, produit à partir du rayonnement réel RTE/ODRÉ du Grand Est.
- **Prix** : prix spot français 2025 d'Energy-Charts.
- **Batterie** : capacité nominale 1 000 kWh, puissance maximale 500 kW (`0,5 C`), rendement aller-retour 90 %, SOC minimal 10 % et maximal 90 %.
- **Stratégie** : `price_threshold`, avec écrêtage prioritaire au-dessus de 650 kW et une réserve de 240 kWh pour les pointes. La réserve représente 30 % de la capacité utilisable (800 kWh).
- **Prix d'achat** : le premier contrat ajoute un surcoût choisi de 50 €/MWh sur l'énergie soutirée. Ce surcoût est transmis à la stratégie pour juger si l'arbitrage vaut la peine.
- **Période affichée** : `2025-06-16` inclus, pendant 7 jours, soit jusqu'au début du 23 juin en heure locale.

Le SOC minimal est de 10 % (100 kWh). La réserve d'arbitrage de 240 kWh porte donc le plancher normal de décharge à environ **34 % du SOC nominal** : `(100 + 240) / 1 000`. Cela explique le SOC qui reste autour de 35 % sur certaines périodes. Une pointe au-dessus de 650 kW peut toutefois solliciter cette réserve, car l'écrêtage est traité avant l'arbitrage prix.

## 4. Comment les courbes sont produites

### 4.1 Calcul de la simulation

Le point d'entrée est `simu.scenario.run(config)`. Il charge et aligne les séries de consommation, de production PV et de prix au format standard : DataFrame pandas indexé en UTC au pas de 15 minutes.

À chaque pas, `simu.simulate.run(...)` :

1. calcule le bilan net avant batterie : `net_kw = load_kw - pv_kw` ;
2. demande une consigne à la stratégie ;
3. applique cette consigne au modèle de batterie, qui limite charge/décharge par la puissance maximale et par les bornes du SOC ;
4. enregistre les puissances de charge/décharge, l'énergie stockée et le SOC.

La puissance au réseau est ensuite calculée ainsi :

```text
grid_kw = load_kw - pv_kw + bat_charge_kw - bat_discharge_kw
```

Le DataFrame de résultat distingue notamment `pv_to_battery_kw`, `grid_to_battery_kw`, `bat_discharge_kw`, `spot_eur_mwh` et `soc`. Ces colonnes constituent les séries dessinées.

### 4.2 Règle de pilotage par les prix

La logique est dans `simu.strategies.rules.PriceThreshold`, **pas dans la fonction de tracé**. Elle prépare pour chaque journée locale un seuil bas et un seuil haut à partir des prix et des capacités disponibles :

- **Surplus PV** (`load_kw - pv_kw < 0`) : il est stocké en priorité.
- **Prix bas** (`spot <= seuil_bas`) : la batterie peut charger depuis le réseau, dans la limite de sa puissance, de l'espace disponible et de la puissance souscrite.
- **Prix haut** (`spot >= seuil_haut`) : la batterie décharge pour couvrir la consommation, sauf si l'écrêtage d'une pointe passe d'abord.
- **Entre les seuils** : la batterie conserve son énergie.
- **Réserve** : l'arbitrage prix ne décharge pas sous `SOC_min + réserve`. L'écrêtage prioritaire peut utiliser cette réserve.

Les seuils sont calculés en classant les quarts d'heure de la journée par prix, puis en cumulant l'énergie chargeable ou déchargeable jusqu'à la quantité nécessaire. Le seuil bas retient les périodes les moins chères; le seuil haut retient les périodes les plus chères. La quantité à acheter est diminuée du surplus PV prévu dans la journée (`anticipate_pv=True` par défaut).

La stratégie vérifie aussi que l'écart de prix justifie l'arbitrage après rendement et surcoût :

```text
seuil_haut × rendement_aller-retour
    − seuil_bas
    − (1 − rendement_aller-retour) × surcoût
    > marge_minimale
```

Dans le scénario de l'usine, la marge minimale est nulle et le surcoût vaut 50 €/MWh. La stratégie ne revend pas volontairement l'énergie de la batterie (`allow_export=False` par défaut) : elle sert d'abord à réduire les achats réseau. L'écrêtage intervient si la puissance nette dépasse 650 kW.

Le modèle de batterie convertit ensuite la consigne en puissance réellement réalisable. Avec un rendement aller-retour de 90 %, le code utilise un rendement identique en charge et en décharge égal à `sqrt(0,90)`. L'énergie stockée suit :

```text
énergie_fin = énergie_début
              + rendement × puissance_charge × 0,25 h
              − puissance_décharge / rendement × 0,25 h
```

### 4.3 Tracé Matplotlib

La fonction de dessin est `simu.plots.battery_use(r, start, days, title)` :

1. `_window` sélectionne la semaine en convertissant les horodatages UTC en heure locale.
2. Le panneau supérieur trace `soc × 100` en escalier (`steps-post`) et remplit la surface sous la courbe.
3. Le panneau inférieur trace les trois flux de puissance : `pv_to_battery_kw`, `grid_to_battery_kw` et `-bat_discharge_kw`.
4. Si les prix sont disponibles, `twinx()` ajoute un axe droit et trace `spot_eur_mwh` en escalier.
5. `_time_axis` formate l'axe des dates pour une période de sept jours.

### 4.4 Correspondance directe entre le code et le graphique

Dans `plots.py`, `r` est le DataFrame des résultats de la simulation et `w` est sa partie limitée à la semaine affichée. Les lignes du panneau inférieur correspondent à :

| Ce que tu vois | Instruction dans `plots.battery_use` | Colonne des résultats | Couleur |
|---|---|---|---|
| Zone et courbe du haut | `ax1.fill_between(...)` et `ax1.plot(...)` | `w["soc"] * 100` | `C["bat"]` : turquoise |
| Charge solaire | premier `ax2.bar(...)` | `w["pv_to_battery_kw"]` | `C["pv"]` : jaune |
| Charge réseau | deuxième `ax2.bar(...)` | `w["grid_to_battery_kw"]` | `C["grid_after"]` : bleu |
| Décharge | troisième `ax2.bar(...)` | `-w["bat_discharge_kw"]` | `C["grid"]` : rouge |
| Prix spot | `ax3.plot(...)` | `w["spot_eur_mwh"]` | `C["spot"]` : violet |

`C` est simplement le dictionnaire des couleurs défini au début de `plots.py`. Les noms `pv_to_battery_kw`, `grid_to_battery_kw`, `bat_discharge_kw`, `soc` et `spot_eur_mwh` sont les colonnes du DataFrame que `simulate.run` a calculé.

La hauteur de chaque barre est une **puissance en kW pendant ce quart d'heure**. Comme l'intervalle vaut 0,25 h, une barre de charge de 100 kW pendant un pas correspond à 25 kWh prélevés pour charger. Le bleu est dessiné au-dessus du jaune (`bottom=w["pv_to_battery_kw"]`) pour empiler les deux sources de charge. Le signe moins devant `bat_discharge_kw` (`-w["bat_discharge_kw"]`) place les décharges sous la ligne zéro. Ce signe ne transforme pas la donnée de la batterie : il sert à la représentation graphique.

La décision qui fait apparaître une barre bleue ou rouge se trouve ailleurs, dans `PriceThreshold.__call__` de `strategies/rules.py`. En version raccourcie :

```python
if net_kw < 0:
    return -net_kw                    # surplus PV : demande de charge
if net_kw > peak_limit_kw:
    return -(net_kw - peak_limit_kw)   # pointe : décharge prioritaire
if worth[i] and spot <= low[i]:
    return charge_power_allowed       # prix bas : charge réseau, limitée par le réseau
if spot >= high[i]:
    return -min(net_kw, available_kw) # prix haut : décharge, limitée par le SOC
return 0.0                            # sinon : ne rien demander
```

Ce bloc est du pseudo-code pour montrer la logique : dans le vrai code, `charge_power_allowed` est calculé avec `battery.p_max_kw` et la puissance souscrite du réseau; le test de pointe est fait seulement si `peak_limit_kw` est configuré. Ici, `spot` est le prix du quart d'heure courant; `low[i]` et `high[i]` sont les seuils calculés pour le jour; `worth[i]` indique si l'arbitrage est estimé intéressant; `net_kw` vaut consommation moins production PV. Une consigne positive signifie « charger », une consigne négative « décharger », et zéro « ne rien demander ». `Battery.step` borne ensuite la consigne : la puissance de charge ou de décharge réellement affichée peut donc être plus petite, par exemple si la batterie est presque pleine ou presque vide.

En résumé : **`PriceThreshold` choisit l'action; `Battery.step` calcule ce qui est faisable; `simulate.run` met le résultat dans les colonnes; `battery_use` associe ces colonnes aux couleurs et les dessine.**

Appel de génération des graphiques d'un scénario :

```python
plots.save(
    plots.battery_use(res.after, week_start),
    out_dir / "2_utilisation_batterie.png",
)
```

Pour la présentation, `scripts/rapport.py` charge le scénario de l'usine, appelle `scenario.make_plots(...)` avec `week_start="2025-06-16"`, puis enregistre le graphique sous `pro_usine/2_utilisation_batterie.png`. La fonction `battery_use` reçoit donc les **résultats calculés**, et non les données brutes ni la règle elle-même.

## 5. Repères dans le code

| Rôle | Fichier / fonction |
|---|---|
| Paramètres de l'usine et de la batterie | [`scenarios/usine_strasbourg.yaml`](../scenarios/usine_strasbourg.yaml) |
| Chargement du scénario, application de la stratégie, résultats `before` / `after` | [`src/simu/scenario.py`](../src/simu/scenario.py), `run`, `make_plots` |
| Calcul pas à pas et colonnes du DataFrame de sortie | [`src/simu/simulate.py`](../src/simu/simulate.py), `run` |
| Décision de charge/décharge et seuils journaliers | [`src/simu/strategies/rules.py`](../src/simu/strategies/rules.py), `PriceThreshold` |
| Bornes SOC, puissance et rendement | [`src/simu/models/battery.py`](../src/simu/models/battery.py), `Battery.step` |
| Deux panneaux, barres de flux et prix sur axe secondaire | [`src/simu/plots.py`](../src/simu/plots.py), `battery_use` |
| Sélection de la semaine et génération pour l'usine | [`scripts/rapport.py`](../scripts/rapport.py), boucle « Hôpital et usine » |

## 6. Limites d'interprétation

- La ligne du prix et les barres de puissance utilisent **deux échelles verticales différentes** : leur croisement ne signifie pas une égalité de valeur.
- Le graphique illustre la sortie d'une règle de seuil, pas une optimisation globale ni une décision fondée sur le prix seul. Le surplus PV, le SOC, les limites de puissance, le réseau et la réserve influencent aussi le résultat.
- Le profil de consommation de l'usine est inventé; il ne représente pas une mesure client réelle.
- La série est calculée au pas de 15 minutes. Les détails plus rapides que ce pas ne sont pas représentés.
- L'axe du SOC est affiché de 0 à 100 %, même si les consignes normales maintiennent la batterie entre 10 et 90 % et préservent une réserve supplémentaire pour l'arbitrage.
