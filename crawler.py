import urllib.request
import urllib.parse
import json
import re
import sys
import os
import argparse
import webbrowser
from bs4 import BeautifulSoup

# Define helper to clean and extract price
def extract_numeric_price(price_str):
    if not price_str:
        return 0.0
    # Find all digits and commas/dots
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
    from concurrent.futures import ThreadPoolExecutor
    print(f"\n[PChome 24h] 正在搜尋: '{keyword}' (共 {max_pages} 頁)...")
    all_products = []
    chunk_size = 10
    pages = list(range(1, max_pages + 1))
    
    for i in range(0, len(pages), chunk_size):
        chunk = pages[i:i+chunk_size]
        if i > 0:
            import time
            time.sleep(0.5)
            
        with ThreadPoolExecutor(max_workers=len(chunk)) as executor:
            futures = [executor.submit(scrape_pchome_page, keyword, p) for p in chunk]
            for fut in futures:
                all_products.extend(fut.result())
                
    print(f"[PChome 24h] 成功爬取 {len(all_products)} 項商品。")
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
    from concurrent.futures import ThreadPoolExecutor
    print(f"\n[Yahoo 購物中心] 正在搜尋: '{keyword}' (共 {max_pages} 頁)...")
    all_products = []
    chunk_size = 10
    pages = list(range(1, max_pages + 1))
    
    for i in range(0, len(pages), chunk_size):
        chunk = pages[i:i+chunk_size]
        if i > 0:
            import time
            time.sleep(0.5)
            
        with ThreadPoolExecutor(max_workers=len(chunk)) as executor:
            futures = [executor.submit(scrape_yahoo_page, keyword, p) for p in chunk]
            for fut in futures:
                all_products.extend(fut.result())
                
    print(f"[Yahoo 購物中心] 成功爬取 {len(all_products)} 項商品。")
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
    from concurrent.futures import ThreadPoolExecutor
    print(f"\n[Amazon 亞馬遜] 正在搜尋: '{keyword}' (共 {max_pages} 頁)...")
    all_products = []
    chunk_size = 10
    pages = list(range(1, max_pages + 1))
    
    for i in range(0, len(pages), chunk_size):
        chunk = pages[i:i+chunk_size]
        if i > 0:
            import time
            time.sleep(0.5)
            
        with ThreadPoolExecutor(max_workers=len(chunk)) as executor:
            futures = [executor.submit(scrape_amazon_page, keyword, p) for p in chunk]
            for fut in futures:
                all_products.extend(fut.result())
                
    print(f"[Amazon 亞馬遜] 成功爬取 {len(all_products)} 項商品。")
    return all_products

def scrape_shopee(keyword, max_pages=3):
    print(f"\n[蝦皮購物] 正在啟動 Playwright 爬取: '{keyword}' (共 {max_pages} 頁)...")
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
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                locale="zh-TW",
                viewport={"width": 1280, "height": 800}
            )
            
            for page_idx in range(max_pages):
                if page_idx > 0:
                    import time
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
                        
                    if page.locator('text="登入以繼續"').count() > 0 or page.locator('text="頁面無法顯示"').count() > 0:
                        print("[蝦皮購物] 檢測到登入牆。請在開啟的瀏覽器視窗中完成登入/驗證。程式將暫停等待...")
                        try:
                            page.wait_for_selector('div[data-sqe="item"]', timeout=60000)
                            print("[蝦皮購物] 驗證成功，開始載入商品！")
                        except Exception:
                            print("[蝦皮購物] 等待登入/驗證超時，跳過本頁。")
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
            print(f"[蝦皮購物] 成功爬取 {len(products)} 項商品。")
            return products
    except Exception as e:
        print(f"[蝦皮購物] 失敗: {e}")
        return []

