"""
Building plotly dashboard.

Builds plotly pages with call backs. There are 2 options the user has for running code.
1. Fly.io build set up
2. Local running

To run locally:
1. cd into root directory
2. run plotly dashboard - `python app.py`

The ascii text is generated using https://patorjk.com/software/taag/
with "standard font"
"""

from io import StringIO

import dash
import pandas as pd
import plotly.graph_objs as go
from celery.result import AsyncResult
from dash import dcc, html
from dash.dash_table.Format import Format, Scheme
from dash.dependencies import Input, Output, State

from folioflex.budget import budget
from folioflex.dashboard import dashboard_helper, layouts, pages
from folioflex.portfolio import heatmap, wrappers
from folioflex.utils import config_helper, cq

#      _    ____  ____
#     / \  |  _ \|  _ \
#    / _ \ | |_) | |_) |
#   / ___ \|  __/|  __/
#  /_/   \_\_|   |_|

app = dash.Dash(
    __name__, external_stylesheets=["https://codepen.io/chriddyp/pen/bWLwgP.css"]
)
server = app.server
app.config.suppress_callback_exceptions = True

app.title = "FolioFlex"
app._favicon = "folioflex_logo.ico"
app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        html.Div(id="page-content"),
        dcc.Store(id="login-status", storage_type="session"),
        html.Div(id="login-alert", children="", style={"display": "none"}),
    ]
)

#   ___ _   _ ____  _______  __
#  |_ _| \ | |  _ \| ____\ \/ /
#   | ||  \| | | | |  _|  \  /
#   | || |\  | |_| | |___ /  \
#  |___|_| \_|____/|_____/_/\_\


@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname"), Input("login-alert", "children")],
    State("login-status", "data"),
)
def display_page(pathname, login_alert, login_status):
    """Create navigation for app."""
    if pathname == "/":
        return pages.stocks.layout(login_status=login_status, login_alert=login_alert)
    elif pathname == "/stocks":
        return pages.stocks.layout(login_status=login_status, login_alert=login_alert)
    elif pathname == "/sectors":
        return pages.sectors.layout(login_status=login_status, login_alert=login_alert)
    elif pathname == "/ideas":
        return pages.ideas.layout(login_status=login_status, login_alert=login_alert)
    elif pathname == "/macro":
        return pages.macro.layout(login_status=login_status, login_alert=login_alert)
    elif pathname == "/personal":
        if not login_status or not login_status.get("logged_in"):
            return pages.login.layout(
                login_status=login_status, login_alert=login_alert
            )
        else:
            return pages.personal.layout(
                login_status=login_status, login_alert=login_alert
            )
    elif pathname == "/budget":
        if not login_status or not login_status.get("logged_in"):
            return pages.login.layout(
                login_status=login_status, login_alert=login_alert
            )
        else:
            return pages.budget.layout(
                login_status=login_status, login_alert=login_alert
            )
    else:
        return "404"


#   ____ _____ ___   ____ _  __
#  / ___|_   _/ _ \ / ___| |/ /
#  \___ \ | || | | | |   | ' /
#   ___) || || |_| | |___| . \
#  |____/ |_| \___/ \____|_|\_\


