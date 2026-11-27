# Tâche 4 – Puissance et Énergie

## 1. Énergie et puissance
Energie
Unité SI = J
Unité électricité Wh
1 W = 1J/s -> 1 Wh = 1 W x 3600 s = 3600 J
1 kWh = 1000 Wh = 3,6 x 10^6 J = 3,6 MJ
**La puissance (** $P$ **)** est la vitesse à laquelle cette énergie est produite, transférée ou consommée. C'est un flux par unité de temps :
$P=\frac{dE}{dt}$

**L'analogie hydraulique :** La puissance correspond au **débit** d'un robinet (en litres par seconde), tandis que l'énergie correspond au **volume d'eau** total recueilli dans le seau (en litres). Un robinet à fort débit (forte puissance) ouvert très brièvement peut délivrer moins d'eau (moins d'énergie) qu'un petit filet d'eau qui coule toute la nuit.

## 2. Courbe de charge et calcul discret
Une **courbe de charge** représente l'évolution de la puissance électrique $P(t)$ appelée (consommée) ou injectée (produite) en fonction du temps.
- **Formulation continue :** L'énergie totale consommée ou produite entre deux instants ${t}_{1}$ et ${t}_{2}$ est l'aire sous la courbe de puissance :
$E=\int_{{t}_{1}}^{{t}_{2}} P(t) dt$
- **Formulation discrète (utilisée en simulation et par les compteurs) :** Les données réelles (Linky, RTE, météo) sont relevées par pas de temps fixes $Δt$ (souvent $10$ , $15$ , $30$ ou $60 minutes$ ). En supposant la puissance moyenne constante sur chaque intervalle $i$ :
$E=\sum_{i=1}^{N} {P}_{i}⋅Δt$
Exemple : Pour une journée découpée en pas de $Δt=15 min=0,25 h$ , on additionne $96$ valeurs de puissance ( $24 h×4$ ). Si ${P}_{i}$ est en $kW$ , multiplier chaque valeur par $0,25 h$ donne directement l'énergie en $kWh$ .

## 3. Conservation de l'énergie et conversions électromécaniques
Energie ne se détruit pas elle se tranforme
Energie potentiel
${E}_{p}=m⋅g⋅H [J]$

m : masse en kg
g : accélération => 9.81m/s² sur terre (ou arrondi a 10)
h : Hauteur
${E}_{c}=\frac{1}{2}⋅m⋅{v}^{2} [J]$
m : masse
v : vitesse en m/s
**Exemple concret :** Une voiture de $m=1 500 kg$ qui roule à $v=20 m/s$ ( $72 km/h$ ) possède une énergie cinétique de :
${E}_{c}=\frac{1}{2}×1 500×{20}^{2}=750×400=300 000 J=300 kJ$

$Puissance (P)=\frac{Énergie (E)}{Temps (t)}$

Pour 1 seconde
Pour 1000m3/s a 10m
1m3 = 1000kg
EP = (1000 x 1000) x 10 x 10 = 100 000 000 J
P = 100 000 000 / 1 = 100 000 000 watts
1 kW = 1000 W -> 100 000 kW
1MW = 1 000 000 W -> 100MW
Pour 15m = 0,25h = 900s
E = 1000 x 1000 x 10 x 10 x 900 = 90 000 000 000 J /3600 = 25MWh
E = P x T = 100 MW x 0,25 = 25 MWh

## 4. Ordres de grandeur à retenir (secteur de l'énergie)
- **Solaire PV :** 1 panneau $≈400 Wc$ ( $2{ m}^{2}$ , rendement $≈20%$ ) $⋅$ Toiture maison $≈3 à 9 kWc$ ( $∼1 100 kWh/an$ par $kWc$ en France) $⋅$ Toiture pro / parking $≈100 kWc$ à quelques $MWc$ .
- **Autres productions :** Éolienne terrestre $≈2 à 5 MW$ $⋅$ Réacteur nucléaire $≈900 à 1 650 MW$ .
- **Consommation :** Appartement (hors chauffage élec.) $≈2 000 kWh/an$ ( $∼6 kWh/j$ ) $⋅$ Maison tout électrique $≈12 000 kWh/an$ $⋅$ PME / bureaux $≈50 à 500 MWh/an$ $⋅$ France $≈460 TWh/an$ (puissance de $40 GW$ l'été à $85 GW$ l'hiver).
- **Batteries & Mobilité :** Batterie maison $≈5 à 15 kWh$ $⋅$ Batterie pro/industrie $≈100 kWh$ à quelques $MWh$ (rendement charge/décharge $≈85–90%$ ) $⋅$ Voiture électrique : batterie $≈60 kWh$ , conso $≈17 kWh/100 km$ $⋅$ $1 L$ de carburant $≈10 kWh$ (rendement moteur $≈30%$ ).
- **Prix repères :** Tarif particulier $≈0,20–0,25 €/kWh$ $⋅$ Marché Spot $≈50–100 €/MWh$ en moyenne (peut passer sous $0 €/MWh$ au pic solaire et dépasser $150–250 €/MWh$ le soir).

