import datetime

from supplementary import get_year_month, MonthPartitionedTrades, \
    TradeAction, TradeActionsPerCompany, TradeType, CapitalGainLine, TradesWithinMonth

currency = "USD"
test_symbol = "BTU"
buy_date = "2021-05-18, 14:53:23"
buy_quantity = "15"
buy_price = "6.77"
buy_fee = "-0.36225725"
buy_action1 = TradeAction(test_symbol, buy_date, currency, buy_quantity, buy_price, buy_fee)

sell_date1 = "2021-06-03, 11:44:04"
sell_quantity1 = "-10"
sell_price1 = "7.875"
sell_fee1 = "-0.353848875"
sell_action1 = TradeAction(test_symbol, sell_date1, currency, sell_quantity1, sell_price1, sell_fee1)

sell_date2 = "2021-10-04, 09:44:11"
sell_quantity2 = "-5"
sell_price2 = "17.36"
sell_fee2 = "-0.35229493"
sell_action2 = TradeAction(test_symbol, sell_date2, currency, sell_quantity2, sell_price2, sell_fee2)

simple_trade: TradeActionsPerCompany = {test_symbol: {
    TradeType.BUY: [(int(buy_quantity), buy_action1)],
    TradeType.SELL: [(abs(int(sell_quantity1)), sell_action1), (abs(int(sell_quantity2)), sell_action2)]
}}

line1 = CapitalGainLine(test_symbol, currency)
line1.add_trade(10, buy_action1)
line1.add_trade(10, sell_action1)
line1.validate()

line2 = CapitalGainLine(test_symbol, currency)
line2.add_trade(5, buy_action1)
line2.add_trade(5, sell_action2)
line2.validate()
capitalGainLinesPerCompany = {"BTU": [line1, line2]}
