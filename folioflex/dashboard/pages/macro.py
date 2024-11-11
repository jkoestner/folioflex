"""Macro dashboard."""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, html

from folioflex.dashboard.utils import dashboard_helper
from folioflex.portfolio.wrappers import BLS, Fred, TradingView
from folioflex.utils import custom_logger

logger = custom_logger.setup_logging(__name__)

dash.register_page(__name__, path="/macro", title="folioflex - Macro", order=2)

#   _                            _
#  | |    __ _ _   _  ___  _   _| |_
#  | |   / _` | | | |/ _ \| | | | __|
#  | |__| (_| | |_| | (_) | |_| | |_
#  |_____\__,_|\__, |\___/ \__,_|\__|
#              |___/


def layout():
    """Macro layout."""
    return dbc.Container(
        [
            html.H2("Macro Economic Dashboard", className="text-center my-4"),
            # buttons
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Button(
                            "Show Indicators",
                            id="indicators-button",
                            n_clicks=0,
                            color="primary",
                        ),
                        width="auto",
                    ),
                    dbc.Col(
                        dbc.Button(
                            "Show Economic Calendar",
                            id="calendar-button",
                            n_clicks=0,
                            color="primary",
                        ),
                        width="auto",
                    ),
                ],
                className="mb-4",
                justify="center",
            ),
            html.Div(id="content-container"),
            # adding variables needed that are used in callbacks.
            *dashboard_helper.get_defaults(),
        ],
        fluid=True,
    )


#    ____      _ _ _                _
#   / ___|__ _| | | |__   __ _  ___| | _____
#  | |   / _` | | | '_ \ / _` |/ __| |/ / __|
#  | |__| (_| | | | |_) | (_| | (__|   <\__ \
#   \____\__,_|_|_|_.__/ \__,_|\___|_|\_\___/
#


# economic indicator and calendar buttons
@callback(
    Output("content-container", "children"),
    [
        Input("indicators-button", "n_clicks"),
        Input("calendar-button", "n_clicks"),
    ],
)
def display_content(indicators_clicks, calendar_clicks):
    """Display content based on button clicks."""
    ctx = dash.callback_context

    if not ctx.triggered:
        return html.Div()
    else:
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "indicators-button":
        return dbc.Card(
            [
                dbc.CardHeader(html.H4("Key Indicators")),
                dbc.CardBody(
                    [
                        create_indicators_table(),
                    ]
                ),
            ],
            className="mt-4",
        )
    elif button_id == "calendar-button":
        return dbc.Card(
            [
                dbc.CardHeader(html.H4("Economic Calendar")),
                dbc.CardBody(
                    [
                        create_economic_calendar_table(),
                    ]
                ),
            ],
            className="mt-4",
        )
    else:
        return html.Div()


def create_indicators_table():
    """Create the indicators table."""
    # Getting data from wrappers
    fred_summary = Fred().get_summary()
    bls_cpi = BLS().get_cpi()

    indicators_data = [
        {
            "Indicator": "US Recession Probability",
            "Value": fred_summary["recession"],
            "Link": "https://fred.stlouisfed.org/series/RECPROUSM156N",
        },
        {
            "Indicator": "US Housing Starts",
            "Value": fred_summary["housing_starts"],
            "Link": "https://fred.stlouisfed.org/series/HOUST",
        },
        {
            "Indicator": "US Unemployment Rate",
            "Value": fred_summary["unemployment"],
            "Link": "https://fred.stlouisfed.org/series/UNRATE",
        },
        {
            "Indicator": "US Federal Fund Rate",
            "Value": fred_summary["fed_funds"],
            "Link": "https://fred.stlouisfed.org/series/FEDFUNDS",
        },
        {
            "Indicator": "US CPI - FRED",
            "Value": fred_summary["inflation"],
            "Link": "https://fred.stlouisfed.org/series/CPIAUCSL",
        },
        {
            "Indicator": "US Inflation (YoY) - BLS",
            "Value": f"{bls_cpi['cpi']} - {bls_cpi['month']}",
            "Link": "https://www.bls.gov/charts/consumer-price-index/consumer-price-index-by-category-line-chart.htm",
        },
        {
            "Indicator": "10-year Treasury",
            "Value": fred_summary["10_year"],
            "Link": "https://fred.stlouisfed.org/series/DGS10",
        },
    ]
    columns = [
        {"name": "Indicator", "id": "Indicator"},
        {"name": "Value", "id": "Value"},
        {
            "name": "Source",
            "id": "Link",
            "type": "text",
            "presentation": "markdown",
        },
    ]
    data = [{**row, "Link": f"[Source]({row['Link']})"} for row in indicators_data]
    indicators_table = dashboard_helper.create_datatable(columns, data)

    return indicators_table


def create_economic_calendar_table():
    """Create the economic calendar table."""
    # Getting data from wrapper
    economic_calendar = TradingView().get_economic_calendar()
    columns = [{"name": i, "id": i} for i in economic_calendar.columns]
    data = economic_calendar.to_dict("records")
    economic_calendar_table = dashboard_helper.create_datatable(columns, data)

    return economic_calendar_table
