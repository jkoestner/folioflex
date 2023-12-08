"""Macro dashboard."""

from dash import dash_table, dcc, html

from folioflex.dashboard import dashboard_helper
from folioflex.portfolio.wrappers import BLS, Fred, TradingView

# Creating the dash app


def layout(login_status, login_alert):
    """Macro layout."""
    # getting data from wrappers
    fred_summary = Fred().get_summary()
    bls_cpi = BLS().get_cpi()
    economic_calendar = TradingView().get_economic_calendar()

    # creating html table for items
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
            "Link": "https://fred.stlouisfed.org/series/FEDFUNDS",
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

    indicators_table = dash_table.DataTable(
        id="key-indicators-table",
        columns=[
            {"name": "Indicator", "id": "Indicator"},
            {"name": "Value", "id": "Value"},
            {
                "name": "Source",
                "id": "Link",
                "type": "text",
                "presentation": "markdown",
            },
        ],
        data=[{**row, "Link": f"[Source]({row['Link']})"} for row in indicators_data],
        style_table={"overflowX": "auto"},
        markdown_options={"link_target": "_blank"},
    )

    return html.Div(
        [
            # adding variables needed that are used in callbacks.
            *dashboard_helper.get_defaults(),
            dcc.Store(id="login-status", data=login_status),
            html.Div(id="login-alert", children=login_alert, style={"display": "none"}),
            # ---------------------------------------------------------------
            # menu section
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
            # key indicators section
            html.Div(
                [
                    html.Div(
                        indicators_table,
                        className="four columns",
                    ),
                ],
                className="row",
            ),
            # economic calendar section
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
                                style_cell={
                                    "whiteSpace": "normal",
                                    "height": "auto",
                                    "textAlign": "left",
                                },
                                style_cell_conditional=[
                                    # Apply a default width to all columns
                                    {
                                        "if": {"column_id": c},
                                        "minWidth": "50px",
                                        "width": "150px",
                                        "maxWidth": "180px",
                                    }
                                    for c in economic_calendar.columns
                                    if c != "comment"
                                ]
                                + [
                                    # Specifically targeting the 'comment'
                                    # column to have a larger width
                                    {
                                        "if": {"column_id": "comment"},
                                        "minWidth": "150px",
                                        "width": "2400px",
                                        "maxWidth": "2450px",
                                    },
                                ],
                                style_table={"overflowX": "auto"},
                                page_action="none",
                                style_data={"overflow": "hidden"},
                            ),
                        ],
                        className="ten columns",
                    ),
                ],
                className="row",
            ),
        ]
    )
