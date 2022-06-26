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
import plotly.graph_objs as go

from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
from dateutil.relativedelta import relativedelta
from rq import Queue
from rq.job import Job

from iex.pages import stocks, sectors, ideas, macro, tracker, crypto, personal
from iex.util import constants, layouts, utils, worker

q = Queue(connection=worker.conn)

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
        html.Div(id="task-id", children="none", style={"display": "none"}),
        html.Div(id="sector-status", children="none", style={"display": "none"}),
        html.Div(id="av-data", children="none", style={"display": "none"}),
        html.Div(id="personal-task-status", children="none", style={"display": "none"}),
        html.Div(id="personal-task-id", children="none", style={"display": "none"}),
        html.Div(id="personal-status", children="none", style={"display": "none"}),
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
            "https://cloud.iexapis.com/stable/stock/market/list/mostactive?listLimit=20&token="
            + constants.iex_api_live
        )
        active = pd.read_json(urlactive, orient="columns")
        active["vol_delta"] = active["volume"] / active["avgTotalVolume"]
        active = active[layouts.active_col]
        active = active.round(2)
        active["changePercent"] = (
            active["changePercent"].astype(float).map("{:.1%}".format)
        )
        active["ytdChange"] = active["ytdChange"].astype(float).map("{:.1%}".format)

        active_table = [{"name": i, "id": i} for i in active.columns], active.to_dict(
            "records"
        )

    return active_table


#   ____  _____ ____ _____ ___  ____
#  / ___|| ____/ ___|_   _/ _ \|  _ \
#  \___ \|  _|| |     | || | | | |_) |
#   ___) | |__| |___  | || |_| |  _ <
#  |____/|_____\____| |_| \___/|_| \_\

# Graph
@app.callback(
    Output("task-id", "children"),
    [Input(component_id="sector-initialize", component_property="n_clicks")],
)
def initialize_SectorGraph(n_clicks):
    """Provide sector analysis graph."""
    if n_clicks == 0:
        task_id = "none"
    else:
        task_id = q.enqueue(worker.sector_query).id

    return task_id


@app.callback(
    [Output("task-status", "children"), Output("refresh_text", "children")],
    [Input("interval-component", "n_intervals")],
    [State("task-id", "children"), State("task-status", "children")],
)
def status_check(n_intervals, task_id, task_status):
    """Provide status check."""
    if task_id != "none":
        try:
            job = Job.fetch(task_id, connection=worker.conn)
            task_status = job.get_status()
        except:
            task_status = "waiting"
    else:
        task_status = "waiting"
    return task_status, task_status


@app.callback(
    [Output("av-data", "children"), Output("sector-status", "children")],
    [Input("task-status", "children")],
    [State("task-id", "children")],
)
def get_results(task_status, task_id):
    """Provide status results."""
    if task_status == "finished":
        job = Job.fetch(task_id, connection=worker.conn)
        sector_close = job.result
        job.delete()
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
    [State("av-data", "children")],
)
def update_SectorData(sector_status, av_data):
    """Provide sector data table."""
    if sector_status == "ready":
        sector_close = pd.read_json(av_data)
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
    [State("av-data", "children"), State("sector-status", "children")],
)
def update_SectorGraph(slide_value, av_data, sector_status):
    """Provide sector graph."""
    res = []
    layout = go.Layout(hovermode="closest")

    if sector_status == "ready" and slide_value != 0:
        sector_close = pd.read_json(av_data)
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

tracker_portfolio = constants.tracker_portfolio
tracker_portfolio_tx = constants.tracker_portfolio.transactions_history


@app.callback(Output("Tracker-Graph", "figure"), [Input("track_slider", "value")])
def update_TrackerGraph(slide_value):
    """Provide tracker graph."""
    fig = utils.update_graph(slide_value, tracker_portfolio, tracker_portfolio_tx)

    return fig


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
        personal_task_id = q.enqueue(
            worker.portfolio_query, personal_tx_file, filter_broker=broker
        ).id

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
    Input("interval-component", "n_intervals"),
    [
        State("personal-task-id", "children"),
        State("personal-task-status", "children"),
    ],
)
def personal_status_check(n_intervals, personal_task_id, personal_task_status):
    """Provide status check."""
    if personal_task_id != "none":
        try:
            job = Job.fetch(personal_task_id, connection=worker.conn)
            personal_task_status = job.get_status()
        except:
            personal_task_status = "waiting"

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
    if personal_task_status == "finished":
        job = Job.fetch(personal_task_id, connection=worker.conn)
        personal_portfolio_tx = job.result
        job.delete()
        personal_portfolio_tx = personal_portfolio_tx.to_json()
        personal_status = "ready"
        personal_task_id = "none"
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
        tx_df = pd.read_json(personal_portfolio_tx)
        fig = utils.update_graph(slide_value, tracker_portfolio, tx_df)
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
        tx_df = pd.read_json(personal_portfolio_tx)
        portfolio_view = tracker_portfolio._get_portfolio_view(tx_df=tx_df)
        min, max, value, marks = utils.get_slider_values(portfolio_view.index)
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
        tx_df = pd.read_json(personal_portfolio_tx)
        performance = tracker_portfolio.get_performance(
            date=tx_df["date"].max(), tx_df=tx_df
        ).reset_index()

        performance_table = [
            {"name": i, "id": i} for i in performance.columns
        ], performance.to_dict("records")
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
        tx_df = pd.read_json(personal_portfolio_tx)
        tx_df = tx_df[tx_df["units"] != 0]

        transaction_table = [
            {"name": i, "id": i} for i in tx_df.columns
        ], tx_df.to_dict("records")
    else:
        transaction_table = (None, None)

    return transaction_table


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
    ],
)
def toggle_interval_speed(task_status, task_id, personal_task_status, personal_task_id):
    """Triggered by changes in task-id and task-status divs.

    It switches the page refresh interval to fast (1 sec) if a task is running, or slow (24 hours) if a task is
    pending or complete.
    """
    try:
        job = Job.fetch(task_id, connection=worker.conn)
        task_id = job.get_status()
    except:
        task_id = "stand by"
    try:
        job = Job.fetch(personal_task_id, connection=worker.conn)
        personal_task_status = job.get_status()
    except:
        personal_task_status = "stand by"

    if (task_id != "none" and task_status in ["started", "waiting"]) or (
        personal_task_id != "none" and personal_task_status in ["started", "waiting"]
    ):
        return 1000
    else:
        return 24 * 60 * 60 * 1000


if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0")
