import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from supabase import create_client, Client

# === Supabase Config ===
url = "https://sjoryqgtggoukbqviqqe.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNqb3J5cWd0Z2dvdWticXZpcXFlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDE5NzA4MTEsImV4cCI6MjA1NzU0NjgxMX0.LMIJ4SZncXI4YvpLOvBwlS98wOUnBvwRhGY_Hnjw460"

supabase: Client = create_client(url, key)

st.title("💰 Budget Manager (Supabase Edition)")

# === Inserimento ===
st.header("➕ Inserisci nuova voce")

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
anno_corrente = datetime.now().year
st.header(f"📈 Report completo {anno_corrente}")

# Selettore anno
anni_disponibili = sorted(df["data"].dt.year.unique())
anno_selezionato = st.selectbox("📅 Seleziona l'anno", anni_disponibili, index=anni_disponibili.index(anno_corrente) if anno_corrente in anni_disponibili else 0)
df = df[df["data"].dt.year == anno_selezionato]

data_result = supabase.table("budget").select("*").execute()
df = pd.DataFrame(data_result.data)

if not df.empty:
    df["data"] = pd.to_datetime(df["data"])
    df["mese"] = pd.Categorical(df["data"].dt.strftime("%b"), categories=["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"], ordered=True)
    df["mese_label"] = df["data"].dt.strftime("%b")
    df["mese_ord"] = df["data"].dt.month

    # === REPORT 1: Spese per categoria per mese ===
    st.subheader("📊 Spese mensili per categoria")
    spese = df[df["tipologia"] == "spesa"]
    grouped = spese.groupby([df["data"].dt.to_period("M").astype(str), "categoria"])["ammontare"].sum().reset_index()
    pivot = grouped.pivot(index="data", columns="categoria", values="ammontare").fillna(0)
    pivot = pivot.sort_index()

    fig1 = go.Figure()
    for col in pivot.columns:
        fig1.add_trace(go.Bar(name=col, x=pivot.index.astype(str), y=pivot[col]))

    # Totali sopra barre
    totali = pivot.sum(axis=1)
    for x, y in zip(pivot.index, totali):
        fig1.add_annotation(
            x=x,
            y=y,
            text=f"{y:.0f}€",
            showarrow=False,
            yshift=12,
            font=dict(size=11)
        )

    fig1.update_layout(barmode="stack", title="Spese per Categoria (Mensili)", xaxis_title="Mese", yaxis_title="€", xaxis_tickangle=-15)
    st.plotly_chart(fig1, use_container_width=True)

    # === REPORT 2: Trend Ricavi / Spese / Saldo ===
    st.subheader("📈 Andamento mensile Ricavi, Spese, Saldo")
    df["periodo"] = df["data"].dt.to_period("M").astype(str)
    trend = df.groupby(["periodo", "tipologia"])["ammontare"].sum().unstack().fillna(0)
    trend["saldo"] = trend.get("ricavo", 0) - trend.get("spesa", 0)
    trend = trend.sort_index()

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=trend.index.astype(str), y=trend.get("ricavo", 0), name="Ricavi", line=dict(color="green")))
    fig2.add_trace(go.Scatter(x=trend.index.astype(str), y=trend.get("spesa", 0), name="Spese", line=dict(color="red")))
    fig2.add_trace(go.Scatter(x=trend.index.astype(str), y=trend["saldo"], name="Saldo", line=dict(color="gold")))

    fig2.update_layout(title="Andamento Ricavi / Spese / Saldo", xaxis_title="Mese", yaxis_title="€")
    st.plotly_chart(fig2, use_container_width=True)

    # === REPORT 3: Torta % spese ===
    st.subheader("🥧 Distribuzione % delle Spese per Categoria")
    torta = spese.groupby("categoria")["ammontare"].sum()
    fig3 = go.Figure(data=[go.Pie(labels=torta.index, values=torta.values, hole=0.3)])
    fig3.update_layout(title="Distribuzione % delle Spese")
    st.plotly_chart(fig3, use_container_width=True)

else:
    st.info("Nessun dato ancora disponibile.")