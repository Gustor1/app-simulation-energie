# Tâche 5 – Sources pour modéliser la courbe de charge de la batterie

## Modèle simple retenu (à utiliser pour la v1)
À chaque pas de temps Δt = 0,25 h :

```
E(t+1) = E(t) + ( η_c · P_charge − P_decharge / η_d ) · Δt
SOC(t) = E(t) / Capacité
```

| Paramètre | Valeur de départ | Remarque |
|---|---|---|
| Capacité | 10 kWh / 100 kWh / 1 MWh | tailles du docx de prix |
| Puissance max charge/décharge | 0,5 C (ex. 50 kW pour 100 kWh) | `P_max = C-rate × capacité` |
| Rendement aller-retour | ≈ 90 % | `η_c = η_d = √0,90 ≈ 0,95` |
| SOC min / max | 10 % / 90 % | protège la batterie |
| Cycles de vie | 3 000 – 7 000 | valeur du docx de prix |

Contraintes : `SOC_min ≤ SOC ≤ SOC_max` ; `0 ≤ P ≤ P_max` ; pas de charge et de décharge simultanées.

**Coût d'usure par kWh déchargé** = `CAPEX / (cycles × capacité × profondeur de décharge)`.
Exemple : 100 kWh à 40 000 €, 5 000 cycles, 80 % → 40 000 / (5 000 × 100 × 0,8) = **0,10 €/kWh**.
→ à comparer au spread : arbitrer n'a de sens que si le spread (en €/kWh) dépasse ce coût + les pertes.

## Outils open source qui contiennent déjà un modèle de batterie
| Outil | Usage | Pour nous |
|---|---|---|
| **SimSES** (Python) | analyse technico-économique de stockage, vieillissement cyclage + calendaire | le plus proche de notre besoin |
| **oemof.solph** (Python) | optimisation linéaire de systèmes énergétiques | utile si on passe à l'optimisation |
| **breos** (Python) | suivi du SOC, modèles de vieillissement Naumann / Lam | léger, bon pour comprendre |
| **PyBaMM** (Python) | physique de la cellule | trop détaillé pour ce projet |

## Pour la suite (hors v1)
Modéliser le vieillissement (perte de capacité avec les cycles, fort SOC, température) : voir la revue arXiv ci-dessous.

## Sources
- [Choosing the Right Battery Model for Data Center Simulations (arXiv 2506.17739)](https://arxiv.org/html/2506.17739v1)
- [Lithium-ion battery degradation: how to model it (arXiv 2112.02037)](https://arxiv.org/pdf/2112.02037)
- [breos.battery – code source et documentation](https://breos.readthedocs.io/en/stable/_modules/breos/battery.html)
- [DLR – vieillissement batterie dans l'optimisation linéaire (oemof)](https://elib.dlr.de/215549/1/Modeling%20battery%20aging%20in%20linear%20energy%20system%20optimizations%20by%20applying%20convex%20hulls%20-accuracy%20benefits%20and%20computational%20cost%20-%20Final%20Print%20Version.pdf)

*Les outils ont été identifiés par recherche, leur documentation n'a pas été vérifiée en détail (gestion du C-rate, rendement). À confirmer avant de s'appuyer dessus.*
