import dash
from dash import dcc
from dash import html
import pandas as pd
import dash_table
from urllib import request
from dash.dependencies import Input, Output, State
from pages import utils

# Creating the dash app
recession = (
    request.urlopen(
        "https://cloud.iexapis.com/stable/data-points/market/RECPROUSM156N?token=pk_5d82796966de466bb2f966ed65ca70c7"
    )
    .read()
    .decode("utf8")
)
housing = (
    request.urlopen(
        "https://cloud.iexapis.com/stable/data-points/market/HOUST?token=pk_5d82796966de466bb2f966ed65ca70c7"
    )
    .read()
    .decode("utf8")
)
unemployment = (
    request.urlopen(
        "https://cloud.iexapis.com/stable/data-points/market/UNRATE?token=pk_5d82796966de466bb2f966ed65ca70c7"
    )
    .read()
    .decode("utf8")
)
fedfunds = (
    request.urlopen(
        "https://cloud.iexapis.com/stable/data-points/market/FEDFUNDS?token=pk_5d82796966de466bb2f966ed65ca70c7"
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
                    ],
                    className="three columns",
                ),
            ],
            className="row",
        ),
    ]
)
