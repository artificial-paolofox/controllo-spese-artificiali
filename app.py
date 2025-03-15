import pandas as pd
import plotly.graph_objects as go

# Carica CSV
df = pd.read_csv("budget_rows.csv")
df["data"] = pd.to_datetime(df["data"], errors="coerce")
df["ammontare"] = pd.to_numeric(df["ammontare"], errors="coerce")

# Ordine mesi
month_order = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
               "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
df["mese"] = pd.Categorical(df["data"].dt.strftime("%b"), categories=month_order, ordered=True)

# Raggruppamento e calcolo saldo
grouped = df.groupby(["mese", "tipologia"])["ammontare"].sum().unstack().fillna(0)
grouped["saldo"] = grouped.get("ricavo", 0) - grouped.get("spesa", 0)
grouped = grouped.reindex(month_order).fillna(0)

# Grafico
fig = go.Figure()
fig.add_trace(go.Scatter(x=grouped.index, y=grouped.get("ricavo", 0), name="Ricavi", line=dict(color="green")))
fig.add_trace(go.Scatter(x=grouped.index, y=grouped.get("spesa", 0), name="Spese", line=dict(color="red")))
fig.add_trace(go.Scatter(x=grouped.index, y=grouped["saldo"], name="Saldo", line=dict(color="gold")))
fig.update_layout(title="Trend Mensile Ricavi / Spese / Saldo", xaxis_title="Mese", yaxis_title="€")

fig.show()