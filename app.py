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

st.title("💰 Controllo Finanze")

# === Password ===
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

# === Inserimento nuova voce ===
categorie_data = supabase.table("budget").select("categoria").execute()
sottocategorie_data = supabase.table("budget").select("sottocategoria").execute()

categorie_esistenti = sorted(set(i['categoria'] for i in categorie_data.data if i['categoria']))
sottocategorie_esistenti = sorted(set(i['sottocategoria'] for i in sottocategorie_data.data if i['sottocategoria']))

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

# === Report completo ===
data_result = supabase.table("budget").select("*").execute()
df = pd.DataFrame(data_result.data)

if not df.empty:
    df["data"] = pd.to_datetime(df["data"])

    st.header("📈 Report completo")

    anni_disponibili = sorted(df["data"].dt.year.unique())
    anno_corrente = datetime.now().year
    anno_selezionato = st.selectbox("📅 Seleziona l'anno", anni_disponibili, index=anni_disponibili.index(anno_corrente) if anno_corrente in anni_disponibili else 0)
    df = df[df["data"].dt.year == anno_selezionato]

    # --- fix periodo ---
    month_map = {"01": "Gen", "02": "Feb", "03": "Mar", "04": "Apr", "05": "Mag", "06": "Giu", "07": "Lug", "08": "Ago", "09": "Set", "10": "Ott", "11": "Nov", "12": "Dic"}
    month_order = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

    df["mese_num"] = df["data"].dt.strftime("%m")
    df["periodo"] = df["mese_num"].map(month_map)
    df["periodo"] = pd.Categorical(df["periodo"], categories=month_order, ordered=True)
    # ------------------

    # === Grafici ===
    spese = df[df["tipologia"] == "spesa"]
    grouped = spese.groupby(["periodo", "categoria"])["ammontare"].sum().reset_index()
    pivot = grouped.pivot(index="periodo", columns="categoria", values="ammontare").fillna(0)

    colori_categorie = crea_colori(pivot.columns)

    fig1 = go.Figure()
    for col in pivot.columns:
        fig1.add_trace(go.Bar(name=col, x=pivot.index, y=pivot[col], marker_color=colori_categorie[col]))

    fig1.update_layout(barmode="stack", title="Spese per Categoria (Mensili)", xaxis_title="Mese", yaxis_title="€", xaxis_tickangle=-15)
    st.plotly_chart(fig1, use_container_width=True)

    trend = df.groupby(["periodo", "tipologia"])["ammontare"].sum().unstack().fillna(0)
    trend["saldo"] = trend.get("ricavo", 0) - trend.get("spesa", 0)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=trend.index, y=trend.get("ricavo", 0), name="Ricavi", line=dict(color="green")))
    fig2.add_trace(go.Scatter(x=trend.index, y=trend.get("spesa", 0), name="Spese", line=dict(color="red")))
    fig2.add_trace(go.Scatter(x=trend.index, y=trend["saldo"], name="Saldo", line=dict(color="gold")))
    fig2.update_layout(title="Andamento Ricavi / Spese / Saldo", xaxis_title="Mese", yaxis_title="€")
    st.plotly_chart(fig2, use_container_width=True)

    torta = spese.groupby("categoria")["ammontare"].sum()
    colori_categorie_torta = crea_colori(torta.index)

    fig3 = go.Figure(data=[go.Pie(
        labels=torta.index,
        values=torta.values,
        marker_colors=[colori_categorie_torta[cat] for cat in torta.index],
        hole=0.3
    )])
    fig3.update_layout(title="Distribuzione % delle Spese")
    st.plotly_chart(fig3, use_container_width=True)

    # === Filtri database ===
    st.subheader("🧰 Filtra i dati del database")

    tipologie = df["tipologia"].dropna().unique().tolist()
    tipologia_sel = st.selectbox("📌 Tipologia", ["Tutte"] + tipologie)
    mesi_disponibili = df["data"].dt.strftime("%b").unique().tolist()
    mese_sel = st.selectbox("📅 Mese", ["Tutti"] + mesi_disponibili)
    testo_libero = st.text_input("🔍 Cerca per categoria / sottocategoria / note").strip().lower()

    min_amm, max_amm = float(df["ammontare"].min()), float(df["ammontare"].max())
    ammontare_range = st.slider("💶 Filtro per ammontare (€)", min_amm, max_amm, (min_amm, max_amm))

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
    filtro_df = filtro_df[
        (filtro_df["ammontare"] >= ammontare_range[0]) & (filtro_df["ammontare"] <= ammontare_range[1])
    ]

    with st.expander("📋 Visualizza dati filtrati"):
        if not filtro_df.empty:
            st.dataframe(filtro_df.sort_values("data", ascending=False), use_container_width=True)
        else:
            st.info("Nessun dato corrisponde ai filtri selezionati.")

    # === Gestione Record ===
    st.header("🛠️ Gestione Record")

    with st.expander("✏️ Modifica o Cancella un Record"):
        record_selezionato = st.selectbox("Seleziona un record", df.index)

        if record_selezionato is not None:
            record = df.loc[record_selezionato]

            with st.form("modifica_form"):
                nuova_data = st.date_input("Data", value=record["data"]).strftime("%Y-%m-%d")
                nuova_categoria = st.text_input("Categoria", value=record["categoria"])
                nuova_sottocategoria = st.text_input("Sottocategoria", value=record["sottocategoria"])
                nuovo_ammontare = st.number_input("Ammontare (€)", value=float(record["ammontare"]), step=0.01)
                nuova_note = st.text_input("Note", value=record["note"])
                nuova_tipologia = st.selectbox("Tipologia", ["spesa", "ricavo"], index=0 if record["tipologia"] == "spesa" else 1)

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
    st.info("Nessun dato ancora disponibile.")