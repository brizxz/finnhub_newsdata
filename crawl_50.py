from utils import get_company_news, finnhub_client, API_KEY
import argparse
from datetime import datetime, timedelta
import requests
import os
import re
from bs4 import BeautifulSoup
import time
from readability import Document
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
import random

# --- Helper: Define a list of common User-Agents ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.7103.25 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0"
]

# --- Helper: Define common "load more" button texts/selectors ---
COMMON_LOAD_MORE_SELECTORS_TEXTS = [
    "[id*='show-more']",
    "[class*='load-more']",
    "[class*='show-more']",
    "[data-testid*='load-more']",
    "button:has-text('Show more')",
    "button:has-text('Load more')",
    "button:has-text('Read more')",
    "a:has-text('Continue reading')",
    "a.more-link"
]

def get_random_user_agent():
    """Selects a random User-Agent string."""
    return random.choice(USER_AGENTS)

def handle_press_and_hold(page, hold_time=8):
    """
    處理需要按住按鈕的反機器人機制
    
    Args:
        page: Playwright page物件
        hold_time: 按住的秒數
    
    Returns:
        是否成功處理
    """
    try:
        # 初始化 x, y 變數的預設值（頁面中心）
        viewport = page.viewport_size
        x = viewport["width"] / 2
        y = viewport["height"] / 2
        
        # 檢查頁面文本是否包含與按住相關的提示
        page_text = page.content().lower()
        if not ("press" in page_text and "hold" in page_text):
            print("未檢測到press & hold機制")
            return False
            
        print(f"偵測到press & hold反機器人機制，嘗試按住{hold_time}秒...")
        
        # 精確定位文本元素
        text_locator = page.locator("text=Press & Hold to confirm you are")
        
        if text_locator.count() > 0:
            print("找到'Press & Hold to confirm'文本元素")
            
            # 獲取元素位置
            try:
                element = text_locator.first
                box = element.bounding_box()
                
                if box:
                    # 點擊文本中心
                    x = box["x"] + box["width"] / 2
                    y = box["y"] + box["height"] / 2
                    print(f"找到目標元素，位置: ({x}, {y})")
                else:
                    print(f"無法獲取元素位置，使用頁面中心: ({x}, {y})")
            except Exception as e:
                print(f"獲取元素位置時出錯: {e}")
                print(f"使用頁面中心: ({x}, {y})")
        else:
            print(f"未找到確切的文本元素，使用頁面中心: ({x}, {y})")
        
        # 執行長按
        print(f"在位置 ({x}, {y}) 按住 {hold_time} 秒")
        page.mouse.move(x, y)
        page.mouse.down()
        time.sleep(hold_time)  # 長按指定時間
        page.mouse.up()
        print("釋放按鈕")
        
        # 等待頁面反應
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception as e:
            print(f"等待頁面載入時出錯: {e}")
        
        # 檢查是否還有press & hold文字
        after_text = page.content().lower()
        if "press" in after_text and "hold" in after_text:
            print("長按後仍有press & hold文字，可能未成功")
            # 再嘗試一次，稍微移動位置
            try:
                print(f"再次嘗試，位置稍作偏移 ({x+20}, {y+20})")
                page.mouse.move(x+20, y+20)
                page.mouse.down()
                time.sleep(hold_time)
                page.mouse.up()
                
                # 等待頁面反應
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except:
                    pass
                
                # 再次檢查
                after_text = page.content().lower()
                if "press" in after_text and "hold" in after_text:
                    print("第二次嘗試也未成功，可能需要非無頭模式或真實瀏覽器")
                    
                        
                    return False
                else:
                    print("第二次嘗試可能成功")
                    return True
            except Exception as e:
                print(f"第二次嘗試時出錯: {e}")
                return False
        else:
            print("長按後未檢測到press & hold文字，可能成功")
            return True
            
    except Exception as e:
        print(f"處理press & hold機制時出錯: {e}")
        return False

