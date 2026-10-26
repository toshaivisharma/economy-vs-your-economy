# Economy vs. Your Economy

Has everyday life kept up with the headline economy since 2000? Two views of the same FRED data:

- **Streamlit dashboard** (`app.py`): stocks, GDP per capita, median household income, rent and grocery prices, indexed or in their own units, with or without inflation; the stocks-vs-income gap; hours of work needed for rent and grocery staples; and a state rent-burden map (Census ACS).
- **The Economy Feels Fine** (`feelings/`): a static page that opens with a scrollytelling story after The Pudding's [songwriters piece](https://pudding.cool/2023/07/songwriters/), then an explorer in the spirit of [We Feel Fine](http://www.wefeelfine.org/) and *Dear Data*, where every monthly, quarterly or yearly move is a dot. Five movements: Madness, Murmurs, Mounds, Rings, Hours. The dashboard embeds the explorer in its "Every moment" tab.

## Run the dashboard

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

Optional keys, as environment variables or in `.streamlit/secrets.toml` (see `secrets.toml.example`):

- `FRED_API_KEY`: uses the official FRED API; without it the app falls back to FRED's public CSV export.
- `CENSUS_API_KEY`: needed for the state rent-burden map ([free key](https://api.census.gov/data/key_signup.html)).

## Rebuild the static page

```bash
.venv/bin/python build_feelings_data.py
```

This refetches the data and writes `feelings/index.html` with the data inlined. The page has no build step or server.

## Data and method

All series come from FRED (Federal Reserve Bank of St. Louis): `NASDAQCOM`, `A939RC0Q052SBEA`, `MEHOINUSA646N`, `CUSR0000SEHA`, `CPIFABSL`; inflation from `CPIAUCSL`; wages from `AHETPI`; BLS average prices for eggs, milk, bread and ground beef.

- Every series is fetched as paid; "after inflation" divides by the overall CPI for the same period.
- Stocks are the Nasdaq Composite because FRED only serves the last 10 years of the S&P 500.
- Rent in dollars starts from the Census 2000 median gross rent ($602/month) and grows with the rent CPI, which trails new-lease rents by about a year.
- Hours of work use average hourly earnings of production and nonsupervisory workers (about 80% of private-sector jobs).
