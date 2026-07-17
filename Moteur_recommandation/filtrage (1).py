"""

Rôle dans le pipeline :
    Étant donné un profil PME, ce module détermine :
      1) quels risques (parmi les 95 de 01_risques.json) le concernent,
      2) quelles règles de recommandation (parmi les 95 de
         05_regles_recommandation.json) s'appliquent à ces risques et à
         son secteur,
      3) quelles solutions (parmi les 119 de 02_solutions.json) en
         découlent.
    La sortie sert d'entrée à exposition.py (Module/Algorithme 1 :
    Exposition), qui n'aura ainsi à calculer l'exposition que sur les
    risques réellement pertinents pour le profil, et le scoring que sur
    les solutions réellement éligibles.

Fichiers sources attendus (format des livrables S1-2 / architecture v2) :
    01_risques.json                    -> {"risques": {"r001": {...}, ...}}
    02_solutions.json                  -> {"solutions": {"sol001": {...}, ...}}
    03_profils_pme.json                -> {"profils_pme": {"pme001": {...}, ...}}
    04_matrice_risques_solutions.json  -> {"matrice_risques_solutions": {...}}
    05_regles_recommandation.json      -> {"regles_recommandation": {...}, "meta": {...}}

Note sur 04_matrice_risques_solutions.json :
    Ce module ne l'utilise pas directement : les règles de
    05_regles_recommandation.json en sont déjà dérivées (voir meta.
    methodologie) et contiennent risques_cibles + solutions_associees,
    ce qui suffit pour filtrer. La matrice reste disponible si on veut
    un jour court-circuiter les règles et raisonner risque -> solutions
    directement.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class ProfilInvalideError(Exception):
    """Levée quand le profil PME ne contient pas les champs minimums requis."""
    pass


# Champs minimums attendus dans un profil (voir 03_profils_pme.json)
CHAMPS_PROFIL_REQUIS = [
    "id",
    "nom",
    "secteur",
    "nb_employes",
    "maturite_it",
    "risques_principaux",
]


# ---------------------------------------------------------------------------
# Chargement des données
# ---------------------------------------------------------------------------

def charger_donnees(dossier: str | Path) -> Dict[str, Any]:
    """Charge les 5 fichiers JSON de l'architecture depuis un dossier.

    Args:
        dossier: chemin vers le dossier contenant les 5 fichiers.

    Returns:
        dict avec les clés : risques, solutions, profils, matrice, regles, meta_regles
    """
    dossier = Path(dossier)

    def _load(nom_fichier: str, cle: str) -> Dict[str, Any]:
        with open(dossier / nom_fichier, encoding="utf-8") as f:
            return json.load(f)[cle]

    return {
        "risques": _load("01_risques__1_.json", "risques"),
        "solutions": _load("02_solutions__1_.json", "solutions"),
        "profils": _load("03_profils_pme__1_.json", "profils_pme"),
        "matrice": _load("04_matrice_risques_solutions__1_.json", "matrice_risques_solutions"),
        "regles": _load("05_regles_recommandation__1_.json", "regles_recommandation"),
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def valider_profil(profil: Dict[str, Any]) -> None:
    """Vérifie que le profil contient les champs minimums nécessaires au filtrage."""
    champs_manquants = [c for c in CHAMPS_PROFIL_REQUIS if c not in profil]
    if champs_manquants:
        raise ProfilInvalideError(
            f"Champs manquants dans le profil '{profil.get('nom', '?')}' : {champs_manquants}"
        )


# ---------------------------------------------------------------------------
# Étape 1 : risques pertinents pour le profil
# ---------------------------------------------------------------------------

def get_risques_profil(
    profil: Dict[str, Any],
    risques_db: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Retourne les risques pertinents pour un profil.

    Base : le champ `risques_principaux` du profil, déjà curé en amont
    (voir 03_profils_pme.json). On récupère les objets risque complets
    correspondants.


    """
    risques_ids = profil.get("risques_principaux", [])
    risques = []
    for rid in risques_ids:
        risque = risques_db.get(rid)
        if risque is None:
            print(f"[filtrage] Attention : risque '{rid}' référencé par le profil "
                  f"'{profil.get('nom')}' introuvable dans 01_risques.json.")
            continue
        risques.append(risque)
    return risques


# ---------------------------------------------------------------------------
# Étape 2 : correspondance sectorielle
# ---------------------------------------------------------------------------

def secteur_correspond(secteur_profil: str, secteurs_cibles: List[str]) -> bool:
    """Détermine si le secteur du profil est couvert par une liste de secteurs cibles.

    Règles (voir secteurs_affectes des risques / secteurs_prioritaires des règles) :
      - "tous" dans la liste -> s'applique à tout le monde.
      - correspondance exacte (insensible à la casse) -> ok.
      - correspondance partielle (ex: secteur profil "E-commerce" et cible
        "tous avec site web") -> non déductible automatiquement à ce stade
        (le profil n'indique pas explicitement s'il a un site web) ; à
        traiter comme cas limite, voir TODO ci-dessous.
    """
    secteurs_cibles_norm = [s.strip().lower() for s in secteurs_cibles]

    if "tous" in secteurs_cibles_norm:
        return True

    if secteur_profil.strip().lower() in secteurs_cibles_norm:
        return True

    # "tous avec site web" / "tous avec paiement en ligne", qui ne sont
    # pas des secteurs à proprement parler mais des conditions
    # d'infrastructure. Piste : croiser avec infrastructure_it.outils du
    # profil (ex: présence d'un site e-commerce) plutôt qu'avec le
    # secteur seul. Décision à documenter comme pour les données
    # estimées du J1.
    for cible in secteurs_cibles_norm:
        if cible.startswith("tous avec"):
            # Non tranché : on exclut par défaut (comportement conservateur)
            # tant que le critère d'infrastructure n'est pas implémenté.
            continue

    return False


