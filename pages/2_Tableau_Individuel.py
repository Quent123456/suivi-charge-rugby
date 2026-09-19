"""
pages/2_Tableau_Individuel.py
Dashboard individuel : KPI, alertes ACWR, graphiques évolution + bien-être.
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modules.database import get_players, get_sessions
from modules.calculations import (
    acute_load, chronic_load, acwr, monotony, strain,
    wellness_score, compute_rolling_metrics,
)
from modules.alerts import acwr_alert, monotony_alert, wellness_alert, strain_alert
from modules.visualizations import (
    plot_load_evolution, plot_wellness_radar,
    plot_acwr_gauge, plot_wellness_history,
)

st.set_page_config(page_title="Tableau Individuel", page_icon="👤", layout="wide")

st.title("👤 Tableau de bord individuel")

# ── Sélection joueur ────────────────────────────────────────────────────────────
players_df = get_players()

if players_df.empty:
    st.warning("Aucun joueur. Ajoutez des joueurs dans **Gestion des Joueurs**.")
    st.stop()

player_options = {
    f"{row['prenom']} {row['nom']} — {row['poste']}": row["id"]
    for _, row in players_df.iterrows()
}

col_sel1, col_sel2 = st.columns([2, 1])
with col_sel1:
    selected_label = st.selectbox("Sélectionner un joueur", list(player_options.keys()))
with col_sel2:
    period = st.selectbox("Période d'analyse", [28, 42, 56, 84], index=0,
                          format_func=lambda x: f"{x} derniers jours")

player_id = player_options[selected_label]
player_name = selected_label.split(" —")[0]

# ── Chargement données ──────────────────────────────────────────────────────────
df_raw = get_sessions(player_id, days=max(period, 35))

if df_raw.empty or df_raw["foster_load"].sum() == 0:
    st.info(f"Aucune séance enregistrée pour {player_name}. Commencez par la **Saisie Quotidienne**.")
    st.stop()

df = compute_rolling_metrics(df_raw)
df_period = df.tail(period)

# Calculs actuels (snapshot dernier jour avec données)
last = df[df["foster_load"] > 0]
loads = df["foster_load"]

a     = acute_load(loads, 7)
c     = chronic_load(loads, 28)
ratio = acwr(a, c)
mono  = monotony(loads, 7)
st_   = strain(loads, 7)

# Bien-être moyen 7 derniers jours
well_recent = df.tail(7).dropna(subset=["fatigue", "courbatures", "sommeil"])
avg_well = (
    wellness_score(
        well_recent["fatigue"].mean(),
        well_recent["courbatures"].mean(),
        well_recent["sommeil"].mean(),
    ) if not well_recent.empty else None
)

# ── ALERTES ─────────────────────────────────────────────────────────────────────
alert     = acwr_alert(ratio)
em_mono, msg_mono  = monotony_alert(mono)
em_well, msg_well  = wellness_alert(avg_well)
em_st, msg_st      = strain_alert(st_)

# Bannière d'alerte principale
if alert.level == "danger":
    st.error(f"{alert.emoji} **ALERTE RISQUE** — {alert.message}")
elif alert.level == "warning":
    st.warning(f"{alert.emoji} **Vigilance** — {alert.message}")
elif alert.level == "underload":
    st.info(f"{alert.emoji} **{alert.label}** — {alert.message}")
else:
    st.success(f"{alert.emoji} **{alert.label}** — {alert.message}")

st.markdown("---")

# ── KPI CARDS ───────────────────────────────────────────────────────────────────
st.subheader("📊 Indicateurs clés")

k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("⚡ Charge aiguë 7j", f"{a:.0f} UA",
          help="Charge moyenne des 7 derniers jours")
k2.metric("📈 Charge chronique 28j", f"{c:.0f} UA",
          help="Charge moyenne des 28 derniers jours")
k3.metric(
    "⚖️ ACWR",
    f"{ratio:.2f}" if ratio else "N/A",
    delta=f"{ratio - 1.0:+.2f}" if ratio else None,
    delta_color="inverse" if ratio and ratio > 1 else "normal",
    help="Optimal : 0.8 – 1.3",
)
k4.metric("🔁 Monotonie", f"{mono:.2f}" if mono else "N/A",
          help="< 1.5 : bonne variabilité | > 2.0 : ⚠️")
k5.metric("🔥 Contrainte", f"{st_:.0f} UA",
          help="Charge hebdo × Monotonie. Seuil : 6000")
k6.metric("😴 Bien-être /5", f"{avg_well:.1f}" if avg_well else "N/A",
          help="Moyenne fatigue + courbatures + sommeil (7j)")

st.markdown("---")

# ── GRAPHIQUES ──────────────────────────────────────────────────────────────────
st.subheader("📉 Évolution de la charge")

col_g1, col_g2 = st.columns([3, 1])
with col_g1:
    fig_load = plot_load_evolution(df_period, player_name)
    st.plotly_chart(fig_load, width='stretch')
with col_g2:
    fig_gauge = plot_acwr_gauge(ratio, player_name)
    st.plotly_chart(fig_gauge, width='stretch')

    # Alertes textuelles compactes
    st.markdown(f"{em_mono} {msg_mono}")
    st.markdown(f"{em_st} {msg_st}")

st.markdown("---")
st.subheader("😴 Bien-être")

col_w1, col_w2 = st.columns(2)
with col_w1:
    fig_radar = plot_wellness_radar(df_period, player_name)
    st.plotly_chart(fig_radar, width='stretch')
with col_w2:
    fig_hist = plot_wellness_history(df_period, player_name)
    st.plotly_chart(fig_hist, width='stretch')

st.markdown(f"**Bilan bien-être :** {em_well} {msg_well}")

# ── TABLEAU DES DONNÉES BRUTES ──────────────────────────────────────────────────
st.markdown("---")
with st.expander("📋 Données brutes — Sessions"):
    display_df = df_period[["session_date", "rpe", "duration", "foster_load",
                             "acute_load_7", "chronic_load_28", "acwr",
                             "fatigue", "courbatures", "sommeil"]].copy()
    display_df["session_date"] = display_df["session_date"].dt.strftime("%d/%m/%Y")
    display_df.columns = ["Date", "RPE", "Durée (min)", "Charge (UA)",
                           "Aiguë 7j", "Chronique 28j", "ACWR",
                           "Fatigue", "Courbatures", "Sommeil"]
    st.dataframe(display_df, width='stretch', hide_index=True)

    # Export CSV
    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Télécharger CSV",
        data=csv,
        file_name=f"sessions_{player_name.replace(' ', '_')}.csv",
        mime="text/csv",
    )
