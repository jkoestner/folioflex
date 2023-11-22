"""Macro dashboard."""

from dash import dash_table
from dash import dcc
from dash import html

from folioflex.dashboard import dashboard_helper
from folioflex.portfolio.wrappers import BLS, Fred, TradingView

# Creating the dash app
fred_summary = Fred().get_summary()
bls_cpi = BLS().get_cpi()
economic_calendar = TradingView().get_economic_calendar()


def layout(login_status, login_alert):
    """Macro layout."""
    return html.Div(
        [
            # adding variables needed that are used in callbacks.
            *dashboard_helper.get_defaults(),
            dcc.Store(id="login-status", data=login_status),
            html.Div(id="login-alert", children=login_alert, style={"display": "none"}),
            # ---------------------------------------------------------------
            html.Div(
                [
                    dashboard_helper.get_menu(),
                    dcc.Markdown(
                        """
                        Macro indicators
                        """
                    ),
                    html.P(),
                ],
                className="row",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            # creating recession
                            html.A(
                                "US Recession Probability",
                                href="https://fred.stlouisfed.org/series/RECPROUSM156N",
                                target="_blank",
                            ),
                            html.Label(fred_summary["recession"]),
                            # creating housing starts
                            html.A(
                                "US Housing Starts",
                                href="https://fred.stlouisfed.org/series/HOUST",
                                target="_blank",
                            ),
                            html.Label(fred_summary["housing_starts"]),
                            # creating unemployment rate
                            html.A(
                                "US Unemployment Rate",
                                href="https://fred.stlouisfed.org/series/UNRATE",
                                target="_blank",
                            ),
                            html.Label(fred_summary["unemployment"]),
                            # creating fed fund rate
                            html.A(
                                "US Federal Fund Rate",
                                href="https://fred.stlouisfed.org/series/FEDFUNDS",
                                target="_blank",
                            ),
                            html.Label(fred_summary["fed_funds"]),
                            # CPI
                            html.A(
                                "US CPI - FRED",
                                href="https://fred.stlouisfed.org/series/CPIAUCSL",
                                target="_blank",
                            ),
                            html.Label(fred_summary["inflation"]),
                            # BLS - inflation
                            html.A(
                                "US Inflation (YoY) - BLS",
                                href=(
                                    "https://www.bls.gov/charts/consumer-price-index/"
                                    "consumer-price-index-by-category-line-chart.htm"
                                ),
                                target="_blank",
                            ),
                            html.Label(f"{bls_cpi['cpi']} - {bls_cpi['month']}"),
                            # 10-year treasury
                            html.A(
                                "10-year Treasury",
                                href="https://fred.stlouisfed.org/series/DGS10",
                                target="_blank",
                            ),
                            html.Label(fred_summary["10_year"]),
                        ],
                        className="three columns",
                    ),
                ],
                className="row",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            # creating economic calendar
                            html.A(
                                "Economic Calendar",
                                href="https://www.tradingview.com/economic-calendar/",
                                target="_blank",
                            ),
                            dash_table.DataTable(
                                id="economic-calendar",
                                columns=[
                                    {"name": i, "id": i}
                                    for i in economic_calendar.columns
                                ],
                                data=economic_calendar.to_dict("records"),
                            ),
                        ],
                        className="three columns",
                    ),
                ],
                className="row",
            ),
        ]
    )
