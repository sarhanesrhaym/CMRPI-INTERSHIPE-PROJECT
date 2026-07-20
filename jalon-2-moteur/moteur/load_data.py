# -*- coding: utf-8 -*-
"""
load_data.py — Jour 1 : Mise en place du projet
=================================================

Ce module charge les 5 fichiers JSON de la base de connaissances
(construite pendant le Jalon 1) en mémoire, pour que le reste du
moteur (regles_universelles.py, regles_conditionnelles.py, etc.)
puisse s'en servir directement.

Tache partagee Aymane + Fatima Zahraa.
"""

import json
import os

# Dossier où se trouvent les 5 fichiers JSON. On part du principe
# qu'ils sont dans un sous-dossier "data" a cote de ce script.
DOSSIER_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _charger_json(nom_fichier):
    """Ouvre un fichier JSON du dossier data/ et retourne son contenu."""
    chemin = os.path.join(DOSSIER_DATA, nom_fichier)
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def charger_donnees():
    """
    Charge les 5 fichiers de la base de connaissances et les retourne
    sous forme d'un seul dictionnaire, pour que le reste du code n'ait
    qu'un seul objet a passer entre les fonctions.

    Retourne un dictionnaire avec les cles :
        - "risques"    : dict des 22 risques (cle = id du risque, ex "r001")
        - "solutions"  : dict des 21 solutions (cle = id de la solution, ex "sol001")
        - "profils"    : dict des 5 profils d'exemple
        - "grille"     : liste des 23 lignes de la grille risque/solution
        - "regles"     : dict des 6 regles de recommandation pretes a coder
        - "questions"  : description des 6 questions de profilage (dans le fichier 05)
    """
    risques_json = _charger_json("01_risques.json")
    solutions_json = _charger_json("02_solutions.json")
    profils_json = _charger_json("03_profils_pme.json")
    matrice_json = _charger_json("04_matrice_risques_solutions.json")
    regles_json = _charger_json("05_regles_recommandation.json")

    donnees = {
        "risques": risques_json["risques"],
        "solutions": solutions_json["solutions"],
        "profils": profils_json["profils_exemple"],
        "grille": matrice_json["grille"],
        "regles": regles_json["regles_recommandation"],
        "questions": regles_json["questions"],
    }
    return donnees


def verifier_donnees(donnees):
    """
    Verification simple de bon sens : est-ce que chaque regle pointe bien
    vers des risques et des solutions qui existent vraiment ? Cela evite
    de decouvrir une erreur de copier-coller au milieu d'un test plus tard.

    Affiche un message d'erreur pour chaque probleme trouve, et retourne
    True si tout est correct, False sinon.
    """
    ok = True
    ids_risques = set(donnees["risques"].keys())
    ids_solutions = set(donnees["solutions"].keys())

    for id_regle, regle in donnees["regles"].items():
        for reco in regle["recommandations"]:
            if reco["risque_id"] not in ids_risques:
                print(f"[ERREUR] {id_regle} : risque inconnu {reco['risque_id']}")
                ok = False
            if reco["solution_id"] not in ids_solutions:
                print(f"[ERREUR] {id_regle} : solution inconnue {reco['solution_id']}")
                ok = False
    return ok


if __name__ == "__main__":
    # Petit test manuel : lancer "python load_data.py" doit afficher
    # le nombre d'elements charges dans chaque fichier, et confirmer
    # que les regles ne pointent vers rien d'inexistant.
    donnees = charger_donnees()

    print("Chargement termine :")
    print(f"  - {len(donnees['risques'])} risques")
    print(f"  - {len(donnees['solutions'])} solutions")
    print(f"  - {len(donnees['profils'])} profils d'exemple")
    print(f"  - {len(donnees['grille'])} lignes de grille")
    print(f"  - {len(donnees['regles'])} regles de recommandation")

    print()
    if verifier_donnees(donnees):
        print("Verification des references : tout est coherent.")
    else:
        print("Verification des references : des erreurs ont ete trouvees (voir ci-dessus).")