def handle_slider_captcha(page, max_attempts=3):
    """
    處理滑動驗證碼（如MarketWatch的滑動驗證）
    
    Args:
        page: Playwright page物件
        max_attempts: 最大嘗試次數
        
    Returns:
        是否成功處理
    """
    try:
        # 檢查頁面是否包含滑動驗證碼
        page_content = page.content().lower()
        has_slider = any(term in page_content for term in ["slide to continue", "drag", "slider", "verify you are human"])
        
        if not has_slider:
            print("未檢測到滑動驗證碼")
            return False
            
        print("偵測到滑動驗證碼，嘗試處理...")
        
        # MarketWatch常見的滑塊選擇器
        slider_selectors = [
            ".captcha-slider",
            ".slider-button",
            ".slide-to-verify",
            ".verification-slider",
            "[role='slider']",
            ".recaptcha-slider",
            "div[class*='slider']",
            "div[class*='captcha'] span",
            "div[class*='verify'] span"
        ]
        
        # 目標選擇器（滑動終點）
        target_selectors = [
            ".slider-target",
            ".captcha-target",
            ".target-zone",
            "div[class*='target']"
        ]
        
        # 尋找滑塊元素
        slider = None
        for selector in slider_selectors:
            try:
                elements = page.locator(selector)
                if elements.count() > 0:
                    slider = elements.first
                    print(f"找到滑塊元素: {selector}")
                    break
            except Exception as e:
                print(f"查找滑塊選擇器 {selector} 時出錯: {e}")
        
        if not slider:
            print("無法找到滑塊元素")
            return False
        
        # 尋找目標元素（如果有）
        target = None
        target_x = None
        for selector in target_selectors:
            try:
                elements = page.locator(selector)
                if elements.count() > 0:
                    target = elements.first
                    target_box = target.bounding_box()
                    if target_box:
                        target_x = target_box["x"] + target_box["width"] / 2
                        print(f"找到目標元素: {selector}，位置: {target_x}")
                        break
            except Exception as e:
                print(f"查找目標選擇器 {selector} 時出錯: {e}")
        
        # 獲取滑塊的位置和大小
        slider_box = slider.bounding_box()
        if not slider_box:
            print("無法獲取滑塊位置")
            return False
            
        slider_x = slider_box["x"] + slider_box["width"] / 2
        slider_y = slider_box["y"] + slider_box["height"] / 2
        
        # 如果沒有找到特定目標，估算滑動距離（通常是滑軌寬度的75-90%）
        container_selector = "div[class*='captcha-container'], div[class*='slider-container'], div[class*='verification']"
        container = page.locator(container_selector).first
        container_box = None
        try:
            container_box = container.bounding_box()
        except:
            print("無法找到滑塊容器，使用頁面寬度估算")
            container_box = {"width": page.viewport_size["width"] * 0.3}  # 估計滑軌寬度為頁面寬度的30%
            
        if not target_x:
            # 估算目標位置（通常是滑軌右側）
            slider_track_width = container_box["width"]
            target_x = slider_x + (slider_track_width * 0.85)  # 移動到滑軌85%的位置
            print(f"未找到目標元素，估算目標位置: {target_x}")
        
        # 嘗試滑動驗證
        success = False
        for attempt in range(max_attempts):
            try:
                print(f"滑動嘗試 {attempt+1}/{max_attempts}")
                
                # 移動到滑塊位置
                page.mouse.move(slider_x, slider_y)
                page.mouse.down()
                
                # 計算滑動所需的步數（越多步數移動越平滑）
                steps = 10
                distance = target_x - slider_x
                step_x = distance / steps
                
                # 慢慢滑動，模擬人類行為
                current_x = slider_x
                for step in range(steps):
                    # 添加一些隨機性使移動看起來更自然
                    current_x += step_x + random.uniform(-2, 2)
                    current_y = slider_y + random.uniform(-1, 1)
                    page.mouse.move(current_x, current_y)
                    # 隨機的短暫停頓
                    time.sleep(random.uniform(0.01, 0.05))
                
                # 確保最終位置接近目標
                page.mouse.move(target_x, slider_y)
                time.sleep(0.1)
                page.mouse.up()
                
                # 等待頁面反應
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except Exception as e:
                    print(f"等待頁面反應時出錯: {e}")
                
                
                # 檢查驗證是否成功（驗證碼可能消失或頁面變化）
                after_content = page.content().lower()
                verification_terms = ["slide to continue", "verify you are human", "captcha"]
                if not any(term in after_content for term in verification_terms):
                    print("滑動驗證可能已成功，驗證提示不再存在")
                    success = True
                    break
                
                # 檢查URL是否變化（有些驗證成功後會重定向）
                current_url = page.url
                if page.url != current_url:
                    print(f"URL已變化，可能已通過驗證: {page.url}")
                    success = True
                    break
                
                # 嘗試點擊可能出現的"繼續"按鈕
                continue_selectors = ["button:has-text('Continue')", "button:has-text('Proceed')", "button:has-text('Next')"]
                for continue_selector in continue_selectors:
                    if page.locator(continue_selector).count() > 0:
                        try:
                            page.locator(continue_selector).first.click(timeout=3000)
                            print("點擊了'繼續'按鈕")
                            success = True
                            break
                        except:
                            pass
                
                if success:
                    break
                    
                print("滑動驗證未成功，將重試...")
                time.sleep(1)  # 等待一下再嘗試
                
            except Exception as e:
                print(f"滑動過程中出錯: {e}")
                
        return success
        
    except Exception as e:
        print(f"處理滑動驗證碼時出錯: {e}")
        return False

def handle_seekingalpha_content(page, google_email=None, google_password=None):
    """
    處理SeekingAlpha網站的訪問限制，嘗試獲取文章內容
    
    Args:
        page: Playwright page物件
        google_email: Google登入電子郵件 (可選)
        google_password: Google登入密碼 (可選)
        
    Returns:
        是否成功處理
    """
    try:
        print("檢查是否為SeekingAlpha網站...")
        if "seekingalpha.com" not in page.url:
            print("不是SeekingAlpha網站，無需特殊處理")
            return False
            
        print("檢測到SeekingAlpha網站")
        
        # 尋找公開可見的文章摘要和關鍵信息
        print("嘗試獲取公開可見的文章內容...")
        
        # 查找文章標題
        title_selector = "h1"
        title_text = "無標題"
        try:
            title_element = page.locator(title_selector).first
            title_text = title_element.text_content().strip()
            print(f"文章標題: {title_text}")
        except:
            print("無法獲取文章標題")
        
        # 查找文章摘要/導言段落
        summary_selectors = [
            "div[data-test-id='article-summary']",
            ".article-summary",
            ".article-introduction",
            "div.sa-art > p:first-of-type",
            "div[data-test-id='content-container'] > p:first-of-type"
        ]
        
        summary_text = ""
        for selector in summary_selectors:
            try:
                summary_elements = page.locator(selector)
                if summary_elements.count() > 0:
                    summary_text = summary_elements.first.text_content().strip()
                    print(f"找到文章摘要: {summary_text[:100]}...")
                    break
            except:
                pass
                
        # 查找任何可見的段落文本（通常會顯示部分內容）
        visible_paragraphs = []
        try:
            paragraphs = page.locator("div[data-test-id='content-container'] p, .sa-art p, article p").all()
            for p in paragraphs:
                if p.is_visible():
                    text = p.text_content().strip()
                    if text and len(text) > 30:  # 忽略太短的段落
                        visible_paragraphs.append(text)
            
            if visible_paragraphs:
                print(f"找到 {len(visible_paragraphs)} 個可見段落")
        except Exception as e:
            print(f"提取可見段落時出錯: {e}")
            
        # 嘗試關閉登入提示
        try:
            close_selectors = [
                "button.close",
                "button[aria-label='Close']",
                ".modal-close",
                "button:has-text('Not now')",
                "button:has-text('Later')",
                "button:has-text('×')"
            ]
            
            for selector in close_selectors:
                close_buttons = page.locator(selector)
                if close_buttons.count() > 0:
                    close_buttons.first.click(timeout=3000)
                    print(f"關閉了登入提示 ({selector})")
                    time.sleep(1)
                    break
        except:
            pass
        
        # 如果提供了Google憑證，嘗試登入
        if google_email and google_password:
            print("嘗試使用Google帳號登入...")
            
            # 尋找Google登入按鈕
            google_login_selectors = [
                "button:has-text('Continue with Google')",
                "a:has-text('Continue with Google')",
                "[data-test-id='google-login']",
                "[aria-label='Sign in with Google']"
            ]
            
            login_button = None
            for selector in google_login_selectors:
                buttons = page.locator(selector)
                if buttons.count() > 0:
                    login_button = buttons.first
                    break
                    
            if login_button:
                print("找到Google登入按鈕，嘗試登入...")
                
                # 點擊登入按鈕
                login_button.click(timeout=5000)
                
                # 等待Google登入頁面加載
                try:
                    # 等待重定向到Google登入頁面
                    page.wait_for_url("*accounts.google.com*", timeout=5000)
                    print("已跳轉到Google登入頁面")
                    
                    # 輸入電子郵件
                    page.locator("input[type='email']").fill(google_email)
                    page.locator("button:has-text('Next')").click()
                    
                    # 等待密碼輸入框
                    page.wait_for_selector("input[type='password']", timeout=5000)
                    page.locator("input[type='password']").fill(google_password)
                    page.locator("button:has-text('Next')").click()
                    
                    # 等待重定向回SeekingAlpha
                    page.wait_for_url("*seekingalpha.com*", timeout=15000)
                    print("成功登入並返回SeekingAlpha")
                    
                    # 等待頁面加載
                    page.wait_for_load_state("networkidle", timeout=5000)
                    
                    # 檢查是否登入成功（尋找會員專屬元素）
                    if page.locator(".premium-content, .paywalled-content").count() == 0:
                        print("登入成功，可以訪問完整內容")
                        return True
                    else:
                        print("登入後仍無法訪問完整內容，可能需要付費訂閱")
                except Exception as e:
                    print(f"Google登入過程中出錯: {e}")
                    return False
            else:
                print("未找到Google登入按鈕")
        
        # 如果沒有登入憑證或登入失敗，至少返回摘要內容
        if visible_paragraphs or summary_text:
            print("無法訪問完整內容，但已獲取部分公開內容")
            
            # 構造替代內容（標題 + 摘要 + 可見段落）
            alternative_content = f"<h1>{title_text}</h1>\n"
            
            if summary_text:
                alternative_content += f"<p><strong>摘要:</strong> {summary_text}</p>\n"
                
            if visible_paragraphs:
                alternative_content += "<div class='visible-content'>\n"
                for p in visible_paragraphs:
                    alternative_content += f"<p>{p}</p>\n"
                alternative_content += "</div>\n"
                
            alternative_content += "<p><em>注意: 這只是部分內容，完整內容需要登入/訂閱</em></p>"
            
            # 將替代內容注入頁面，以便讀取器提取
            script = f"""
            document.body.innerHTML = `{alternative_content}`;
            """
            page.evaluate(script)
            print("已注入替代內容到頁面")
            
            return True
            
        return False
        
    except Exception as e:
        print(f"處理SeekingAlpha內容時出錯: {e}")
        return False

