import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
import time
import random

# --- Helper: Define a list of common User-Agents ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.7103.25 Safari/537.36"
]

# --- Helper: Define common "load more" button texts/selectors (examples) ---
# These are highly site-specific. This list is for demonstration and may need adjustment.
COMMON_LOAD_MORE_SELECTORS_TEXTS = [
    "[id*='show-more']",
    "[class*='load-more']",
    "[class*='show-more']",
    "[data-testid*='load-more']"
]

def get_random_user_agent():
    """Selects a random User-Agent string."""
    return random.choice(USER_AGENTS)

def fetch_full_article_playwright(url, custom_load_more_selectors=None, max_clicks_per_button_type=2, attempt_common_selectors=True):
    """
    Fetches the full HTML content of an article using Playwright.
    It attempts to click "load more" type buttons and handles potential anti-scraping.
    It also correctly handles page navigations if button clicks lead to new URLs.

    Args:
        url (str): The URL of the article to fetch.
        custom_load_more_selectors (list, optional): A list of site-specific CSS selectors for "load more" buttons.
        max_clicks_per_button_type (int): Max number of times to click each type of identified button.
        attempt_common_selectors (bool): Whether to try a list of common "load more" selectors.

    Returns:
        tuple: (html_content, final_url) or (None, original_url) if fetching fails.
    """
    html_content = None
    final_url = url
    browser = None # Initialize browser variable

    load_more_selectors_to_try = []
    if custom_load_more_selectors:
        load_more_selectors_to_try.extend(custom_load_more_selectors)
    if attempt_common_selectors:
        load_more_selectors_to_try.extend(COMMON_LOAD_MORE_SELECTORS_TEXTS)

    print(f"Attempting to fetch with Playwright: {url}")
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True) # Set headless=False for debugging
            context = browser.new_context(
                user_agent=get_random_user_agent(),
                java_script_enabled=True,
                accept_downloads=False,
                viewport={'width': 1920, 'height': 1080} # Common desktop viewport
            )
            # Set common HTTP headers for all requests within this context [2]
            context.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
            })
            page = context.new_page()
            
            print(f"Navigating to: {url}")
            # Increased timeout for navigation, wait until network is idle [3, 4]
            page.goto(url, wait_until="networkidle", timeout=90000) 
            print(f"Initial load complete. Current URL: {page.url}")
            final_url = page.url # Update final_url after initial navigation

            # Attempt to click "load more" or "accept cookies" buttons
            if load_more_selectors_to_try:
                for selector in load_more_selectors_to_try:
                    for click_attempt in range(max_clicks_per_button_type):
                        try:
                            # Using.first to avoid issues if multiple elements match
                            button_locator = page.locator(selector).first 
                            # Wait for button to be visible before interacting [5, 3]
                            if button_locator.is_visible(timeout=7000): 
                                print(f"Button with selector '{selector}' is visible. Attempting click {click_attempt + 1}...")
                                url_before_click = page.url
                                
                                # Try to scroll into view if needed, then click
                                button_locator.scroll_into_view_if_needed(timeout=5000)
                                button_locator.click(timeout=15000) # Click with timeout
                                
                                # Wait for potential navigation or AJAX content to load
                                try:
                                    # If URL changes, wait_for_url might be more specific,
                                    # but networkidle covers AJAX updates too.
                                    page.wait_for_load_state("networkidle", timeout=20000)
                                except PlaywrightTimeoutError:
                                    print(f"Timeout waiting for networkidle after click on '{selector}'. Content might be partially loaded or navigation is slow.")

                                current_url_after_click = page.url
                                if current_url_after_click!= url_before_click:
                                    print(f"URL changed after click: {url_before_click} -> {current_url_after_click}")
                                    final_url = current_url_after_click
                                    # If URL changed, new page content is primary.
                                    # Depending on site, might break from this selector's clicks or continue.
                                else:
                                    print(f"Clicked '{selector}', page URL did not change. Waited for dynamic content.")
                                
                                time.sleep(random.uniform(1.5, 3.5)) # Small random delay to mimic human behavior
                            else:
                                # Button not visible, break from this selector's attempts
                                break 
                        except PlaywrightTimeoutError:
                            print(f"Timeout finding or clicking button '{selector}' (attempt {click_attempt + 1}).")
                            if click_attempt == max_clicks_per_button_type -1: # If last attempt for this selector
                                print(f"Max click attempts reached for selector '{selector}'.")
                            # Continue to next attempt or next selector
                        except PlaywrightError as e:
                            if "Target page, context or browser has been closed" in str(e):
                                print(f"Browser/Page closed unexpectedly during click: {e}")
                                raise 
                            print(f"Playwright error clicking button '{selector}': {e}")
                            break # Break from this selector's attempts
            
            print(f"Finished interactions. Final URL for content retrieval: {final_url}")
            html_content = page.content() # Get the final HTML content [6, 7]
            
        except PlaywrightTimeoutError as e:
            print(f"Playwright operation timed out for {url}: {e}")
        except PlaywrightError as e: 
            print(f"A Playwright error occurred for {url}: {e}")
        except Exception as e:
            print(f"A generic error occurred during Playwright fetch for {url}: {e}")
        finally:
            if browser and browser.is_connected():
                print("Closing Playwright browser.")
                browser.close()
    
    # Fallback if Playwright failed to get content
    if not html_content:
        print(f"Playwright did not retrieve content for {url}. Attempting fallback with 'requests'.")
        return fetch_article_requests_fallback(url)
        
    return html_content, final_url

