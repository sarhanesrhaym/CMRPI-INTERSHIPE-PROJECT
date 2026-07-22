"""
profil.py
---------
Jalon 2 - Moteur de règles
Auteur : Fatima (J2)

Ce module contient les profils PME extraits du fichier
03_profils_pme.json (Jalon 1), sous forme de dictionnaires Python
directement utilisables par le moteur de règles.

Chaque profil correspond aux réponses données au questionnaire :
    - secteur
    - nb_employes
    - site_web
    - personne_it
    - employes_nomades
    - donnees_personnelles
"""

# ---------------------------------------------------------------------------
# Profil 1 : Boutique Zahra (exemple)
# Usage : Cas simple -> uniquement les recommandations universelles
# ---------------------------------------------------------------------------
profil_exemple001 = {
    "secteur": "Généraliste",
    "nb_employes": "moins de 10",
    "site_web": "Non",
    "personne_it": "Non",
    "employes_nomades": "Non",
    "donnees_personnelles": "Non"
}

# ---------------------------------------------------------------------------
# Profil 2 : Boutique en ligne ShopMaroc (exemple)
# Usage : Site web + données personnelles, sans IT dédié -> teste Q3 et Q6
# ---------------------------------------------------------------------------
profil_exemple002 = {
    "secteur": "E-commerce",
    "nb_employes": "10 à 50",
    "site_web": "Oui",
    "personne_it": "Non",
    "employes_nomades": "Non",
    "donnees_personnelles": "Oui"
}

# ---------------------------------------------------------------------------
# Profil 3 : Cabinet de change Rif Finance (exemple)
# Usage : Secteur sensible + IT dédié + mobilité -> teste Q1, Q4, Q5, Q6
# ---------------------------------------------------------------------------
profil_exemple003 = {
    "secteur": "Finance",
    "nb_employes": "10 à 50",
    "site_web": "Non",
    "personne_it": "Oui",
    "employes_nomades": "Oui",
    "donnees_personnelles": "Oui"
}

# ---------------------------------------------------------------------------
# Profil 4 : Cabinet médical MedCare (exemple)
# Usage : Données sensibles sans aucune ressource IT -> Q6 doit rester active
# ---------------------------------------------------------------------------
profil_exemple004 = {
    "secteur": "Santé",
    "nb_employes": "moins de 10",
    "site_web": "Non",
    "personne_it": "Non",
    "employes_nomades": "Non",
    "donnees_personnelles": "Oui"
}

# ---------------------------------------------------------------------------
# Profil 5 : Atelier textile Souss (exemple)
# Usage : Cas complet -> déclenche toute la grille (universelles + conditionnelles)
# ---------------------------------------------------------------------------
profil_exemple005 = {
    "secteur": "Industrie",
    "nb_employes": "plus de 50",
    "site_web": "Oui",
    "personne_it": "Oui",
    "employes_nomades": "Oui",
    "donnees_personnelles": "Oui"
}

# ---------------------------------------------------------------------------
# Regroupement de tous les profils dans un seul dictionnaire
# Clé = id du profil, Valeur = dictionnaire des réponses
# ---------------------------------------------------------------------------
PROFILS_EXEMPLE = {
    "exemple001": profil_exemple001,
    "exemple002": profil_exemple002,
    "exemple003": profil_exemple003,
    "exemple004": profil_exemple004,
    "exemple005": profil_exemple005,
}


def get_profil(profil_id: str) -> dict:
    """
    Retourne le dictionnaire de réponses d'un profil donné.

    Exemple :
        get_profil("exemple002")
        -> {
            "secteur": "E-commerce",
            "nb_employes": "10 à 50",
            "site_web": "Oui",
            "personne_it": "Non",
            "employes_nomades": "Non",
            "donnees_personnelles": "Oui"
        }
    """
    if profil_id not in PROFILS_EXEMPLE:
        raise ValueError(f"Profil inconnu : {profil_id}")
    return PROFILS_EXEMPLE[profil_id]


def liste_profils() -> list:
    """Retourne la liste des identifiants de profils disponibles."""
    return list(PROFILS_EXEMPLE.keys())


# ---------------------------------------------------------------------------
# Test rapide si le fichier est exécuté directement
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    for pid, profil in PROFILS_EXEMPLE.items():
        print(f"--- {pid} ---")
        print(profil)
        print()
