"""All Plotly chart builders for the dashboard.

Pudding-style night stage: cream ink on warm near-black, purple for stocks against
gold for household income, and anything outside the current focus fades back.
The five series colors pass the colorblind checks against #191817 in this order.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data.fetcher import GROCERIES, SERIES

COLORS = dict(
    stocks="#9a4fc6", income="#c4870b", gdp="#14a49b", rent="#db4a28", food="#cc6ab4",
    ink="#fffad7", ink2="#cfc9ac", ink3="#8f8a77", rule="#3a3733", surface="#24221f", bg="#191817",
)
# Lighter tints of the same hues, for colored words in running text (>= 4.5:1 on bg).
TEXT = dict(stocks="#d795ff", income="#ffb102", gdp="#5fd3c9", rent="#ff8a65", food="#f29bdc")

HEADLINE = ("stocks", "gdp")
HOUSEHOLD = ("income", "rent", "food")
FADED = 0.15

SANS = "DM Sans, -apple-system, Helvetica, Arial, sans-serif"
MONO = "DM Mono, Menlo, monospace"
SERIF = "Young Serif, Georgia, serif"

_axis = dict(gridcolor=COLORS["rule"], linecolor=COLORS["rule"], zeroline=False, showline=False,
             automargin=True, tickfont=dict(family=MONO, size=12, color=COLORS["ink3"]),
             title_font=dict(family=SANS, size=13, color=COLORS["ink3"]))
LAYOUT = dict(
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(family=SANS, size=13, color=COLORS["ink"])),
    margin=dict(l=8, r=12, t=48, b=8),
    height=460,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family=SANS, color=COLORS["ink"]),
    hoverlabel=dict(bgcolor=COLORS["ink"], bordercolor=COLORS["ink"],
                    font=dict(family=SANS, color=COLORS["bg"], size=13)),
    xaxis={**_axis, "showgrid": False, "showline": True, "ticks": "outside", "tickcolor": COLORS["rule"],
           "showspikes": True, "spikemode": "across", "spikethickness": 1, "spikecolor": COLORS["ink3"],
           "spikedash": "dot"},
    yaxis=_axis,
)


def _alpha(hex_color, a):
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}, {a})"


def _fit_x(fig, years):
    """Pin the x-axis to the data's years (endpoint labels otherwise stretch it)."""
    fig.update_xaxes(range=[min(years) - 0.4, max(years) + 0.4])
    return fig


def _style_axes(fig):
    """Apply the axis style to every subplot axis, not just the first."""
    fig.update_xaxes(**LAYOUT["xaxis"])
    fig.update_yaxes(**LAYOUT["yaxis"])
    fig.update_annotations(font=dict(family=SERIF, size=14, color=COLORS["ink"]))
    return fig


def _line(key, x, y, name, focus, **kw):
    """A series line: bold when in focus (or no focus set), faded when not."""
    dim = bool(focus) and key not in focus
    return go.Scatter(
        x=x, y=y, name=name, mode="lines",
        line=dict(color=COLORS[key], width=2 if dim else 2.75, shape="spline", smoothing=0.4),
        opacity=FADED if dim else 1, **kw,
    )


def _end_label(fig, key, x, y, text, row=None, col=None):
    """Emphasized endpoint plus a direct label in ink (the dot carries the color)."""
    kw = dict(row=row, col=col) if row else {}
    fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers", showlegend=False, hoverinfo="skip",
                             marker=dict(size=9, color=COLORS[key], line=dict(width=2, color=COLORS["bg"]))), **kw)
    fig.add_annotation(x=x, y=y, text=text, showarrow=False, xanchor="left", xshift=10,
                       font=dict(family=SANS, size=13, color=COLORS["ink"]), **kw)


