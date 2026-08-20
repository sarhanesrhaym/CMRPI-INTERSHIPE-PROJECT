# -*- coding: utf-8 -*-
"""
export_pdf.py — Génère un rapport PDF des recommandations pour une PME.

Ajout demandé au J4 : permettre à un dirigeant de télécharger/imprimer/
partager ses recommandations avec un prestataire IT, plutôt que de
rester coincé dans le navigateur.

Nécessite reportlab : pip install reportlab
"""

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

COULEUR_PRIMAIRE = colors.HexColor("#243491")
COULEUR_HAUTE = colors.HexColor("#D92B32")
COULEUR_MOYENNE = colors.HexColor("#5B65B0")
COULEUR_BASSE = colors.HexColor("#00864B")

COULEURS_PRIORITE = {
    "Haute": COULEUR_HAUTE,
    "Moyenne": COULEUR_MOYENNE,
    "Basse": COULEUR_BASSE,
}

LABELS_PROFIL = {
    "secteur": "Secteur d'activité",
    "nb_employes": "Nombre d'employés",
    "site_web": "Site web",
    "personne_it": "Personne IT dédiée",
    "employes_nomades": "Employés nomades",
    "donnees_personnelles": "Données personnelles collectées",
}


def generer_pdf(profil, groupees):
    """
    Construit un rapport PDF à partir d'un profil (dict des 6 réponses)
    et des recommandations déjà groupées par solution (sortie de
    moteur.grouper_par_solution). Retourne les octets du PDF, prêts à
    être passés à st.download_button.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=20 * mm, bottomMargin=18 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
    )

    styles = getSampleStyleSheet()
    style_titre = ParagraphStyle(
        "TitrePrincipal", parent=styles["Title"],
        textColor=COULEUR_PRIMAIRE, fontSize=18, spaceAfter=4,
    )
    style_soustitre = ParagraphStyle(
        "SousTitre", parent=styles["Normal"],
        textColor=colors.HexColor("#5B607A"), fontSize=9, spaceAfter=14,
    )
    style_section = ParagraphStyle(
        "Section", parent=styles["Heading2"],
        textColor=COULEUR_PRIMAIRE, fontSize=13, spaceBefore=14, spaceAfter=8,
    )
    style_solution = ParagraphStyle(
        "Solution", parent=styles["Heading3"],
        fontSize=11, spaceBefore=8, spaceAfter=2,
    )
    style_corps = ParagraphStyle(
        "Corps", parent=styles["Normal"], fontSize=9.5, leading=13,
    )
    style_note = ParagraphStyle(
        "Note", parent=styles["Normal"], fontSize=9, leading=12,
        textColor=colors.HexColor("#8A1418"), spaceBefore=3,
    )

    elements = []

    elements.append(Paragraph("Recommandations cyber-résilience pour PME", style_titre))
    elements.append(Paragraph(
        f"Généré le {date.today().strftime('%d/%m/%Y')} — CMRPI/AUSIM, "
        "Espace Maroc Cyberconfiance",
        style_soustitre,
    ))

    # Tableau récapitulatif du profil
    lignes_profil = [[LABELS_PROFIL.get(cle, cle), str(valeur)] for cle, valeur in profil.items()]
    table_profil = Table(lignes_profil, colWidths=[65 * mm, 100 * mm])
    table_profil.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), COULEUR_PRIMAIRE),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#E4E6F2")),
    ]))
    elements.append(table_profil)
    elements.append(Spacer(1, 10))

    for priorite in ["Haute", "Moyenne", "Basse"]:
        sous_groupe = [g for g in groupees if g["priorite"] == priorite]
        if not sous_groupe:
            continue

        elements.append(Paragraph(f"Priorité {priorite} ({len(sous_groupe)})", style_section))

        for g in sous_groupe:
            elements.append(Paragraph(g["solution_nom"], style_solution))
            if g["solution_description"]:
                elements.append(Paragraph(g["solution_description"], style_corps))
            elements.append(Paragraph(
                f"<b>Risque(s) couvert(s) :</b> {', '.join(g['risques_couverts'])}",
                style_corps,
            ))
            for note in g["notes_adaptation"]:
                elements.append(Paragraph(f"⚠ {note}", style_note))

    elements.append(Spacer(1, 16))
    elements.append(Paragraph(
        "Outil pédagogique CMRPI/AUSIM — Espace Maroc Cyberconfiance. "
        "Les recommandations sont générées à partir d'un jeu de règles "
        "fixe, sans intelligence artificielle.",
        style_soustitre,
    ))

    doc.build(elements)
    return buffer.getvalue()