# -*- coding: utf-8 -*-
"""
regles_site_web_mobilite.py — Jour 4 : Regles conditionnelles (site web et mobilite)
======================================================================================

Responsable : Aymane

Ce module code les deux premiers blocs de regles CONDITIONNELLES de la
grille du Jalon 1 : celles qui ne s'appliquent que si la PME a repondu
"Oui" a une question precise.

  - regle_002 : s'applique si site_web == "Oui"        (4 recommandations)
  - regle_003 : s'applique si employes_nomades == "Oui" (2 recommandations)

Le fichier 05_regles_recommandation.json contient deja, pour chaque
regle, un champ "condition" structure (type / question / valeur).
Pour ce Jalon 2, on garde des "if" ecrits en clair (plus faciles a
relire et a expliquer a l'encadrante) plutot que de generaliser tout
de suite une lecture automatique de ce champ.
"""

from load_data import charger_donnees


def _recommandations_de(donnees, condition_lisible):
    """
    Petite fonction utilitaire : va chercher, dans le fichier de regles,
    la liste des recommandations associee a une condition precise
    (identifiee par son texte lisible, ex "site_web == Oui").

    Cela evite de coder en dur le nom exact de la regle ("regle_002")
    et rend le code plus resistant si l'ordre des regles change un jour
    dans le fichier JSON.
    """
    for id_regle, regle in donnees["regles"].items():
        if regle.get("condition_lisible") == condition_lisible:
            return regle["recommandations"]
    print(f"[ATTENTION] Condition '{condition_lisible}' introuvable dans 05_regles_recommandation.json")
    return []


def regles_site_web(donnees, profil):
    """
    Retourne les recommandations liees au site web / a la vente en ligne,
    uniquement si le profil a repondu "Oui" a la question site_web.
    """
    if profil["site_web"] == "Oui":
        return _recommandations_de(donnees, "site_web == Oui")
    return []


def regles_mobilite(donnees, profil):
    """
    Retourne les recommandations liees a la mobilite (employes nomades,
    travail a distance), uniquement si le profil a repondu "Oui" a la
    question employes_nomades.
    """
    if profil["employes_nomades"] == "Oui":
        return _recommandations_de(donnees, "employes_nomades == Oui")
    return []


def regles_site_web_et_mobilite(donnees, profil):
    """Regroupe les deux blocs ci-dessus : pratique pour les tests et pour J6."""
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

    # Profil 1 : site web = Oui, nomade = Non -> doit donner 4 recos site web, 0 mobilite
    profil_site_web = {
        "secteur": "E-commerce", "nb_employes": "10 à 50",
        "site_web": "Oui", "personne_it": "Non",
        "employes_nomades": "Non", "donnees_personnelles": "Oui",
    }
    recos = regles_site_web_et_mobilite(donnees, profil_site_web)
    afficher_recommandations(recos, titre="Profil avec site web, sans mobilite")

    # Profil 2 : site web = Non, nomade = Oui -> doit donner 0 reco site web, 2 mobilite
    profil_nomade = {
        "secteur": "Finance", "nb_employes": "10 à 50",
        "site_web": "Non", "personne_it": "Oui",
        "employes_nomades": "Oui", "donnees_personnelles": "Oui",
    }
    recos = regles_site_web_et_mobilite(donnees, profil_nomade)
    afficher_recommandations(recos, titre="Profil sans site web, avec mobilite")

    # Profil 3 : les deux a Non -> doit donner 0 recommandation ici
    profil_minimal = {
        "secteur": "Généraliste", "nb_employes": "moins de 10",
        "site_web": "Non", "personne_it": "Non",
        "employes_nomades": "Non", "donnees_personnelles": "Non",
    }
    recos = regles_site_web_et_mobilite(donnees, profil_minimal)
    afficher_recommandations(recos, titre="Profil minimal (aucune condition remplie)")
