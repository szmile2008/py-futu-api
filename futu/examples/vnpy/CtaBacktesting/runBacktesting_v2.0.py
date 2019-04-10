# encoding: UTF-8

"""
展示如何执行策略回测。
"""
from vnpy.trader.app.ctaStrategy.backtesting import BacktestingEngine
from .double_ma_strategy import DoubleMaStrategy


if __name__ == '__main__':

    # 创建回测引擎
    engine = BacktestingEngine()
    setting = {}
    engine.set_parameters(
        vt_symbol='00700.SEHK',
        interval='1m',
        start='20170101',
        rate=1/10000,
        slippage=0.2,
        size=100,
        pricetick=0.2,
        capital=100000,
        end='20190601',
        mode=BacktestingMode.BAR
    )

    # 在引擎中创建策略对象
    d = {}
    engine.add_strategy(DoubleMaStrategy, setting)
    engine.load_data()
    engine.run_backtesting()
    engine.calculate_result()
    
    # 显示回测结果
    engine.show_chart()