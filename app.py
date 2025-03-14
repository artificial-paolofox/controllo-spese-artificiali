import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from supabase import create_client, Client

# === Supabase Config ===
url = "https://sjoryqgtggoukbqviqqe.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNqb3J5cWd0Z2dvdWticXZpcXFlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDE5NzA4MTEsImV4cCI6MjA1NzU0NjgxMX0.LMIJ4SZncXI4YvpLOvBwlS98wOUnBvwRhGY_Hnjw460"

supabase: Client = create_client(url, key)

# === Streamlit UI ===
st.title("💰 Budget Manager (Cloud Edition)")

# --- Form di inserimento ---
st.header("➕ Inserisci nuova voce")

# Leggi le categorie esistenti per i dropdown
categorie_data = supabase.table("budget").select("categoria").execute()
sottocategorie_data = supabase.table("budget").select("sottocategoria").execute()

categorie_esistenti = sorted(set(i['categoria'] for i in categorie_data.data if i['categoria']))
sottocategorie_esistenti = sorted(set(i['sottocategoria'] for i in sottocategorie_data.data if i['sottocategoria']))

with st.form("inserimento_form"):
    col1, col2 = st.columns(2)

    with col1:
        data = st.date_input("Data", value=datetime.today()).strftime("%Y-%m-%d")
        categoria_sel = st.selectbox("Categoria esistente", categorie_esistenti) if categorie_esistenti else ""
        nuova_categoria = st.text_input("...oppure scrivi una nuova categoria")
        categoria = nuova_categoria if nuova_categoria else categoria_sel

        sottocategoria_sel = st.selectbox("Sottocategoria esistente", sottocategorie_esistenti) if sottocategorie_esistenti else ""
        nuova_sottocategoria = st.text_input("...oppure scrivi una nuova sottocategoria")
        sottocategoria = nuova_sottocategoria if nuova_sottocategoria else sottocategoria_sel

    with col2:
        ammontare = st.number_input("Ammontare (€)", step=0.01)
        tipologia = st.selectbox("Tipologia", ["spesa", "ricavo"])
        note = st.text_input("Note")

    submitted = st.form_submit_button("Inserisci")

    if submitted:
        errori = []

        if not categoria:
            errori.append("⚠️ Categoria obbligatoria.")
        elif not categoria.isupper():
            errori.append("⚠️ La categoria deve essere tutta MAIUSCOLA.")

        if not sottocategoria:
            errori.append("⚠️ Sottocategoria obbligatoria.")
        elif not sottocategoria.islower():
            errori.append("⚠️ La sottocategoria deve essere tutta minuscola.")

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
                "ammontare": ammontare,
                "note": note,
                "tipologia": tipologia
            }).execute()
            st.success("✅ Voce inserita con successo!")

# === Grafici ===
st.header("📈 Report Mensile (Supabase)")

data_result = supabase.table("budget").select("*").execute()
df = pd.DataFrame(data_result.data)

if not df.empty:
    df["data"] = pd.to_datetime(df["data"])
    df["mese"] = df["data"].dt.strftime("%b %Y")

    # TREND
    df_trend = df.groupby(["mese", "tipologia"])["ammontare"].sum().unstack().fillna(0)
    df_trend["saldo"] = df_trend.get("ricavo", 0) - df_trend.get("spesa", 0)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_trend.index, y=df_trend.get("ricavo", 0), name="Ricavi", line=dict(color="green")))
    fig.add_trace(go.Scatter(x=df_trend.index, y=df_trend.get("spesa", 0), name="Spese", line=dict(color="red")))
    fig.add_trace(go.Scatter(x=df_trend.index, y=df_trend["saldo"], name="Saldo", line=dict(color="gold")))
    fig.update_layout(title="Andamento Ricavi / Spese / Saldo", xaxis_title="Mese", yaxis_title="€")
    st.plotly_chart(fig, use_container_width=True)

    # TORTA
    spese_per_cat = df[df["tipologia"] == "spesa"].groupby("categoria")["ammontare"].sum()
    if not spese_per_cat.empty:
        fig_pie = go.Figure(data=[go.Pie(labels=spese_per_cat.index, values=spese_per_cat.values, hole=0.3)])
        fig_pie.update_layout(title="Distribuzione Spese per Categoria (%)")
        st.plotly_chart(fig_pie, use_container_width=True)

else:
    st.info("Nessun dato ancora inserito.")