# -*- coding: utf-8 -*-
"""
test_nouveaux_profils.py — Jour 8 : Test avec 2-3 nouveaux profils fictifs
============================================================================

Contrairement a test_profils_exemple.py (qui verifie des totaux connus
a l'avance), ce script sert a tester la ROBUSTESSE du moteur sur des
profils qu'on n'avait pas prevus au depart. Le but n'est pas de
verifier un chiffre precis, mais de VERIFIER A L'OEIL que chaque
recommandation qui sort a bien un sens pour le profil concerne.

On ajoute quand meme quelques verifications automatiques simples
(assert) sur des cas evidents : par exemple, un profil sans site web
ne doit jamais recevoir une recommandation liee au site web.
"""

import sys
import os

DOSSIER_TESTS = os.path.dirname(os.path.abspath(__file__))
RACINE_JALON2 = os.path.dirname(DOSSIER_TESTS)
DOSSIER_MOTEUR = os.path.join(RACINE_JALON2, "moteur")
sys.path.insert(0, DOSSIER_MOTEUR)

from load_data import charger_donnees
from moteur import recommander, afficher_recommandations


# Les 3 nouveaux profils, invents pour ce test (pas dans profil.py)
NOUVEAUX_PROFILS = {
    "test_blog_vitrine": {
        "description": "Site web vitrine simple, sans collecte de donnees personnelles",
        "profil": {
            "secteur": "Généraliste", "nb_employes": "moins de 10",
            "site_web": "Oui", "personne_it": "Non",
            "employes_nomades": "Non", "donnees_personnelles": "Non",
        },
    },
    "test_consultant_nomade": {
        "description": "Consultant independant, tout le temps en deplacement, pas de site web",
        "profil": {
            "secteur": "Généraliste", "nb_employes": "moins de 10",
            "site_web": "Non", "personne_it": "Non",
            "employes_nomades": "Oui", "donnees_personnelles": "Oui",
        },
    },
    "test_startup_finance_sans_it": {
        "description": "Jeune structure Finance sans personne IT dediee (cas limite)",
        "profil": {
            "secteur": "Finance", "nb_employes": "moins de 10",
            "site_web": "Non", "personne_it": "Non",
            "employes_nomades": "Non", "donnees_personnelles": "Oui",
        },
    },
}


def verifications_de_bon_sens(profil_id, profil, resultats):
    """
    Quelques verifications automatiques simples, pour attraper les
    incoherences les plus evidentes sans avoir a tout relire a l'oeil.
    Retourne la liste des problemes trouves (vide si tout va bien).
    """
    problemes = []
    noms_recommandations = [r["solution_nom"] for r in resultats]

    # Si pas de site web, aucune recommandation "CMS", "site web" ou "paiement en ligne"
    if profil["site_web"] == "Non":
        for nom in noms_recommandations:
            if "CMS" in nom or "site web" in nom.lower() or "paiement en ligne" in nom.lower():
                problemes.append(f"Recommandation '{nom}' presente alors que site_web = Non")

    # Si pas nomade, pas de VPN ni de chiffrement d'equipements nomades
    if profil["employes_nomades"] == "Non":
        for nom in noms_recommandations:
            if "VPN" in nom or "équipements nomades" in nom.lower():
                problemes.append(f"Recommandation '{nom}' presente alors que employes_nomades = Non")

    # Si pas de donnees personnelles, pas de recommandation loi 09-08
    if profil["donnees_personnelles"] == "Non":
        for nom in noms_recommandations:
            if "09-08" in nom or "conservation des données" in nom.lower():
                problemes.append(f"Recommandation '{nom}' presente alors que donnees_personnelles = Non")

    return problemes


if __name__ == "__main__":
    donnees = charger_donnees()

    print("=== Test avec de nouveaux profils fictifs (Jour 8) ===")

    tous_ok = True
    for profil_id, contenu in NOUVEAUX_PROFILS.items():
        profil = contenu["profil"]
        print(f"\n--- {profil_id} ---")
        print(f"Description : {contenu['description']}")

        resultats = recommander(profil, donnees=donnees)
        afficher_recommandations(resultats, titre=f"Recommandations pour {profil_id}")

        problemes = verifications_de_bon_sens(profil_id, profil, resultats)
        if problemes:
            tous_ok = False
            print(f"\n[ATTENTION] {len(problemes)} incoherence(s) detectee(s) pour {profil_id} :")
            for p in problemes:
                print(f"   - {p}")
        else:
            print(f"\n[OK] Aucune incoherence evidente detectee pour {profil_id}.")

    print("\n" + "=" * 60)
    if tous_ok:
        print("Resultat global : aucune incoherence automatique detectee.")
        print("Relire quand meme les recommandations ci-dessus a l'oeil avant le J9.")
    else:
        print("Resultat global : des incoherences ont ete detectees, a corriger au J9.")
