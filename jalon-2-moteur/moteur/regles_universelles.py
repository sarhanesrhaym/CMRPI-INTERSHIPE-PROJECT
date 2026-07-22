# -*- coding: utf-8 -*-

from load_data import charger_donnees


def regles_universelles(donnees):
   
    return donnees["regles"]["regle_001"]["recommandations"]


def afficher_recommandations(recommandations, titre="Recommandations"):
    print(f"\n{titre} ({len(recommandations)}) :")
    for reco in recommandations:
        print(f"  [{reco['priorite']}] {reco['solution_nom']}")
        print(f"      -> couvre le risque : {reco['risque_nom']}")


if __name__ == "__main__":
  
    donnees = charger_donnees()
    recos = regles_universelles(donnees)
    afficher_recommandations(recos, titre="Recommandations universelles (tout profil)")

    if len(recos) == 11:
        print("\nOK : 11 recommandations universelles, conforme a la grille du Jalon 1.")
    else:
        print(f"\n[ATTENTION] {len(recos)} recommandations trouvees, 11 attendues : a verifier.")
