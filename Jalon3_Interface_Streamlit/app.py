# -*- coding: utf-8 -*-
"""
app.py — Interface Streamlit, Jalon 3 (refonte UI sobre et professionnelle)
============================================================================

J5 : refonte d'interface « application professionnelle de cybersécurité ».
UNIQUEMENT la couche présentation (HTML/CSS injecté) a été refondue.
La logique métier, le moteur de recommandation, les données et les calculs
restent STRICTEMENT IDENTIQUES.

Le moteur du Jalon 2 (`moteur/`) est réutilisé tel quel, sans être dupliqué ici.

Note technique importante : tout HTML injecté via st.markdown(...,
unsafe_allow_html=True) est construit SANS indentation au début des lignes.
Streamlit/Markdown interprète une ligne commençant par 4 espaces ou plus
comme un bloc de code, ce qui casse le rendu HTML.
"""

import base64
import html
import os
import sys

import streamlit as st

try:
    from export_pdf import generer_pdf
    PDF_DISPONIBLE = True
except ImportError:
    PDF_DISPONIBLE = False

# --- Connexion au moteur du Jalon 2, sans dupliquer le code -----------------

RACINE_PROJET = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATS_DOSSIER_MOTEUR = [
    os.path.join(RACINE_PROJET, "jalon-2-moteur", "moteur"),
    os.path.join(RACINE_PROJET, "moteur"),
]

DOSSIER_MOTEUR = next((c for c in CANDIDATS_DOSSIER_MOTEUR if os.path.isdir(c)), None)

if DOSSIER_MOTEUR is None:
    st.error(
        "Dossier `moteur/` introuvable.\n\n"
        "Chemins recherchés :\n" + "\n".join(f"- `{c}`" for c in CANDIDATS_DOSSIER_MOTEUR) + "\n\n"
        f"Contenu actuel de `{RACINE_PROJET}` : "
        f"{os.listdir(RACINE_PROJET) if os.path.isdir(RACINE_PROJET) else '(dossier parent introuvable)'}\n\n"
        "Vérifiez l'emplacement du dossier `moteur/` (contenant moteur.py, "
        "load_data.py, etc.)."
    )
    st.stop()

if DOSSIER_MOTEUR not in sys.path:
    sys.path.insert(0, DOSSIER_MOTEUR)

try:
    from moteur import recommander, grouper_par_solution  # noqa: E402
    from load_data import charger_donnees  # noqa: E402
except ModuleNotFoundError as e:
    st.error(
        f"Import du moteur échoué : {e}\n\n"
        f"Contenu de `{DOSSIER_MOTEUR}` : {os.listdir(DOSSIER_MOTEUR)}\n\n"
        "Vérifiez que moteur.py et load_data.py sont bien directement dans "
        "ce dossier (pas dans un sous-dossier supplémentaire)."
    )
    st.stop()


# --- Configuration de la page ------------------------------------------------

st.set_page_config(
    page_title="Recommandation cyber-résilience PME",
    page_icon="",
    layout="centered",
)


# --- Chargement de la feuille de style -------------------------------------

