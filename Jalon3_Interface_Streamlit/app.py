# -*- coding: utf-8 -*-



import os
import sys

import streamlit as st


RACINE_PROJET = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER_MOTEUR = os.path.join(RACINE_PROJET, "moteur")
if DOSSIER_MOTEUR not in sys.path:
    sys.path.insert(0, DOSSIER_MOTEUR)

from moteur import recommander, grouper_par_solution  # noqa: E402
from load_data import charger_donnees  # noqa: E402


# --- Configuration de la page ----------------------------------------------

st.set_page_config(
    page_title="Recommandation cyber-résilience PME",
    page_icon="🛡️",
    layout="centered",
)


# --- Chargement des données (mise en cache pour éviter de relire les JSON
#     à chaque interaction utilisateur) -------------------------------------

@st.cache_data
def get_donnees():
    return charger_donnees()


def afficher_formulaire(donnees):

    st.subheader("Profil de votre PME")

    questions = donnees["questions"]

    with st.form("formulaire_profil"):
        secteur = st.selectbox("Secteur d'activité", questions["secteur"]["options"])
        nb_employes = st.selectbox("Nombre d'employés", questions["nb_employes"]["options"])
        site_web = st.radio("Avez-vous un site web ?", ["Oui", "Non"], horizontal=True)
        personne_it = st.radio("Avez-vous une personne IT dédiée ?", ["Oui", "Non"], horizontal=True)
        employes_nomades = st.radio("Avez-vous des employés nomades (déplacements, télétravail) ?", ["Oui", "Non"], horizontal=True)
        donnees_personnelles = st.radio("Collectez-vous des données personnelles ?", ["Oui", "Non"], horizontal=True)

        soumis = st.form_submit_button("Obtenir mes recommandations")

    if not soumis:
        return None

    return {
        "secteur": secteur,
        "nb_employes": nb_employes,
        "site_web": site_web,
        "personne_it": personne_it,
        "employes_nomades": employes_nomades,
        "donnees_personnelles": donnees_personnelles,
    }


PRIORITE_COULEUR = {
    "Haute": "🔴",
    "Moyenne": "🟠",
    "Basse": "🟢",
}


def afficher_resultats(recommandations):
  
    st.subheader("Vos recommandations")

    groupees = grouper_par_solution(recommandations)

    if not groupees:
        st.write("Aucune recommandation ne s'applique à ce profil.")
        return

    nb_liens = len(recommandations)
    st.caption(f"{len(groupees)} solution(s) distincte(s) — {nb_liens} lien(s) risque/solution couvert(s) au total.")

    for priorite in ["Haute", "Moyenne", "Basse"]:
        sous_groupe = [g for g in groupees if g["priorite"] == priorite]
        if not sous_groupe:
            continue
        st.markdown(f"### {PRIORITE_COULEUR.get(priorite, '')} Priorité {priorite}")
        for g in sous_groupe:
            with st.expander(g["solution_nom"]):
                if g["solution_description"]:
                    st.write(g["solution_description"])
                st.write("**Risque(s) couvert(s) :** " + ", ".join(g["risques_couverts"]))
                for note in g["notes_adaptation"]:
                    st.warning(note)


def main():
    st.title("🛡️ Recommandation cyber-résilience pour PME")
    st.caption(
        "CMRPI / Espace Maroc Cyberconfiance — basé sur le guide CMRPI/AUSIM."
    )

    donnees = get_donnees()

    profil = afficher_formulaire(donnees)

    if profil is not None:
        resultats = recommander(profil, donnees=donnees)
        afficher_resultats(resultats)


if __name__ == "__main__":
    main()
