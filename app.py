import streamlit as st

from components import charts
from data import fetcher

st.set_page_config(page_title="Economy vs. Your Economy", page_icon="📉", layout="wide")

THEME = getattr(st.context.theme, "type", None) or "light"
charts.set_theme(THEME)
C = charts.COLORS

# Masthead, cards and section headings styled after feelings/template.html.
st.markdown(f"""
<style>
.block-container {{ max-width: 1120px; padding-top: 2.5rem; }}
h1, h2, h3 {{ font-weight: 400 !important; letter-spacing: 0 !important; }}
h3 {{ font-size: 1.6rem !important; margin-top: 1.2rem !important; }}
.eyebrow {{ font-family: 'IBM Plex Mono', monospace; font-size: 12px; letter-spacing: .08em;
           text-transform: uppercase; color: {C['ink3']}; }}
.masthead h1 {{ font-size: clamp(34px, 6vw, 58px) !important; line-height: 1.02 !important; padding: 4px 0 8px !important; }}
.lede {{ font-size: 17px; color: {C['ink2']}; max-width: 62ch; margin: 0 0 6px; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 18px;
         padding: 14px 0 6px; border-block: 1px solid {C['rule']}; margin: 6px 0 10px; }}
.card .name {{ display: flex; align-items: center; gap: 7px; font-weight: 700; font-size: 14px; }}
.card .dot {{ width: 12px; height: 12px; border-radius: 50%; flex: none;
             background: radial-gradient(circle, var(--c) 0 28%, transparent 30% 48%, var(--c) 50%); }}
.card .big {{ font-family: 'Young Serif', serif; font-size: 34px; line-height: 1.1; margin-top: 4px; }}
.card .sub {{ font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: {C['ink3']}; }}
.mode {{ font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: {C['ink3']}; }}
[data-testid="stCaptionContainer"] {{ color: {C['ink3']}; }}
</style>
""", unsafe_allow_html=True)


def cards(items):
    """items: (color, label, big number, small line)."""
    html = "".join(
        f'<div class="card" style="--c:{c}"><div class="name"><span class="dot"></span>{label}</div>'
        f'<div class="big">{big}</div><div class="sub">{sub}</div></div>'
        for c, label, big, sub in items
    )
    st.markdown(f'<div class="cards">{html}</div>', unsafe_allow_html=True)


def plot(fig):
    st.plotly_chart(fig, use_container_width=True, theme=None)


@st.cache_data(ttl=6 * 3600, show_spinner="Fetching FRED data…")
def load_fred():
    return fetcher.fetch_all_fred()


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def load_cpi():
    return fetcher.fetch_cpi()


@st.cache_data(ttl=6 * 3600, show_spinner="Fetching wages and prices…")
def load_hours():
    return fetcher.fetch_hours()


@st.cache_data(ttl=24 * 3600, show_spinner="Fetching Census ACS data…")
def load_rent_burden():
    return fetcher.fetch_rent_burden()


# --- Sidebar ---------------------------------------------------------------
with st.sidebar:
    st.header("View")
    view = st.radio("Chart mode", ["Indexed view", "Absolute values view"])
    st.caption(
        "Indexed view rebases every series to the first year of the selected "
        "range = 100. Absolute view shows each series in its own units."
    )
    real = st.toggle("Adjust for inflation", value=True)
    st.caption(
        "On: every series is divided by the overall Consumer Price Index, so a rise "
        "means it beat inflation. Off: values as paid at the time."
    )

st.markdown(
    '<div class="masthead"><div class="eyebrow">FRED · Federal Reserve Bank of St. Louis · 2000 to today</div>'
    '<h1>Economy vs. Your Economy</h1>'
    '<p class="lede">Headline numbers next to what everyday life costs: stock prices and GDP against '
    'household income, rent and groceries.</p></div>',
    unsafe_allow_html=True,
)

try:
    data = load_fred()
    cpi = load_cpi()
except Exception as e:
    st.error(f"Could not load FRED data: {e}")
    st.stop()

# --- Date range ------------------------------------------------------------
min_year, max_year = int(data.index.min()), int(data.index.max())
start, end = st.slider(
    "Year range", min_value=min_year, max_value=max_year, value=(min_year, max_year)
)
cpi_year = int(cpi.index.max())
df = (fetcher.deflate(data, cpi) if real else data).loc[start:end]
mode_note = (
    f"After inflation, in {cpi_year} dollars. Rent and food show their price relative to everything else."
    if real else "As paid at the time (not adjusted for inflation)."
)
st.markdown(f'<div class="mode">{mode_note}</div>', unsafe_allow_html=True)