def charger_css():
    chemin_css = os.path.join(os.path.dirname(__file__), "assets", "style.css")
    with open(chemin_css, encoding="utf-8") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def _image_base64(nom_fichier):
    chemin = os.path.join(os.path.dirname(__file__), "assets", "logos", nom_fichier)
    if not os.path.isfile(chemin):
        return None
    with open(chemin, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


# =========================================================================
# HEADER — identité navy professionnelle
# =========================================================================

def afficher_entete():
    """
    En-tête avec identité visuelle navy. Logos CMRPI et EMC, titre de l'application.
    Aucun badge décoratif, aucun élément marketing.
    """
    logo_cmrpi = _image_base64("logo_cmrpi.png")
    logo_emc = _image_base64("logo_emc.png")

    logo_gauche = ""
    if logo_cmrpi:
        logo_gauche = f'<img src="data:image/png;base64,{logo_cmrpi}" class="logo-img" alt="Logo CMRPI">'
    else:
        logo_gauche = '<div class="header-logo-text">CMRPI</div>'

    logo_droite = ""
    if logo_emc:
        logo_droite = f'<img src="data:image/png;base64,{logo_emc}" class="logo-img" alt="Logo Espace Maroc Cyberconfiance">'

    bloc = (
        '<div class="app-header">'
        f'<div class="header-side">{logo_gauche}</div>'
        '<div class="header-center">'
        '<div class="header-title">Recommandation cyber-résilience pour PME</div>'
        '<div class="header-subtitle">CMRPI · AUSIM</div>'
        '</div>'
        f'<div class="header-side right">{logo_droite}</div>'
        '</div>'
    )
    st.markdown(bloc, unsafe_allow_html=True)


def afficher_introduction():
    """
    Introduction avec composition visuelle structurée :
    hero navy premium + badge + titre fort + description.
    """
    bloc = (
        '<div class="hero-section">'
        '<div class="hero-inner">'
        '<div class="hero-badge">Plateforme d\'évaluation</div>'
        '<h1 class="hero-title">Recommandation Cyber-Résilience <span class="hero-accent">pour PME</span></h1>'
        '<p class="hero-desc">Évaluez le profil de votre entreprise et obtenez '
        'des mesures de sécurité adaptées à vos principaux risques.</p>'
        '<div class="hero-divider"></div>'
        '</div>'
        '</div>'
    )
    st.markdown(bloc, unsafe_allow_html=True)


def afficher_pied_de_page():
    bloc = (
        '<div class="app-footer">Outil pédagogique CMRPI/AUSIM — Espace Maroc '
        'Cyberconfiance. Les recommandations sont générées à partir d\'un jeu '
        'de règles fixe, sans intelligence artificielle.</div>'
    )
    st.markdown(bloc, unsafe_allow_html=True)


# --- Chargement des données (mise en cache pour éviter de relire les JSON
#     à chaque interaction utilisateur) -------------------------------------

@st.cache_data
def get_donnees():
    return charger_donnees()


# --- Indicateur d'étapes ---------------------------------------------------

def afficher_etapes(etape_active):
    """
    Indicateur d'étapes sous forme de progress bar horizontale professionnelle.
    `etape_active` vaut 1 ou 2 — conservé tel quel.
    """
    classe_1 = "step active" if etape_active == 1 else "step"
    classe_2 = "step active" if etape_active == 2 else "step"

    bloc = (
        '<div class="stepper">'
        f'<div class="{classe_1}"><span class="step-num">01</span> Profil de votre PME</div>'
        '<div class="step-line"></div>'
        f'<div class="{classe_2}"><span class="step-num">02</span> Vos recommandations</div>'
        '</div>'
    )
    st.markdown(bloc, unsafe_allow_html=True)


def _afficher_titre_section(titre, legende=None):
    """Titre de section avec accent navu vertical."""
    legende_html = f'<p class="section-legend">{html.escape(legende)}</p>' if legende else ""
    bloc = (
        '<div class="section-head">'
        '<div class="section-accent"></div>'
        f'<h2 class="section-title">{html.escape(titre)}</h2>'
        f'{legende_html}'
        '</div>'
    )
    st.markdown(bloc, unsafe_allow_html=True)


# --- Formulaire ------------------------------------------------------------

def afficher_formulaire(donnees):
    """
    Formulaire des 6 questions de profilage, en disposition 2 colonnes.

    Les options de chaque question sont lues depuis donnees["questions"]
    (05_regles_recommandation.json) plutôt que codées en dur ici, pour
    ne jamais désynchroniser le formulaire des règles du moteur.

    La structure HTML autour du formulaire est modernisée (carte de
    configuration « Profil de votre organisation »), mais les 6 questions,
    leurs libellés et leurs valeurs restent STRICTEMENT IDENTIQUES.
    """
    _afficher_titre_section("Profil de votre PME",
                            "Répondez aux 6 questions ci-dessous pour recevoir vos recommandations.")

    questions = donnees["questions"]

    # Carte "Profil de votre organisation"
    st.markdown(
        '<div class="form-shell">'
        '<div class="form-head">'
        '<div class="form-title">Profil de votre organisation</div>'
        '<div class="form-desc">Informations générales utilisées pour personnaliser les recommandations.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.form("formulaire_profil"):
        # Section 1 — Activité
        st.markdown(
            '<div class="form-group">'
            '<div class="form-group-head">'
            '<div class="form-group-num">01</div>'
            '<div>'
            '<div class="form-group-title">Activité</div>'
            '<div class="form-group-desc">Secteur et taille de votre organisation</div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        col_gauche, col_droite = st.columns(2)

        with col_gauche:
            secteur = st.selectbox("Secteur d'activité", questions["secteur"]["options"])
        with col_droite:
            nb_employes = st.selectbox("Nombre d'employés", questions["nb_employes"]["options"])

        st.markdown('</div>', unsafe_allow_html=True)

        # Section 2 — Infrastructure
        st.markdown(
            '<div class="form-group">'
            '<div class="form-group-head">'
            '<div class="form-group-num">02</div>'
            '<div>'
            '<div class="form-group-title">Infrastructure</div>'
            '<div class="form-group-desc">Présence en ligne et ressources techniques</div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        col_gauche, col_droite = st.columns(2)

        with col_gauche:
            site_web = st.radio("Avez-vous un site web ?", ["Oui", "Non"], horizontal=True)
        with col_droite:
            personne_it = st.radio("Personne IT dédiée ?", ["Oui", "Non"], horizontal=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Section 3 — Données et mobilité
        st.markdown(
            '<div class="form-group">'
            '<div class="form-group-head">'
            '<div class="form-group-num">03</div>'
            '<div>'
            '<div class="form-group-title">Données et mobilité</div>'
            '<div class="form-group-desc">Accès distants et traitement des données</div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        col_gauche, col_droite = st.columns(2)

        with col_gauche:
            employes_nomades = st.radio(
                "Employés nomades (déplacements, télétravail) ?", ["Oui", "Non"], horizontal=True,
            )
        with col_droite:
            donnees_personnelles = st.radio("Données personnelles collectées ?", ["Oui", "Non"], horizontal=True)

        st.markdown('</div>', unsafe_allow_html=True)

        soumis = st.form_submit_button("Obtenir mes recommandations")

    # Fermeture de la carte "form-shell"
    st.markdown('</div>', unsafe_allow_html=True)

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


# =========================================================================
# RÉSULTATS — scorecards + cartes de recommandations
# =========================================================================

def afficher_scorecard(groupees):
    """
    Résumé des priorités en trois cartes KPI professionnelles.
    Les compteurs restent calculés à partir des recommandations générées
    par le moteur (aucune logique modifiée).
    """
    compte = {"Haute": 0, "Moyenne": 0, "Basse": 0}
    for g in groupees:
        compte[g["priorite"]] = compte.get(g["priorite"], 0) + 1

    blocs = []
    for label in ["Haute", "Moyenne", "Basse"]:
        blocs.append(
            f'<div class="summary-card {label.lower()}">'
            f'<div class="summary-label">Priorité {label}</div>'
            f'<div class="summary-number">{compte[label]}</div>'
            f'<div class="summary-unit">recommandation(s)</div>'
            f'</div>'
        )

    st.markdown(f'<div class="summary-grid">{"".join(blocs)}</div>', unsafe_allow_html=True)


def afficher_resultats(recommandations, profil):
    """
    Affichage des résultats retournés par moteur.recommander().
    Cartes en grille (CSS grid), groupées par priorité.
    """
    st.markdown('<div class="results-section">', unsafe_allow_html=True)

    _afficher_titre_section("Vos recommandations",
                            "Mesures de sécurité prioritaires adaptées au profil renseigné.")

    groupees = grouper_par_solution(recommandations)

    if not groupees:
        st.info("Aucune recommandation ne s'applique à ce profil.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    afficher_scorecard(groupees)

    nb_liens = len(recommandations)
    st.markdown(
        '<div class="recap-bar">'
        '<div class="recap-label">Résumé</div>'
        f'<div class="recap-text">{len(groupees)} solution(s) distincte(s) — {nb_liens} lien(s) risque/solution couvert(s) au total.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    for priorite in ["Haute", "Moyenne", "Basse"]:
        sous_groupe = [g for g in groupees if g["priorite"] == priorite]
        if not sous_groupe:
            continue

        classe_priorite = {
            "Haute": "high",
            "Moyenne": "medium",
            "Basse": "low",
        }.get(priorite, "high")

        cartes = []

        for g in sous_groupe:
            titre = html.escape(g["solution_nom"])
            desc = html.escape(g["solution_description"]) if g["solution_description"] else ""
            notes_html = "".join(
                f'<div class="solution-note">{html.escape(note)}</div>'
                for note in g["notes_adaptation"]
            )

            risques_tags = "".join(
                f'<span class="risk-tag">{html.escape(r.strip())}</span>'
                for r in g["risques_couverts"]
            )

            cartes.append(
                f'<div class="solution-card {classe_priorite}">'
                f'<div class="priority-label"><span class="priority-dot"></span>{priorite}</div>'
                f'<p class="solution-title">{titre}</p>'
                f'<p class="solution-desc">{desc}</p>'
                f'<div class="risk-label">Risque(s) couvert(s)</div>'
                f'<div class="risk-tags">{risques_tags}</div>'
                f'{notes_html}'
                f'</div>'
            )

        grille = f'<div class="solutions-grid">{"".join(cartes)}</div>'
        st.markdown(grille, unsafe_allow_html=True)

    afficher_export_pdf(profil, groupees)
    afficher_encart_contact()

    st.markdown('</div>', unsafe_allow_html=True)


def afficher_export_pdf(profil, groupees):
    """Bouton de téléchargement du rapport PDF des recommandations."""
    if not PDF_DISPONIBLE:
        st.caption(
            "Export PDF indisponible (module `reportlab` non installé — "
            "`pip install reportlab`)."
        )
        return

    pdf_bytes = generer_pdf(profil, groupees)

    # Icône SVG (téléchargement) — pas d'emoji
    icone_svg = (
        '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
        '<polyline points="7 10 12 15 17 10"/>'
        '<line x1="12" y1="15" x2="12" y2="3"/>'
        '</svg>'
    )

    st.markdown(
        f'<a class="btn-pdf" href="data:application/pdf;base64,{base64.b64encode(pdf_bytes).decode("ascii")}" '
        f'download="recommandations_cyber_resilience.pdf">{icone_svg} Télécharger le rapport PDF</a>',
        unsafe_allow_html=True,
    )


def afficher_encart_contact():
    """
    Section contact professionnelle. Coordonnées CMRPI/AUSIM
    conservées telles quelles.
    """
    bloc = (
        '<div class="help-section">'
        '<div class="help-title">Besoin d\'accompagnement ?</div>'
        '<div class="help-grid">'
        '<div class="help-left">'
        '<p>Le CMRPI et l\'Espace Maroc Cyberconfiance (AUSIM) peuvent vous '
        'accompagner dans la mise en place de ces mesures.</p>'
        '</div>'
        '<div class="help-right">'
        '<div class="help-item">'
        '<div class="help-item-label">Email</div>'
        '<div class="help-item-value">contact@cmrpi.ma</div>'
        '</div>'
        '<div class="help-item">'
        '<div class="help-item-label">Téléphone</div>'
        '<div class="help-item-value">(+ 212) 6 51 69 55 03</div>'
        '</div>'
        '<div class="help-item">'
        '<div class="help-item-label">Structure</div>'
        '<div class="help-item-value">CMRPI, BP 1474 CD Kénitra</div>'
        '</div>'
        '</div>'
        '</div>'
        '</div>'
    )
    st.markdown(bloc, unsafe_allow_html=True)


def main():
    charger_css()
    afficher_entete()
    afficher_introduction()

    donnees = get_donnees()

    if "profil" not in st.session_state:
        st.session_state.profil = None

    afficher_etapes(2 if st.session_state.profil is not None else 1)

    profil_saisi = afficher_formulaire(donnees)
    if profil_saisi is not None:
        st.session_state.profil = profil_saisi

    if st.session_state.profil is not None:
        resultats = recommander(st.session_state.profil, donnees=donnees)
        afficher_resultats(resultats, st.session_state.profil)

    afficher_pied_de_page()


if __name__ == "__main__":
    main()
