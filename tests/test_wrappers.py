"""Tests the wrappers."""

try:
    import wrappers
except (ImportError, ModuleNotFoundError):
    from iex.portfolio import wrappers


def test_stock_history():
    """Checks that stock information can be pulled."""
    yahoo = wrappers.Yahoo()
    tickers = ["AMD"]
    min_year = 2020
    stock_data = yahoo.stock_history(tickers, min_year)

    assert (
        round(stock_data.iloc[0]["last_price"], 2) == 49.1
    ), "Stock data not pulled correctly."

    expected_columns = ["ticker", "date", "last_price"]
    assert (
        list(stock_data.columns) == expected_columns
    ), "Stock data columns not correct."


def test_news():
    """Checks that stock news can be pulled."""
    yahoo = wrappers.Yahoo()
    ticker = "AMD"
    news = yahoo.news(ticker)
    assert news.shape[0] > 0, "News not pulled."


def test_info():
    """Checks that stock information can be pulled."""
    yahoo = wrappers.Yahoo()
    ticker = "AMD"
    info = yahoo.info(ticker)
    assert info.shape[0] > 0, "Info not pulled."

    expected_values = [
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
        "longBusinessSummary",
        "fullTimeEmployees",
        "companyOfficers",
        "auditRisk",
        "boardRisk",
        "compensationRisk",
        "shareHolderRightsRisk",
        "overallRisk",
        "governanceEpochDate",
        "compensationAsOfEpochDate",
        "maxAge",
        "priceHint",
        "previousClose",
        "open",
        "dayLow",
        "dayHigh",
        "regularMarketPreviousClose",
        "regularMarketOpen",
        "regularMarketDayLow",
        "regularMarketDayHigh",
        "exDividendDate",
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
        "currentPrice",
        "targetHighPrice",
        "targetLowPrice",
        "targetMeanPrice",
        "targetMedianPrice",
        "recommendationMean",
        "recommendationKey",
        "numberOfAnalystOpinions",
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
    ]

    missing_values = set(expected_values).difference(set(info.index))
    assert (
        missing_values == set()
    ), f"Missing values in info such as {sorted(missing_values)[0]}."


def test_quote():
    """Checks that stock quote can be pulled."""
    yahoo = wrappers.Yahoo()
    ticker = "AMD"
    quote = yahoo.quote(ticker)
    assert quote.shape[0] > 0, "Quote not pulled."
