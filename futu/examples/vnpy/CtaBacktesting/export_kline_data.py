from futu import *
from time import sleep
import datetime
import pandas as pd

EXPORT_STOCK_CODE = 'HK.00700'
HOST = '127.0.0.1'
PORT = 11111


def export_stock_kline(stock_code, host, port, kltype=KLType.K_1M, file_path=None):
    quote_ctx = OpenQuoteContext(host, port)

    page_key = None
    all_data = None
    try_max = 100
    try_count = 0
    start_year = datetime.datetime.now().year
    end_year = start_year

    if kltype == KLType.K_DAY:
        start_year -= 10
    else:
        start_year -= 1

    start_time = u'{}-01-01 0:0:0'.format(start_year)
    end_time = u'{}-12-31 23:59:59'.format(end_year)

    while True:
        if try_count >= try_max:
            break
        ret, data, page_key = quote_ctx.request_history_kline(stock_code, start_time, end_time, kltype,
                                                AuType.QFQ, [KL_FIELD.DATE_TIME, KL_FIELD.OPEN, KL_FIELD.HIGH,
                                                KL_FIELD.LOW, KL_FIELD.CLOSE, KL_FIELD.TRADE_VOL], 1000, page_key)
        if ret == RET_OK:
            if all_data is not None:
                all_data = pd.concat([all_data, data], ignore_index=True)
            else:
                all_data = data
        else:
            try_count += 1
            sleep(1)

        if not page_key:
            break

    all_data.rename(columns={'time_key': 'Datetime', 'open': 'Open', 'high': 'High', 'low': 'Low',
                               'close': 'Close', 'vol': 'Volume'}, inplace=True)
    all_data.rename(columns={'volume': 'Volume'}, inplace=True)
    all_data.drop(['code'], axis=1, inplace=True)

    if file_path is None:
        file_path = 'export_' + stock_code + '_' + kltype + '.csv'

    all_data.to_csv(file_path, index=False)

    print('export to file:{}  total:{}'.format(file_path, len(all_data)))
    quote_ctx.close()


if __name__ == "__main__":
    # export_stock_kline(EXPORT_STOCK_CODE, HOST, PORT, KLType.K_1M)
    export_stock_kline('US.AAPL', HOST, PORT, KLType.K_1M)
