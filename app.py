import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from supabase import create_client, Client

# === Supabase Config ===
url = "https://sjoryqgtggoukbqviqqe.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNqb3J5cWd0Z2dvdWticXZpcXFlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDE5NzA4MTEsImV4cCI6MjA1NzU0NjgxMX0.LMIJ4SZncXI4YvpLOvBwlS98wOUnBvwRhGY_Hnjw460"
supabase: Client = create_client(url, key)

# === Protezione con password + logout ===
def check_password():
    def password_entered():
        if st.session_state["password"] == "ciaobudget":
            st.session_state["autenticato"] = True
        else:
            st.session_state["autenticato"] = False

    if "autenticato" not in st.session_state:
        st.text_input("🔐 Inserisci password:", type="password", on_change=password_entered, key="password")
        st.stop()
    elif not st.session_state["autenticato"]:
        st.text_input("🔐 Inserisci password:", type="password", on_change=password_entered, key="password")
        st.warning("❌ Password errata")
        st.stop()
    else:
        if st.button("🔓 Logout"):
            st.session_state["autenticato"] = False
            st.experimental_rerun()

check_password()

st.title("💰 Budget Manager")

# === Caricamento dati ===
data_result = supabase.table("budget").select("*").execute()
df = pd.DataFrame(data_result.data)

if not df.empty:
    df["data"] = pd.to_datetime(df["data"])
    df["anno"] = df["data"].dt.year

    # === Selettore anno ===
    anno_sel = st.selectbox("📅 Seleziona anno", sorted(df["anno"].unique()))
    df = df[df["anno"] == anno_sel]

    # === Mese ordinato per grafici ===
    month_order = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    df["mese"] = pd.Categorical(df["data"].dt.strftime("%b"), categories=month_order, ordered=True)

    st.subheader(f"📊 Report completo {anno_sel}")

    # === Grafico a barre: Spese per categoria ===
    spese = df[df["tipologia"] == "spesa"].copy()
    grouped = spese.groupby(["mese", "categoria"])["ammontare"].sum().reset_index()
    pivot = grouped.pivot(index="mese", columns="categoria", values="ammontare").fillna(0)
    pivot = pivot.reindex(month_order, fill_value=0)
    fig1 = go.Figure()
    for col in pivot.columns:
        fig1.add_trace(go.Bar(name=col, x=pivot.index, y=pivot[col]))
    totali = pivot.sum(axis=1)
    for x, y in zip(pivot.index, totali):
        fig1.add_annotation(x=x, y=y, text=f"{y:.0f}€", showarrow=False, yshift=10)
    fig1.update_layout(barmode="stack", title="Spese mensili per categoria", xaxis_title="Mese", yaxis_title="€", xaxis_tickangle=-15)
    st.plotly_chart(fig1, use_container_width=True)

    # === Grafico di trend: Ricavi / Spese / Saldo ===
    grouped_trend = df.groupby(["mese", "tipologia"])["ammontare"].sum().unstack().fillna(0)
    grouped_trend["saldo"] = grouped_trend.get("ricavo", 0) - grouped_trend.get("spesa", 0)
    grouped_trend = grouped_trend.reindex(month_order).fillna(0)
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=grouped_trend.index, y=grouped_trend.get("ricavo", 0), name="Ricavi", line=dict(color="green")))
    fig2.add_trace(go.Scatter(x=grouped_trend.index, y=grouped_trend.get("spesa", 0), name="Spese", line=dict(color="red")))
    fig2.add_trace(go.Scatter(x=grouped_trend.index, y=grouped_trend["saldo"], name="Saldo", line=dict(color="gold")))
    fig2.update_layout(title="Trend Mensile", xaxis_title="Mese", yaxis_title="€")
    st.plotly_chart(fig2, use_container_width=True)

    # === Grafico a torta ===
    st.subheader("🥧 Distribuzione % delle Spese per Categoria")
    torta = spese.groupby("categoria")["ammontare"].sum()
    fig3 = go.Figure(data=[go.Pie(labels=torta.index, values=torta.values, hole=0.3)])
    fig3.update_layout(title="Distribuzione % delle Spese")
    st.plotly_chart(fig3, use_container_width=True)

else:
    st.warning("⚠️ Nessun dato disponibile nel database.")