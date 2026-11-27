# Tâche 3 – Spread intraday + intérêt du couplage batterie / PV / autoconsommation

## 1. Le spread
**Spread** = écart entre le prix spot le plus bas et le plus haut d'une même journée. C'est ce que la batterie « achète à bas prix, revend à prix haut » (arbitrage).

### Chiffres France 2025 (sources ci-dessous)
| Indicateur | 2024 | 2025 |
|---|---|---|
| Prix spot moyen annuel | 58 €/MWh | 61 €/MWh |
| Écart moyen min-max horaire (Hellowatt) | 76 €/MWh | 90 €/MWh |
| Heures à prix négatif | 352 h | 513 h |
| Heures ≥ 100 €/MWh | – | 1 807 h |

- Depuis **octobre 2025**, le marché spot France est au **pas de 15 min** (cohérent avec notre simulation).
- Plus de solaire à midi → prix bas voire négatifs l'après-midi, pointes le soir.

> ⚠️ La fourchette « 80–180 €/MWh » du docx n'est **pas confirmée** telle quelle : la seule moyenne trouvée est ≈ **90 €/MWh** (source secondaire). À recalculer sur de vraies données.
>
> ✅ **Recalculé (25/11/2026)** sur les vrais prix spot 2025 (Energy-Charts) : spread médian **92 €/MWh**, moyen 95 €/MWh ;
> **64 %** des jours entre 80 et 180 €/MWh, 35 % en dessous. Détails et graphiques : `docs/rapport/RAPPORT.md` (étape 0) ;
> résumé dans le cahier des charges (tâche 7).

### À faire pour valider (action concrète)
1. Télécharger les prix spot 2025 (Energy-Charts ou RTE).
2. Par jour : `spread = max(prix) − min(prix)`.
3. Tracer l'histogramme et la moyenne mensuelle.

## 2. Pourquoi coupler batterie + PV + autoconsommation ?
Trois usages possibles, qui s'additionnent :
1. **Autoconsommation** : stocker le surplus solaire de midi pour le soir.
2. **Arbitrage** : charger quand le spot est bas, décharger quand il est haut.
3. **Peak shaving** : écrêter les pointes pour éviter les pénalités de dépassement de puissance souscrite.

### Ce que disent les études (résumés lus, pas les textes complets)
- Le **peak shaving** est en général la principale source de revenus.
- Pris **séparément**, autoconsommation et arbitrage sont souvent peu rentables ; **cumulés**, ils peuvent le devenir selon le profil du site.
- L'arbitrage était jugé marginal dans les études **anciennes** (spreads plus faibles) ; les spreads 2025 sont plus élevés.
- Résultats très **dépendants du profil de charge** du client → d'où l'intérêt du simulateur.

➡️ **Conséquence pour le projet :** la simulation doit inclure le **peak shaving**, pas seulement l'arbitrage.

## Sources
- [RTE – Bilan 2025, prix](https://analysesetdonnees.rte-france.com/en/annual-review-2025/prices)
- [Hellowatt – Observatoire prix électricité 2026](https://www.hellowatt.fr/blog/observatoire-prix-electricite-2026/)
- [Modo Energy – Batteries en France (sept. 2025)](https://modoenergy.com/research/fr/france-battery-energy-storage-solar-nuclear-grid-ancillary-revenue-september-2025)
- [CRE – Note PV et stockage (2026)](https://www.cre.fr/fileadmin/Documents/Rapports_et_etudes/2026/260305_Note_PV_Stockage.pdf)
- [Applied Energy 2019 – rentabilité batterie industrielle (peak shaving, autoconsommation, arbitrage)](https://econpapers.repec.org/RePEc:eee:appene:v:239:y:2019:i:c:p:1424-1440)
- [Applied Energy 2025 – simulation de 50 PME](https://ideas.repec.org/a/eee/appene/v383y2025ics0306261925000832.html)
- [MDPI Energies – stockage et pointe industrielle](https://www.mdpi.com/1996-1073/15/16/5859)
