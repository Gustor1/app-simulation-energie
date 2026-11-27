# Tâche 1 – Offres « Bloc + Spot » : descriptif et analyse

## Principe
Le client achète **à l'avance, à prix fixe**, une partie de sa consommation (le **bloc**). Le reste (l'écart entre sa conso réelle et le bloc) est réglé au **prix spot** du jour.

- Conso réelle **>** bloc : l'excédent est **acheté au spot**.
- Conso réelle **<** bloc : le surplus de bloc est **revendu au spot**.
- Taille habituelle d'un bloc : 0,5 à 1 MW (certains fournisseurs proposent moins). Durée : mensuelle, trimestrielle ou annuelle.
- Le prix final du mois n'est connu qu'en M+1.

## Formule

```
Coût = Σ [ bloc(t) × prix_bloc  +  (conso(t) − bloc(t)) × spot(t) ] × Δt
```
(le terme spot est négatif quand on revend)

## Exemple chiffré (journée simplifiée, valeurs fictives)

Bloc = 100 kW à 80 €/MWh sur 24 h.

| Période | Durée | Conso | Spot | Énergie conso | Énergie bloc | Écart | Coût spot |
|---|---|---|---|---|---|---|---|
| Nuit 0–6 h | 6 h | 60 kW | 40 €/MWh | 360 kWh | 600 kWh | −240 kWh | −9,6 € (revente) |
| Jour 6–18 h | 12 h | 140 kW | 70 €/MWh | 1680 kWh | 1200 kWh | +480 kWh | +33,6 € |
| Soir 18–24 h | 6 h | 160 kW | 150 €/MWh | 960 kWh | 600 kWh | +360 kWh | +54,0 € |

- Coût du bloc : 2400 kWh × 0,080 = **192 €**
- Coût spot net : −9,6 + 33,6 + 54 = **78 €**
- **Total Bloc + Spot = 270 €** → 90 €/MWh en moyenne

Comparaison sur les mêmes 3000 kWh : spot pur = **276 €** ; prix fixe 80 €/MWh = **240 €**.
Ici le bloc + spot est intermédiaire : il protège en partie des pointes du soir, sans fixer tout le prix.
*(Servira de cas de test pour le code.)*

## Analyse

| Avantages | Limites |
|---|---|
| Budget partiellement sécurisé (le bloc) | Prix final non connu avant M+1 |
| Profite des heures à spot bas ou négatif | Exposé aux pics de spot (soir) |
| Revente de l'excédent de bloc | Demande un suivi quotidien du marché |

**Lien avec la batterie :** la batterie réduit la part de conso achetée au spot cher (décharge le soir) et peut valoriser l'excédent de bloc (charge quand le spot est bas).

## Cas ÉS (Électricité de Strasbourg)
**Pas d'offre « bloc + spot » publique trouvée chez ÉS.** Ce qui est documenté :
- Offre publique pro : **prix fixe**, réservée aux sites **≤ 36 kVA** du territoire de Strasbourg Électricité Réseaux (fourniture + acheminement).
- ÉS propose aussi des **offres indexées** sur le marché (source tierce).
- Les CGV d'ÉS définissent le **prix spot EPEX** : prix d'un bloc de 1 MW livré en France pendant une heure, publié chaque heure par EPEX Spot. C'est la même référence spot que dans notre simulation.
- Gros sites (**HTA, > 250 kVA**) : structuration **sur mesure** selon la courbe de charge et le volume annuel, avec indexation EPEX Spot pour la part marché. *Info d'un comparateur tiers (Selectra), pas d'un document ÉS ; elle mentionne aussi l'ARENH, qui a pris fin en 2025, donc source à prendre avec prudence.*

➡️ Un bloc + spot chez ÉS passerait donc **probablement par un contrat grands comptes négocié**. À confirmer en contactant le service pro d'ÉS ou en demandant à ton tuteur si un contrat ÉS existe déjà.

## Sources
- [ÉS – Offre à prix fixe pro (≤ 36 kVA)](https://entreprises-collectivites.es.fr/sites/default/files/documents/PRO_Offre_a_prix_fixe_0.pdf)
- [ÉS – CGV offre à prix fixe (définition du prix spot EPEX)](https://entreprises-collectivites.es.fr/sites/default/files/documents/Offre-a-prix-fixe-Conditions-Generales-de-Vente_1.pdf)
- [Selectra – ÉS Énergies pour les entreprises](https://entreprises.selectra.info/energie/fournisseurs/es-energies)
- [Opéra Énergie – Électricité de Strasbourg](https://opera-energie.com/electricite-de-strasbourg-es/)
- [Opéra Énergie – Contrat bloc + spot](https://opera-energie.com/contrat-bloc-spot/)
- [Opéra Énergie – Stratégie d'achat flexible](https://opera-energie.com/media/contrat-blocs-spot-strategie-achat-flexible-competitivite/)
- [Ohm Énergie – offre Bloc + Spot (grands comptes)](https://ohm-energie.com/pro/grands-comptes)

*Sources commerciales : pour seuils, frais et règlement des écarts, voir les conditions contractuelles d'un fournisseur.*
