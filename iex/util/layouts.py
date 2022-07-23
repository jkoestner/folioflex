"""Layout lookups.

List of lookups for reference to dashapp
"""

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
