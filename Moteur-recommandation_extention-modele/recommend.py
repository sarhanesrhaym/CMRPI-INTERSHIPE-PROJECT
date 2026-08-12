from __future__ import annotations
import argparse
import logging
from typing import Any, Dict

from filtrage import charger_donnees, filtrer
from exposition import calculer_exposition
from estimations import enrichir_solutions, enrichir_profils
from scoring import scorer_solutions_profil
from dependances import ordonner_solutions
from allocation_phases import allouer_par_phases
from strategies import generer_strategies, NOMS_PLANS
from justification import justifier_plan

logger = logging.getLogger(__name__)

"""
recommend.py — Pipeline complet du moteur de recommandation

Assemble, dans l'ordre, les 6 algorithmes de l'architecture + les 2 modules
d'assemblage (Stratégies, Justification) :

    profil PME
      -> filtrage.filtrer()                      (Module 1)
      -> exposition.calculer_exposition()         (Algo 1)
      -> scoring.scorer_solutions_profil()        (Algo 2)
      -> dependances.ordonner_solutions()         (Algo 3)
      -> allocation_phases.allouer_par_phases()   (Algo 4)
      -> strategies.generer_strategies()          (Algo 5)
      -> justification.justifier_plan()           (Algo 6)
      -> plan de recommandation complet (JSON)

Ne contient aucune logique métier propre : chaque étape est déléguée au
module correspondant, déjà testé indépendamment et sur les 40 profils
(voir les tests de non-régression). Ce fichier ne fait qu'orchestrer et
enrichir les données une seule fois en amont (estimations.py), pour éviter
de recalculer efficacite/cout_estimation/budget_disponible à chaque appel.

Rappel de transparence (déjà documenté dans chaque module) : les champs
utilisés par le Scoring et l'Allocation (cout_estimation, budget_disponible,
efficacite, roi_estime, complexite...) sont des ESTIMATIONS DE TRAVAIL
produites par estimations.py, pas des données sourcées du guide CMRPI.
"""


def generer_plan_recommandation(profil_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Point d'entrée unique du moteur : profil PME -> plan de recommandation complet.

    Paramètres :
        profil_id : identifiant du profil (ex: "pme001")
        data : dict retourné par charger_donnees(), avec solutions/profils
               DÉJÀ enrichis par estimations.enrichir_solutions/enrichir_profils
               (voir charger_donnees_enrichies() ci-dessous pour le cas
               d'utilisation standard).

    Retourne un dict avec :
        - profil_id, nom_profil
        - risques_pertinents, expositions (Algo 1)
        - solutions_scorees (Algo 2)
        - ordre_implementation, cycle_detecte, prerequis_manquants (Algo 3)
        - allocation_phases (Algo 4)
        - strategies : {"Minimal": {...}, "Balanced": {...}, "Premium": {...}} (Algo 5)
        - justifications (Algo 6)
    """
    profil = data["profils"][profil_id]

    # --- Module 1 : Filtrage ---
    resultat_filtrage = filtrer(profil, data)

    # --- Algo 1 : Exposition ---
    expositions = calculer_exposition(resultat_filtrage["risques_pertinents"], profil)

    # --- Algo 2 : Scoring ---
    solutions_scorees = scorer_solutions_profil(resultat_filtrage, expositions, profil)

    # --- Algo 3 : Dépendances ---
    resultat_deps = ordonner_solutions(solutions_scorees, data["solutions"])
    if resultat_deps["cycle_detecte"]:
        logger.warning(
            "Profil '%s' : cycle de dépendances détecté (%s) — l'ordre produit "
            "n'est pas garanti cohérent pour les solutions impliquées.",
            profil_id, resultat_deps["cycle_detecte"],
        )

    # --- Algo 4 : Allocation par phases ---
    resultat_phases = allouer_par_phases(
        resultat_deps["ordre"], data["solutions"], profil.get("budget_disponible", 0.0)
    )

    # --- Algo 5 : Stratégies (Minimal / Balanced / Premium) ---
    strategies = generer_strategies(resultat_phases, resultat_filtrage, data["solutions"], profil)

    # --- Algo 6 : Justification ---
    justifications = justifier_plan(resultat_deps["ordre"], expositions, data["solutions"])
    justifications_par_id = {j["solution_id"]: j for j in justifications}

    return {
        "profil_id": profil_id,
        "nom_profil": profil.get("nom"),
        "secteur": profil.get("secteur"),
        "budget_disponible": profil.get("budget_disponible"),
        "nb_risques_pertinents": len(resultat_filtrage["risques_pertinents"]),
        "nb_solutions_eligibles": len(resultat_filtrage["solutions_eligibles"]),
        "expositions": expositions,
        "cycle_dependances_detecte": resultat_deps["cycle_detecte"],
        "prerequis_manquants": resultat_deps["prerequis_manquants"],
        "hors_budget": [s["nom"] for s in resultat_phases["hors_budget"]],
        "strategies": strategies,
        "justifications_par_solution": justifications_par_id,
    }


def charger_donnees_enrichies(dossier: str) -> Dict[str, Any]:
    """Charge les 5 fichiers JSON puis enrichit solutions/profils UNE SEULE FOIS
    (estimations.py) — à réutiliser pour tous les profils plutôt que de
    recalculer les estimations à chaque appel de generer_plan_recommandation."""
    data = charger_donnees(dossier)
    data["solutions"] = enrichir_solutions(data["solutions"], data["matrice"])
    data["profils"] = enrichir_profils(data["profils"])
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline complet du moteur de recommandation")
    parser.add_argument("--dossier", default="../data")
    parser.add_argument("--profil", default="pme001")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING if args.verbose else logging.ERROR,
                         format="[recommend] %(levelname)s: %(message)s")

    data = charger_donnees_enrichies(args.dossier)
    plan = generer_plan_recommandation(args.profil, data)

    print(f"\n{'=' * 70}")
    print(f"Plan de recommandation — {plan['nom_profil']} ({plan['secteur']})")
    print(f"Budget disponible (échelle abstraite, pas des MAD) : {plan['budget_disponible']}")
    print(f"{'=' * 70}")
    print(f"Risques pertinents : {plan['nb_risques_pertinents']} | "
          f"Solutions éligibles : {plan['nb_solutions_eligibles']}")

    if plan["cycle_dependances_detecte"]:
        print(f"\n[ATTENTION] Cycle de dépendances détecté : {plan['cycle_dependances_detecte']}")

    print("\n--- Top 3 risques les plus exposants ---")
    for e in plan["expositions"][:3]:
        print(f"  [{e['classification']:10s}] score={e['score_exposition']:.3f}  {e['risque_nom']}")

    for nom_plan in NOMS_PLANS:
        s = plan["strategies"][nom_plan]
        v = s["verdict_budgetaire"]
        print(f"\n--- Stratégie {nom_plan} — {s['nb_solutions']} solution(s), "
              f"coût total {s['cout_total']} ({v['statut']}) ---")
        print(f"  {v['message']}")
        for phase_id, sols in s["phases"].items():
            if not sols:
                continue
            for sol in sols:
                j = plan["justifications_par_solution"].get(sol["solution_id"])
                marque = " [ajoutée par dépendance]" if sol.get("requise_par_dependance_uniquement") else ""
                print(f"    • {sol['nom']}{marque}")
                if j:
                    print(f"        {j['texte']}")

    if plan["hors_budget"]:
        print(f"\n[HORS BUDGET, toutes stratégies confondues] {plan['hors_budget']}")
