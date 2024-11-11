"""Stocks dashboard."""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, html

from folioflex.dashboard.components import layouts
from folioflex.dashboard.utils import dashboard_helper
from folioflex.portfolio import wrappers
from folioflex.utils import custom_logger

logger = custom_logger.setup_logging(__name__)

dash.register_page(__name__, path="/", title="folioflex", order=0)

#   _                            _
#  | |    __ _ _   _  ___  _   _| |_
#  | |   / _` | | | |/ _ \| | | | __|
#  | |__| (_| | |_| | (_) | |_| | |_
#  |_____\__,_|\__, |\___/ \__,_|\__|
#              |___/


def layout():
    """Stocks layout."""
    return dbc.Container(
        [
            # Header
            html.H2("Stock Analysis Dashboard", className="text-center my-4"),
            # Screener Section
            dbc.Card(
                [
                    dbc.CardHeader(html.H4("Screener")),
                    dbc.CardBody(
                        [
                            dbc.Button(
                                "Active",
                                id="active-button",
                                n_clicks=0,
                                color="primary",
                            ),
                            html.Div(id="active-table-container"),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            # Stock Analysis Section
            dbc.Card(
                [
                    dbc.CardHeader(html.H4("Stock Analysis")),
                    dbc.CardBody(
                        [
                            # Input Field
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Input(
                                            id="stock-input",
                                            placeholder="Enter Stock Symbol...",
                                            type="text",
                                        ),
                                        width=4,
                                    ),
                                    dbc.Col(
                                        dbc.ButtonGroup(
                                            [
                                                dbc.Button(
                                                    "Stock Info",
                                                    id="stock-button",
                                                    n_clicks=0,
                                                    color="primary",
                                                ),
                                                dbc.Button(
                                                    "Quote",
                                                    id="quote-button",
                                                    n_clicks=0,
                                                    color="primary",
                                                ),
                                                dbc.Button(
                                                    "News",
                                                    id="news-button",
                                                    n_clicks=0,
                                                    color="primary",
                                                ),
                                                dbc.Button(
                                                    "Insider",
                                                    id="insider-summary-button",
                                                    n_clicks=0,
                                                    color="primary",
                                                ),
                                                dbc.Button(
                                                    "Earnings Calendar",
                                                    id="earnings-button",
                                                    n_clicks=0,
                                                    color="primary",
                                                ),
                                            ]
                                        ),
                                        width=8,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Stock Analysis Table Container
                            html.Div(id="stock-table-container"),
                        ]
                    ),
                ]
            ),
        ],
        fluid=True,
    )


#    ____      _ _ _                _
#   / ___|__ _| | | |__   __ _  ___| | _____
#  | |   / _` | | | '_ \ / _` |/ __| |/ / __|
#  | |__| (_| | | | |_) | (_| | (__|   <\__ \
#   \____\__,_|_|_|_.__/ \__,_|\___|_|\_\___/


# Callback for Screener Section
@callback(
    Output("active-table-container", "children"),
    Input("active-button", "n_clicks"),
)
def display_active_table(n_clicks):
    """Display most active stocks table."""
    if n_clicks > 0:
        # Generate active table
        active = wrappers.Yahoo().most_active(count=25)
        active = active.reset_index()
        columns = layouts.active_fmt
        data = active.to_dict("records")
        table = dashboard_helper.create_datatable(columns, data)
        return dbc.Card(
            [
                dbc.CardHeader("Most Active Stocks"),
                dbc.CardBody(table),
            ],
            className="mt-4",
        )
    else:
        return html.Div()


# Callback for Stock Analysis Section
@callback(
    Output("stock-table-container", "children"),
    [
        Input("stock-button", "n_clicks"),
        Input("quote-button", "n_clicks"),
        Input("news-button", "n_clicks"),
        Input("insider-summary-button", "n_clicks"),
        Input("earnings-button", "n_clicks"),
    ],
    State("stock-input", "value"),
)
def display_stock_table(
    stock_clicks,
    quote_clicks,
    news_clicks,
    insider_clicks,
    earnings_clicks,
    input_value,
):
    """Display stock information table."""
    ctx = dash.callback_context

    if not ctx.triggered:
        return html.Div()
    else:
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if not input_value:
        return dbc.Alert("Please enter a stock symbol.", color="warning")

    if button_id == "stock-button":
        # Generate stock info table
        stock = wrappers.Yahoo().info(input_value)
        stock = stock.reset_index()
        stock.columns = ["Variable", "Value"]
        stock = stock[stock["Variable"].isin(layouts.yahoo_info["info"])]
        columns = [{"name": i, "id": i} for i in stock.columns]
        data = stock.to_dict("records")
        table = dashboard_helper.create_datatable(columns, data)
        return dbc.Card(
            [
                dbc.CardHeader(f"Stock Information: {input_value.upper()}"),
                dbc.CardBody(table),
            ],
            className="mt-4",
        )
    elif button_id == "quote-button":
        # Generate quote table
        quote = wrappers.Yahoo().quote(input_value)
        quote = quote.reset_index()
        columns = [{"name": i, "id": i} for i in quote.columns]
        data = quote.to_dict("records")
        table = dashboard_helper.create_datatable(columns, data)
        return dbc.Card(
            [
                dbc.CardHeader(f"Quote Information: {input_value.upper()}"),
                dbc.CardBody(table),
            ],
            className="mt-4",
        )
    elif button_id == "news-button":
        # Generate news table
        news_table = wrappers.Yahoo().news(input_value)
        news_table = news_table.drop(columns=["relatedTickers"])
        news_table = news_table.reset_index()
        news_table["link"] = news_table.apply(
            lambda row: f"[{row['link']}]({row['link']})", axis=1
        )
        columns = [
            {"name": i, "id": i, "presentation": "markdown"}
            if i == "link"
            else {"name": i, "id": i}
            for i in news_table.columns
        ]
        data = news_table.to_dict("records")
        table = dashboard_helper.create_datatable(columns, data)
        return dbc.Card(
            [
                dbc.CardHeader(f"Latest News: {input_value.upper()}"),
                dbc.CardBody(table),
            ],
            className="mt-4",
        )
    elif button_id == "insider-summary-button":
        # Generate insider summary table
        insider = wrappers.Web().insider_activity(ticker=input_value)
        insider = insider.reset_index()
        insider = insider.head(10)
        columns = [{"name": i, "id": i} for i in insider.columns]
        data = insider.to_dict("records")
        table = dashboard_helper.create_datatable(columns, data)
        return dbc.Card(
            [
                dbc.CardHeader(f"Insider Activity: {input_value.upper()}"),
                dbc.CardBody(table),
            ],
            className="mt-4",
        )
    elif button_id == "earnings-button":
        # Generate earnings table
        earnings = wrappers.Yahoo().earnings_calendar(input_value)
        earnings = earnings.reset_index()
        columns = [{"name": i, "id": i} for i in earnings.columns]
        data = earnings.to_dict("records")
        table = dashboard_helper.create_datatable(columns, data)
        return dbc.Card(
            [
                dbc.CardHeader(f"Earnings: {input_value.upper()}"),
                dbc.CardBody(table),
            ],
            className="mt-4",
        )
    else:
        return html.Div()