def scrape_surugaya(keyword):
    print(f"\n[駿河屋] 正在啟動瀏覽器以搜尋: '{keyword}'...")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[駿河屋] 錯誤: 未安裝 Playwright 模組。請執行 'pip install playwright' 並執行 'playwright install'。")
        return []

    STEALTH_JS = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    products = []
    
    try:
        with sync_playwright() as p:
            # Launch headfully because Cloudflare Turnstile blocks headless chromium easily
            # Setting headless=False allows the user to complete verification if triggered.
            print("[駿河屋] 啟動 Chromium 瀏覽器 (可見視窗)...")
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                locale="ja-JP"
            )
            page = context.new_page()
            page.add_init_script(STEALTH_JS)
            
            url = f"https://www.suruga-ya.jp/search?category=&search_word={urllib.parse.quote(keyword)}&searchbox=1"
            print(f"[駿河屋] 正在前往網頁: {url}")
            page.goto(url, wait_until="domcontentloaded")
            
            # Wait for content to render, or wait for selector
            print("[駿河屋] 正在等待商品列表載入 (若出現驗證碼，請在瀏覽器視窗中點選驗證)...")
            try:
                # Wait for any of the product items to appear
                page.wait_for_selector('div.item, li.item, .search_result_item', timeout=30000)
                print("[駿河屋] 商品列表載入成功！")
            except Exception as e:
                print(f"[駿河屋] 等待商品列表超時 (可能卡在驗證碼或查無此商品): {e}")
            
            # Extract items
            raw_data = page.evaluate('''() => {
                const items = document.querySelectorAll('.search_result_item, div.item, li.item, .item');
                const result = [];
                items.forEach(item => {
                    // Try different possible class mappings for title
                    const titleElement = item.querySelector('.title, .item_title, .product_name, .name') || item.querySelector('a');
                    const title = titleElement ? titleElement.innerText : "";
                    
                    // Try to get price
                    const priceElement = item.querySelector('.price, .item_price, .product_price');
                    const price = priceElement ? priceElement.innerText : "0";
                    
                    // Try to get link
                    const aElement = item.querySelector('a');
                    const link = aElement ? aElement.href : "";
                    
                    // Try to get image
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
                # If price is 0, let's try to extract from title or other texts, or keep it
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
            print(f"[駿河屋] 成功爬取 {len(products)} 項商品。")
            return products
    except Exception as e:
        print(f"[駿河屋] 爬取時發生錯誤: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="關鍵字商品比價爬蟲")
    parser.add_argument("--keyword", "-k", type=str, help="搜尋商品關鍵字")
    parser.add_argument("--surugaya", "-s", action="store_true", help="是否啟用日方駿河屋爬取 (需要 Playwright)")
    parser.add_argument("--shopee", "-sh", action="store_true", help="是否啟用蝦皮購物爬取 (需要 Playwright)")
    parser.add_argument("--amazon", "-am", action="store_true", help="是否啟用亞馬遜爬取")
    parser.add_argument("--pages", "-p", type=int, default=3, help="爬取頁數 (預設為 3)")
    args = parser.parse_args()
    
    keyword = args.keyword
    if not keyword:
        keyword = input("請輸入想要比價的商品關鍵字：").strip()
        if not keyword:
            print("錯誤: 搜尋關鍵字不能為空！")
            sys.exit(1)
            
    # Run scrapers
    pchome_items = scrape_pchome(keyword, args.pages)
    yahoo_items = scrape_yahoo(keyword, args.pages)
    amazon_items = []
    surugaya_items = []
    shopee_items = []
    
    if args.amazon:
        amazon_items = scrape_amazon(keyword, args.pages)
    else:
        print("\n[亞馬遜] 已跳過 (如需爬取日本亞馬遜商品，請加上參數 -am 或 --amazon)")
        
    if args.surugaya:
        surugaya_items = scrape_surugaya(keyword)
    else:
        print("\n[駿河屋] 已跳過 (如需爬取日本駿河屋商品，請加上參數 -s 或 --surugaya)")
        
    if args.shopee:
        shopee_items = scrape_shopee(keyword, args.pages)
    else:
        print("\n[蝦皮] 已跳過 (如需爬取蝦皮商品，請加上參數 -sh 或 --shopee)")
        
    all_items = pchome_items + yahoo_items + amazon_items + surugaya_items + shopee_items
    
    # Sort by price (TWD first, JPY conversions handled on UI)
    all_items.sort(key=lambda x: x['price'])
    
    # Structure the output data
    output_data = {
        'keyword': keyword,
        'timestamp': urllib.parse.quote(urllib.parse.quote("")), # placeholder, let's just write format in JS
        'items': all_items
    }
    
    # Write to results.js (to bypass local browser CORS issues)
    js_content = f"window.crawlerResults = {json.dumps(output_data, ensure_ascii=False, indent=2)};"
    
    results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.js")
    with open(results_path, "w", encoding="utf-8") as f:
        f.write(js_content)
        
    print(f"\n[完成] 共爬取 {len(all_items)} 筆商品比價資料。")
    print(f"資料已寫入: {results_path}")
    
    # Open local HTML visualization
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    
    # If running on local server (as specified in AGENTS.md), use localhost URL, otherwise file URL
    local_url = "http://localhost:8000/index.html"
    print(f"正在瀏覽器開啟比價清單：{local_url}")
    
    try:
        # We can try to open both so user has immediate access
        webbrowser.open(local_url)
    except Exception:
        webbrowser.open(f"file:///{html_path.replace(os.sep, '/')}")

if __name__ == "__main__":
    main()
