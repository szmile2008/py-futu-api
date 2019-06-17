from futu import *
from time import sleep
import datetime
import pandas as pd
from tigeropen.common.consts import *
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.quote.quote_client import QuoteClient

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


def get_tiger_client_config(sandbox=False):
    """
    https://www.itiger.com/openapi/info 开发者信息获取
    :return:
    """
    client_config = TigerOpenClientConfig(sandbox_debug=sandbox)
    client_config.private_key = read_private_key('c:/rsa_private_key.pem')  # read_private_key('填写私钥文件的路径')
    client_config.tiger_id = '20150277'
    client_config.account = 'U10192539'
    client_config.standard_account = None
    client_config.paper_account = '20190424102103233'  # 模拟账户
    client_config.language = Language.zh_CN
    return client_config


import datetime as dt


def export_tiger_kline(kltype=BarPeriod.DAY):
    client_config = get_tiger_client_config()
    quote_client = QuoteClient(client_config)

    stock = ['00700']
    init_year = 2000
    limit_bars = 1000
    for year in range(init_year, 2020, 1):
        start = dt.datetime(year, 1, 1, 0, 0, 0)
        end = dt.datetime(year, 12, 31, 23, 59, 59)
        bars = quote_client.get_bars(stock, period=kltype, begin_time=int(start.timestamp()) * 1000, end_time=int(end.timestamp()) * 1000, limit=limit_bars)
        # sleep(1)
        if bars is not None and len(bars):
            end = int(bars.iloc[0:1]['time'])
            print(bars)
            print(end)
            print(year)
            d1 = dt.datetime.now().timestamp()
            dt_start = d1
            req_count = 1
            try:
                while True:
                    bars = quote_client.get_bars(stock, period=kltype, begin_time=int(start.timestamp()) * 1000,
                                                 end_time=end, limit=limit_bars)
                    req_count += 1
                    d2 = dt.datetime.now().timestamp()
                    dt_sec = d2 - d1
                    d1 = d2
                    print('time:{}'.format(dt_sec))
                    print('-----------------------------------------------')
                    sleep(0.2)
            except Exception as e:
                rate_speed = req_count / (d1 - dt_start)
                print(e)
                print('req count: {}, speed rate: {}/s'.format(req_count, rate_speed))

            print(bars)
            break

if __name__ == "__main__":
    # export_stock_kline(EXPORT_STOCK_CODE, HOST, PORT, KLType.K_1M)
    # export_stock_kline('US.AAPL', HOST, PORT, KLType.K_1M)

    export_tiger_kline(BarPeriod.ONE_MINUTE)
