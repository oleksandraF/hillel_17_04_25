# app.py — Belgium — Self-Employed Market Analysis (2017–2023)
import os
import numpy as np
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output

DATA_DIR = os.path.join("data", "processed")
SELF_FILE = "self_employed_entrepreneurs_BE_2017_2025.csv"

def read_csv(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    return pd.read_csv(path)

df_self = read_csv(os.path.join(DATA_DIR, SELF_FILE))
df_self["year"] = pd.to_numeric(df_self["year"], errors="coerce").astype("Int64")
df_self["entrepreneurs"] = pd.to_numeric(df_self["entrepreneurs"], errors="coerce")

country_ts = (
    df_self.groupby("year", as_index=False)["entrepreneurs"]
           .sum()
           .sort_values("year")
)

min_year = int(country_ts["year"].min())
max_year = int(country_ts["year"].max()) 
total_latest = int(country_ts.loc[country_ts["year"] == max_year, "entrepreneurs"].values[0])

def pct_fmt(v): 
    return "—" if v is None or np.isnan(v) else f"{v:.1f}%"

# YoY (Year-over-Year) change
yoy_last = None
if len(country_ts) >= 2 and (max_year - 1) in country_ts["year"].values:
    last = country_ts.loc[country_ts["year"] == max_year, "entrepreneurs"].values[0]
    prev = country_ts.loc[country_ts["year"] == max_year - 1, "entrepreneurs"].values[0]
    yoy_last = (last / prev - 1.0) * 100.0

# CAGR (Compound Annual Growth Rate)
cagr_all = None
if max_year > min_year:
    v0 = country_ts.loc[country_ts["year"] == min_year, "entrepreneurs"].values[0]
    v1 = country_ts.loc[country_ts["year"] == max_year, "entrepreneurs"].values[0]
    if v0 > 0:
        cagr_all = ((v1 / v0) ** (1 / (max_year - min_year)) - 1) * 100.0

BASE_YEAR = 2019
COVID_YEAR = 2020
v_2019 = country_ts.loc[country_ts["year"] == BASE_YEAR, "entrepreneurs"].values[0] if BASE_YEAR in country_ts["year"].values else None
v_2020 = country_ts.loc[country_ts["year"] == COVID_YEAR, "entrepreneurs"].values[0] if COVID_YEAR in country_ts["year"].values else None
v_latest = total_latest

covid_dip = None        
recovery_vs_2019 = None   
time_to_recover = "Not yet"
post_covid_cagr = None 

if v_2019 and v_2020 and v_2019 > 0:
    covid_dip = (v_2020 / v_2019 - 1) * 100.0
    recovery_vs_2019 = (v_latest / v_2019 - 1) * 100.0

    after_2019 = country_ts[country_ts["year"] >= BASE_YEAR]
    rec_year = after_2019.loc[after_2019["entrepreneurs"] >= v_2019, "year"]
    if len(rec_year):
        time_to_recover = int(rec_year.iloc[0] - BASE_YEAR)
    else:
        time_to_recover = "Not yet"

if v_2020 and v_latest and v_2020 > 0 and max_year > COVID_YEAR:
    post_covid_cagr = ((v_latest / v_2020) ** (1 / (max_year - COVID_YEAR)) - 1) * 100.0

app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Belgium — Self-Employed (2017–2023)"

CARD = {"border":"1px solid #e9ecef","borderRadius":"6px","padding":"12px 16px","background":"#fff",
        "boxShadow":"0 1px 2px rgba(0,0,0,0.04)"}
HINT = {"color":"#6c757d","fontSize":"12px"}

def overview_layout():
    fig = px.line(country_ts, x="year", y="entrepreneurs", markers=True,
                  title="Self-employed by year (COVID period highlighted)")
    fig.update_layout(yaxis_title="People", xaxis_title="Year")


    x0 = COVID_YEAR - 0.5
    x1 = min(max_year, 2021) + 0.5
    fig.add_vrect(x0=x0, x1=x1, fillcolor="red", opacity=0.08, line_width=0)


    covid_row = country_ts[country_ts["year"].between(COVID_YEAR, min(max_year, 2021))]
    if not covid_row.empty:
        y_min = covid_row["entrepreneurs"].min()
        x_min = int(covid_row.loc[covid_row["entrepreneurs"].idxmin(), "year"])
        fig.add_annotation(x=x_min, y=y_min,
                           text=f"Min {x_min}: {y_min:,.0f}".replace(",", " "),
                           showarrow=True, arrowhead=3, yshift=12)

    yoy_fig = px.bar(country_ts.assign(yoy=lambda d: d["entrepreneurs"].pct_change()*100.0),
                     x="year", y="yoy", title="YoY growth (%)").update_layout(yaxis_title="%")

    return html.Div([
        html.Div([
            html.Div([html.Div("Total self-employed (latest)", style=HINT),
                      html.H2(f"{total_latest:,.0f}".replace(",", " "))], style=CARD),
            html.Div([html.Div("YoY change, %", style=HINT),
                      html.H2(pct_fmt(yoy_last))], style={**CARD, "marginLeft":"10px"}),
            html.Div([html.Div(f"CAGR {min_year}–{max_year}, %", style=HINT),
                      html.H2(pct_fmt(cagr_all))], style={**CARD, "marginLeft":"10px"}),
            html.Div([html.Div("COVID dip (2020 vs 2019), %", style=HINT),
                      html.H2(pct_fmt(covid_dip))], style={**CARD, "marginLeft":"10px"}),
            html.Div([html.Div("Recovery vs 2019, %", style=HINT),
                      html.H2(pct_fmt(recovery_vs_2019))], style={**CARD, "marginLeft":"10px"}),
            html.Div([html.Div("Time to recover (years)", style=HINT),
                      html.H2(str(time_to_recover))], style={**CARD, "marginLeft":"10px"}),
            html.Div([html.Div(f"Post-COVID CAGR (2020–{max_year}), %", style=HINT),
                      html.H2(pct_fmt(post_covid_cagr))], style={**CARD, "marginLeft":"10px"}),
        ], style={"display":"flex","flexWrap":"wrap","gap":"8px"}),

        html.Div(style={"height":"10px"}),

        html.Div([dcc.Graph(figure=fig)], style=CARD),
        html.Div(style={"height":"10px"}),
        html.Div([dcc.Graph(figure=yoy_fig)], style=CARD),
    ])

def regions_layout():
    years = sorted(country_ts["year"].dropna().astype(int).tolist())
    return html.Div([
        html.Div([html.Label("Year:", style=HINT),
                  dcc.Dropdown(id="dd_year_regions",
                               options=[{"label":str(y), "value":y} for y in years],
                               value=max_year, clearable=False, style={"width":"200px"})],
                 style={"marginBottom":"8px"}),
        html.Div([dcc.Graph(id="fig_regions")], style=CARD)
    ])

def sectors_layout():
    years = sorted(country_ts["year"].dropna().astype(int).tolist())
    return html.Div([
        html.Div([html.Label("Year:", style=HINT),
                  dcc.Dropdown(id="dd_year_sectors",
                               options=[{"label":str(y), "value":y} for y in years],
                               value=max_year, clearable=False, style={"width":"200px"})],
                 style={"marginBottom":"8px"}),
        html.Div([dcc.Graph(id="fig_sectors_top")], style=CARD)
    ])

def demo_layout():
    regions = sorted(df_self["region_name_en"].dropna().unique().tolist())
    years = sorted(country_ts["year"].dropna().astype(int).tolist())
    default_region = regions[0] if regions else None
    return html.Div([
        html.Div(style={"display":"flex","gap":"12px"}, children=[
            html.Div([html.Label("Year:", style=HINT),
                      dcc.Dropdown(id="dd_year_demo",
                                   options=[{"label":str(y), "value":y} for y in years],
                                   value=max_year, clearable=False, style={"width":"150px"})]),
            html.Div([html.Label("Region:", style=HINT),
                      dcc.Dropdown(id="dd_region_demo",
                                   options=[{"label":r, "value":r} for r in regions],
                                   value=default_region, clearable=False, style={"width":"320px"})]),
        ]),
        html.Div(style={"height":"8px"}),
        html.Div([dcc.Graph(id="fig_gender")], style=CARD),
        html.Div(style={"height":"8px"}),
        html.Div([dcc.Graph(id="fig_age")], style=CARD),
    ])

app.layout = html.Div(style={"fontFamily":"Segoe UI, Roboto, Arial, sans-serif",
                             "background":"#f7f8fa","padding":"12px 16px"}, children=[
    html.H3("Belgium — Self-Employed Market Analysis (2017–2023)", style={"margin":"6px 0 12px"}),
    dcc.Tabs(id="tabs", value="tab-overview", children=[
        dcc.Tab(label="Overview", value="tab-overview"),
        dcc.Tab(label="Regions", value="tab-regions"),
        dcc.Tab(label="Sectors", value="tab-sectors"),
        dcc.Tab(label="Demographics", value="tab-demo"),
    ]),
    html.Div(id="tab-content", style={"marginTop":"14px"})
])

@app.callback(Output("tab-content","children"), Input("tabs","value"))
def render_tab(tab):
    if tab == "tab-overview":  return overview_layout()
    if tab == "tab-regions":   return regions_layout()
    if tab == "tab-sectors":   return sectors_layout()
    if tab == "tab-demo":      return demo_layout()
    return html.Div("…")

# Regions
@app.callback(Output("fig_regions","figure"), Input("dd_year_regions","value"))
def update_regions(year):
    d = (df_self[df_self["year"] == year]
         .groupby("region_name_en", as_index=False)["entrepreneurs"].sum()
         .sort_values("entrepreneurs", ascending=False))
    if d.empty: 
        return px.bar(title="No data for selected year")
    fig = px.bar(d, x="region_name_en", y="entrepreneurs",
                 title=f"Self-employed by region — {year}", text_auto=".3s")
    fig.update_layout(xaxis_title="", yaxis_title="People")
    return fig

# Sectors
@app.callback(Output("fig_sectors_top","figure"), Input("dd_year_sectors","value"))
def update_sectors(year):
    d = (df_self[df_self["year"] == year]
         .groupby("sector_name_en", as_index=False)["entrepreneurs"].sum()
         .sort_values("entrepreneurs", ascending=False)
         .head(12))
    if d.empty:
        return px.bar(title="No data for selected year")
    fig = px.bar(d, y="sector_name_en", x="entrepreneurs", orientation="h",
                 title=f"Top sectors — self-employed (year={year})", text_auto=".3s")
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_layout(xaxis_title="People", yaxis_title="")
    return fig

# Demographics
@app.callback(Output("fig_gender","figure"),
              Output("fig_age","figure"),
              Input("dd_year_demo","value"),
              Input("dd_region_demo","value"))
def update_demo(year, region):
    d = df_self[(df_self["year"] == year) & (df_self["region_name_en"] == region)]
    g = d.groupby("gender_name_en", as_index=False)["entrepreneurs"].sum().rename(columns={"entrepreneurs":"people"})
    a = d.groupby("age_group_en", as_index=False)["entrepreneurs"].sum().rename(columns={"entrepreneurs":"people"})
    order = ["< 30 years","30 - 39 years","40 - 49 years","50 - 59 years","> 60 years"]
    if set(order).issuperset(set(a["age_group_en"].unique())):
        a["age_group_en"] = pd.Categorical(a["age_group_en"], categories=order, ordered=True)
        a = a.sort_values("age_group_en")

    fig_g = px.pie(g, values="people", names="gender_name_en",
                   title=f"Gender — {region} ({year})", hole=0.35)
    fig_g.update_traces(textposition="inside", textinfo="percent+label")

    fig_a = px.bar(a, x="age_group_en", y="people",
                   title=f"Age — {region} ({year})", text_auto=".3s")
    fig_a.update_layout(xaxis_title="", yaxis_title="Entrepreneurs")
    return fig_g, fig_a

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
