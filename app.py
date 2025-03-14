import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# === Connessione al database ===
DB_PATH = 'Budget_copy.db'
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# === Crea la tabella se non esiste ===
cursor.execute("""
CREATE TABLE IF NOT EXISTS budget (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Data TEXT NOT NULL,
    Categoria TEXT NOT NULL,
    Sottocategoria TEXT,
    Ammontare REAL NOT NULL,
    Note TEXT,
    Tipologia TEXT NOT NULL
)
""")
conn.commit()

# === Streamlit UI ===
st.title("💰 Budget Manager")

# --- Form di inserimento ---
st.header("➕ Inserisci nuova voce")

with st.form("inserimento_form"):
    col1, col2 = st.columns(2)
    with col1:
        data = st.date_input("Data", value=datetime.today()).strftime("%Y-%m-%d")
        categoria = st.text_input("Categoria")
        sottocategoria = st.text_input("Sottocategoria")
    with col2:
        ammontare = st.number_input("Ammontare (€)", step=0.01)
        tipologia = st.selectbox("Tipologia", ["spesa", "ricavo"])
        note = st.text_input("Note")

    submitted = st.form_submit_button("Inserisci")

    if submitted:
        cursor.execute("""
            INSERT INTO budget (Data, Categoria, Sottocategoria, Ammontare, Note, Tipologia)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (data, categoria, sottocategoria, ammontare, note, tipologia))
        conn.commit()
        st.success("✅ Voce inserita con successo!")

# === Report: Spese mensili per categoria ===
st.header("📊 Spese mensili per categoria (impilate)")

df_spese = pd.read_sql_query("""
    SELECT strftime('%Y-%m', Data) AS Mese, Categoria, SUM(Ammontare) AS Totale
    FROM budget
    WHERE Tipologia = 'spesa'
    GROUP BY Mese, Categoria
    ORDER BY Mese, Categoria
""", conn)

if not df_spese.empty:
    pivot_df = df_spese.pivot(index='Mese', columns='Categoria', values='Totale').fillna(0)
    pivot_df = pivot_df.sort_index()

    fig = go.Figure()

    for categoria in pivot_df.columns:
        fig.add_trace(go.Bar(
            name=categoria,
            x=pivot_df.index,
            y=pivot_df[categoria],
            text=pivot_df[categoria].apply(lambda x: f"€{x:,.2f}" if x > 0 else ""),
            hovertemplate='%{x}<br>%{y} €<br>' + categoria,
        ))

    fig.update_layout(
        barmode='stack',
        title='Spese mensili per categoria',
        xaxis_title='Mese',
        yaxis_title='Totale €',
        legend_title='Categoria',
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nessuna spesa disponibile per il grafico.")

conn.close()