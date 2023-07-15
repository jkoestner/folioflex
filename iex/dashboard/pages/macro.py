"""Macro dashboard."""

from dash import dcc
from dash import html
from urllib import request
from iex import constants

from iex.dashboard import utils

# Creating the dash app
recession = (
    request.urlopen(
        "https://cloud.iexapis.com/stable/data-points/market/RECPROUSM156N?token="
        + constants.iex_api_live
    )
    .read()
    .decode("utf8")
)
housing = (
    request.urlopen(
        "https://cloud.iexapis.com/stable/data-points/market/HOUST?token="
        + constants.iex_api_live
    )
    .read()
    .decode("utf8")
)
unemployment = (
    request.urlopen(
        "https://cloud.iexapis.com/stable/data-points/market/UNRATE?token="
        + constants.iex_api_live
    )
    .read()
    .decode("utf8")
)
fedfunds = (
    request.urlopen(
        "https://cloud.iexapis.com/stable/data-points/market/FEDFUNDS?token="
        + constants.iex_api_live
    )
    .read()
    .decode("utf8")
)
cpiaucsl = (
    request.urlopen(
        "https://cloud.iexapis.com/stable/data-points/market/CPIAUCSL?token="
        + constants.iex_api_live
    )
    .read()
    .decode("utf8")
)


layout = html.Div(
    [
        html.Div(
            [
                utils.get_menu(),
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
                            "US Inflation",
                            href="https://fred.stlouisfed.org/series/CPIAUCSL",
                            target="_blank",
                        ),
                        html.Label(cpiaucsl),
                    ],
                    className="three columns",
                ),
            ],
            className="row",
        ),
    ]
)
