#!/usr/bin/env python3
"""
測試處理'Continue Reading'按鈕和跳轉功能
"""
import sys
import time
import argparse
from playwright.sync_api import sync_playwright

# 定義"Continue Reading"類型的按鈕選擇器
CONTINUE_READING_SELECTORS = [
    "a:has-text('Continue Reading')",
    "button:has-text('Continue Reading')",
    "a:has-text('Read More')",
    "button:has-text('Read More')",
    "a:has-text('Continue')",
    "a.continue-reading",
    "a.read-more",
    "[class*='continue-reading']",
    "[class*='read-more']",
    "[aria-label*='Continue Reading']",
    "[aria-label*='Read More']"
]

def click_continue_reading(url, headless=False, timeout=30000):
    """
    測試訪問URL並點擊"Continue Reading"按鈕跳轉到目標網站
    
    Args:
        url: 起始URL
        headless: 是否使用無頭模式
        timeout: 頁面加載超時時間(毫秒)
        
    Returns:
        tuple: (成功狀態, 最終URL, 備註)
    """
    print(f"開始測試處理'Continue Reading'按鈕: {url}")
    
    with sync_playwright() as p:
        try:
            # 啟動瀏覽器
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # 設置超時時間
            page.set_default_timeout(timeout)
            
            # 訪問URL
            print(f"正在訪問頁面...")
            page.goto(url, wait_until="domcontentloaded")
            
            # 等待頁面加載
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception as e:
                print(f"等待頁面加載完成時出錯: {e}")
            
            # 獲取初始URL
            initial_url = page.url
            if initial_url != url:
                print(f"頁面已重定向到: {initial_url}")
            
            # 嘗試保存截圖
            try:
                screenshot_path = f"before_click_{int(time.time())}.png"
                page.screenshot(path=screenshot_path)
                print(f"已保存點擊前截圖: {screenshot_path}")
            except Exception as e:
                print(f"保存截圖時出錯: {e}")
            
            # 檢查並點擊"Continue Reading"按鈕
            continue_reading_clicked = False
            button_found = False
            
            for selector in CONTINUE_READING_SELECTORS:
                try:
                    # 檢查是否存在這類按鈕
                    button_count = page.locator(selector).count()
                    if button_count > 0:
                        button_found = True
                        print(f"發現'Continue Reading'類型按鈕: {selector}，共{button_count}個")
                        
                        # 獲取點擊前的URL
                        url_before_click = page.url
                        
                        # 嘗試點擊按鈕
                        for i in range(min(button_count, 3)):  # 最多嘗試前3個匹配的按鈕
                            try:
                                button = page.locator(selector).nth(i)
                                
                                # 檢查按鈕是否可見
                                if button.is_visible():
                                    # 獲取按鈕文本
                                    button_text = "未知文本"
                                    try:
                                        button_text = button.text_content().strip()
                                    except:
                                        pass
                                    
                                    # 獲取按鈕位置
                                    try:
                                        box = button.bounding_box()
                                        if box:
                                            button_x = box["x"] + box["width"] / 2
                                            button_y = box["y"] + box["height"] / 2
                                            print(f"按鈕 '{button_text}' 位於: ({button_x}, {button_y})")
                                    except:
                                        pass
                                    
                                    # 準備點擊
                                    print(f"嘗試點擊第{i+1}個按鈕: '{button_text}'")
                                    
                                    # 確保按鈕在視圖中
                                    button.scroll_into_view_if_needed()
                                    
                                    # 再次保存截圖
                                    try:
                                        screenshot_path = f"button_{i+1}_{int(time.time())}.png"
                                        page.screenshot(path=screenshot_path)
                                        print(f"已保存包含按鈕的截圖: {screenshot_path}")
                                    except:
                                        pass
                                    
                                    # 點擊按鈕
                                    button.click(force=True)
                                    
                                    # 等待可能的頁面導航
                                    try:
                                        page.wait_for_load_state("networkidle", timeout=20000)
                                    except Exception as e:
                                        print(f"點擊後等待頁面加載時出錯: {e}")
                                    
                                    # 檢查URL是否變化
                                    current_url = page.url
                                    if current_url != url_before_click:
                                        print(f"點擊成功跳轉: {url_before_click} -> {current_url}")
                                        
                                        # 保存跳轉後截圖
                                        try:
                                            screenshot_path = f"after_redirect_{int(time.time())}.png"
                                            page.screenshot(path=screenshot_path)
                                            print(f"已保存跳轉後截圖: {screenshot_path}")
                                        except:
                                            pass
                                        
                                        continue_reading_clicked = True
                                        break
                                    else:
                                        print("點擊後URL未變化")
                            except Exception as e:
                                print(f"點擊按鈕時出錯: {e}")
                        
                        # 如果點擊成功並跳轉，跳出循環
                        if continue_reading_clicked:
                            break
                except Exception as e:
                    print(f"處理選擇器 {selector} 時出錯: {e}")
            
            # 獲取最終結果
            final_url = page.url
            
            # 關閉瀏覽器
            browser.close()
            
            # 返回結果
            if continue_reading_clicked:
                return True, final_url, "成功點擊'Continue Reading'並跳轉"
            elif button_found:
                return False, final_url, "找到'Continue Reading'按鈕但點擊未成功跳轉"
            else:
                return False, final_url, "未找到任何'Continue Reading'按鈕"
                
        except Exception as e:
            print(f"測試過程中發生錯誤: {e}")
            return False, url, f"發生錯誤: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description='測試處理Continue Reading按鈕')
    parser.add_argument('url', help='要測試的URL')
    parser.add_argument('--headless', action='store_true', 
                        help='使用無頭模式 (默認為有頭模式以便觀察)')
    parser.add_argument('--timeout', type=int, default=30000,
                        help='頁面加載超時時間(毫秒)')
    
    args = parser.parse_args()
    
    success, final_url, note = click_continue_reading(args.url, args.headless, args.timeout)
    
    print("\n===== 測試結果 =====")
    print(f"起始URL: {args.url}")
    print(f"最終URL: {final_url}")
    print(f"結果: {'成功' if success else '失敗'}")
    print(f"備註: {note}")

if __name__ == "__main__":
    main() 