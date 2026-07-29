from __future__ import annotations
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

"""
estimations.py — Module d'enrichissement des données (pas un des 6 algorithmes)
=================================================================================

Rôle dans le pipeline :
    scoring.py attend sur chaque solution des champs numériques
    (efficacite, cout_estimation, facilite_implementation,
    prerequis_infrastructure, roi_estime, complexite) et sur chaque
    profil un champ budget_disponible. AUCUN de ces champs n'existe
    dans 02_solutions.json / 03_profils_pme.json — les guides sources
    ne fournissent que des échelles qualitatives (Faible/Moyenne/Élevée)
    ou rien du tout selon les cas.

    Ce module les calcule à partir de ce qui existe réellement (type de
    solution, texte de prérequis/difficultés, efficacité qualitative
    dans la matrice risques-solutions, taille et budget_cyber_dedie du
    profil), et les documente explicitement comme des ESTIMATIONS DE
    TRAVAIL, jamais des données sourcées.

Choix méthodologique important — pas de MAD inventés :
    cout_estimation et budget_disponible ne sont PAS des montants en
    dirhams. C'est une échelle abstraite 0-100 ("points de coût" /
    "points de capacité budgétaire"), cohérente en interne pour faire
    fonctionner le ratio de scoring.score_faisabilite_budgetaire, mais
    qui ne doit JAMAIS être présentée comme un chiffrage réel dans le
    rapport de stage. C'est la même logique de transparence que celle
    déjà appliquée dans exposition.py (échelle 0-1 pour severite/probabilite).

Chaque fonction ci-dessous documente sa règle de calcul. Ces règles sont
volontairement simples et doivent être présentées à l'encadrante comme
des hypothèses de travail, pas des résultats validés.
"""

# ------------------------------------------------------------------
# 1. EFFICACITÉ intrinsèque (0-100)
#    Calculée à partir de la matrice risques-solutions (04), pas
#    inventée : moyenne des efficacités qualitatives (Élevée/Moyenne/
#    Faible) trouvées pour cette solution, tous risques confondus.
# ------------------------------------------------------------------

POIDS_EFFICACITE_QUALITATIVE = {"Élevée": 85, "Moyenne": 55, "Faible": 25}
EFFICACITE_PAR_DEFAUT = 50.0  # si la solution n'apparaît dans aucune entrée de la matrice


def _calculer_efficacite_intrinseque(matrice: Dict[str, Any]) -> Dict[str, float]:
    """Retourne {solution_id: efficacite_moyenne_0_100} à partir de 04_matrice_risques_solutions.json."""
    valeurs: Dict[str, List[float]] = {}
    for entree_risque in matrice.values():
        for sol in entree_risque.get("solutions", []):
            sid = sol.get("solution_id")
            eff = POIDS_EFFICACITE_QUALITATIVE.get(sol.get("efficacite"))
            if sid is None or eff is None:
                continue
            valeurs.setdefault(sid, []).append(eff)
    return {sid: round(sum(v) / len(v), 1) for sid, v in valeurs.items()}


# ------------------------------------------------------------------
# 2. COÛT (échelle abstraite 0-100, PAS des MAD) et COMPLEXITÉ
#    Priorité au champ cout_estime qualitatif existant (33/119
#    solutions) ; sinon inféré du type.
# ------------------------------------------------------------------

COUT_QUALITATIF_VERS_SCORE = {"Faible": 15, "Moyen": 45, "Élevé": 80}

COUT_PAR_TYPE_SI_ABSENT = {
    "Humain": 10, "Organisationnel": 20, "Légal": 30, "Légale": 30,
    "Financier": 35, "Physique": 50, "Technique": 45,
}
COUT_DEFAUT = 45  # type inconnu ou composite non reconnu


def _types_de(solution: Dict[str, Any]) -> List[str]:
    return [t.strip() for t in str(solution.get("type", "")).split("/") if t.strip()]


