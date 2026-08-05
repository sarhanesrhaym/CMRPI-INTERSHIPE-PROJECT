from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)



DEPENDANCES: Dict[str, List[str]] = {

    "sol034": ["sol033"],          
    "sol010": ["sol033"],          
    "sol060": ["sol033", "sol004"], 
    "sol031": ["sol010"],          

  
    "sol024": ["sol032"],          
    "sol036": ["sol024", "sol021"], 
    "sol042": ["sol036"],           
    "sol049": ["sol036"],          


    "sol021": ["sol050"],           

  
    "sol001": ["sol004"],          

 
    "sol019": ["sol059", "sol004"], 


    "sol045": ["sol044"],           
    "sol046": ["sol044"],         
    "sol025": ["sol044"],          

  
    "sol039": ["sol028"],          


    "sol038": ["sol003"],          
    "sol009": ["sol035"],          
}


class CycleDependanceError(Exception):
   
    pass


def construire_sous_graphe(
    solution_ids: List[str],
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    
    solution_ids_set = set(solution_ids)
    sous_graphe: Dict[str, List[str]] = {sid: [] for sid in solution_ids}
    dependances_externes: Dict[str, List[str]] = {}

    for sid in solution_ids:
        prerequis = DEPENDANCES.get(sid, [])
        for prereq in prerequis:
            if prereq in solution_ids_set:
                sous_graphe[sid].append(prereq)
            else:
                dependances_externes.setdefault(sid, []).append(prereq)

    return sous_graphe, dependances_externes


def tri_topologique_kahn(
    sous_graphe: Dict[str, List[str]],
    priorite: Optional[Dict[str, float]] = None,
) -> Tuple[List[str], Optional[List[str]]]:
  
    priorite = priorite or {}

    
    degre_entrant = {sid: len(prereqs) for sid, prereqs in sous_graphe.items()}

  
    dependants: Dict[str, List[str]] = {sid: [] for sid in sous_graphe}
    for sid, prereqs in sous_graphe.items():
        for prereq in prereqs:
            dependants[prereq].append(sid)

   
    prets = [sid for sid, d in degre_entrant.items() if d == 0]
    prets.sort(key=lambda sid: priorite.get(sid, 0), reverse=True)

    ordre: List[str] = []
    while prets:
       
        courant = prets.pop(0)
        ordre.append(courant)

        for suivant in dependants[courant]:
            degre_entrant[suivant] -= 1
            if degre_entrant[suivant] == 0:
                prets.append(suivant)
        prets.sort(key=lambda sid: priorite.get(sid, 0), reverse=True)

    if len(ordre) != len(sous_graphe):
       
        noeuds_en_cycle = [sid for sid in sous_graphe if sid not in ordre]
        logger.warning(
            "Cycle de dependances detecte, impliquant : %s. "
            "Ces solutions sont ajoutees en fin d'ordre sans garantie de coherence.",
            noeuds_en_cycle,
        )
        ordre.extend(noeuds_en_cycle)
        return ordre, noeuds_en_cycle

    return ordre, None


def ordonner_solutions(
    solutions_scorees: List[Dict[str, Any]],
    solutions_db: Dict[str, Any],
) -> Dict[str, Any]:
 
    solution_ids = [s["solution_id"] for s in solutions_scorees]
    priorite = {s["solution_id"]: s["score_final"] for s in solutions_scorees}

    sous_graphe, dependances_externes = construire_sous_graphe(solution_ids)
    ordre_ids, cycle = tri_topologique_kahn(sous_graphe, priorite)

    solutions_par_id = {s["solution_id"]: s for s in solutions_scorees}
    ordre_final = [solutions_par_id[sid] for sid in ordre_ids]

    prerequis_manquants = {}
    for sid, prereqs_externes in dependances_externes.items():
        noms = [solutions_db.get(p, {}).get("nom", p) for p in prereqs_externes]
        prerequis_manquants[sid] = noms

    return {
        "ordre": ordre_final,
        "cycle_detecte": cycle,
        "prerequis_manquants": prerequis_manquants,
    }


if __name__ == "__main__":
    import argparse
    from filtrage import charger_donnees, filtrer
    from exposition import calculer_exposition
    from estimations import enrichir_solutions, enrichir_profils
    from scoring import scorer_solutions_profil

    parser = argparse.ArgumentParser(description="Algorithme 3 - Dependances entre solutions")
    parser.add_argument("--dossier", default="data")
    parser.add_argument("--profil", default=None, help="Identifiant d'un profil (ex: pme010, riche en solutions -> bon cas de test)")
    parser.add_argument("--test-cycle", action="store_true",
                         help="Lance un test isole avec un cycle artificiel A->B->C->A pour verifier la detection")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="[dependances] %(levelname)s: %(message)s")

    if args.test_cycle:
        print("=== Test isole : detection de cycle (A depend de B, B de C, C de A) ===")
        graphe_cycle = {"A": ["B"], "B": ["C"], "C": ["A"]}
        ordre, cycle = tri_topologique_kahn(graphe_cycle)
        print(f"Ordre obtenu : {ordre}")
        print(f"Cycle detecte : {cycle}")
        raise SystemExit(0)

    data = charger_donnees(args.dossier)
    data["solutions"] = enrichir_solutions(data["solutions"], data["matrice"])
    data["profils"] = enrichir_profils(data["profils"])

    profil_id = args.profil or "pme010"  # Smart Factory Meknès : profil riche en solutions (bon cas de test)
    profil = data["profils"][profil_id]

    resultat_filtrage = filtrer(profil, data)
    expositions = calculer_exposition(resultat_filtrage["risques_pertinents"], profil)
    solutions_scorees = scorer_solutions_profil(resultat_filtrage, expositions, profil)

    resultat = ordonner_solutions(solutions_scorees, data["solutions"])

    print(f"\n=== Ordre de mise en oeuvre — {profil['nom']} ({profil['secteur']}) ===")
    print(f"{len(resultat['ordre'])} solution(s) a ordonner\n")

    for i, sol in enumerate(resultat["ordre"], start=1):
        sid = sol["solution_id"]
        prereqs_internes = DEPENDANCES.get(sid, [])
        marque = " (a un prerequis dans ce plan)" if any(
            p in [s["solution_id"] for s in resultat["ordre"]] for p in prereqs_internes
        ) else ""
        print(f"  {i:2d}. [{sol['score_final']:>5.1f}] {sol['nom']}{marque}")

    if resultat["cycle_detecte"]:
        print(f"\n[ATTENTION] Cycle de dependances detecte : {resultat['cycle_detecte']}")

    if resultat["prerequis_manquants"]:
        print("\n[INFO] Prerequis logiques non couverts par ce plan (a signaler a l'utilisateur) :")
        for sid, noms in resultat["prerequis_manquants"].items():
            nom_solution = data["solutions"].get(sid, {}).get("nom", sid)
            print(f"  - {nom_solution} suppose : {', '.join(noms)}")
