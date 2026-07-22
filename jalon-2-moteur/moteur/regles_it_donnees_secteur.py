from load_data import charger_donnees
def _recommandations_de(donnees, condition_lisible):

    for id_regle, regle in donnees["regles"].items():
        if regle.get("condition_lisible") == condition_lisible:
            return regle["recommandations"]
    print(f"[ATTENTION] Condition '{condition_lisible}' introuvable dans 05_regles_recommandation.json")
    return []


def regles_personne_it(donnees, profil):

    if profil["personne_it"] == "Oui":
        return _recommandations_de(donnees, "personne_it == Oui")
    return []


def regles_donnees_personnelles(donnees, profil):

    if profil["donnees_personnelles"] == "Oui":
        return _recommandations_de(donnees, "donnees_personnelles == Oui")
    return []


def regles_secteur(donnees, profil):

    if profil["secteur"] in ["Finance", "E-commerce"]:
        return _recommandations_de(donnees, "secteur in [Finance, E-commerce]")
    return []


def regles_it_donnees_secteur(donnees, profil):

    return (
        regles_personne_it(donnees, profil)
        + regles_donnees_personnelles(donnees, profil)
        + regles_secteur(donnees, profil)
    )


def afficher_recommandations(recommandations, titre="Recommandations"):
    print(f"\n{titre} ({len(recommandations)}) :")
    if not recommandations:
        print("  (aucune : condition non remplie pour ce profil)")
    for reco in recommandations:
        print(f"  [{reco['priorite']}] {reco['solution_nom']}")
        print(f"      -> couvre le risque : {reco['risque_nom']}")


if __name__ == "__main__":
    donnees = charger_donnees()

    profil_finance_complet = {
        "secteur": "Finance", "nb_employes": "10 à 50",
        "site_web": "Oui", "personne_it": "Oui",
        "employes_nomades": "Non", "donnees_personnelles": "Oui",
    }
    recos = regles_it_donnees_secteur(donnees, profil_finance_complet)
    afficher_recommandations(recos, titre="Profil Finance, IT et donnees personnelles")

    profil_ecommerce_sans_it = {
        "secteur": "E-commerce", "nb_employes": "moins de 10",
        "site_web": "Oui", "personne_it": "Non",
        "employes_nomades": "Oui", "donnees_personnelles": "Oui",
    }
    recos = regles_it_donnees_secteur(donnees, profil_ecommerce_sans_it)
    afficher_recommandations(recos, titre="Profil E-commerce, sans personne IT")

    profil_minimal = {
        "secteur": "Généraliste", "nb_employes": "moins de 10",
        "site_web": "Non", "personne_it": "Non",
        "employes_nomades": "Non", "donnees_personnelles": "Non",
    }
    recos = regles_it_donnees_secteur(donnees, profil_minimal)
    afficher_recommandations(recos, titre="Profil minimal (aucune condition remplie)")
