"""Stocks dashboard."""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dash_table, dcc, html

from folioflex.dashboard.components import layouts
from folioflex.dashboard.utils import dashboard_helper
from folioflex.portfolio import wrappers
from folioflex.utils import custom_logger

logger = custom_logger.setup_logging(__name__)

dash.register_page(__name__, path="/", title="folioflex - Stocks", order=0)

#   _                            _
#  | |    __ _ _   _  ___  _   _| |_
#  | |   / _` | | | |/ _ \| | | | __|
#  | |__| (_| | |_| | (_) | |_| | |_
#  |_____\__,_|\__, |\___/ \__,_|\__|
#              |___/


def layout():
    """Stocks layout."""
    return html.Div(
        [
            # adding variables needed that are used in callbacks.
            *dashboard_helper.get_defaults(),
            # ---------------------------------------------------------------
            html.Div(
                [
                    html.Label("Stock Analysis"),
                    html.P(),
                    dcc.Markdown(
                        """
                    A site to review for insider activity.
                    http://www.insiderinsights.com/free
                    """
                    ),
                    html.P(),
                    dbc.Col(
                        [
                            dcc.Input(
                                id="stock-input",
                                placeholder="Enter Stock...",
                                type="text",
                            ),
                            html.Button(
                                "Active Submit", id="active-button", n_clicks=0
                            ),
                            html.Button("Stock Submit", id="stock-button", n_clicks=0),
                            html.Button("Quote Submit", id="quote-button", n_clicks=0),
                            html.Button("News Submit", id="news-button", n_clicks=0),
                            html.Button(
                                "Insider Summary Submit",
                                id="insider-summary-button",
                                n_clicks=0,
                            ),
                        ]
                    ),
                ],
                className="row",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            # creating active information
                            html.P(),
                            dash_table.DataTable(
                                id="active-table",
                                page_action="native",
                                sort_action="native",
                            ),
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
                            # creating stock information
                            dash_table.DataTable(
                                id="stock-table",
                                page_action="native",
                            ),
                        ],
                        className="three columns",
                    ),
                    html.Div(
                        [
                            # creating quote information
                            dash_table.DataTable(
                                id="quote-table",
                                page_action="native",
                            ),
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
                            # creating news information
                            html.P(),
                            dash_table.DataTable(
                                id="news-table",
                                page_action="native",
                            ),
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
                            # creating insider summary
                            html.P(),
                            dash_table.DataTable(
                                id="insider-summary-table",
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


#    ____      _ _ _                _
#   / ___|__ _| | | |__   __ _  ___| | _____
#  | |   / _` | | | '_ \ / _` |/ __| |/ / __|
#  | |__| (_| | | | |_) | (_| | (__|   <\__ \
#   \____\__,_|_|_|_.__/ \__,_|\___|_|\_\___/


@callback(
    [
        Output("stock-table", "columns"),
        Output("stock-table", "data"),
    ],
    [Input("stock-button", "n_clicks")],
    [State("stock-input", "value")],
)
def update_stockanalysis(n_clicks, input_value):
    """Provide stock info table."""
    if n_clicks == 0:
        stock_table = (None, None)
    else:
        stock = wrappers.Yahoo().info(input_value)
        stock = stock.reset_index()
        stock.columns = ["Variable", "Value"]
        stock = stock[stock["Variable"].isin(layouts.yahoo_info["info"])]

        stock_table = (
            [{"name": i, "id": i} for i in stock.columns],
            stock.to_dict("records"),
        )

    return stock_table


@callback(
    [
        Output("quote-table", "columns"),
        Output("quote-table", "data"),
    ],
    [Input("quote-button", "n_clicks")],
    [State("stock-input", "value")],
)
def update_quoteanalysis(n_clicks, input_value):
    """Provide quote analysis table."""
    if n_clicks == 0:
        quote_table = (None, None)
    else:
        quote = wrappers.Yahoo().quote(input_value)
        quote = quote.reset_index()

        quote_table = (
            [{"name": i, "id": i} for i in quote.columns],
            quote.to_dict("records"),
        )

    return quote_table


@callback(
    [
        Output("news-table", "columns"),
        Output("news-table", "data"),
    ],
    [Input("news-button", "n_clicks")],
    [State("stock-input", "value")],
)
def update_newsanalysis(n_clicks, input_value):
    """Provide news analysis table."""
    if n_clicks == 0:
        news_table = (None, None)
    else:
        news_table = wrappers.Yahoo().news(input_value)
        news_table = news_table.drop(columns=["relatedTickers"])
        news_table = news_table.reset_index()

        news_table = (
            [{"name": i, "id": i} for i in news_table.columns],
            news_table.to_dict("records"),
        )

    return news_table


@callback(
    [
        Output("active-table", "columns"),
        Output("active-table", "data"),
    ],
    [Input("active-button", "n_clicks")],
)
def update_activeanalysis(n_clicks):
    """Provide active analysis table."""
    if n_clicks == 0:
        active_table = (None, None)
    else:
        active = wrappers.Yahoo().most_active(count=25)
        active = active.reset_index()

        active_table = layouts.active_fmt, active.to_dict("records")

    return active_table


@callback(
    [
        Output("insider-summary-table", "columns"),
        Output("insider-summary-table", "data"),
    ],
    [Input("insider-summary-button", "n_clicks")],
    [State("stock-input", "value")],
)
def update_insidersummaryanalysis(n_clicks, input_value):
    """Provide insider summary table."""
    if n_clicks == 0:
        insider_summary_table = (None, None)
    else:
        insider = wrappers.Web().insider_activity(ticker=input_value)
        insider = insider.reset_index()
        insider = insider.head(10)

        insider_summary_table = (
            [{"name": i, "id": i} for i in insider.columns],
            insider.to_dict("records"),
        )

    return insider_summary_table
