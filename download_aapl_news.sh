#!/bin/bash

# 運行 crawl_50.py 獲取 AAPL 新聞並下載內容
python crawl_50.py --type company --symbol AAPL --from-date 2023-04-01 --to-date 2023-04-30 --download-articles --output-dir ./aapl_news_articles

echo "腳本執行完畢。" 