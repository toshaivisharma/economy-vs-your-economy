from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from components import charts
from data import fetcher

st.set_page_config(page_title="Economy vs. Your Economy", page_icon="📉", layout="wide",
                   initial_sidebar_state="collapsed")

C, T = charts.COLORS, charts.TEXT
FEELINGS = Path(__file__).parent / "feelings" / "index.html"

# Pudding-style night stage, shared with feelings/template.html: cream ink on warm
# near-black, controls in one row above the content, everything else fades on focus.
st.markdown(f"""
<style>
[data-testid="stSidebarCollapsedControl"], [data-testid="stSidebar"] {{ display: none; }}
.block-container {{ max-width: 1120px; padding-top: 2.75rem; }}
h1, h2, h3 {{ font-weight: 400 !important; letter-spacing: 0 !important; }}
h3 {{ font-size: 1.55rem !important; margin-top: 1.4rem !important; }}
.eyebrow {{ font-family: 'DM Mono', monospace; font-size: 12px; letter-spacing: .1em; text-transform: uppercase; color: {C['ink3']}; }}
.masthead h1 {{ font-size: clamp(36px, 6.4vw, 64px) !important; line-height: 1.02 !important; padding: 6px 0 10px !important; }}
.lede {{ font-family: 'Iowan Old Style', 'Source Serif 4', Georgia, serif; font-size: 20px; line-height: 1.5;
        color: {C['ink2']}; max-width: 60ch; margin: 0 0 8px; }}
.w-stocks {{ color: {T['stocks']}; }} .w-income {{ color: {T['income']}; }} .w-gdp {{ color: {T['gdp']}; }}
.w-rent {{ color: {T['rent']}; }} .w-food {{ color: {T['food']}; }}
.mode {{ font-family: 'DM Mono', monospace; font-size: 12px; color: {C['ink3']}; margin-top: -4px; }}

@keyframes rise {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: none; }} }}
.cards {{ display: grid; grid-template-columns: repeat(var(--n), minmax(0, 1fr)); gap: 20px;
         padding: 16px 0 8px; border-block: 1px solid {C['rule']}; margin: 6px 0 12px; }}
.card {{ animation: rise .6s cubic-bezier(.2, .7, .2, 1) both; animation-delay: calc(var(--i) * 70ms); }}
.card > * {{ transition: opacity .5s ease; }}
.card.dim > * {{ opacity: {charts.FADED * 2}; }}
.card .name {{ display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 14px; }}
.card .dot {{ width: 12px; height: 12px; border-radius: 50%; flex: none; background: var(--c); box-shadow: 0 0 0 3px {C['bg']}, 0 0 0 4px var(--c); }}
.card .big {{ font-family: 'Young Serif', serif; font-size: clamp(26px, 3.2vw, 36px); line-height: 1.1; margin-top: 6px; }}
@media (max-width: 720px) {{ .cards {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .card:last-child:nth-child(odd) {{ grid-column: 1 / -1; }} }}
.card .sub {{ font-family: 'DM Mono', monospace; font-size: 11px; color: {C['ink3']}; }}
[data-testid="stPlotlyChart"] {{ animation: rise .7s cubic-bezier(.2, .7, .2, 1) both; }}
[data-testid="stCaptionContainer"] {{ color: {C['ink3']}; }}
.stTabs [data-baseweb="tab"] p {{ font-family: 'Young Serif', serif; font-size: 19px; }}

.hrs {{ display: grid; gap: 22px; padding: 10px 0 6px; }}
.hrow {{ display: grid; grid-template-columns: minmax(150px, 210px) minmax(0, 1fr); gap: 8px 22px; animation: rise .6s ease both;
        animation-delay: calc(var(--i) * 90ms); }}
.hrow h4 {{ margin: 0; padding: 0; font-family: 'Young Serif', serif; font-weight: 400; font-size: 19px; }}
.hrow .chg {{ font-size: 14px; color: {C['ink2']}; }}
.yr {{ display: grid; grid-template-columns: 44px minmax(0, 1fr); gap: 10px; align-items: center; margin-bottom: 6px; }}
.yr time {{ font-family: 'DM Mono', monospace; font-size: 12px; color: {C['ink3']}; }}
.dots {{ display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }}
.dots i {{ width: 12px; height: 12px; border-radius: 50%; border: 2px solid var(--c);
          background: linear-gradient(90deg, var(--c) var(--f, 100%), transparent var(--f, 100%)); }}
.dots span {{ font-family: 'DM Mono', monospace; font-size: 12px; color: {C['ink2']}; margin-left: 6px; }}
@media (max-width: 640px) {{ .hrow {{ grid-template-columns: minmax(0, 1fr); }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; transition: none !important; }} }}
</style>
""", unsafe_allow_html=True)


