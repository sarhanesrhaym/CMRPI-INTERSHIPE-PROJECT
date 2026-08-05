
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
POIDS_CRITERES = {
    "efficacite": 0.40,
    "faisabilite_budgetaire": 0.25,
    "facilite_implementation": 0.15,
    "infrastructure": 0.10,
    "roi": 0.10,
}

LIBELLES_CRITERES = {
    "efficacite": "son efficacite contre les risques cibles, combinee au niveau d'exposition de votre profil",
    "faisabilite_budgetaire": "son faible cout au regard de votre budget disponible",
    "facilite_implementation": "sa facilite de mise en oeuvre",
    "infrastructure": "sa compatibilite avec votre infrastructure existante",
    "roi": "son retour sur investissement estime",
}

SEUIL_BUDGET_TENDU = 40.0  # faisabilite_budgetaire en dessous de ce seuil -> avertissement

def facteur_dominant(sous_scores: Dict[str, float]) -> Dict[str, Any]:
    """Identifie, parmi les 5 sous-scores, celui qui contribue le plus au
    score final une fois pondere (poids * sous_score) - c'est l'argument
    principal a mettre en avant dans la justification.
    """
    if not sous_scores:
        return {"critere": None, "valeur": None, "contribution": 0.0}

    contributions = {
        critere: POIDS_CRITERES.get(critere, 0) * valeur
        for critere, valeur in sous_scores.items()
    }
    critere_dominant = max(contributions, key=contributions.get)

    return {
        "critere": critere_dominant,
        "valeur": sous_scores[critere_dominant],
        "contribution": round(contributions[critere_dominant], 1),
    }

def _decrire_risques_couverts(
    risques_couverts: List[str],
    expositions: List[Dict[str, Any]],
) -> str:
    expo_par_risque = {e["risque_id"]: e for e in expositions}

    descriptions = []
    for rid in risques_couverts:
        expo = expo_par_risque.get(rid)
        if expo is None:
            logger.warning("Risque '%s' couvert par une solution mais absent des expositions fournies.", rid)
            continue
        descriptions.append(
            f"{expo['risque_nom']} (exposition {expo['classification'].lower()}, "
            f"score {expo['score_exposition']:.2f})"
        )
    if not descriptions:
        return "un ou plusieurs risques identifies pour votre profil"

    if len(descriptions) == 1:
        return descriptions[0]

    return ", ".join(descriptions[:-1]) + " et " + descriptions[-1]

def _decrire_dependances(
    solution_id: str,
    solutions_db: Dict[str, Any],
    noms_par_id: Dict[str, str],
) -> Optional[str]:
    dependances_ids = solutions_db.get(solution_id, {}).get("dependances", [])
    if not dependances_ids:
        return None
    noms = [noms_par_id.get(did, did) for did in dependances_ids]
    if len(noms) == 1:
        return f"Sa mise en oeuvre suppose au prealable : {noms[0]}."
    return "Sa mise en oeuvre suppose au prealable : " + ", ".join(noms[:-1]) + f" et {noms[-1]}."

def justifier_solution(
    solution_scoree: Dict[str, Any],
    expositions: List[Dict[str, Any]],
    solutions_db: Dict[str, Any],
    noms_par_id: Dict[str, str],
    phase: Optional[str] = None,
) -> Dict[str, Any]:
   
 
    ajoutee_par_dependance = solution_scoree.get("ajoutee_par_dependance", False)
    sous_scores = solution_scoree.get("sous_scores", {})
    risques_texte = _decrire_risques_couverts(solution_scoree.get("risques_couverts", []), expositions)
    dominant = facteur_dominant(sous_scores)
    dependances_texte = _decrire_dependances(solution_scoree["solution_id"], solutions_db, noms_par_id)

    phrases = []

    # Justification principale
    phrases.append(
        f"{solution_scoree['nom']} est recommandee pour traiter : {risques_texte}."
    )
    if dominant["critere"] is not None:
        phrases.append(
            f"Elle obtient un score de pertinence de {solution_scoree.get('score_final', '?')}/100 "
            f"pour votre profil, tire principalement par {LIBELLES_CRITERES.get(dominant['critere'], dominant['critere'])} "
            f"({dominant['valeur']}/100)."
        )

    if dependances_texte:
        phrases.append(dependances_texte)

    if avertissement_budget:
        phrases.append(
            "Attention : le cout de cette solution represente une part importante du budget disponible."
        )

    if phase:
        phrases.append(f"Mise en oeuvre prevue : {phase}.")

    return {
        "solution_id": solution_scoree["solution_id"],
        "nom": solution_scoree.get("nom"),
        "risques_couverts_texte": risques_texte,
        "facteur_dominant": dominant,
        "ajoutee_par_dependance": ajoutee_par_dependance,
        "avertissement_budget": avertissement_budget,
        "texte": " ".join(phrases),
    }


def justifier_plan(
    ordre_implementation: List[Dict[str, Any]],
    expositions: List[Dict[str, Any]],
    solutions_db: Dict[str, Any],
    phase_par_solution: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
  
    noms_par_id = {sid: s.get("nom", sid) for sid, s in solutions_db.items()}
    phase_par_solution = phase_par_solution or {}

    return [
        justifier_solution(
            solution, expositions, solutions_db, noms_par_id,
            phase=phase_par_solution.get(solution["solution_id"]),
        )
        for solution in ordre_implementation
    ]


if __name__ == "__main__":
    import argparse

    from filtrage import charger_donnees, filtrer_tous_profils
    from exposition import calculer_exposition
    from scoring import scorer_solutions_profil
    from dependances import resoudre_dependances, DependanceCirculaireError

    parser = argparse.ArgumentParser(description="Algorithme de justification")
    parser.add_argument("--dossier", default="data")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING if args.verbose else logging.ERROR,
                         format="[justification] %(levelname)s: %(message)s")

    data = charger_donnees(args.dossier)
    resultats_filtrage = filtrer_tous_profils(data)

    for profil_id, resultat_filtrage in resultats_filtrage.items():
        profil = data["profils"][profil_id]
        expositions = calculer_exposition(resultat_filtrage["risques_pertinents"], profil)
        scores = scorer_solutions_profil(resultat_filtrage, expositions, profil)

        print(f"\n{'=' * 70}\n{profil['nom']}\n{'=' * 70}")
        try:
            resultat_deps = resoudre_dependances(scores, data["solutions"])
        except DependanceCirculaireError as e:
            print(f"  ERREUR : {e}")
            continue

        justifications = justifier_plan(
            resultat_deps["ordre_implementation"], expositions, data["solutions"]
        )
        for j in justifications:
            print(f"\n>> {j['nom']}")
            print(f"   {j['texte']}")