# ---------------------------------------------------------------------------
# Étape 3 : règles applicables
# ---------------------------------------------------------------------------

def filtrer_regles(
    profil: Dict[str, Any],
    risques_profil_ids: List[str],
    regles_db: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Sélectionne les règles de recommandation applicables au profil.

    Une règle s'applique si :
      - au moins un de ses `risques_cibles` fait partie des risques
        pertinents du profil, ET
      - son secteur (`secteurs_prioritaires`) correspond au secteur du
        profil (voir secteur_correspond).
    """
    secteur_profil = profil.get("secteur", "")
    regles_applicables = []

    for regle in regles_db.values():
        risques_cibles = set(regle.get("risques_cibles", []))
        if not risques_cibles.intersection(risques_profil_ids):
            continue
        if not secteur_correspond(secteur_profil, regle.get("secteurs_prioritaires", ["tous"])):
            continue
        regles_applicables.append(regle)

    return regles_applicables


# ---------------------------------------------------------------------------
# Étape 4 : solutions éligibles
# ---------------------------------------------------------------------------

def extraire_solutions_eligibles(
    regles_applicables: List[Dict[str, Any]],
    solutions_db: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Déduplique et enrichit les solutions issues des règles applicables.

    Chaque solution retournée contient les champs de 02_solutions.json,
    plus des métadonnées utiles à exposition.py / scoring.py :
      - regles_sources : ids des règles qui l'ont amenée
      - priorite_max : priorité la plus haute parmi ses règles sources
      - phases_associees : phases suggérées par ses règles sources
    """
    ordre_priorite = {"Critique": 3, "Haute": 2, "Moyenne": 1, "Basse": 0}
    solutions_par_id: Dict[str, Dict[str, Any]] = {}

    for regle in regles_applicables:
        for sol_id in regle.get("solutions_associees", []):
            solution_ref = solutions_db.get(sol_id)
            if solution_ref is None:
                print(f"[filtrage] Attention : solution '{sol_id}' référencée par la règle "
                      f"'{regle.get('id')}' introuvable dans 02_solutions.json.")
                continue

            if sol_id not in solutions_par_id:
                solutions_par_id[sol_id] = {
                    **solution_ref,
                    "regles_sources": [],
                    "priorite_max": None,
                    "phases_associees": set(),
                }

            entree = solutions_par_id[sol_id]
            entree["regles_sources"].append(regle.get("id"))
            entree["phases_associees"].add(regle.get("phase"))

            priorite_regle = regle.get("priorite")
            if entree["priorite_max"] is None or (
                ordre_priorite.get(priorite_regle, -1) > ordre_priorite.get(entree["priorite_max"], -1)
            ):
                entree["priorite_max"] = priorite_regle

    # sets -> listes pour un output JSON-serialisable en aval
    resultat = []
    for entree in solutions_par_id.values():
        entree["phases_associees"] = sorted(entree["phases_associees"])
        resultat.append(entree)

    return resultat


# ---------------------------------------------------------------------------
# Point d'entrée principal du module
# ---------------------------------------------------------------------------

def filtrer(profil: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """Point d'entrée du Module 1 (Filtrage).

    Args:
        profil: un profil PME (dict issu de 03_profils_pme.json).
        data: dict retourné par charger_donnees() (risques, solutions, regles...).

    Returns:
        dict prêt à être transmis à exposition.py :
        {
            "profil_id": ...,
            "risques_pertinents": [ {risque complet}, ... ],
            "regles_applicables": [ {regle complète}, ... ],
            "solutions_eligibles": [ {solution enrichie}, ... ],
        }

    Raises:
        ProfilInvalideError: si le profil ne contient pas les champs requis.
    """
    valider_profil(profil)

    risques_pertinents = get_risques_profil(profil, data["risques"])
    risques_ids = [r["id"] for r in risques_pertinents]

    regles_applicables = filtrer_regles(profil, risques_ids, data["regles"])
    solutions_eligibles = extraire_solutions_eligibles(regles_applicables, data["solutions"])

    if not solutions_eligibles:
        print(f"[filtrage] Aucune solution éligible pour le profil "
              f"'{profil.get('nom', 'inconnu')}' — cas limite à traiter (voir J7).")

    return {
        "profil_id": profil["id"],
        "risques_pertinents": risques_pertinents,
        "regles_applicables": regles_applicables,
        "solutions_eligibles": solutions_eligibles,
    }


if __name__ == "__main__":
    # Test manuel sur des vraies données. À remplacer par de vrais tests
    # pytest au J8 (voir dependances.py / allocation_phases.py / strategies.py
    # pour les cas limites : profil sans solution éligible, etc.)
    DOSSIER_DONNEES = "/mnt/user-data/uploads"  # adapter selon l'emplacement réel

    data = charger_donnees(DOSSIER_DONNEES)

    for profil_id in ["pme001", "pme002"]:
        profil = data["profils"][profil_id]
        resultat = filtrer(profil, data)

        print(f"\n=== {profil['nom']} ({profil['secteur']}) ===")
        print(f"Risques pertinents ({len(resultat['risques_pertinents'])}) : "
              + ", ".join(r["nom"] for r in resultat["risques_pertinents"]))
        print(f"Règles applicables : {len(resultat['regles_applicables'])}")
        print(f"Solutions éligibles ({len(resultat['solutions_eligibles'])}) :")
        for s in sorted(resultat["solutions_eligibles"], key=lambda s: s["nom"]):
            print(f"  - {s['nom']} (priorité max : {s['priorite_max']})")
