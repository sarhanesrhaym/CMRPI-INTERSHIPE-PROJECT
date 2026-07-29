from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

POIDS_EFFICACITE = 0.40
POIDS_FAISABILITE_BUDGETAIRE = 0.25
POIDS_FACILITE_IMPLEMENTATION = 0.15
POIDS_INFRASTRUCTURE = 0.10
POIDS_ROI = 0.10

assert abs(
    POIDS_EFFICACITE + POIDS_FAISABILITE_BUDGETAIRE + POIDS_FACILITE_IMPLEMENTATION
    + POIDS_INFRASTRUCTURE + POIDS_ROI - 1.0
) < 1e-9, "Les poids des criteres doivent sommer a 1.0"

EFFICACITE_INTRINSEQUE_POIDS = 0.6
EFFICACITE_EXPOSITION_POIDS = 0.4

# Malus applique APRES ponderation, selon la complexite declaree de la solution.
MALUS_COMPLEXITE = {
    "faible": 0,
    "moyenne": 5,
    "elevee": 12,
    "tres_elevee": 20,
}

VALEUR_PAR_DEFAUT = 50.0


def _clamp(valeur: float, mini: float = 0.0, maxi: float = 100.0) -> float:
    return max(mini, min(maxi, valeur))

def _risques_couverts_par_solution(
    solution: Dict[str, Any],
    regles_applicables: List[Dict[str, Any]],
) -> List[str]:
    """Retrouve les ids de risques traites par une solution, en remontant
    via ses regles sources (solution['regles_sources'] -> regle['risques_cibles']).
    """
    regles_par_id = {r["id"]: r for r in regles_applicables}
    risques_ids: set[str] = set()
    for regle_id in solution.get("regles_sources", []):
        regle = regles_par_id.get(regle_id)
        if regle is None:
            continue
        risques_ids.update(regle.get("risques_cibles", []))
    return sorted(risques_ids)


def score_efficacite(
    solution: Dict[str, Any],
    risques_couverts: List[str],
    exposition_par_risque: Dict[str, float],
) -> float:
    """Efficacite = melange efficacite intrinseque (0-100) + exposition
    moyenne (0-1 -> remise a l'echelle 0-100) des risques couverts.
    """
    efficacite_intrinseque = solution.get("efficacite")
    if efficacite_intrinseque is None:
        logger.warning(
            "Champ 'efficacite' absent pour la solution '%s' - valeur par defaut utilisee.",
            solution.get("id"),
        )
        efficacite_intrinseque = VALEUR_PAR_DEFAUT

    if risques_couverts:
        # exposition_par_risque est sur l'echelle 0-1 produite par exposition.py
        scores_exposition_0_100 = [
            _clamp(exposition_par_risque.get(rid, VALEUR_PAR_DEFAUT / 100) * 100)
            for rid in risques_couverts
        ]
        exposition_moyenne = sum(scores_exposition_0_100) / len(scores_exposition_0_100)
    else:
        logger.warning(
            "Aucun risque couvert identifie pour la solution '%s' - "
            "exposition moyenne non calculable, valeur par defaut utilisee.",
            solution.get("id"),
        )
        exposition_moyenne = VALEUR_PAR_DEFAUT

    score = (
        EFFICACITE_INTRINSEQUE_POIDS * efficacite_intrinseque
        + EFFICACITE_EXPOSITION_POIDS * exposition_moyenne
    )
    return _clamp(score)
def score_faisabilite_budgetaire(solution: Dict[str, Any], budget_disponible) -> float:
    """100 si le cout est nul ou le budget non contraint, decroit lineairement
    jusqu'a 0 quand le cout atteint le budget disponible, puis reste a 0
    au-dela (solution hors de portee financiere).
    """
    cout = solution.get("cout_estimation")
    if cout is None:
        logger.warning(
            "Champ 'cout_estimation' absent pour la solution '%s' - valeur par defaut utilisee.",
            solution.get("id"),
        )
        return VALEUR_PAR_DEFAUT

    if budget_disponible is None or budget_disponible <= 0:
        logger.warning("Budget disponible non renseigne pour le profil - valeur par defaut utilisee.")
        return VALEUR_PAR_DEFAUT

    if cout <= 0:
        return 100.0

    ratio = cout / budget_disponible
    return _clamp(100.0 * (1 - ratio))

def score_facilite_implementation(solution: Dict[str, Any]) -> float:
    """Lecture directe du champ 0-100 fourni par la base solutions."""
    valeur = solution.get("facilite_implementation")
    if valeur is None:
        logger.warning(
            "Champ 'facilite_implementation' absent pour la solution '%s' - valeur par defaut utilisee.",
            solution.get("id"),
        )
        return VALEUR_PAR_DEFAUT
    return _clamp(valeur)

def score_infrastructure(solution: Dict[str, Any], profil: Dict[str, Any]) -> float:
    """Part des prerequis d'infrastructure de la solution deja couverte par
    l'infrastructure declaree du profil. 100 si aucun prerequis.
    """
    prerequis = solution.get("prerequis_infrastructure", [])
    if not prerequis:
        return 100.0

    outils_profil = [
        o.strip().lower() for o in profil.get("infrastructure_it", {}).get("outils", [])
    ]

    nb_couverts = 0
    for besoin in prerequis:
        besoin_norm = besoin.strip().lower()
        if any(besoin_norm in outil or outil in besoin_norm for outil in outils_profil):
            nb_couverts += 1

    return _clamp(100.0 * nb_couverts / len(prerequis))