def fetch_article_requests_fallback(url):
    """
    使用requests作為首選方法獲取文章內容
    這將不處理JavaScript驅動的交互
    """
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5,zh-TW;q=0.3',
            'Referer': url.split('/')[0] + '//' + url.split('/')[2] + '/', 
            'DNT': '1', 
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        # Using a session for potential cookie persistence
        session = requests.Session()
        session.headers.update(headers)
        
        response = session.get(url, timeout=15, allow_redirects=True)
        response.raise_for_status()
        print(f"請求GET成功: {response.url}")
        
        # 檢查是否重定向到SeekingAlpha或WSJ
        if "seekingalpha.com" in response.url:
            print(f"URL已重定向到SeekingAlpha: {response.url}")
            print("SeekingAlpha網站需要登入才能獲取完整內容，已設定為跳過")
            return None, response.url
        elif "wsj.com" in response.url:
            print(f"URL已重定向到Wall Street Journal: {response.url}")
            print("Wall Street Journal網站需要訂閱才能獲取完整內容，已設定為跳過")
            return None, response.url
        
        # 檢查是否是Yahoo Finance新聞頁面並且有"Continue Reading"按鈕
        if "finnhub.io/api/news" in url or "finance.yahoo.com" in url:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # # 檢查是否包含SeekingAlpha或WSJ鏈接
            # all_links = soup.find_all('a', href=True)
            # for link in all_links:
            #     if "seekingalpha.com" in link['href']:
            #         print(f"檢測到Finnhub API返回的內容包含SeekingAlpha鏈接: {link['href']}")
            #         print("SeekingAlpha網站需要登入才能獲取完整內容，已設定為跳過")
            #         return None, url
            #     elif "wsj.com" in link['href']:
            #         print(f"檢測到Finnhub API返回的內容包含Wall Street Journal鏈接: {link['href']}")
            #         print("Wall Street Journal網站需要訂閱才能獲取完整內容，已設定為跳過")
            #         return None, url
                    
            # 特別檢查Yahoo Finance的Continue Reading按鈕
            yahoo_continue_buttons = soup.select('a.secondary-btn-link.continue-reading-button[title="Continue Reading"], a.yf-1uzpsm3[title="Continue Reading"], a[aria-label="Continue Reading"][title="Continue Reading"]')
            
            if yahoo_continue_buttons:
                for button in yahoo_continue_buttons:
                    continue_url = button.get('href')
                    if continue_url and "wsj.com" in continue_url:
                        print(f"發現'Continue Reading'按鈕指向WSJ: {continue_url}")
                        print("Wall Street Journal網站需要訂閱才能獲取完整內容，已設定為跳過")
                        return None, continue_url  # Return the WSJ URL as the final URL instead of the original URL

                continue_url = yahoo_continue_buttons[0].get('href')
                if continue_url:
                    print(f"發現'Continue Reading'按鈕，目標URL: {continue_url}")
                    
                    # 檢查目標URL是否是WSJ
                    if "wsj.com" in continue_url:
                        print("目標URL是Wall Street Journal網站，根據設定將跳過處理")
                        return None, continue_url  # Return the WSJ URL as the final URL instead of the original URL
                    
                    # 請求目標文章
                    try:
                        target_response = session.get(continue_url, timeout=15, allow_redirects=True)
                        target_response.raise_for_status()
                        print(f"成功獲取目標文章: {target_response.url}")
                        
                        # 再次檢查是否重定向到WSJ
                        if "wsj.com" in target_response.url:
                            print(f"目標URL已重定向到Wall Street Journal: {target_response.url}")
                            print("Wall Street Journal網站需要訂閱才能獲取完整內容，已設定為跳過")
                            return None, target_response.url
                        
                        return target_response.text, target_response.url
                    except Exception as e:
                        print(f"獲取目標文章時出錯: {e}")
                        # 無論什麼錯誤，都返回continue_url作為最終URL
                        # 這樣會確保barrons.com、wsj.com等網站的URL被正確記錄
                        return None, continue_url
        
        return response.text, response.url
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP錯誤 ({url}): {http_err.response.status_code} - {http_err}")
        if "wsj.com" in str(http_err):
            print("錯誤涉及Wall Street Journal網站，根據設定將跳過處理")
            # 從http_err中提取WSJ URL並返回為最終URL
            wsj_url = str(http_err).split("url: ")[1].strip() if "url: " in str(http_err) else url
            return None, wsj_url
        else:
            return None, url
    except requests.exceptions.RequestException as req_err:
        print(f"請求錯誤 ({url}): {req_err}")
        return None, url
    except Exception as e:
        print(f"通用錯誤 ({url}): {e}")
    return None, url

