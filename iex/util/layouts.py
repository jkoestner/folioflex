"""Layout lookups.

List of lookups for reference to dashapp
"""
from dash.dash_table.Format import Format, Scheme

# set up lists
USexchanges = [
    "NASDAQ",
    "New York Stock Exchange",
]  # ,'US OTC', 'NYSE American' 'NASDAQ', 'New York Stock Exchange'
cols_col = [
    "symbol",
    "companyName",
    "primaryExchange",
    "peRatio",
    "cap*perc",
    "changePercent",
    "marketCap",
    "change",
    "close",
    "open",
    "latestPrice",
    "latestSource",
    "latestUpdate",
]

quote_col = [
    "symbol",
    "companyName",
    "isUSMarketOpen",
    "latestPrice",
    "previousClose",
    "latestUpdate",
    "latestSource",
    "change",
    "changePercent",
    "ytdChange",
    "latestVolume",
    "avgTotalVolume",
    "previousVolume",
    "marketCap",
    "peRatio",
    "extendedPrice",
    "extendedPriceTime",
    "open",
    "close",
    "high",
    "low",
    "week52High",
    "week52Low",
]

crypto_quote_col = [
    "symbol",
    "sector",
    "calculationPrice",
    "latestPrice",
    "latestSource",
    "latestUpdate",
    "latestVolume",
    "bidPrice",
    "bidSize",
    "askPrice",
    "askSize",
    "high",
    "low",
    "previousClose",
]

active_col = [
    "symbol",
    "companyName",
    "primaryExchange",
    "vol_delta",
    "volume",
    "avgTotalVolume",
    "changePercent",
    "change",
    "ytdChange",
    "open",
    "close",
    "latestPrice",
    "latestSource",
    "latestTime",
    "previousClose",
    "previousVolume",
    "marketCap",
    "peRatio",
]

formatter_col = {
    "peRatio": "{:,.2f}".format,
    "cap*perc": "{:,.2f}".format,
    "changePercent": "{0:.2%}".format,
    "marketCap": "{:,.2f}".format,
    "change": "{:,.2f}".format,
    "close": "{:,.2f}".format,
    "open": "{:,.2f}".format,
    "latestPrice": "{:,.2f}".format,
    "latestSource": "{:,.2f}".format,
    "latestUpdate": "{:,.2f}".format,
}

performance_col = [
    dict(id="ticker", name="ticker", type="numeric", format=Format()),
    dict(id="date", name="date", type="numeric", format=Format()),
    dict(
        id="average_price",
        name="average_price",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed),
    ),
    dict(
        id="last_price",
        name="last_price",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed),
    ),
    dict(
        id="cumulative_units",
        name="cumulative_units",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed),
    ),
    dict(
        id="cumulative_cost",
        name="cumulative_cost",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed),
    ),
    dict(
        id="market_value",
        name="market_value",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed),
    ),
    dict(
        id="return",
        name="return",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed),
    ),
    dict(
        id="return_pct",
        name="return_pct",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.percentage),
    ),
    dict(
        id="realized",
        name="realized",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed),
    ),
    dict(
        id="unrealized",
        name="unrealized",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed),
    ),
]

list_sector = [
    "XLV",
    "XLK",
    "XLY",
    "XLP",
    "XLB",
    "XLI",
    "IYT",
    "RWR",
    "XLF",
    "XLU",
    "SPY",
]
