from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

"""
allocation_phases.py — Algorithme 4 : Allocation par phases
================================================================

Rôle dans le pipeline :
    Prend la sortie de dependances.ordonner_solutions() (déjà triée en
    respectant les prérequis internes + le score_final) et répartit les
    solutions dans 4 phases budgétaires :
        Phase 0 : solutions gratuites/à très faible coût — toujours
                  faisables immédiatement, indépendamment du budget.
        Phase 1 : 40% du budget disponible
        Phase 2 : 40% du budget disponible
        Phase 3 : 20% du budget disponible restant

    Une solution ne peut jamais être placée dans une phase antérieure à
    celle de son prérequis interne (cohérence avec l'ordre de
    dependances.py) — même si elle est gratuite, elle attend son
    prérequis payant si besoin.

    Si aucune phase ne peut absorber le coût restant d'une solution,
    elle est placée dans "hors_budget" et SIGNALÉE, jamais supprimée
    silencieusement (cas limite prévu au J7 : budget insuffisant).

IMPORTANT — budget_disponible et cout_estimation viennent de
estimations.py : ce sont des ESTIMATIONS sur une échelle abstraite
0-100, pas des montants en MAD. Les pourcentages 40/40/20 sont la
répartition demandée par l'architecture du moteur, pas une donnée
sourcée non plus.
"""

REPARTITION_PHASES = {1: 0.40, 2: 0.40, 3: 0.20}
SEUIL_GRATUIT = 20.0  # cout_estimation <= ce seuil => solution consideree "gratuite" (cf. estimations.py, tier "Faible" = 15)
COUT_PAR_DEFAUT = 45.0  # si cout_estimation absent (ne devrait pas arriver apres estimations.enrichir_solutions)


def _phase_min_autorisee(sid: str, sous_graphe: Dict[str, List[str]], phase_assignee: Dict[str, int]) -> int:
    """Une solution ne peut pas être planifiée avant son dernier prérequis interne."""
    prereqs = sous_graphe.get(sid, [])
    phases_prereqs = [phase_assignee[p] for p in prereqs if p in phase_assignee]
    return max(phases_prereqs, default=0)


def allouer_par_phases(
    ordre_solutions: List[Dict[str, Any]],
    solutions_db: Dict[str, Any],
    budget_disponible: float,
    sous_graphe: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """
    Point d'entrée principal.

    Paramètres :
        ordre_solutions : liste de solutions scorées, DÉJÀ ordonnée par
            dependances.ordonner_solutions() (clé "ordre" de son retour).
        solutions_db : dict complet des solutions ENRICHIES (sortie de
            estimations.enrichir_solutions), pour retrouver cout_estimation.
        budget_disponible : budget du profil (estimations.enrichir_profils),
            échelle abstraite 0-100.
        sous_graphe : dépendances internes au plan (sortie de
            dependances.construire_sous_graphe), pour respecter l'ordre
            même entre phases. Si None, recalculé à partir de
            dependances.DEPENDANCES (import paresseux pour éviter un
            couplage circulaire si ce module est utilisé isolément).

    Retourne :
        {
            "phases": {0: [...], 1: [...], 2: [...], 3: [...]},
            "hors_budget": [...],   # solutions n'ayant trouvé aucune phase
            "budget_par_phase": {1: .., 2: .., 3: ..},
            "depense_par_phase": {0: .., 1: .., 2: .., 3: ..},
        }
    """
    if sous_graphe is None:
        from dependances import construire_sous_graphe
        solution_ids = [s["solution_id"] for s in ordre_solutions]
        sous_graphe, _ = construire_sous_graphe(solution_ids)

    budget_par_phase = {p: round(budget_disponible * part, 1) for p, part in REPARTITION_PHASES.items()}
    depense_par_phase = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}
    phases: Dict[int, List[Dict[str, Any]]] = {0: [], 1: [], 2: [], 3: []}
    hors_budget: List[Dict[str, Any]] = []
    phase_assignee: Dict[str, int] = {}

    for solution in ordre_solutions:
        sid = solution["solution_id"]
        cout = solutions_db.get(sid, {}).get("cout_estimation", COUT_PAR_DEFAUT)
        phase_min = _phase_min_autorisee(sid, sous_graphe, phase_assignee)

        if phase_min == 0 and cout <= SEUIL_GRATUIT:
            # Vraiment gratuite ET aucun prerequis ne la retarde : phase 0,
            # jamais soumise a un plafond budgetaire.
            depense_par_phase[0] += cout
            phase_assignee[sid] = 0
            phases[0].append(solution)
            continue

        # Payante, OU gratuite mais retardee par un prerequis paye (phase_min >= 1) :
        # dans les deux cas elle doit respecter le plafond de la phase visee.
        phase = max(phase_min, 1)
        placee = False
        while phase <= 3:
            if depense_par_phase[phase] + cout <= budget_par_phase[phase]:
                depense_par_phase[phase] += cout
                phase_assignee[sid] = phase
                phases[phase].append(solution)
                placee = True
                break
            phase += 1

        if not placee:
            # Aucune phase budgetaire ne peut absorber ce cout : signale, ne
            # supprime jamais silencieusement (cas limite J7).
            logger.warning(
                "Solution '%s' (cout=%.1f) hors budget sur les 3 phases (budget total dispo=%.1f) - "
                "signalee dans 'hors_budget', pas de phase attribuee.",
                sid, cout, budget_disponible,
            )
            # Reference de phase la plus tardive pour ne pas bloquer un eventuel
            # dependant qui, lui, tiendrait dans le budget.
            phase_assignee[sid] = 3
            hors_budget.append(solution)

    return {
        "phases": phases,
        "hors_budget": hors_budget,
        "budget_par_phase": budget_par_phase,
        "depense_par_phase": depense_par_phase,
    }


