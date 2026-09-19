"""
pages/3_Tableau_Collectif.py
Dashboard collectif : heatmap ACWR équipe, tableau de risque, export CSV.
"""

import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modules.database import get_all_sessions_team, get_players
from modules.calculations import compute_team_acwr_snapshot
from modules.alerts import acwr_alert, acwr_color
from modules.visualizations import plot_team_heatmap

st.set_page_config(page_title="Tableau Collectif", page_icon="👥", layout="wide")

st.title("👥 Tableau de bord collectif")
st.markdown("Vue d'ensemble de la charge et du risque pour tout l'effectif.")

# ── Chargement ──────────────────────────────────────────────────────────────────
sessions_all = get_all_sessions_team(days=35)

if sessions_all.empty:
    st.info("Aucune donnée disponible. Saisissez des séances dans **Saisie Quotidienne**.")
    st.stop()

# ── SNAPSHOT ÉQUIPE ─────────────────────────────────────────────────────────────
snapshot = compute_team_acwr_snapshot(sessions_all)

# ── KPI COLLECTIFS ──────────────────────────────────────────────────────────────
st.subheader("📊 Résumé de l'effectif")

n_total   = len(snapshot)
n_danger  = (snapshot["ACWR"] > 1.5).sum()
n_warning = ((snapshot["ACWR"] >= 1.3) & (snapshot["ACWR"] <= 1.5)).sum()
n_optimal = ((snapshot["ACWR"] >= 0.8) & (snapshot["ACWR"] < 1.3)).sum()
n_under   = (snapshot["ACWR"] < 0.8).sum()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("👥 Effectif", n_total)
k2.metric("🟢 Zone optimale", n_optimal)
k3.metric("🟠 Vigilance",     n_warning)
k4.metric("🔴 Risque élevé",  n_danger)
k5.metric("🔵 Sous-charge",   n_under)

if n_danger > 0:
    joueurs_danger = snapshot[snapshot["ACWR"] > 1.5]["Joueur"].tolist()
    st.error(f"⚠️ **{n_danger} joueur(s) en zone rouge** : {', '.join(joueurs_danger)}")

if n_warning > 0:
    joueurs_warn = snapshot[(snapshot["ACWR"] >= 1.3) & (snapshot["ACWR"] <= 1.5)]["Joueur"].tolist()
    st.warning(f"🟠 **{n_warning} joueur(s) en vigilance** : {', '.join(joueurs_warn)}")

st.markdown("---")

# ── HEATMAP ─────────────────────────────────────────────────────────────────────
st.subheader("🗓️ Heatmap ACWR — 14 derniers jours")
fig_heatmap = plot_team_heatmap(snapshot, sessions_all)
st.plotly_chart(fig_heatmap, width='stretch')

st.markdown("---")

# ── TABLEAU DE RISQUE ────────────────────────────────────────────────────────────
st.subheader("📋 Tableau de risque — Effectif complet")

# Ajout colonne Niveau de risque
def format_risk(row):
    alert = acwr_alert(row["ACWR"])
    return f"{alert.emoji} {alert.label}"

snapshot_display = snapshot.copy()
snapshot_display["Risque"] = snapshot_display.apply(format_risk, axis=1)

# Tri par ACWR décroissant
snapshot_display = snapshot_display.sort_values("ACWR", ascending=False, na_position="last")

# Formatage
for col in ["ACWR", "Monotonie"]:
    snapshot_display[col] = snapshot_display[col].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
    )
for col in ["Charge aiguë (7j)", "Charge chronique (28j)", "Contrainte"]:
    snapshot_display[col] = snapshot_display[col].apply(
        lambda x: f"{x:.0f} UA" if pd.notna(x) else "N/A"
    )
snapshot_display["Bien-être /5"] = snapshot_display["Bien-être /5"].apply(
    lambda x: f"{x:.1f}/5" if pd.notna(x) else "N/A"
)

display_cols = ["Joueur", "Poste", "Risque", "ACWR",
                "Charge aiguë (7j)", "Charge chronique (28j)",
                "Monotonie", "Contrainte", "Bien-être /5"]

st.dataframe(
    snapshot_display[display_cols].reset_index(drop=True),
    width='stretch',
    hide_index=True,
)

# ── EXPORT CSV ──────────────────────────────────────────────────────────────────
col_exp1, col_exp2 = st.columns(2)
with col_exp1:
    csv_snap = snapshot_display[display_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Exporter snapshot équipe (CSV)",
        data=csv_snap,
        file_name="snapshot_equipe.csv",
        mime="text/csv",
    )
with col_exp2:
    csv_all = sessions_all.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Exporter toutes les sessions (CSV)",
        data=csv_all,
        file_name="sessions_equipe_completes.csv",
        mime="text/csv",
    )

# ── VUE PAR POSTE ───────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("📌 Vue par poste"):
    postes = snapshot["Poste"].unique()
    for poste in sorted(postes):
        st.markdown(f"**{poste}**")
        poste_df = snapshot_display[snapshot_display["Poste"] == poste][display_cols]
        st.dataframe(poste_df.reset_index(drop=True), width='stretch', hide_index=True)