def cards(items, focus=None):
    """items: (key for color and focus, label, big number, small line)."""
    html = "".join(
        f'<div class="card{" dim" if focus and k not in focus else ""}" style="--c:{C[ck]};--i:{i}">'
        f'<div class="name"><span class="dot"></span>{label}</div>'
        f'<div class="big">{big}</div><div class="sub">{sub}</div></div>'
        for i, (k, ck, label, big, sub) in enumerate(items)
    )
    st.markdown(f'<div class="cards" style="--n:{len(items)}">{html}</div>', unsafe_allow_html=True)


def plot(fig):
    st.plotly_chart(fig, use_container_width=True, theme=None, config={"displayModeBar": False})


def pct(x):
    return f"{x:+.0f}%".replace("-", "−")


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


# --- Masthead ---------------------------------------------------------------
st.markdown(
    '<div class="masthead"><div class="eyebrow">FRED · Federal Reserve Bank of St. Louis · 2000 to today</div>'
    '<h1>Economy vs. Your Economy</h1>'
    '<p class="lede">The headline economy is <span class="w-stocks">stock prices</span> and '
    '<span class="w-gdp">GDP</span>. Your economy is <span class="w-income">your household\'s income</span>, '
    'your <span class="w-rent">rent</span> and your <span class="w-food">groceries</span>. '
    'Since 2000, the two have drifted a long way apart.</p></div>',
    unsafe_allow_html=True,
)

try:
    data = load_fred()
    cpi = load_cpi()
except Exception as e:
    st.error(f"Could not load FRED data: {e}")
    st.stop()

# --- Controls (one row above everything they filter) -------------------------
c1, c2, c3 = st.columns([1, 1.15, 1.6])
view = c1.segmented_control("Chart", ["Indexed", "Own units"], default="Indexed") or "Indexed"
dollars = c2.segmented_control("Dollars", ["After inflation", "As paid"], default="After inflation") or "After inflation"
focus_name = c3.segmented_control("Focus", ["Everything", "Headline economy", "Your economy"],
                                  default="Everything") or "Everything"
focus = {"Headline economy": charts.HEADLINE, "Your economy": charts.HOUSEHOLD}.get(focus_name)
real = dollars == "After inflation"

min_year, max_year = int(data.index.min()), int(data.index.max())
start, end = st.slider("Years", min_value=min_year, max_value=max_year, value=(min_year, max_year))
cpi_year = int(cpi.index.max())
df = (fetcher.deflate(data, cpi) if real else data).loc[start:end]
st.markdown(
    f'<div class="mode">{"After inflation, in " + str(cpi_year) + " dollars. Rent and groceries show their price relative to everything else." if real else "As paid at the time, not adjusted for inflation."}</div>',
    unsafe_allow_html=True,
)

tab_two, tab_hours, tab_moments, tab_map = st.tabs(["Two economies", "Hours of work", "Every moment", "Rent by state"])

# --- Two economies ------------------------------------------------------------
with tab_two:
    items = []
    for key, (_, label, _) in fetcher.SERIES.items():
        s = df[key].dropna()
        if len(s) < 2:
            items.append((key, key, label, "n/a", "not enough data"))
            continue
        items.append((key, key, label, pct((s.iloc[-1] / s.iloc[0] - 1) * 100), f"{s.index[0]} → {s.index[-1]}"))
    cards(items, focus)

    st.subheader("Headline vs. household")
    if view == "Indexed":
        _, bases = charts.index_to_base(df, start)
        late = [fetcher.SERIES[k][1] for k, y in bases.items() if y != start]
        plot(charts.indexed_chart(df, start, focus))
        if late:
            st.caption(f"{', '.join(late)} has no data for {start} on FRED, so it is indexed to its first year instead.")
    else:
        units = {k: u for k, (_, _, u) in fetcher.SERIES.items()}
        if real:
            units.update(gdp=f"{cpi_year} $ per person", income=f"{cpi_year} $ per year",
                         stocks=f"index level, {cpi_year} prices",
                         rent="CPI index ÷ overall CPI", food="CPI index ÷ overall CPI")
        plot(charts.absolute_chart(df, units, focus))

    st.subheader("The gap: stocks vs. median household income")
    fig, base = charts.divergence_chart(df)
    if fig is None:
        st.info("No overlapping stock and income data in these years.")
    else:
        plot(fig)
        st.caption(
            f"Both indexed to {base} = 100. Stocks are the Nasdaq Composite, because FRED only publishes the "
            "last 10 years of the S&P 500. Nasdaq leans toward tech, so it swings harder than the S&P 500."
        )

