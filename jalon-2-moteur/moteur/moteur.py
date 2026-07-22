
from load_data import charger_donnees
from regles_universelles import regles_universelles
from regles_site_web_mobilite import regles_site_web_et_mobilite
from regles_it_donnees_secteur import regles_it_donnees_secteur


ORDRE_PRIORITE = {"Haute": 0, "Moyenne": 1, "Basse": 2}


def recommander(profil, donnees=None):
  
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
