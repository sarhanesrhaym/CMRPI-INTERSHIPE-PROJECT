"""
Algorithme de justification — génère l'argumentaire de chaque solution recommandée.

PROPOSITION DE CONCEPTION (aucune specification recue - a valider avec
l'equipe, en particulier la formulation exacte du texte, qui devrait
sans doute etre relue/ajustee pour le rapport de stage final).

Role dans le pipeline :
    ... -> Scoring -> Dependances -> [Allocation par phases] -> Justification -> rapport final

    Volontairement decouple de allocation_phases.py / strategies.py, dont
    l'API est encore en discussion avec l'equipe : ce module ne consomme
    que filtrage.py, exposition.py et scoring.py, deja stables. Il peut
    recevoir un `phase_par_solution` optionnel pour mentionner le
    calendrier des lors que l'Algorithme 4 sera finalise.

Objectif :
    Un plan de solutions sans justification n'est qu'une liste de noms de
    produits. Ce module transforme chaque solution retenue en un texte
    explicatif combinant :
      1. Quel(s) risque(s) elle couvre, et leur niveau d'exposition
         (sortie d'exposition.py : score + classification).
      2. Quel critere du scoring a le plus pese dans son classement
         (le sous-score, pondere, qui contribue le plus au score final -
         "facteur dominant").
      3. Si elle est un prerequis technique amene par une autre solution
         (ajoutee_par_dependance=True, flag pose par dependances.py) plutot
         qu'un choix prioritaire en soi - la justification est alors
         differente : "necessaire pour" plutot que "recommandee pour".
      4. Un avertissement si son cout pese lourd sur le budget
         (faisabilite_budgetaire basse), pour preparer le lecteur au
         verdict budgetaire qui suivra.

HYPOTHESE : le champ `dependances` (ids d'autres solutions requises) est
suppose exister sur les entrees de solutions_db, comme pour dependances.py.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Poids du scoring (doivent rester synchronises avec scoring.py - dupliques
# ici plutot qu'importes pour ne pas coupler ce module a une version precise
# de scoring.py qui est elle-meme encore susceptible d'evoluer, voir
# discussion sur estimations.py / echelle des couts).
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


# ---------------------------------------------------------------------------
# Etape 1 : facteur dominant du scoring
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Etape 2 : description des risques couverts, avec leur exposition
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Etape 3 : dependances (prerequis techniques)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Point d'entree : justification d'UNE solution
# ---------------------------------------------------------------------------

def justifier_solution(
    solution_scoree: Dict[str, Any],
    expositions: List[Dict[str, Any]],
    solutions_db: Dict[str, Any],
    noms_par_id: Dict[str, str],
    phase: Optional[str] = None,
) -> Dict[str, Any]:
    """Construit la justification structuree + le texte d'une solution.

    Args:
        solution_scoree: entree de la sortie de scoring.scorer_solutions_profil()
            (ou de dependances.resoudre_dependances()["ordre_implementation"],
            qui porte en plus `ajoutee_par_dependance` le cas echeant).
        expositions: sortie de exposition.calculer_exposition() pour ce profil.
        solutions_db: data["solutions"] complet (pour les dependances).
        noms_par_id: {solution_id: nom} sur l'ensemble des solutions
            (pas seulement les eligibles - une dependance ajoutee peut
            referencer une solution hors plan).
        phase: libelle de phase optionnel (branchement futur avec
            allocation_phases.py), inclus dans le texte si fourni.

    Returns:
        {
            "solution_id": ..., "nom": ...,
            "risques_couverts_texte": ...,
            "facteur_dominant": {...},
            "texte": "paragraphe complet",
            "avertissement_budget": bool,
        }
    """
    ajoutee_par_dependance = solution_scoree.get("ajoutee_par_dependance", False)
    sous_scores = solution_scoree.get("sous_scores", {})
    risques_texte = _decrire_risques_couverts(solution_scoree.get("risques_couverts", []), expositions)
    dominant = facteur_dominant(sous_scores)
    dependances_texte = _decrire_dependances(solution_scoree["solution_id"], solutions_db, noms_par_id)

    phrases = []

    if ajoutee_par_dependance:
        phrases.append(
            f"{solution_scoree['nom']} n'est pas prioritaire en elle-meme pour votre profil, "
            f"mais elle est indispensable comme prerequis technique d'une autre solution retenue "
            f"dans le plan."
        )
    else:
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

    avertissement_budget = sous_scores.get("faisabilite_budgetaire", 100) < SEUIL_BUDGET_TENDU
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


# ---------------------------------------------------------------------------
# Point d'entree : justification de TOUT le plan d'un profil
# ---------------------------------------------------------------------------

def justifier_plan(
    ordre_implementation: List[Dict[str, Any]],
    expositions: List[Dict[str, Any]],
    solutions_db: Dict[str, Any],
    phase_par_solution: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Genere la justification de chaque solution d'un plan, dans l'ordre
    d'implementation deja etabli par dependances.py.

    Args:
        ordre_implementation: sortie de dependances.resoudre_dependances()["ordre_implementation"]
            (ou directement scoring.scorer_solutions_profil() si les
            dependances n'ont pas encore ete resolues).
        expositions: sortie de exposition.calculer_exposition() pour ce profil.
        solutions_db: data["solutions"] complet.
        phase_par_solution: {solution_id: libelle_phase} optionnel, une
            fois allocation_phases.py disponible.
    """
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