@app.callback(
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


@app.callback(
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


@app.callback(
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


@app.callback(
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


@app.callback(
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


#   ____  _____ ____ _____ ___  ____
#  / ___|| ____/ ___|_   _/ _ \|  _ \
#  \___ \|  _|| |     | || | | | |_) |
#   ___) | |__| |___  | || |_| |  _ <
#  |____/|_____\____| |_| \___/|_| \_\


# Sector Graph
@app.callback(
    Output("task-id", "children"),
    [Input(component_id="sector-initialize", component_property="n_clicks")],
)
def initialize_SectorGraph(n_clicks):
    """Provide sector analysis graph."""
    if n_clicks == 0:
        task_id = "none"
    else:
        task = cq.sector_query.delay()
        task_id = task.id

    return task_id


@app.callback(
    [Output("task-status", "children"), Output("refresh_text", "children")],
    [Input("interval-component", "n_intervals")],
    [State("task-id", "children"), State("task-status", "children")],
)
def status_check(n_intervals, task_id, task_status):
    """Provide status check."""
    if task_id != "none":
        task = AsyncResult(task_id, app=cq.celery_app)
        task_status = task.status
    else:
        task_status = "waiting"
    return task_status, task_status


@app.callback(
    [Output("yf-data", "children"), Output("sector-status", "children")],
    [Input("task-status", "children")],
    [State("task-id", "children")],
)
def get_results(task_status, task_id):
    """Provide status results."""
    if task_status == "SUCCESS":
        task = AsyncResult(task_id, app=cq.celery_app)
        cq_sector_close = task.result
        sector_status = "ready"
    else:
        sector_status = "none"
        cq_sector_close = None
    return cq_sector_close, sector_status


@app.callback(
    [
        Output("slider", "min"),
        Output("slider", "max"),
        Output("slider", "value"),
        Output("slider", "marks"),
    ],
    [Input("sector-status", "children")],
    [State("yf-data", "children")],
)
def update_SectorData(sector_status, yf_data):
    """Provide sector data table."""
    if sector_status == "ready":
        cq_sector_close = pd.read_json(StringIO(yf_data))
        min, max, value, marks = dashboard_helper.get_slider_values(
            cq_sector_close.index
        )
    else:
        min = 0
        max = 100
        value = [0, 100]
        marks = {i: str(i) for i in range(0, 101, 10)}

    return min, max, value, marks


@app.callback(
    Output("Sector-Graph", "figure"),
    [Input("slider", "value")],
    [State("yf-data", "children"), State("sector-status", "children")],
)
def update_SectorGraph(slide_value, yf_data, sector_status):
    """Provide sector graph."""
    res = []
    layout = go.Layout(hovermode="closest")

    if sector_status == "ready" and slide_value != 0:
        cq_sector_close = pd.read_json(StringIO(yf_data))
        sector_data = cq_sector_close[
            (dashboard_helper.unix_time_millis(cq_sector_close.index) > slide_value[0])
            & (
                dashboard_helper.unix_time_millis(cq_sector_close.index)
                <= slide_value[1]
            )
        ].copy()
        for col in sector_data.columns:
            sector_data["change"] = sector_data[col] / sector_data[col].iat[0] - 1
            sector_data = sector_data.drop([col], axis=1)
            sector_data["change"] = sector_data["change"].map("{0:.1%}".format)
            sector_data = sector_data.rename(columns={"change": col})
            res.append(
                go.Scatter(
                    x=sector_data.index, y=sector_data[col].values.tolist(), name=col
                )
            )
    else:
        "could not load"

    fig = {"data": res, "layout": layout}

    return fig


# Heatmap Graph
@app.callback(
    Output("Heatmap-Graph", "figure"),
    [Input(component_id="heatmap-initialize", component_property="n_clicks")],
)
def initialize_HeatmapGraph(n_clicks):
    """Provide heatmap graph."""
    if n_clicks == 0:
        fig = {"data": [], "layout": go.Layout(hovermode="closest")}
    else:
        fig = heatmap.get_heatmap()

    return fig


#   ___ ____  _____    _    ____
#  |_ _|  _ \| ____|  / \  / ___|
#   | || | | |  _|   / _ \ \___ \
#   | || |_| | |___ / ___ \ ___) |
#  |___|____/|_____/_/   \_\____/


@app.callback(
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


#   __  __    _    ____ ____   ___
#  |  \/  |  / \  / ___|  _ \ / _ \
#  | |\/| | / _ \| |   | |_) | | | |
#  | |  | |/ ___ \ |___|  _ <| |_| |
#  |_|  |_/_/   \_\____|_| \_\\___/


#   ____  _____ ____  ____   ___  _   _    _    _
#  |  _ \| ____|  _ \/ ___| / _ \| \ | |  / \  | |
#  | |_) |  _| | |_) \___ \| | | |  \| | / _ \ | |
#  |  __/| |___|  _ < ___) | |_| | |\  |/ ___ \| |___
#  |_|   |_____|_| \_\____/ \___/|_| \_/_/   \_\_____|


# initializing workers
@app.callback(
    Output("personal-task-id", "children"),
    Input("personal-initialize", "n_clicks"),
    [
        State("personal-dropdown", "value"),
        State("lookback-input", "value"),
    ],
)
def initialize_PersonalGraph(n_clicks, dropdown, lookback):
    """Provide personal graph."""
    if n_clicks == 0:
        personal_task_id = "none"
    else:
        config_file = "portfolio_personal.ini"

        personal_task = cq.portfolio_query.delay(
            config_file=config_file, broker=dropdown, lookback=lookback
        )
        personal_task_id = personal_task.id

    return personal_task_id


# text
@app.callback(
    Output("personal_refresh_text", "children"),
    Input("personal-task-status", "children"),
)
def personal_refresh_text(personal_task_status):
    """Provide text for personal graph."""
    return personal_task_status


@app.callback(
    Output("personal-task-status", "children"),
    [
        Input("interval-component", "n_intervals"),
        Input("personal-task-id", "children"),
    ],
    [
        State("personal-task-status", "children"),
    ],
)
def personal_status_check(n_intervals, personal_task_id, personal_task_status):
    """Provide status check."""
    if personal_task_id != "none":
        personal_task = AsyncResult(personal_task_id, app=cq.celery_app)
        personal_task_status = personal_task.status

    else:
        personal_task_status = "waiting"
    return personal_task_status


@app.callback(
    [
        Output("personal-portfolio-tx", "data"),
        Output("personal-status", "children"),
    ],
    Input("personal-task-status", "children"),
    State("personal-task-id", "children"),
)
def personal_get_results(personal_task_status, personal_task_id):
    """Provide status results."""
    if personal_task_status == "SUCCESS":
        personal_task = AsyncResult(personal_task_id, app=cq.celery_app)
        personal_portfolio_tx = personal_task.result
        personal_status = "ready"
    else:
        personal_status = "none"
        personal_portfolio_tx = None

    return personal_portfolio_tx, personal_status


# graph
@app.callback(
    Output("personal_graph", "figure"),
    [
        Input("personal_slider", "value"),
    ],
    [
        State("personal-status", "children"),
        State("personal-portfolio-tx", "data"),
    ],
)
def update_PersonalGraph(slide_value, personal_status, cq_portfolio_dict):
    """Provide personal graph."""
    if personal_status == "ready":
        fig = dashboard_helper.update_graph(
            slide_value,
            pd.read_json(cq_portfolio_dict["view_return"]),
            pd.read_json(cq_portfolio_dict["view_cost"]),
        )
    else:
        "could not load"
        fig = {"data": [], "layout": go.Layout(hovermode="closest")}

    return fig


@app.callback(
    [
        Output("personal_slider", "min"),
        Output("personal_slider", "max"),
        Output("personal_slider", "value"),
        Output("personal_slider", "marks"),
    ],
    [Input("personal-status", "children")],
    [State("personal-portfolio-tx", "data")],
)
def update_PersonalSlider(personal_status, cq_portfolio_dict):
    """Provide sector data table."""
    if personal_status == "ready":
        return_view = pd.read_json(cq_portfolio_dict["view_return"])
        min, max, value, marks = dashboard_helper.get_slider_values(return_view.index)
    else:
        min = 0
        max = 100
        value = [0, 100]
        marks = {i: str(i) for i in range(0, 101, 10)}

    return min, max, value, marks


# performance table
@app.callback(
    [
        Output("personal_perfomance_table", "columns"),
        Output("personal_perfomance_table", "data"),
    ],
    [
        Input("personal-status", "children"),
    ],
    [
        State("personal-portfolio-tx", "data"),
    ],
)
def update_PersonalPerformance(personal_status, cq_portfolio_dict):
    """Provide personal performance table."""
    if personal_status == "ready":
        performance = pd.read_json(cq_portfolio_dict["performance"])
        performance["lookback_date"] = pd.to_datetime(
            performance["lookback_date"], unit="ms"
        )
        performance = performance[performance["market_value"] != 0].sort_values(
            "return", ascending=False
        )

        performance_table = layouts.performance_fmt, performance.to_dict("records")
    else:
        performance_table = (None, None)

    return performance_table


# transactions table
@app.callback(
    [
        Output("personal_transaction_table", "columns"),
        Output("personal_transaction_table", "data"),
    ],
    [
        Input("personal-status", "children"),
    ],
    [
        State("personal-portfolio-tx", "data"),
    ],
)
def update_PersonalTransaction(personal_status, cq_portfolio_dict):
    """Provide personal transaction table."""
    if personal_status == "ready":
        transactions = pd.read_json(cq_portfolio_dict["transactions"])
        transaction_table = layouts.transactions_fmt, transactions.to_dict("records")
    else:
        transaction_table = (None, None)

    return transaction_table


# ------------------------------------------------------------------
# Portfolio Manager
# initializing workers
@app.callback(
    Output("manager-task-id", "children"),
    Input("manager-initialize", "n_clicks"),
    State("lookback-input", "value"),
)
def initialize_ManagerTable(n_clicks, lookback):
    """Provide sector analysis graph."""
    if n_clicks == 0:
        manager_task_id = "none"
    else:
        config_file = "portfolio_personal.ini"
        task = cq.manager_query.delay(config_file, lookback)
        manager_task_id = task.id
        print(f"initializing manager table - {manager_task_id}")
    return manager_task_id


# text
@app.callback(
    Output("manager_refresh_text", "children"),
    Input("manager-task-status", "children"),
)
def manager_refresh_text(manager_task_status):
    """Provide text for manager table."""
    return manager_task_status


@app.callback(
    Output("manager-task-status", "children"),
    [
        Input("interval-component", "n_intervals"),
        Input("manager-task-id", "children"),
    ],
    [
        State("manager-task-status", "children"),
    ],
)
def manager_status_check(n_intervals, manager_task_id, manager_task_status):
    """Provide status check."""
    if manager_task_id != "none":
        task = AsyncResult(manager_task_id, app=cq.celery_app)
        manager_task_status = task.status

    else:
        manager_task_status = "waiting"
    return manager_task_status


@app.callback(
    [Output("manager-status", "children"), Output("manager-df", "children")],
    Input("manager-task-status", "children"),
    State("manager-task-id", "children"),
)
def manager_get_results(manager_task_status, manager_task_id):
    """Provide status results."""
    if manager_task_status == "SUCCESS":
        task = AsyncResult(manager_task_id, app=cq.celery_app)
        cq_pm = task.result
        manager_status = "ready"
    else:
        cq_pm = None
        manager_status = "none"

    return manager_status, cq_pm


# manager table
@app.callback(
    [
        Output("manager_table", "columns"),
        Output("manager_table", "data"),
    ],
    [
        Input("manager-status", "children"),
    ],
    [
        State("manager-df", "children"),
    ],
)
def update_ManagerTable(manager_status, cq_pm):
    """Provide personal performance table."""
    if manager_status == "ready":
        cq_pm = pd.read_json(cq_pm).reset_index()
        cq_pm["lookback_date"] = pd.to_datetime(cq_pm["lookback_date"], unit="ms")
        # formatting floats
        # TODO: put this in dashboard_helper function
        manager_table = (
            [
                {
                    "name": i,
                    "id": i,
                    **(
                        {
                            "type": "numeric",
                            "format": Format(precision=2, scheme=Scheme.fixed).group(
                                True
                            ),
                        }
                        if cq_pm[i].dtype == "float64"
                        else {}
                    ),
                }
                for i in cq_pm.columns
            ],
            cq_pm.to_dict("records"),
        )
    else:
        manager_table = (None, None)

    return manager_table


#   ____  _   _ ____   ____ _____ _____
#  | __ )| | | |  _ \ / ___| ____|_   _|
#  |  _ \| | | | | | | |  _|  _|   | |
#  | |_) | |_| | |_| | |_| | |___  | |
#  |____/ \___/|____/ \____|_____| |_|
#


# budget expense chart
@app.callback(
    [
        Output("budget-chart", "figure"),
        Output("budget-chart-labels", "children"),
    ],
    [Input("budget-chart-button", "n_clicks")],
    [State("budget-chart-input", "value")],
)
def update_budgetchart(n_clicks, input_value):
    """Provide budget info chart."""
    if n_clicks == 0:
        budget_chart = go.Figure()
        budget_chart.add_annotation(
            text="No data available", x=0.5, y=0.5, showarrow=False, font_size=20
        )
        budget_chart.update_layout(xaxis={"visible": False}, yaxis={"visible": False})
        len_label = 0
        len_unlabel = 0
    else:
        bdgt = budget.Budget(config_path="budget_personal.ini", budget="personal")
        budget_df = bdgt.get_transactions()
        budget_df = bdgt.modify_transactions(budget_df)
        budget_view = bdgt.budget_view(
            budget_df, target_date=input_value, exclude_labels=["income"]
        )
        budget_chart = bdgt.display_budget_view(budget_view)
        len_label = len(budget_df[~budget_df["label"].isnull()])
        len_unlabel = len(budget_df[budget_df["label"].isnull()])

    return budget_chart, f"Labeled: {len_label} | Unlabeled: {len_unlabel}"


# income chart
@app.callback(
    Output("income-chart", "figure"),
    [Input("income-chart-button", "n_clicks")],
    [State("budget-chart-input", "value")],
)
def update_incomeview(n_clicks, input_value):
    """Provide income info chart."""
    if n_clicks == 0:
        income_chart = go.Figure()
        income_chart.add_annotation(
            text="No data available", x=0.5, y=0.5, showarrow=False, font_size=20
        )
        income_chart.update_layout(xaxis={"visible": False}, yaxis={"visible": False})
    else:
        bdgt = budget.Budget(config_path="budget_personal.ini", budget="personal")
        budget_df = bdgt.get_transactions()
        budget_df = bdgt.modify_transactions(budget_df)
        income_chart = bdgt.display_income_view(budget_df)

    return income_chart


# budget compare chart
@app.callback(
    Output("compare-chart", "figure"),
    [Input("budget-compare-button", "n_clicks")],
    [State("budget-chart-input", "value")],
)
def update_comparechart(n_clicks, input_value):
    """Provide budget compare info chart."""
    if n_clicks == 0:
        compare_chart = go.Figure()
        compare_chart.add_annotation(
            text="No data available", x=0.5, y=0.5, showarrow=False, font_size=20
        )
        compare_chart.update_layout(xaxis={"visible": False}, yaxis={"visible": False})
    else:
        bdgt = budget.Budget(config_path="budget_personal.ini", budget="personal")
        budget_df = bdgt.get_transactions()
        budget_df = bdgt.modify_transactions(budget_df)
        compare_chart = bdgt.display_compare_expenses_view(
            budget_df, target_date=input_value, avg_months=3
        )

    return compare_chart


#   _                 _
#  | |               (_)
#  | |     ___   __ _ _ _ __
#  | |    / _ \ / _` | | '_ \
#  | |___| (_) | (_| | | | | |
#  |______\___/ \__, |_|_| |_|
#                __/ |
#               |___/


# User credentials
# dictionary of username and password
# e.g. {"username": "password"}
credentials = {config_helper.FFX_USERNAME: config_helper.FFX_PASSWORD}


@app.callback(
    [
        Output("login-status", "data"),
        Output("login-alert", "children"),
    ],
    Input("login-button", "n_clicks"),
    [State("username", "value"), State("password", "value")],
    prevent_initial_call=True,
)
def validate_login(n_clicks, username, password):
    """Validate login credentials."""
    if not n_clicks:
        # Return empty values if the button has not been clicked yet
        return (
            dash.no_update,
            dash.no_update,
        )
    elif (
        username is not None
        and password is not None
        and (username, password) in credentials.items()
    ):
        return (
            {"logged_in": True},
            "Success (switch pages to see the change)",
        )
    else:
        return (
            {"logged_in": False},
            "Invalid Credentials",
        )


#  __        _____  ____  _  _______ ____
#  \ \      / / _ \|  _ \| |/ / ____|  _ \
#   \ \ /\ / / | | | |_) | ' /|  _| | |_) |
#    \ V  V /| |_| |  _ <| . \| |___|  _ <
#     \_/\_/  \___/|_| \_\_|\_\_____|_| \_\


@app.callback(
    Output("interval-component", "interval"),
    [
        Input("task-status", "children"),
        Input("task-id", "children"),
        Input("personal-task-status", "children"),
        Input("personal-task-id", "children"),
        Input("manager-task-status", "children"),
        Input("manager-task-id", "children"),
    ],
)
def toggle_interval_speed(
    task_status,
    task_id,
    personal_task_status,
    personal_task_id,
    manager_task_status,
    manager_task_id,
):
    """
    Triggered by changes in task-id and task-status divs.

    It switches the page refresh interval to fast (1 sec) if a task is running,
    or slow (24 hours) if a task is pending or complete.
    """
    if (
        (task_id != "none" and task_status in ["waiting", "PENDING"])
        or (
            personal_task_id != "none"
            and personal_task_status in ["waiting", "PENDING"]
        )
        or (manager_task_id != "none" and manager_task_status in ["waiting", "PENDING"])
    ):
        return 1000
    else:
        return 24 * 60 * 60 * 1000


if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0")
