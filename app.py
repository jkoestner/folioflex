import dash
import datetime
import math
import pandas as pd
import pandas_market_calendars as mcal
import plotly.graph_objs as go
from dash import dash_table
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
from dateutil.relativedelta import relativedelta
from rq import Queue
from rq.job import Job
from worker import conn

import function
from pages import stocks, layouttab, sectors, utils, ideas, macro, tracker

q = Queue(connection=conn)

###APP###
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

##########Index Page callback##################
@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def display_page(pathname):
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
    else:
        return "404"


##########Stock callback##################
@app.callback(
    [
        Output(component_id="stock-table", component_property="columns"),
        Output(component_id="stock-table", component_property="data"),
    ],
    [Input(component_id="stock-button", component_property="n_clicks")],
    [State(component_id="stock-input", component_property="value")],
)
def update_stockanalysis(n_clicks, input_value):
    urlstock = (
        "https://cloud.iexapis.com/stable/stock/"
        + format(input_value)
        + "/stats?token=pk_5d82796966de466bb2f966ed65ca70c7"
    )
    # urlstock='https://sandbox.iexapis.com/stable/stock/AMZN/stats?token=Tsk_2b2286bdd1084f7ea6254e1d240f083a'

    stock = pd.read_json(urlstock, orient="index", typ="frame")

    #    for f in layouttab.formatter_stock.items():
    #            column = f[0]
    #            if stock.loc[column].values[0] is not None:
    #                stock.loc[column] = stock.loc[column].apply(f[1])

    stock = stock.reset_index()
    stock.columns = ["Variable", "Value"]

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
    urlquote = (
        "https://cloud.iexapis.com/stable/stock/"
        + format(input_value)
        + "/quote?token=pk_5d82796966de466bb2f966ed65ca70c7"
    )
    # urlquote = 'https://sandbox.iexapis.com/stable/stock/aapl/quote?token=Tsk_2b2286bdd1084f7ea6254e1d240f083a'
    quote = pd.read_json(urlquote, orient="index", typ="frame")

    #    for f in layouttab.formatter_quote.items():
    #        column = f[0]
    #        if quote.loc[column].values[0] is not None:
    #            quote.loc[column] = quote.loc[column].apply(f[1])

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

    quote = quote.loc[layouttab.quote_col]
    quote = quote.reset_index()
    quote.columns = ["Variable", "Value"]

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
    urlpeer = (
        "https://cloud.iexapis.com/stable/stock/"
        + format(input_value)
        + "/peers?token=pk_5d82796966de466bb2f966ed65ca70c7"
    )
    # urlpeer = 'https://sandbox.iexapis.com/stable/stock/aapl/peers?token=Tsk_2b2286bdd1084f7ea6254e1d240f083a'
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
    date_obj = datetime.datetime.strptime(date_value, "%Y-%m-%d")
    urlsentiment = (
        "https://cloud.iexapis.com/stable/stock/"
        + format(input_value)
        + "/sentiment/daily/"
        + date_obj.strftime("%Y%m%d")
        + "?token=pk_5d82796966de466bb2f966ed65ca70c7"
    )
    # urlsentiment = 'https://sandbox.iexapis.com/stable/stock/aapl/sentiment/daily/20191008?token=Tsk_2b2286bdd1084f7ea6254e1d240f083a'
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
    urlnews = (
        "https://cloud.iexapis.com/stable/stock/"
        + format(input_value)
        + "/news/last/5?token=pk_5d82796966de466bb2f966ed65ca70c7"
    )
    # urlnews = 'https://sandbox.iexapis.com/stable/stock/aapl/peers?token=Tsk_2b2286bdd1084f7ea6254e1d240f083a'
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
    urlactive = "https://cloud.iexapis.com/stable/stock/market/list/mostactive?listLimit=20&token=pk_5d82796966de466bb2f966ed65ca70c7"
    # urlactive = 'https://sandbox.iexapis.com/stable/stock/market/list/mostactive?token=Tsk_2b2286bdd1084f7ea6254e1d240f083a'
    active = pd.read_json(urlactive, orient="columns")
    active["vol_delta"] = active["volume"] / active["avgTotalVolume"]
    active = active[layouttab.active_col]

    return [{"name": i, "id": i} for i in active.columns], active.to_dict("records")


