"""All Plotly chart builders for the dashboard."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data.fetcher import GROCERIES, SERIES

# Same tokens as feelings/template.html; both palettes pass the colorblind checks
# against their own background.
PALETTES = {
    "light": dict(stocks="#4a67b5", income="#d99a1c", gdp="#2f9a84", rent="#e0503f", food="#8b52a8",
                  ink="#23212a", ink2="#55525c", ink3="#85818c", rule="#d2cdc3", surface="#f3f0ea", bg="#e9e5dd"),
    "dark": dict(stocks="#6a84d2", income="#b88626", gdp="#38a88f", rent="#e15f4b", food="#a06fc2",
                 ink="#ecebef", ink2="#b4b2bb", ink3="#807d89", rule="#34333c", surface="#25242c", bg="#1c1b22"),
}
COLORS = dict(PALETTES["light"])
LAYOUT = {}
MONO = "IBM Plex Mono, ui-monospace, monospace"


def set_theme(mode):
    """Point COLORS and LAYOUT at the light or dark palette. Call once per run."""
    COLORS.clear()
    COLORS.update(PALETTES["dark" if mode == "dark" else "light"])
    c = COLORS
    axis = dict(gridcolor=c["rule"], linecolor=c["rule"], zeroline=False, showline=False, automargin=True,
                tickfont=dict(family=MONO, size=12, color=c["ink2"]),
                title_font=dict(size=13, color=c["ink2"]))
    LAYOUT.clear()
    LAYOUT.update(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    font=dict(family=MONO, size=12, color=c["ink"])),
        margin=dict(l=8, r=12, t=48, b=8),
        height=460,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Atkinson Hyperlegible, sans-serif", color=c["ink"]),
        hoverlabel=dict(bgcolor=c["ink"], font=dict(color=c["bg"], family="Atkinson Hyperlegible, sans-serif"),
                        bordercolor=c["ink"]),
        xaxis={**axis, "showgrid": False, "showline": True, "ticks": "outside", "tickcolor": c["rule"]},
        yaxis=axis,
    )


def _style_axes(fig):
    """Apply the axis style to every subplot axis, not just the first."""
    fig.update_xaxes(**LAYOUT["xaxis"])
    fig.update_yaxes(**LAYOUT["yaxis"])
    fig.update_annotations(font=dict(family="Young Serif, serif", size=14, color=COLORS["ink"]))
    return fig


set_theme("light")


def index_to_base(df, base_year):
    """Index each column to base_year = 100.

    A series with no data in base_year (e.g. FRED's S&P 500, which only covers
    the last 10 years) is indexed to its own first available year instead.
    Returns (indexed_df, {column: year actually used as base}).
    """
    indexed, bases = df.copy(), {}
    for col in df.columns:
        s = df[col].dropna()
        s = s[s.index >= base_year]
        if s.empty:
            indexed[col] = float("nan")
            continue
        bases[col] = s.index[0]
        indexed[col] = df[col] / s.iloc[0] * 100
    return indexed, bases


def indexed_chart(df, base_year):
    indexed, bases = index_to_base(df, base_year)
    fig = go.Figure()
    for key in df.columns:
        label = SERIES[key][1]
        rebased = key in bases and bases[key] != base_year
        if rebased:
            label += f" ({bases[key]}=100)"
        fig.add_trace(go.Scatter(
            x=indexed.index, y=indexed[key], name=label, mode="lines+markers",
            line=dict(color=COLORS[key], width=2, dash="dash" if rebased else "solid"), marker=dict(size=6),
            hovertemplate="%{y:.1f}",
        ))
    fig.add_hline(y=100, line=dict(color=COLORS["ink3"], width=1, dash="dot"))
    fig.update_layout(**LAYOUT, yaxis_title=f"Index ({base_year} = 100)")
    return fig


def absolute_chart(df, units=None):
    """Small multiples, since the series have incompatible units."""
    units = units or {k: SERIES[k][2] for k in df.columns}
    keys = list(df.columns)
    fig = make_subplots(
        rows=len(keys), cols=1, shared_xaxes=True, vertical_spacing=0.04,
        subplot_titles=[f"{SERIES[k][1]} — {units[k]}" for k in keys],
    )
    for i, key in enumerate(keys, start=1):
        fig.add_trace(go.Scatter(
            x=df.index, y=df[key], name=SERIES[key][1], mode="lines+markers",
            line=dict(color=COLORS[key], width=2), hovertemplate="%{y:,.1f}",
        ), row=i, col=1)
    fig.update_layout(**{**LAYOUT, "height": 170 * len(keys)}, showlegend=False)
    _style_axes(fig)
    fig.update_annotations(x=0, xanchor="left")
    return fig


def divergence_chart(df):
    """Filled gap between stocks and median household income.

    Both are indexed to their first common year so the gap starts at zero.
    """
    both = df[["stocks", "income"]].dropna()
    if both.empty:
        return None, None
    base = both.index[0]
    idx = both / both.iloc[0] * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=idx.index, y=idx["income"], name=SERIES["income"][1],
        line=dict(color=COLORS["income"], width=2), hovertemplate="%{y:.1f}",
    ))
    fig.add_trace(go.Scatter(
        x=idx.index, y=idx["stocks"], name=SERIES["stocks"][1],
        line=dict(color=COLORS["stocks"], width=2), fill="tonexty",
        fillcolor=_alpha(COLORS["stocks"], 0.18), hovertemplate="%{y:.1f}",
    ))
    fig.update_layout(**{**LAYOUT, "height": 380}, yaxis_title=f"Index ({base} = 100)")
    return fig, base


def rent_burden_map(df):
    fig = go.Figure(go.Choropleth(
        locations=df["abbr"], z=df["rent_burden"], locationmode="USA-states",
        colorscale="RdYlGn_r", text=df["state_name"],
        hovertemplate="<b>%{text}</b><br>Rent burden: %{z:.1f}%<extra></extra>",
        colorbar=dict(title="% of income", ticksuffix="%"),
        marker_line_color=COLORS["surface"],
    ))
    fig.update_layout(
        geo=dict(scope="usa", projection_type="albers usa", bgcolor="rgba(0,0,0,0)", lakecolor="rgba(0,0,0,0)"),
        paper_bgcolor="rgba(0,0,0,0)", font=LAYOUT["font"],
        margin=dict(l=0, r=0, t=10, b=0), height=460,
    )
    return fig


def rent_hours_chart(hours):
    """Hours of work at the average hourly wage to pay a month's rent."""
    fig = go.Figure(go.Scatter(
        x=hours.index, y=hours["rent"], mode="lines+markers", name="Hours for a month's rent",
        line=dict(color=COLORS["rent"], width=2),
        customdata=hours[["rent_dollars", "wage"]],
        hovertemplate="%{y:.1f} hours<br>$%{customdata[0]:,.0f} rent ÷ $%{customdata[1]:.2f}/hr<extra></extra>",
    ))
    lo, hi = hours["rent"].min(), hours["rent"].max()
    pad = max(2, (hi - lo) * 0.6)
    fig.update_layout(**{**LAYOUT, "height": 320, "yaxis": {**LAYOUT["yaxis"], "title": "Hours of work",
                                                            "range": [lo - pad, hi + pad]}},
                      showlegend=False)
    return fig


def grocery_minutes_chart(hours):
    """Minutes of work per staple, one small panel each (prices move on different scales)."""
    keys = list(GROCERIES)
    fig = make_subplots(rows=1, cols=len(keys), subplot_titles=[GROCERIES[k][1].replace("A pound of ", "").replace("A gallon of ", "").replace("A dozen ", "").capitalize() for k in keys],
                        horizontal_spacing=0.05)
    for i, k in enumerate(keys, start=1):
        fig.add_trace(go.Scatter(
            x=hours.index, y=hours[k], mode="lines", name=GROCERIES[k][1],
            line=dict(color=COLORS["food"], width=2),
            customdata=hours[[k + "_price", "wage"]],
            hovertemplate="%{y:.1f} min<br>$%{customdata[0]:.2f} ÷ $%{customdata[1]:.2f}/hr<extra></extra>",
        ), row=1, col=i)
        fig.update_yaxes(rangemode="tozero", row=1, col=i)
    fig.update_yaxes(title_text="Minutes of work", row=1, col=1)
    fig.update_layout(**{**LAYOUT, "height": 300, "hovermode": "closest"}, showlegend=False)
    _style_axes(fig)
    return fig


def _alpha(hex_color, a):
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}, {a})"