def _estimer_cout(solution: Dict[str, Any]) -> float:
    cout_qualitatif = solution.get("cout_estime")
    if cout_qualitatif in COUT_QUALITATIF_VERS_SCORE:
        return float(COUT_QUALITATIF_VERS_SCORE[cout_qualitatif])
    types = _types_de(solution)
    if not types:
        return float(COUT_DEFAUT)
    scores = [COUT_PAR_TYPE_SI_ABSENT.get(t, COUT_DEFAUT) for t in types]
    return round(sum(scores) / len(scores), 1)


FACILITE_PAR_TYPE = {
    "Humain": 85, "Organisationnel": 70, "Légal": 55, "Légale": 55,
    "Financier": 55, "Technique": 50, "Physique": 45,
}
FACILITE_DEFAUT = 60


def _estimer_facilite_implementation(solution: Dict[str, Any]) -> float:
    types = _types_de(solution)
    if not types:
        return float(FACILITE_DEFAUT)
    scores = [FACILITE_PAR_TYPE.get(t, FACILITE_DEFAUT) for t in types]
    return round(sum(scores) / len(scores), 1)


MOTS_CLES_INFRASTRUCTURE = ["serveur", "infrastructure", "cloud", "réseau dédié",
                            "administrateur", "hébergement", "vpn", "antivirus", "pare-feu"]


def _texte(champ) -> str:
    if isinstance(champ, list):
        return " ".join(str(x) for x in champ).lower()
    return str(champ or "").lower()


def _estimer_prerequis_infrastructure(solution: Dict[str, Any]) -> List[str]:
    """Extrait, depuis le texte libre de 'prerequis', les mots-clés d'infrastructure
    reconnus. Liste vide = aucun prérequis technique identifié (score_infrastructure
    de scoring.py renverra alors 100, ce qui est le comportement voulu)."""
    texte = _texte(solution.get("prerequis"))
    return [mc for mc in MOTS_CLES_INFRASTRUCTURE if mc in texte]


MOTS_CLES_COMPLEXITE = ["juridique", "audit", "expertise", "résistance", "cartographie", "long"]


def _estimer_complexite(solution: Dict[str, Any]) -> str:
    """faible / moyenne / elevee / tres_elevee, cohérent avec MALUS_COMPLEXITE de scoring.py."""
    nb_types = len(_types_de(solution))
    if nb_types <= 1:
        niveau = 0  # faible
    elif nb_types == 2:
        niveau = 1  # moyenne
    else:
        niveau = 2  # elevee

    texte_difficultes = _texte(solution.get("difficultes"))
    if any(mc in texte_difficultes for mc in MOTS_CLES_COMPLEXITE):
        niveau = min(niveau + 1, 3)

    return ["faible", "moyenne", "elevee", "tres_elevee"][niveau]


def _estimer_roi(efficacite: float, cout: float) -> float:
    """Proxy 'valeur pour l'argent' : haute efficacité + faible coût = ROI élevé.
    Pas un ROI financier réel (aucune donnée de perte évitée en MAD disponible)."""
    return round((efficacite + (100 - cout)) / 2, 1)


def enrichir_solutions(solutions_db: Dict[str, Any], matrice: Dict[str, Any]) -> Dict[str, Any]:
    """Retourne une COPIE de solutions_db avec les champs estimés ajoutés.
    Ne modifie jamais 02_solutions.json sur disque."""
    efficacites = _calculer_efficacite_intrinseque(matrice)
    resultat: Dict[str, Any] = {}
    nb_sans_matrice = 0

    for sid, solution in solutions_db.items():
        sol_enrichie = dict(solution)

        efficacite = efficacites.get(sid)
        if efficacite is None:
            efficacite = EFFICACITE_PAR_DEFAUT
            nb_sans_matrice += 1

        cout = _estimer_cout(solution)
        sol_enrichie["efficacite"] = efficacite
        sol_enrichie["cout_estimation"] = cout
        sol_enrichie["facilite_implementation"] = _estimer_facilite_implementation(solution)
        sol_enrichie["prerequis_infrastructure"] = _estimer_prerequis_infrastructure(solution)
        sol_enrichie["complexite"] = _estimer_complexite(solution)
        sol_enrichie["roi_estime"] = _estimer_roi(efficacite, cout)
        sol_enrichie["_champs_estimes"] = [
            "efficacite", "cout_estimation", "facilite_implementation",
            "prerequis_infrastructure", "complexite", "roi_estime",
        ]

        resultat[sid] = sol_enrichie

    if nb_sans_matrice:
        logger.warning(
            "%d/%d solutions absentes de la matrice risques-solutions : "
            "efficacite par defaut (%.0f) appliquee.",
            nb_sans_matrice, len(solutions_db), EFFICACITE_PAR_DEFAUT,
        )

    return resultat


