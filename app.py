import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from supabase import create_client, Client
import random

# === CONFIG ===
palette = [
    '#FF00FF', '#00FFFF', '#FF5F1F', '#FFFF00',
    '#39FF14', '#FF1493', '#1E90FF', '#FF073A',
    '#8A2BE2', '#FFFFFF'
]

def crea_colori(categorie):
    categorie_ordinate = sorted(categorie)
    colori = {}
    for i, cat in enumerate(categorie_ordinate):
        if i < len(palette):
            colori[cat] = palette[i]
        else:
            colori[cat] = "#%06x" % random.randint(0, 0xFFFFFF)
    return colori

# === SUPABASE CONFIG ===
url = "https://sjoryqgtggoukbqviqqe.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNqb3J5cWd0Z2dvdWticXZpcXFlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDE5NzA4MTEsImV4cCI6MjA1NzU0NjgxMX0.LMIJ4SZncXI4YvpLOvBwlS98wOUnBvwRhGY_Hnjw460"
supabase: Client = create_client(url, key)

st.title("💰 Controllo Finanze")

# === Caricamento dati ===
data_result = supabase.table("budget").select("*").execute()
df = pd.DataFrame(data_result.data)

if not df.empty:
    df["data"] = pd.to_datetime(df["data"])

    st.header("📈 Report completo")

    anni_disponibili = sorted(df["data"].dt.year.unique())
    anno_corrente = datetime.now().year
    anno_selezionato = st.selectbox("📅 Seleziona l'anno", anni_disponibili, index=anni_disponibili.index(anno_corrente) if anno_corrente in anni_disponibili else 0)
    df = df[df["data"].dt.year == anno_selezionato]

    # === Correzione importante: creazione della colonna "periodo" ===
    month_map = {"01": "Gen", "02": "Feb", "03": "Mar", "04": "Apr", "05": "Mag", "06": "Giu", "07": "Lug", "08": "Ago", "09": "Set", "10": "Ott", "11": "Nov", "12": "Dic"}
    month_order = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

    df["mese_num"] = df["data"].dt.strftime("%m")
    df["periodo"] = df["mese_num"].map(month_map)
    df["periodo"] = pd.Categorical(df["periodo"], categories=month_order, ordered=True)

    # === GRAFICO TREND ===
    trend = df.groupby(["periodo", "tipologia"])["ammontare"].sum().unstack().fillna(0)
    trend["saldo"] = trend.get("ricavo", 0) - trend.get("spesa", 0)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=trend.index, y=trend.get("ricavo", 0), name="Ricavi", line=dict(color="green")))
    fig.add_trace(go.Scatter(x=trend.index, y=trend.get("spesa", 0), name="Spese", line=dict(color="red")))
    fig.add_trace(go.Scatter(x=trend.index, y=trend["saldo"], name="Saldo", line=dict(color="gold")))

    fig.update_layout(title="Andamento Ricavi / Spese / Saldo", xaxis_title="Mese", yaxis_title="€")

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Nessun dato ancora disponibile.")