##########Sector callback##################
@app.callback(
    [
        Output(component_id="sector-table", component_property="columns"),
        Output(component_id="sector-table", component_property="data"),
    ],
    [Input(component_id="sector-dropdown", component_property="value")],
)
def update_table(dropdown_value):
    urlcol = (
        "https://cloud.iexapis.com/stable/stock/market/collection/sector?collectionName="
        + format(dropdown_value)
        + "&token=pk_5d82796966de466bb2f966ed65ca70c7"
    )
    # urlcol = 'https://sandbox.iexapis.com/stable/stock/market/collection/sector?collectionName=Technology&token=Tsk_2b2286bdd1084f7ea6254e1d240f083a'
    collection_all = pd.read_json(urlcol, orient="columns")
    collection = collection_all[
        collection_all.primaryExchange.isin(layouttab.USexchanges)
    ]
    collection["cap*perc"] = collection["marketCap"] * collection["changePercent"]
    collection["latestUpdate"] = pd.to_datetime(collection["latestUpdate"], unit="ms")
    collection = collection[layouttab.cols_col]
    collection = collection.sort_values(by=["cap*perc"], ascending=False)

    #    for f in layouttab.formatter_col.items():
    #        column = f[0]
    #        collection[column] = collection[column].map(f[1])

    return [{"name": i, "id": i} for i in collection.columns], collection.to_dict(
        "records"
    )


#################Sector Graph Callback#####################
@app.callback(
    Output("task-id", "children"),
    [Input(component_id="sector-initialize", component_property="n_clicks")],
)
def initialize_SectorGraph(n_clicks):

    task_id = q.enqueue(function.sector_query).id

    return task_id


@app.callback(
    Output("interval-component", "interval"),
    [Input("task-status", "children"), Input("task-id", "children")],
)
def toggle_interval_speed(task_status, task_id):
    """This callback is triggered by changes in task-id and task-status divs.  It switches the
    page refresh interval to fast (1 sec) if a task is running, or slow (24 hours) if a task is
    pending or complete."""
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
            #            sector_data['change'] = sector_data['change'].map('{0:.2%}'.format)
            sector_data = sector_data.rename(columns={"change": col})
            res.append(
                go.Scatter(
                    x=sector_data.index, y=sector_data[col].values.tolist(), name=col
                )
            )
    else:
        tbd = "delete"

    fig = dict(data=res, layout=layout)

    return fig


#################Tracker Graph Callback#####################
@app.callback(
    [
        Output("track_slider", "min"),
        Output("track_slider", "max"),
        Output("track_slider", "value"),
        Output("track_slider", "marks"),
    ],
    [Input("track_data", "children")],
)
def update_TrackerData(track_data):
    track_json = pd.read_json(track_data)
    daterange = track_json.index
    min = utils.unix_time_millis(daterange.min())
    max = utils.unix_time_millis(daterange.max())
    value = [
        utils.unix_time_millis(daterange.min()),
        utils.unix_time_millis(daterange.max()),
    ]
    marks = utils.getMarks(daterange.min(), daterange.max())

    return min, max, value, marks


@app.callback(Output("Tracker-Graph", "figure"), [Input("track_slider", "value")])
def update_TrackerGraph(slide_value):
    res = []
    layout = go.Layout(hovermode="closest")

    tx_df, portfolio = function.get_portfolio_and_transaction()
    track_data = portfolio
    track_json = pd.read_json(track_data)
    track_grph = track_json[
        (utils.unix_time_millis(track_json.index) > slide_value[0])
        & (utils.unix_time_millis(track_json.index) <= slide_value[1])
    ]
    for col in track_grph.columns:
        track_grph["change"] = track_grph[col] / track_grph[col].iat[0] - 1
        track_grph.drop([col], axis=1, inplace=True)
        track_grph = track_grph.rename(columns={"change": col})
        res.append(
            go.Scatter(x=track_grph.index, y=track_grph[col].values.tolist(), name=col)
        )

    fig = dict(data=res, layout=layout)

    return fig


##########Ideas callback##################
@app.callback(
    [
        Output(component_id="sma-table", component_property="columns"),
        Output(component_id="sma-table", component_property="data"),
    ],
    [Input(component_id="sma-button", component_property="n_clicks")],
    [State(component_id="idea-input", component_property="value")],
)
def sma_value(n_clicks, input_value):
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
        + "&token=pk_5d82796966de466bb2f966ed65ca70c7"
    )
    sma = pd.read_json(urlsma, orient="index", typ="frame")
    sma_val = sma.loc["indicator"].values[0][-1]
    urlquote = (
        "https://cloud.iexapis.com/stable/stock/"
        + format(input_value)
        + "/quote?token=pk_5d82796966de466bb2f966ed65ca70c7"
    )
    quote = pd.read_json(urlquote, orient="index", typ="frame")
    latest_price = quote.loc["latestPrice"].values[0]
    urlstock = (
        "https://cloud.iexapis.com/stable/stock/"
        + format(input_value)
        + "/stats?token=pk_5d82796966de466bb2f966ed65ca70c7"
    )
    stock = pd.read_json(urlstock, orient="index", typ="frame")
    return_12mo = stock.loc["year1ChangePercent"].values[0]

    # build table
    stock_data = [[input_value, sma_val, latest_price, return_12mo]]
    df = pd.DataFrame(
        stock_data, columns=["Stock", "12mo SMA", "Latest Price", "12mo Return"]
    )

    return [{"name": i, "id": i} for i in df.columns], df.to_dict("records")


if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0")
