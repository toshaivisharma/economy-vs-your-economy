"""All external API calls: FRED (economic series) and Census ACS (state rent burden)."""

import io
import os

import pandas as pd
import requests

START_DATE = "2000-01-01"
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
CENSUS_URL = "https://api.census.gov/data/2022/acs/acs1"

# key -> (FRED series id, display label, unit description)
# All series are nominal (as paid); app.py deflates them with CPI_ID on request,
# so headline and household numbers are always measured the same way.
# Stocks use the Nasdaq Composite because FRED only serves the last 10 years of SP500.
SERIES = {
    "stocks": ("NASDAQCOM", "Nasdaq Composite", "Index level"),
    "gdp": ("A939RC0Q052SBEA", "GDP per capita", "$ per person"),
    "income": ("MEHOINUSA646N", "Median household income", "$ per year"),
    "rent": ("CUSR0000SEHA", "Rent (CPI)", "CPI index, 1982-84=100"),
    "food": ("CPIFABSL", "Food at home (CPI)", "CPI index, 1982-84=100"),
}

# Consumer Price Index for All Urban Consumers: the deflator for "after inflation" views.
CPI_ID = "CPIAUCSL"

# Average hourly earnings, production and nonsupervisory workers (about 80% of private jobs).
WAGE_ID = "AHETPI"

# BLS average retail prices, U.S. city average, $ per unit.
GROCERIES = {
    "eggs": ("APU0000708111", "A dozen eggs"),
    "milk": ("APU0000709112", "A gallon of milk"),
    "bread": ("APU0000702111", "A pound of white bread"),
    "beef": ("APU0000703112", "A pound of ground beef"),
}

# Census 2000 median gross rent ($/month). The rent CPI carries it forward, since FRED
# has no national rent level in dollars.
RENT_2000 = 602

STATE_ABBR = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT",
    "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL",
    "18": "IN", "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD",
    "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE",
    "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV",
    "55": "WI", "56": "WY", "72": "PR",
}


def _get_key(name):
    """Read an API key from Streamlit secrets or the environment."""
    try:
        import streamlit as st

        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name)


def _fetch_fred_api(series_id, api_key):
    resp = requests.get(
        FRED_API_URL,
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": START_DATE,
        },
        timeout=30,
    )
    resp.raise_for_status()
    obs = resp.json()["observations"]
    df = pd.DataFrame(obs)[["date", "value"]]
    return pd.Series(
        pd.to_numeric(df["value"], errors="coerce").values,
        index=pd.to_datetime(df["date"]),
    )


def _fetch_fred_csv(series_id):
    """Keyless fallback: FRED's public graph CSV export."""
    resp = requests.get(
        FRED_CSV_URL, params={"id": series_id, "cosd": START_DATE}, timeout=30
    )
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    return pd.Series(
        pd.to_numeric(df.iloc[:, 1], errors="coerce").values,
        index=pd.to_datetime(df.iloc[:, 0]),
    )


def fetch_fred_raw(series_id):
    """Fetch one FRED series from START_DATE at its native frequency."""
    api_key = _get_key("FRED_API_KEY")
    raw = _fetch_fred_api(series_id, api_key) if api_key else _fetch_fred_csv(series_id)
    return raw.dropna()


def fetch_fred_series(series_id):
    """Fetch one FRED series from START_DATE and resample to annual averages.

    Returns a Series indexed by integer year.
    """
    annual = fetch_fred_raw(series_id).resample("YS").mean().dropna()
    annual.index = annual.index.year
    return annual


def fetch_all_fred():
    """Fetch every series in SERIES into one DataFrame (rows=year, cols=series key)."""
    return pd.DataFrame({key: fetch_fred_series(sid) for key, (sid, _, _) in SERIES.items()})


def fetch_cpi():
    """Annual-average CPI, indexed by year."""
    return fetch_fred_series(CPI_ID)


def deflate(df, cpi):
    """Convert nominal annual values to dollars of the latest CPI year."""
    cpi = cpi.reindex(df.index)
    return df.mul(cpi.iloc[-1] / cpi, axis=0)


def fetch_hours():
    """Hours of work at the average hourly wage needed to pay a month's rent,
    and minutes of work for each grocery staple. Rows=year.

    Prices and wages are both nominal, so inflation cancels out of the ratio.
    """
    wage = fetch_fred_series(WAGE_ID)
    rent_idx = fetch_fred_series(SERIES["rent"][0])
    rent_dollars = RENT_2000 * rent_idx / rent_idx.loc[2000]
    out = pd.DataFrame({"wage": wage, "rent_dollars": rent_dollars})
    out["rent"] = out["rent_dollars"] / out["wage"]
    for key, (sid, _) in GROCERIES.items():
        price = fetch_fred_series(sid)
        out[key + "_price"] = price
        out[key] = price / out["wage"] * 60
    return out.dropna()


def fetch_rent_burden():
    """Median gross rent as % of household income (ACS B25071), 2022, by state.

    Requires CENSUS_API_KEY; returns None if no key is configured.
    """
    api_key = _get_key("CENSUS_API_KEY")
    if not api_key:
        return None
    resp = requests.get(
        CENSUS_URL,
        params={"get": "NAME,B25071_001E", "for": "state:*", "key": api_key},
        timeout=30,
    )
    resp.raise_for_status()
    rows = resp.json()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df["rent_burden"] = pd.to_numeric(df["B25071_001E"], errors="coerce")
    df["abbr"] = df["state"].map(STATE_ABBR)
    return df.rename(columns={"NAME": "state_name"})[["state_name", "abbr", "rent_burden"]]
