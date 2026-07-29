from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

"""
dependances.py — Algorithme 3 : Dependances entre solutions
===============================================================

Responsable : Aymane

Ce module ordonne une liste de solutions recommandees pour un profil
(sortie de scoring.py) en respectant les prerequis logiques entre elles
(ex: separer les comptes utilisateur/admin suppose d'avoir deja fait
l'inventaire des actifs). L'ordre est calcule par un tri topologique
(algorithme de Kahn), qui place toujours un prerequis avant la ou les
solutions qui en dependent.

IMPORTANT - Transparence sur les donnees estimees (meme principe qu'au
J1 pour exposition.py et estimations.py) :
Aucun champ "cette solution depend de telle autre" n'existe dans
02_solutions.json. La table DEPENDANCES ci-dessous est une estimation
assumee, construite a partir d'un raisonnement metier (quel prerequis
logique a du sens pour quelle solution), PAS une donnee extraite des
guides sources. Elle est volontairement limitee aux cas ou la
dependance est claire et defendable ; toutes les solutions ne sont pas
couvertes, et c'est normal (beaucoup de solutions sont independantes
les unes des autres).
"""

# ------------------------------------------------------------------
# Table des dependances : solution_id -> liste des solution_id qui
# doivent etre mises en oeuvre AVANT elle. ESTIMATION ASSUMEE (voir
# docstring ci-dessus), a valider avec l'encadrante si presentee comme
# livrable.
# ------------------------------------------------------------------

DEPENDANCES: Dict[str, List[str]] = {
    # Gestion des identites et des acces : il faut savoir ce qu'on a
    # avant de savoir qui y accede.
    "sol034": ["sol033"],           # Separation comptes utilisateur/admin <- Inventaire des actifs
    "sol010": ["sol033"],           # Gestion des permissions d'acces <- Inventaire des actifs
    "sol060": ["sol033", "sol004"], # Comptes privilegies <- Inventaire des actifs + Politique mdp
    "sol031": ["sol010"],           # Matrice d'habilitations <- Gestion des permissions

    # Journalisation : des logs sans horloges synchronisees ne servent
    # a rien pour retracer un incident.
    "sol024": ["sol032"],           # Centralisation des journaux <- Synchronisation NTP
    "sol036": ["sol024", "sol021"], # Plan de reponse a incident <- Journaux + PCA/PRA
    "sol042": ["sol036"],           # Declaration d'incident <- Plan de reponse a incident
    "sol049": ["sol036"],           # Exercices de gestion de crise <- Plan de reponse a incident

    # Continuite d'activite : un plan de reprise suppose de savoir quels
    # risques on couvre en priorite.
    "sol021": ["sol050"],           # PCA/PRA <- Analyse de risques EBIOS

    # Acces distant : une authentification forte doit preceder l'ouverture
    # d'un acces VPN, sinon le VPN protege un mot de passe faible.
    "sol001": ["sol004"],           # VPN <- Politique de mots de passe

    # Cloud : chiffrer avant d'envoyer suppose de savoir ce qui est
    # sensible.
    "sol019": ["sol059", "sol004"], # Chiffrement pre-cloud <- Classification des donnees + Politique mdp

    # Cycle de developpement securise : les outils d'analyse automatisee
    # n'ont de sens qu'une fois la securite integree au processus.
    "sol045": ["sol044"],           # SAST/DAST <- Integration securite SDLC
    "sol046": ["sol044"],           # SCA <- Integration securite SDLC
    "sol025": ["sol044"],           # Separation environnements dev/test/prod <- Integration securite SDLC

    # Reseau : une strategie anti-DDoS a plus de sens sur un reseau deja
    # segmente.
    "sol039": ["sol028"],           # Mitigation DDoS <- Cloisonnement reseau

    # Site web : verifier l'integrite des fichiers suppose d'avoir deja
    # une version de reference a jour.
    "sol038": ["sol003"],           # Verification integrite fichiers site <- Mise a jour CMS
    "sol009": ["sol035"],           # Sauvegarde du site web <- Regle de sauvegarde 3-2-1
}


