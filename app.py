"""
Rugby Training Load — Application principale
Point d'entrée Streamlit avec page d'accueil et navigation.
"""

import streamlit as st
from modules.database import init_db

# ── Configuration globale ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Rugby Training Load",
    page_icon="🏉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialisation base de données au démarrage
init_db()

# ── Page d'accueil ─────────────────────────────────────────────────────────────
st.title("🏉 Rugby Training Load Manager")
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.info(
        """
        ### 📝 Saisie Quotidienne
        Enregistrez la charge de séance (RPE × Durée)
        et l'état de bien-être de chaque joueur.
        """
    )

with col2:
    st.success(
        """
        ### 👤 Tableau Individuel
        Visualisez la charge aiguë/chronique (ACWR),
        la monotonie, la contrainte et le bien-être d'un joueur.
        """
    )

with col3:
    st.warning(
        """
        ### 👥 Tableau Collectif
        Heatmap de l'ACWR pour tout l'effectif.
        Identifiez rapidement les joueurs à risque.
        """
    )

st.markdown("---")
st.markdown(
    """
    #### 📊 Indicateurs calculés automatiquement

    | Indicateur | Formule | Interprétation |
    |---|---|---|
    | **Charge Foster** | RPE × Durée (min) | Charge de séance en UA |
    | **Charge aiguë** | Moyenne 7 jours | Fatigue court terme |
    | **Charge chronique** | Moyenne 28 jours | Forme long terme |
    | **ACWR** | Aiguë / Chronique | Ratio risque blessure |
    | **Monotonie** | Moyenne / Écart-type (7j) | Variabilité des séances |
    | **Contrainte** | Charge hebdo × Monotonie | Stress cumulé |

    #### 🎨 Zones ACWR
    🟢 **0.8 – 1.3** → Zone optimale &nbsp;&nbsp;
    🟠 **1.3 – 1.5** → Vigilance &nbsp;&nbsp;
    🔴 **> 1.5** → Risque blessure élevé &nbsp;&nbsp;
    🔵 **< 0.8** → Sous-charge
    """
)

st.markdown("---")
st.caption("Développé avec Streamlit · Données stockées localement (SQLite) · v1.0")
