import urllib.request
import urllib.parse
import json
import re
import os
import sys
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from concurrent.futures import ThreadPoolExecutor

# Reconfigure stdout/stderr to UTF-8 to prevent CP950 UnicodeEncodeError on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def is_headless_env():
    # Detect if running on a headless cloud platform (e.g. Render) or Linux without GUI display
    if os.environ.get('RENDER') == 'true':
        return True
    if sys.platform.startswith('linux') and 'DISPLAY' not in os.environ:
        return True
    return False

# Define helper to clean and extract price
def extract_numeric_price(price_str):
    if not price_str:
        return 0.0
    match = re.search(r'[\d,]+', str(price_str))
    if match:
        try:
            return float(match.group(0).replace(',', ''))
        except ValueError:
            return 0.0
    return 0.0

def scrape_pchome_page(keyword, page_num):
    url = f"https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={urllib.parse.quote(keyword)}&page={page_num}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    try:
        res = urllib.request.urlopen(req, timeout=10)
        data = json.loads(res.read().decode('utf-8'))
        products = []
        if 'prods' in data and data['prods']:
            for prod in data['prods']:
                products.append({
                    'title': prod.get('name', '').strip(),
                    'price': float(prod.get('price', 0)),
                    'link': f"https://24h.pchome.com.tw/prod/{prod.get('Id')}",
                    'image': f"https://f.ecimg.tw{prod.get('picB')}" if prod.get('picB') else "",
                    'source': 'PChome 24h',
                    'currency': 'TWD',
                    'sales': 0
                })
        return products
    except Exception as e:
        print(f"[PChome 24h] 頁數 {page_num} 失敗: {e}")
        return []

def scrape_pchome(keyword, max_pages=3):
    print(f"[PChome 24h] 正在爬取: '{keyword}' (共 {max_pages} 頁)...")
    all_products = []
    chunk_size = 10
    pages = list(range(1, max_pages + 1))
    
    for i in range(0, len(pages), chunk_size):
        chunk = pages[i:i+chunk_size]
        if i > 0:
            time.sleep(0.5)
            
        with ThreadPoolExecutor(max_workers=len(chunk)) as executor:
            futures = [executor.submit(scrape_pchome_page, keyword, p) for p in chunk]
            for fut in futures:
                all_products.extend(fut.result())
                
    print(f"[PChome 24h] 成功，共取得 {len(all_products)} 項商品。")
    return all_products

def scrape_yahoo_page(keyword, page_num):
    url = f"https://tw.buy.yahoo.com/search/product?p={urllib.parse.quote(keyword)}&pg={page_num}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    try:
        res = urllib.request.urlopen(req, timeout=10)
        html = res.read().decode('utf-8')
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        for script in soup.find_all('script'):
            content = script.string or ""
            if '"ecsearch"' in content:
                data = json.loads(content)
                hits = data.get('search', {}).get('ecsearch', {}).get('hits', [])
                for hit in hits:
                    img_url = hit.get('ec_image', '')
                    if img_url and not img_url.startswith('http') and not img_url.startswith('//'):
                        img_url = f"https://s.yimg.com/zp/MerchandiseImages/{img_url}"
                    products.append({
                        'title': hit.get('ec_title', '').strip(),
                        'price': float(hit.get('ec_price', 0)),
                        'link': hit.get('ec_item_url'),
                        'image': img_url,
                        'source': 'Yahoo 購物中心',
                        'currency': 'TWD',
                        'sales': int(hit.get('ec_total_sales_count') or 0)
                    })
                break
        return products
    except Exception as e:
        print(f"[Yahoo 購物中心] 頁數 {page_num} 失敗: {e}")
        return []

def scrape_yahoo(keyword, max_pages=3):
    print(f"[Yahoo 購物中心] 正在爬取: '{keyword}' (共 {max_pages} 頁)...")
    all_products = []
    chunk_size = 10
    pages = list(range(1, max_pages + 1))
    
    for i in range(0, len(pages), chunk_size):
        chunk = pages[i:i+chunk_size]
        if i > 0:
            time.sleep(0.5)
            
        with ThreadPoolExecutor(max_workers=len(chunk)) as executor:
            futures = [executor.submit(scrape_yahoo_page, keyword, p) for p in chunk]
            for fut in futures:
                all_products.extend(fut.result())
                
    print(f"[Yahoo 購物中心] 成功，共取得 {len(all_products)} 項商品。")
    return all_products

