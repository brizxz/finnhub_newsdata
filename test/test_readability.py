#!/usr/bin/env python3
"""
測試readability-lxml抓取文章功能
"""
import requests
from readability import Document
from bs4 import BeautifulSoup
import sys

def extract_article(url):
    """使用readability-lxml擷取文章內容"""
    try:
        # 發送HTTP請求獲取網頁內容
        headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.7103.25 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 使用readability-lxml解析文章內容
        doc = Document(response.text)
        
        # 提取標題和主要內容
        title = doc.title()
        content = doc.summary()
        
        # 使用BeautifulSoup清理HTML標籤獲取純文本
        soup = BeautifulSoup(content, 'html.parser')
        article_text = soup.get_text()
        
        # 清理文字
        lines = (line.strip() for line in article_text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        article_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # 輸出結果
        print(f"\n===== 文章資訊 =====")
        print(f"URL: {url}")
        print(f"標題: {title}")
        
        print(f"\n===== 正文 (前500字) =====")
        print(article_text)
        
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