if __name__ == "__main__":
    import argparse
    import logging as _logging

    from filtrage import charger_donnees, filtrer
    from exposition import calculer_exposition
    from estimations import enrichir_solutions, enrichir_profils
    from scoring import scorer_solutions_profil
    from dependances import ordonner_solutions

    parser = argparse.ArgumentParser(description="Algorithme 4 - Allocation par phases")
    parser.add_argument("--dossier", default="../data")
    parser.add_argument("--profil", default="pme001")
    args = parser.parse_args()

    _logging.basicConfig(level=_logging.WARNING, format="[allocation_phases] %(levelname)s: %(message)s")

    data = charger_donnees(args.dossier)
    data["solutions"] = enrichir_solutions(data["solutions"], data["matrice"])
    data["profils"] = enrichir_profils(data["profils"])

    profil = data["profils"][args.profil]
    resultat_filtrage = filtrer(profil, data)
    expositions = calculer_exposition(resultat_filtrage["risques_pertinents"], profil)
    solutions_scorees = scorer_solutions_profil(resultat_filtrage, expositions, profil)
    resultat_deps = ordonner_solutions(solutions_scorees, data["solutions"])

    resultat = allouer_par_phases(resultat_deps["ordre"], data["solutions"], profil["budget_disponible"])

    print(f"\n=== Allocation par phases — {profil['nom']} (budget_disponible={profil['budget_disponible']}) ===")
    print(f"Budget par phase : {resultat['budget_par_phase']}")
    for p in [0, 1, 2, 3]:
        sols = resultat["phases"][p]
        print(f"\nPhase {p} ({'gratuite' if p == 0 else f'{REPARTITION_PHASES[p]*100:.0f}% budget'}) "
              f"— dépense {resultat['depense_par_phase'][p]:.1f} — {len(sols)} solution(s) :")
        for s in sols:
            cout = data["solutions"][s["solution_id"]]["cout_estimation"]
            print(f"    [{s['score_final']:>5.1f}] {s['nom'][:45]:45s} (cout={cout:.0f})")

    if resultat["hors_budget"]:
        print(f"\n[HORS BUDGET] {len(resultat['hors_budget'])} solution(s) non planifiable(s) avec ce budget :")
        for s in resultat["hors_budget"]:
            print(f"    {s['nom']}")
