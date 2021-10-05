import dash
from dash import dcc
from dash import html
import pandas as pd
import dash_table
from dash.dependencies import Input, Output, State

# set up lists
USexchanges = [
    "NASDAQ",
    "New York Stock Exchange",
]  # ,'US OTC', 'NYSE American' 'NASDAQ', 'New York Stock Exchange'
cols_col = [
    "symbol",
    "companyName",
    "primaryExchange",
    "peRatio",
    "cap*perc",
    "changePercent",
    "marketCap",
    "change",
    "close",
    "open",
    "latestPrice",
    "latestSource",
    "latestUpdate",
]

formatter_col = {
    "cap*perc": "{:,.2f}".format,
    "changePercent": "{0:.2%}".format,
    "marketCap": "{:,.2f}".format,
}

formatter_stock = {
    "day5ChangePercent": "{0:.2%}".format,
    "week52change": "{:,.2f}".format,
    "year1ChangePercent": "{0:.2%}".format,
    "month3ChangePercent": "{0:.2%}".format,
    "month1ChangePercent": "{0:.2%}".format,
    "dividendYield": "{0:.2%}".format,
    "day30ChangePercent": "{0:.2%}".format,
    "month6ChangePercent": "{0:.2%}".format,
    "ytdChangePercent": "{0:.2%}".format,
    "year2ChangePercent": "{0:.2%}".format,
    "year5ChangePercent": "{0:.2%}".format,
    "beta": "{:,.2f}".format,
    "ttmDividendRate": "{:,.2f}".format,
    "ttmEPS": "{:,.2f}".format,
    "peRatio": "{:,.2f}".format,
    "week52low": "{:,.2f}".format,
    "day200MovingAvg": "{:,.2f}".format,
    "day50MovingAvg": "{:,.2f}".format,
    "maxChangePercent": "{0:.2%}".format,
    "week52high": "{:,.2f}".format,
    "employees": "{:,.2f}".format,
    "avg30Volume": "{:,.2f}".format,
    "avg10Volume": "{:,.2f}".format,
    "float": "{:,.2f}".format,
    "sharesOutstanding": "{:,.2f}".format,
    "marketcap": "{:,.2f}".format,
}

quote_col = [
    "symbol",
    "companyName",
    "isUSMarketOpen",
    "latestPrice",
    "previousClose",
    "latestUpdate",
    "latestSource",
    "change",
    "changePercent",
    "ytdChange",
    "latestVolume",
    "avgTotalVolume",
    "previousVolume",
    "marketCap",
    "peRatio",
    "extendedPrice",
    "extendedPriceTime",
    "open",
    "close",
    "high",
    "low",
    "week52High",
    "week52Low",
]

formatter_quote = {
    "avgTotalVolume": "{:,.2f}".format,
    "change": "{:,.2f}".format,
    "close": "{:,.2f}".format,
    "delayedPrice": "{:,.2f}".format,
    "delayedPriceTime": "{:,.2f}".format,
    "extendedChange": "{:,.2f}".format,
    "extendedChangePercent": "{:,.2f}".format,
    "extendedPrice": "{:,.2f}".format,
    "high": "{:,.2f}".format,
    "iexAskPrice": "{:,.2f}".format,
    "iexAskSize": "{:,.2f}".format,
    "iexBidPrice": "{:,.2f}".format,
    "iexBidSize": "{:,.2f}".format,
    "iexRealtimePrice": "{:,.2f}".format,
    "iexRealtimeSize": "{:,.2f}".format,
    "iexVolume": "{:,.2f}".format,
    "latestPrice": "{:,.2f}".format,
    "latestVolume": "{:,.2f}".format,
    "low": "{:,.2f}".format,
    "marketCap": "{:,.2f}".format,
    "open": "{:,.2f}".format,
    "openTime": "{:,.2f}".format,
    "peRatio": "{:,.2f}".format,
    "previousClose": "{:,.2f}".format,
    "previousVolume": "{:,.2f}".format,
    "volume": "{:,.2f}".format,
    "week52High": "{:,.2f}".format,
    "week52Low": "{:,.2f}".format,
    "changePercent": "{0:.2%}".format,
    "ytdChange": "{0:.2%}".format,
}


# Sector URL
urlsec = "https://cloud.iexapis.com/stable/ref-data/sectors?token=pk_5d82796966de466bb2f966ed65ca70c7"
sectors = pd.read_json(urlsec, orient="columns")
sectors["name"] = sectors["name"].str.replace(" ", "%20")

# Creating the dash app

app = dash.Dash(
    __name__, external_stylesheets=["https://codepen.io/chriddyp/pen/bWLwgP.css"]
)

server = app.server

app.layout = html.Div(
    [
        html.Div(
            [
                html.Label("Stock Analysis"),
                html.P(),
                dcc.Input(id="stock-input", placeholder="Enter Stock...", type="text"),
                html.Button(id="stock-button", children="Stock Submit"),
                html.Button(id="quote-button", children="Quote Submit"),
                html.Button(id="peer-button", children="Peer Submit"),
                html.Button(id="news-button", children="News Submit"),
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
                html.Div(
                    [
                        # creating peer information
                        html.P(),
                        dash_table.DataTable(
                            id="peer-table",
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
                # creating dropdown menu
                html.Label("Sector Dropdown"),
                dcc.Dropdown(
                    id="sector-dropdown",
                    options=[{"label": i, "value": i} for i in sectors.name.unique()],
                    multi=False,
                    placeholder="Select Sector...",
                ),
                # creating table that is based on dropdown menu
                html.P(),
                html.Label("Sector Table"),
                dash_table.DataTable(
                    id="sector-table",
                    filter_action="native",
                    sort_action="native",
                    # virtualization=True,
                    page_action="native",
                ),
                html.Div(id="my-div"),
            ],
            className="row",
        ),
    ]
)


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
    collection = collection_all[collection_all.primaryExchange.isin(USexchanges)]
    collection["cap*perc"] = collection["marketCap"] * collection["changePercent"]
    collection["latestUpdate"] = pd.to_datetime(collection["latestUpdate"], unit="ms")
    collection = collection[cols_col]
    collection = collection.sort_values(by=["cap*perc"], ascending=False)

    for f in formatter_col.items():
        column = f[0]
        collection[column] = collection[column].map(f[1])

    return [{"name": i, "id": i} for i in collection.columns], collection.to_dict(
        "records"
    )


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

    for f in formatter_stock.items():
        column = f[0]
        if stock.loc[column].values[0] is not None:
            stock.loc[column] = stock.loc[column].apply(f[1])

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

    for f in formatter_quote.items():
        column = f[0]
        if quote.loc[column].values[0] is not None:
            quote.loc[column] = quote.loc[column].apply(f[1])

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

    quote = quote.loc[quote_col]
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


if __name__ == "__main__":
    app.run_server(debug=False)
