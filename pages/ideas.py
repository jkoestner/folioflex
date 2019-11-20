import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import dash_table
from dash.dependencies import Input, Output, State
from pages import utils

#Creating the dash app

layout = html.Div(
        
[
 
    html.Div([
        utils.get_menu(),
        
        dcc.Markdown('''
        Momentum and Value are 2 metrics that determine the viability of investing in the market.
                     
        **12 mo Moving Average** - current price of market is greater than the 12 month moving average.
                   
        **12 mo TMOM** - 12 month return is greater than the return of the 10 year treasury bond
        '''),
                     
        html.P(),  
        
        dcc.Input(id='idea-input', placeholder='Enter Stock...', type='text'),
        
        html.Button(id='sma-button', children='SMA Submit'),
               
    ],className="row"),

    html.Div([
            
        html.Div([
            #simple moving average 
            dcc.Markdown("Simple Moving Average="),
            html.Div(id='sma-value'),
                    
        ], className="three columns"),
                    
                                        
    ],className="row"),
                    
])   

