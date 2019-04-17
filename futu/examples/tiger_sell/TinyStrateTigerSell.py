# encoding: UTF-8

'''
    实盘策略范例，接口用法见注释及范例代码
'''
from futu import *
from futu.examples.tiny_quant.tiny_quant_frame.TinyStrateBase import *
from futu.examples.tiny_quant.tiny_quant_frame.TinyQuantFrame import *
from time import sleep


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
       self.trade_vol = None
       self.ask_bid_drop_max = None
       self.ref_price_slip_size = None
       self.run_ctx = {}

    def is_ask_bind_price_ok(self, p1, p2):
        return abs(p1 - p2) <= abs(self.ask_bid_drop_max)

    def clear_ctx(self):
        self.run_ctx = {}
        for code in self.symbol_pools:
            code_ctx = {}
            code_ctx['is_trade_short'] = False
            code_ctx['is_trade_close'] = False

            # 定单id
            code_ctx['orderid_short'] = 0
            code_ctx['orderid_close'] = 0

            # 记录下单的分钟时间
            code_ctx['trade_time_short'] = 0
            code_ctx['trade_time_close'] = 0

            # 报价记录
            code_ctx['price_jump_last_minute'] = 0
            code_ctx['price_jump_mid'] = 0
            code_ctx['price_jump_count'] = 0
            code_ctx['price_jump_ref'] = 0
            code_ctx['place_order_errs'] = 0

    def is_place_order_err_limited(self, symbol):
        if symbol not in self.run_ctx.keys():
            return False
        code_ctx = self.run_ctx[symbol]

        if code_ctx['place_order_errs'] >= 10:
            self.log("place_order_err_limited: {}".format(code_ctx['place_order_errs']))
            return True
        return False

    def record_place_order_err(self, symbol):
        if symbol not in self.run_ctx.keys():
            return
        code_ctx = self.run_ctx[symbol]
        code_ctx['place_order_errs'] += 1

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
        print("trade_vol:", self.trade_vol)
        print("ask_bid_drop_max:", self.ask_bid_drop_max)
        print("ref_price_slip_size:", self.ref_price_slip_size)

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

        # 前一分钟的收盘价
        am_data = self.get_kl_min1_am(quote.symbol)
        last_min_close = am_data.close[-2]
        if not last_min_close:
            return

        print('lastprice = {} close[-5,-1] = {} {} {} , {} , {}'.format(quote.lastPrice, \
                                            am_data.close[-5], am_data.close[-4], \
                                            am_data.close[-3], am_data.close[-2], am_data.close[-1]))

        if not quote.lastPrice or not quote.preClosePrice or not time_mins or not quote.askPrice1 or not quote.bidPrice1:
            return

        order_type = OrderType.NORMAL
        fall_price_slip = 0.01 * self.ref_price_slip_size
        if 'HK.' in quote.symbol:
            order_type = OrderType.SPECIAL_LIMIT
            if not quote.askPrice2 or not quote.askPrice1:
                return
            fall_price_slip = abs(quote.askPrice2 - quote.askPrice1) * self.ref_price_slip_size

        # 当前价高于到期值了
        ref_sell_price = (self.price_jump_rate + 1) * quote.preClosePrice
        if quote.lastPrice >= ref_sell_price:
            str_log = 'symbol:{} price:{}'.format(quote.symbol, quote.lastPrice)
            self.log(str_log)

            if quote.lastPrice > code_ctx['price_jump_mid']:
                code_ctx['price_jump_mid'] = quote.lastPrice
                code_ctx['price_jump_last_minute'] = time_mins
                code_ctx['price_jump_ref'] = (code_ctx['price_jump_mid'] + last_min_close) / 2
                # 每次报价创新高，重置计数
                code_ctx['price_jump_count'] = 1

            elif quote.lastPrice < (code_ctx['price_jump_ref'] - fall_price_slip) and time_mins != code_ctx['price_jump_last_minute']:
                code_ctx['price_jump_count'] += 1

            # 上涨达到卖空的设计: 跳了二次以上， 并且处在报价下降的阶段（如果一直上涨，也不会做空)
            if not code_ctx['is_trade_short']:
                str_log = 'price_jump_count:{} quote.bidPrice1:{} price_jump_ref:{}'.format(code_ctx['price_jump_count'], quote.bidPrice1, code_ctx['price_jump_ref'])
                self.log(str_log)
                if code_ctx['price_jump_count'] > 1 and quote.bidPrice1 and \
                    quote.lastPrice <= (code_ctx['price_jump_ref'] - fall_price_slip) and \
                        self.is_ask_bind_price_ok(quote.bidPrice1, quote.lastPrice):

                    ret = RET_ERROR
                    if not self.is_place_order_err_limited(quote.symbol):
                        ret, data = self.sell(quote.bidPrice1, self.trade_vol, quote.symbol, order_type, 0,
                                          self.account_id)
                    str_log = 'sell symbol: {} price:{} vol:{} ret:'.format(quote.symbol, quote.bidPrice1,
                                                                                    self.trade_vol, ret)
                    self.log(str_log)
                    if ret == RET_OK and data['order_id'][0]:
                        code_ctx['is_trade_short'] = True
                        code_ctx['orderid_short'] = data['order_id'][0]
                        code_ctx['trade_time_short'] = time_mins
                        code_ctx['price_sell'] = quote.bidPrice1
                    else:
                        self.record_place_order_err(quote.symbol)

        # 上涨后又下跌平仓， 赚取至少 close_short_rate 的差价
        if (not code_ctx['is_trade_close']) and code_ctx['is_trade_short'] and quote.askPrice1 and \
                code_ctx['price_sell'] and quote.lastPrice <= (1 - self.close_short_rate) * code_ctx['price_sell'] and \
                self.is_ask_bind_price_ok(quote.askPrice1, quote.lastPrice):

            short_vol = self.query_order_filled(code_ctx['orderid_short'])
            if short_vol != 0 and short_vol <= self.trade_vol:
                ret = RET_ERROR
                if not self.is_place_order_err_limited(quote.symbol):
                    ret, data = self.buy(quote.askPrice1, short_vol, quote.symbol, order_type, 0, self.account_id)
                str_log = 'buy symbol:{} last_price:{} buy_price:{} vol:{} ret:{}'.format(quote.symbol, quote.lastPrice,
                                                                                     quote.askPrice1, short_vol, ret)
                self.log(str_log)
                if ret == RET_OK and data['order_id'][0]:
                    code_ctx['is_trade_close'] = True
                    code_ctx['orderid_close'] = data['order_id'][0]
                    code_ctx['trade_time_close'] = time_mins
                else:
                    self.record_place_order_err(quote.symbol)

    def on_bar_min1(self, tiny_bar):
        """每一分钟触发一次回调, 如果订单不能在下一分钟内成交，就取消掉"""
        for code in self.run_ctx.keys():
            code_ctx = self.run_ctx[code]
            quote = self.get_rt_tiny_quote(code)
            if quote is None or quote.datetime is None:
                continue
            time_mins = quote.datetime.hour * 60 + quote.datetime.minute

            if code_ctx['trade_time_short'] != time_mins and code_ctx['is_trade_short']:
                self.cancel_order_if_not_finish(code_ctx['orderid_short'])

            if code_ctx['trade_time_close'] != time_mins and code_ctx['is_trade_close']:
                self.cancel_order_if_not_finish(code_ctx['orderid_close'])

    def cancel_order_if_not_finish(self, order_id):
        """如果order_id没有成交， 就立即cancel"""

        for x in range(3):
            order = self.get_tiny_trade_order(order_id)
            if order is None:
                return False

            if order.order_status == OrderStatus.FILLED_ALL or order.order_status == OrderStatus.TIMEOUT or \
                    order.order_status == OrderStatus.FAILED:
                return False
            if order.order_status == OrderStatus.CANCELLED_ALL or order.order_status == OrderStatus.CANCELLED_PART:
                return True

            self.cancel_order(order_id)
            sleep(0.1)

        return False

    def query_order_filled(self, order_id):
        order = self.get_tiny_trade_order(order_id)
        if order is None:
            return 0

        if order.order_status == OrderStatus.FILLED_ALL or order.order_status == OrderStatus.CANCELLED_PART or \
                order.order_status == OrderStatus.FILLED_PART:
            return order.trade_volume
        return 0


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

