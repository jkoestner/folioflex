"""Macro dashboard."""

from dash import dcc
from dash import html

from folioflex.dashboard import dashboard_helper
from folioflex.portfolio.wrappers import Fred

# Creating the dash app
fred_summary = Fred().get_summary()
recession = fred_summary["recession"]
housing = fred_summary["housing_starts"]
unemployment = fred_summary["unemployment"]
fedfunds = fred_summary["fed_funds"]
cpiaucsl = fred_summary["inflation"]


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
                            html.Label(recession),
                            # creating housing starts
                            html.A(
                                "US Housing Starts",
                                href="https://fred.stlouisfed.org/series/HOUST",
                                target="_blank",
                            ),
                            html.Label(housing),
                            # creating unemployment rate
                            html.A(
                                "US Unemployment Rate",
                                href="https://fred.stlouisfed.org/series/UNRATE",
                                target="_blank",
                            ),
                            html.Label(unemployment),
                            # creating fed fund rate
                            html.A(
                                "US Federal Fund Rate",
                                href="https://fred.stlouisfed.org/series/FEDFUNDS",
                                target="_blank",
                            ),
                            html.Label(fedfunds),
                            # creating cpi
                            html.A(
                                "US Inflation - FRED",
                                href="https://fred.stlouisfed.org/series/CPIAUCSL",
                                target="_blank",
                            ),
                            html.Label(cpiaucsl),
                            html.A(
                                "US Inflation - BLS",
                                href=(
                                    "https://www.bls.gov/charts/consumer-price-index/"
                                    "consumer-price-index-by-category-line-chart.htm"
                                ),
                                target="_blank",
                            ),
                        ],
                        className="three columns",
                    ),
                ],
                className="row",
            ),
        ]
    )