def scrape_amazon_page(keyword, page_num):
    url = f"https://www.amazon.co.jp/s?k={urllib.parse.quote(keyword)}&page={page_num}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
    })
    try:
        res = urllib.request.urlopen(req, timeout=15)
        html = res.read().decode('utf-8')
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        if "api-services-support@amazon.com" in html or "Type the characters you see below" in html:
            print(f"[Amazon 亞馬遜] 頁數 {page_num} 被機器人驗證攔截。")
            return []
            
        items = soup.select('div[data-component-type="s-search-result"]')
        products = []
        for item in items:
            h2 = item.find('h2')
            if not h2:
                continue
            title = h2.text.strip()
            
            link = ""
            a_tag = h2.find_parent('a') or h2.find('a') or item.select_one('a.a-link-normal')
            if a_tag:
                link = a_tag.get('href', '')
                if link and not link.startswith('http'):
                    link = f"https://www.amazon.co.jp{link}"
            
            price_whole = item.select_one('.a-price-whole')
            price = 0.0
            currency = "JPY"
            if price_whole:
                try:
                    price = float(price_whole.text.replace(',', '').strip())
                except ValueError:
                    price = 0.0
                
                parent_price = price_whole.find_parent(class_="a-price")
                if parent_price:
                    parent_text = parent_price.text
                    if "TWD" in parent_text or "$" in parent_text:
                        currency = "TWD"
            
            img = item.find('img', class_='s-image')
            img_url = img.get('src', '') if img else ""
            
            all_text = item.get_text(" ")
            bought_match = re.search(r'過去1[かヶ]月[でに]([\d,萬万+]+)[點点]以上購入されました', all_text)
            sales = 0
            if bought_match:
                bought_str = bought_match.group(1).replace(',', '').replace('+', '').strip()
                if '萬' in bought_str or '万' in bought_str:
                    try:
                        sales = int(float(bought_str.replace('萬', '').replace('万', '')) * 10000)
                    except ValueError:
                        sales = 0
                else:
                    try:
                        sales = int(bought_str)
                    except ValueError:
                        sales = 0
            
            products.append({
                'title': title,
                'price': price,
                'link': link,
                'image': img_url,
                'source': 'Amazon 亞馬遜',
                'currency': currency,
                'sales': sales
            })
        return products
    except Exception as e:
        print(f"[Amazon 亞馬遜] 頁數 {page_num} 失敗: {e}")
        return []

def scrape_amazon(keyword, max_pages=3):
    print(f"[Amazon 亞馬遜] 正在爬取: '{keyword}' (共 {max_pages} 頁)...")
    all_products = []
    chunk_size = 10
    pages = list(range(1, max_pages + 1))
    
    for i in range(0, len(pages), chunk_size):
        chunk = pages[i:i+chunk_size]
        if i > 0:
            time.sleep(0.5)
            
        with ThreadPoolExecutor(max_workers=len(chunk)) as executor:
            futures = [executor.submit(scrape_amazon_page, keyword, p) for p in chunk]
            for fut in futures:
                all_products.extend(fut.result())
                
    print(f"[Amazon 亞馬遜] 成功，共取得 {len(all_products)} 項商品。")
    return all_products

