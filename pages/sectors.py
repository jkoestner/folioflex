import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import dash_table
from dash.dependencies import Input, Output, State
import app
from pages import utils

# Sector URL
urlsec = 'https://cloud.iexapis.com/stable/ref-data/sectors?token=pk_5d82796966de466bb2f966ed65ca70c7'
sectors = pd.read_json(urlsec, orient='columns')
sectors['name']=sectors['name'].str.replace(' ','%20')
#Creating the dash app

layout = html.Div(
        
[
 
    html.Div([
        utils.get_menu(),
        
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

