#!/usr/bin/env python3
"""
專門測試處理Press & Hold反機器人機制的腳本
"""
import sys
import time
import argparse
from playwright.sync_api import sync_playwright

def test_press_and_hold(url, selector=None, hold_time=5, headless=True):
    """
    專門測試Press & Hold反機器人驗證機制
    
    Args:
        url: 目標網站URL
        selector: 要按住的元素選擇器 (若為None則自動偵測)
        hold_time: 按住時間(秒)
        headless: 是否使用無頭模式
    """
    print(f"開始測試Press & Hold於網站: {url}")
    print(f"按住時間: {hold_time}秒")
    print(f"瀏覽器模式: {'無頭模式' if headless else '有頭模式'}")
    
    with sync_playwright() as p:
        try:
            # 根據參數決定是否使用無頭模式
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # 設置更長的超時時間
            page.set_default_timeout(90000)
            
            # 訪問網站
            print(f"正在訪問頁面...")
            page.goto(url, wait_until="domcontentloaded")
            
            # 檢查頁面是否重定向
            final_url = page.url
            if final_url != url:
                print(f"頁面已重定向到: {final_url}")
            
            # 等待頁面載入
            time.sleep(2)
            
            # 如果沒有提供選擇器，嘗試自動偵測
            if not selector:
                # 檢查頁面文本是否包含相關提示
                page_content = page.content().lower()
                if "press" in page_content and "hold" in page_content:
                    print("偵測到可能的Press & Hold提示文字")
                    
                    # 嘗試常見的選擇器
                    common_selectors = [
                        "button:has-text('Press & Hold')",
                        "div:has-text('Press & Hold')",
                        "[class*='captcha']",
                        "[id*='captcha']",
                        "[class*='press-hold']",
                        "[class*='press']",
                    ]
                    
                    for sel in common_selectors:
                        if page.locator(sel).count() > 0:
                            selector = sel
                            print(f"找到可能的Press & Hold元素: {selector}")
                            break
                
                # 如果還沒找到元素，嘗試使用body
                if not selector:
                    print("未找到特定元素，將在整個頁面上嘗試")
                    selector = "body"
            
            # 獲取要按住的元素
            print(f"使用選擇器: {selector}")
            element = page.locator(selector).first
            
            if not element.is_visible():
                print(f"警告: 元素 {selector} 不可見")
                
            # 獲取元素位置
            bounding_box = element.bounding_box()
            if not bounding_box:
                print("警告: 無法獲取元素位置，將使用頁面中心")
                # 使用頁面中心
                viewport_size = page.viewport_size
                x = viewport_size["width"] / 2
                y = viewport_size["height"] / 2
            else:
                x = bounding_box["x"] + bounding_box["width"] / 2
                y = bounding_box["y"] + bounding_box["height"] / 2
            
            # 模擬按住動作
            print(f"在位置 ({x}, {y}) 開始按住元素")
            page.mouse.move(x, y)
            page.mouse.down()
            
            # 按住指定時間
            print(f"按住元素 {hold_time} 秒...")
            time.sleep(hold_time)
            
            # 釋放
            page.mouse.up()
            print("釋放元素")
            
            # 等待頁面可能的變化
            print("等待頁面響應...")
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
                print("頁面加載完成")
            except Exception as e:
                print(f"等待頁面加載時出現警告: {e}")
            
            # 顯示處理後的URL
            after_url = page.url
            if after_url != final_url:
                print(f"處理後URL已變更: {final_url} -> {after_url}")
            
            # 獲取最終HTML內容
            final_html = page.content()
            print(f"\n頁面HTML大小: {len(final_html)} 字節")
            
            # 檢查是否仍然存在press & hold文字
            if "press" in final_html.lower() and "hold" in final_html.lower():
                print("警告: 頁面仍然包含press & hold文字，可能未成功通過驗證")
            else:
                print("成功: 頁面不再包含press & hold文字，可能已通過驗證")
            
            # 在無頭模式下，直接結束
            if headless:
                print("\n測試完成。")
            else:
                # 在有頭模式下，等待用戶檢查
                print("\n測試完成。請檢查瀏覽器中的結果。")
                print("按下Ctrl+C結束測試...")
                
                # 等待用戶中斷
                while True:
                    time.sleep(1)
                
        except Exception as e:
            print(f"測試過程中發生錯誤: {e}")
        finally:
            if 'browser' in locals() and browser:
                browser.close()
                print("已關閉瀏覽器")

def parse_args():
    parser = argparse.ArgumentParser(description='測試處理Press & Hold反機器人機制')
    parser.add_argument('url', nargs='?', default="https://seekingalpha.com/article/4780240-franklin-rising-dividends-fund-q1-2025-commentary",
                        help='目標網站URL')
    parser.add_argument('--selector', '-s', help='要按住的元素選擇器')
    parser.add_argument('--hold-time', '-t', type=int, default=5,
                        help='按住時間(秒), 預設5秒')
    parser.add_argument('--headed', action='store_true',
                        help='使用有頭模式 (可視化瀏覽器), 預設為無頭模式')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    test_press_and_hold(args.url, args.selector, args.hold_time, not args.headed) 