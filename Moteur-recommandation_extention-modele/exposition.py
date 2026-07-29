from __future__ import annotations
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


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


VALEUR_PAR_DEFAUT = 0.50


def _valeur_num(valeur_qualitative: str, table: Dict[str, float], nom_champ: str) -> float:
    if valeur_qualitative not in table:
        logger.warning(
            "Valeur '%s' inconnue pour le champ '%s' - utilisation de la valeur par defaut (%.2f).",
            valeur_qualitative, nom_champ, VALEUR_PAR_DEFAUT,
        )
        return VALEUR_PAR_DEFAUT
    return table[valeur_qualitative]



FACTEURS_MATURITE = [
    ("très faible", 1.30),
    ("faible", 1.15),   # attrape aussi "faible à moyenne" en plus du mot-cle ci-dessus
    ("moyenne", 1.00),
    ("bonne", 0.85),
]


MOTS_CLES_DONNEES_SENSIBLES = [
    "santé", "sante", "médical", "medical", "financi", "bancaire",
    "personnelles", "patients", "paiement",
]


def facteur_maturite(profil: Dict[str, Any]) -> float:
   
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
   
    textes = profil.get("donnees_traitees", [])
    texte_complet = " ".join(str(t) for t in textes).lower()
    if any(mot in texte_complet for mot in MOTS_CLES_DONNEES_SENSIBLES):
        return 1.15
    return 1.00


def facteur_impact_pme(profil: Dict[str, Any]) -> float:
    
    return (
        facteur_maturite(profil)
        * facteur_taille(profil)
        * facteur_donnees_sensibles(profil)
    )



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
