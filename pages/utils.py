import dash_html_components as html
import dash_core_components as dcc
import datetime
from dateutil.relativedelta import relativedelta



def Header(app):
    return html.Div([get_header(app), html.Br([]), get_menu()])


def get_header(app):
    header = html.Div(
        [
            html.Div(
                [
                    html.Img(
                        src=app.get_asset_url("dash-financial-logo.png"),
                        className="logo",
                    ),
                    html.A(
                        html.Button("Learn More", id="learn-more-button"),
                        href="https://plot.ly/dash/pricing/",
                    ),
                ],
                className="row",
            ),
            html.Div(
                [
                    html.Div(
                        [html.H5("Calibre Financial Index Fund Investor Shares")],
                        className="seven columns main-title",
                    ),
                    html.Div(
                        [
                            dcc.Link(
                                "Full View",
                                href="/dash-financial-report/full-view",
                                className="full-view-link",
                            )
                        ],
                        className="five columns",
                    ),
                ],
                className="twelve columns",
                style={"padding-left": "0"},
            ),
        ],
        className="row",
    )
    return header


def get_menu():
    menu = html.Div(
        [
            dcc.Link(
                "Stocks   ",
                href="/stocks",
            ),
                
            dcc.Link(
                "Sectors   ",
                href="/sectors",
                style={'padding': 10},
            ),
            
            dcc.Link(
                "Ideas   ",
                href="/ideas",
                style={'padding': 10},
            ),

            dcc.Link(
                "Macro   ",
                href="/macro",
                style={'padding': 10},
            ),

            dcc.Link(
                "Tracker   ",
                href="/tracker",
                style={'padding': 10},
            ),
        ])
    return menu


def make_dash_table(df):
    """ Return a dash definition of an HTML table for a Pandas dataframe """
    table = []
    for index, row in df.iterrows():
        html_row = []
        for i in range(len(row)):
            html_row.append(html.Td([row[i]]))
        table.append(html.Tr(html_row))
    return table



def unix_time_millis(dt):
    epoch = datetime.datetime.utcfromtimestamp(0)
    return (dt - epoch).total_seconds()

def unixToDatetime(unix):
    ''' Convert unix timestamp to datetime. '''
    return pd.to_datetime(unix,unit='s')

def getMarks(start, end, Nth=365):
    ''' Returns the marks for labeling. 
        Every Nth value will be used.
    '''
    result = []
    current = start
    while current <= end:
        result.append(current)
        current += relativedelta(years=1)
    return {int(unix_time_millis(date)):(str(date.strftime('%Y-%m'))) for date in result}
