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

# === Funzione mese + anno abbreviato ===
def abbrevia_mese_anno(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m")
        return f"{calendar.month_abbr[dt.month].lower()} {dt.year}"
    except:
        return date_str

# === Streamlit UI ===
st.title("💰 Budget Manager")


# --- Form di inserimento con dropdown personalizzabili ---

# Leggiamo categorie e sottocategorie esistenti dal DB
df_cat = pd.read_sql_query("SELECT DISTINCT Categoria FROM budget", conn)
df_subcat = pd.read_sql_query("SELECT DISTINCT Sottocategoria FROM budget WHERE Sottocategoria IS NOT NULL AND Sottocategoria != ''", conn)

categorie_esistenti = sorted(df_cat['Categoria'].dropna().unique())
sottocategorie_esistenti = sorted(df_subcat['Sottocategoria'].dropna().unique())

st.header("➕ Inserisci nuova voce")

with st.form("inserimento_form"):
    col1, col2 = st.columns(2)
    with col1:
        data = st.date_input("Data", value=datetime.today()).strftime("%Y-%m-%d")
        
categoria_selezionata = st.selectbox("Categoria esistente", categorie_esistenti, index=0 if categorie_esistenti else None)
nuova_categoria = st.text_input("...oppure scrivi una nuova categoria")
categoria = nuova_categoria if nuova_categoria else categoria_selezionata

        
sottocategoria_selezionata = st.selectbox("Sottocategoria esistente", sottocategorie_esistenti, index=0 if sottocategorie_esistenti else None)
nuova_sottocategoria = st.text_input("...oppure scrivi una nuova sottocategoria")
sottocategoria = nuova_sottocategoria if nuova_sottocategoria else sottocategoria_selezionata

    with col2:
        ammontare = st.number_input("Ammontare (€)", step=0.01)
        tipologia = st.selectbox("Tipologia", ["spesa", "ricavo"])
        note = st.text_input("Note")

    submitted = st.form_submit_button("Inserisci")

    
# === VALIDAZIONE ===
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

    if tipologia not in ["spesa", "ricavo"]:
        errori.append("⚠️ Tipologia non valida.")

    if errori:
        for e in errori:
            st.warning(e)
    else:

        cursor.execute("""
            INSERT INTO budget (Data, Categoria, Sottocategoria, Ammontare, Note, Tipologia)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (data, categoria, sottocategoria, ammontare, note, tipologia))
        conn.commit()
        st.success("✅ Voce inserita con successo!")

# === Spese mensili per categoria (barre impilate) ===
st.header("📊 Spese mensili per categoria")

df_spese = pd.read_sql_query("""
    SELECT strftime('%Y-%m', Data) AS Mese, Categoria, SUM(Ammontare) AS Totale
    FROM budget
    WHERE Tipologia = 'spesa'
    GROUP BY Mese, Categoria
    ORDER BY Mese, Categoria
""", conn)

if not df_spese.empty:
    df_spese['MeseAnno'] = df_spese['Mese'].apply(abbrevia_mese_anno)
    pivot_df = df_spese.pivot(index='MeseAnno', columns='Categoria', values='Totale').fillna(0)
    pivot_df = pivot_df.loc[sorted(pivot_df.index, key=lambda x: datetime.strptime(x, "%b %Y"))]

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

# === Andamento Ricavi / Spese / Saldo (linee) ===
st.header("📈 Trend: Ricavi / Spese / Saldo mensili")

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
    df_trend['MeseAnno'] = df_trend['Mese'].apply(abbrevia_mese_anno)
    df_trend = df_trend.set_index('MeseAnno')
    df_trend = df_trend.loc[sorted(df_trend.index, key=lambda x: datetime.strptime(x, "%b %Y"))]

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(x=df_trend.index, y=df_trend['Ricavi'], mode='lines+markers', name='Ricavi',
                                   line=dict(color='green')))
    fig_trend.add_trace(go.Scatter(x=df_trend.index, y=df_trend['Spese'], mode='lines+markers', name='Spese',
                                   line=dict(color='red')))
    fig_trend.add_trace(go.Scatter(x=df_trend.index, y=df_trend['Saldo'], mode='lines+markers', name='Saldo',
                                   line=dict(color='gold')))

    fig_trend.update_layout(
        title="Andamento Ricavi / Spese / Saldo",
        xaxis_title="Mese",
        yaxis_title="€",
        height=500
    )

    st.plotly_chart(fig_trend, use_container_width=True)

# === Torta spese per categoria ===
st.header("🥧 Distribuzione % delle Spese per Categoria")

df_torta = pd.read_sql_query("""
    SELECT Categoria, SUM(Ammontare) AS Totale
    FROM budget
    WHERE Tipologia = 'spesa'
    GROUP BY Categoria
""", conn)

if not df_torta.empty:
    fig_pie = go.Figure(data=[go.Pie(
        labels=df_torta['Categoria'],
        values=df_torta['Totale'],
        textinfo='label+percent',
        hole=0.3
    )])

    fig_pie.update_layout(title="Distribuzione % delle Spese per Categoria", height=500)
    st.plotly_chart(fig_pie, use_container_width=True)

conn.close()