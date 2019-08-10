import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import dash_table
from dash.dependencies import Input, Output, State
from pages import stocks, layout, sectors

app = dash.Dash(
    __name__,
    external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css']
)
server = app.server
app.config.suppress_callback_exceptions = True

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

##########Index Page callback##################
@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/':
        return stocks.layout
    elif pathname == '/stocks':
        return stocks.layout
    elif pathname == '/sectors':
        return sectors.layout
    else:
        return '404'

##########Stock callback##################
@app.callback(
    [Output(component_id='stock-table', component_property='columns'),
     Output(component_id='stock-table', component_property='data')],
     [Input(component_id='stock-button', component_property='n_clicks')],
    [State(component_id='stock-input', component_property='value')]
)

def update_stockanalysis(n_clicks,input_value):
    urlstock='https://cloud.iexapis.com/stable/stock/'  + format(input_value) + '/stats?token=pk_5d82796966de466bb2f966ed65ca70c7'
    #urlstock='https://sandbox.iexapis.com/stable/stock/AMZN/stats?token=Tsk_2b2286bdd1084f7ea6254e1d240f083a'
    
    stock = pd.read_json(urlstock, orient='index', typ='frame')
            
    for f in layout.formatter_stock.items():
            column = f[0]
            if stock.loc[column].values[0] is not None:
                stock.loc[column] = stock.loc[column].apply(f[1])              

    
    stock = stock.reset_index()
    stock.columns = ['Variable', 'Value']
            
    return [{"name": i, "id": i} for i in stock.columns], stock.to_dict('records')

@app.callback(
    [Output(component_id='quote-table', component_property='columns'),
     Output(component_id='quote-table', component_property='data')],
     [Input(component_id='quote-button', component_property='n_clicks')],
    [State(component_id='stock-input', component_property='value')]
)

def update_quoteanalysis(n_clicks,input_value):          
    urlquote='https://cloud.iexapis.com/stable/stock/'  + format(input_value) + '/quote?token=pk_5d82796966de466bb2f966ed65ca70c7'
    #urlquote = 'https://sandbox.iexapis.com/stable/stock/aapl/quote?token=Tsk_2b2286bdd1084f7ea6254e1d240f083a'
    quote = pd.read_json(urlquote, orient='index', typ='frame')   

    for f in layout.formatter_quote.items():
        column = f[0]
        if quote.loc[column].values[0] is not None:
            quote.loc[column] = quote.loc[column].apply(f[1])   
    
    quote.loc['closeTime'].values[0]=pd.to_datetime(quote.loc['closeTime'].values[0], unit='ms')
    quote.loc['iexLastUpdated'].values[0]=pd.to_datetime(quote.loc['iexLastUpdated'].values[0], unit='ms')
    quote.loc['lastTradeTime'].values[0]=pd.to_datetime(quote.loc['lastTradeTime'].values[0], unit='ms')
    quote.loc['latestUpdate'].values[0]=pd.to_datetime(quote.loc['latestUpdate'].values[0], unit='ms')
    quote.loc['extendedPriceTime'].values[0]=pd.to_datetime(quote.loc['extendedPriceTime'].values[0], unit='ms')
    
    quote = quote.loc[layout.quote_col]
    quote = quote.reset_index()
    quote.columns = ['Variable', 'Value']

            
    return [{"name": i, "id": i} for i in quote.columns], quote.to_dict('records')

@app.callback(
    [Output(component_id='peer-table', component_property='columns'),
     Output(component_id='peer-table', component_property='data')],
     [Input(component_id='peer-button', component_property='n_clicks')],
    [State(component_id='stock-input', component_property='value')]
)

def update_peeranalysis(n_clicks,input_value):          
    urlpeer='https://cloud.iexapis.com/stable/stock/'  + format(input_value) + '/peers?token=pk_5d82796966de466bb2f966ed65ca70c7'
    #urlpeer = 'https://sandbox.iexapis.com/stable/stock/aapl/peers?token=Tsk_2b2286bdd1084f7ea6254e1d240f083a'
    peer = pd.read_json(urlpeer, orient='columns', typ='series')
    peer = peer.reset_index()
    peer.columns = ['Index','Peer']           
            
    return [{"name": i, "id": i} for i in peer.columns], peer.to_dict('records')
    
@app.callback(
    [Output(component_id='news-table', component_property='columns'),
     Output(component_id='news-table', component_property='data')],
     [Input(component_id='news-button', component_property='n_clicks')],
    [State(component_id='stock-input', component_property='value')]
)

def update_newsanalysis(n_clicks,input_value):          
    urlnews='https://cloud.iexapis.com/stable/stock/'  + format(input_value) + '/news/last/5?token=pk_5d82796966de466bb2f966ed65ca70c7'
    #urlnews = 'https://sandbox.iexapis.com/stable/stock/aapl/peers?token=Tsk_2b2286bdd1084f7ea6254e1d240f083a'
    news = pd.read_json(urlnews, orient='columns')
        
            
    return [{"name": i, "id": i} for i in news.columns], news.to_dict('records')

##########Sector callback##################
@app.callback(
    [Output(component_id='sector-table', component_property='columns'),
     Output(component_id='sector-table', component_property='data')],
    [Input(component_id='sector-dropdown', component_property='value')]
)
def update_table(dropdown_value):
    urlcol='https://cloud.iexapis.com/stable/stock/market/collection/sector?collectionName=' + format(dropdown_value) + '&token=pk_5d82796966de466bb2f966ed65ca70c7'
    #urlcol = 'https://sandbox.iexapis.com/stable/stock/market/collection/sector?collectionName=Technology&token=Tsk_2b2286bdd1084f7ea6254e1d240f083a'
    collection_all = pd.read_json(urlcol, orient='columns')
    collection = collection_all[collection_all.primaryExchange.isin(layout.USexchanges)]
    collection['cap*perc']=collection['marketCap']*collection['changePercent']
    collection['latestUpdate']=pd.to_datetime(collection['latestUpdate'], unit='ms')
    collection = collection[layout.cols_col]
    collection = collection.sort_values(by=['cap*perc'], ascending=False)
    
    for f in layout.formatter_col.items():
        column = f[0]
        collection[column] = collection[column].map(f[1])
    
    return [{"name": i, "id": i} for i in collection.columns],collection.to_dict('records')

if __name__ == '__main__':
    app.run_server(debug=False)
