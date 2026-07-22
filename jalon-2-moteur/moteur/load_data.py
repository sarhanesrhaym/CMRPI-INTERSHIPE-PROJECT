# -*- coding: utf-8 -*-


import json
import os


DOSSIER_MOTEUR = os.path.dirname(os.path.abspath(__file__))
RACINE_JALON2 = os.path.dirname(DOSSIER_MOTEUR)
DOSSIER_DATA = os.path.join(RACINE_JALON2, "data")


def _charger_json(nom_fichier):
   
    chemin = os.path.join(DOSSIER_DATA, nom_fichier)
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def charger_donnees():
   
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