class CycleDependanceError(Exception):
    """Levee quand un cycle est detecte entre des solutions (ex: A depend de B qui depend de A)."""
    pass


def construire_sous_graphe(
    solution_ids: List[str],
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    A partir d'une liste de solutions a ordonner (celles recommandees pour
    UN profil precis), construit :
      - le sous-graphe des dependances INTERNES a cette liste (celles que
        le tri topologique doit respecter)
      - les dependances EXTERNES (des prerequis qui existent dans
        DEPENDANCES mais qui ne font pas partie des solutions recommandees
        pour ce profil - a signaler, pas a ignorer silencieusement)
    """
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
    """
    Algorithme de Kahn : ordonne les noeuds d'un graphe de dependances de
    sorte que chaque prerequis apparaisse avant les noeuds qui en dependent.

    Parametres :
        sous_graphe : {solution_id: [ids des prerequis internes]}
        priorite    : {solution_id: score}, optionnel. Quand plusieurs
                      solutions sont pretes en meme temps (aucun prerequis
                      restant), on choisit d'abord celle avec le score le
                      plus eleve (integration avec l'Algorithme 2 - Scoring).

    Retourne (ordre, cycle) :
        - ordre : liste des solution_id dans un ordre valide, ou liste
          partielle si un cycle empeche de tout ordonner
        - cycle : None si aucun cycle, sinon la liste des solution_id
          impliques dans un cycle detecte
    """
    priorite = priorite or {}

    # degre entrant = nombre de prerequis restants pour chaque solution
    degre_entrant = {sid: len(prereqs) for sid, prereqs in sous_graphe.items()}

    # graphe inverse : pour un prerequis, quelles solutions en dependent
    dependants: Dict[str, List[str]] = {sid: [] for sid in sous_graphe}
    for sid, prereqs in sous_graphe.items():
        for prereq in prereqs:
            dependants[prereq].append(sid)

    # File des solutions pretes (sans prerequis restant), triee par
    # priorite decroissante pour un ordre deterministe et coherent avec
    # le scoring.
    prets = [sid for sid, d in degre_entrant.items() if d == 0]
    prets.sort(key=lambda sid: priorite.get(sid, 0), reverse=True)

    ordre: List[str] = []
    while prets:
        # On retire toujours le premier (le mieux priorise) de la liste
        # triee, puis on re-trie apres ajout de nouveaux elements prets.
        courant = prets.pop(0)
        ordre.append(courant)

        for suivant in dependants[courant]:
            degre_entrant[suivant] -= 1
            if degre_entrant[suivant] == 0:
                prets.append(suivant)
        prets.sort(key=lambda sid: priorite.get(sid, 0), reverse=True)

    if len(ordre) != len(sous_graphe):
        # Il reste des noeuds avec un degre entrant > 0 : ils font partie
        # d'un cycle (ou dependent d'un noeud dans un cycle).
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
    """
    Point d'entree principal : prend la liste des solutions deja scorees
    pour un profil (sortie de scoring.scorer_solutions_profil) et retourne
    un ordre de mise en oeuvre respectant les dependances internes,
    departage par le score_final quand plusieurs solutions sont pretes en
    meme temps.

    Retourne un dictionnaire avec :
        - "ordre" : liste des solutions dans l'ordre de mise en oeuvre
          (memes dictionnaires que solutions_scorees, dans le nouvel ordre)
        - "cycle_detecte" : None ou liste des solution_id en cycle
        - "prerequis_manquants" : {solution_id: [prerequis non couverts
          par ce plan]}, a signaler a l'utilisateur (ex : "la separation
          des comptes admin est recommandee mais l'inventaire des actifs
          ne fait pas partie du plan actuel")
    """
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
