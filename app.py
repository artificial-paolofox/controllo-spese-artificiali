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

# === Importa dati ===
data_result = supabase.table("budget").select("*").execute()
df = pd.DataFrame(data_result.data)

if not df.empty:

    df["data"] = pd.to_datetime(df["data"])
    df["ammontare"] = pd.to_numeric(df["ammontare"], errors="coerce")
    month_order = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    df["mese"] = pd.Categorical(df["data"].dt.strftime("%b"), categories=month_order, ordered=True)

    df["anno"] = df["data"].dt.year
    df["mese"] = df["data"].dt.strftime("%b")
    df["periodo"] = df["data"].dt.to_period("M")

    st.title("💰 Budget Manager")

        # === Inserimento nuova voce ===
    with st.expander("➕ Inserisci nuova voce"):
        categorie_data = df["categoria"].dropna().unique().tolist()
        sottocategorie_data = df["sottocategoria"].dropna().unique().tolist()

    with st.form("inserimento"):
        col1, col2 = st.columns(2)
    with col1:
        data = st.date_input("📅 Data", value=datetime.today()).strftime("%Y-%m-%d")
        cat_esistente = st.selectbox("Categoria", [""] + sorted(categorie_data))
        nuova_cat = st.text_input("Nuova categoria")
        categoria = nuova_cat if nuova_cat else cat_esistente

        subcat_esistente = st.selectbox("Sottocategoria", [""] + sorted(sottocategorie_data))
        nuova_subcat = st.text_input("Nuova sottocategoria")
        sottocategoria = nuova_subcat if nuova_subcat else subcat_esistente
    with col2:
        ammontare = st.number_input("💶 Ammontare", step=0.01)
        tipologia = st.selectbox("📌 Tipologia", ["spesa", "ricavo"])
        note = st.text_input("📝 Note")

        invia = st.form_submit_button("Salva")
        if invia:
        errori = []
        if not categoria or not categoria.isupper():
        errori.append("⚠️ Categoria obbligatoria in MAIUSCOLO.")
        if not sottocategoria or not sottocategoria.islower():
        errori.append("⚠️ Sottocategoria obbligatoria in minuscolo.")
        if note and not note.islower():
        errori.append("⚠️ Le note devono essere tutte minuscole.")
        if errori:
        for e in errori:
        st.warning(e)
        else:
        supabase.table("budget").insert({
        "data": data,
        "categoria": categoria,
        "sottocategoria": sottocategoria,
        "ammontare": float(ammontare),
        "note": note,
        "tipologia": tipologia
        }).execute()
        st.success("✅ Inserito correttamente!")

    # === Selezione anno per report ===
        anno_sel = st.selectbox("📅 Seleziona anno", sorted(df["anno"].unique()), index=len(sorted(df["anno"].unique())) - 1)
        df = df[df["anno"] == anno_sel]

        st.subheader(f"📊 Report completo {anno_sel}")
        month_order = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

    # === Grafico a barre spese mensili ===
        spese = df[df["tipologia"] == "spesa"].copy()
        spese["mese"] = pd.Categorical(spese["data"].dt.strftime("%b"), categories=month_order, ordered=True)
        grouped = spese.groupby(["mese", "categoria"])["ammontare"].sum().reset_index()
        pivot = grouped.pivot(index="mese", columns="categoria", values="ammontare").fillna(0)
        fig1 = go.Figure()
        for col in pivot.columns:
        fig1.add_trace(go.Bar(name=col, x=pivot.index, y=pivot[col]))
        totali = pivot.sum(axis=1)
        for x, y in zip(pivot.index, totali):
        fig1.add_annotation(x=x, y=y, text=f"{y:.0f}€", showarrow=False, yshift=10)
        fig1.update_layout(barmode="stack", title="Spese mensili per categoria", xaxis_title="Mese", yaxis_title="€", xaxis_tickangle=-15)
        st.plotly_chart(fig1, use_container_width=True)

    # === Grafico a linee ricavi/spese/saldo ===
        trend = df.groupby(["mese", "tipologia"])["ammontare"].sum().unstack().fillna(0)
        trend["saldo"] = trend.get("ricavo", 0) - trend.get("spesa", 0)
        trend = trend.reindex(month_order, fill_value=0).dropna(how="all")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=trend.index, y=trend.get("ricavo", 0), name="Ricavi", line=dict(color="green")))
        fig2.add_trace(go.Scatter(x=trend.index, y=trend.get("spesa", 0), name="Spese", line=dict(color="red")))
        fig2.add_trace(go.Scatter(x=trend.index, y=trend["saldo"], name="Saldo", line=dict(color="gold")))
        fig2.update_layout(title="Trend Mensile", xaxis_title="Mese", yaxis_title="€")
        st.plotly_chart(fig2, use_container_width=True)

    # === Torta delle spese ===
        st.subheader("🥧 Distribuzione % delle Spese per Categoria")
        torta = spese.groupby("categoria")["ammontare"].sum()
        fig3 = go.Figure(data=[go.Pie(labels=torta.index, values=torta.values, hole=0.3)])
        st.plotly_chart(fig3, use_container_width=True)

    # === Tabella filtrabile ===
        st.subheader("🧰 Filtra i dati del database")
        tipologie = df["tipologia"].dropna().unique().tolist()
        tipologia_sel = st.selectbox("📌 Tipologia", ["Tutte"] + tipologie)
        mesi_disponibili = df["data"].dt.strftime("%b").unique().tolist()
        mese_sel = st.selectbox("📅 Mese", ["Tutti"] + mesi_disponibili)
        testo_libero = st.text_input("🔍 Cerca testo")
        min_amm, max_amm = df["ammontare"].min(), df["ammontare"].max()
        ammontare_range = st.slider("💶 Range ammontare (€)", float(min_amm), float(max_amm), (float(min_amm), float(max_amm)))

        filtro_df = df.copy()
        if tipologia_sel != "Tutte":
        filtro_df = filtro_df[filtro_df["tipologia"] == tipologia_sel]
        if mese_sel != "Tutti":
        filtro_df = filtro_df[filtro_df["data"].dt.strftime("%b") == mese_sel]
        if testo_libero:
        filtro_df = filtro_df[
        filtro_df["categoria"].str.lower().str.contains(testo_libero.lower()) |
        filtro_df["sottocategoria"].str.lower().str.contains(testo_libero.lower()) |
        filtro_df["note"].str.lower().str.contains(testo_libero.lower())
        ]
        filtro_df = filtro_df[
        (filtro_df["ammontare"] >= ammontare_range[0]) & (filtro_df["ammontare"] <= ammontare_range[1])
        ]

    with st.expander("📋 Visualizza dati grezzi dal database"):
        if not filtro_df.empty:
        st.dataframe(filtro_df.sort_values("data", ascending=False), use_container_width=True)
        else:
        st.info("⚠️ Nessun dato corrisponde ai filtri.")

        else:
        st.warning("⚠️ Nessun dato disponibile nel database.")