"""Build feelings/index.html: the We Feel Fine-style page with its data inlined.

One record per observation. Daily stocks are averaged to months; everything else keeps
its native frequency (monthly CPI, quarterly GDP, annual income). Each record carries
the change from the previous observation, both as paid ("p") and after inflation ("r"),
where the after-inflation value is the nominal value divided by the overall CPI
averaged over the same period.
"""

import datetime
import json
from pathlib import Path

from data.fetcher import (
    CPI_ID, GROCERIES, RENT_2000, SERIES, WAGE_ID, fetch_fred_raw, fetch_hours,
)

# pandas resample rule matching each series' own period
PERIOD = {"stocks": "MS", "gdp": "QS", "income": "YS", "rent": "MS", "food": "MS"}

cpi_monthly = fetch_fred_raw(CPI_ID).resample("MS").mean()

records = {}
for key, (sid, label, unit) in SERIES.items():
    rule = PERIOD[key]
    s = fetch_fred_raw(sid).resample(rule).mean().dropna()
    deflator = cpi_monthly.resample(rule).mean().reindex(s.index)
    real = (s / deflator).dropna()
    s = s.loc[real.index]
    pn = s.pct_change(fill_method=None) * 100
    pr = real.pct_change(fill_method=None) * 100
    rows = []
    for d, v, rv, p, r in zip(s.index, s.values, real.values, pn.values, pr.values):
        if p != p or r != r:  # first point, or no CPI for this period yet
            continue
        rows.append({"d": d.strftime("%Y-%m"), "v": round(float(v), 2),
                     "rv": round(float(rv), 5), "p": round(float(p), 3), "r": round(float(r), 3)})
    records[key] = rows
    print(key, len(rows), rows[0]["d"], "->", rows[-1]["d"])

hours = fetch_hours()
hours_out = {
    str(y): {k: round(float(v), 2) for k, v in row.items()} for y, row in hours.iterrows()
}

payload = {
    "meta": {k: {"id": sid, "label": label, "unit": unit} for k, (sid, label, unit) in SERIES.items()},
    "series": records,
    "hours": hours_out,
    "groceries": {k: label for k, (_, label) in GROCERIES.items()},
    "ids": {"cpi": CPI_ID, "wage": WAGE_ID, **{k: sid for k, (sid, _) in GROCERIES.items()}},
    "rent2000": RENT_2000,
    "cpiLatest": float(cpi_monthly.dropna().iloc[-1]),
    "cpiLatestDate": cpi_monthly.dropna().index[-1].strftime("%Y-%m"),
    "built": datetime.date.today().strftime("%-d %B %Y"),
}

out = Path("feelings")
out.mkdir(exist_ok=True)
data = json.dumps(payload, separators=(",", ":"), allow_nan=False)
(out / "data.json").write_text(data)
page = (out / "template.html").read_text().replace("/*DATA*/", data.replace("</", "<\\/"))
(out / "index.html").write_text(page)
print("feelings/index.html", len(page), "bytes")
