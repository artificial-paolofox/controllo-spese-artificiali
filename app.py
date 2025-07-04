import streamlit as st 
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from datetime import datetime
from supabase import create_client, Client
import random

# Palette fissa
palette = [ '#FFFFFF',  # Magenta fluo
    '#00FFFF',  # Ciano fluo
    '#FF5F1F',  # Arancione neon
    '#FFFF00',  # Giallo fluo
    '#39FF14',  # Verde lime fluo
    '#FF1493',  # Rosa shocking
    '#1E90FF',  # Blu neon
    '#FF073A',  # Rosso fluo brillante
    '#8A2BE2',  # Viola fluo
    '#FFFFFF'   # Bianco puro (nuovo!)
    ]

# Dizionario per associare colori alle categorie
colori_categorie = {}

# Funzione per ottenere un colore coerente per ogni categoria
def get_colore(categoria):
    if categoria in colori_categorie:
        return colori_categorie[categoria]
    else:
        if len(colori_categorie) < len(palette):
            colore = palette[len(colori_categorie)]
        else:
            colore = "#%06x" % random.randint(0, 0xFFFFFF)
        colori_categorie[categoria] = colore
        return colore

# === Supabase Config ===
url = "https://sjoryqgtggoukbqviqqe.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNqb3J5cWd0Z2dvdWticXZpcXFlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDE5NzA4MTEsImV4cCI6MjA1NzU0NjgxMX0.LMIJ4SZncXI4YvpLOvBwlS98wOUnBvwRhGY_Hnjw460"

supabase: Client = create_client(url, key)

st.title("💰 Controllo della Finanza")

# === Protezione con password + logout ===
def check_password():
    def password_entered():
        if st.session_state["password"] == "ciaobudget":
            st.session_state["autenticato"] = True
        else:
            st.session_state["autenticato"] = False

    if "autenticato" not in st.session_state:
        st.text_input("🔐 Inserisci password:", type="password", on_change=password_entered, key="password")
        st.stop()
    elif not st.session_state["autenticato"]:
        st.text_input("🔐 Inserisci password:", type="password", on_change=password_entered, key="password")
        st.warning("❌ Password errata")
        st.stop()
    else:
        if st.button("🔓 Logout"):
            st.session_state["autenticato"] = False
            st.rerun()

check_password()

# === Inserimento ===
# Recupera dati categorie e sottocategorie (PRIMA di aprire il form)
categorie_data = supabase.table("budget").select("categoria").execute()
sottocategorie_data = supabase.table("budget").select("sottocategoria").execute()

categorie_esistenti = sorted(set(i['categoria'] for i in categorie_data.data if i['categoria']))
sottocategorie_esistenti = sorted(set(i['sottocategoria'] for i in sottocategorie_data.data if i['sottocategoria']))

# Ora l'expander con il form dentro
with st.expander("➕ Inserisci nuova voce"):
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

                # === Caricamento dati dal database ===
data_result = supabase.table("budget").select("*").execute()
if data_result.data:
    df = pd.DataFrame(data_result.data)
else:
    df = pd.DataFrame()  # Evita crash se non ci sono dati


with st.expander("✏️ Modifica o elimina un record"):
    df["data"] = pd.to_datetime(df["data"])  # ✅ Conversione in datetime
    if not df.empty:
        df_sorted = df.sort_values("data", ascending=False).reset_index(drop=True)
        record_index = st.selectbox("Seleziona il record da modificare/eliminare", df_sorted.index, format_func=lambda i: f"{df_sorted.loc[i, 'data'].date()} | {df_sorted.loc[i, 'categoria']} | {df_sorted.loc[i, 'ammontare']}€")

        record = df_sorted.loc[record_index]

        # Campi precompilati
        mod_data = st.date_input("Data", value=record["data"])
        mod_categoria = st.text_input("Categoria", value=record["categoria"])
        mod_sottocategoria = st.text_input("Sottocategoria", value=record["sottocategoria"])
        mod_ammontare = st.number_input("Ammontare (€)", value=record["ammontare"], step=0.01)
        mod_note = st.text_input("Note", value=record["note"] or "")
        mod_tipologia = st.selectbox("Tipologia", ["spesa", "ricavo"], index=0 if record["tipologia"] == "spesa" else 1)

        # Azioni
        col_mod, col_del = st.columns(2)
        with col_mod:
            if st.button("💾 Salva Modifiche"):
              try:
                  supabase.table("budget").update({
                  "data": mod_data.strftime("%Y-%m-%d"),
                  "categoria": mod_categoria,
                  "sottocategoria": mod_sottocategoria,
                  "ammontare": mod_ammontare,
                  "note": mod_note,
                  "tipologia": mod_tipologia
                  }).eq("id", record["id"]).execute()
                  st.success("✅ Modifica salvata. Ricarica la pagina.")
                  st.experimental_rerun()
              except Exception as e:
                   st.error(f"Errore: {e}")


        with col_del:
            if st.button("🗑️ Elimina Record"):
               try:
                 supabase.table("budget").delete().eq("id", record["id"]).execute()
                 st.success("✅ Record eliminato. Ricarica la pagina.")
                 st.experimental_rerun()
               except Exception as e:
                st.error(f"Errore: {e}")

    else:
        st.info("Nessun dato disponibile per la modifica o l'eliminazione.")

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
        fig1.add_trace(go.Bar(name=col, x=pivot.index, y=pivot[col], marker_color=get_colore(col)))

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

    fig3 = go.Figure(data=[go.Pie(
        labels=torta.index,
        values=torta.values,
        marker_colors=[get_colore(cat) for cat in torta.index],
        hole=0.3
    )])
    fig3.update_layout(title="Distribuzione % delle Spese")
    st.plotly_chart(fig3, use_container_width=True)

else:
    st.info("Nessun dato ancora disponibile.")

# === Visualizza tabella completa con filtri ===
st.subheader("🧰 Filtra i dati del database")



# Filtro per tipologia
tipologie = df["tipologia"].dropna().unique().tolist()
tipologia_sel = st.selectbox("📌 Tipologia", ["Tutte"] + tipologie)

# Filtro per mese
mesi_disponibili = df["data"].dt.strftime("%b").unique().tolist()
mese_sel = st.selectbox("📅 Mese", ["Tutti"] + mesi_disponibili)

# Filtro per categoria o note
testo_libero = st.text_input("🔍 Cerca per categoria / sottocategoria / note").strip().lower()


# Applica i filtri
filtro_df = df.copy()
if tipologia_sel != "Tutte":
    filtro_df = filtro_df[filtro_df["tipologia"] == tipologia_sel]
if mese_sel != "Tutti":
    filtro_df = filtro_df[filtro_df["data"].dt.strftime("%b") == mese_sel]
if testo_libero:
    filtro_df = filtro_df[
        filtro_df["categoria"].str.lower().str.contains(testo_libero) |
        filtro_df["sottocategoria"].str.lower().str.contains(testo_libero) |
        filtro_df["note"].str.lower().str.contains(testo_libero)
    ]


# Visualizza la tabella filtrata
with st.expander("📋 Visualizza dati grezzi dal database"):
    if not filtro_df.empty:
        st.dataframe(filtro_df.sort_values("data", ascending=False), use_container_width=True)
    else:
        st.info("Nessun dato corrisponde ai filtri selezionati.")



