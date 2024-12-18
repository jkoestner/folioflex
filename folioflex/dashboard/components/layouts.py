"""
Layout lookups.

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

yahoo_info = {
    "info": [
        "address1",
        "city",
        "state",
        "zip",
        "country",
        "phone",
        "website",
        "industry",
        "industryDisp",
        "sector",
        "sectorDisp",
        # "longBusinessSummary",
        "fullTimeEmployees",
        # "companyOfficers",
        "exchange",
        "quoteType",
        "symbol",
        "underlyingSymbol",
        "shortName",
        "longName",
        "firstTradeDateEpochUtc",
        "timeZoneFullName",
        "timeZoneShortName",
        "uuid",
        "messageBoardId",
        "gmtOffSetMilliseconds",
        "exDividendDate",
    ],
    "risk": [
        "auditRisk",
        "boardRisk",
        "compensationRisk",
        "shareHolderRightsRisk",
        "overallRisk",
        "governanceEpochDate",
        "compensationAsOfEpochDate",
        "maxAge",
    ],
    "quote": [
        "priceHint",
        "previousClose",
        "open",
        "dayLow",
        "dayHigh",
        "regularMarketPreviousClose",
        "regularMarketOpen",
        "regularMarketDayLow",
        "regularMarketDayHigh",
        "payoutRatio",
        "beta",
        "trailingPE",
        "forwardPE",
        "volume",
        "regularMarketVolume",
        "averageVolume",
        "averageVolume10days",
        "averageDailyVolume10Day",
        "bid",
        "ask",
        "bidSize",
        "askSize",
        "marketCap",
        "fiftyTwoWeekLow",
        "fiftyTwoWeekHigh",
        "priceToSalesTrailing12Months",
        "fiftyDayAverage",
        "twoHundredDayAverage",
        "trailingAnnualDividendRate",
        "trailingAnnualDividendYield",
        "currency",
        "enterpriseValue",
        "profitMargins",
        "floatShares",
        "sharesOutstanding",
        "sharesShort",
        "sharesShortPriorMonth",
        "sharesShortPreviousMonthDate",
        "dateShortInterest",
        "sharesPercentSharesOut",
        "heldPercentInsiders",
        "heldPercentInstitutions",
        "shortRatio",
        "shortPercentOfFloat",
        "impliedSharesOutstanding",
        "bookValue",
        "priceToBook",
        "lastFiscalYearEnd",
        "nextFiscalYearEnd",
        "mostRecentQuarter",
        "earningsQuarterlyGrowth",
        "netIncomeToCommon",
        "trailingEps",
        "forwardEps",
        "pegRatio",
        "lastSplitFactor",
        "lastSplitDate",
        "enterpriseToRevenue",
        "enterpriseToEbitda",
        "52WeekChange",
        "SandP52WeekChange",
        "currentPrice",
    ],
    "analyst": [
        "targetHighPrice",
        "targetLowPrice",
        "targetMeanPrice",
        "targetMedianPrice",
        "recommendationMean",
        "recommendationKey",
        "numberOfAnalystOpinions",
    ],
    "fundamental": [
        "totalCash",
        "totalCashPerShare",
        "ebitda",
        "totalDebt",
        "quickRatio",
        "currentRatio",
        "totalRevenue",
        "debtToEquity",
        "revenuePerShare",
        "returnOnAssets",
        "returnOnEquity",
        "grossProfits",
        "freeCashflow",
        "operatingCashflow",
        "earningsGrowth",
        "revenueGrowth",
        "grossMargins",
        "ebitdaMargins",
        "operatingMargins",
        "financialCurrency",
        "trailingPegRatio",
    ],
}

# set up table formats
active_fmt = [
    {"id": "symbol", "name": "symbol"},
    {"id": "name", "name": "name"},
    {
        "id": "price",
        "name": "price",
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.fixed).group(True),
    },
    {
        "id": "change",
        "name": "change",
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.fixed).group(True),
    },
    {
        "id": "change_%",
        "name": "change_%",
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.percentage),
    },
    {
        "id": "volume",
        "name": "volume",
        "type": "numeric",
        "format": Format(precision=0, scheme=Scheme.fixed).group(True),
    },
    {
        "id": "avg_vol_3m",
        "name": "avg_vol_3m",
        "type": "numeric",
        "format": Format(precision=0, scheme=Scheme.fixed).group(True),
    },
    {
        "id": "market_cap",
        "name": "market_cap",
        "type": "numeric",
        "format": Format(precision=0, scheme=Scheme.fixed).group(True),
    },
    {
        "id": "vol_delta",
        "name": "vol_delta",
        "type": "numeric",
        "format": Format(precision=0, scheme=Scheme.percentage),
    },
    {
        "id": "vol_price",
        "name": "vol_price",
        "type": "numeric",
        "format": Format(precision=0, scheme=Scheme.fixed).group(True),
    },
]

performance_fmt = [
    {"id": "ticker", "name": "ticker"},
    {"id": "date", "name": "date"},
    {"id": "lookback_date", "name": "lookback_date"},
    {
        "id": "average_price",
        "name": "average_price",
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.fixed).group(True),
    },
    {
        "id": "last_price",
        "name": "last_price",
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.fixed).group(True),
    },
    {
        "id": "cumulative_units",
        "name": "cumulative_units",
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.fixed).group(True),
    },
    {
        "id": "cumulative_cost",
        "name": "cumulative_cost",
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.fixed).group(True),
    },
    {
        "id": "market_value",
        "name": "market_value",
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.fixed).group(True),
    },
    {
        "id": "return",
        "name": "return",
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.fixed).group(True),
    },
    {
        "id": "dwrr_pct",
        "name": "dwrr_pct",
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.percentage),
    },
    {
        "id": "dwrr_ann_pct",
        "name": "dwrr_ann_pct",
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.percentage),
    },
    {
        "id": "div_dwrr_pct",
        "name": "div_dwrr_pct",
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.percentage),
    },
    {
        "id": "realized",
        "name": "realized",
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.fixed).group(True),
    },
    {
        "id": "unrealized",
        "name": "unrealized",
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.fixed).group(True),
    },
]

transactions_fmt = [
    {
        "id": "date",
        "name": "date",
    },
    {
        "id": "ticker",
        "name": "ticker",
    },
    {
        "id": "type",
        "name": "type",
    },
    {
        "id": "units",
        "name": "units",
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.fixed).group(True),
    },
    {
        "id": "cost",
        "name": "cost",
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.fixed).group(True),
    },
    {
        "id": "broker",
        "name": "broker",
    },
    {
        "id": "price",
        "name": "price",
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.fixed).group(True),
    },
]
