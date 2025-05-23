#!/usr/bin/env python3
"""
測試newspaper3k抓取文章功能
"""
from newspaper import Article
import sys

def extract_article(url):
    """使用newspaper3k擷取文章內容"""
    try:
        # 建立Article物件
        article = Article(url)
        
        # 下載和解析文章
        article.download()
        article.parse()
        
        # 自然語言處理 (摘要和關鍵字)
        article.nlp()
        
        # 輸出結果
        print(f"\n===== 文章資訊 =====")
        print(f"URL: {url}")
        print(f"標題: {article.title}")
        print(f"發布日期: {article.publish_date}")
        print(f"作者: {', '.join(article.authors) if article.authors else '未知'}")
        
        print(f"\n===== 關鍵字 =====")
        print(', '.join(article.keywords) if article.keywords else '無關鍵字')
        
        print(f"\n===== 摘要 =====")
        print(article.summary)
        
        print(f"\n===== 正文 (前500字) =====")
        print(article.text)
        
        return True
    except Exception as e:
        print(f"錯誤: {e}")
        return False

if __name__ == "__main__":
    # 如果沒有提供URL，則使用範例URL
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://finance.yahoo.com/video/amazon-apple-earnings-coverage-eli-230052060.html"
        print(f"未提供URL，使用範例URL: {url}")
    
    extract_article(url) 