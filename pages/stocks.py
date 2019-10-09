import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import dash_table
import datetime
from dash.dependencies import Input, Output, State
from pages import utils

#Creating the dash app

layout = html.Div(
        
[
 
    html.Div([
        utils.get_menu(),
        
        html.Label('Stock Analysis'),
        html.P(),  
        
        dcc.Input(id='stock-input', placeholder='Enter Stock...', type='text'),
        
        html.Button(id='stock-button', children='Stock Submit'),
               
        html.Button(id='quote-button', children='Quote Submit'),
        
        html.Button(id='peer-button', children='Peer Submit'),
        
        html.Button(id='news-button', children='News Submit'),
        
        html.Button(id='active-button', children='Active Submit'),
        
        html.Button(id='sentiment-button', children='Sentiment Submit'),
    ],className="row"),

    html.Div([
        
        dcc.DatePickerSingle(id='date-input', initial_visible_month=datetime.date.today(), date=datetime.date.today()),

    ],className="row"),


    html.Div([
            
        html.Div([
            #creating stock information        
            dash_table.DataTable(
            id='stock-table',
            page_action="native",
            ),
                    
        ], className="three columns"),
                    
        html.Div([
            #creating quote information        
            dash_table.DataTable(
            id='quote-table',
            page_action="native",
            ),
                    
        ], className="three columns"),
        
        html.Div([
            #creating peer information                  
            html.P(),             
            dash_table.DataTable(
            id='peer-table',
            page_action="native",
            ),
        ], className="three columns"),
                                        
    ],className="row"),

    html.Div([    
                    
        html.Div([
            #creating sentiment information                  
            html.P(),             
            dash_table.DataTable(
            id='sentiment-table',
            sort_action="native",
            ),
        ], className="three columns"),
                    
    ],className="row"),
                    
    html.Div([    
                    
        html.Div([
            #creating active information                  
            html.P(),             
            dash_table.DataTable(
            id='active-table',
            page_action="native",
            sort_action="native",
            ),
        ], className="three columns"),
                    
    ],className="row"),
                    
    html.Div([
            
        html.Div([
            #creating news information                  
            html.P(),             
            dash_table.DataTable(
            id='news-table',
            page_action="native",
            ),
        ], className="three columns"),
                    
    ],className="row"),

])   

