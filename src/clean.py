"""Preprocessing (plan §2). Builds a cached, cleaned order-line table and baskets.

Run `python -m src.clean` to build the cache and write results/cleaning_log.csv.
"""
import hashlib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "online_retail_II.xlsx"
INTERIM = ROOT / "data" / "interim"
RESULTS = ROOT / "results"

Y1 = ("2009-12-01", "2010-12-01")  # year 1: 2009-12 .. 2010-11
Y2 = ("2010-12-01", "2011-12-01")  # year 2: 2010-12 .. 2011-11
CODE_PATTERN = r"^\d{5}[A-Za-z]*$"


def _sha8(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:8]


def _cache_path():
    return INTERIM / f"lines_{_sha8(RAW)}_{_sha8(__file__)}.parquet"


def _read_raw():
    sheets = pd.read_excel(RAW, sheet_name=None, dtype={"Invoice": str, "StockCode": str, "Description": str})
    return pd.concat(sheets.values(), ignore_index=True)


def build():
    """Clean the raw file. Returns (lines, log) where log is a list of (step, rows)."""
    df = _read_raw()
    log = [("1 merge sheets", len(df))]
    df = df.drop_duplicates()
    log.append(("2 drop exact duplicates", len(df)))
    df = df[~df.Invoice.str.match(r"^[CA]")]
    log.append(("3 drop cancel (C) and adjust (A) invoices", len(df)))
    df = df[(df.Quantity > 0) & (df.Price > 0)]
    log.append(("4 drop quantity<=0 or price<=0", len(df)))
    df = df[df.StockCode.str.match(CODE_PATTERN)]
    log.append(("5 drop non-product codes", len(df)))
    df = df.assign(StockCode=df.StockCode.str.upper())
    log.append(("6 upper-case suffixes", len(df)))
    # Step 7: replace Customer ID with a local number (0..), guests get -1. Original IDs are dropped.
    ids = df["Customer ID"]
    codes = {c: i for i, c in enumerate(sorted(ids.dropna().unique()))}
    df = df.assign(customer=ids.map(codes).fillna(-1).astype(int)).drop(columns="Customer ID")
    log.append(("7 pseudonymise customers", len(df)))
    df = df.rename(columns={"Invoice": "invoice", "StockCode": "code", "Description": "description",
                            "Quantity": "quantity", "InvoiceDate": "date", "Price": "price", "Country": "country"})
    log.append(("8 result", len(df)))
    return df.reset_index(drop=True), log


def load_lines():
    """Cleaned order lines (cached parquet). Columns: invoice, code, description, quantity, date, price, customer, country."""
    path = _cache_path()
    if path.exists():
        return pd.read_parquet(path)
    lines, log = build()
    INTERIM.mkdir(parents=True, exist_ok=True)
    lines.to_parquet(path)
    RESULTS.mkdir(exist_ok=True)
    pd.DataFrame(log, columns=["step", "rows"]).to_csv(RESULTS / "cleaning_log.csv", index=False)
    return lines


def load_baskets(lines=None):
    """One row per invoice: invoice, date, customer (-1 = guest), country, year (1, 2 or 0), items (sorted tuple of codes)."""
    lines = load_lines() if lines is None else lines
    g = lines.groupby("invoice", sort=True)
    b = g.agg(date=("date", "min"), customer=("customer", "first"), country=("country", "first"))
    b["items"] = g["code"].agg(lambda s: tuple(sorted(set(s))))
    b["year"] = 0
    b.loc[(b.date >= Y1[0]) & (b.date < Y1[1]), "year"] = 1
    b.loc[(b.date >= Y2[0]) & (b.date < Y2[1]), "year"] = 2
    return b.reset_index()


def descriptions(lines=None):
    """code -> most frequent description."""
    lines = load_lines() if lines is None else lines
    d = lines.dropna(subset=["description"])
    return d.groupby("code")["description"].agg(lambda s: s.value_counts().index[0]).to_dict()


if __name__ == "__main__":
    b = load_baskets()
    print(pd.read_csv(RESULTS / "cleaning_log.csv").to_string(index=False))
    print("baskets", len(b), "items", len({i for t in b["items"] for i in t}))
    print(b.year.value_counts().sort_index().to_dict())
