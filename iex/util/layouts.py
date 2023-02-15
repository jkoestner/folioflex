"""Layout lookups.

List of lookups for reference to dashapp
"""
from dash.dash_table.Format import Format, Scheme

# set up lists
USexchanges = [
    "NASDAQ",
    "New York Stock Exchange",
]  # ,'US OTC', 'NYSE American' 'NASDAQ', 'New York Stock Exchange'

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

# set up columns
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

# set up table formats
collection_fmt = [
    dict(id="symbol", name="symbol"),
    dict(id="companyName", name="companyName"),
    dict(
        id="primaryExchange",
        name="primaryExchange",
    ),
    dict(
        id="vol_delta",
        name="vol_delta",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.percentage),
    ),
    dict(
        id="volume",
        name="volume",
        type="numeric",
        format=Format(precision=0, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="avgTotalVolume",
        name="avgTotalVolume",
        type="numeric",
        format=Format(precision=0, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="changePercent",
        name="changePercent",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.percentage),
    ),
    dict(
        id="change",
        name="change",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="ytdChange",
        name="ytdChange",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.percentage),
    ),
    dict(
        id="open",
        name="open",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="close",
        name="close",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="latestPrice",
        name="latestPrice",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="latestSource",
        name="latestSource",
    ),
    dict(
        id="latestTime",
        name="latestTime",
    ),
    dict(
        id="previousClose",
        name="previousClose",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="previousVolume",
        name="previousVolume",
        type="numeric",
        format=Format(precision=0, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="marketCap",
        name="marketCap",
        type="numeric",
        format=Format(precision=0, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="peRatio",
        name="peRatio",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
]

performance_fmt = [
    dict(id="ticker", name="ticker"),
    dict(id="date", name="date"),
    dict(
        id="average_price",
        name="average_price",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="last_price",
        name="last_price",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="cumulative_units",
        name="cumulative_units",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="cumulative_cost",
        name="cumulative_cost",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="market_value",
        name="market_value",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="return",
        name="return",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
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
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="unrealized",
        name="unrealized",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
]

transactions_fmt = [
    dict(
        id="ticker",
        name="ticker",
    ),
    dict(
        id="date",
        name="date",
    ),
    dict(
        id="last_price",
        name="last_price",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="sale_price",
        name="sale_price",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="units",
        name="units",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="cost",
        name="cost",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="broker",
        name="broker",
    ),
    dict(
        id="cumulative_units",
        name="cumulative_units",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="cumulative_cost",
        name="cumulative_cost",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="average_price",
        name="average_price",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="market_value",
        name="market_value",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="return",
        name="return",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="unrealized",
        name="unrealized",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
    dict(
        id="realized",
        name="realized",
        type="numeric",
        format=Format(precision=2, scheme=Scheme.fixed).group(True),
    ),
]
