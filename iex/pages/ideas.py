"""Ideas dashboard."""

from dash import dash_table
from dash import dcc
from dash import html

from iex.util import utils

# Creating the dash app

layout = html.Div(
    [
        html.Div(
            [
                utils.get_menu(),
                dcc.Markdown(
                    """
                    Momentum and Value are 2 metrics that determine the viability of investing in the market.
                    **12 mo Moving Average** - current price of market is greater than the 12 month moving average.
                    **12 mo TMOM** - 12 month return is greater than the return of the 10 year treasury bond
                    It's recommended to do 50% of investment in one method and 50% in other
                    """
                ),
                html.P(),
                dcc.Input(id="idea-input", placeholder="Enter Stock...", type="text"),
                html.Button(id="sma-button", children="SMA Submit"),
                html.P(),
                # creating fed fund rate
                html.A(
                    "10-Year Treasury",
                    href="https://fred.stlouisfed.org/series/DGS10",
                    target="_blank",
                ),
            ],
            className="row",
        ),
        html.Div(
            [
                html.Div(
                    [
                        # simple moving average
                        dash_table.DataTable(
                            id="sma-table",
                            page_action="native",
                        ),
                    ],
                    className="three columns",
                ),
            ],
            className="row",
        ),
    ]
)
