"""
Building plotly dashboard.

Builds plotly pages with call backs. There are 2 options the user has for running code.
1. Heroku build set up
2. Local running

To run locally:
1. cd into root directory
2. run plotly dashboard - `python app.py`

The ascii text is generated using https://patorjk.com/software/taag/ with "standard font"
"""

import dash
import datetime
import math
import pandas as pd
import pandas_market_calendars as mcal
import plotly.express as px
import plotly.graph_objs as go

from celery.result import AsyncResult
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
from dateutil.relativedelta import relativedelta

from iex.pages import stocks, sectors, ideas, macro, tracker, crypto, personal
from iex.util import constants, cq, layouts, page_constants, utils
from iex.portfolio import heatmap


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

app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        html.Div(id="page-content"),
        html.Div(id="task-status", children="none", style={"display": "none"}),
        html.Div(id="refresh_text", children="none", style={"display": "none"}),
        html.Div(id="task-id", children="none", style={"display": "none"}),
        html.Div(id="sector-status", children="none", style={"display": "none"}),
        html.Div(id="yf-data", children="none", style={"display": "none"}),
        html.Div(id="personal-task-status", children="none", style={"display": "none"}),
        html.Div(id="personal-task-id", children="none", style={"display": "none"}),
        html.Div(id="personal-status", children="none", style={"display": "none"}),
        html.Div(id="manager-df", children="none", style={"display": "none"}),
        html.Div(id="manager-task-status", children="none", style={"display": "none"}),
        html.Div(id="manager-task-id", children="none", style={"display": "none"}),
        html.Div(id="manager-status", children="none", style={"display": "none"}),
        html.Div(
            id="personal-portfolio-tx", children="none", style={"display": "none"}
        ),
        dcc.Interval(
            id="interval-component", interval=24 * 60 * 60 * 1000, n_intervals=0
        ),
    ]
)

#   ___ _   _ ____  _______  __
#  |_ _| \ | |  _ \| ____\ \/ /
#   | ||  \| | | | |  _|  \  /
#   | || |\  | |_| | |___ /  \
#  |___|_| \_|____/|_____/_/\_\