def scrape_shopee(keyword, max_pages=3):
    print(f"[蝦皮購物] 正在啟動 Playwright 爬取: '{keyword}' (共 {max_pages} 頁)...")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[蝦皮購物] 未安裝 Playwright，跳過。")
        return []

    STEALTH_JS = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_dir = os.path.join(script_dir, ".shopee_user_data")
    
    products = []
    
    try:
        with sync_playwright() as p:
            print("[蝦皮購物] 啟動 Chromium 瀏覽器並加載登入會話...")
            using_persistent = True
            browser = None
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=is_headless_env(),
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    locale="zh-TW",
                    viewport={"width": 1280, "height": 800},
                    ignore_default_args=["--enable-automation"],
                    args=["--disable-blink-features=AutomationControlled"]
                )
            except Exception as e_launch:
                print(f"[蝦皮購物] 無法開啟持久化瀏覽器會話 (可能目錄被鎖定): {e_launch}。嘗試使用臨時無痕會話...")
                using_persistent = False
                browser = p.chromium.launch(
                    headless=is_headless_env(),
                    ignore_default_args=["--enable-automation"],
                    args=["--disable-blink-features=AutomationControlled"]
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    locale="zh-TW",
                    viewport={"width": 1280, "height": 800}
                )
            
            for page_idx in range(max_pages):
                if page_idx > 0:
                    time.sleep(1.0)
                
                page = context.new_page()
                page.add_init_script(STEALTH_JS)
                
                url = f"https://shopee.tw/search?keyword={urllib.parse.quote(keyword)}&page={page_idx}"
                print(f"[蝦皮購物] 正在爬取第 {page_idx + 1} 頁: {url}")
                
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    
                    try:
                        page.wait_for_selector('text="繁體中文", div[data-sqe="item"], text="登入", text="頁面無法顯示"', timeout=10000)
                    except Exception:
                        pass
                    
                    lang_btn = page.locator('text="繁體中文"')
                    if lang_btn.count() > 0 and lang_btn.first.is_visible():
                        print("[蝦皮購物] 檢測到語言選擇器，點選繁體中文...")
                        lang_btn.first.click()
                        time.sleep(1.5)
                        
                    is_blocked = (
                        "verify/traffic" in page.url or 
                        "verify" in page.url or
                        page.locator('text="登入以繼續"').count() > 0 or 
                        page.locator('text="頁面無法顯示"').count() > 0
                    )
                    if is_blocked:
                        print("[蝦皮購物] 檢測到人機滑塊驗證碼或登入牆！請在彈出的瀏覽器視窗中「完成滑塊拼圖」或點選「登入」。程式將暫停等待驗證成功...")
                        try:
                            page.wait_for_selector('div[data-sqe="item"]', timeout=90000)
                            print("[蝦皮購物] 驗證成功，已進入商品頁面！")
                        except Exception:
                            print("[蝦皮購物] 等待驗證/登入超時，跳過本頁。")
                            page.close()
                            continue
                    
                    try:
                        page.wait_for_selector('div[data-sqe="item"]', timeout=15000)
                    except Exception:
                        print(f"[蝦皮購物] 第 {page_idx + 1} 頁未發現商品列表 (可能該頁無商品或防爬阻擋)。")
                        page.close()
                        continue
                    
                    page.evaluate("window.scrollBy(0, 1000);")
                    time.sleep(0.5)
                    page.evaluate("window.scrollBy(0, 2000);")
                    time.sleep(0.5)
                    page.evaluate("window.scrollBy(0, 3000);")
                    time.sleep(0.5)
                    
                    raw_data = page.evaluate('''() => {
                        const items = document.querySelectorAll('div[data-sqe="item"]');
                        const result = [];
                        items.forEach(item => {
                            const titleEl = item.querySelector('div[data-sqe="name"]');
                            const title = titleEl ? titleEl.innerText : "";
                            
                            const priceEls = item.querySelectorAll('div.font-medium, div.text-primary, ._1d6S5E');
                            let priceText = "0";
                            if (priceEls.length > 0) {
                                priceText = Array.from(priceEls).map(el => el.innerText).join(" ");
                            }
                            
                            const aEl = item.querySelector('a');
                            const link = aEl ? aEl.href : "";
                            
                            const imgEl = item.querySelector('img');
                            const image = imgEl ? imgEl.src : "";
                            
                            const salesEl = item.querySelector('.text-muted, .text-xs, ._229v_1, div[style*="font-size: 0.75rem"]');
                            const salesText = salesEl ? salesEl.innerText : "";
                            
                            if (title && link) {
                                result.push({
                                    title: title.replace(/\\n/g, ' ').trim(),
                                    priceText: priceText,
                                    link: link,
                                    image: image,
                                    salesText: salesText
                                });
                            }
                        });
                        return result;
                    }''')
                    
                    for item in raw_data:
                        price_val = 0.0
                        price_parts = item['priceText'].split('-')
                        if price_parts:
                            match = re.search(r'[\d,]+', price_parts[0])
                            if match:
                                try:
                                    price_val = float(match.group(0).replace(',', ''))
                                except ValueError:
                                    pass
                        
                        sales_val = 0
                        sales_text = item['salesText']
                        bought_match = re.search(r'(?:已售出|已售)\s*([\d,.]+)\s*(萬|万|k)?', sales_text)
                        if bought_match:
                            num_str = bought_match.group(1).replace(',', '')
                            unit = bought_match.group(2)
                            try:
                                val = float(num_str)
                                if unit in ('萬', '万'):
                                    sales_val = int(val * 10000)
                                elif unit == 'k':
                                    sales_val = int(val * 1000)
                                else:
                                    sales_val = int(val)
                            except ValueError:
                                pass
                        
                        products.append({
                            'title': item['title'],
                            'price': price_val,
                            'link': item['link'],
                            'image': item['image'],
                            'source': '蝦皮購物',
                            'currency': 'TWD',
                            'sales': sales_val
                        })
                        
                    page.close()
                except Exception as e_page:
                    print(f"[蝦皮購物] 第 {page_idx + 1} 頁爬取失敗: {e_page}")
                    try:
                        page.close()
                    except Exception:
                        pass
            
            context.close()
            if not using_persistent and browser:
                browser.close()
            print(f"[蝦皮購物] 成功，共取得 {len(products)} 項商品。")
            return products
    except Exception as e:
        print(f"[蝦皮購物] 失敗: {e}")
        return []

