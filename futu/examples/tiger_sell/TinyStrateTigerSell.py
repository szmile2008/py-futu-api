# encoding: UTF-8

'''
    实盘策略范例，接口用法见注释及范例代码
'''
from futu.examples.tiny_quant.tiny_quant_frame.TinyStrateBase import *
from futu.examples.tiny_quant.tiny_quant_frame.TinyQuantFrame import *


class TinyStrateTigerSell(TinyStrateBase):
    """策略名称, setting.json中作为该策略配置的key"""
    name = 'TinyStrateTigerSell'

    """策略需要用到行情数据的股票池"""
    symbol_pools = []

    def __init__(self):
       super(TinyStrateTigerSell, self).__init__()

       """请在setting.json中配置参数"""
       self.all_code = None
       self.account_id = None
       self.price_jump_rate = None
       self.close_short_rate = None
       self.num_short = None
       self.ask_bid_drop_max = 0
       self.run_ctx = {}

    def is_ask_bind_price_ok(self, p1, p2):
        return abs(p1 - p2) < abs(self.ask_bid_drop_max)

    def clear_ctx(self):
        self.run_ctx = {}
        for code in self.symbol_pools:
            code_ctx = {}
            code_ctx['is_trade_short'] = False
            code_ctx['is_trade_close'] = False
            code_ctx['price_jump_last_minute'] = 0
            code_ctx['price_jump_mid'] = 0
            code_ctx['price_jump_count'] = 0

            self.run_ctx[code] = code_ctx

    def on_init_strate(self):
        """策略加载完配置后的回调
        1. 可修改symbol_pools 或策略内部其它变量的初始化
        2. 此时还不能调用futu api的接口
        """
        self.symbol_pools = list(self.all_code)
        print("all_code:", self.all_code)
        print("account_id:", self.account_id)
        print("price_jump_rate:", self.price_jump_rate)
        print("close_short_rate:", self.close_short_rate)
        print("num_short:", self.num_short)

        self.clear_ctx()
        print(self.run_ctx)

    def on_start(self):
        """策略启动完成后的回调
        1. 框架已经完成初始化， 可调用任意的futu api接口
        2. 修改symbol_pools无效, 不会有动态的行情数据回调
        """
        pass

    def on_quote_changed(self, tiny_quote):
        """报价、摆盘实时数据变化时，会触发该回调"""
        # TinyQuoteData
        quote = tiny_quote
        code_ctx = self.run_ctx[quote.symbol]
        time_mins = 0
        if quote.datetime is not None:
            time_mins = quote.datetime.hour * 60 + quote.datetime.minute

        if not quote.lastPrice or not quote.preClosePrice:
            return

        # 当前价高于到期值了
        ref_sell_price = (self.price_jump_rate + 1) * quote.preClosePrice
        if quote.lastPrice >= ref_sell_price and time_mins:
            self.log(str(quote.lastPrice))
            if quote.lastPrice > code_ctx['price_jump_mid']:
                code_ctx['price_jump_mid'] = quote.lastPrice
                code_ctx['price_jump_last_minute'] = time_mins
                if code_ctx['price_jump_count'] == 0:
                    code_ctx['price_jump_count'] = 1
            elif quote.lastPrice < code_ctx['price_jump_mid'] and time_mins != code_ctx['price_jump_last_minute']:
                code_ctx['price_jump_count'] += 1

            #上涨达到卖空的设计
            if (not code_ctx['is_trade_short']) and code_ctx['price_jump_count'] > 1 and quote.bidPrice1 and \
                    self.is_ask_bind_price_ok(quote.bidPrice1, quote.lastPrice):
                code_ctx['is_trade_short'] = True
                code_ctx['price_sell'] = quote.bidPrice1
                self.sell(quote.bidPrice1, self.num_short, quote.symbol, OrderType.NORMAL, 0, self.account_id)

        #上涨后又下跌可购回
        if (not code_ctx['is_trade_close']) and code_ctx['is_trade_short'] and quote.askPrice1 and \
                code_ctx['price_sell'] and quote.lastPrice <= (1 - self.close_short_rate) * code_ctx['price_sell'] and \
                self.is_ask_bind_price_ok(quote.askPrice1, quote.lastPrice):
            code_ctx['is_trade_close'] = True
            self.buy(quote.askPrice1, self.num_short, quote.symbol, OrderType.NORMAL, 0, self.account_id)


    def on_bar_min1(self, tiny_bar):
        """每一分钟触发一次回调"""
        pass

    def on_bar_day(self, tiny_bar):
        """收盘时会触发一次日k回调"""
        pass

    def on_before_trading(self, date_time):
        """开盘时触发一次回调, 脚本挂机切换交易日时，港股会在09:30:00回调"""
        str_log = "on_before_trading - %s" % date_time.strftime('%Y-%m-%d %H:%M:%S')
        self.log(str_log)
        self.clear_ctx()

    def on_after_trading(self, date_time):
        """收盘时触发一次回调, 脚本挂机时，港股会在16:00:00回调"""
        str_log = "on_after_trading - %s" % date_time.strftime('%Y-%m-%d %H:%M:%S')
        self.log(str_log)


if __name__ == '__main__':
    my_strate = TinyStrateTigerSell()
    frame = TinyQuantFrame(my_strate)
    frame.run()