def fetch_full_article_playwright(url, custom_load_more_selectors=None, max_clicks_per_button_type=2, attempt_common_selectors=True, headless=True):
    """
    使用Playwright抓取文章的完整HTML內容。
    這個函數會嘗試：
    1. 處理反機器人機制如'Press & Hold'
    2. 點擊'Continue Reading'/'Read More'按鈕並跳轉到目標網站
    3. 點擊'Load More'類型按鈕加載更多內容
    4. 處理可能的頁面導航和URL變更

    Args:
        url (str): 文章的URL
        custom_load_more_selectors (list, optional): 自定義的"加載更多"按鈕選擇器列表
        max_clicks_per_button_type (int): 每種類型按鈕最多點擊次數
        attempt_common_selectors (bool): 是否嘗試常見的"加載更多"按鈕選擇器
        headless (bool): 是否使用無頭模式運行瀏覽器

    Returns:
        tuple: (html_content, final_url) 成功返回HTML內容和最終URL，失敗返回(None, 原始URL)
    """
    # 預先定義需要跳過的網站清單 - 這些網站不使用Playwright處理
    skip_sites = [
        "seekingalpha.com",
        "wsj.com",
        "barrons.com",
        "ft.com",
        "fool.com/premium",
        "morningstar.com/insights/",
        "investors.com/premium",
        "marketwatch.com"
    ]
    
    # 檢查URL是否匹配任何需要跳過的網站
    for site in skip_sites:
        if site in url:
            site_name = site.split('.')[0].capitalize()
            print(f"檢測到{site_name}網站URL: {url}")
            print(f"{site_name}網站需要訂閱才能獲取完整內容，跳過Playwright處理")
            return None, url
    
    html_content = None
    final_url = url
    browser = None # Initialize browser variable

    # 檢查X server是否可用，如果不可用但要求有頭模式則自動切換
    if not headless and not os.environ.get('DISPLAY'):
        print("\n警告: 請求了有頭模式運行瀏覽器，但沒有檢測到X server。")
        print("自動切換到無頭模式繼續執行。")
        print("如需使用有頭模式，請確保X server運行中，或使用xvfb-run命令。\n")
        headless = True

    load_more_selectors_to_try = []
    if custom_load_more_selectors:
        load_more_selectors_to_try.extend(custom_load_more_selectors)
    if attempt_common_selectors:
        load_more_selectors_to_try.extend(COMMON_LOAD_MORE_SELECTORS_TEXTS)

    # 定義需要處理滑動驗證碼的網站列表
    sliding_captcha_sites = [
        "marketwatch.com",
        "barrons.com",
        "wsj.com"  # 華爾街日報也可能有類似驗證
    ]

    # 定義"Continue Reading"類型的按鈕選擇器 - 使用更精確的選擇器包括title屬性
    continue_reading_selectors = [
        "a[title='Continue Reading']",
        "button[title='Continue Reading']",
        "a[aria-label='Continue Reading'][title='Continue Reading']",
        "a:has-text('Continue Reading')[title='Continue Reading']",
        "a.secondary-btn-link.continue-reading-button[title='Continue Reading']",
        "a.yf-1uzpsm3[title='Continue Reading']",
        "button[title='Read More']",
        "a[title='Read More']",
        "a:has-text('Read More')[title='Read More']",
        "a:has-text('Continue')[title*='Continue']",
        "a.continue-reading-button[title*='Continue']",
        "a.read-more[title*='Read More']"
    ]
    
    # 為Yahoo Finance新聞頁面添加精確的選擇器
    yahoo_finance_selectors = [
        ".yf-article-container a[href*='://']:not([href*='yahoo.com'])",  # 更通用的選擇器，尋找外部鏈接
        "div[data-plugin-continue-reading] a",  # Yahoo新文章格式
        "a.caas-button",  # 一些Yahoo文章中的通用按鈕類
        "a.js-content-viewer",  # 較舊的Yahoo閱讀器按鈕
        "a.secondary-btn-link.continue-reading-button",
        "a.yf-1uzpsm3", 
        "a[data-ylk*='partnercta']",
        "a[aria-label='Continue Reading']"
    ]
    continue_reading_selectors.extend(yahoo_finance_selectors)

    print(f"使用Playwright抓取文章: {url}")
    print(f"瀏覽器模式: {'無頭模式' if headless else '有頭模式'}")
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=headless) # Set headless=False for debugging
            context = browser.new_context(
                user_agent=get_random_user_agent(),
                java_script_enabled=True,
                accept_downloads=False,
                viewport={'width': 1920, 'height': 1080} # Common desktop viewport
            )
            # Set common HTTP headers for all requests within this context
            context.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9,zh-TW;q=0.8,zh;q=0.7',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
            })
            page = context.new_page()
            
            # 縮短超時時間
            page.set_default_timeout(5000)
            
            print(f"正在訪問: {url}")
            # 縮短頁面加載超時時間
            page.goto(url, wait_until="domcontentloaded", timeout=5000) 
            print(f"初始頁面載入完成。當前URL: {page.url}")
            final_url = page.url # Update final_url after initial navigation
            
            # 跳過WSJ網站
            if "wsj.com" in final_url:
                print(f"檢測到Wall Street Journal網站，根據設定直接跳過處理")
                print("Wall Street Journal網站需要訂閱才能獲取完整內容")
                html_content = page.content()
                return html_content, final_url

            # 檢查是否需要處理滑動驗證碼
            for site in sliding_captcha_sites:
                if site in page.url:
                    print(f"檢測到可能需要滑動驗證的網站: {site}")
                    if handle_slider_captcha(page):
                        print(f"成功處理{site}的滑動驗證碼")
                        # 等待頁面完全加載
                        try:
                            page.wait_for_load_state("networkidle", timeout=5000)
                        except:
                            pass
                    else:
                        print(f"未檢測到滑動驗證碼或處理失敗")
                    break

            # 檢查是否存在press & hold反機器人機制
            page_content = page.content().lower()
            if "press" in page_content and "hold" in page_content:
                print("偵測到可能的press & hold反機器人機制，嘗試處理...")
                if handle_press_and_hold(page):
                    print("成功處理press & hold機制")
                    # 更新頁面URL，可能重定向了
                    final_url = page.url
                    print(f"處理後的URL: {final_url}")
                else:
                    print("處理press & hold機制失敗")
            
            # 檢查MarketWatch滑動驗證碼
            if "marketwatch.com" in url or "marketwatch.com" in page.url:
                print("檢測到MarketWatch網站，檢查滑動驗證碼...")
                if handle_slider_captcha(page):
                    print("成功處理滑動驗證碼")
                    final_url = page.url
                    print(f"處理後的URL: {final_url}")
                    # 等待頁面完全加載
                    try:
                        page.wait_for_load_state("networkidle", timeout=5000)
                    except:
                        pass
                else:
                    print("未發現滑動驗證碼或處理失敗")
            
            # 處理SeekingAlpha網站
            if "seekingalpha.com" in url or "seekingalpha.com" in page.url:
                print("檢測到SeekingAlpha網站，根據設定直接跳過處理")
                print("SeekingAlpha網站需要登入才能獲取完整內容，已設定為跳過")
                html_content = page.content()
                final_url = page.url
                return html_content, final_url
            
            # 檢查是否是Yahoo Finance新聞頁面
            if "finnhub.io/api/news" in url or "finance.yahoo.com" in url:
                print("檢測到Yahoo Finance新聞頁面，尋找'Continue Reading'或'Story Continues'按鈕...")
                
                # 先檢查是否有"Story Continues"按鈕 (這種按鈕會展開當前頁面內容而非跳轉)
                try:
                    # 使用更精確的選擇器
                    story_continues_selectors = [
                        'button.readmore-button[title="Story Continues"]', 
                        'button[aria-label="Story Continues"]',
                        'button.secondary-btn.fin-size-large.readmore-button',
                        'button.secondary-btn.readmore-button',
                        'button.readmore-button',
                        'button:has-text("Story Continues")',
                        'button span:has-text("Story Continues")'
                    ]
                    
                    # 檢查每個可能的選擇器
                    story_buttons_found = False
                    
                    for selector in story_continues_selectors:
                        story_buttons = page.locator(selector)
                        story_count = story_buttons.count()
                        
                        if story_count > 0:
                            story_buttons_found = True
                            print(f"找到'Story Continues'按鈕，使用選擇器 '{selector}'，共{story_count}個")
                            
                            # 嘗試點擊所有Story Continues按鈕展開內容
                            for i in range(story_count):
                                try:
                                    button = story_buttons.nth(i)
                                    if button.is_visible():
                                        print(f"嘗試點擊第{i+1}個'Story Continues'按鈕")
                                        
                                        # 先滾動到按鈕視圖中確保可見
                                        button.scroll_into_view_if_needed(timeout=5000)
                                        time.sleep(1)  # 等待滾動完成
                                        
                                        # 點擊按鈕展開內容
                                        button.click(timeout=5000)
                                        print(f"已點擊第{i+1}個'Story Continues'按鈕")
                                        
                                        # 等待更長時間讓DOM更新
                                        print("等待內容展開...")
                                        try:
                                            # 先等待網絡活動完成
                                            page.wait_for_load_state("networkidle", timeout=5000)
                                        except Exception as e:
                                            print(f"等待網絡活動時出錯 (可能只是DOM更新): {e}")
                                            
                                        # 額外等待DOM更新
                                        time.sleep(3)  # 確保DOM有足夠時間更新
                                        
                                        # 檢查按鈕是否消失，表示內容已展開
                                        try:
                                            if not button.is_visible(timeout=1000):
                                                print("按鈕已消失，內容可能已展開")
                                        except:
                                            print("按鈕可能仍然存在或已被移除")
                                except Exception as e:
                                    print(f"點擊'Story Continues'按鈕 {i+1} 時出錯: {e}")
                            
                            # 如果找到並處理了按鈕，跳出選擇器循環
                            break
                    
                    if story_buttons_found:
                        print("已處理所有'Story Continues'按鈕，獲取當前頁面的完整內容")
                        return page.content(), page.url
                    else:
                        print("未找到'Story Continues'按鈕，繼續檢查是否有'Continue Reading'按鈕")
                except Exception as e:
                    print(f"處理'Story Continues'按鈕時出錯: {e}")
                
                # 只檢查是否有明確的"Continue Reading"按鈕，如果有才導航到外部URL
                try:
                    # 先等待頁面完全加載
                    page.wait_for_load_state("networkidle", timeout=5000)
                    
                    # 特別尋找Yahoo Finance標準Continue Reading按鈕
                    yahoo_button_selector = 'a.secondary-btn-link.continue-reading-button[title="Continue Reading"], a.yf-1uzpsm3[title="Continue Reading"], a[aria-label="Continue Reading"][title="Continue Reading"]'
                    standard_buttons = page.locator(yahoo_button_selector)
                    count = standard_buttons.count()
                    
                    if count > 0:
                        print(f"找到標準Yahoo Finance 'Continue Reading'按鈕，共{count}個")
                        
                        # 檢查每個標準按鈕是否指向WSJ
                        for i in range(count):
                            try:
                                button = standard_buttons.nth(i)
                                href = button.get_attribute("href")
                                
                                if href and "wsj.com" in href:
                                    print(f"按鈕 {i+1}/{count} 指向WSJ網站: {href}")
                                    print("Wall Street Journal網站需要訂閱才能獲取完整內容，已設定為跳過")
                                    return page.content(), page.url
                                    
                                if href and href.startswith("http"):
                                    print(f"找到有效的Continue Reading按鈕，指向: {href}")
                                    # 直接導航到目標URL
                                    page.goto(href, wait_until="domcontentloaded", timeout=5000)
                                    
                                    # 檢查是否重定向到WSJ
                                    if "wsj.com" in page.url:
                                        print(f"繼續閱讀鏈接導向WSJ網站: {page.url}")
                                        print("Wall Street Journal網站需要訂閱才能獲取完整內容，已設定為跳過")
                                        return page.content(), page.url
                                        
                                    final_url = page.url
                                    print(f"成功跳轉到: {final_url}")
                                    return page.content(), final_url
                            except Exception as e:
                                print(f"處理標準按鈕 {i+1}/{count} 時出錯: {e}")
                    
                    # 未找到標準的Continue Reading按鈕，回傳當前頁面的內容
                    print("未找到標準的'Continue Reading'按鈕，將直接回傳當前頁面內容")
                    return page.content(), page.url
                        
                except Exception as e:
                    print(f"尋找Continue Reading按鈕時出錯: {e}")
                    print("將直接回傳當前頁面內容")
                    return page.content(), page.url
            
            # 首先檢查並點擊"Continue Reading"類型的按鈕 (如果還沒有處理)
            if final_url == url:  # 如果還沒有跳轉
                continue_reading_clicked = False
                for selector in continue_reading_selectors:
                    try:
                        # 檢查是否存在這類按鈕
                        button_count = page.locator(selector).count()
                        if button_count > 0:
                            print(f"發現'Continue Reading'類型按鈕: {selector}，共{button_count}個")
                            
                            # 獲取點擊前的URL
                            url_before_click = page.url
                            
                            # 尋找最可能是主要"Continue Reading"按鈕的元素 (通常是第一個或最明顯的)
                            for i in range(min(button_count, 3)):  # 最多嘗試前3個匹配的按鈕
                                try:
                                    button = page.locator(selector).nth(i)
                                    
                                    # 檢查按鈕是否可見且可點擊
                                    if button.is_visible() and button.is_enabled():
                                        # 獲取按鈕的文本和位置信息
                                        button_text = "未知文本"
                                        try:
                                            button_text = button.text_content().strip()
                                        except:
                                            pass
                                        
                                        # 獲取按鈕的href屬性
                                        href = None
                                        try:
                                            href = button.get_attribute("href")
                                            print(f"按鈕href: {href}")
                                        except:
                                            pass
                                        
                                        # 準備點擊
                                        print(f"嘗試點擊第{i+1}個'Continue Reading'按鈕: '{button_text}'")
                                        
                                        # 直接使用href導航，如果可用
                                        if href and href.startswith("http"):
                                            print(f"直接導航到按鈕href: {href}")
                                            page.goto(href, wait_until="domcontentloaded", timeout=5000)
                                            if page.url != url_before_click:
                                                print(f"成功導航到目標URL: {page.url}")
                                                final_url = page.url
                                                continue_reading_clicked = True
                                                break
                                        
                                        # 嘗試點擊
                                        try:
                                            # 先滾動到按鈕附近
                                            page.evaluate(f"""
                                                window.scrollTo(0, {random.randint(300, 500)});
                                            """)
                                            time.sleep(1)
                                            
                                            # 確保按鈕在視圖中並點擊
                                            button.click(timeout=5000, force=True)
                                            
                                            # 等待頁面導航完成
                                            try:
                                                page.wait_for_load_state("domcontentloaded", timeout=5000)
                                                # 檢查URL是否變化
                                                current_url = page.url
                                                if current_url != url_before_click:
                                                    print(f"點擊'Continue Reading'後成功跳轉: {url_before_click} -> {current_url}")
                                                    final_url = current_url
                                                    continue_reading_clicked = True
                                                    # 等待一下確保頁面完全加載
                                                    time.sleep(1)
                                                    break
                                                else:
                                                    print(f"點擊後URL未變化，可能需要嘗試其他按鈕")
                                            except Exception as e:
                                                print(f"等待頁面加載時出錯: {e}")
                                        except Exception as e:
                                            print(f"點擊按鈕時出錯: {e}")
                                except Exception as e:
                                    print(f"處理第{i+1}個按鈕時出錯: {e}")
                            
                            # 如果成功點擊了Continue Reading並跳轉，跳出選擇器循環
                            if continue_reading_clicked:
                                break
                    except Exception as e:
                        print(f"處理Continue Reading按鈕時出錯: {e}")
            
            # 如果已經點擊了Continue Reading並跳轉，跳過常規的load more按鈕處理
            if final_url != url:  # 已經跳轉到新網站
                # 等待目標網站加載
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                except:
                    pass
            else:  # 如果沒有跳轉，嘗試常規的load more按鈕
                # Attempt to click "load more" or "accept cookies" buttons
                if load_more_selectors_to_try:
                    for selector in load_more_selectors_to_try:
                        for click_attempt in range(max_clicks_per_button_type):
                            try:
                                # Using .first to avoid issues if multiple elements match
                                button_locator = page.locator(selector).first 
                                # Wait for button to be visible before interacting
                                if button_locator.is_visible(timeout=3000): 
                                    print(f"發現可點擊元素 '{selector}'。嘗試點擊 {click_attempt + 1}...")
                                    url_before_click = page.url
                                    
                                    # Try to scroll into view if needed, then click
                                    button_locator.scroll_into_view_if_needed(timeout=5000)
                                    button_locator.click(timeout=5000) # Click with timeout
                                    
                                    # Wait for potential navigation or AJAX content to load
                                    try:
                                        page.wait_for_load_state("domcontentloaded", timeout=5000)
                                    except PlaywrightTimeoutError:
                                        print(f"點擊 '{selector}' 後等待頁面載入超時。內容可能已部分載入。")

                                    current_url_after_click = page.url
                                    if current_url_after_click != url_before_click:
                                        print(f"點擊後URL已更改: {url_before_click} -> {current_url_after_click}")
                                        final_url = current_url_after_click
                                    else:
                                        print(f"點擊 '{selector}' 後URL未變更。已等待動態內容載入。")
                                    
                                    time.sleep(random.uniform(1, 2)) # Smaller random delay
                                else:
                                    # Button not visible, break from this selector's attempts
                                    break 
                            except PlaywrightTimeoutError:
                                print(f"尋找或點擊按鈕 '{selector}' 超時 (嘗試 {click_attempt + 1})。")
                                if click_attempt == max_clicks_per_button_type - 1: # If last attempt for this selector
                                    print(f"已達到選擇器 '{selector}' 的最大點擊嘗試次數。")
                            except PlaywrightError as e:
                                if "Target page, context or browser has been closed" in str(e):
                                    print(f"點擊過程中瀏覽器意外關閉: {e}")
                                    raise 
                                print(f"點擊按鈕 '{selector}' 時出錯: {e}")
                                break # Break from this selector's attempts
            
            print(f"交互完成。最終內容獲取URL: {final_url}")
            html_content = page.content() # Get the final HTML content
            
        except PlaywrightTimeoutError as e:
            print(f"Playwright操作超時 ({url}): {e}")
        except PlaywrightError as e: 
            print(f"Playwright錯誤 ({url}): {e}")
        except Exception as e:
            print(f"使用Playwright抓取時發生錯誤 ({url}): {e}")
        finally:
            if browser and browser.is_connected():
                print("正在關閉Playwright瀏覽器。")
                browser.close()
    
    # 如果成功獲取了內容
    if html_content:
        return html_content, final_url
    # 如果Playwright也無法獲取內容
    return None, url

