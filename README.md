# CMRPI-INTERSHIPE-PROJECT
Système de recommandation IA pour le renforcement de la cyberrésilience des PME
# Base de connaissances — Système de recommandation IA pour la cyber-résilience des PME marocaines

**Projet N°13 — CMRPI, Espace Maroc Cyberconfiance**
**Phase : Semaines 1-2 — Profils PME et conception**
Dernière mise à jour : voir date de génération des fichiers

---

## 1. Vue d'ensemble

Cette base de connaissances constitue le socle du moteur de recommandation IA pour la cyber-résilience des PME marocaines. Elle sera utilisée en Semaines 3-4 pour construire le moteur de recommandation (matching profil PME → risques → solutions priorisées).

| Fichier | Contenu | Nombre d'entrées |
|---|---|---|
| `01_risques.json` | Catalogue des risques de cybersécurité | 95 |
| `02_solutions.json` | Catalogue des solutions/mesures de protection | 119 |
| `03_profils_pme.json` | Profils PME composites représentatifs | 5 |
| `04_matrice_risques_solutions.json` | Correspondance risque → solutions avec efficacité | 95 risques couverts |
| `05_regles_recommandation.json` | Règles de recommandation exploitables par le moteur | 95 |

---

## 2. Sources utilisées

Chaque risque et solution porte un champ `source_guide` traçant sa provenance exacte (chapitre, section ou question précise). Cinq sources ont été mobilisées :

1. **Guide de bonnes pratiques cybersécurité CMRPI/AUSIM** — guide de référence du projet, cité dans la fiche technique officielle.
2. **DGSSI/DNSSI** — Directive Nationale de la Sécurité des Systèmes d'Information (2023) et guides sectoriels associés (référentiel de gestion des incidents, guide sécurité des systèmes industriels). Source officielle marocaine ; cible en priorité les administrations et infrastructures d'importance vitale (IIV), utilisée ici comme référentiel de bonnes pratiques adaptable aux PME.
3. **ANSSI/CPME** — guide français "La cybersécurité pour les TPE/PME en 13 questions". Approche très actionnable, orientée hygiène de base.
4. **Guide DGSSI — Sécurité des systèmes d'information industriels** — pertinent pour le profil PME du secteur Industrie.
5. **Article académique** : *"Management des risques des SI au Maroc : Entre ambition réglementaire et défis culturels — Une analyse critique de l'état des lieux"*, International Journal of Accounting, Finance, Auditing, Management and Economics (IJAFAME), ISSN 2658-8455, Vol. 5, Issue 10 (2024), pp. 317-346. Seule source couvrant les facteurs **culturels et organisationnels** (fatalisme, résistance au changement, maturité par secteur).

---

## 3. Méthodologie et choix assumés

