# Jalon 2 — Moteur de règles

**Projet N°13 — CMRPI, Espace Maroc Cyberconfiance**
Aymane Sarhane & Fatima Zahraa El-Ouali — 1er au 15 août 2026

## Objectif

Implémenter en Python la grille de correspondance du Jalon 1 (22 risques, 21 solutions, 6 questions de profilage), sous forme de règles simples (if/elif), et vérifier que les recommandations produites restent cohérentes sur plusieurs profils.

## Structure du livrable

```
Jalon2_Moteur_Regles/
├── README_Jalon2.md
├── moteur/
│   ├── load_data.py
│   ├── profil.py
│   ├── regles_universelles.py
│   ├── regles_site_web_mobilite.py
│   ├── regles_it_donnees_secteur.py
│   └── moteur.py
├── data/
│   └── (les 5 fichiers JSON du Jalon 1)
└── tests/
    ├── test_profils_exemple.py
    └── test_nouveaux_profils.py
```

## Comment lancer le moteur

Depuis la racine du dossier `Jalon2_Moteur_Regles/` :

```
python moteur/moteur.py
```

Affiche une démonstration sur un profil d'exemple (E-commerce), avec pour chaque recommandation : la priorité, le nom de la mesure, sa justification, les risques couverts, et une éventuelle note d'adaptation (voir section Ajustements).

## Comment lancer les tests

```
python tests/test_profils_exemple.py
python tests/test_nouveaux_profils.py
```

## Répartition des tâches

- **Aymane** : chargement des données (`load_data.py`), règles universelles, règles site web/mobilité
- **Fatima Zahraa** : représentation du profil (`profil.py`), règles IT/données personnelles/secteur, tests sur nouveaux profils
- **En binôme** : assemblage final (`moteur.py`), tests, ajustements

## Résultats des tests

### Test 1 — Les 5 profils d'exemple (`test_profils_exemple.py`)

5/5 profils conformes à la grille du Jalon 1 :

| Profil | Secteur | Recommandations |
|---|---|---|
| exemple001 | Généraliste (profil minimal) | 11 |
| exemple002 | E-commerce | 18 |
| exemple003 | Finance | 19 |
| exemple004 | Santé | 13 |
| exemple005 | Industrie | 22 |

### Test 2 — 7 profils fictifs supplémentaires (`test_nouveaux_profils.py`)

7/7 profils conformes, aucune incohérence détectée. Cette suite de tests a été étendue de 3 à 7 profils afin de couvrir davantage de combinaisons (secteur, mobilité, présence d'une personne IT, données personnelles) et d'intégrer une vérification automatique dédiée à l'ajustement décrit ci-dessous.

## Ajustement effectué (Jour 9)

**Constat.** Les premiers tests ont révélé qu'une PME sans personne dédiée à l'informatique, mais exposée à des risques (secteur Finance/E-commerce ou collecte de données personnelles), ne recevait aucune recommandation sur la gestion des permissions d'accès ou l'externalisation cloud — ces mesures étaient conditionnées à la présence d'une personne IT. Le résultat n'était pas incohérent techniquement, mais insatisfaisant : l'absence de ressource interne ne supprime pas l'exposition au risque.

**Correction apportée.** La règle a été révisée : une PME sans personne IT dédiée, mais exposée par son secteur ou par les données qu'elle traite, reçoit désormais les mêmes recommandations, avec :
- une priorité relevée à Haute (l'exposition demeure, quelle que soit la ressource disponible),
- une note explicite invitant à faire réaliser la mesure par un prestataire informatique ponctuel plutôt qu'en interne.

**Validation.** Le cas ayant motivé cet ajustement (PME Finance sans IT) ainsi qu'un cas apparenté (PME généraliste sans IT, mais avec données personnelles) ont été ajoutés à `test_nouveaux_profils.py` avec une vérification automatique dédiée, en complément de la relecture manuelle des résultats.

## Limite assumée, non corrigée

Les risques de blanchiment via monnaies virtuelles et d'extorsion par déni de service (DDoS) restent sans contre-mesure dédiée dans le guide CMRPI/AUSIM. Ce point, identifié dès le Jalon 1, n'appelle pas de correction côté moteur : aucune recommandation pertinente n'existe dans la base source pour ces cas, et il serait trompeur d'en inventer une.

## Point à valider avec l'encadrante

Confirmer que l'élargissement de priorité (Moyenne → Haute) pour les PME exposées sans IT dédié est bien la lecture souhaitée de la grille du Jalon 1, ou si une autre approche est préférée.
