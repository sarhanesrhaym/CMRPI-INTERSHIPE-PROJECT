
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class ProfilInvalideError(Exception):
    """Levee quand le profil PME ne contient pas les champs minimums requis."""
    pass


class FichierSourceIntrouvableError(Exception):
    """Levee quand un des 5 fichiers JSON attendus n'est pas trouve dans le dossier."""
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

MOTS_CLES_INFRASTRUCTURE = {
    "tous avec site web": ["site web", "site e-commerce", "e-commerce"],
    "tous avec paiement en ligne": ["paiement en ligne", "paiement", "e-commerce"],
}


# (prefixe attendu, cle racine dans le JSON, cle de sortie dans le dict retourne)
_FICHIERS_ATTENDUS = [
    ("01_risques", "risques", "risques"),
    ("02_solutions", "solutions", "solutions"),
    ("03_profils_pme", "profils_pme", "profils"),
    ("04_matrice_risques_solutions", "matrice_risques_solutions", "matrice"),
    ("05_regles_recommandation", "regles_recommandation", "regles"),
]


def _trouver_fichier(dossier: Path, prefixe: str) -> Path:
    candidats = sorted(dossier.glob(f"{prefixe}*.json"))
    if not candidats:
        raise FichierSourceIntrouvableError(
            f"Aucun fichier '{prefixe}*.json' trouve dans '{dossier}'."
        )
    if len(candidats) > 1:
        logger.warning(
            "Plusieurs fichiers correspondent a '%s*.json' dans %s : %s. "
            "Utilisation du premier (%s).",
            prefixe, dossier, [c.name for c in candidats], candidats[0].name,
        )
    return candidats[0]


def charger_donnees(dossier: str | Path) -> Dict[str, Any]:
    dossier = Path(dossier)
    resultat: Dict[str, Any] = {}

    for prefixe, cle_json, cle_sortie in _FICHIERS_ATTENDUS:
        chemin = _trouver_fichier(dossier, prefixe)
        with open(chemin, encoding="utf-8") as f:
            contenu = json.load(f)
        if cle_json not in contenu:
            raise FichierSourceIntrouvableError(
                f"Cle '{cle_json}' absente de '{chemin.name}'."
            )
        resultat[cle_sortie] = contenu[cle_json]

    return resultat
def valider_profil(profil: Dict[str, Any]) -> None:
    """Verifie que le profil contient les champs minimums necessaires au filtrage."""
    champs_manquants = [c for c in CHAMPS_PROFIL_REQUIS if c not in profil]
    if champs_manquants:
        raise ProfilInvalideError(
            f"Champs manquants dans le profil '{profil.get('nom', '?')}' : {champs_manquants}"
        )
def get_risques_profil(
    profil: Dict[str, Any],
    risques_db: Dict[str, Any],
) -> List[Dict[str, Any]]:
    risques_ids = profil.get("risques_principaux", [])
    risques = []
    for rid in risques_ids:
        risque = risques_db.get(rid)
        if risque is None:
            logger.warning(
                "Risque '%s' reference par le profil '%s' introuvable dans 01_risques.json.",
                rid, profil.get("nom"),
            )
            continue
        risques.append(risque)
    return risques

def secteur_correspond(
    secteur_profil: str,
    secteurs_cibles: List[str],
    outils_infrastructure: Optional[List[str]] = None,
) -> bool:
    
    secteurs_cibles_norm = [s.strip().lower() for s in secteurs_cibles]
    outils_norm = [o.strip().lower() for o in (outils_infrastructure or [])]

    if "tous" in secteurs_cibles_norm:
        return True

    if secteur_profil.strip().lower() in secteurs_cibles_norm:
        return True

    for cible in secteurs_cibles_norm:
        if cible.startswith("tous avec"):
            mots_cles = MOTS_CLES_INFRASTRUCTURE.get(cible)
            if mots_cles is None:
                logger.warning(
                    "Condition d'infrastructure inconnue '%s' - exclusion par defaut. "
                    "Ajouter une entree dans MOTS_CLES_INFRASTRUCTURE si elle est legitime.",
                    cible,
                )
                continue
            if any(mc in outil for outil in outils_norm for mc in mots_cles):
                return True

    return False

