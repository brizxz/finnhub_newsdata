from utils import get_company_news, finnhub_client, API_KEY
import argparse
from datetime import datetime, timedelta

def display_company_news(symbol, from_date=None, to_date=None):
    """
    取得並顯示特定公司的新聞
    
    Args:
        symbol: 公司股票代碼
        from_date: 起始日期 (YYYY-MM-DD格式)
        to_date: 結束日期 (YYYY-MM-DD格式)
    """
    # 如果未指定日期範圍，預設為過去一週
    if from_date is None or to_date is None:
        today = datetime.now()
        one_week_ago = today - timedelta(days=7)
        from_date = from_date or one_week_ago.strftime('%Y-%m-%d')
        to_date = to_date or today.strftime('%Y-%m-%d')
    
    print(f"\n--- 正在獲取 {symbol} 從 {from_date} 到 {to_date} 的公司新聞 ---")
    company_news = get_company_news(symbol, from_date, to_date)
    
    if company_news:
        print(f"共獲取 {len(company_news)} 條新聞。")
        # 只顯示前 3 條新聞的標題和來源
        for i, news_item in enumerate(company_news[:3]):
            news_datetime = datetime.fromtimestamp(news_item.get('datetime')).strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n新聞 {i+1}:")
            print(f"  標題 (Headline): {news_item.get('headline')}")
            print(f"  來源 (Source): {news_item.get('source')}")
            print(f"  發布時間 (Datetime): {news_datetime}")
            print(f"  URL: {news_item.get('url')}")
    else:
        print("未能獲取公司新聞，或該時段內無新聞。")
    
    return company_news

def get_market_news(category="general", min_id=0):
    """
    獲取一般市場新聞。

    :param category: 新聞類別 (例如 general, forex, crypto, merger)
    :param min_id: (用於分頁) 只獲取 ID 大於 min_id 的新聞
    :return: 新聞列表 (JSON)
    """
    try:
        return finnhub_client.general_news(category=category)
    except Exception as e:
        print(f"獲取市場新聞時發生錯誤: {e}")
        return None

def display_market_news(category="general", min_id=0):
    """顯示市場新聞"""
    print(f"\n--- 正在獲取{category}市場新聞 ---")
    market_news_data = get_market_news(category=category, min_id=min_id)
    
    if market_news_data:
        print(f"共獲取 {len(market_news_data)} 條市場新聞。")
        for i, news_item in enumerate(market_news_data[:3]): # 只顯示前3條
            news_datetime = datetime.fromtimestamp(news_item.get('datetime')).strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n市場新聞 {i+1}:")
            print(f"  標題: {news_item.get('headline')}")
            print(f"  來源: {news_item.get('source')}")
            print(f"  發布時間: {news_datetime}")
    else:
        print("未能獲取市場新聞。")
    
    return market_news_data

def parse_args():
    """解析命令列參數"""
    parser = argparse.ArgumentParser(description='獲取金融新聞')
    parser.add_argument('--type', type=str, choices=['company', 'market'], default='company',
                      help='新聞類型: company (公司新聞) 或 market (市場新聞)')
    parser.add_argument('--symbol', type=str, default='AAPL',
                      help='公司股票代碼 (預設: AAPL)')
    parser.add_argument('--from-date', type=str,
                      help='起始日期 (YYYY-MM-DD格式，預設: 一週前)')
    parser.add_argument('--to-date', type=str,
                      help='結束日期 (YYYY-MM-DD格式，預設: 今天)')
    parser.add_argument('--category', type=str, default='general',
                      choices=['general', 'forex', 'crypto', 'merger'],
                      help='市場新聞類別 (預設: general)')
    parser.add_argument('--min-id', type=int, default=0,
                      help='市場新聞最小ID (用於分頁，預設: 0)')
    return parser.parse_args()

# --- 使用範例 ---
if __name__ == "__main__":
    if API_KEY == "YOUR_FINNHUB_API_KEY":
        print("請先在程式碼中設定您的 API_KEY")
    else:
        # 解析命令列參數
        args = parse_args()
        
        # 根據新聞類型調用相應的函式
        if args.type == 'company':
            display_company_news(args.symbol, args.from_date, args.to_date)
        else:  # market news
            display_market_news(args.category, args.min_id)