# === Protezione con password + logout ===
import streamlit as st

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
            st.experimental_rerun()

check_password()



import pandas as pd
from supabase import create_client, Client

# === Supabase Config ===
url = "https://sjoryqgtggoukbqviqqe.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNqb3J5cWd0Z2dvdWticXZpcXFlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDE5NzA4MTEsImV4cCI6MjA1NzU0NjgxMX0.LMIJ4SZncXI4YvpLOvBwlS98wOUnBvwRhGY_Hnjw460"
supabase: Client = create_client(url, key)

# === App ===
st.title("💰 Budget Manager - Tabella Filtrabile")

# Carica dati
data_result = supabase.table("budget").select("*").execute()
df = pd.DataFrame(data_result.data)

if not df.empty:
    df["data"] = pd.to_datetime(df["data"])
    # Forza ordine mesi per non saltare 'Gen' nei grafici
    month_order = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", 
                   "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    df["mese"] = pd.Categorical(df["data"].dt.strftime("%b"), categories=month_order, ordered=True)

    st.subheader("🧰 Filtra i dati del database")
    tipologie = df["tipologia"].dropna().unique().tolist()
    tipologia_sel = st.selectbox("📌 Tipologia", ["Tutte"] + tipologie)
    mesi_disponibili = df["mese"].dropna().unique().tolist()
    mese_sel = st.selectbox("📅 Mese", ["Tutti"] + list(mesi_disponibili))
    testo_libero = st.text_input("🔍 Cerca per categoria / sottocategoria / note").strip().lower()
    min_amm, max_amm = float(df["ammontare"].min()), float(df["ammontare"].max())
    ammontare_range = st.slider("💶 Filtro per ammontare (€)", min_amm, max_amm, (min_amm, max_amm))

    filtro_df = df.copy()
    if tipologia_sel != "Tutte":
        filtro_df = filtro_df[filtro_df["tipologia"] == tipologia_sel]
    if mese_sel != "Tutti":
        filtro_df = filtro_df[filtro_df["mese"] == mese_sel]
    if testo_libero:
        filtro_df = filtro_df[
            filtro_df["categoria"].str.lower().str.contains(testo_libero) |
            filtro_df["sottocategoria"].str.lower().str.contains(testo_libero) |
            filtro_df["note"].str.lower().str.contains(testo_libero)
        ]
    filtro_df = filtro_df[
        (filtro_df["ammontare"] >= ammontare_range[0]) & (filtro_df["ammontare"] <= ammontare_range[1])
    ]

    with st.expander("📋 Visualizza dati grezzi dal database"):
        if not filtro_df.empty:
            st.dataframe(filtro_df.sort_values("data", ascending=False), use_container_width=True)
        else:
            st.info("Nessun dato corrisponde ai filtri selezionati.")
else:
    st.info("📭 Nessun dato disponibile nel database.")