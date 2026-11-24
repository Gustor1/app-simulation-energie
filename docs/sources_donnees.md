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

## Réseau
- Derrière le proxy de l'entreprise, la vérification TLS échoue avec les certificats de Python : le paquet `truststore` (certificats Windows) est utilisé ; la vérification n'est pas désactivée.
- Cache local : `data/cache/` (non versionné). Une période en cours (jour non terminé) reste en cache telle qu'elle a été lue : supprimer le fichier pour la relire.
