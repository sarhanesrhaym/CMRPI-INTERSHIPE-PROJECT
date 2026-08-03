# -*- coding: utf-8 -*-
import sys
import os

DOSSIER_TESTS = os.path.dirname(os.path.abspath(__file__))
RACINE_JALON2 = os.path.dirname(DOSSIER_TESTS)
DOSSIER_MOTEUR = os.path.join(RACINE_JALON2, "moteur")
sys.path.insert(0, DOSSIER_MOTEUR)

from load_data import charger_donnees
from moteur import recommander, afficher_recommandations


NOUVEAUX_PROFILS = {
    "test_blog_vitrine": {
        "description": "Site web vitrine simple, sans collecte de données personnelles",
        "profil": {
            "secteur": "Généraliste", "nb_employes": "moins de 10",
            "site_web": "Oui", "personne_it": "Non",
            "employes_nomades": "Non", "donnees_personnelles": "Non",
        },
    },
    "test_consultant_nomade": {
        "description": "Consultant indépendant, tout le temps en déplacement, pas de site web",
        "profil": {
            "secteur": "Généraliste", "nb_employes": "moins de 10",
            "site_web": "Non", "personne_it": "Non",
            "employes_nomades": "Oui", "donnees_personnelles": "Oui",
        },
    },
    "test_startup_finance_sans_it": {
        "description": "Jeune structure Finance sans personne IT dédiée (cas corrige au J9)",
        "profil": {
            "secteur": "Finance", "nb_employes": "moins de 10",
            "site_web": "Non", "personne_it": "Non",
            "employes_nomades": "Non", "donnees_personnelles": "Oui",
        },
    },
    "test_ecommerce_sans_donnees": {
        "description": "Site e-commerce qui ne collecte pas encore de données personnelles (cas rare mais possible)",
        "profil": {
            "secteur": "E-commerce", "nb_employes": "10 à 50",
            "site_web": "Oui", "personne_it": "Oui",
            "employes_nomades": "Non", "donnees_personnelles": "Non",
        },
    },
    "test_sante_avec_it_et_nomade": {
        "description": "Structure de santé bien équipée : IT dédié et praticiens nomades",
        "profil": {
            "secteur": "Santé", "nb_employes": "10 à 50",
            "site_web": "Non", "personne_it": "Oui",
            "employes_nomades": "Oui", "donnees_personnelles": "Oui",
        },
    },
    "test_industrie_sans_site_web": {
        "description": "PME industrielle sans site web mais avec beaucoup de données internes",
        "profil": {
            "secteur": "Industrie", "nb_employes": "plus de 50",
            "site_web": "Non", "personne_it": "Oui",
            "employes_nomades": "Non", "donnees_personnelles": "Oui",
        },
    },
    "test_generaliste_donnees_sans_it": {
        "description": "Petite structure généraliste sans IT, mais qui collecte des données personnelles (cas proche du correctif J9, hors Finance/E-commerce)",
        "profil": {
            "secteur": "Généraliste", "nb_employes": "moins de 10",
            "site_web": "Non", "personne_it": "Non",
            "employes_nomades": "Non", "donnees_personnelles": "Oui",
        },
    },
}


def verifications_de_bon_sens(profil_id, profil, resultats):
    problemes = []
    noms_recommandations = [r["solution_nom"] for r in resultats]

    if profil["site_web"] == "Non":
        for nom in noms_recommandations:
            if "CMS" in nom or "site web" in nom.lower() or "paiement en ligne" in nom.lower():
                problemes.append(f"Recommandation '{nom}' présente alors que site_web = Non")

    if profil["employes_nomades"] == "Non":
        for nom in noms_recommandations:
            if "VPN" in nom or "équipements nomades" in nom.lower():
                problemes.append(f"Recommandation '{nom}' présente alors que employes_nomades = Non")

    if profil["donnees_personnelles"] == "Non":
        for nom in noms_recommandations:
            if "09-08" in nom or "conservation des données" in nom.lower():
                problemes.append(f"Recommandation '{nom}' présente alors que donnees_personnelles = Non")


    est_finance_ou_ecommerce = profil["secteur"] in ["Finance", "E-commerce"]
    expose_sans_it = profil["personne_it"] == "Non" and (
        est_finance_ou_ecommerce or profil["donnees_personnelles"] == "Oui"
    )
    if expose_sans_it:
        a_une_note_adaptation = any(r.get("note_adaptation") for r in resultats)
        if not a_une_note_adaptation:
            problemes.append(
                "Profil expose sans IT dedie mais aucune recommandation adaptee "
                "(note_adaptation) trouvee - le correctif J9 ne semble pas actif"
            )

    return problemes


if __name__ == "__main__":
    donnees = charger_donnees()

    print("=== Test avec des profils fictifs supplémentaires (Jour 8, version enrichie J9) ===")

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
            print(f"\n[ATTENTION] {len(problemes)} incohérence(s) détectée(s) pour {profil_id} :")
            for p in problemes:
                print(f"   - {p}")
        else:
            print(f"\n[OK] Aucune incohérence évidente détectée pour {profil_id}.")

    print("\n" + "=" * 60)
    if tous_ok:
        print(f"Résultat global : {len(NOUVEAUX_PROFILS)} profils testés, aucune incohérence détectée.")
    else:
        print("Résultat global : des incohérences ont été détectées, à corriger.")