@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def display_page(pathname):
    """Create navigation for app."""
    if pathname == "/":
        return stocks.layout
    elif pathname == "/stocks":
        return stocks.layout
    elif pathname == "/sectors":
        return sectors.layout
    elif pathname == "/ideas":
        return ideas.layout
    elif pathname == "/macro":
        return macro.layout
    elif pathname == "/tracker":
        return tracker.layout
    elif pathname == "/crypto":
        return crypto.layout
    elif pathname == "/personal":
        return personal.layout
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
    """Provide stock analysis table."""
    if n_clicks == 0:
        stock_table = (None, None)
    else:
        urlstock = (
            "https://cloud.iexapis.com/stable/stock/"
            + format(input_value)
            + "/stats?token="
            + constants.iex_api_live
        )

        stock = pd.read_json(urlstock, orient="index", typ="frame")
        stock = stock.reset_index()
        stock.columns = ["Variable", "Value"]
        stock = stock.round(2)

        stock_table = [{"name": i, "id": i} for i in stock.columns], stock.to_dict(
            "records"
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
        urlquote = (
            "https://cloud.iexapis.com/stable/stock/"
            + format(input_value)
            + "/quote?token="
            + constants.iex_api_live
        )
        quote = pd.read_json(urlquote, orient="index", typ="frame")

        quote.loc["closeTime"].values[0] = pd.to_datetime(
            quote.loc["closeTime"].values[0], unit="ms"
        )
        quote.loc["iexLastUpdated"].values[0] = pd.to_datetime(
            quote.loc["iexLastUpdated"].values[0], unit="ms"
        )
        quote.loc["lastTradeTime"].values[0] = pd.to_datetime(
            quote.loc["lastTradeTime"].values[0], unit="ms"
        )
        quote.loc["latestUpdate"].values[0] = pd.to_datetime(
            quote.loc["latestUpdate"].values[0], unit="ms"
        )
        quote.loc["extendedPriceTime"].values[0] = pd.to_datetime(
            quote.loc["extendedPriceTime"].values[0], unit="ms"
        )

        quote = quote.loc[layouts.quote_col]
        quote = quote.reset_index()
        quote.columns = ["Variable", "Value"]
        quote = quote.round(2)

        quote_table = [{"name": i, "id": i} for i in quote.columns], quote.to_dict(
            "records"
        )

    return quote_table


@app.callback(
    [
        Output("peer-table", "columns"),
        Output("peer-table", "data"),
    ],
    [Input("peer-button", "n_clicks")],
    [State("stock-input", "value")],
)
def update_peeranalysis(n_clicks, input_value):
    """Provide peer analysis table."""
    if n_clicks == 0:
        peer_table = (None, None)
    else:
        urlpeer = (
            "https://cloud.iexapis.com/stable/stock/"
            + format(input_value)
            + "/peers?token="
            + constants.iex_api_live
        )
        peer = pd.read_json(urlpeer, orient="columns", typ="series")
        peer = peer.reset_index()
        peer.columns = ["Index", "Peer"]
        peer_table = [{"name": i, "id": i} for i in peer.columns], peer.to_dict(
            "records"
        )

    return peer_table


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
        urlnews = (
            "https://cloud.iexapis.com/stable/stock/"
            + format(input_value)
            + "/news/last/5?token="
            + constants.iex_api_live
        )
        news = pd.read_json(urlnews, orient="columns")

        news_table = [{"name": i, "id": i} for i in news.columns], news.to_dict(
            "records"
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
        urlactive = (
            "https://cloud.iexapis.com/stable/stock/market/list/mostactive?listLimit=60&token="
            + constants.iex_api_live
        )
        active = pd.read_json(urlactive, orient="columns")
        active["vol_delta"] = active["volume"] / active["avgTotalVolume"]
        active["vol_price"] = active["volume"] * active["latestPrice"]
        active = active.sort_values("vol_price", ascending=False)
        active = active.head(20)
        active = active[layouts.active_col]
        active = active.round(2)

        active["changePercent"] = active["changePercent"].astype(float)
        active["ytdChange"] = active["ytdChange"].astype(float)

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
        url_insider_summary = (
            "https://cloud.iexapis.com/stable/stock/"
            + format(input_value)
            + "/insider-roster?token="
            + constants.iex_api_live
        )
        insider = pd.read_json(url_insider_summary, orient="columns")

        insider_summary_table = [
            {"name": i, "id": i} for i in insider.columns
        ], insider.to_dict("records")

    return insider_summary_table


@app.callback(
    [
        Output("insider-tx-table", "columns"),
        Output("insider-tx-table", "data"),
    ],
    [Input("insider-tx-button", "n_clicks")],
    [State("stock-input", "value")],
)
def update_insidertransactionsanalysis(n_clicks, input_value):
    """Provide insider transactions table."""
    if n_clicks == 0:
        insider_transactions_table = (None, None)
    else:
        url_insider_transactions = (
            "https://cloud.iexapis.com/stable/stock/"
            + format(input_value)
            + "/insider-transactions?token="
            + constants.iex_api_live
        )
        insider = pd.read_json(url_insider_transactions, orient="columns")

        insider_transactions_table = [
            {"name": i, "id": i} for i in insider.columns
        ], insider.to_dict("records")

    return insider_transactions_table


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
        sector_close = task.result
        sector_status = "ready"
        sector_close = sector_close.to_json()
    else:
        sector_status = "none"
        sector_close = None
    return sector_close, sector_status


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
        sector_close = pd.read_json(yf_data)
        min, max, value, marks = utils.get_slider_values(sector_close.index)
    else:
        min = 0
        max = 10
        value = 0
        marks = 0

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
        sector_close = pd.read_json(yf_data)
        sector_data = sector_close[
            (utils.unix_time_millis(sector_close.index) > slide_value[0])
            & (utils.unix_time_millis(sector_close.index) <= slide_value[1])
        ].copy()
        for col in sector_data.columns:
            sector_data["change"] = sector_data[col] / sector_data[col].iat[0] - 1
            sector_data.drop([col], axis=1, inplace=True)
            sector_data["change"] = sector_data["change"].map("{0:.1%}".format)
            sector_data = sector_data.rename(columns={"change": col})
            res.append(
                go.Scatter(
                    x=sector_data.index, y=sector_data[col].values.tolist(), name=col
                )
            )
    else:
        "could not load"

    fig = dict(data=res, layout=layout)

    return fig


# Heatmap Graph
@app.callback(
    Output("Heatmap-Graph", "figure"),
    [Input(component_id="heatmap-initialize", component_property="n_clicks")],
)
def initialize_HeatmapGraph(n_clicks):
    """Provide heatmap graph."""
    if n_clicks == 0:
        fig = dict(data=[], layout=go.Layout(hovermode="closest"))
    else:
        fig = heatmap.get_heatmap()

    return fig


# Table
@app.callback(
    [
        Output("sector-table", "columns"),
        Output("sector-table", "data"),
    ],
    [Input("sector-dropdown", "value")],
)
def update_table(dropdown_value):
    """Provide sector analysis table."""
    if dropdown_value is None:
        sector_table = (None, None)
    else:
        urlcol = (
            "https://cloud.iexapis.com/stable/stock/market/collection/sector?collectionName="
            + format(dropdown_value)
            + "&token="
            + constants.iex_api_live
        )
        collection_all = pd.read_json(urlcol, orient="columns")
        collection = collection_all[
            collection_all["primaryExchange"].isin(layouts.USexchanges)
        ].copy()

        collection["cap*perc"] = collection["marketCap"] * collection["changePercent"]
        collection["latestUpdate"] = pd.to_datetime(
            collection["latestUpdate"], unit="ms"
        )
        collection = collection[layouts.cols_col]
        collection = collection.sort_values(by=["cap*perc"], ascending=False)

        sector_table = [
            {"name": i, "id": i} for i in collection.columns
        ], collection.to_dict("records")

    return sector_table


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
        nyse = mcal.get_calendar("NYSE")
        days = math.floor(
            len(
                nyse.valid_days(
                    start_date=(datetime.datetime.now() - relativedelta(years=1)),
                    end_date=datetime.datetime.now(),
                )
            )
            / 12
        )
        days = str(days)
        urlsma = (
            "https://cloud.iexapis.com/stable/stock/"
            + format(input_value)
            + "/indicator/sma?range=1y&input1=12&sort=asc&chartCloseOnly=True&chartInterval="
            + days
            + "&token="
            + constants.iex_api_live
        )
        sma = pd.read_json(urlsma, orient="index", typ="frame")
        sma_val = sma.loc["indicator"].values[0][-1]
        urlquote = (
            "https://cloud.iexapis.com/stable/stock/"
            + format(input_value)
            + "/quote?token="
            + constants.iex_api_live
        )
        quote = pd.read_json(urlquote, orient="index", typ="frame")
        latest_price = quote.loc["latestPrice"].values[0]
        urlstock = (
            "https://cloud.iexapis.com/stable/stock/"
            + format(input_value)
            + "/stats?token="
            + constants.iex_api_live
        )
        stock = pd.read_json(urlstock, orient="index", typ="frame")
        return_12mo = stock.loc["year1ChangePercent"].values[0]

        # build table
        stock_data = [[input_value, sma_val, latest_price, return_12mo]]
        df = pd.DataFrame(
            stock_data, columns=["Stock", "12mo SMA", "Latest Price", "12mo Return"]
        )

        sma_table = [{"name": i, "id": i} for i in df.columns], df.to_dict("records")

    return sma_table


#   __  __    _    ____ ____   ___
#  |  \/  |  / \  / ___|  _ \ / _ \
#  | |\/| | / _ \| |   | |_) | | | |
#  | |  | |/ ___ \ |___|  _ <| |_| |
#  |_|  |_/_/   \_\____|_| \_\\___/


#   _____ ____      _    ____ _  _______ ____
#  |_   _|  _ \    / \  / ___| |/ / ____|  _ \
#    | | | |_) |  / _ \| |   | ' /|  _| | |_) |
#    | | |  _ <  / ___ \ |___| . \| |___|  _ <
#    |_| |_| \_\/_/   \_\____|_|\_\_____|_| \_\

tracker_portfolio = page_constants.tracker_portfolio


@app.callback(Output("Tracker-Graph", "figure"), [Input("Tracker-Dropdown", "value")])
def update_TrackerGraph(dropdown):
    """Provide tracker graph."""
    px_df = tracker_portfolio.get_view(view=dropdown)
    px_line = px.line(px_df, title="tracker")
    px_line.update_xaxes(
        title_text="Date",
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list(
                [
                    dict(count=5, label="5D", step="day", stepmode="backward"),
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(step="all"),
                ]
            )
        ),
    )

    px_line.update_yaxes(title_text=dropdown, autorange=True, fixedrange=False)
    px_line.update_traces(
        visible="legendonly", selector=lambda t: t.name not in ["portfolio"]
    )

    return px_line


#    ____ ______   ______ _____ ___
#   / ___|  _ \ \ / /  _ \_   _/ _ \
#  | |   | |_) \ V /| |_) || || | | |
#  | |___|  _ < | | |  __/ | || |_| |
#   \____|_| \_\|_| |_|    |_| \___/


@app.callback(
    [
        Output(component_id="crypto-quote-table", component_property="columns"),
        Output(component_id="crypto-quote-table", component_property="data"),
    ],
    [Input(component_id="crypto-quote-button", component_property="n_clicks")],
    [State(component_id="crypto-input", component_property="value")],
)
def update_cryptoquoteanalysis(n_clicks, input_value):
    """Provide crypto analysis table."""
    if n_clicks == 0:
        crypto_table = (None, None)
    else:
        urlquote = (
            "https://cloud.iexapis.com/stable/crypto/"
            + format(input_value)
            + "/quote?token="
            + constants.iex_api_live
        )
        quote = pd.read_json(urlquote, orient="index", typ="frame")

        quote.loc["latestUpdate"].values[0] = pd.to_datetime(
            quote.loc["latestUpdate"].values[0], unit="ms"
        )

        quote = quote.loc[layouts.crypto_quote_col]
        quote = quote.reset_index()
        quote.columns = ["Variable", "Value"]
        quote = quote.round(2)

        crypto_table = [{"name": i, "id": i} for i in quote.columns], quote.to_dict(
            "records"
        )

    return crypto_table


#   ____  _____ ____  ____   ___  _   _    _    _
#  |  _ \| ____|  _ \/ ___| / _ \| \ | |  / \  | |
#  | |_) |  _| | |_) \___ \| | | |  \| | / _ \ | |
#  |  __/| |___|  _ < ___) | |_| | |\  |/ ___ \| |___
#  |_|   |_____|_| \_\____/ \___/|_| \_/_/   \_\_____|


# initializing workers
@app.callback(
    Output("personal-task-id", "children"),
    Input("personal-initialize", "n_clicks"),
    State("personal-dropdown", "value"),
)
def initialize_PersonalGraph(n_clicks, dropdown):
    """Provide sector analysis graph."""
    if n_clicks == 0:
        personal_task_id = "none"
    else:
        if dropdown == "Total":
            broker = None
        else:
            broker = [dropdown]

        personal_tx_file = constants.aws_tx_file
        personal_task = cq.portfolio_query.delay(personal_tx_file, filter_broker=broker)
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
        Output("personal-portfolio-tx", "children"),
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
        personal_portfolio_tx = personal_portfolio_tx.to_json()
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
        State("personal-portfolio-tx", "children"),
    ],
)
def update_PersonalGraph(slide_value, personal_status, personal_portfolio_tx):
    """Provide personal graph."""
    if personal_status == "ready":
        tx_hist_df = pd.read_json(personal_portfolio_tx)
        fig = utils.update_graph(slide_value, tracker_portfolio, tx_hist_df)
    else:
        "could not load"
        fig = dict(data=[], layout=go.Layout(hovermode="closest"))

    return fig


