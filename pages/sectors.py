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
from pages import utils, layouttab

# Sector URL
urlsec = 'https://cloud.iexapis.com/stable/ref-data/sectors?token=pk_5d82796966de466bb2f966ed65ca70c7'
sectors = pd.read_json(urlsec, orient='columns')
sectors['name']=sectors['name'].str.replace(' ','%20')

#Creating the dash app

layout = html.Div(
        
[
 
    html.Div([
        utils.get_menu(),
        
        html.Button(id='sector-initialize', children='Sector initialize'),

        #graph
        dcc.Graph(
                id = 'Sector-Graph',
        ),
        
        # range slider
        html.P([
            html.Label("Time Period"),
            dcc.RangeSlider(id = 'slider',
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

