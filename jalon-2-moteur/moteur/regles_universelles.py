from load_data import charger_donnees
def regles_universelles(donnees):
    for id_regle, regle in donnees["regles"].items():
        if regle["condition"]["type"] == "toujours":
            return regle["recommandations"]
  
    print("[ATTENTION] Aucune regle universelle trouvee dans 05_regles_recommandation.json")
    return []
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
