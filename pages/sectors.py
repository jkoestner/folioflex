import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import dash_table
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import datetime
from dateutil.relativedelta import relativedelta
import app
from pages import utils, layout

# Sector URL
urlsec = 'https://cloud.iexapis.com/stable/ref-data/sectors?token=pk_5d82796966de466bb2f966ed65ca70c7'
sectors = pd.read_json(urlsec, orient='columns')
sectors['name']=sectors['name'].str.replace(' ','%20')

# Sector Data
sector_close=pd.DataFrame([])
for i in layout.sector_list:
    urlsec_data='https://api.worldtradingdata.com/api/v1/history?symbol=' + format(i) + '&sort=newest&api_token=aB0PKnbqXhFuYJtXmOvasDHf2M82BCY3PI9N9o4kb0UHwf5zVckMnD0PL2hc'
    sector_temp = pd.read_json(urlsec_data, orient='columns')
    sector_temp = pd.concat([sector_temp.drop(['history'], axis=1), sector_temp['history'].apply(pd.Series)], axis=1)
    sector_temp["close"] = pd.to_numeric(sector_temp["close"])
    sector_temp2 = sector_temp[['close']]
    sector_temp2.columns = sector_temp.name.unique()
    sector_close = pd.concat([sector_temp2, sector_close], axis=1)
    daterange = sector_close.index
    sector_data = sector_close
res=[]
fig = dict(data = res)
    

#Creating the dash app

layout = html.Div(
        
[
 
    html.Div([
        utils.get_menu(),
        
        #graph
        dcc.Graph(
                id = 'Sector-Graph',
                figure = fig,
        ),
        
        # range slider
        html.P([
            html.Label("Time Period"),
            dcc.RangeSlider(id = 'slider',
                            min = utils.unix_time_millis(daterange.min()),
                            max = utils.unix_time_millis(daterange.max()),
                            value = [utils.unix_time_millis(daterange.min()),
                                     utils.unix_time_millis(daterange.max())],
                            marks= utils.getMarks(daterange.min(),
                                           daterange.max()),
                            tooltip = 'always_visible',
                            ) 
        ], style = {'width' : '80%',
                'fontSize' : '20px',
                'padding-left' : '100px',
                'display': 'inline-block'}
        ),
    
        html.P(),
        html.P(),
        
        #creating dropdown menu
        html.Label('Sectors Dropdown'),
    
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
    ],className="row"),

])   