# --- Metric cards ----------------------------------------------------------
items = []
for key, (_, label, _) in fetcher.SERIES.items():
    s = df[key].dropna()
    if len(s) < 2:
        items.append((C[key], label, "n/a", "not enough data"))
        continue
    pct = (s.iloc[-1] / s.iloc[0] - 1) * 100
    items.append((C[key], label, f"{pct:+.0f}%".replace("-", "−"), f"{s.index[0]} → {s.index[-1]}"))
cards(items)

# --- Main chart ------------------------------------------------------------
st.subheader("Headline vs. household")
if view == "Indexed view":
    _, bases = charts.index_to_base(df, start)
    late = [fetcher.SERIES[k][1] for k, y in bases.items() if y != start]
    plot(charts.indexed_chart(df, start))
    if late:
        st.caption(
            f"Dashed lines ({', '.join(late)}) have no data for {start} on FRED and are "
            "indexed to their first available year instead."
        )
else:
    units = {k: u for k, (_, _, u) in fetcher.SERIES.items()}
    if real:
        units.update(gdp=f"{cpi_year} $ per person", income=f"{cpi_year} $ per year",
                     stocks=f"Index level, {cpi_year} prices",
                     rent="CPI index ÷ overall CPI", food="CPI index ÷ overall CPI")
    plot(charts.absolute_chart(df, units))

# --- Divergence chart ------------------------------------------------------
st.subheader("The gap: stocks vs. median household income")
fig, base = charts.divergence_chart(df)
if fig is None:
    st.info("No overlapping stock and income data in the selected range.")
else:
    plot(fig)
    st.caption(
        f"Both series indexed to {base} = 100 (their first common year in range). Stocks are the "
        "Nasdaq Composite, because FRED only publishes the last 10 years of the S&P 500. "
        "Nasdaq is weighted toward tech, so it swings harder than the S&P 500."
    )

# --- Hours of work ---------------------------------------------------------
st.subheader("Hours of work")
st.caption(
    "What things cost in time, at the average hourly wage of production and nonsupervisory "
    "workers (about 80% of private-sector jobs). Wages and prices are both as paid, so "
    "inflation cancels out and the inflation toggle doesn't apply."
)
try:
    hours = load_hours().loc[start:end]
except Exception as e:
    hours = None
    st.error(f"Could not load wage and price data: {e}")
if hours is not None and len(hours) >= 2:
    first, last = hours.iloc[0], hours.iloc[-1]
    y0, y1 = hours.index[0], hours.index[-1]
    rows = [("A month's rent", "rent", "hours", C["rent"])] + [
        (label, k, "min", C["food"]) for k, (_, label) in fetcher.GROCERIES.items()
    ]
    cards([
        (c, label, f"{last[k]:.1f} {unit}",
         f"{last[k] - first[k]:+.1f} {unit} vs {y0}".replace("-", "−"))
        for label, k, unit, c in rows
    ])
    plot(charts.rent_hours_chart(hours))
    st.caption(
        f"Rent in dollars starts from the Census 2000 median gross rent (${fetcher.RENT_2000}/month) "
        "and grows with the rent CPI. The rent CPI covers all tenants, including long leases, so it "
        "trails new-lease market rents by about a year."
    )
    plot(charts.grocery_minutes_chart(hours))

# --- Choropleth ------------------------------------------------------------
st.subheader("Rent burden by state (2022)")
st.caption(
    "Median gross rent as a percentage of household income, ACS 1-year table B25071. "
    "Single-year snapshot, so the year range above doesn't apply."
)
try:
    burden = load_rent_burden()
except Exception as e:
    burden = None
    st.error(f"Could not load Census data: {e}")
else:
    if burden is None:
        st.info(
            "Set a `CENSUS_API_KEY` (free at https://api.census.gov/data/key_signup.html) "
            "as an environment variable or in `.streamlit/secrets.toml` to show this map."
        )
if burden is not None:
    plot(charts.rent_burden_map(burden))

# --- Footer ----------------------------------------------------------------
st.divider()
st.caption(
    "Data sources: Federal Reserve Bank of St. Louis (FRED), including BLS consumer prices, "
    "average retail prices and hourly earnings; U.S. Census Bureau (Census 2000, ACS). "
    "Series are annual averages; the latest year is the average so far."
)
