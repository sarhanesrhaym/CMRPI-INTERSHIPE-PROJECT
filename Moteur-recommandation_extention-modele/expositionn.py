from __future__ import annotations
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

"""
exposition.py — Algorithme 1 : Exposition aux risques
========================================================

Responsable : Aymane

Ce module prend la sortie du module Filtrage (filtrage.filtrer(profil, data))
et calcule, pour chaque risque pertinent d'un profil, un score d'exposition
qui combine :
    - la severite du risque (donnee sourcee, dans 01_risques.json)
    - la probabilite du risque (donnee sourcee, dans 01_risques.json)
    - un facteur d'impact propre au profil PME (taille, maturite IT,
      sensibilite des donnees traitees)

IMPORTANT - Transparence sur les donnees estimees (decision du J1) :
Les champs "severite" et "probabilite" sont qualitatifs dans nos fichiers
sources (ex: "ÉLEVÉE", "MOYENNE") car aucune source consultee ne fournit
de probabilite numerique fiable pour le contexte marocain. Pour pouvoir
calculer un score, on leur associe ici une valeur numerique sur une
echelle 0-1. CETTE CONVERSION EST UNE ESTIMATION ASSUMEE (une mise en
correspondance raisonnable d'une echelle ordinale vers une echelle
numerique), PAS une donnee retrouvee dans les guides sources. Le facteur
d'impact PME (taille/maturite/donnees sensibles) est du meme ordre : une
regle de calcul that nous avons choisie et documentee, pas une donnee
sourcee. Tout chiffre produit par ce module doit etre presente comme tel
dans le rapport de stage.
"""

# ------------------------------------------------------------------
# 1. Conversion des echelles qualitatives en valeurs numeriques (0-1)
#    ESTIMATION ASSUMEE - voir docstring du module.
# ------------------------------------------------------------------

SEVERITE_NUM: Dict[str, float] = {
    "CRITIQUE": 1.00,
    "ÉLEVÉE": 0.70,
    "MOYENNE": 0.40,
}

PROBABILITE_NUM: Dict[str, float] = {
    "TRÈS ÉLEVÉE": 0.90,
    "ÉLEVÉE": 0.70,
    "MOYENNE": 0.50,
    "FAIBLE-MOYENNE": 0.35,
    "FAIBLE": 0.20,
}

# Valeur par defaut si un risque a une severite/probabilite absente ou
# non reconnue (ne devrait pas arriver si 01_risques.json est propre,
# mais on prefere une valeur prudente a un plantage).
VALEUR_PAR_DEFAUT = 0.50


def _valeur_num(valeur_qualitative: str, table: Dict[str, float], nom_champ: str) -> float:
    if valeur_qualitative not in table:
        logger.warning(
            "Valeur '%s' inconnue pour le champ '%s' - utilisation de la valeur par defaut (%.2f).",
            valeur_qualitative, nom_champ, VALEUR_PAR_DEFAUT,
        )
        return VALEUR_PAR_DEFAUT
    return table[valeur_qualitative]


# ------------------------------------------------------------------
# 2. Facteur d'impact propre au profil PME
#    ESTIMATION ASSUMEE - regle de calcul documentee ci-dessous.
# ------------------------------------------------------------------

# Mots-cles recherches dans profil["maturite_it"] (le champ contient parfois
# des valeurs composees comme "Bonne (IT) / Moyenne (OT)" : on prend le
# MAXIMUM des facteurs trouves, c'est-a-dire le maillon le plus faible,
# car l'exposition d'une PME est tiree vers le haut par sa plus grande
# faiblesse, pas par sa moyenne.
FACTEURS_MATURITE = [
    ("très faible", 1.30),
    ("faible", 1.15),   # attrape aussi "faible à moyenne" en plus du mot-cle ci-dessus
    ("moyenne", 1.00),
    ("bonne", 0.85),
]

# Mots-cles recherches dans profil["donnees_traitees"] (liste de textes
# libres) pour detecter si la PME traite des donnees particulierement
# sensibles, ce qui alourdit les consequences d'un incident.
MOTS_CLES_DONNEES_SENSIBLES = [
    "santé", "sante", "médical", "medical", "financi", "bancaire",
    "personnelles", "patients", "paiement",
]


def facteur_maturite(profil: Dict[str, Any]) -> float:
    """
    Retourne le facteur lie a la maturite IT du profil. Si la valeur est
    composee (ex: 'Bonne (IT) / Moyenne (OT)'), on retient le facteur le
    plus penalisant parmi les mots-cles trouves.
    """
    maturite = str(profil.get("maturite_it", "")).lower()
    facteurs_trouves = [f for mot, f in FACTEURS_MATURITE if mot in maturite]
    if not facteurs_trouves:
        logger.warning(
            "maturite_it '%s' non reconnue pour le profil '%s' - facteur neutre (1.0) applique.",
            profil.get("maturite_it"), profil.get("nom"),
        )
        return 1.00
    return max(facteurs_trouves)


def facteur_taille(profil: Dict[str, Any]) -> float:
    """
    Retourne un facteur lie a la taille de l'entreprise (nombre d'employes).
    Hypothese assumee : une tres petite structure a generalement moins de
    ressources pour absorber un incident (facteur legerement superieur a 1),
    une structure plus grande est supposee legerement plus mature en moyenne.
    Cette hypothese est discutable et doit etre revue si des donnees reelles
    contredisent cette estimation.
    """
    nb_employes = profil.get("nb_employes", 0)
    try:
        nb_employes = int(nb_employes)
    except (TypeError, ValueError):
        logger.warning(
            "nb_employes '%s' non interpretable pour le profil '%s' - facteur neutre (1.0) applique.",
            profil.get("nb_employes"), profil.get("nom"),
        )
        return 1.00

    if nb_employes < 15:
        return 1.10
    if nb_employes <= 50:
        return 1.00
    return 0.95


