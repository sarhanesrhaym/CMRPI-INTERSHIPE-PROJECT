
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

from allocation_phases import PHASES_ORDRE, LIBELLES_PHASES
logger = logging.getLogger(__name__)

ORDRE_PRIORITE = {"Critique": 3, "Haute": 2, "Moyenne": 1, "Basse": 0}

SEUILS_PRIORITE_PAR_PLAN = {
    "Minimal": ORDRE_PRIORITE["Critique"],
    "Balanced": ORDRE_PRIORITE["Haute"],
    "Premium": ORDRE_PRIORITE["Basse"],
}

NOMS_PLANS = ["Minimal", "Balanced", "Premium"]

def _index_priorite_solutions(resultat_filtrage: Dict[str, Any]) -> Dict[str, str]:
    """{solution_id: priorite_max} a partir de resultat_filtrage["solutions_eligibles"]
    (deja calcule par filtrage.extraire_solutions_eligibles)."""
    return {
        s["id"]: s.get("priorite_max", "Moyenne")
        for s in resultat_filtrage.get("solutions_eligibles", [])
    }

def _fermeture_dependances(
    ids_retenus: set,
    solutions_db: Dict[str, Any],
) -> set:
    ids_complets = set(ids_retenus)
    a_traiter = list(ids_retenus)

    while a_traiter:
        sol_id = a_traiter.pop()
        for dep_id in solutions_db.get(sol_id, {}).get("dependances", []):
            if dep_id not in ids_complets:
                ids_complets.add(dep_id)
                a_traiter.append(dep_id)

    return ids_complets


def _cout_solution(sol_id: str, solutions_db: Dict[str, Any]) -> float:
    cout = solutions_db.get(sol_id, {}).get("cout_estimation")
    if cout is None:
        logger.warning("Cout inconnu pour la solution '%s' - traite comme 0.", sol_id)
        return 0.0
    return cout


def _verdict_budgetaire(cout_total: float, budget_disponible: Optional[float]) -> Dict[str, Any]:
    if budget_disponible is None or budget_disponible < 0:
        return {
            "statut": "INDETERMINE",
            "message": "Budget disponible non renseigne pour ce profil - faisabilite non evaluable.",
        }

    if cout_total <= budget_disponible:
        marge = budget_disponible - cout_total
        return {
            "statut": "FAISABLE",
            "message": f"Cout total ({cout_total:.0f}) couvert par le budget disponible "
                       f"({budget_disponible:.0f}). Marge restante : {marge:.0f}.",
        }

    depassement = cout_total - budget_disponible
    pourcentage = (depassement / budget_disponible * 100) if budget_disponible > 0 else float("inf")
    return {
        "statut": "DEPASSEMENT",
        "message": f"Depassement de {depassement:.0f} par rapport au budget disponible "
                   f"({budget_disponible:.0f}), soit +{pourcentage:.0f}%.",
    }


def _construire_plan(
    nom_plan: str,
    resultat_phases: Dict[str, Any],
    index_priorite: Dict[str, str],
    solutions_db: Dict[str, Any],
    budget_disponible: Optional[float],
) -> Dict[str, Any]:
    seuil = SEUILS_PRIORITE_PAR_PLAN[nom_plan]

    ids_natifs = set()
    for phase, solutions in resultat_phases["phases"].items():
        for s in solutions:
            sol_id = s["solution_id"]
            priorite = index_priorite.get(sol_id, "Moyenne")
            if ORDRE_PRIORITE.get(priorite, 0) >= seuil:
                ids_natifs.add(sol_id)

    ids_complets = _fermeture_dependances(ids_natifs, solutions_db)
    ids_ajoutes_pour_dependance = ids_complets - ids_natifs

    phases_du_plan: Dict[str, List[Dict[str, Any]]] = {p: [] for p in PHASES_ORDRE}
    cout_total = 0.0
    nb_solutions = 0

    for phase in PHASES_ORDRE:
        for s in resultat_phases["phases"][phase]:
            sol_id = s["solution_id"]
            if sol_id not in ids_complets:
                continue
            cout = _cout_solution(sol_id, solutions_db)
            cout_total += cout
            nb_solutions += 1
            phases_du_plan[phase].append({
                "solution_id": sol_id,
                "nom": s["nom"],
                "cout_estimation": cout,
                "score_final": s.get("score_final"),
                "priorite": index_priorite.get(sol_id, "Moyenne"),
                "requise_par_dependance_uniquement": sol_id in ids_ajoutes_pour_dependance,
            })

    verdict = _verdict_budgetaire(cout_total, budget_disponible)

    return {
        "nom_plan": nom_plan,
        "nb_solutions": nb_solutions,
        "cout_total": round(cout_total, 2),
        "budget_disponible": budget_disponible,
        "verdict_budgetaire": verdict,
        "phases": phases_du_plan,
    }


def generer_strategies(
    resultat_phases: Dict[str, Any],
    resultat_filtrage: Dict[str, Any],
    solutions_db: Dict[str, Any],
    profil: Dict[str, Any],
) -> Dict[str, Any]:
    index_priorite = _index_priorite_solutions(resultat_filtrage)
    budget_disponible = profil.get("budget_disponible")

    return {
        nom_plan: _construire_plan(
            nom_plan, resultat_phases, index_priorite, solutions_db, budget_disponible
        )
        for nom_plan in NOMS_PLANS
    }
if __name__ == "__main__":
    import argparse

    from filtrage import charger_donnees, filtrer_tous_profils
    from exposition import calculer_exposition
    from scoring import scorer_solutions_profil
    from dependances import resoudre_dependances, DependanceCirculaireError
    from allocation_phases import allouer_phases

    parser = argparse.ArgumentParser(description="Algorithme 5 - Generation de 3 strategies")
    parser.add_argument("--dossier", default="data")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING if args.verbose else logging.ERROR,
                         format="[strategies] %(levelname)s: %(message)s")

    data = charger_donnees(args.dossier)
    resultats_filtrage = filtrer_tous_profils(data)

    for profil_id, resultat_filtrage in resultats_filtrage.items():
        profil = data["profils"][profil_id]
        expositions = calculer_exposition(resultat_filtrage["risques_pertinents"], profil)
        scores = scorer_solutions_profil(resultat_filtrage, expositions, profil)

        print(f"\n{'=' * 60}\n{profil['nom']} — budget disponible : {profil.get('budget_disponible')}\n{'=' * 60}")
        try:
            resultat_deps = resoudre_dependances(scores, data["solutions"])
        except DependanceCirculaireError as e:
            print(f"  ERREUR : {e}")
            continue

        resultat_phases = allouer_phases(
            resultat_deps["ordre_implementation"], resultat_filtrage, data["solutions"]
        )
        strategies = generer_strategies(resultat_phases, resultat_filtrage, data["solutions"], profil)

        for nom_plan in NOMS_PLANS:
            plan = strategies[nom_plan]
            v = plan["verdict_budgetaire"]
            print(f"\n--- Plan {nom_plan} ({plan['nb_solutions']} solutions, "
                  f"cout total {plan['cout_total']}) ---")
            print(f"  Verdict : {v['statut']} - {v['message']}")
            for phase in PHASES_ORDRE:
                sols = plan["phases"][phase]
                if not sols:
                    continue
                noms = ", ".join(
                    s["nom"] + (" [dependance]" if s["requise_par_dependance_uniquement"] else "")
                    for s in sols
                )
                print(f"    {LIBELLES_PHASES[phase]} : {noms}")
