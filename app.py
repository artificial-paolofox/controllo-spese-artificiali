import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# === Connessione al database ===
DB_PATH = 'Budget_copy.db'  # Assicurati che il file sia nella stessa cartella
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

# --- Report ---
st.header("📊 Report mensile")

df = pd.read_sql_query("""
    SELECT strftime('%Y-%m', Data) AS Mese,
           SUM(CASE WHEN Tipologia = 'ricavo' THEN Ammontare ELSE 0 END) AS Ricavi,
           SUM(CASE WHEN Tipologia = 'spesa' THEN Ammontare ELSE 0 END) AS Spese
    FROM budget
    GROUP BY Mese
    ORDER BY Mese
""", conn)

if not df.empty:
    st.dataframe(df)

    # --- Grafico ---
    st.subheader("📈 Andamento Ricavi vs Spese")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df['Mese'], df['Ricavi'], marker='o', label='Ricavi')
    ax.plot(df['Mese'], df['Spese'], marker='o', label='Spese')
    ax.set_xlabel('Mese')
    ax.set_ylabel('€')
    ax.set_title('Andamento mensile')
    ax.legend()
    ax.grid(True)
    plt.xticks(rotation=45)
    st.pyplot(fig)
else:
    st.info("Nessun dato disponibile per ora.")

conn.close()