def scrape_surugaya(keyword):
    print(f"[駿河屋] 正在啟動 Playwright 爬取: '{keyword}'...")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[駿河屋] 未安裝 Playwright，跳過。")
        return []

    STEALTH_JS = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    products = []
    
    try:
        with sync_playwright() as p:
            # Setting headless mode dynamically based on running environment
            browser = p.chromium.launch(
                headless=is_headless_env(),
                ignore_default_args=["--enable-automation"],
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                locale="ja-JP"
            )
            page = context.new_page()
            page.add_init_script(STEALTH_JS)
            
            url = f"https://www.suruga-ya.jp/search?category=&search_word={urllib.parse.quote(keyword)}&searchbox=1"
            page.goto(url, wait_until="domcontentloaded")
            
            # Wait for content to render, or wait for selector
            print("[駿河屋] 正在等待商品列表載入 (若出現驗證碼，請在瀏覽器視窗中點選驗證)...")
            try:
                # Wait for any of the product items to appear
                page.wait_for_selector('div.item, li.item, .search_result_item', timeout=30000)
                print("[駿河屋] 商品列表載入成功！")
            except Exception as e:
                print(f"[駿河屋] 等待商品列表超時 (可能卡在驗證碼或查無此商品): {e}")
            
            raw_data = page.evaluate('''() => {
                const items = document.querySelectorAll('.search_result_item, div.item, li.item, .item');
                const result = [];
                items.forEach(item => {
                    const titleElement = item.querySelector('.title, .item_title, .product_name, .name') || item.querySelector('a');
                    const title = titleElement ? titleElement.innerText : "";
                    
                    const priceElement = item.querySelector('.price, .item_price, .product_price');
                    const price = priceElement ? priceElement.innerText : "0";
                    
                    const aElement = item.querySelector('a');
                    const link = aElement ? aElement.href : "";
                    
                    const imgElement = item.querySelector('img');
                    const image = imgElement ? imgElement.src : "";
                    
                    if (title && link) {
                        result.push({
                            title: title.replace(/\\n/g, ' ').trim(),
                            price: price,
                            link: link,
                            image: image
                        });
                    }
                });
                return result;
            }''')
            
            for item in raw_data:
                price_val = extract_numeric_price(item['price'])
                products.append({
                    'title': item['title'],
                    'price': price_val,
                    'link': item['link'],
                    'image': item['image'],
                    'source': '駿河屋',
                    'currency': 'JPY',
                    'sales': 0
                })
            
            browser.close()
            print(f"[駿河屋] 成功，取得 {len(products)} 項商品。")
            return products
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[駿河屋] 失敗: {e}")
        return []

