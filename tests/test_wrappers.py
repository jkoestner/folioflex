"""Tests the wrappers."""

import pytest

from folioflex.portfolio import wrappers


def test_stock_history():
    """Checks that stock information can be pulled."""
    yahoo = wrappers.Yahoo()
    tickers = ["AMD"]
    min_year = 2020
    stock_data = yahoo.stock_history(tickers, min_year)

    assert (
        round(stock_data.iloc[0]["last_price"], 2) == 49.1
    ), "Stock data not pulled correctly."

    expected_columns = ["ticker", "date", "last_price", "stock_splits"]
    assert (
        list(stock_data.columns) == expected_columns
    ), "Stock data columns not correct."


def test_news():
    """Checks that stock news can be pulled."""
    yahoo = wrappers.Yahoo()
    ticker = "AMD"
    news = yahoo.news(ticker)
    assert news.shape[0] > 0, "News not pulled."


@pytest.mark.xfail
def test_info():
    """Checks that stock information can be pulled."""
    yahoo = wrappers.Yahoo()
    ticker = "AMD"
    info = yahoo.info(ticker)
    assert info.shape[0] > 0, "Info not pulled."


def test_quote():
    """Checks that stock quote can be pulled."""
    yahoo = wrappers.Yahoo()
    ticker = "AMD"
    quote = yahoo.quote(ticker)
    assert quote.shape[0] > 0, "Quote not pulled."
