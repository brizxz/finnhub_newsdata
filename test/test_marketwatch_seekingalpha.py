#!/usr/bin/env python3
"""
測試MarketWatch的滑動驗證碼和SeekingAlpha的登入機制處理
"""
import sys
import argparse
import time
import os
from playwright.sync_api import sync_playwright

# 導入我們實現的處理函數
from crawl_50 import handle_slider_captcha, handle_seekingalpha_content

def test_marketwatch(url=None, headless=True):
    """測試MarketWatch滑動驗證碼處理"""
    if not url:
        url = "https://www.marketwatch.com/story/nvidia-stock-price-target-raised-to-140-from-115-at-jefferies-2024-05-24"
    
    print(f"\n===== 測試MarketWatch滑動驗證 =====")
    print(f"URL: {url}")
    browser_mode = "無頭模式" if headless else "有頭模式"
    print(f"瀏覽器模式: {browser_mode}")
    print("="*50)
    
    with sync_playwright() as p:
        try:
            print(f"正在啟動瀏覽器 ({browser_mode})...")
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # 訪問MarketWatch頁面
            print(f"正在訪問: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # 保存訪問前的截圖
            try:
                screenshot_path = f"marketwatch_before_{int(time.time())}.png"
                page.screenshot(path=screenshot_path)
                print(f"已保存訪問前截圖: {screenshot_path}")
            except Exception as e:
                print(f"保存截圖時出錯: {e}")
            
            # 檢查是否有滑動驗證
            page_content = page.content().lower()
            has_slider = any(term in page_content for term in [
                "slide to continue", "drag", "slider", "verify you are human"
            ])
            
            if has_slider:
                print("偵測到滑動驗證碼，嘗試處理...")
                if handle_slider_captcha(page):
                    print("成功處理滑動驗證碼！")
                    
                    # 等待頁面加載
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except:
                        pass
                    
                    # 保存處理後的截圖
                    try:
                        screenshot_path = f"marketwatch_after_{int(time.time())}.png"
                        page.screenshot(path=screenshot_path)
                        print(f"已保存處理後截圖: {screenshot_path}")
                    except Exception as e:
                        print(f"保存截圖時出錯: {e}")
                    
                    # 檢查頁面內容是否可訪問
                    try:
                        article_title = page.locator("h1").text_content()
                        print(f"文章標題: {article_title}")
                        
                        paragraphs = page.locator("p").all()
                        if paragraphs:
                            print(f"找到 {len(paragraphs)} 個段落")
                            print(f"第一段內容: {paragraphs[0].text_content()[:100]}...")
                            return True
                    except Exception as e:
                        print(f"提取文章內容時出錯: {e}")
                else:
                    print("處理滑動驗證碼失敗")
            else:
                print("未檢測到滑動驗證碼，可能不需要處理或頁面結構已變更")
                return True
            
            browser.close()
            return False
            
        except Exception as e:
            print(f"測試MarketWatch滑動驗證時出錯: {e}")
            return False

def test_seekingalpha(url=None, headless=True):
    """測試SeekingAlpha登入和內容獲取"""
    if not url:
        url = "https://seekingalpha.com/article/4672787-microsoft-corporation-msft-stock-still-solid-investment-despite-pressure"
    
    print(f"\n===== 測試SeekingAlpha內容獲取 =====")
    print(f"URL: {url}")
    browser_mode = "無頭模式" if headless else "有頭模式"
    print(f"瀏覽器模式: {browser_mode}")
    print("="*50)
    
    # 檢查環境變量
    google_email = os.environ.get("GOOGLE_EMAIL")
    google_password = os.environ.get("GOOGLE_PASSWORD")
    
    if google_email and google_password:
        print(f"已設置Google登入憑證 (email: {google_email[:3]}...)")
    else:
        print("未設置Google登入憑證，將只獲取公開內容")
    
    with sync_playwright() as p:
        try:
            print(f"正在啟動瀏覽器 ({browser_mode})...")
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # 訪問SeekingAlpha頁面
            print(f"正在訪問: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # 保存訪問前的截圖
            try:
                screenshot_path = f"seekingalpha_before_{int(time.time())}.png"
                page.screenshot(path=screenshot_path)
                print(f"已保存訪問前截圖: {screenshot_path}")
            except Exception as e:
                print(f"保存截圖時出錯: {e}")
            
            # 處理SeekingAlpha內容
            if handle_seekingalpha_content(page, google_email, google_password):
                print("成功處理SeekingAlpha內容")
                
                # 保存處理後的截圖
                try:
                    screenshot_path = f"seekingalpha_after_{int(time.time())}.png"
                    page.screenshot(path=screenshot_path)
                    print(f"已保存處理後截圖: {screenshot_path}")
                except Exception as e:
                    print(f"保存截圖時出錯: {e}")
                
                # 檢查內容
                try:
                    title = page.locator("h1").text_content()
                    print(f"文章標題: {title}")
                    
                    paragraphs = page.locator("p").all()
                    if paragraphs:
                        print(f"找到 {len(paragraphs)} 個段落")
                        print(f"第一段內容: {paragraphs[0].text_content()[:100]}...")
                        return True
                except Exception as e:
                    print(f"提取文章內容時出錯: {e}")
            else:
                print("處理SeekingAlpha內容失敗")
            
            browser.close()
            return False
            
        except Exception as e:
            print(f"測試SeekingAlpha時出錯: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='測試MarketWatch滑動驗證和SeekingAlpha登入處理')
    parser.add_argument('--site', choices=['marketwatch', 'seekingalpha', 'both'], default='both',
                      help='要測試的網站')
    parser.add_argument('--url', type=str, help='要測試的URL')
    parser.add_argument('--no-headless', action='store_true', 
                      help='使用有頭模式運行瀏覽器（便於觀察）')
    
    args = parser.parse_args()
    
    requested_mode = "有頭模式" if args.no_headless else "無頭模式"
    
    # 檢查X server是否可用，如果不可用但要求有頭模式則顯示警告
    if args.no_headless and not os.environ.get('DISPLAY'):
        print("\n警告: 你請求了有頭模式 (--no-headless)，但沒有檢測到X server。")
        print("你有兩個選擇:")
        print("  1. 移除 --no-headless 參數，使用無頭模式運行")
        print("  2. 安裝並使用xvfb: sudo apt-get install xvfb")
        print("     然後運行: xvfb-run ./test_marketwatch_seekingalpha.py --no-headless")
        print("\n自動切換到無頭模式繼續執行...\n")
        headless = True
        actual_mode = "無頭模式 (自動切換)"
    else:
        headless = not args.no_headless
        actual_mode = requested_mode
    
    # 顯示測試配置
    print("\n===== 測試配置 =====")
    print(f"要測試的站點: {args.site}")
    if args.url:
        print(f"指定URL: {args.url}")
    print(f"請求的瀏覽器模式: {requested_mode}")
    print(f"實際的瀏覽器模式: {actual_mode}")
    print("="*50)
    
    marketwatch_success = seekingalpha_success = False
    
    if args.site in ['marketwatch', 'both']:
        marketwatch_url = args.url if args.site == 'marketwatch' and args.url else None
        marketwatch_success = test_marketwatch(marketwatch_url, headless)
    
    if args.site in ['seekingalpha', 'both']:
        seekingalpha_url = args.url if args.site == 'seekingalpha' and args.url else None
        seekingalpha_success = test_seekingalpha(seekingalpha_url, headless)
    
    # 顯示測試結果
    print("\n===== 測試結果摘要 =====")
    if args.site in ['marketwatch', 'both']:
        print(f"MarketWatch滑動驗證測試: {'成功' if marketwatch_success else '失敗'}")
    
    if args.site in ['seekingalpha', 'both']:
        print(f"SeekingAlpha內容獲取測試: {'成功' if seekingalpha_success else '失敗'}")
    
    # 返回值供自動化測試使用
    if args.site == 'marketwatch':
        return 0 if marketwatch_success else 1
    elif args.site == 'seekingalpha':
        return 0 if seekingalpha_success else 1
    else:  # both
        return 0 if (marketwatch_success and seekingalpha_success) else 1

if __name__ == "__main__":
    sys.exit(main()) 