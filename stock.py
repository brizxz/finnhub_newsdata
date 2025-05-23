from utils import finnhub_client, API_KEY
import argparse
from datetime import datetime, timedelta

def get_stock_quote(symbol):
    """
    獲取指定股票的即時報價。

    :param symbol: 公司股票代碼
    :return: 報價數據 (JSON)
    """
    try:
        return finnhub_client.quote(symbol)
    except Exception as e:
        print(f"獲取股票報價時發生錯誤: {e}")
        return None

def get_stock_candles(symbol, resolution, from_timestamp, to_timestamp):
    """
    獲取指定股票的 K 線數據。

    :param symbol: 公司股票代碼
    :param resolution: 解析度/時間間隔 (例如 'D' 日線, 'W' 週線, 'M' 月線, '1', '5', '15', '30', '60' 分鐘線)
    :param from_timestamp: 開始時間的 UNIX 時間戳
    :param to_timestamp: 結束時間的 UNIX 時間戳
    :return: K 線數據 (JSON)
    """
    try:
        return finnhub_client.stock_candles(symbol, resolution, from_timestamp, to_timestamp)
    except Exception as e:
        print(f"獲取股票K線數據時發生錯誤: {e}")
        return None

def display_stock_quote(symbol):
    """顯示股票即時報價"""
    print(f"\n--- 正在獲取 {symbol} 的即時報價 ---")
    quote_data = get_stock_quote(symbol)
    if quote_data:
        print(f"  目前價格 (Current Price, c): {quote_data.get('c')}")
        print(f"  今日最高價 (High Price, h): {quote_data.get('h')}")
        print(f"  今日最低價 (Low Price, l): {quote_data.get('l')}")
        print(f"  今日開盤價 (Open Price, o): {quote_data.get('o')}")
        print(f"  昨日收盤價 (Previous Close, pc): {quote_data.get('pc')}")
        if 't' in quote_data:
            quote_time = datetime.fromtimestamp(quote_data.get('t')).strftime('%Y-%m-%d %H:%M:%S')
            print(f"  報價時間 (Timestamp, t): {quote_time}")
    else:
        print("未能獲取股票報價。")

def display_stock_candles(symbol, resolution, days):
    """顯示股票K線數據"""
    to_ts = int(datetime.now().timestamp())
    from_ts = int((datetime.now() - timedelta(days=days)).timestamp())

    print(f"\n--- 正在獲取 {symbol} 過去{days}天的{resolution}線數據 ---")
    candle_data = get_stock_candles(symbol, resolution, from_ts, to_ts)

    if candle_data and candle_data.get('s') == 'ok':
        print(f"成功獲取 K 線數據。資料點數: {len(candle_data.get('t', []))}")
        num_points_to_show = 3
        if len(candle_data.get('t', [])) >= num_points_to_show:
            print(f"顯示最近 {num_points_to_show} 筆數據:")
            for i in range(-num_points_to_show, 0):
                dt_object = datetime.fromtimestamp(candle_data['t'][i])
                print(f"  日期: {dt_object.strftime('%Y-%m-%d')}, "
                      f"開: {candle_data['o'][i]}, 高: {candle_data['h'][i]}, "
                      f"低: {candle_data['l'][i]}, 收: {candle_data['c'][i]}, "
                      f"量: {candle_data['v'][i]}")
        elif len(candle_data.get('t', [])) > 0:
            print("數據不足3筆，顯示所有獲取到的數據。")
            for i in range(len(candle_data['t'])):
                dt_object = datetime.fromtimestamp(candle_data['t'][i])
                print(f"  日期: {dt_object.strftime('%Y-%m-%d')}, "
                      f"開: {candle_data['o'][i]}, 高: {candle_data['h'][i]}, "
                      f"低: {candle_data['l'][i]}, 收: {candle_data['c'][i]}, "
                      f"量: {candle_data['v'][i]}")
    elif candle_data and candle_data.get('s') != 'ok':
        print(f"獲取 K 線數據時發生錯誤或無數據: {candle_data.get('s')}")
    else:
        print("未能獲取 K 線數據。")

def parse_args():
    """解析命令列參數"""
    parser = argparse.ArgumentParser(description='獲取股票數據')
    parser.add_argument('--type', type=str, choices=['quote', 'candle'], default='quote',
                      help='數據類型: quote (即時報價) 或 candle (K線數據)')
    parser.add_argument('--symbol', type=str, default='AAPL',
                      help='公司股票代碼 (預設: AAPL)')
    parser.add_argument('--resolution', type=str, default='D',
                      choices=['1', '5', '15', '30', '60', 'D', 'W', 'M'],
                      help='K線時間間隔 (預設: D)')
    parser.add_argument('--days', type=int, default=30,
                      help='要獲取的天數 (預設: 30)')
    return parser.parse_args()

# --- 使用範例 ---
if __name__ == "__main__":
    if API_KEY == "YOUR_FINNHUB_API_KEY":
        print("請先在程式碼中設定您的 API_KEY")
    else:
        # 解析命令列參數
        args = parse_args()
        
        # 根據數據類型調用相應的函式
        if args.type == 'quote':
            display_stock_quote(args.symbol)
        else:  # candle
            display_stock_candles(args.symbol, args.resolution, args.days)