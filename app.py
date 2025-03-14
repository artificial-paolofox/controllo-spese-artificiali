import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import calendar

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

# === Pre-elaborazione mesi abbreviati ===
def abbrevia_mese(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m")
        return calendar.month_abbr[dt.month].lower()
    except:
        return date_str

# === SPESA: Barre impilate per categoria ===
st.header("📊 Spese mensili per categoria")

df_spese = pd.read_sql_query("""
    SELECT strftime('%Y-%m', Data) AS Mese, Categoria, SUM(Ammontare) AS Totale
    FROM budget
    WHERE Tipologia = 'spesa'
    GROUP BY Mese, Categoria
    ORDER BY Mese, Categoria
""", conn)

if not df_spese.empty:
    df_spese['MeseAbbr'] = df_spese['Mese'].apply(abbrevia_mese)
    pivot_df = df_spese.pivot(index='MeseAbbr', columns='Categoria', values='Totale').fillna(0)
    pivot_df = pivot_df.loc[sorted(pivot_df.index, key=lambda x: list(calendar.month_abbr).index(x.capitalize()))]

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

# === TREND: Ricavi, Spese e Saldo ===
st.header("📈 Andamento mensile: Ricavi, Spese e Saldo")

df_trend = pd.read_sql_query("""
    SELECT strftime('%Y-%m', Data) AS Mese,
           SUM(CASE WHEN Tipologia = 'ricavo' THEN Ammontare ELSE 0 END) AS Ricavi,
           SUM(CASE WHEN Tipologia = 'spesa' THEN Ammontare ELSE 0 END) AS Spese
    FROM budget
    GROUP BY Mese
    ORDER BY Mese
""", conn)

if not df_trend.empty:
    df_trend['Saldo'] = df_trend['Ricavi'] - df_trend['Spese']
    df_trend['MeseAbbr'] = df_trend['Mese'].apply(abbrevia_mese)
    df_trend = df_trend.set_index('MeseAbbr')
    df_trend = df_trend.loc[sorted(df_trend.index, key=lambda x: list(calendar.month_abbr).index(x.capitalize()))]

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(x=df_trend.index, y=df_trend['Ricavi'], mode='lines+markers', name='Ricavi'))
    fig_trend.add_trace(go.Scatter(x=df_trend.index, y=df_trend['Spese'], mode='lines+markers', name='Spese'))
    fig_trend.add_trace(go.Scatter(x=df_trend.index, y=df_trend['Saldo'], mode='lines+markers', name='Saldo'))

    fig_trend.update_layout(
        title="Andamento Ricavi / Spese / Saldo",
        xaxis_title="Mese",
        yaxis_title="€",
        height=500
    )

    st.plotly_chart(fig_trend, use_container_width=True)

conn.close()