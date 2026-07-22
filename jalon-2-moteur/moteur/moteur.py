# -*- coding: utf-8 -*-
"""
moteur.py
---------
Jalon 2 - Moteur de règles (assemblage final, J6)
Auteurs : Aymane + Fatima Zahraa

Rassemble les 3 blocs de règles (universelles, site web/mobilité,
IT/données/secteur) dans une seule fonction recommander(profil) qui
retourne la liste complète des recommandations applicables à ce profil,
triées par priorité (Haute puis Moyenne).
"""

from load_data import charger_donnees
from regles_universelles import regles_universelles
from regles_site_web_mobilite import regles_site_web_et_mobilite
from regles_it_donnees_secteur import regles_it_donnees_secteur


# Ordre de priorité utilisé pour le tri (plus petit = affiché en premier)
ORDRE_PRIORITE = {"Haute": 0, "Moyenne": 1, "Basse": 2}


def recommander(profil, donnees=None):
    """
    Prend un profil PME en entrée et retourne la liste complète des
    recommandations qui s'appliquent à ce profil, toutes règles
    confondues, triées par priorité (Haute puis Moyenne).

    Paramètres :
        profil  : dictionnaire du profil PME (voir profil.py)
        donnees : données déjà chargées via charger_donnees() (optionnel).
                  Si non fourni, les 5 JSON sont rechargés à chaque appel
                  (pratique pour tester, mais si recommander() est appelé
                  en boucle sur plusieurs profils, il vaut mieux charger
                  une seule fois et passer `donnees` explicitement).
    """
    if donnees is None:
        donnees = charger_donnees()

    recommandations = []
    recommandations += regles_universelles(donnees)
    recommandations += regles_site_web_et_mobilite(donnees, profil)
    recommandations += regles_it_donnees_secteur(donnees, profil)

    recommandations_triees = sorted(
        recommandations,
        key=lambda reco: ORDRE_PRIORITE.get(reco["priorite"], 99),
    )

    return recommandations_triees


def afficher_recommandations(recommandations, titre="Recommandations pour ce profil"):
    print(f"\n{titre} ({len(recommandations)} recommandation(s)) :")
    if not recommandations:
        print("  (aucune recommandation ne s'applique)")
    for reco in recommandations:
        print(f"  [{reco['priorite']}] {reco['solution_nom']}")
        print(f"      -> couvre le risque : {reco['risque_nom']}")


if __name__ == "__main__":
    from profil import PROFILS_EXEMPLE

    donnees = charger_donnees()

    for profil_id, profil in PROFILS_EXEMPLE.items():
        resultats = recommander(profil, donnees=donnees)
        afficher_recommandations(resultats, titre=f"Profil {profil_id} ({profil['secteur']})")