# Custom Request Handler
class LiveCompareHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        
        # Route to API endpoint
        if parsed_url.path == '/api/compare':
            try:
                query_params = urllib.parse.parse_qs(parsed_url.query)
                keyword = query_params.get('q', [''])[0]
                include_surugaya = query_params.get('surugaya', ['false'])[0].lower() == 'true'
                include_shopee = query_params.get('shopee', ['false'])[0].lower() == 'true'
                include_amazon = query_params.get('amazon', ['false'])[0].lower() == 'true'
                
                if not keyword:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Keyword parameter "q" is required'}, ensure_ascii=False).encode('utf-8'))
                    return
                    
                # Parse pages count (default to 3 pages)
                max_pages = 3
                try:
                    max_pages = int(query_params.get('pages', ['3'])[0])
                    if max_pages < 1:
                        max_pages = 3
                except ValueError:
                    max_pages = 3
                    
                print(f"\n[API 請求] 搜尋關鍵字: '{keyword}' (頁數: {max_pages}, 駿河屋: {include_surugaya}, 蝦皮: {include_shopee}, 亞馬遜: {include_amazon})")
                
                # Scrape PChome, Yahoo and Amazon in parallel using thread pool
                pchome_items = []
                yahoo_items = []
                amazon_items = []
                
                workers = 2
                if include_amazon:
                    workers += 1
                    
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    future_pchome = executor.submit(scrape_pchome, keyword, max_pages)
                    future_yahoo = executor.submit(scrape_yahoo, keyword, max_pages)
                    
                    future_amazon = None
                    if include_amazon:
                        future_amazon = executor.submit(scrape_amazon, keyword, max_pages)
                        
                    try:
                        pchome_items = future_pchome.result(timeout=90)
                    except Exception as e_pc:
                        print(f"[PChome 24h] 失敗或超時: {e_pc}")
                        
                    try:
                        yahoo_items = future_yahoo.result(timeout=90)
                    except Exception as e_yh:
                        print(f"[Yahoo 購物中心] 失敗或超時: {e_yh}")
                        
                    if include_amazon and future_amazon:
                        try:
                            amazon_items = future_amazon.result(timeout=90)
                        except Exception as e_am:
                            print(f"[Amazon 亞馬遜] 失敗或超時: {e_am}")
                    
                # Scrape Surugaya (synchronously as it opens a browser window)
                surugaya_items = []
                if include_surugaya:
                    try:
                        surugaya_items = scrape_surugaya(keyword)
                    except Exception as e_su:
                        print(f"[駿河屋] 失敗: {e_su}")
                    
                # Scrape Shopee (synchronously as it opens a browser window with persistent login profile)
                shopee_items = []
                if include_shopee:
                    try:
                        shopee_items = scrape_shopee(keyword, max_pages)
                    except Exception as e_sh:
                        print(f"[蝦皮購物] 失敗: {e_sh}")
                    
                all_items = pchome_items + yahoo_items + amazon_items + surugaya_items + shopee_items
                all_items.sort(key=lambda x: x['price'])
                
                # Return JSON
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response_data = {
                    'keyword': keyword,
                    'items': all_items
                }
                
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
                print(f"[API 回應] 成功回傳 {len(all_items)} 筆比價商品資料。\n")
            except Exception as e_global:
                print(f"[API 全局錯誤] {e_global}")
                import traceback
                traceback.print_exc()
                try:
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    err_response = {
                        'keyword': keyword if 'keyword' in locals() else '',
                        'items': [],
                        'error': f'伺服器全局錯誤: {str(e_global)}'
                    }
                    self.wfile.write(json.dumps(err_response, ensure_ascii=False).encode('utf-8'))
                except Exception:
                    pass
            
        else:
            # Default to static file server
            # Serve index.html if root is requested
            # If the user requests root "/", let's redirect/serve index.html directly
            if parsed_url.path == '/':
                self.path = '/index.html'
            super().do_GET()

def main():
    port = int(os.environ.get('PORT', 8000))
    server_address = ('', port)
    
    # Switch working directory to server.py directory to serve static files correctly
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    httpd = ThreadingHTTPServer(server_address, LiveCompareHandler)
    print("=" * 60)
    print(f"  商品即時比價伺服器已成功啟動！")
    print(f"  請在瀏覽器開啟： http://localhost:{port}/index.html")
    print("=" * 60)
    
    # Auto-open browser
    try:
        webbrowser.open(f"http://localhost:{port}/index.html")
    except Exception:
        pass
        
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n伺服器已關閉。")
        sys.exit(0)

if __name__ == "__main__":
    main()
