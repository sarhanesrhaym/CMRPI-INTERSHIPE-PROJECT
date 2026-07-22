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


def grouper_par_solution(recommandations):
 
    groupes = {}
    ordre_apparition = []

    for reco in recommandations:
        sid = reco["solution_id"]
        if sid not in groupes:
            groupes[sid] = {
                "solution_nom": reco["solution_nom"],
                "priorite": reco["priorite"],
                "risques_couverts": [],
            }
            ordre_apparition.append(sid)
        groupes[sid]["risques_couverts"].append(reco["risque_nom"])

    return [groupes[sid] for sid in ordre_apparition]


def afficher_recommandations(recommandations, titre="Recommandations pour ce profil"):
    groupees = grouper_par_solution(recommandations)

    print(f"\n{titre}")
    print(f"({len(groupees)} solution(s) distincte(s) — {len(recommandations)} lien(s) risque/solution au total) :")

    if not groupees:
        print("  (aucune recommandation ne s'applique)")

    for g in groupees:
        risques_str = ", ".join(g["risques_couverts"])
        print(f"  [{g['priorite']}] {g['solution_nom']}")
        print(f"      -> couvre : {risques_str}")


if _name_ == "_main_":
    from profil import PROFILS_EXEMPLE

    donnees = charger_donnees()

    for profil_id, profil in PROFILS_EXEMPLE.items():
        resultats = recommander(profil, donnees=donnees)
        afficher_recommandations(resultats, titre=f"Profil {profil_id} ({profil['secteur']})")
