"""
pages/1_Saisie_Quotidienne.py
Formulaire de saisie quotidienne : RPE × Durée + bien-être.
Écrit simultanément dans SQLite (local) ET Google Sheets.
"""

import streamlit as st
from datetime import date
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modules.database import get_players, add_session
from modules.calculations import foster_load
from modules.gsheets import (
    append_saisie_row,
    update_rpe_indv,
    update_rpe_par_ligne_semaine,
    is_configured,
    init_sheets,
    JOURS_ENTRAINEMENT,
    RPE_LABELS,
)

st.set_page_config(page_title="Saisie Quotidienne", page_icon="📝", layout="centered")

st.title("Saisie Quotidienne")
st.markdown("Enregistrez la séance d'entraînement et le ressenti de chaque joueur.")

# ── Statut Google Sheets ────────────────────────────────────────────────────────
gsheets_ok = is_configured()

if gsheets_ok:
    st.success(
        "Google Sheets connecté — Les données seront enregistrées dans "
        "**Test - Suivi Charge RCA Amiens**"
    )
else:
    st.warning(
        "Google Sheets non configuré. Les données seront enregistrées "
        "**uniquement en local** (SQLite). "
        "Consultez l'onglet **Configuration Google Sheets** pour activer la synchronisation."
    )

# ── Chargement joueurs ──────────────────────────────────────────────────────────
players_df = get_players()

if players_df.empty:
    st.warning("Aucun joueur enregistré. Ajoutez des joueurs dans **Gestion des Joueurs**.")
    st.stop()

player_options = {
    f"{row['prenom']} {row['nom']} — {row['poste']}": {
        "id":    row["id"],
        "nom":   f"{row['nom']} {row['prenom']}",
        "poste": row["poste"],
    }
    for _, row in players_df.iterrows()
}


def _get_week_number(d) -> int:
    """Calcule le numéro de semaine ISO."""
    try:
        return d.isocalendar()[1]
    except Exception:
        return 1

# ── Formulaire ──────────────────────────────────────────────────────────────────
with st.form("saisie_form", clear_on_submit=True):

    col1, col2 = st.columns(2)
    with col1:
        selected_label = st.selectbox("Joueur", options=list(player_options.keys()))
    with col2:
        session_date = st.date_input("Date", value=date.today(), max_value=date.today())

    col_sem, col_jour = st.columns(2)
    with col_sem:
        semaine = st.number_input(
            "Numéro de semaine",
            min_value=1, max_value=52, value=_get_week_number(session_date),
            help="Numéro de semaine de la saison (1 = première semaine)",
        )
    with col_jour:
        jour = st.selectbox(
            "Jour d'entraînement",
            options=JOURS_ENTRAINEMENT,
            index=1,  # Mardi par défaut
            help="Correspond aux colonnes Mardi / Mercredi / Vendredi / Jour de match",
        )

    st.markdown("---")
    st.subheader("Charge de séance")

    col3, col4, col5 = st.columns(3)
    with col3:
        rpe = st.select_slider(
            "RPE — Perception de l'effort (Borg CR-10)",
            options=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            value=5,
            format_func=lambda x: RPE_LABELS.get(x, str(x)),
        )
    with col4:
        duration = st.number_input(
            "Durée (minutes)", min_value=0, max_value=300, value=75, step=5
        )
    with col5:
        load = foster_load(rpe, duration)
        st.metric("Charge Foster (UA)", f"{load:.0f}")
        st.caption("RPE x Durée")

    st.markdown("---")
    st.subheader("Etat de bien-être")
    st.caption("1 = très mauvais · 5 = excellent")

    col6, col7, col8 = st.columns(3)
    with col6:
        fatigue = st.select_slider(
            "Fatigue générale",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: {1: "1 — Épuisé", 2: "2 — Fatigué",
                                    3: "3 — Normal", 4: "4 — Bien", 5: "5 — Excellent"}[x],
        )
    with col7:
        courbatures = st.select_slider(
            "Courbatures / douleurs",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: {1: "1 — Très douloureux", 2: "2 — Douloureux",
                                    3: "3 — Légères", 4: "4 — Minimes", 5: "5 — Aucune"}[x],
        )
    with col8:
        sommeil = st.select_slider(
            "Qualité du sommeil",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: {1: "1 — Très mauvais", 2: "2 — Mauvais",
                                    3: "3 — Moyen", 4: "4 — Bon", 5: "5 — Excellent"}[x],
        )

    avg_well = (fatigue + courbatures + sommeil) / 3
    well_color = (
        "OK" if avg_well >= 4 else
        "Correct" if avg_well >= 3 else
        "Dégradé" if avg_well >= 2 else
        "ALERTE"
    )
    st.markdown(f"**Score bien-être moyen :** **{avg_well:.1f} / 5** ({well_color})")

    st.markdown("---")
    notes = st.text_area(
        "Notes / Observations (optionnel)",
        placeholder="Ex: séance terrain, match amical, blessure légère...",
        height=80,
    )

    is_rest_day = st.checkbox(
        "Jour de repos (charge = 0, mais enregistrer le bien-être)",
        value=False,
    )

    submitted = st.form_submit_button(
        "Enregistrer la séance", type="primary", width='stretch'
    )


