"""
Module 1 de l'architecture — Filtrage profil -> risques -> regles -> solutions.

Role dans le pipeline :
    Etant donne un profil PME, ce module determine :
      1) quels risques (parmi les 95 de 01_risques.json) le concernent,
      2) quelles regles de recommandation (parmi les 95 de
         05_regles_recommandation.json) s'appliquent a ces risques et a
         son secteur,
      3) quelles solutions (parmi les 119 de 02_solutions.json) en
         decoulent.
    La sortie sert d'entree a exposition.py (Module 2 : Exposition), qui
    n'aura ainsi a calculer l'exposition que sur les risques reellement
    pertinents pour chaque profil, et le scoring que sur les solutions
    reellement eligibles.

Changements par rapport a l'ebauche S1-2 (J2) :
    - charger_donnees() ne depend plus de noms de fichiers exacts
      (les exports/telechargements successifs ajoutent des suffixes du
      type "__1_", "(1)", etc.) : elle recherche par prefixe numerique.
    - secteur_correspond() resout le cas "tous avec <condition
      d'infrastructure>" en croisant avec infrastructure_it.outils du
      profil, au lieu de l'exclure par defaut.
    - Ajout de filtrer_tous_profils() : le pipeline traite l'ensemble
      des profils PME avant l'etape d'exposition, pas un profil isole ;
      c'est ce point d'entree que l'orchestrateur appellera.
    - Les diagnostics passent par le module `logging` (niveau WARNING)
      plutot que `print`, pour rester silencieux par defaut une fois
      integre a un pipeline appele par un autre script.
    - Ajout d'une fonction d'export JSON (exporter_resultats) pour
      materialiser la sortie du Module 1 sur disque, au format attendu
      en entree par exposition.py.

Fichiers sources attendus (format des livrables S1-2 / architecture v2) :
    01_risques.json                    -> {"risques": {"r001": {...}, ...}}
    02_solutions.json                  -> {"solutions": {"sol001": {...}, ...}}
    03_profils_pme.json                -> {"profils_pme": {"pme001": {...}, ...}}
    04_matrice_risques_solutions.json  -> {"matrice_risques_solutions": {...}}
    05_regles_recommandation.json      -> {"regles_recommandation": {...}, "meta": {...}}

Note sur 04_matrice_risques_solutions.json :
    Ce module ne l'utilise pas directement : les regles de
    05_regles_recommandation.json en sont deja derivees (voir meta.
    methodologie) et contiennent risques_cibles + solutions_associees,
    ce qui suffit pour filtrer. La matrice reste disponible si on veut
    un jour court-circuiter les regles et raisonner risque -> solutions
    directement.
"""

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

# Mots-cles d'infrastructure reconnus dans les secteurs_prioritaires du
# type "tous avec X", mis en correspondance avec les libelles pouvant
# apparaitre dans profil.infrastructure_it.outils. A completer au fil de
# l'eau si de nouvelles regles introduisent d'autres conditions.
MOTS_CLES_INFRASTRUCTURE = {
    "tous avec site web": ["site web", "site e-commerce", "e-commerce"],
    "tous avec paiement en ligne": ["paiement en ligne", "paiement", "e-commerce"],
}


# ---------------------------------------------------------------------------
# Chargement des donnees
# ---------------------------------------------------------------------------

# (prefixe attendu, cle racine dans le JSON, cle de sortie dans le dict retourne)
_FICHIERS_ATTENDUS = [
    ("01_risques", "risques", "risques"),
    ("02_solutions", "solutions", "solutions"),
    ("03_profils_pme", "profils_pme", "profils"),
    ("04_matrice_risques_solutions", "matrice_risques_solutions", "matrice"),
    ("05_regles_recommandation", "regles_recommandation", "regles"),
]


def _trouver_fichier(dossier: Path, prefixe: str) -> Path:
    """Trouve un fichier JSON par prefixe, tolerant aux suffixes ajoutes
    par des telechargements/exports successifs (ex: '__1_', ' (1)').
    """
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
    """Charge les 5 fichiers JSON de l'architecture depuis un dossier.

    Args:
        dossier: chemin vers le dossier contenant les 5 fichiers.

    Returns:
        dict avec les cles : risques, solutions, profils, matrice, regles

    Raises:
        FichierSourceIntrouvableError: si un des 5 fichiers est absent.
    """
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


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def valider_profil(profil: Dict[str, Any]) -> None:
    """Verifie que le profil contient les champs minimums necessaires au filtrage."""
    champs_manquants = [c for c in CHAMPS_PROFIL_REQUIS if c not in profil]
    if champs_manquants:
        raise ProfilInvalideError(
            f"Champs manquants dans le profil '{profil.get('nom', '?')}' : {champs_manquants}"
        )