def filtrer_regles(
    profil: Dict[str, Any],
    risques_profil_ids: List[str],
    regles_db: Dict[str, Any],
) -> List[Dict[str, Any]]:
    
    secteur_profil = profil.get("secteur", "")
    outils_infrastructure = profil.get("infrastructure_it", {}).get("outils", [])
    regles_applicables = []

    for regle in regles_db.values():
        risques_cibles = set(regle.get("risques_cibles", []))
        if not risques_cibles.intersection(risques_profil_ids):
            continue
        if not secteur_correspond(
            secteur_profil,
            regle.get("secteurs_prioritaires", ["tous"]),
            outils_infrastructure,
        ):
            continue
        regles_applicables.append(regle)

    return regles_applicables

def extraire_solutions_eligibles(
    regles_applicables: List[Dict[str, Any]],
    solutions_db: Dict[str, Any],
) -> List[Dict[str, Any]]:
    
    ordre_priorite = {"Critique": 3, "Haute": 2, "Moyenne": 1, "Basse": 0}
    solutions_par_id: Dict[str, Dict[str, Any]] = {}

    for regle in regles_applicables:
        for sol_id in regle.get("solutions_associees", []):
            solution_ref = solutions_db.get(sol_id)
            if solution_ref is None:
                logger.warning(
                    "Solution '%s' referencee par la regle '%s' introuvable dans 02_solutions.json.",
                    sol_id, regle.get("id"),
                )
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

def filtrer(profil: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    valider_profil(profil)

    risques_pertinents = get_risques_profil(profil, data["risques"])
    risques_ids = [r["id"] for r in risques_pertinents]

    regles_applicables = filtrer_regles(profil, risques_ids, data["regles"])
    solutions_eligibles = extraire_solutions_eligibles(regles_applicables, data["solutions"])

    if not solutions_eligibles:
        logger.warning(
            "Aucune solution eligible pour le profil '%s' - cas limite (voir J7).",
            profil.get("nom", "inconnu"),
        )

    return {
        "profil_id": profil["id"],
        "risques_pertinents": risques_pertinents,
        "regles_applicables": regles_applicables,
        "solutions_eligibles": solutions_eligibles,
    }

def filtrer_tous_profils(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    resultats: Dict[str, Dict[str, Any]] = {}
    for profil_id, profil in data["profils"].items():
        try:
            resultats[profil_id] = filtrer(profil, data)
        except ProfilInvalideError as e:
            logger.error("Profil '%s' ignore : %s", profil_id, e)
    return resultats


def exporter_resultats(resultats: Dict[str, Dict[str, Any]], chemin_sortie: str | Path) -> Path:
    
    chemin_sortie = Path(chemin_sortie)
    chemin_sortie.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin_sortie, "w", encoding="utf-8") as f:
        json.dump(resultats, f, ensure_ascii=False, indent=2)
    return chemin_sortie


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Module 1 - Filtrage profil -> regles -> solutions")
    parser.add_argument("--dossier", default="/mnt/user-data/uploads",
                         help="Dossier contenant les 5 fichiers JSON sources")
    parser.add_argument("--sortie", default=None,
                         help="Si fourni, ecrit le resultat filtre au format JSON a ce chemin")
    parser.add_argument("--verbose", action="store_true", help="Active les logs WARNING")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING if args.verbose else logging.ERROR,
                         format="[filtrage] %(levelname)s: %(message)s")

    data = charger_donnees(args.dossier)
    resultats = filtrer_tous_profils(data)

    for profil_id, resultat in resultats.items():
        profil = data["profils"][profil_id]
        print(f"\n=== {profil['nom']} ({profil['secteur']}) ===")
        print(f"Risques pertinents ({len(resultat['risques_pertinents'])}) : "
              + ", ".join(r["nom"] for r in resultat["risques_pertinents"]))
        print(f"Regles applicables : {len(resultat['regles_applicables'])}")
        print(f"Solutions eligibles ({len(resultat['solutions_eligibles'])}) :")
        for s in sorted(resultat["solutions_eligibles"], key=lambda s: s["nom"]):
            print(f"  - {s['nom']} (priorite max : {s['priorite_max']})")

    if args.sortie:
        chemin = exporter_resultats(resultats, args.sortie)
        print(f"\nResultats exportes vers {chemin}")
