import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import dash_table
from dash.dependencies import Input, Output
from utils import make_dash_table

#set up lists
USexchanges=['NASDAQ', 'New York Stock Exchange'] #,'US OTC', 'NYSE American' 'NASDAQ', 'New York Stock Exchange'
cols_col = ['symbol',
        'companyName',
        'primaryExchange',
        'peRatio',
        'cap*perc',
        'changePercent',
        'marketCap',
        'change',
        'close',
        'open',
        'latestPrice',
        'latestSource',
        'latestUpdate']

formatter_col = {'cap*perc':'{:,.2f}'.format,
                 'changePercent':'{0:.2%}'.format, 
                 'marketCap':'{:,.2f}'.format}

formatter_stock = {'day5ChangePercent':'{0:.2%}'.format,
                    'week52change':'{:,.2f}'.format,
                    'year1ChangePercent':'{0:.2%}'.format,
                    'month3ChangePercent':'{0:.2%}'.format,
                    'month1ChangePercent':'{0:.2%}'.format,
                    'dividendYield':'{0:.2%}'.format,
                    'day30ChangePercent':'{0:.2%}'.format,
                    'month6ChangePercent':'{0:.2%}'.format,
                    'ytdChangePercent':'{0:.2%}'.format,
                    'year2ChangePercent':'{0:.2%}'.format,
                    'year5ChangePercent':'{0:.2%}'.format,
                    'beta':'{:,.2f}'.format,
                    'ttmDividendRate':'{:,.2f}'.format,
                    'ttmEPS':'{:,.2f}'.format,
                    'peRatio':'{:,.2f}'.format,
                    'week52low':'{:,.2f}'.format,
                    'day200MovingAvg':'{:,.2f}'.format,
                    'day50MovingAvg':'{:,.2f}'.format,
                    'maxChangePercent':'{0:.2%}'.format,
                    'week52high':'{:,.2f}'.format,
                    'employees':'{:,.2f}'.format,
                    'avg30Volume':'{:,.2f}'.format,
                    'avg10Volume':'{:,.2f}'.format,
                    'float':'{:,.2f}'.format,
                    'sharesOutstanding':'{:,.2f}'.format,
                    'marketcap':'{:,.2f}'.format,}
                



# Sector URL
urlsec = 'https://cloud.iexapis.com/stable/ref-data/sectors?token=sk_073f76780cf94eb5948b7f5f11bec968'
sectors = pd.read_json(urlsec, orient='columns')
sectors['name']=sectors['name'].str.replace(' ','%20')

#Creating the dash app

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__)

server = app.server

app.layout = html.Div([
    
    #creating stock information
    html.Label('Stock Analysis'),
    html.P(),  
    
    dcc.Input(id='stock-input', placeholder='Enter Stock...', type='text'),
    
    dash_table.DataTable(
    id='stock-table',
    filter_action="native",
    sort_action="native",
    #virtualization=True,
    page_action="native",
    ),
    
    #creating dropdown menu
    html.Label('Sector Dropdown'),

    dcc.Dropdown(
    id='sector-dropdown', 
    options=[
    {'label': i, 'value': i} for i in sectors.name.unique()
    ], 
    multi=False, 
    placeholder='Select Sector...',
    ),
    
    #creating table that is based on dropdown menu
    html.P(),    
    
    html.Label('Sector Table'),
    
    dash_table.DataTable(
    id='sector-table',
    filter_action="native",
    sort_action="native",
    #virtualization=True,
    page_action="native",
    ),
            
    html.Div(id='my-div')

])
    
    
@app.callback(
    [Output(component_id='sector-table', component_property='columns'),
     Output(component_id='sector-table', component_property='data')],
    [Input(component_id='sector-dropdown', component_property='value')]
)
def update_table(dropdown_value):
    urlcol='https://cloud.iexapis.com/stable/stock/market/collection/sector?collectionName=' + format(dropdown_value) + '&token=sk_073f76780cf94eb5948b7f5f11bec968'
    #urlcol = 'https://sandbox.iexapis.com/stable/stock/market/collection/sector?collectionName=Technology&token=Tsk_2b2286bdd1084f7ea6254e1d240f083a'
    collection_all = pd.read_json(urlcol, orient='columns')
    collection = collection_all[collection_all.primaryExchange.isin(USexchanges)]
    collection['cap*perc']=collection['marketCap']*collection['changePercent']
    collection['latestUpdate']=pd.to_datetime(collection['latestUpdate'], unit='ms')
    collection = collection[cols_col]
    collection = collection.sort_values(by=['cap*perc'], ascending=False)
    
    for f in formatter_col.items():
        column = f[0]
        collection[column] = collection[column].map(f[1])
    
    return [{"name": i, "id": i} for i in collection.columns],collection.to_dict('records')

@app.callback(
    [Output(component_id='stock-table', component_property='columns'),
     Output(component_id='stock-table', component_property='data')],
    [Input(component_id='stock-input', component_property='value')]
)
def update_stockanalysis(input_value):
    urlstock='https://cloud.iexapis.com/stable/stock/'  + format(input_value) + '/stats?token=sk_073f76780cf94eb5948b7f5f11bec968'
    stock = pd.read_json(urlstock, orient='index', typ='frame')
            
    for f in formatter_stock.items():
            column = f[0]
            stock.loc[column] = stock.loc[column].apply(f[1])
    
    stock = stock.reset_index()
    stock.columns = ['Variable', 'Value']
            
    return [{"name": i, "id": i} for i in stock.columns], stock.to_dict('records')



 
if __name__ == '__main__':
    app.run_server(debug=False)
    