def fetch_article_requests_fallback(url):
    """
    Fallback function to fetch article content using the requests library.
    This will not handle JavaScript-driven interactions.
    """
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': url.split('/') + '//' + url.split('/')[1] + '/', 
            'DNT': '1', 
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        # Using a session for potential cookie persistence if multiple fallbacks are made to same domain
        session = requests.Session()
        session.headers.update(headers)
        
        response = session.get(url, timeout=30, allow_redirects=True)
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX) [2]
        print(f"Fallback 'requests' GET successful for {response.url}")
        return response.text, response.url
    except requests.exceptions.HTTPError as http_err:
        print(f"Fallback HTTP error for {url}: {http_err.response.status_code} - {http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Fallback Request error for {url}: {req_err}")
    except Exception as e:
        print(f"Fallback Generic error for {url}: {e}")
    return None, url

# --- Your original functions, modified to use the new fetcher ---

def download_article_content(article_url, custom_load_more_selectors=None):
    """
    Downloads and returns the full HTML content of an article from a given URL.
    Uses Playwright for dynamic content and button clicks, with a requests fallback.
    """
    print(f"Attempting to download article from: {article_url}")
    
    content_tuple = fetch_full_article_playwright(
        article_url, 
        custom_load_more_selectors=custom_load_more_selectors
    )
    
    if content_tuple and content_tuple:
        html_content, final_url = content_tuple
        print(f"Successfully fetched content from {final_url} (original: {article_url}). Length: {len(html_content)}")
        return html_content, final_url 
    else:
        print(f"Failed to download article content from {article_url} after all attempts.")
        return None, article_url

def download_article_content_from_id(news_id_or_url):
    """
    Downloads the article content.
    Assumes news_id_or_url is the direct article URL.
    If it's an ID for Finnhub, you first need to fetch the actual article URL from Finnhub API.
    """
    article_url = news_id_or_url # Assuming news_id_or_url is the actual article URL

    print(f"Downloading content for (URL/ID): {article_url}")
    
    # Example: Site-specific selectors can be added here
    custom_selectors = None
    if "marketwatch.com" in article_url:
        # These are examples; actual selectors would need to be identified from MarketWatch
        custom_selectors = [
            "button:has-text('Agree and Continue')", # For cookie/consent popups
            # "a.truncate-view-more" # Example for a "view more" link
        ]
        print("Applying custom selectors/logic for marketwatch.com")

    # The download_article_content function now returns a tuple (html_content, final_url)
    html_content, final_url = download_article_content(article_url, custom_load_more_selectors=custom_selectors)
    
    # Your original function returned only the content.
    # If you need the final URL, you can modify your calling code to use it.
    return html_content


# --- Example Usage (Illustrative - replace with your actual URLs/IDs) ---
if __name__ == '__main__':
    # IMPORTANT: Before running, ensure Playwright is installed (`pip install playwright`)
    # and browser binaries are downloaded (`playwright install`).

    # Test Case 1: A known problematic URL (like the MarketWatch one)
    # The ID here is assumed to be the direct URL as per your original structure.
    marketwatch_example_url = "https://www.marketwatch.com/articles/boeing-earnings-stock-price-5f458152"
    print(f"\n--- Testing MarketWatch URL: {marketwatch_example_url} ---")
    content_mw = download_article_content_from_id(marketwatch_example_url)
    if content_mw:
        print(f"Successfully fetched MarketWatch content. Size: {len(content_mw)} bytes.")
        # soup = BeautifulSoup(content_mw, 'html.parser')
        # title = soup.find('title')
        # print(f"Page Title: {title.string if title else 'No title found'}")
        # print(f"First 500 chars:\n{content_mw[:500]}")
    else:
        print(f"Failed to fetch content from MarketWatch URL: {marketwatch_example_url}")

    # Test Case 2: A generic news URL that might have a "load more" or dynamic elements
    # Replace with an actual URL you expect to have such features for testing.
    # dynamic_test_url = "https://www.scrapingcourse.com/button-click/" # A known test site for button clicks
    # print(f"\n--- Testing URL with potential 'Load More' button: {dynamic_test_url} ---")
    # content_dynamic, final_dynamic_url = download_article_content(dynamic_test_url)
    # if content_dynamic:
    #     print(f"Successfully fetched dynamic content from {final_dynamic_url}. Size: {len(content_dynamic)} bytes.")
    #     # soup_dynamic = BeautifulSoup(content_dynamic, 'html.parser')
    #     # items = soup_dynamic.select(".product-item.product-name") # Example selector for the test site
    #     # print(f"Found {len(items)} product names on {final_dynamic_url}.")
    #     # for item in items:
    #     #     print(f"- {item.get_text(strip=True)}")
    # else:
    #     print(f"Failed to fetch content from {dynamic_test_url}")

    # Test Case 3: A simple static page (should be handled by Playwright or fallback)
    # static_test_url = "http://books.toscrape.com/"
    # print(f"\n--- Testing a relatively static URL: {static_test_url} ---")
    # content_static, final_static_url = download_article_content(static_test_url)
    # if content_static:
    #     print(f"Successfully fetched static content from {final_static_url}. Size: {len(content_static)} bytes.")
    # else:
    #     print(f"Failed to fetch content from {static_test_url}")