# -*- coding: utf-8 -*-


from load_data import charger_donnees


def _recommandations_de(donnees, condition_lisible):
   
    for id_regle, regle in donnees["regles"].items():
        if regle.get("condition_lisible") == condition_lisible:
            return regle["recommandations"]
    print(f"[ATTENTION] Condition '{condition_lisible}' introuvable dans 05_regles_recommandation.json")
    return []


def regles_site_web(donnees, profil):
   
    if profil["site_web"] == "Oui":
        return _recommandations_de(donnees, "site_web == Oui")
    return []


def regles_mobilite(donnees, profil):
  
    if profil["employes_nomades"] == "Oui":
        return _recommandations_de(donnees, "employes_nomades == Oui")
    return []


def regles_site_web_et_mobilite(donnees, profil):
   
    return regles_site_web(donnees, profil) + regles_mobilite(donnees, profil)


def afficher_recommandations(recommandations, titre="Recommandations"):
    print(f"\n{titre} ({len(recommandations)}) :")
    if not recommandations:
        print("  (aucune : condition non remplie pour ce profil)")
    for reco in recommandations:
        print(f"  [{reco['priorite']}] {reco['solution_nom']}")
        print(f"      -> couvre le risque : {reco['risque_nom']}")


if __name__ == "__main__":
    donnees = charger_donnees()
    profil_site_web = {
        "secteur": "E-commerce", "nb_employes": "10 à 50",
        "site_web": "Oui", "personne_it": "Non",
        "employes_nomades": "Non", "donnees_personnelles": "Oui",
    }
    recos = regles_site_web_et_mobilite(donnees, profil_site_web)
    afficher_recommandations(recos, titre="Profil avec site web, sans mobilite")

    profil_nomade = {
        "secteur": "Finance", "nb_employes": "10 à 50",
        "site_web": "Non", "personne_it": "Oui",
        "employes_nomades": "Oui", "donnees_personnelles": "Oui",
    }
    recos = regles_site_web_et_mobilite(donnees, profil_nomade)
    afficher_recommandations(recos, titre="Profil sans site web, avec mobilite")

    profil_minimal = {
        "secteur": "Généraliste", "nb_employes": "moins de 10",
        "site_web": "Non", "personne_it": "Non",
        "employes_nomades": "Non", "donnees_personnelles": "Non",
    }
    recos = regles_site_web_et_mobilite(donnees, profil_minimal)
    afficher_recommandations(recos, titre="Profil minimal (aucune condition remplie)")