# ---------------------------------------------------------------------------
# Etape 1 : risques pertinents pour le profil
# ---------------------------------------------------------------------------

def get_risques_profil(
    profil: Dict[str, Any],
    risques_db: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Retourne les risques pertinents pour un profil.

    Base : le champ `risques_principaux` du profil, deja cure en amont
    (voir 03_profils_pme.json). On recupere les objets risque complets
    correspondants.
    """
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


# ---------------------------------------------------------------------------
# Etape 2 : correspondance sectorielle
# ---------------------------------------------------------------------------

def secteur_correspond(
    secteur_profil: str,
    secteurs_cibles: List[str],
    outils_infrastructure: Optional[List[str]] = None,
) -> bool:
    """Determine si le profil est couvert par une liste de secteurs cibles.

    Regles (voir secteurs_affectes des risques / secteurs_prioritaires des regles) :
      - "tous" dans la liste -> s'applique a tout le monde.
      - correspondance exacte (insensible a la casse) -> ok.
      - "tous avec <condition d'infrastructure>" (ex: "tous avec site
        web") -> resolue en croisant avec profil.infrastructure_it.outils
        (voir MOTS_CLES_INFRASTRUCTURE). Comportement conservateur si
        l'information n'est pas disponible : exclusion.
    """
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


# ---------------------------------------------------------------------------
# Etape 3 : regles applicables
# ---------------------------------------------------------------------------

def filtrer_regles(
    profil: Dict[str, Any],
    risques_profil_ids: List[str],
    regles_db: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Selectionne les regles de recommandation applicables au profil.

    Une regle s'applique si :
      - au moins un de ses `risques_cibles` fait partie des risques
        pertinents du profil, ET
      - son secteur (`secteurs_prioritaires`) correspond au profil
        (voir secteur_correspond, y compris les conditions d'infrastructure).
    """
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


# ---------------------------------------------------------------------------
# Etape 4 : solutions eligibles
# ---------------------------------------------------------------------------

def extraire_solutions_eligibles(
    regles_applicables: List[Dict[str, Any]],
    solutions_db: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Deduplique et enrichit les solutions issues des regles applicables.

    Chaque solution retournee contient les champs de 02_solutions.json,
    plus des metadonnees utiles a exposition.py / scoring.py :
      - regles_sources : ids des regles qui l'ont amenee
      - priorite_max : priorite la plus haute parmi ses regles sources
      - phases_associees : phases suggerees par ses regles sources
    """
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


# ---------------------------------------------------------------------------
# Point d'entree principal du module (un profil)
# ---------------------------------------------------------------------------

def filtrer(profil: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """Filtre un profil unique.

    Args:
        profil: un profil PME (dict issu de 03_profils_pme.json).
        data: dict retourne par charger_donnees() (risques, solutions, regles...).

    Returns:
        dict pret a etre transmis a exposition.py :
        {
            "profil_id": ...,
            "risques_pertinents": [ {risque complet}, ... ],
            "regles_applicables": [ {regle complete}, ... ],
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


# ---------------------------------------------------------------------------
# Point d'entree du pipeline (tous les profils)
# ---------------------------------------------------------------------------

def filtrer_tous_profils(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Applique filtrer() a tous les profils de data["profils"].

    C'est ce point d'entree que l'orchestrateur du pipeline appelle avant
    d'invoquer exposition.py : celui-ci n'a alors plus qu'a iterer sur
    resultats[profil_id]["risques_pertinents"] / ["solutions_eligibles"].

    Un profil invalide n'interrompt pas le traitement des autres : il est
    journalise et ignore (le pipeline global decide comment reagir).

    Returns:
        dict {profil_id: resultat_filtrage}
    """
    resultats: Dict[str, Dict[str, Any]] = {}
    for profil_id, profil in data["profils"].items():
        try:
            resultats[profil_id] = filtrer(profil, data)
        except ProfilInvalideError as e:
            logger.error("Profil '%s' ignore : %s", profil_id, e)
    return resultats


def exporter_resultats(resultats: Dict[str, Dict[str, Any]], chemin_sortie: str | Path) -> Path:
    """Serialise la sortie du Module 1 en JSON pour exposition.py.

    Args:
        resultats: sortie de filtrer_tous_profils().
        chemin_sortie: fichier .json a ecrire.

    Returns:
        le Path du fichier ecrit.
    """
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
