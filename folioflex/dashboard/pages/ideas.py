"""Ideas dashboard."""

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, callback, dash_table, dcc, html

from folioflex.dashboard.utils import dashboard_helper
from folioflex.portfolio import wrappers
from folioflex.utils import custom_logger

logger = custom_logger.setup_logging(__name__)

dash.register_page(__name__, path="/ideas", title="folioflex - Ideas", order=3)

#   _                            _
#  | |    __ _ _   _  ___  _   _| |_
#  | |   / _` | | | |/ _ \| | | | __|
#  | |__| (_| | |_| | (_) | |_| | |_
#  |_____\__,_|\__, |\___/ \__,_|\__|
#              |___/


def layout():
    """Ideas layout."""
    return dbc.Container(
        [
            # adding variables needed that are used in callbacks.
            *dashboard_helper.get_defaults(),
            html.H2("Investment Ideas Dashboard", className="text-center my-4"),
            # ---------------------------------------------------------------
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            dcc.Markdown(
                                """
                                Momentum and Value are 2 metrics that determine the viability of
                                investing in the market. **12 mo Moving Average** - current price
                                of market is greater than the 12 month moving average. **12 mo
                                TMOM** - 12 month return is greater than the return of the 10
                                year treasury bond It's recommended to do 50% of
                                investment in one method and 50% in other
                                """
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            dbc.Card(
                [
                    dbc.CardHeader(html.H4("Simple Moving Average Analysis")),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dcc.Input(
                                            id="idea-input",
                                            placeholder="Enter Stock Symbol...",
                                            type="text",
                                            className="form-control",
                                        ),
                                        xs=12,
                                        md=6,
                                        className="mb-2 mb-md-0",
                                    ),
                                    dbc.Col(
                                        dbc.Button(
                                            "Calculate SMA",
                                            id="sma-button",
                                            n_clicks=0,
                                            color="primary",
                                            className="w-100",
                                        ),
                                        xs=12,
                                        md="auto",
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.A(
                                "10-Year Treasury Reference",
                                href="https://fred.stlouisfed.org/series/DGS10",
                                target="_blank",
                                className="mb-3 d-block",
                            ),
                            # simple moving average
                            dash_table.DataTable(
                                id="sma-table",
                                page_action="native",
                                style_table={"overflowX": "auto"},
                            ),
                        ]
                    ),
                ],
            ),
        ],
        fluid=True,
    )


#    ____      _ _ _                _
#   / ___|__ _| | | |__   __ _  ___| | _____
#  | |   / _` | | | '_ \ / _` |/ __| |/ / __|
#  | |__| (_| | | | |_) | (_| | (__|   <\__ \
#   \____\__,_|_|_|_.__/ \__,_|\___|_|\_\___/


@callback(
    [
        Output(component_id="sma-table", component_property="columns"),
        Output(component_id="sma-table", component_property="data"),
    ],
    [Input(component_id="sma-button", component_property="n_clicks")],
    [State(component_id="idea-input", component_property="value")],
)
def sma_value(n_clicks, input_value):
    """Provide simple moving average on ideas."""
    if n_clicks == 0:
        sma_table = (None, None)
    else:
        sma = wrappers.Yahoo().get_sma(ticker=input_value, days=365)
        latest_price = wrappers.Yahoo().fast_info(ticker=input_value)["lastPrice"]
        change_percent = wrappers.Yahoo().get_change_percent(
            ticker=input_value, days=365
        )

        # build table
        sma_table = [input_value, sma, latest_price, change_percent]
        df = pd.DataFrame(
            [sma_table], columns=["stock", "sma", "latest_price", "change_percent"]
        )

        sma_table = [{"name": i, "id": i} for i in df.columns], df.to_dict("records")

    return sma_table