## 5. Réseau électrique et facturation (pourquoi piloter PV + batterie ?)
Sur le réseau électrique, l'électricité ne se stocke pas : à chaque instant, **production = consommation**. La facture d'un client pro se découpe donc en deux parties :
- **L'énergie consommée (** $€/kWh$ **ou** $€/MWh$ **) :** le volume utilisé, dont le prix sur le marché (Spot) bouge toutes les heures / 15 min selon l'offre et la demande.
- **La puissance souscrite (** $kVA$ **ou** $kW$ **) :** le dimensionnement de raccordement au réseau. Si le site dépasse sa puissance maximale prévue, il paie des **pénalités**.
**L'intérêt de coupler solaire (PV) + batterie :**
- **Autoconsommation :** stocker le surplus solaire de midi pour l'utiliser le soir.
- **Écrêtage de pointe (Peak Shaving) :** vider la batterie pendant les pics d'activité pour éviter de dépasser la puissance souscrite.
- **Arbitrage de prix :** charger la batterie quand le prix de marché est bas et l'utiliser quand le prix explose.

## 6. Ordres de grandeur du point du 23/11 (slide 3), vérifiés
*Complément ajouté le 25/11/2026. Chiffres nationaux : vraie consommation France 2025, RTE éCO2mix (au 1/4 h).*

| Ordre de grandeur du point | Vérification |
|---|---|
| Barrage : 1 000 m³/s qui tombent de 10 m → 100 MW | ✅ Ep = 1 000 000 kg × 10 × 10 = 10⁸ J chaque seconde = 100 MW (§ 3) |
| 10 centrales hydrauliques = 1 centrale nucléaire | ✅ 10 × 100 MW = 1 GW ≈ 1 réacteur (900 à 1 650 MW) |
| 1 éolienne = 1 à 10 MW | ✅ terrestre 2 à 5 MW, en mer jusqu'à ≈ 15 MW |
| Panneaux sur un parking = 0,25 MW ; sur le toit du COM = 2 MW | ✅ à 250 W/m² : ≈ 1 000 m² et ≈ 8 000 m² de panneaux |
| 1 habitant ≈ 0,5 kW en moyenne | ✅ France 2025 : **444 TWh** consommés pour ≈ 68,6 M d'habitants → **0,74 kW par habitant**, industrie et services compris |
| Consommation France (éCO2mix 2025) | moyenne **50,7 GW** ; minimum **30,3 GW** (dimanche 01/06 à 6 h 30) ; maximum **87,7 GW** (mardi 14/01 à 9 h) |
| Studio : 4 300 kWh/an ≈ 10 kWh/jour ≈ 2,5 €/jour | ✅ 4 300 ÷ 365 = 11,8 kWh/jour ; × ≈ 0,21 €/kWh ≈ 2,5 €/jour. Le studio simulé consomme 13,2 kWh/jour avec chauffage, 10,3 sans |
| Voiture électrique : 77 kWh, moteur 200 kW, 15–20 kWh/100 km | ✅ 20 kW à 100 km/h pendant 1 h = 20 kWh pour 100 km ; 10 kW à 50 km/h pendant 2 h = 20 kWh pour 100 km |
| Être humain : 150 W en endurance | ✅ 8 h d'effort = 1,2 kWh, soit ≈ 0,25 € d'électricité |
| 1 L de diesel = 10 kWh ; 6 L/100 km = 60 kWh/100 km | ✅ 3 fois plus que la voiture électrique, à cause du rendement du moteur (≈ 30 %) |