# ── Traitement à la validation ──────────────────────────────────────────────────
if submitted:
    player_info     = player_options[selected_label]
    player_id       = player_info["id"]
    nom_prenom      = player_info["nom"]
    poste           = player_info["poste"]

    actual_rpe      = 0 if is_rest_day else rpe
    actual_duration = 0 if is_rest_day else duration
    actual_load     = 0.0 if is_rest_day else load

    # 1. Enregistrement SQLite local (toujours)
    add_session(
        player_id=player_id,
        session_date=str(session_date),
        rpe=actual_rpe,
        duration=actual_duration,
        foster_load=actual_load,
        fatigue=fatigue,
        courbatures=courbatures,
        sommeil=sommeil,
        notes=notes,
    )

    # 2. Enregistrement Google Sheets (si configuré)
    gs_success = False
    if gsheets_ok:
        with st.spinner("Synchronisation Google Sheets..."):
            # Initialisation des onglets si première utilisation
            init_sheets()

            # Onglet Saisies → nouvelle ligne
            ok1 = append_saisie_row(
                nom_prenom=nom_prenom,
                poste=poste,
                semaine=int(semaine),
                jour=jour,
                rpe=actual_rpe,
                duree=actual_duration,
                charge=actual_load,
                fatigue=fatigue,
                courbatures=courbatures,
                sommeil=sommeil,
                notes=notes,
                is_rest=is_rest_day,
            )

            # Onglet RPE INDV → mise à jour cellule
            ok2 = True
            if not is_rest_day and jour in ["Mardi", "Mercredi", "Vendredi", "Jour de match"]:
                ok2 = update_rpe_indv(
                    nom_prenom=nom_prenom,
                    poste=poste,
                    semaine=int(semaine),
                    jour=jour,
                    rpe=actual_rpe,
                    duree=actual_duration,
                    charge=actual_load,
                )

            # Onglet RPE PAR LIGNE SEMAINE → agrégats par poste
            ok3 = True
            if not is_rest_day:
                ok3 = update_rpe_par_ligne_semaine(
                    poste=poste,
                    semaine=int(semaine),
                    nom_prenom=nom_prenom,
                    rpe=actual_rpe,
                    duree=actual_duration,
                    charge=actual_load,
                )

            gs_success = ok1 and ok2 and ok3

    # 3. Messages de confirmation
    if is_rest_day:
        msg = f"Jour de repos enregistré pour **{selected_label}** le {session_date}."
    else:
        msg = (
            f"Séance enregistrée pour **{selected_label}** — "
            f"Semaine {semaine}, {jour} — "
            f"Charge : **{actual_load:.0f} UA** (RPE {actual_rpe} x {actual_duration} min)"
        )
    st.success(msg)

    if gsheets_ok:
        if gs_success:
            st.info(
                f"Google Sheets mis à jour : onglets **Saisies** + **RPE INDV** + **RPE PAR LIGNE SEMAINE**"
            )
        else:
            st.warning("Enregistrement local OK, mais erreur lors de la synchronisation Google Sheets.")

    if avg_well <= 2.5:
        st.warning(f"Score bien-être faible ({avg_well:.1f}/5). Pensez à adapter la charge.")

# ── Aide RPE ────────────────────────────────────────────────────────────────────
with st.expander("Echelle RPE de Borg CR-10"):
    st.markdown("""
    | RPE | Description |
    |-----|-------------|
    | 0   | Repos complet |
    | 1   | Très très facile |
    | 2   | Très facile |
    | 3   | Facile |
    | 4   | Effort modéré |
    | 5   | Effort moyen |
    | 6   | Effort un peu difficile |
    | 7   | Difficile |
    | 8   | Très difficile |
    | 9   | Très très difficile |
    | 10  | Maximal |
    """)
