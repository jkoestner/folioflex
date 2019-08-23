import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import dash_table
from dash.dependencies import Input, Output, State


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

quote_col = ['symbol',
            'companyName',
            'isUSMarketOpen',
            'latestPrice',
            'previousClose',
            'latestUpdate',
            'latestSource',
            'change',
            'changePercent',
            'ytdChange',
            'latestVolume',
            'avgTotalVolume',
            'previousVolume',
            'marketCap',
            'peRatio',
            'extendedPrice',
            'extendedPriceTime',
            'open',
            'close',
            'high',
            'low',
            'week52High',
            'week52Low',]

formatter_quote = {'avgTotalVolume':'{:,.2f}'.format,
                    'change':'{:,.2f}'.format,
                    'close':'{:,.2f}'.format,
                    'delayedPrice':'{:,.2f}'.format,
                    'delayedPriceTime':'{:,.2f}'.format,
                    'extendedChange':'{:,.2f}'.format,
                    'extendedChangePercent':'{:,.2f}'.format,
                    'extendedPrice':'{:,.2f}'.format,
                    'high':'{:,.2f}'.format,
                    'iexAskPrice':'{:,.2f}'.format,
                    'iexAskSize':'{:,.2f}'.format,
                    'iexBidPrice':'{:,.2f}'.format,
                    'iexBidSize':'{:,.2f}'.format,
                    'iexRealtimePrice':'{:,.2f}'.format,
                    'iexRealtimeSize':'{:,.2f}'.format,
                    'iexVolume':'{:,.2f}'.format,
                    'latestPrice':'{:,.2f}'.format,
                    'latestVolume':'{:,.2f}'.format,
                    'low':'{:,.2f}'.format,
                    'marketCap':'{:,.2f}'.format,
                    'open':'{:,.2f}'.format,
                    'openTime':'{:,.2f}'.format,
                    'peRatio':'{:,.2f}'.format,
                    'previousClose':'{:,.2f}'.format,
                    'previousVolume':'{:,.2f}'.format,
                    'volume':'{:,.2f}'.format,
                    'week52High':'{:,.2f}'.format,
                    'week52Low':'{:,.2f}'.format,
                    'changePercent':'{0:.2%}'.format,
                    'ytdChange':'{0:.2%}'.format,}

sector_list = ['XLF', 'XLU', 'XLV', 'RWR']
               #, 'XLV', 'RWR', 'XLK', 'XLY', 'XLP', 'XLB', 'XLI', 'IYT']
