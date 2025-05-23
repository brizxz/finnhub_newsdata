# import finnhub

# finnhub_client = finnhub.Client(api_key='d0lt541r01qpni3183d0d0lt541r01qpni3183dg')
# symbols = finnhub_client.stock_symbols('US')

# print(len(symbols))
# # 顯示前10個支援的股票代碼
# for symbol in symbols[:10]:
#     print(f"{symbol['symbol']} - {symbol['description']}")

import finnhub
finnhub_client = finnhub.Client(api_key="d0lt541r01qpni3183d0d0lt541r01qpni3183dg")

print(finnhub_client.stock_symbols('US'))