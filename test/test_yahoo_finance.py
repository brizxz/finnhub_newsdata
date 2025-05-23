#!/usr/bin/env python3
"""
專門測試Yahoo Finance新聞頁面上的"Continue Reading"按鈕處理
"""
import sys
import argparse
import time
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def test_yahoo_finance_requests(url):
    """使用requests方法測試Yahoo Finance新聞頁面上的Continue Reading按鈕"""
    print(f"使用requests方法測試: {url}")
    
    try:
        # 設置headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5,zh-TW;q=0.3',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # 使用session保持cookie
        session = requests.Session()
        session.headers.update(headers)
        
        # 請求頁面
        response = session.get(url, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        print(f"請求成功: {response.url}")
        print(f"HTTP狀態碼: {response.status_code}")
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尋找"Continue Reading"按鈕
        continue_reading_selectors = [
            'a.continue-reading-button', 
            'a.secondary-btn-link',
            'a[aria-label="Continue Reading"]',
            'a.yf-1uzpsm3',
            'a[data-ylk*="partnercta"]'
        ]
        
        target_link = None
        for selector in continue_reading_selectors:
            links = soup.select(selector)
            if links:
                print(f"找到按鈕 (選擇器: {selector})，共{len(links)}個")
                for i, link in enumerate(links):
                    href = link.get('href')
                    text = link.text.strip()
                    print(f"  按鈕 {i+1}: 文本='{text}'，href='{href}'")
                    if 'Continue Reading' in text and href:
                        target_link = href
                        print(f"  這是目標Continue Reading按鈕")
                        break
                if target_link:
                    break
        
        if not target_link:
            print("未找到'Continue Reading'按鈕")
            return False, None
        
        # 請求目標URL
        print(f"請求目標URL: {target_link}")
        target_response = session.get(target_link, timeout=15, allow_redirects=True)
        target_response.raise_for_status()
        
        print(f"成功獲取目標頁面: {target_response.url}")
        print(f"目標頁面大小: {len(target_response.text)} 字節")
        
        # 解析目標頁面標題
        target_soup = BeautifulSoup(target_response.text, 'html.parser')
        title = target_soup.title.text if target_soup.title else "無標題"
        print(f"目標頁面標題: {title}")
        
        return True, target_response.url
    
    except Exception as e:
        print(f"requests方法出錯: {e}")
        return False, None

def test_yahoo_finance_playwright(url, headless=True):
    """使用Playwright方法測試Yahoo Finance新聞頁面上的Continue Reading按鈕"""
    print(f"使用Playwright方法測試: {url}")
    
    with sync_playwright() as p:
        try:
            # 啟動瀏覽器
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # 設置較短的超時時間
            page.set_default_timeout(8000)
            
            # 訪問URL
            print("正在訪問頁面...")
            page.goto(url, wait_until="domcontentloaded")
            
            # 等待頁面加載
            try:
                page.wait_for_load_state("domcontentloaded")
            except:
                pass
            
            # 保存頁面截圖
            try:
                screenshot_path = f"yahoo_finance_before_{int(time.time())}.png"
                page.screenshot(path=screenshot_path)
                print(f"已保存頁面截圖: {screenshot_path}")
            except Exception as e:
                print(f"保存截圖時出錯: {e}")
            
            # 特定於Yahoo Finance的按鈕選擇器
            yahoo_selectors = [
                "a.secondary-btn-link.continue-reading-button",
                "a.yf-1uzpsm3",
                "a[data-ylk*='partnercta']",
                "a[aria-label='Continue Reading']",
                "a:has-text('Continue Reading')"
            ]
            
            # 尋找並點擊按鈕
            button_found = False
            target_url = None
            
            for selector in yahoo_selectors:
                try:
                    buttons = page.locator(selector)
                    count = buttons.count()
                    
                    if count > 0:
                        print(f"找到按鈕 (選擇器: {selector})，共{count}個")
                        button_found = True
                        
                        # 獲取第一個按鈕
                        button = buttons.first
                        
                        # 獲取按鈕文本
                        button_text = "未知"
                        try:
                            button_text = button.text_content().strip()
                            print(f"按鈕文本: '{button_text}'")
                        except:
                            pass
                        
                        # 獲取按鈕href
                        try:
                            href = button.get_attribute("href")
                            if href:
                                target_url = href
                                print(f"按鈕目標URL: {href}")
                        except:
                            pass
                        
                        # 確保按鈕可見
                        button.scroll_into_view_if_needed()
                        
                        # 保存有按鈕的截圖
                        try:
                            screenshot_path = f"yahoo_button_{int(time.time())}.png"
                            page.screenshot(path=screenshot_path)
                            print(f"已保存包含按鈕的截圖: {screenshot_path}")
                        except:
                            pass
                        
                        # 記錄點擊前URL
                        url_before_click = page.url
                        
                        # 點擊按鈕
                        print("點擊按鈕...")
                        button.click(force=True)
                        
                        # 等待導航完成
                        try:
                            page.wait_for_load_state("domcontentloaded")
                        except Exception as e:
                            print(f"等待頁面載入時出錯: {e}")
                        
                        # 檢查URL是否變化
                        current_url = page.url
                        if current_url != url_before_click:
                            print(f"點擊後成功導航到: {current_url}")
                            
                            # 保存導航後截圖
                            try:
                                screenshot_path = f"after_navigation_{int(time.time())}.png"
                                page.screenshot(path=screenshot_path)
                                print(f"已保存導航後截圖: {screenshot_path}")
                            except:
                                pass
                            
                            # 獲取頁面標題
                            title = page.title()
                            print(f"目標頁面標題: {title}")
                            
                            return True, current_url
                        else:
                            print("點擊後URL未變化")
                            
                            # 如果按鈕有href但點擊沒有導航，直接訪問href
                            if target_url:
                                print(f"嘗試直接訪問按鈕href: {target_url}")
                                page.goto(target_url, wait_until="domcontentloaded")
                                
                                # 檢查URL是否變化
                                if page.url != url_before_click:
                                    print(f"成功直接導航到: {page.url}")
                                    return True, page.url
                                else:
                                    print("直接訪問href後URL仍未變化")
                except Exception as e:
                    print(f"處理選擇器 {selector} 時出錯: {e}")
            
            # 如果找到按鈕但未成功導航，且有目標URL
            if button_found and target_url:
                print(f"找到按鈕但未成功導航。嘗試直接訪問目標URL: {target_url}")
                page.goto(target_url, wait_until="domcontentloaded")
                print(f"直接訪問後的URL: {page.url}")
                return True, page.url
            
            # 關閉瀏覽器
            browser.close()
            
            if not button_found:
                print("未找到任何'Continue Reading'按鈕")
            return False, None
        
        except Exception as e:
            print(f"Playwright方法出錯: {e}")
            return False, None

def main():
    parser = argparse.ArgumentParser(description='測試Yahoo Finance新聞頁面的Continue Reading按鈕')
    parser.add_argument('url', help='要測試的Yahoo Finance新聞URL')
    parser.add_argument('--no-headless', action='store_true', 
                      help='使用有頭模式運行瀏覽器（便於觀察）')
    parser.add_argument('--method', choices=['both', 'requests', 'playwright'], 
                      default='both', help='測試方法')
    
    args = parser.parse_args()
    
    # 顯示測試信息
    print("\n===== Yahoo Finance 'Continue Reading'按鈕測試 =====")
    print(f"測試URL: {args.url}")
    print(f"測試方法: {args.method}")
    print(f"瀏覽器模式: {'有頭模式' if args.no_headless else '無頭模式'}")
    print("="*50 + "\n")
    
    # 根據選擇的方法運行測試
    requests_success = playwright_success = False
    requests_url = playwright_url = None
    
    if args.method in ['both', 'requests']:
        requests_success, requests_url = test_yahoo_finance_requests(args.url)
    
    if args.method in ['both', 'playwright']:
        playwright_success, playwright_url = test_yahoo_finance_playwright(args.url, not args.no_headless)
    
    # 顯示結果
    print("\n===== 測試結果 =====")
    if args.method in ['both', 'requests']:
        print(f"Requests方法: {'成功' if requests_success else '失敗'}")
        if requests_url:
            print(f"  目標URL: {requests_url}")
    
    if args.method in ['both', 'playwright']:
        print(f"Playwright方法: {'成功' if playwright_success else '失敗'}")
        if playwright_url:
            print(f"  目標URL: {playwright_url}")
    
    # 最終結論
    if args.method == 'both':
        if requests_success or playwright_success:
            print("\n測試通過: 至少一種方法成功獲取了目標頁面")
            successful_url = requests_url if requests_success else playwright_url
            print(f"最終目標URL: {successful_url}")
        else:
            print("\n測試失敗: 兩種方法都未成功獲取目標頁面")
    elif args.method == 'requests':
        print(f"\n測試{'通過' if requests_success else '失敗'}")
    else:  # playwright
        print(f"\n測試{'通過' if playwright_success else '失敗'}")

if __name__ == "__main__":
    main() 