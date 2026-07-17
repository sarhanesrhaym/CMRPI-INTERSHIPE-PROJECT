# J1 — Note de décision : données estimées pour le moteur

**Auteurs :** Aymane & Fatima Zahraa
**Statut :** Estimations de travail, à valider par l'encadrant — ne pas présenter comme des données sourcées.

## 1. Constat

La base S1-2 (95 risques, 119 solutions, 40 profils) ne contient **aucune donnée chiffrée** (probabilité 0-1, coût MAD, budget cyber annuel), par choix assumé documenté dans le README (pas de chiffres inventés sans source). Les 6 algorithmes du moteur ont besoin de nombres. On distingue donc :

- **Donnée sourcée** (ex : `severite: "ÉLEVÉE"`) → vient du guide/article, qualitative.
- **Donnée estimée** (ex : `poids_severite: 3`) → construite par nous pour faire tourner l'algorithme, marquée `estimation: true`, jamais présentée comme un fait du guide.

Aucun fichier source (`01_risques.json`, etc.) n'est modifié : les estimations vivent dans des fichiers séparés sous `data/` (`grille_estimation.json`) et sont calculées à la volée par le code, jamais fusionnées silencieusement dans les fichiers d'origine.

## 2. Grille de conversion qualitatif → numérique

### 2.1 Sévérité et probabilité (utilisées par Exposition — Aymane, J2)

| Sévérité | Poids | Probabilité | Poids |
|---|---|---|---|
| FAIBLE | 1 | FAIBLE | 1 |
| MOYENNE | 2 | FAIBLE-MOYENNE | 1.5 |
| ÉLEVÉE | 3 | MOYENNE | 2 |
| CRITIQUE | 4 | ÉLEVÉE | 3 |
| — | — | TRÈS ÉLEVÉE | 4 |

### 2.2 Facteur d'impact PME (utilisé par Exposition — Aymane, J2)

`facteur_impact_pme = clip(mod_maturite × mod_taille × mod_donnees_sensibles, 0.7, 1.6)`

**mod_maturite_it** (moins mature = plus vulnérable à risque égal) :
Très Faible = 1.3 · Faible = 1.2 · Faible à Moyenne = 1.15 · Moyenne = 1.0 · Moyenne à Bonne = 0.9 · Bonne = 0.8 · Bonne (IT)/Moyenne (OT) = 0.95 (hypothèse : le volet OT moins mature tire le facteur au-dessus de la moyenne malgré un bon IT)

**mod_taille** (hypothèse : une structure plus petite encaisse moins bien un incident donné — impact relatif plus fort, pas la probabilité) :
< 15 employés = 1.15 · 15-50 = 1.05 · 50-100 = 1.0 · > 100 = 0.90

**mod_donnees_sensibles** : 1.15 si `donnees_traitees` ou `compliance` contient un mot-clé sensible (santé, bancaire, personnelles, mineurs, carte, RIB, KYC), sinon 1.0

⚠️ Ces trois modificateurs et leurs bornes sont une hypothèse de travail, pas un résultat validé — à challenger avec l'encadrant, notamment le sens de `mod_taille` (on pourrait défendre l'inverse : plus grand = plus de surface d'attaque).

### 2.3 Efficacité des solutions (utilisée par Scoring — Aymane, J3)

Élevée = 0.85 · Moyenne = 0.55 · Faible = 0.25 (milieux d'intervalle, à défaut de valeur exacte dans la matrice)

### 2.4 Budget cyber annuel par profil (nécessaire pour Scoring/Allocation — J3/J4)

Non traité au J1 : `budget_cyber_dedie` n'est qu'un booléen dans les profils. **Décision reportée au J3**, avec Fatima Zahraa, au moment d'implémenter la faisabilité budgétaire — proposition à ce moment-là : estimer un budget annuel par tranche d'effectif × secteur (ex : % du CA estimé), clairement marqué `estimation: true`.

## 3. Ce qui reste sourcé, non estimé

`severite`, `probabilite` (qualitatifs), `efficacite` (qualitatif dans la matrice), `source_guide`, tous les textes descriptifs. Rien n'est réécrit dans les fichiers `01`-`05` d'origine.