# ------------------------------------------------------------------
# 3. BUDGET DISPONIBLE par profil (échelle abstraite 0-100, PAS des MAD)
#    Basé sur nb_employes (proxy de taille/moyens) et budget_cyber_dedie
#    (seule donnée budgétaire réellement présente dans les profils).
# ------------------------------------------------------------------

def _capacite_budgetaire_base(nb_employes: int) -> float:
    if nb_employes < 15:
        return 40.0
    if nb_employes <= 50:
        return 55.0
    if nb_employes <= 100:
        return 70.0
    return 85.0


FACTEUR_SANS_BUDGET_DEDIE = 0.4  # réduction si budget_cyber_dedie est False


def _estimer_budget_disponible(profil: Dict[str, Any]) -> float:
    try:
        nb_employes = int(profil.get("nb_employes", 0))
    except (TypeError, ValueError):
        nb_employes = 0
    base = _capacite_budgetaire_base(nb_employes)
    if not profil.get("budget_cyber_dedie", False):
        base *= FACTEUR_SANS_BUDGET_DEDIE
    return round(base, 1)


def enrichir_profils(profils_db: Dict[str, Any]) -> Dict[str, Any]:
    """Retourne une COPIE de profils_db avec budget_disponible ajouté.
    Ne modifie jamais 03_profils_pme.json sur disque."""
    resultat: Dict[str, Any] = {}
    for pid, profil in profils_db.items():
        profil_enrichi = dict(profil)
        profil_enrichi["budget_disponible"] = _estimer_budget_disponible(profil)
        profil_enrichi["_champs_estimes"] = ["budget_disponible"]
        resultat[pid] = profil_enrichi
    return resultat


if __name__ == "__main__":
    import argparse
    from filtrage import charger_donnees

    parser = argparse.ArgumentParser(description="Module d'enrichissement estimations.py")
    parser.add_argument("--dossier", default="../data")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="[estimations] %(levelname)s: %(message)s")

    data = charger_donnees(args.dossier)
    solutions_enrichies = enrichir_solutions(data["solutions"], data["matrice"])
    profils_enrichis = enrichir_profils(data["profils"])

    print("=== Exemple sur 3 solutions ===")
    for sid in list(solutions_enrichies.keys())[:3]:
        s = solutions_enrichies[sid]
        print(f"{sid} - {s['nom'][:40]:40s} "
              f"eff={s['efficacite']:.0f} cout={s['cout_estimation']:.0f} "
              f"facilite={s['facilite_implementation']:.0f} roi={s['roi_estime']:.0f} "
              f"complexite={s['complexite']} infra_prereq={s['prerequis_infrastructure']}")

    print("\n=== Budget disponible (echelle abstraite 0-100, PAS des MAD) sur 5 profils ===")
    for pid in list(profils_enrichis.keys())[:5]:
        p = profils_enrichis[pid]
        print(f"{pid} - {p['nom']:30s} nb_employes={p['nb_employes']:>4} "
              f"budget_dedie={p['budget_cyber_dedie']!s:5s} -> budget_disponible={p['budget_disponible']}")
