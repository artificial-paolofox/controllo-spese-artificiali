import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from supabase import create_client, Client

# === Supabase Config ===
url = "https://sjoryqgtggoukbqviqqe.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNqb3J5cWd0Z2dvdWticXZpcXFlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDE5NzA4MTEsImV4cCI6MjA1NzU0NjgxMX0.LMIJ4SZncXI4YvpLOvBwlS98wOUnBvwRhGY_Hnjw460"

supabase: Client = create_client(url, key)

st.title("💰 Budget Manager (Cloud Edition)")

# === Form di Inserimento ===
st.header("➕ Inserisci nuova voce")

# Preleva categorie/sottocategorie esistenti
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
        if not categoria or not categoria.isupper():
            errori.append("⚠️ Categoria obbligatoria e tutta MAIUSCOLA.")
        if not sottocategoria or not sottocategoria.islower():
            errori.append("⚠️ Sottocategoria obbligatoria e tutta minuscola.")
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
            st.success("✅ Voce inserita con successo!")

# === Report ===
st.header("📊 Report completo")

data_result = supabase.table("budget").select("*").execute()
df = pd.DataFrame(data_result.data)

if not df.empty:
    df["data"] = pd.to_datetime(df["data"])
    df["mese"] = df["data"].dt.strftime("%b")
    df["mese_num"] = df["data"].dt.month
    df = df.sort_values("mese_num")

    # === Grafico 1: Barre impilate per categoria e mese (solo spese) ===
    st.subheader("📊 Spese mensili per categoria")
    df_spese = df[df["tipologia"] == "spesa"]
    grouped = df_spese.groupby(["mese", "categoria"])["ammontare"].sum().reset_index()
    pivot_df = grouped.pivot(index="mese", columns="categoria", values="ammontare").fillna(0)
    pivot_df = pivot_df.sort_index()

    fig1 = go.Figure()
    for categoria in pivot_df.columns:
        y_values = pivot_df[categoria].values
        for i, val in enumerate(y_values):
            if val > 0:
                fig1.add_annotation(x=pivot_df.index[i], y=val, text=f"{val:.0f}€", showarrow=False, font=dict(size=10), yshift=10)
        fig1.add_trace(go.Bar(name=categoria, x=pivot_df.index, y=pivot_df[categoria]))
    fig1.update_layout(barmode="stack", xaxis_title="Mese", yaxis_title="Totale Spese €", title="Spese mensili per categoria")
    st.plotly_chart(fig1, use_container_width=True)

    # === Grafico 2: Trend Ricavi / Spese / Saldo ===
    st.subheader("📈 Trend mensile Ricavi / Spese / Saldo")
    df_trend = df.groupby(["mese", "tipologia"])["ammontare"].sum().unstack().fillna(0)
    df_trend["saldo"] = df_trend.get("ricavo", 0) - df_trend.get("spesa", 0)
    df_trend = df_trend.sort_index()

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df_trend.index, y=df_trend.get("ricavo", 0), name="Ricavi", line=dict(color="green")))
    fig2.add_trace(go.Scatter(x=df_trend.index, y=df_trend.get("spesa", 0), name="Spese", line=dict(color="red")))
    fig2.add_trace(go.Scatter(x=df_trend.index, y=df_trend["saldo"], name="Saldo", line=dict(color="gold")))
    fig2.update_layout(xaxis_title="Mese", yaxis_title="€", title="Andamento mensile Ricavi/Spese/Saldo")
    st.plotly_chart(fig2, use_container_width=True)

    # === Grafico 3: Torta spese per categoria ===
    st.subheader("🥧 Distribuzione % Spese per categoria")
    torta = df_spese.groupby("categoria")["ammontare"].sum()
    if not torta.empty:
        fig3 = go.Figure(data=[go.Pie(labels=torta.index, values=torta.values, hole=0.3)])
        fig3.update_layout(title="Distribuzione % delle Spese per Categoria")
        st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Nessun dato ancora disponibile.")