def index_to_base(df, base_year):
    """Index each column to base_year = 100.

    A series with no data in base_year is indexed to its own first available year instead.
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


def indexed_chart(df, base_year, focus=None):
    indexed, bases = index_to_base(df, base_year)
    fig = go.Figure()
    for key in df.columns:
        label = SERIES[key][1]
        if key in bases and bases[key] != base_year:
            label += f" ({bases[key]}=100)"
        fig.add_trace(_line(key, indexed.index, indexed[key], label, focus, hovertemplate="%{y:.1f}"))
    fig.add_hline(y=100, line=dict(color=COLORS["ink3"], width=1, dash="dot"))
    for key in (focus or ()):
        s = indexed[key].dropna()
        if len(s):
            _end_label(fig, key, s.index[-1], s.iloc[-1], f"{SERIES[key][1]} {s.iloc[-1] - 100:+.0f}%".replace("-", "−"))
    fig.update_layout(**{**LAYOUT, "margin": {**LAYOUT["margin"], "r": 210 if focus else 12}},
                      yaxis_title=f"Index ({base_year} = 100)")
    return _fit_x(fig, df.index)


def absolute_chart(df, units=None, focus=None):
    """Small multiples, since the series have incompatible units."""
    units = units or {k: SERIES[k][2] for k in df.columns}
    keys = list(df.columns)
    fig = make_subplots(
        rows=len(keys), cols=1, shared_xaxes=True, vertical_spacing=0.05,
        subplot_titles=[f"{SERIES[k][1]} · {units[k]}" for k in keys],
    )
    for i, key in enumerate(keys, start=1):
        fig.add_trace(_line(key, df.index, df[key], SERIES[key][1], focus, hovertemplate="%{y:,.1f}"),
                      row=i, col=1)
    fig.update_layout(**{**LAYOUT, "height": 170 * len(keys)}, showlegend=False)
    _style_axes(fig)
    fig.update_annotations(x=0, xanchor="left")
    if focus:
        for i, key in enumerate(keys):
            if key not in focus:
                fig.layout.annotations[i].font.color = COLORS["ink3"]
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
    fig.add_trace(_line("income", idx.index, idx["income"], SERIES["income"][1], None, hovertemplate="%{y:.1f}"))
    fig.add_trace(_line("stocks", idx.index, idx["stocks"], SERIES["stocks"][1], None, hovertemplate="%{y:.1f}",
                        fill="tonexty", fillcolor=_alpha(COLORS["stocks"], 0.22)))
    for key in ("stocks", "income"):
        v = idx[key].iloc[-1]
        _end_label(fig, key, idx.index[-1], v, f"{SERIES[key][1]} {v - 100:+.0f}%".replace("-", "−"))
    fig.update_layout(**{**LAYOUT, "height": 400, "margin": {**LAYOUT["margin"], "r": 210}},
                      yaxis_title=f"Index ({base} = 100)", showlegend=False)
    return _fit_x(fig, idx.index), base


def rent_burden_map(df):
    """Sequential rent hue: dim for light burdens, bright for heavy ones."""
    fig = go.Figure(go.Choropleth(
        locations=df["abbr"], z=df["rent_burden"], locationmode="USA-states",
        colorscale=[[0, "#3a2420"], [0.5, COLORS["rent"]], [1, "#ffb59a"]], text=df["state_name"],
        hovertemplate="<b>%{text}</b><br>Rent burden: %{z:.1f}%<extra></extra>",
        colorbar=dict(title="% of income", ticksuffix="%", tickfont=dict(family=MONO, color=COLORS["ink3"])),
        marker_line_color=COLORS["bg"],
    ))
    fig.update_layout(
        geo=dict(scope="usa", projection_type="albers usa", bgcolor="rgba(0,0,0,0)", lakecolor="rgba(0,0,0,0)"),
        paper_bgcolor="rgba(0,0,0,0)", font=LAYOUT["font"], hoverlabel=LAYOUT["hoverlabel"],
        margin=dict(l=0, r=0, t=10, b=0), height=460,
    )
    return fig


def rent_hours_chart(hours):
    """Hours of work at the average hourly wage to pay a month's rent."""
    fig = go.Figure(_line("rent", hours.index, hours["rent"], "Hours for a month's rent", None,
                          customdata=hours[["rent_dollars", "wage"]],
                          hovertemplate="%{y:.1f} hours<br>$%{customdata[0]:,.0f} rent ÷ $%{customdata[1]:.2f}/hr<extra></extra>"))
    lo, hi = hours["rent"].min(), hours["rent"].max()
    pad = max(2, (hi - lo) * 0.6)
    _end_label(fig, "rent", hours.index[-1], hours["rent"].iloc[-1], f"{hours['rent'].iloc[-1]:.1f} hours")
    fig.update_layout(**{**LAYOUT, "height": 320, "margin": {**LAYOUT["margin"], "r": 110},
                         "yaxis": {**LAYOUT["yaxis"], "title": "Hours of work", "range": [lo - pad, hi + pad]}},
                      showlegend=False)
    return _fit_x(fig, hours.index)


def grocery_minutes_chart(hours):
    """Minutes of work per staple, one small panel each (prices move on different scales)."""
    keys = list(GROCERIES)
    short = {"eggs": "Eggs, dozen", "milk": "Milk, gallon", "bread": "Bread, pound", "beef": "Ground beef, pound"}
    fig = make_subplots(rows=1, cols=len(keys), subplot_titles=[short.get(k, GROCERIES[k][1]) for k in keys],
                        horizontal_spacing=0.06)
    for i, k in enumerate(keys, start=1):
        fig.add_trace(_line("food", hours.index, hours[k], GROCERIES[k][1], None,
                            customdata=hours[[k + "_price", "wage"]],
                            hovertemplate="%{y:.1f} min<br>$%{customdata[0]:.2f} ÷ $%{customdata[1]:.2f}/hr<extra></extra>"),
                      row=1, col=i)
        fig.update_yaxes(rangemode="tozero", row=1, col=i)
    fig.update_layout(**{**LAYOUT, "height": 300, "hovermode": "closest"}, showlegend=False)
    _style_axes(fig)
    fig.update_yaxes(title_text="Minutes of work", row=1, col=1)
    return fig
