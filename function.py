import pandas as pd
from pages import stocks, layouttab, sectors, utils
import time

def Query():
    global sector_close
    sector_close=pd.DataFrame([])
    for i in layouttab.sector_list:
        urlsec_data='https://api.worldtradingdata.com/api/v1/history?symbol=' + format(i) + '&sort=newest&api_token=aB0PKnbqXhFuYJtXmOvasDHf2M82BCY3PI9N9o4kb0UHwf5zVckMnD0PL2hc'
        sector_temp = pd.read_json(urlsec_data, orient='columns')
        sector_temp = pd.concat([sector_temp.drop(['history'], axis=1), sector_temp['history'].apply(pd.Series)], axis=1)
        sector_temp["close"] = pd.to_numeric(sector_temp["close"])
        sector_temp2 = sector_temp[['close']]
        sector_temp2.columns = sector_temp.name.unique()
        sector_close = pd.concat([sector_temp2, sector_close], axis=1)
        time.sleep(12)
              
    return sector_close