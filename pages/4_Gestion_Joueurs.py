"""
pages/4_Gestion_Joueurs.py
Gestion de l'effectif : ajout et suppression de joueurs.
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modules.database import get_players, add_player, delete_player

st.set_page_config(page_title="Gestion Joueurs", page_icon="⚙️", layout="wide")

st.title("⚙️ Gestion de l'effectif")

POSTES_RUGBY = [
    "Pilier gauche",
    "Talonneur",
    "Pilier droit",
    "2ème ligne gauche",
    "2ème ligne droit",
    "3ème ligne aile gauche",
    "3ème ligne aile droit",
    "3ème ligne centre",
    "Demi de mêlée",
    "Ouverture",
    "Ailier gauche",
    "Centre gauche",
    "Centre droit",
    "Ailier droit",
    "Arrière",
]

# ── LISTE DES JOUEURS ────────────────────────────────────────────────────────────
st.subheader("📋 Effectif actuel")
players_df = get_players()

if players_df.empty:
    st.info("Aucun joueur enregistré.")
else:
    # Affichage avec option de suppression
    for _, row in players_df.iterrows():
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        col1.markdown(f"**{row['prenom']} {row['nom']}**")
        col2.markdown(f"_{row['poste']}_")
        col3.markdown(f"N°{row['numero']}" if row['numero'] else "")
        if col4.button("🗑️ Supprimer", key=f"del_{row['id']}"):
            delete_player(row["id"])
            st.success(f"✅ {row['prenom']} {row['nom']} supprimé(e) (et toutes ses sessions).")
            st.rerun()

st.markdown(f"**Total : {len(players_df)} joueur(s)**")
st.markdown("---")

# ── AJOUT D'UN JOUEUR ────────────────────────────────────────────────────────────
st.subheader("➕ Ajouter un joueur")

with st.form("add_player_form"):
    col_a, col_b = st.columns(2)
    with col_a:
        prenom = st.text_input("Prénom *", placeholder="Antoine")
        poste  = st.selectbox("Poste *", POSTES_RUGBY)
    with col_b:
        nom    = st.text_input("Nom *", placeholder="Dupont")
        numero = st.number_input("Numéro de maillot", min_value=1, max_value=99, value=9)

    submitted = st.form_submit_button("➕ Ajouter le joueur", type="primary")

    if submitted:
        if not nom.strip() or not prenom.strip():
            st.error("Le nom et le prénom sont obligatoires.")
        else:
            add_player(nom.strip().upper(), prenom.strip().capitalize(), poste, numero)
            st.success(f"✅ {prenom.capitalize()} {nom.upper()} ajouté(e) au poste de {poste}.")
            st.rerun()

# ── IMPORT EN MASSE ──────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("📤 Import en masse (CSV)"):
    st.markdown("""
    Téléchargez un fichier CSV avec les colonnes : `nom`, `prenom`, `poste`, `numero`

    ```
    nom,prenom,poste,numero
    Dupont,Antoine,Demi de mêlée,9
    Ntamack,Romain,Ouverture,10
    ```
    """)
    uploaded_file = st.file_uploader("Choisir un fichier CSV", type="csv")
    if uploaded_file:
        import pandas as pd
        try:
            df_import = pd.read_csv(uploaded_file)
            required = {"nom", "prenom", "poste", "numero"}
            if not required.issubset(df_import.columns):
                st.error(f"Colonnes manquantes : {required - set(df_import.columns)}")
            else:
                st.dataframe(df_import, width='stretch')
                if st.button("✅ Confirmer l'import"):
                    for _, row in df_import.iterrows():
                        add_player(
                            str(row["nom"]).upper(),
                            str(row["prenom"]).capitalize(),
                            str(row["poste"]),
                            int(row["numero"]),
                        )
                    st.success(f"{len(df_import)} joueurs importés avec succès !")
                    st.rerun()
        except Exception as e:
            st.error(f"Erreur de lecture : {e}")