@app.callback(
    [
        Output("personal_slider", "min"),
        Output("personal_slider", "max"),
        Output("personal_slider", "value"),
        Output("personal_slider", "marks"),
    ],
    [Input("personal-status", "children")],
    [State("personal-portfolio-tx", "children")],
)
def update_PersonalSlider(personal_status, personal_portfolio_tx):
    """Provide sector data table."""
    if personal_status == "ready":
        tx_hist_df = pd.read_json(personal_portfolio_tx)
        return_view = tracker_portfolio.get_view(view="return", tx_hist_df=tx_hist_df)
        min, max, value, marks = utils.get_slider_values(return_view.index)
    else:
        min = 0
        max = 10
        value = 0
        marks = 0

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
        State("personal-portfolio-tx", "children"),
    ],
)
def update_PersonalPerformance(personal_status, personal_portfolio_tx):
    """Provide personal performance table."""
    if personal_status == "ready":
        tx_hist_df = pd.read_json(personal_portfolio_tx)
        performance = tracker_portfolio.get_performance(
            date=tx_hist_df["date"].max(), tx_hist_df=tx_hist_df
        ).reset_index()
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
        State("personal-portfolio-tx", "children"),
    ],
)
def update_PersonalTransaction(personal_status, personal_portfolio_tx):
    """Provide personal transaction table."""
    if personal_status == "ready":
        tx_hist_df = pd.read_json(personal_portfolio_tx)
        tx_hist_df = tx_hist_df[tx_hist_df["units"] != 0]
        tx_hist_df = tx_hist_df[tx_hist_df["ticker"] != "Cash"].sort_values(
            "date", ascending=False
        )

        transaction_table = layouts.transactions_fmt, tx_hist_df.to_dict("records")
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
        personal_tx_file = constants.aws_tx_file
        task = cq.manager_query.delay(personal_tx_file, lookback)
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
        manager_df = task.result
        manager_df = manager_df.to_json()
        manager_status = "ready"
    else:
        manager_status = "none"
        manager_df = None

    return manager_status, manager_df


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
def update_ManagerTable(manager_status, manager_df):
    """Provide personal performance table."""
    if manager_status == "ready":
        manager_df = pd.read_json(manager_df).reset_index()
        manager_table = layouts.manager_fmt, manager_df.to_dict("records")
    else:
        manager_table = (None, None)

    return manager_table


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
    """Triggered by changes in task-id and task-status divs.

    It switches the page refresh interval to fast (1 sec) if a task is running, or slow (24 hours) if a task is
    pending or complete.
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