### 3.1 Ce qui est directement issu des sources
- Les risques et solutions techniques/procéduraux sont des **reformulations fidèles** du contenu des guides cités (pas de citation verbatim, pour respecter le droit d'auteur).
- Les 13 risques et 15 solutions "culturels" sont directement dérivés des constats de l'article académique.

### 3.2 Ce qui a été volontairement exclu
- **Aucun coût estimé en MAD** n'a été ajouté aux risques : les sources consultées ne fournissent pas de données chiffrées fiables sur le contexte marocain. Inventer ces chiffres aurait été trompeur.
- **Aucune probabilité numérique (0-1)** n'a été ajoutée : même raison. Seule une échelle qualitative (FAIBLE/MOYENNE/ÉLEVÉE/TRÈS ÉLEVÉE) est utilisée, directement défendable.
- Les solutions ont un champ `cout_estime` qualitatif (Faible/Moyen/Variable) hérité de leur construction initiale — à ne pas confondre avec un chiffrage réel.

### 3.3 Nettoyage des doublons
Le catalogue a été audité et dédoublonné (partant de 93 risques et 106 solutions bruts vers une base propre, avant les derniers ajouts). Les critères de fusion et la liste des suppressions sont documentés dans l'historique de la conversation de conception ; les doublons identifiés étaient soit des reformulations quasi identiques (ex : "absence de journalisation" / "absence de surveillance des logs"), soit des duplications exactes.

### 3.4 Construction de la matrice et des règles (04 et 05)
Vu l'échelle (95 risques × 119 solutions), la correspondance risque → solutions a été construite **par analyse automatique de similarité de contenu** (mots-clés partagés entre descriptions), et non case par case manuellement comme pour le premier lot de 21 risques.

**Implication pratique** : la couverture est complète (0 risque orphelin), mais la précision est hétérogène :
- Les correspondances évidentes (ex : Wi-Fi public → VPN) sont correctement identifiées mais parfois sous-évaluées en efficacité, ou accompagnées de solutions périphériques peu pertinentes.
- Les risques sans vraie solution dans les guides sources (ex : blanchiment via monnaies virtuelles) récupèrent des solutions seulement marginalement liées, honnêtement étiquetées efficacité "Faible".

**Recommandation pour la suite du stage** : traiter cette version comme une base de travail complète et non comme un résultat validé à 100%. Une révision manuelle ciblée est recommandée en priorité sur les risques figurant dans les `risques_principaux` des 5 profils PME (`03_profils_pme.json`), qui sont ceux réellement mobilisés dans les scénarios de démonstration.

---

## 4. Limites et angles morts assumés

| Risque | Limite |
|---|---|
| Blanchiment via monnaies virtuelles | Aucune des sources consultées ne propose de contre-mesure technique dédiée (sujet de conformité AML/KYC, hors périmètre cybersécurité pur) |
| Extorsion DDoS | Partiellement couvert (plan de réponse, mitigation réseau) mais pas de solution "clé en main" pour une petite PME sans budget infrastructure |

---

## 5. ⚠️ Point de synchronisation à traiter

`03_profils_pme.json` (5 profils PME composites, construits à partir de statistiques sectorielles réelles : DGSSI, CGEM, HCP) référence des `risques_principaux` avec les **identifiants d'une version antérieure** de `01_risques.json` (avant les derniers ajouts et renumérotations). Ces références doivent être **revalidées et corrigées** avant toute utilisation dans le moteur de recommandation, sous peine de pointer vers des risques inexistants ou différents.

---

## 6. Structure d'un risque type

```json
{
  "id": "r001",
  "nom": "...",
  "description": "...",
  "severite": "CRITIQUE | ÉLEVÉE | MOYENNE | FAIBLE",
  "probabilite": "TRÈS ÉLEVÉE | ÉLEVÉE | MOYENNE | FAIBLE",
  "secteurs_affectes": ["tous"] ou secteurs spécifiques,
  "facteurs_risque": ["..."],
  "impact_potentiel": "...",
  "notes": "...",
  "source_guide": "Référence précise de la source"
}
```

## 7. Structure d'une règle de recommandation type

```json
{
  "id": "regle_001",
  "nom": "...",
  "categorie": "Technique | Organisationnel | Humain | ...",
  "description": "...",
  "risques_cibles": ["r001"],
  "solutions_associees": ["sol001"],
  "priorite": "Critique | Haute | Moyenne | Basse",
  "delai_mise_en_oeuvre": "...",
  "condition_application": "À quel type de PME cette règle s'applique",
  "phase": "Phase 1 - Urgence | Phase 2 - Structuration | Phase 3 - Maturité avancée",
  "secteurs_prioritaires": ["..."]
}
```

---

## 8. Prochaines étapes (fin S1-2 / début S3-4)

1. Corriger la synchronisation des IDs dans `03_profils_pme.json` (section 5 ci-dessus)
2. Réviser manuellement les règles prioritaires liées aux profils PME
3. Tester la cohérence de bout en bout : profil PME → risques → règles → solutions recommandées, sur les 5 profils
4. Démarrer la conception du moteur de recommandation (Semaine 3-4) : Python/Scikit-learn, logique de scoring et de priorisation par profil