def download_article_content(url, output_dir, headless=True):
    """
    下載文章內容並保存到檔案，使用Playwright處理動態內容和反爬蟲機制
    
    Args:
        url: 文章的URL
        output_dir: 輸出目錄
        headless: 是否使用無頭模式運行瀏覽器
    
    Returns:
        保存的檔案路徑，若下載失敗則返回None
    """
    try:
        # 預先定義需要跳過的網站清單
        skip_sites = [
            "seekingalpha.com",
            "wsj.com",
            "barrons.com",  # 巴倫週刊也需要訂閱
            "ft.com",       # Financial Times需要訂閱
            "fool.com/premium",  # Motley Fool付費內容
            "morningstar.com/insights/", # Morningstar付費內容
            "investors.com/premium", # Investor's Business Daily付費內容
            "barrons.com/articles" # 確保包含完整的Barrons文章鏈接
        ]
        
        # 檢查URL是否匹配任何需要跳過的網站
        skip_site_matched = False
        matched_site = ""
        for site in skip_sites:
            if site in url:
                skip_site_matched = True
                matched_site = site
                break
        
        # 創建輸出目錄
        os.makedirs(output_dir, exist_ok=True)
        
        # 獲取目錄中已存在的news*.txt文件數量
        existing_files = [f for f in os.listdir(output_dir) if f.startswith('news') and f.endswith('.txt')]
        next_number = len(existing_files) + 1
        filename = f"news{next_number}.txt"
        file_path = os.path.join(output_dir, filename)
        
        if skip_site_matched:
            # 根據網站設定適當的站點名稱
            site_name_map = {
                "seekingalpha.com": "SeekingAlpha",
                "wsj.com": "Wall Street Journal",
                "barrons.com": "Barron's",
                "ft.com": "Financial Times",
                "fool.com/premium": "Motley Fool Premium",
                "morningstar.com/insights": "Morningstar Insights",
                "investors.com/premium": "Investor's Business Daily"
            }
            
            site_name = site_name_map.get(matched_site, matched_site.capitalize())
            print(f"跳過{site_name}網站: {url}")
            print(f"{site_name}網站需要訂閱才能獲取完整內容，已設定為跳過")
            
            # 創建提示性文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"原始URL: {url}\n")
                f.write(f"最終URL: {url}\n\n")  # 對於直接跳過的網站，最終URL與原始URL相同
                f.write(f"此為{site_name}網站文章，需要訂閱才能獲取完整內容。\n")
                f.write("根據設定已自動跳過處理。\n")
                
            print(f"已創建提示性文件: {file_path}")
            return file_path
            
        # 使用隨機延遲避免被封鎖
        time.sleep(random.uniform(1, 3))
        
        print(f"開始下載文章: {url}")
        
        # 首先嘗試使用requests獲取內容 (無需JavaScript處理的情況)
        html_content, final_url = fetch_article_requests_fallback(url)
        
        # 檢查是否重定向到需要跳過的網站
        skip_site_matched = False
        matched_site = ""
        if final_url:
            for site in skip_sites:
                if site in final_url:
                    skip_site_matched = True
                    matched_site = site
                    break
        
        if skip_site_matched:
            site_name_map = {
                "seekingalpha.com": "SeekingAlpha",
                "wsj.com": "Wall Street Journal",
                "barrons.com": "Barron's",
                "ft.com": "Financial Times",
                "fool.com/premium": "Motley Fool Premium",
                "morningstar.com/insights": "Morningstar Insights",
                "investors.com/premium": "Investor's Business Daily"
            }
            
            site_name = site_name_map.get(matched_site, matched_site.capitalize())
            print(f"URL已重定向到{site_name}: {final_url}")
            print(f"{site_name}網站需要訂閱才能獲取完整內容，已設定為跳過")
            
            # 創建提示性文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"原始URL: {url}\n")
                f.write(f"最終URL: {final_url}\n\n")
                f.write(f"此為{site_name}網站文章，需要訂閱才能獲取完整內容。\n")
                f.write("根據設定已自動跳過處理。\n")
                
            print(f"已創建提示性文件: {file_path}")
            return file_path
        
        # 如果requests方法失敗，則使用Playwright
        if not html_content:
            print(f"使用requests獲取失敗，切換到Playwright方法")
            
            # 識別特定網站的自定義選擇器
            custom_selectors = None
            if "marketwatch.com" in url:
                custom_selectors = [
                    "button:has-text('Agree and Continue')",  # For cookie/consent popups
                    "button:has-text('Continue reading')"
                ]
                print("為 marketwatch.com 應用自定義選擇器")
            elif "cnbc.com" in url:
                custom_selectors = [
                    "button[id*='accept']",
                    "button:has-text('Accept All Cookies')"
                ]
                print("為 cnbc.com 應用自定義選擇器")
            elif "bloomberg.com" in url:
                custom_selectors = [
                    "button:has-text('Accept cookies')",
                    "button:has-text('I Accept')"
                ]
                print("為 bloomberg.com 應用自定義選擇器")
            elif "finnhub.io/api/news" in url or "finance.yahoo.com" in url:
                custom_selectors = [
                    "button.readmore-button", 
                    "button[aria-label='Story Continues']",
                    "button:has-text('Story Continues')",
                    "a.continue-reading-button",
                    "a[aria-label='Continue Reading']"
                ]
                print("為 Yahoo Finance 新聞應用自定義選擇器")
                
            # 使用Playwright獲取完整HTML
            html_content, final_url = fetch_full_article_playwright(
                url, 
                custom_load_more_selectors=custom_selectors,
                headless=headless
            )
            
            # 檢查Playwright後是否重定向到需要跳過的網站
            skip_site_matched = False
            matched_site = ""
            if final_url:
                for site in skip_sites:
                    if site in final_url:
                        skip_site_matched = True
                        matched_site = site
                        break
            
            if skip_site_matched:
                site_name_map = {
                    "seekingalpha.com": "SeekingAlpha",
                    "wsj.com": "Wall Street Journal",
                    "barrons.com": "Barron's",
                    "ft.com": "Financial Times",
                    "fool.com/premium": "Motley Fool Premium",
                    "morningstar.com/insights": "Morningstar Insights",
                    "investors.com/premium": "Investor's Business Daily"
                }
                
                site_name = site_name_map.get(matched_site, matched_site.capitalize())
                print(f"Playwright瀏覽後URL重定向到{site_name}: {final_url}")
                print(f"{site_name}網站需要訂閱才能獲取完整內容，已設定為跳過")
                
                # 創建提示性文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"原始URL: {url}\n")
                    f.write(f"最終URL: {final_url}\n\n")
                    f.write(f"此為{site_name}網站文章，需要訂閱才能獲取完整內容。\n")
                    f.write("根據設定已自動跳過處理。\n")
                    
                print(f"已創建提示性文件: {file_path}")
                return file_path
        
        if not html_content:
            print(f"無法獲取文章HTML內容: {url}")
            # 即使無法獲取HTML內容，也創建一個包含URL信息的文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"原始URL: {url}\n")
                f.write(f"最終URL: {final_url or url}\n\n")
                f.write("無法獲取文章HTML內容，請檢查網址是否可訪問或嘗試手動訪問。")
            
            print(f"已創建URL信息文件: {file_path}")
            return file_path
        
        # 使用readability-lxml提取文章主要內容
        doc = Document(html_content)
        title = doc.title()
        content = doc.summary()
        
        # 使用BeautifulSoup清理HTML標籤獲取純文本
        soup = BeautifulSoup(content, 'html.parser')
        article_text = soup.get_text()
        
        # 檢查並標記是否為Yahoo Finance文章，並說明Story Continues處理結果
        if "finance.yahoo.com" in final_url:
            # 檢查是否包含Story Continues文本
            has_story_continues = False
            if "Story Continues" in html_content:
                has_story_continues = True
                
            # 檢查原始內容是否包含預期的完整內容標記（例如"Zacks Industry Rank"）
            complete_content_markers = [
                "Zacks Industry Rank",
                "To follow AAPL in the coming trading sessions",
                "Want the latest recommendations from Zacks Investment Research"
            ]
            
            has_complete_content = any(marker in html_content for marker in complete_content_markers)
                
            # 添加一個標記，提示用戶此文件可能是展開或未展開的情況
            if has_story_continues and not has_complete_content:
                article_text += "\n\n[注意: 此文章可能包含'Story Continues'按鈕，但內容未完全展開。內容可能不完整。]"
            elif has_story_continues and has_complete_content:
                article_text += "\n\n[注意: 此文章包含'Story Continues'按鈕，按鈕已被點擊，內容已完全展開。]"
        
        # 清理文字
        lines = (line.strip() for line in article_text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        article_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # 保存到檔案
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"原始URL: {url}\n")
            f.write(f"最終URL: {final_url}\n\n")
            f.write(f"標題: {title}\n\n")
            f.write("正文內容:\n")
            f.write(article_text)
        
        print(f"成功下載文章並保存到: {file_path}")
        return file_path
    
    except Exception as e:
        print(f"下載文章時發生錯誤 ({url}): {e}")
        return None