def facteur_donnees_sensibles(profil: Dict[str, Any]) -> float:
    """
    Retourne un facteur majore si le profil traite des donnees identifiees
    comme particulierement sensibles (sante, finance, paiement...), sur la
    base d'une recherche de mots-cles dans profil['donnees_traitees'].
    """
    textes = profil.get("donnees_traitees", [])
    texte_complet = " ".join(str(t) for t in textes).lower()
    if any(mot in texte_complet for mot in MOTS_CLES_DONNEES_SENSIBLES):
        return 1.15
    return 1.00


def facteur_impact_pme(profil: Dict[str, Any]) -> float:
    """
    Combine les 3 facteurs ci-dessus en un seul multiplicateur d'impact,
    propre au profil (independant du risque). Applique ensuite a chaque
    risque du profil dans calculer_exposition().
    """
    return (
        facteur_maturite(profil)
        * facteur_taille(profil)
        * facteur_donnees_sensibles(profil)
    )


# ------------------------------------------------------------------
# 3. Calcul de l'exposition par risque, et classification
# ------------------------------------------------------------------

# Seuils de classification, calibres empiriquement sur la distribution
# reelle des scores obtenus sur les 40 profils (voir le bloc de test en
# bas de fichier). A ajuster si la base de risques/profils evolue
# significativement.
SEUIL_CRITIQUE = 0.56
SEUIL_IMPORTANTE = 0.42


def classer_exposition(score: float) -> str:
    if score >= SEUIL_CRITIQUE:
        return "CRITIQUE"
    if score >= SEUIL_IMPORTANTE:
        return "IMPORTANTE"
    return "UTILE"


def calculer_exposition(
    risques_pertinents: List[Dict[str, Any]],
    profil: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Prend la liste des risques pertinents d'un profil (sortie de
    filtrage.get_risques_profil, deja disponible dans le resultat de
    filtrage.filtrer()) et retourne, pour chacun, son score d'exposition
    et sa classification, tries du plus exposant au moins exposant.
    """
    impact_pme = facteur_impact_pme(profil)
    resultats = []

    for risque in risques_pertinents:
        severite_num = _valeur_num(risque.get("severite", ""), SEVERITE_NUM, "severite")
        probabilite_num = _valeur_num(risque.get("probabilite", ""), PROBABILITE_NUM, "probabilite")

        score = severite_num * probabilite_num * impact_pme

        resultats.append({
            "risque_id": risque["id"],
            "risque_nom": risque["nom"],
            "severite": risque.get("severite"),
            "probabilite": risque.get("probabilite"),
            "score_exposition": round(score, 3),
            "classification": classer_exposition(score),
        })

    resultats.sort(key=lambda r: r["score_exposition"], reverse=True)
    return resultats


if __name__ == "__main__":
    import argparse
    from filtrage import charger_donnees, filtrer

    parser = argparse.ArgumentParser(description="Algorithme 1 - Exposition aux risques")
    parser.add_argument("--dossier", default="data", help="Dossier contenant les 5 fichiers JSON sources")
    parser.add_argument("--profil", default=None, help="Identifiant d'un profil precis (ex: pme001). Sinon, calibrage sur tous les profils.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.ERROR, format="[exposition] %(levelname)s: %(message)s")

    data = charger_donnees(args.dossier)

    if args.profil:
        profil = data["profils"][args.profil]
        resultat_filtrage = filtrer(profil, data)
        expositions = calculer_exposition(resultat_filtrage["risques_pertinents"], profil)

        print(f"\n=== Exposition aux risques — {profil['nom']} ({profil['secteur']}) ===")
        print(f"Facteur d'impact PME calcule : {facteur_impact_pme(profil):.3f} "
              f"(maturite x{facteur_maturite(profil):.2f}, taille x{facteur_taille(profil):.2f}, "
              f"donnees sensibles x{facteur_donnees_sensibles(profil):.2f})\n")
        for e in expositions:
            print(f"  [{e['classification']:10s}] score={e['score_exposition']:.3f}  {e['risque_nom']}")
    else:
        # Mode calibrage : calcule la distribution des scores sur tous les
        # profils, pour verifier/ajuster SEUIL_CRITIQUE et SEUIL_IMPORTANTE.
        tous_scores = []
        for profil_id, profil in data["profils"].items():
            resultat_filtrage = filtrer(profil, data)
            expositions = calculer_exposition(resultat_filtrage["risques_pertinents"], profil)
            tous_scores.extend(e["score_exposition"] for e in expositions)

        tous_scores.sort()
        n = len(tous_scores)
        print(f"Nombre total de couples (risque, profil) evalues : {n}")
        if n:
            print(f"Min : {tous_scores[0]:.3f}  |  Max : {tous_scores[-1]:.3f}")
            print(f"Mediane : {tous_scores[n // 2]:.3f}")
            print(f"Percentile 33% : {tous_scores[int(n * 0.33)]:.3f}")
            print(f"Percentile 66% : {tous_scores[int(n * 0.66)]:.3f}")
            repartition = {"CRITIQUE": 0, "IMPORTANTE": 0, "UTILE": 0}
            for s in tous_scores:
                repartition[classer_exposition(s)] += 1
            print(f"Repartition avec seuils actuels : {repartition}")
