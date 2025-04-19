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

url = "https://sjoryqgtggoukbqviqqe.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNqb3J5cWd0Z2dvdWticXZpcXFlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDE5NzA4MTEsImV4cCI6MjA1NzU0NjgxMX0.LMIJ4SZncXI4YvpLOvBwlS98wOUnBvwRhGY_Hnjw460"
supabase: Client = create_client(url, key)

# === APP ===
st.title("💰 Controllo Finanze")

data_result = supabase.table("budget").select("*").execute()
df = pd.DataFrame(data_result.data)

if not df.empty:
    df["data"] = pd.to_datetime(df["data"])

    st.subheader("📋 Database Caricato")

    st.dataframe(df, use_container_width=True)

# === GESTIONE RECORD SEMPRE VISIBILE (DEBUG) ===
st.header("🛠️ Gestione Record (DEBUG SEMPRE ATTIVO)")

with st.expander("✏️ Modifica o Cancella un Record"):
    if not df.empty:
        record_selezionato = st.selectbox("Seleziona un record", df.index)

        if record_selezionato is not None:
            record = df.loc[record_selezionato]

            with st.form("modifica_form"):
                nuova_data = st.date_input("Data", value=record["data"]).strftime("%Y-%m-%d")
                nuova_categoria = st.text_input("Categoria", value=record["categoria"])
                nuova_sottocategoria = st.text_input("Sottocategoria", value=record["sottocategoria"])
                nuovo_ammontare = st.number_input("Ammontare (€)", value=float(record["ammontare"]), step=0.01)
                nuova_note = st.text_input("Note", value=record["note"])
                nuova_tipologia = st.selectbox("Tipologia", ["spesa", "ricavo"], index=0 if record["tipologia"]=="spesa" else 1)

                col_mod, col_canc = st.columns(2)

                with col_mod:
                    salva_mod = st.form_submit_button("💾 Salva modifiche")
                with col_canc:
                    cancella = st.form_submit_button("🗑️ Cancella record")

                if salva_mod:
                    supabase.table("budget").update({
                        "data": nuova_data,
                        "categoria": nuova_categoria,
                        "sottocategoria": nuova_sottocategoria,
                        "ammontare": float(nuovo_ammontare),
                        "note": nuova_note,
                        "tipologia": nuova_tipologia
                    }).eq("id", record["id"]).execute()
                    st.success("✅ Record aggiornato con successo!")
                    st.rerun()

                if cancella:
                    supabase.table("budget").delete().eq("id", record["id"]).execute()
                    st.success("✅ Record cancellato con successo!")
                    st.rerun()
    else:
        st.info("Non ci sono ancora dati disponibili per modificare o cancellare.")