def score_roi(solution: Dict[str, Any]) -> float:
    """Lecture directe du champ 0-100 fourni par la base solutions."""
    valeur = solution.get("roi_estime")
    if valeur is None:
        logger.warning(
            "Champ 'roi_estime' absent pour la solution '%s' - valeur par defaut utilisee.",
            solution.get("id"),
        )
        return VALEUR_PAR_DEFAUT
    return _clamp(valeur)
def malus_complexite(solution: Dict[str, Any]) -> float:
    complexite = str(solution.get("complexite", "")).strip().lower()
    if complexite not in MALUS_COMPLEXITE:
        logger.warning(
            "Complexite '%s' inconnue pour la solution '%s' - aucun malus applique.",
            complexite, solution.get("id"),
        )
        return 0.0
    return MALUS_COMPLEXITE[complexite]

def scorer_solution(
    solution: Dict[str, Any],
    profil: Dict[str, Any],
    regles_applicables: List[Dict[str, Any]],
    exposition_par_risque: Dict[str, float],
) -> Dict[str, Any]:
    
    risques_couverts = _risques_couverts_par_solution(solution, regles_applicables)

    sous_scores = {
        "efficacite": score_efficacite(solution, risques_couverts, exposition_par_risque),
        "faisabilite_budgetaire": score_faisabilite_budgetaire(
            solution, profil.get("budget_disponible")
        ),
        "facilite_implementation": score_facilite_implementation(solution),
        "infrastructure": score_infrastructure(solution, profil),
        "roi": score_roi(solution),
    }

    score_pondere = (
        POIDS_EFFICACITE * sous_scores["efficacite"]
        + POIDS_FAISABILITE_BUDGETAIRE * sous_scores["faisabilite_budgetaire"]
        + POIDS_FACILITE_IMPLEMENTATION * sous_scores["facilite_implementation"]
        + POIDS_INFRASTRUCTURE * sous_scores["infrastructure"]
        + POIDS_ROI * sous_scores["roi"]
    )

    malus = malus_complexite(solution)
    score_final = _clamp(score_pondere - malus)

    return {
        "solution_id": solution.get("id"),
        "nom": solution.get("nom"),
        "sous_scores": {k: round(v, 1) for k, v in sous_scores.items()},
        "malus_complexite": malus,
        "score_pondere_avant_malus": round(score_pondere, 1),
        "score_final": round(score_final, 1),
        "risques_couverts": risques_couverts,
    }

def _exposition_par_risque(expositions: List[Dict[str, Any]]) -> Dict[str, float]:
    return {e["risque_id"]: e["score_exposition"] for e in expositions}


def scorer_solutions_profil(
    resultat_filtrage: Dict[str, Any],
    expositions: List[Dict[str, Any]],
    profil: Dict[str, Any],
) -> List[Dict[str, Any]]:
    exposition_par_risque = _exposition_par_risque(expositions)

    resultats = [
        scorer_solution(
            solution,
            profil,
            resultat_filtrage["regles_applicables"],
            exposition_par_risque,
        )
        for solution in resultat_filtrage["solutions_eligibles"]
    ]

    return sorted(resultats, key=lambda r: r["score_final"], reverse=True)


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    from filtrage import charger_donnees, filtrer_tous_profils
    from exposition import calculer_exposition
    from estimations import enrichir_solutions, enrichir_profils

    parser = argparse.ArgumentParser(description="Algorithme 2 - Scoring multi-criteres des solutions")
    parser.add_argument("--dossier", default="data",
                         help="Dossier contenant les 5 fichiers JSON sources")
    parser.add_argument("--sortie", default=None, help="Fichier JSON de sortie du scoring")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING if args.verbose else logging.ERROR,
                         format="[scoring] %(levelname)s: %(message)s")

    data = charger_donnees(args.dossier)

   
    data["solutions"] = enrichir_solutions(data["solutions"], data["matrice"])
    data["profils"] = enrichir_profils(data["profils"])

    resultats_filtrage = filtrer_tous_profils(data)

    tous_les_scores = {}
    for profil_id, resultat_filtrage in resultats_filtrage.items():
        profil = data["profils"][profil_id]
        expositions = calculer_exposition(resultat_filtrage["risques_pertinents"], profil)
        scores = scorer_solutions_profil(resultat_filtrage, expositions, profil)
        tous_les_scores[profil_id] = scores

        print(f"\n=== {profil['nom']} ({profil['secteur']}) ===")
        for s in scores:
            print(f"  {s['score_final']:>5.1f}  {s['nom']}  "
                  f"(eff={s['sous_scores']['efficacite']}, "
                  f"budget={s['sous_scores']['faisabilite_budgetaire']}, "
                  f"malus={s['malus_complexite']})")

    if args.sortie:
        Path(args.sortie).parent.mkdir(parents=True, exist_ok=True)
        with open(args.sortie, "w", encoding="utf-8") as f:
            json.dump(tous_les_scores, f, ensure_ascii=False, indent=2)
        print(f"\nResultats exportes vers {args.sortie}")
