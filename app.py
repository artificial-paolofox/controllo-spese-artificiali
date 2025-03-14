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
st.header("📈 Report completo")

data_result = supabase.table("budget").select("*").execute()
df = pd.DataFrame(data_result.data)

if not df.empty:
    df["data"] = pd.to_datetime(df["data"])

    # === SELETTORE ANNO ===
    anni_disponibili = sorted(df["data"].dt.year.unique())
    anno_corrente = datetime.now().year
    anno_selezionato = st.selectbox("📅 Seleziona l'anno", anni_disponibili, index=anni_disponibili.index(anno_corrente) if anno_corrente in anni_disponibili else 0)
    df = df[df["data"].dt.year == anno_selezionato]
    st.subheader(f"📅 Report completo {anno_selezionato}")

    # === GRAFICO BARRE ===
    spese = df[df["tipologia"] == "spesa"]
    month_map = {"01": "Gen", "02": "Feb", "03": "Mar", "04": "Apr", "05": "Mag", "06": "Giu", "07": "Lug", "08": "Ago", "09": "Set", "10": "Ott", "11": "Nov", "12": "Dic"}
    month_order = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

    spese["mese_num"] = spese["data"].dt.strftime("%m")
    spese["mese_str"] = spese["mese_num"].map(month_map)
    spese["mese_str"] = pd.Categorical(spese["mese_str"], categories=month_order, ordered=True)

    grouped = spese.groupby(["mese_str", "categoria"])["ammontare"].sum().reset_index()
    pivot = grouped.pivot(index="mese_str", columns="categoria", values="ammontare").fillna(0)

    fig1 = go.Figure()
    for col in pivot.columns:
        fig1.add_trace(go.Bar(name=col, x=pivot.index, y=pivot[col]))

    totali = pivot.sum(axis=1)
    for x, y in zip(pivot.index, totali):
        fig1.add_annotation(x=x, y=y, text=f"{y:.0f}€", showarrow=False, yshift=12, font=dict(size=11))

    fig1.update_layout(barmode="stack", title="Spese per Categoria (Mensili)", xaxis_title="Mese", yaxis_title="€", xaxis_tickangle=-15)
    st.plotly_chart(fig1, use_container_width=True)

    # === GRAFICO TREND ===
    df["mese_num"] = df["data"].dt.strftime("%m")
    df["periodo"] = df["mese_num"].map(month_map)
    df["periodo"] = pd.Categorical(df["periodo"], categories=month_order, ordered=True)

    trend = df.groupby(["periodo", "tipologia"])["ammontare"].sum().unstack().fillna(0)
    trend["saldo"] = trend.get("ricavo", 0) - trend.get("spesa", 0)
    trend = trend.reindex(month_order).dropna(how="all")

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=trend.index, y=trend.get("ricavo", 0), name="Ricavi", line=dict(color="green")))
    fig2.add_trace(go.Scatter(x=trend.index, y=trend.get("spesa", 0), name="Spese", line=dict(color="red")))
    fig2.add_trace(go.Scatter(x=trend.index, y=trend["saldo"], name="Saldo", line=dict(color="gold")))

    fig2.update_layout(title="Andamento Ricavi / Spese / Saldo", xaxis_title="Mese", yaxis_title="€")
    st.plotly_chart(fig2, use_container_width=True)

    # === GRAFICO TORTA ===
    st.subheader("🥧 Distribuzione % delle Spese per Categoria")
    torta = spese.groupby("categoria")["ammontare"].sum()
    fig3 = go.Figure(data=[go.Pie(labels=torta.index, values=torta.values, hole=0.3)])
    fig3.update_layout(title="Distribuzione % delle Spese")
    st.plotly_chart(fig3, use_container_width=True)

    # === Visualizza tabella completa ===
    with st.expander("📋 Visualizza dati grezzi dal database"):
        st.dataframe(df.sort_values("data", ascending=False), use_container_width=True)

else:
    st.info("Nessun dato ancora disponibile.")