"""
Building plotly dashboard.

Builds plotly pages with call backs. There are 2 options the user has for running code.
1. Heroku build set up
2. Local running

To run locally:
1. cd into root directory
2. run plotly dashboard - `python app.py`
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

from iex.pages import stocks, sectors, ideas, macro, tracker, crypto
from iex.util import constants, layouts, portfolio, utils
from iex.util.worker import conn

q = Queue(connection=conn)

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
    else:
        return "404"


#   ____ _____ ___   ____ _  __
#  / ___|_   _/ _ \ / ___| |/ /
#  \___ \ | || | | | |   | ' /
#   ___) || || |_| | |___| . \
#  |____/ |_| \___/ \____|_|\_\


@app.callback(
    [
        Output(component_id="stock-table", component_property="columns"),
        Output(component_id="stock-table", component_property="data"),
    ],
    [Input(component_id="stock-button", component_property="n_clicks")],
    [State(component_id="stock-input", component_property="value")],
)
def update_stockanalysis(n_clicks, input_value):
    """Provide stock analysis table."""
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

    return [{"name": i, "id": i} for i in stock.columns], stock.to_dict("records")


@app.callback(
    [
        Output(component_id="quote-table", component_property="columns"),
        Output(component_id="quote-table", component_property="data"),
    ],
    [Input(component_id="quote-button", component_property="n_clicks")],
    [State(component_id="stock-input", component_property="value")],
)
def update_quoteanalysis(n_clicks, input_value):
    """Provide quote analysis table."""
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

    return [{"name": i, "id": i} for i in quote.columns], quote.to_dict("records")


@app.callback(
    [
        Output(component_id="peer-table", component_property="columns"),
        Output(component_id="peer-table", component_property="data"),
    ],
    [Input(component_id="peer-button", component_property="n_clicks")],
    [State(component_id="stock-input", component_property="value")],
)
def update_peeranalysis(n_clicks, input_value):
    """Provide peer analysis table."""
    urlpeer = (
        "https://cloud.iexapis.com/stable/stock/"
        + format(input_value)
        + "/peers?token="
        + constants.iex_api_live
    )
    peer = pd.read_json(urlpeer, orient="columns", typ="series")
    peer = peer.reset_index()
    peer.columns = ["Index", "Peer"]

    return [{"name": i, "id": i} for i in peer.columns], peer.to_dict("records")


@app.callback(
    [
        Output(component_id="sentiment-table", component_property="columns"),
        Output(component_id="sentiment-table", component_property="data"),
    ],
    [Input(component_id="sentiment-button", component_property="n_clicks")],
    [
        State(component_id="stock-input", component_property="value"),
        State(component_id="date-input", component_property="date"),
    ],
)
def update_sentiment(n_clicks, input_value, date_value):
    """Provide sentiment analysis table."""
    date_obj = datetime.datetime.strptime(date_value, "%Y-%m-%d")
    urlsentiment = (
        "https://cloud.iexapis.com/stable/stock/"
        + format(input_value)
        + "/sentiment/daily/"
        + date_obj.strftime("%Y%m%d")
        + "?token="
        + constants.iex_api_live
    )
    sentiment = pd.read_json(urlsentiment, orient="columns", typ="series")
    sentiment = sentiment.reset_index()
    sentiment.columns = ["Variable", "Value"]

    return [{"name": i, "id": i} for i in sentiment.columns], sentiment.to_dict(
        "records"
    )


@app.callback(
    [
        Output(component_id="news-table", component_property="columns"),
        Output(component_id="news-table", component_property="data"),
    ],
    [Input(component_id="news-button", component_property="n_clicks")],
    [State(component_id="stock-input", component_property="value")],
)
def update_newsanalysis(n_clicks, input_value):
    """Provide news analysis table."""
    urlnews = (
        "https://cloud.iexapis.com/stable/stock/"
        + format(input_value)
        + "/news/last/5?token="
        + constants.iex_api_live
    )
    news = pd.read_json(urlnews, orient="columns")

    return [{"name": i, "id": i} for i in news.columns], news.to_dict("records")


@app.callback(
    [
        Output(component_id="active-table", component_property="columns"),
        Output(component_id="active-table", component_property="data"),
    ],
    [Input(component_id="active-button", component_property="n_clicks")],
)
def update_activeanalysis(n_clicks):
    """Provide active analysis table."""
    urlactive = (
        "https://cloud.iexapis.com/stable/stock/market/list/mostactive?listLimit=20&token="
        + constants.iex_api_live
    )
    active = pd.read_json(urlactive, orient="columns")
    active["vol_delta"] = active["volume"] / active["avgTotalVolume"]
    active = active[layouts.active_col]
    active = active.round(2)
    active["changePercent"] = active["changePercent"].astype(float).map("{:.1%}".format)
    active["ytdChange"] = active["ytdChange"].astype(float).map("{:.1%}".format)

    return [{"name": i, "id": i} for i in active.columns], active.to_dict("records")


#   ____  _____ ____ _____ ___  ____
#  / ___|| ____/ ___|_   _/ _ \|  _ \
#  \___ \|  _|| |     | || | | | |_) |
#   ___) | |__| |___  | || |_| |  _ <
#  |____/|_____\____| |_| \___/|_| \_\

# Table
@app.callback(
    [
        Output(component_id="sector-table", component_property="columns"),
        Output(component_id="sector-table", component_property="data"),
    ],
    [Input(component_id="sector-dropdown", component_property="value")],
)
def update_table(dropdown_value):
    """Provide sector analysis table."""
    urlcol = (
        "https://cloud.iexapis.com/stable/stock/market/collection/sector?collectionName="
        + format(dropdown_value)
        + "&token="
        + constants.iex_api_live
    )
    collection_all = pd.read_json(urlcol, orient="columns")
    collection = collection_all[
        collection_all.primaryExchange.isin(layouts.USexchanges)
    ]
    collection["cap*perc"] = collection["marketCap"] * collection["changePercent"]
    collection["latestUpdate"] = pd.to_datetime(collection["latestUpdate"], unit="ms")
    collection = collection[layouts.cols_col]
    collection = collection.sort_values(by=["cap*perc"], ascending=False)

    return [{"name": i, "id": i} for i in collection.columns], collection.to_dict(
        "records"
    )


# Graph
@app.callback(
    Output("task-id", "children"),
    [Input(component_id="sector-initialize", component_property="n_clicks")],
)
def initialize_SectorGraph(n_clicks):
    """Provide sector analysis graph."""
    task_id = q.enqueue(utils.sector_query).id

    return task_id


@app.callback(
    Output("interval-component", "interval"),
    [Input("task-status", "children"), Input("task-id", "children")],
)
def toggle_interval_speed(task_status, task_id):
    """Triggered by changes in task-id and task-status divs.

    It switches the page refresh interval to fast (1 sec) if a task is running, or slow (24 hours) if a task is
    pending or complete.
    """
    if task_id == "none":
        return 24 * 60 * 60 * 1000
    if task_id != "none" and (task_status in ["finished"]):
        return 24 * 60 * 60 * 1000
    else:
        return 1000


@app.callback(
    [Output("task-status", "children"), Output("refresh_text", "children")],
    [Input("interval-component", "n_intervals")],
    [State("task-id", "children"), State("task-status", "children")],
)
def status_check(n_intervals, task_id, task_status):
    """Provide status check."""
    if task_id != "none" and task_status != "finished":
        job = Job.fetch(task_id, connection=conn)
        task_status = job.get_status()
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
        job = Job.fetch(task_id, connection=conn)
        sector_close = job.result
        job.delete()
        sector_status = "ready"
    else:
        sector_status = "none"
        sector_close = pd.DataFrame([])
    return sector_close.to_json(), sector_status


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
        daterange = sector_close.index
        min = utils.unix_time_millis(daterange.min())
        max = utils.unix_time_millis(daterange.max())
        value = [
            utils.unix_time_millis(daterange.min()),
            utils.unix_time_millis(daterange.max()),
        ]
        marks = utils.getMarks(daterange.min(), daterange.max())
    else:
        min = 0
        max = 0
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
        ]
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


#   _____ ____      _    ____ _  _______ ____
#  |_   _|  _ \    / \  / ___| |/ / ____|  _ \
#    | | | |_) |  / _ \| |   | ' /|  _| | |_) |
#    | | |  _ <  / ___ \ |___| . \| |___|  _ <
#    |_| |_| \_\/_/   \_\____|_|\_\_____|_| \_\


tx_file = constants.remote_path + r"transactions.xlsx"
the_portfolio = portfolio.portfolio(
    tx_file, filter_type=["Cash", "Dividend"], funds=["BLKRK"]
)
portfolio_view = the_portfolio.portfolio_view
cost_view = the_portfolio.cost_view


@app.callback(Output("Tracker-Graph", "figure"), [Input("track_slider", "value")])
def update_TrackerGraph(slide_value):
    """Provide tracker graph."""
    res = []
    layout = go.Layout(hovermode="closest")

    track_grph = portfolio_view[
        (utils.unix_time_millis(portfolio_view.index) > slide_value[0])
        & (utils.unix_time_millis(portfolio_view.index) <= slide_value[1])
    ]

    cost_grph = cost_view[
        (utils.unix_time_millis(cost_view.index) > slide_value[0])
        & (utils.unix_time_millis(cost_view.index) <= slide_value[1])
    ]
    for col in track_grph.columns:
        track_grph.loc[track_grph[col] != 0, "change"] = (
            track_grph[col] + cost_grph[col]
        ) / cost_grph[col] - 1
        track_grph.drop([col], axis=1, inplace=True)
        track_grph = track_grph.rename(columns={"change": col})
        res.append(
            go.Scatter(x=track_grph.index, y=track_grph[col].values.tolist(), name=col)
        )

    fig = dict(data=res, layout=layout)

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

    return [{"name": i, "id": i} for i in df.columns], df.to_dict("records")


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

    return [{"name": i, "id": i} for i in quote.columns], quote.to_dict("records")


if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0")
