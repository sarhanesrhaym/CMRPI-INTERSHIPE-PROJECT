# -*- coding: utf-8 -*-
"""
regles_universelles.py — Jour 3 : Regles universelles
=======================================================

Responsable : Aymane

Ce module isole le cas le plus simple de la grille de recommandation :
les recommandations qui s'appliquent a TOUTE PME, quelles que soient
ses reponses aux 6 questions de profilage. Dans le fichier
05_regles_recommandation.json, c'est la regle dont la condition
est {"type": "toujours"} (regle_001, 11 recommandations).

On commence par ce cas car il ne contient aucune logique conditionnelle :
si ce module echoue, le probleme vient forcement de la lecture des
donnees (load_data.py), pas d'une erreur de condition.
"""

from load_data import charger_donnees


def regles_universelles(donnees):
    """
    Retourne la liste des recommandations qui s'appliquent a tout profil,
    sans aucune condition sur les reponses.

    Parametre :
        donnees : le dictionnaire retourne par charger_donnees()

    Retourne :
        une liste de dictionnaires, chacun avec les cles
        risque_id, risque_nom, solution_id, solution_nom,
        solution_description, priorite
    """
    for id_regle, regle in donnees["regles"].items():
        if regle["condition"]["type"] == "toujours":
            return regle["recommandations"]

    # Si on arrive ici, aucune regle "toujours" n'a ete trouvee dans le
    # fichier 05 : c'est anormal, on retourne une liste vide plutot que
    # de planter, mais on previent clairement dans la console.
    print("[ATTENTION] Aucune regle universelle trouvee dans 05_regles_recommandation.json")
    return []


def afficher_recommandations(recommandations, titre="Recommandations"):
    """Affiche une liste de recommandations de facon lisible dans la console."""
    print(f"\n{titre} ({len(recommandations)}) :")
    for reco in recommandations:
        print(f"  [{reco['priorite']}] {reco['solution_nom']}")
        print(f"      -> couvre le risque : {reco['risque_nom']}")


if __name__ == "__main__":
    # Test manuel : "python regles_universelles.py" doit afficher les
    # 11 recommandations universelles attendues (cf. grille du Jalon 1).
    donnees = charger_donnees()
    recos = regles_universelles(donnees)
    afficher_recommandations(recos, titre="Recommandations universelles (tout profil)")

    # Petite verification de bon sens : on attend exactement 11 recommandations
    # d'apres la grille construite au Jalon 1.
    if len(recos) == 11:
        print("\nOK : 11 recommandations universelles, conforme a la grille du Jalon 1.")
    else:
        print(f"\n[ATTENTION] {len(recos)} recommandations trouvees, 11 attendues : a verifier.")
