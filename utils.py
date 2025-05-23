import finnhub
import json
from datetime import datetime, timedelta

# 替換成您自己的 Finnhub API 金鑰
API_KEY = "d0mplk1r01qi78nge0agd0mplk1r01qi78nge0b0"

# 初始化 Finnhub 客戶端
finnhub_client = finnhub.Client(api_key=API_KEY)

def get_company_news(symbol, from_date, to_date):
    """
    獲取指定公司在特定日期範圍內的新聞。

    :param symbol: 公司股票代碼 (例如 AAPL, MSFT)
    :param from_date: 開始日期 (YYYY-MM-DD)
    :param to_date: 結束日期 (YYYY-MM-DD)
    :return: 新聞列表 (JSON)
    """
    try:
        return finnhub_client.company_news(symbol, from_date, to_date)
    except Exception as e:
        print(f"獲取公司新聞時發生錯誤: {e}")
        return None