# --- Hours of work ------------------------------------------------------------
with tab_hours:
    st.caption(
        "What things cost in time, at the average hourly wage of production and nonsupervisory workers "
        "(about 80% of private-sector jobs). Wages and prices are both as paid, so inflation cancels out "
        "and the Dollars switch doesn't apply. Each dot is an hour of work for rent, or a minute for groceries."
    )
    try:
        hours = load_hours().loc[start:end]
    except Exception as e:
        hours = None
        st.error(f"Could not load wage and price data: {e}")
    if hours is not None and len(hours) >= 2:
        y0, y1 = int(hours.index[0]), int(hours.index[-1])
        rows = [("A month's rent", "rent", "hours", "rent", lambda h: f"${h['rent_dollars']:,.0f}")] + [
            (label, k, "minutes", "food", lambda h, k=k: f"${h[k + '_price']:.2f}")
            for k, (_, label) in fetcher.GROCERIES.items()
        ]

        def dots(v):
            whole, frac = int(v), v - int(v)
            return "<i></i>" * whole + (f'<i style="--f:{frac * 100:.0f}%"></i>' if frac >= 0.05 else "")

        html = []
        for i, (label, k, unit, ck, cost) in enumerate(rows):
            a, b = hours.loc[y0, k], hours.loc[y1, k]
            d = b - a
            chg = f"{abs(d):.1f} {unit} {'more' if d > 0 else 'less'} than {y0}" if abs(d) >= 0.05 else f"About the same as {y0}"
            yrs = "".join(
                f'<div class="yr"><time>{y}</time><div class="dots">{dots(hours.loc[y, k])}'
                f'<span>{hours.loc[y, k]:.1f} {unit} · {cost(hours.loc[y])} ÷ ${hours.loc[y, "wage"]:.2f}/hr</span></div></div>'
                for y in (y0, y1)
            )
            html.append(f'<div class="hrow" style="--c:{C[ck]};--i:{i}"><div><h4>{label}</h4>'
                        f'<div class="chg">{chg}</div></div><div>{yrs}</div></div>')
        st.markdown(f'<div class="hrs">{"".join(html)}</div>', unsafe_allow_html=True)
        st.subheader("Rent, year by year")
        plot(charts.rent_hours_chart(hours))
        st.caption(
            f"Rent in dollars starts from the Census 2000 median gross rent (${fetcher.RENT_2000}/month) and "
            "grows with the rent CPI, which covers all tenants and trails new-lease rents by about a year."
        )
        st.subheader("Groceries, year by year")
        plot(charts.grocery_minutes_chart(hours))

# --- Every moment (the We Feel Fine page, embedded) ------------------------------
with tab_moments:
    if FEELINGS.exists():
        page = FEELINGS.read_text(encoding="utf-8").replace(
            '<meta charset="utf-8">',
            '<meta charset="utf-8">\n<script>document.documentElement.classList.add("embed")</script>', 1)
        components.html(page, height=980, scrolling=False)
        st.caption("Every monthly, quarterly and yearly move as a dot. Its data is a snapshot from the last "
                   "build of feelings/index.html, so it doesn't follow the controls above.")
    else:
        st.info("Run build_feelings_data.py to generate this view.")

# --- Rent by state -------------------------------------------------------------
with tab_map:
    st.caption("Median gross rent as a percentage of household income, ACS 1-year table B25071, 2022. "
               "A single-year snapshot, so the controls above don't apply.")
    try:
        burden = load_rent_burden()
    except Exception as e:
        burden = None
        st.error(f"Could not load Census data: {e}")
    else:
        if burden is None:
            st.info("Add a `CENSUS_API_KEY` (free at https://api.census.gov/data/key_signup.html) in the app's "
                    "secrets to show this map.")
    if burden is not None:
        plot(charts.rent_burden_map(burden))

# --- Footer ----------------------------------------------------------------------
st.divider()
st.caption(
    "Data: Federal Reserve Bank of St. Louis (FRED), including BLS consumer prices, average retail prices and "
    "hourly earnings; U.S. Census Bureau (Census 2000, ACS). Annual averages; the latest year is the average so far. "
    "Design after The Pudding's “Women are superstars on stage, but still rarely get to write songs”."
)
