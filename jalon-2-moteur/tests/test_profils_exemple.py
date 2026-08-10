# -*- coding: utf-8 -*-

import sys
import os


DOSSIER_TESTS = os.path.dirname(os.path.abspath(__file__))
RACINE_JALON2 = os.path.dirname(DOSSIER_TESTS)
DOSSIER_MOTEUR = os.path.join(RACINE_JALON2, "moteur")
sys.path.insert(0, DOSSIER_MOTEUR)

from load_data import charger_donnees
from moteur import recommander
from profil import PROFILS_EXEMPLE



TOTAUX_ATTENDUS = {
    "exemple001": 11,  # profil minimal : universelles seules
    "exemple002": 18,  # E-commerce : universelles + site web + donnees + secteur
    "exemple003": 19,  # Finance : universelles + mobilite + IT + donnees + secteur
    "exemple004": 13,  # Sante : universelles + donnees personnelles
    "exemple005": 22,  # Industrie : toutes les conditions reunies
}


def tester_un_profil(profil_id, profil, donnees):
    """Teste un profil et affiche PASS ou ECHEC selon le total attendu."""
    resultats = recommander(profil, donnees=donnees)
    total_obtenu = len(resultats)
    total_attendu = TOTAUX_ATTENDUS.get(profil_id)

    if total_attendu is None:
        print(f"[?] {profil_id} : pas de total attendu enregistre, ignore")
        return True

    if total_obtenu == total_attendu:
        print(f"[PASS] {profil_id} ({profil['secteur']}) : {total_obtenu} recommandations, conforme")
        return True
    else:
        print(f"[ECHEC] {profil_id} ({profil['secteur']}) : {total_obtenu} recommandations obtenues, "
              f"{total_attendu} attendues -> a verifier dans la grille ou le code")
        return False


if __name__ == "__main__":
    donnees = charger_donnees()

    print("=== Test des 5 profils exemple (Jour 7) ===\n")

    resultats_tests = []
    for profil_id, profil in PROFILS_EXEMPLE.items():
        ok = tester_un_profil(profil_id, profil, donnees)
        resultats_tests.append(ok)

    print()
    nb_reussis = sum(resultats_tests)
    nb_total = len(resultats_tests)
    if nb_reussis == nb_total:
        print(f"Resultat global : {nb_reussis}/{nb_total} profils conformes. Le moteur est valide sur ces cas.")
    else:
        print(f"Resultat global : {nb_reussis}/{nb_total} profils conformes. "
              f"{nb_total - nb_reussis} profil(s) a corriger avant de continuer.")
