#!/usr/bin/env python3
"""
測試Playwright抓取文章功能
"""
import sys
import time
from playwright.sync_api import sync_playwright
from readability import Document
from bs4 import BeautifulSoup

def handle_press_and_hold(page, selector=None):
    """
    處理需要按住按鈕的反機器人機制
    
    Args:
        page: Playwright page物件
        selector: 需要按住的元素選擇器，如果為None則嘗試自動偵測
    
    Returns:
        是否成功處理
    """
    try:
        # 如果沒有提供選擇器，嘗試幾種常見的選擇器
        if not selector:
            common_selectors = [
                "button:has-text('Press & Hold')",
                "div:has-text('Press & Hold')",
                "[class*='captcha']",
                "[id*='captcha']",
                "[class*='press-hold']",
                "[class*='press']",
                "body" # 如果找不到特定元素，嘗試在body上操作
            ]
            
            # 檢查頁面文本是否包含與按住相關的提示
            page_text = page.content().lower()
            if "press" in page_text and "hold" in page_text:
                print("偵測到可能的press & hold反機器人機制")
                
                # 嘗試找到匹配的元素
                for sel in common_selectors:
                    if page.locator(sel).count() > 0:
                        selector = sel
                        print(f"找到可能的press & hold元素: {selector}")
                        break
            
            # 如果仍然沒有找到元素，使用body
            if not selector:
                selector = "body"
                print("未找到特定的press & hold元素，將在整個頁面上嘗試")
        
        # 獲取元素的位置
        element = page.locator(selector).first
        if not element.is_visible():
            print(f"元素 {selector} 不可見")
            return False
            
        # 獲取元素的中心位置
        bounding_box = element.bounding_box()
        if not bounding_box:
            print("無法獲取元素位置")
            return False
            
        x = bounding_box["x"] + bounding_box["width"] / 2
        y = bounding_box["y"] + bounding_box["height"] / 2
        
        # 模擬按住動作
        print(f"在位置 ({x}, {y}) 開始按住元素")
        page.mouse.move(x, y)
        page.mouse.down()
        
        # 按住5秒
        hold_time = 5
        print(f"按住元素 {hold_time} 秒...")
        time.sleep(hold_time)
        
        # 釋放
        page.mouse.up()
        print("釋放元素")
        
        # 等待頁面可能的變化
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
            print("頁面加載完成")
        except Exception as e:
            print(f"等待頁面加載時出錯: {e}")
        
        return True
    except Exception as e:
        print(f"處理press & hold機制時出錯: {e}")
        return False

def extract_article_with_playwright(url):
    """使用Playwright擷取文章內容"""
    print(f"開始測試Playwright抓取: {url}")
    
    with sync_playwright() as p:
        try:
            # 啟動瀏覽器
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # 設置基本逾時時間
            page.set_default_timeout(10000)
            
            # 訪問URL
            print(f"正在訪問頁面: {url}")
            page.goto(url, wait_until="networkidle")
            
            # 檢查頁面是否重定向
            final_url = page.url
            if final_url != url:
                print(f"頁面已重定向到: {final_url}")
            
            # 檢查是否有press & hold機制
            page_content = page.content().lower()
            if "press" in page_content and "hold" in page_content:
                print("偵測到可能的press & hold反機器人機制，嘗試處理...")
                handle_press_and_hold(page)
            
            # 查找並點擊常見的"接受Cookie"按鈕
            try:
                # 嘗試多種可能的cookie同意按鈕
                selectors = [
                    "button:has-text('Accept')", 
                    "button:has-text('Accept All')",
                    "button:has-text('I Agree')",
                    "button:has-text('Accept Cookies')",
                    "[id*='accept']:visible"
                ]
                
                for selector in selectors:
                    if page.locator(selector).count() > 0:
                        print(f"找到cookie同意按鈕: {selector}")
                        page.locator(selector).first.click()
                        page.wait_for_load_state("networkidle")
                        print("已點擊cookie同意按鈕")
                        break
            except Exception as e:
                print(f"點擊cookie按鈕時出錯: {e}")
            
            # 提取HTML內容
            html_content = page.content()
            
            # 使用readability-lxml解析文章內容
            doc = Document(html_content)
            title = doc.title()
            article_html = doc.summary()
            
            # 使用BeautifulSoup提取純文本
            soup = BeautifulSoup(article_html, 'html.parser')
            article_text = soup.get_text(separator='\n', strip=True)
            
            # 輸出結果
            print("\n===== 文章資訊 =====")
            print(f"URL: {final_url}")
            print(f"標題: {title}")
            print(f"HTML大小: {len(html_content)} 字節")
            print(f"提取後文章大小: {len(article_text)} 字節")
            
            print("\n===== 文章開頭 (前300字) =====")
            print(article_text[:300] + "..." if len(article_text) > 300 else article_text)
            
            # 關閉瀏覽器
            browser.close()
            return True
            
        except Exception as e:
            print(f"錯誤: {e}")
            return False

if __name__ == "__main__":
    # 如果未提供URL，使用預設URL
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://www.cnbc.com/2023/10/27/apple-aapl-earnings-q4-2023.html"
        print(f"未提供URL，使用範例URL: {url}")
    
    extract_article_with_playwright(url) 