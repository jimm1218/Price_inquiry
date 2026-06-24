import urllib.request
import urllib.parse
import json
import re
import os
import sys
import time
from flask import Flask, request, jsonify, send_from_directory
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup

# Reconfigure stdout/stderr to UTF-8 to prevent CP950 UnicodeEncodeError on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

app = Flask(__name__, static_folder='.')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# ─── Helper ───
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


# ═══════════════════════════════════════════════
#  PChome 24h 爬蟲 (多頁, 純 HTTP API)
# ═══════════════════════════════════════════════
def scrape_pchome_page(keyword, page_num):
    url = f"https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={urllib.parse.quote(keyword)}&page={page_num}"
    req = urllib.request.Request(url, headers=HEADERS)
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
    pages = list(range(1, max_pages + 1))
    chunk_size = 10
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


# ═══════════════════════════════════════════════
#  Yahoo 購物中心爬蟲 (多頁, 純 HTTP)
# ═══════════════════════════════════════════════
def scrape_yahoo_page(keyword, page_num):
    url = f"https://tw.buy.yahoo.com/search/product?p={urllib.parse.quote(keyword)}&pg={page_num}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        res = urllib.request.urlopen(req, timeout=10)
        html = res.read().decode('utf-8')
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
    pages = list(range(1, max_pages + 1))
    chunk_size = 10
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


# ═══════════════════════════════════════════════
#  Amazon 亞馬遜爬蟲 (多頁, 純 HTTP)
# ═══════════════════════════════════════════════
def scrape_amazon_page(keyword, page_num):
    url = f"https://www.amazon.co.jp/s?k={urllib.parse.quote(keyword)}&page={page_num}"
    req = urllib.request.Request(url, headers={
        **HEADERS,
        'Accept-Language': 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
    })
    try:
        res = urllib.request.urlopen(req, timeout=15)
        html = res.read().decode('utf-8')
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
    pages = list(range(1, max_pages + 1))
    chunk_size = 10
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


# ═══════════════════════════════════════════════
#  蝦皮購物爬蟲 (需要 Playwright + 登入)
# ═══════════════════════════════════════════════
def scrape_shopee(keyword, max_pages=2):
    """蝦皮購物爬蟲 - 使用 Playwright headless 模式"""
    print(f"[蝦皮購物] 正在啟動 Playwright 爬取: '{keyword}' (共 {max_pages} 頁)...")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[蝦皮購物] 未安裝 Playwright，跳過。")
        return []

    STEALTH_JS = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    products = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
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
                        page.wait_for_selector('div[data-sqe="item"]', timeout=15000)
                    except Exception:
                        print(f"[蝦皮購物] 第 {page_idx + 1} 頁未發現商品列表。")
                        page.close()
                        continue

                    # Scroll to load more items
                    page.evaluate("window.scrollBy(0, 1000);")
                    time.sleep(0.5)
                    page.evaluate("window.scrollBy(0, 2000);")
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

                            const salesEl = item.querySelector('.text-muted, .text-xs, ._229v_1');
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
                        sales_text = item.get('salesText', '')
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
            browser.close()
            print(f"[蝦皮購物] 成功，共取得 {len(products)} 項商品。")
            return products
    except Exception as e:
        print(f"[蝦皮購物] 失敗: {e}")
        return []


# ═══════════════════════════════════════════════
#  Flask Routes
# ═══════════════════════════════════════════════
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/compare')
def compare():
    keyword = request.args.get('q', '')
    if not keyword:
        return jsonify({'error': 'Keyword parameter "q" is required'}), 400

    include_amazon = request.args.get('amazon', 'false').lower() == 'true'
    include_shopee = request.args.get('shopee', 'false').lower() == 'true'
    include_surugaya = request.args.get('surugaya', 'false').lower() == 'true'

    max_pages = 3
    try:
        max_pages = int(request.args.get('pages', '3'))
        if max_pages < 1:
            max_pages = 3
    except ValueError:
        max_pages = 3

    # ★ 雲端環境限制頁數上限，避免 gunicorn 超時 502
    CLOUD_MAX_PAGES = 10
    if max_pages > CLOUD_MAX_PAGES:
        print(f"[安全限制] 頁數 {max_pages} 超過雲端上限，已降為 {CLOUD_MAX_PAGES} 頁。")
        max_pages = CLOUD_MAX_PAGES

    print(f"\n[API 請求] 搜尋關鍵字: '{keyword}' (頁數: {max_pages}, 亞馬遜: {include_amazon}, 蝦皮: {include_shopee})")

    try:
        # 併發執行 PChome + Yahoo (必定爬取)
        workers = 2
        if include_amazon:
            workers += 1

        pchome_items = []
        yahoo_items = []
        amazon_items = []

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_pchome = executor.submit(scrape_pchome, keyword, max_pages)
            future_yahoo = executor.submit(scrape_yahoo, keyword, max_pages)

            future_amazon = None
            if include_amazon:
                future_amazon = executor.submit(scrape_amazon, keyword, max_pages)

            # 設定超時取得結果，避免無限等待
            try:
                pchome_items = future_pchome.result(timeout=90)
            except Exception as e:
                print(f"[PChome] 超時或失敗: {e}")

            try:
                yahoo_items = future_yahoo.result(timeout=90)
            except Exception as e:
                print(f"[Yahoo] 超時或失敗: {e}")

            if future_amazon:
                try:
                    amazon_items = future_amazon.result(timeout=90)
                except Exception as e:
                    print(f"[Amazon] 超時或失敗: {e}")

        # 蝦皮 (同步，因使用 Playwright 瀏覽器)
        shopee_items = []
        if include_shopee:
            try:
                shopee_items = scrape_shopee(keyword, min(max_pages, 3))
            except Exception as e:
                print(f"[蝦皮] 失敗: {e}")

        all_items = pchome_items + yahoo_items + amazon_items + shopee_items
        all_items.sort(key=lambda x: x['price'])

        print(f"[API 回應] 成功回傳 {len(all_items)} 筆比價商品資料。\n")

        return jsonify({
            'keyword': keyword,
            'items': all_items
        })

    except Exception as e:
        print(f"[API 錯誤] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'keyword': keyword,
            'items': [],
            'error': f'伺服器處理錯誤: {str(e)}'
        }), 500

# Serve static files (JS, CSS, images)
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)