def display_company_news(symbol, from_date=None, to_date=None, download_articles=False, output_dir="downloaded_articles", headless=True):
    """
    取得並顯示特定公司的新聞
    
    Args:
        symbol: 公司股票代碼
        from_date: 起始日期 (YYYY-MM-DD格式)
        to_date: 結束日期 (YYYY-MM-DD格式)
        download_articles: 是否下載文章內容
        output_dir: 文章保存目錄
        headless: 是否使用無頭模式運行瀏覽器
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
        
        # 如果需要下載文章
        if download_articles:
            output_dir = f"{output_dir}/{symbol}_{from_date}_to_{to_date}"
            print(f"\n開始下載文章內容到目錄: {output_dir}")
            print(f"瀏覽器模式: {'無頭模式' if headless else '有頭模式'}")
            downloaded_count = 0
            
            for i, news_item in enumerate(company_news):
                url = news_item.get('url')
                if url:
                    print(f"\n下載文章 {i+1}/{len(company_news)}: {url}")
                    if download_article_content(url, output_dir, headless):
                        downloaded_count += 1
            
            print(f"\n文章下載完成。成功下載: {downloaded_count}/{len(company_news)}")
        
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
        # 使用正確的方法名稱，即 general_news 而非 market_news
        if category in ["general", "forex", "crypto", "merger"]:
            return finnhub_client.general_news(category=category)
        elif category == "crypto":
            # 獲取加密貨幣特定新聞
            # 注意：如果 general_news 已支援 crypto，這部分可能重複
            crypto_news = []
            
            # 嘗試獲取加密貨幣特定的新聞（如果有專用API）
            try:
                crypto_news = finnhub_client.crypto_news()
            except:
                # 如果沒有專用API，回退到使用 general_news 的 crypto 類別
                crypto_news = finnhub_client.general_news(category="crypto")
                
            return crypto_news
        else:
            return finnhub_client.general_news(category="general")
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
    parser.add_argument('--from-date', type=str, default='2025-04-01',
                      help='起始日期 (YYYY-MM-DD格式，預設: 2025-04-01)')
    parser.add_argument('--to-date', type=str, default='2025-04-30',
                      help='結束日期 (YYYY-MM-DD格式，預設: 2025-04-01)')
    parser.add_argument('--category', type=str, default='general',
                      choices=['general', 'forex', 'crypto', 'merger'],
                      help='市場新聞類別 (預設: general)')
    parser.add_argument('--min-id', type=int, default=0,
                      help='市場新聞最小ID (用於分頁，預設: 0)')
    parser.add_argument('--download-articles', action='store_true',
                      help='下載文章內容 (預設: False)')
    parser.add_argument('--output-dir', type=str, default='downloaded_articles',
                      help='文章保存目錄 (預設: downloaded_articles)')
    parser.add_argument('--no-headless', action='store_true',
                      help='使用有頭模式運行瀏覽器 (預設: 無頭模式)')
    
    args = parser.parse_args()
    
    # 轉換no-headless到headless
    args.headless = not args.no_headless
    
    # 檢查X server是否可用，如果不可用但要求有頭模式則顯示警告
    if args.no_headless and not os.environ.get('DISPLAY'):
        print("\n警告: 你請求了有頭模式 (--no-headless)，但沒有檢測到X server。")
        print("你有兩個選擇:")
        print("  1. 移除 --no-headless 參數，使用無頭模式運行")
        print("  2. 安裝並使用xvfb: sudo apt-get install xvfb")
        print("     然後運行: xvfb-run python crawl_50.py [其他參數] --no-headless")
        print("\n自動切換到無頭模式繼續執行...\n")
        args.headless = True
    
    return args

# --- 使用範例 ---
if __name__ == "__main__":
    if API_KEY == "YOUR_FINNHUB_API_KEY":
        print("請先在程式碼中設定您的 API_KEY")
    else:
        # 解析命令列參數
        args = parse_args()
        
        # 根據新聞類型調用相應的函式
        if args.type == 'company':
            display_company_news(args.symbol, args.from_date, args.to_date, 
                                args.download_articles, args.output_dir, args.headless)
        else:  # market news
            display_market_news(args.category, args.min_id)