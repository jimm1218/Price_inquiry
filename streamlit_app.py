import streamlit as st
import urllib.request
import urllib.parse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup

# ─── Page Config ───
st.set_page_config(
    page_title="商品即時比價系統 - Live Price Comparison",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS for premium dark theme ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

    /* Global dark theme overrides */
    .stApp {
        background-color: #070913;
        background-image:
            radial-gradient(circle at 10% 20%, rgba(59, 130, 246, 0.08) 0%, transparent 40%),
            radial-gradient(circle at 90% 80%, rgba(123, 31, 162, 0.08) 0%, transparent 45%);
        font-family: 'Plus Jakarta Sans', 'Outfit', system-ui, -apple-system, sans-serif;
    }

    /* Hide Streamlit default elements for cleaner look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {background: transparent;}

    /* Title styling */
    .main-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.4rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        background: linear-gradient(135deg, #ffffff 30%, #a5b4fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
        line-height: 1.2;
    }

    .main-subtitle {
        color: #9ca3af;
        font-size: 1rem;
        margin-bottom: 24px;
    }

    /* Stat cards */
    .stat-card {
        background: rgba(13, 17, 30, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 20px;
        padding: 24px;
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        transition: border-color 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .stat-card:hover {
        border-color: rgba(255, 255, 255, 0.12);
    }

    .stat-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 3px;
    }

    .stat-card.lowest::before { background: linear-gradient(90deg, #10b981, #34d399); }
    .stat-card.average::before { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
    .stat-card.distribution::before { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }

    .stat-label {
        color: #9ca3af;
        font-size: 0.85rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }

    .stat-value {
        color: #f3f4f6;
        font-family: 'Outfit', sans-serif;
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 4px;
    }

    .stat-sub {
        color: #6b7280;
        font-size: 0.82rem;
        line-height: 1.4;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .stat-sub a {
        color: #60a5fa;
        text-decoration: none;
    }

    /* Product card */
    .product-card {
        background: rgba(13, 17, 30, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
        overflow: hidden;
        transition: all 0.3s ease;
        text-decoration: none;
        display: flex;
        flex-direction: column;
    }

    .product-card:hover {
        border-color: rgba(255, 255, 255, 0.15);
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
    }

    .product-card .img-container {
        position: relative;
        background: rgba(255, 255, 255, 0.03);
        aspect-ratio: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }

    .product-card .img-container img {
        max-width: 85%;
        max-height: 85%;
        object-fit: contain;
        transition: transform 0.3s ease;
    }

    .product-card:hover .img-container img {
        transform: scale(1.05);
    }

    .platform-badge {
        position: absolute;
        top: 10px;
        left: 10px;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.72rem;
        font-weight: 600;
        color: white;
        z-index: 2;
    }

    .platform-badge.pchome { background: linear-gradient(135deg, #0b66ff, #004ecc); }
    .platform-badge.yahoo { background: linear-gradient(135deg, #7b1fa2, #4a148c); }
    .platform-badge.amazon { background: linear-gradient(135deg, #ff9900, #ff5500); }

    .product-details {
        padding: 14px;
        display: flex;
        flex-direction: column;
        flex: 1;
    }

    .product-title {
        color: #e5e7eb;
        font-size: 0.88rem;
        font-weight: 500;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin-bottom: 10px;
    }

    .primary-price {
        color: #10b981;
        font-family: 'Outfit', sans-serif;
        font-size: 1.2rem;
        font-weight: 700;
    }

    .converted-price {
        color: #6b7280;
        font-size: 0.78rem;
    }

    .sales-badge {
        background: rgba(245, 158, 11, 0.15);
        border: 1px solid rgba(245, 158, 11, 0.3);
        color: #f59e0b;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        white-space: nowrap;
    }

    /* Loading animation */
    .loading-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 60px 20px;
    }

    .loading-spinner {
        width: 48px;
        height: 48px;
        border: 4px solid rgba(59, 130, 246, 0.2);
        border-top-color: #3b82f6;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-bottom: 16px;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    .loading-text {
        color: #9ca3af;
        font-size: 1rem;
        text-align: center;
    }

    /* Products grid */
    .products-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
        gap: 20px;
        margin-top: 20px;
    }

    /* Empty state */
    .empty-state {
        text-align: center;
        padding: 60px 20px;
        color: #6b7280;
    }

    .empty-icon {
        font-size: 3rem;
        margin-bottom: 16px;
    }

    .empty-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #9ca3af;
        margin-bottom: 8px;
    }

    .empty-desc {
        font-size: 0.95rem;
    }

    /* Pagination */
    .pagination-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 8px;
        margin: 30px 0 20px;
        flex-wrap: wrap;
    }

    .page-btn {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: #9ca3af;
        padding: 8px 14px;
        border-radius: 10px;
        cursor: pointer;
        font-size: 0.9rem;
        transition: all 0.2s;
    }

    .page-btn:hover {
        background: rgba(59, 130, 246, 0.15);
        border-color: rgba(59, 130, 246, 0.3);
        color: #60a5fa;
    }

    .page-btn.active {
        background: rgba(59, 130, 246, 0.2);
        border-color: rgba(59, 130, 246, 0.4);
        color: #3b82f6;
        font-weight: 600;
    }

    .page-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
    }

    .page-info {
        color: #6b7280;
        font-size: 0.85rem;
        margin-left: 12px;
    }

    /* Fix Streamlit form styling */
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        color: #ffffff !important;
        border-radius: 12px !important;
        font-size: 1.05rem !important;
        padding: 14px 20px !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 15px rgba(59, 130, 246, 0.15) !important;
    }

    .stButton > button {
        background: #3b82f6 !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        padding: 14px 30px !important;
        box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4) !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
    }

    .stButton > button:hover {
        background: #2563eb !important;
        transform: translateY(-2px) !important;
    }

    .stSelectbox > div > div {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 10px !important;
    }

    .stCheckbox label span {
        color: #d1d5db !important;
    }

    .stSlider > div > div {
        color: #9ca3af !important;
    }

    /* Divider */
    hr {
        border-color: rgba(255, 255, 255, 0.06) !important;
    }

    div[data-testid="stExpander"] {
        background: rgba(13, 17, 30, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ─── Scraper Functions (ported from server.py) ───

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

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
    except Exception:
        return []

def scrape_pchome(keyword, max_pages=3):
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
    return all_products

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
    except Exception:
        return []

def scrape_yahoo(keyword, max_pages=3):
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
    return all_products

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
    except Exception:
        return []

def scrape_amazon(keyword, max_pages=3):
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
    return all_products


# ─── Initialize Session State ───
if 'items' not in st.session_state:
    st.session_state.items = []
if 'keyword' not in st.session_state:
    st.session_state.keyword = ""
if 'searched' not in st.session_state:
    st.session_state.searched = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

ITEMS_PER_PAGE = 24

# ─── Header ───
st.markdown('<div class="main-title">商品即時比價儀表板 🔍</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">整合 PChome 24h、Yahoo 購物中心、Amazon 亞馬遜的即時爬蟲資料 — Streamlit Cloud 版</div>', unsafe_allow_html=True)

# ─── Search Section ───
col_input, col_btn = st.columns([5, 1])
with col_input:
    query = st.text_input(
        "搜尋關鍵字",
        placeholder="請輸入您想搜尋比價的商品名稱... (例如: Switch, PS5, LEGO)",
        label_visibility="collapsed"
    )
with col_btn:
    search_clicked = st.button("🔍 即時比價", use_container_width=True)

# Search options
col_opt1, col_opt2, col_opt3 = st.columns(3)
with col_opt1:
    include_amazon = st.checkbox("同步搜尋 Amazon 亞馬遜 🇯🇵", value=True)
with col_opt2:
    pages_option = st.selectbox(
        "爬取頁數",
        options=[1, 3, 5, 10],
        index=1,
        format_func=lambda x: f"{x} 頁 (約 {x * 80} 筆)"
    )
with col_opt3:
    jpy_rate = st.slider("日幣匯率 (TWD/JPY)", min_value=0.15, max_value=0.30, value=0.21, step=0.005, format="%.3f")

st.markdown("---")

# ─── Perform Search ───
if search_clicked and query.strip():
    st.session_state.keyword = query.strip()
    st.session_state.current_page = 1

    with st.spinner(f"🔄 正在為您抓取 PChome 24h、Yahoo 購物中心{', Amazon 亞馬遜' if include_amazon else ''} 的最新商品售價 (共 {pages_option} 頁)..."):
        workers = 3 if include_amazon else 2
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_pchome = executor.submit(scrape_pchome, query.strip(), pages_option)
            future_yahoo = executor.submit(scrape_yahoo, query.strip(), pages_option)

            future_amazon = None
            if include_amazon:
                future_amazon = executor.submit(scrape_amazon, query.strip(), pages_option)

            pchome_items = future_pchome.result()
            yahoo_items = future_yahoo.result()
            amazon_items = future_amazon.result() if future_amazon else []

        all_items = pchome_items + yahoo_items + amazon_items
        # Filter out zero-price items
        all_items = [item for item in all_items if item['price'] > 0]
        all_items.sort(key=lambda x: x['price'])

        st.session_state.items = all_items
        st.session_state.searched = True

    st.success(f"✅ 搜尋完成！共取得 **{len(all_items)}** 筆商品 (PChome: {len(pchome_items)}, Yahoo: {len(yahoo_items)}, Amazon: {len(amazon_items)})")

elif search_clicked and not query.strip():
    st.warning("⚠️ 請輸入商品關鍵字！")


# ─── Display Results ───
if st.session_state.searched and st.session_state.items:
    items = st.session_state.items

    # ── Filter & Sort Controls ──
    with st.expander("🎛️ 篩選與排序", expanded=True):
        fcol1, fcol2 = st.columns([3, 1])
        with fcol1:
            filter_text = st.text_input(
                "在結果中篩選",
                placeholder="輸入關鍵字篩選名稱...",
                label_visibility="collapsed"
            )
        with fcol2:
            sort_option = st.selectbox(
                "排序",
                options=["price-asc", "price-desc", "sales-desc", "title-asc"],
                format_func=lambda x: {
                    "price-asc": "💰 價格：由低到高",
                    "price-desc": "💰 價格：由高到低",
                    "sales-desc": "🔥 銷量：由高到低",
                    "title-asc": "🔤 名稱：A-Z"
                }[x],
                label_visibility="collapsed"
            )

        pcol1, pcol2, pcol3 = st.columns(3)
        with pcol1:
            show_pchome = st.checkbox("PChome 24h", value=True)
        with pcol2:
            show_yahoo = st.checkbox("Yahoo 購物中心", value=True)
        with pcol3:
            show_amazon = st.checkbox("Amazon 亞馬遜", value=True)

    # ── Process Items ──
    processed = []
    for item in items:
        display_price = item['price']
        if item['currency'] == 'JPY':
            display_price = item['price'] * jpy_rate

        # Platform filter
        if item['source'] == 'PChome 24h' and not show_pchome:
            continue
        if item['source'] == 'Yahoo 購物中心' and not show_yahoo:
            continue
        if item['source'] == 'Amazon 亞馬遜' and not show_amazon:
            continue

        # Text filter
        if filter_text and filter_text.lower() not in item['title'].lower():
            continue

        processed.append({**item, 'display_price': display_price})

    # Sort
    if sort_option == "price-asc":
        processed.sort(key=lambda x: x['display_price'])
    elif sort_option == "price-desc":
        processed.sort(key=lambda x: x['display_price'], reverse=True)
    elif sort_option == "sales-desc":
        processed.sort(key=lambda x: x.get('sales', 0), reverse=True)
    elif sort_option == "title-asc":
        processed.sort(key=lambda x: x['title'])

    # ── Stats Cards ──
    if processed:
        lowest = min(processed, key=lambda x: x['display_price'])
        avg_price = sum(x['display_price'] for x in processed) / len(processed)
        pchome_c = sum(1 for x in processed if x['source'] == 'PChome 24h')
        yahoo_c = sum(1 for x in processed if x['source'] == 'Yahoo 購物中心')
        amazon_c = sum(1 for x in processed if x['source'] == 'Amazon 亞馬遜')

        stat_cols = st.columns(3)
        with stat_cols[0]:
            st.markdown(f"""
            <div class="stat-card lowest">
                <div class="stat-label">當前最低價</div>
                <div class="stat-value">NT$ {round(lowest['display_price']):,}</div>
                <div class="stat-sub"><a href="{lowest['link']}" target="_blank">[{lowest['source']}] {lowest['title'][:40]}...</a></div>
            </div>
            """, unsafe_allow_html=True)

        with stat_cols[1]:
            st.markdown(f"""
            <div class="stat-card average">
                <div class="stat-label">平均比價價格</div>
                <div class="stat-value">NT$ {round(avg_price):,}</div>
                <div class="stat-sub">計算範圍: 篩選後的 {len(processed)} 項商品</div>
            </div>
            """, unsafe_allow_html=True)

        with stat_cols[2]:
            st.markdown(f"""
            <div class="stat-card distribution">
                <div class="stat-label">平台商品分佈</div>
                <div class="stat-value">{len(processed)} 筆</div>
                <div class="stat-sub">PChome: {pchome_c} | Yahoo: {yahoo_c} | Amazon: {amazon_c}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Pagination ──
        total_pages = max(1, -(-len(processed) // ITEMS_PER_PAGE))  # ceil division
        if st.session_state.current_page > total_pages:
            st.session_state.current_page = total_pages

        start_idx = (st.session_state.current_page - 1) * ITEMS_PER_PAGE
        page_items = processed[start_idx:start_idx + ITEMS_PER_PAGE]

        # ── Product Grid (rendered via HTML for premium look) ──
        def get_source_class(source):
            if source == 'PChome 24h':
                return 'pchome'
            elif source == 'Yahoo 購物中心':
                return 'yahoo'
            else:
                return 'amazon'

        cards_html = '<div class="products-grid">'
        for item in page_items:
            source_class = get_source_class(item['source'])
            img_src = item.get('image') or 'https://img.yec.tw/ma/auc/item/icon/item-no-image.svg'
            safe_title = item['title'].replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
            safe_link = item.get('link', '#')

            # Price HTML
            if item['currency'] == 'JPY':
                price_html = f"""
                    <span class="primary-price">NT$ {round(item['display_price']):,}</span><br>
                    <span class="converted-price">原價 JPY ¥{round(item['price']):,}</span>
                """
            else:
                price_html = f'<span class="primary-price">NT$ {round(item["price"]):,}</span>'

            # Sales badge
            sales_html = ""
            if item.get('sales', 0) > 0:
                sales_html = f'<span class="sales-badge">🔥 已售出 {item["sales"]:,}</span>'

            cards_html += f"""
            <a href="{safe_link}" target="_blank" class="product-card" style="text-decoration: none;">
                <div class="img-container">
                    <span class="platform-badge {source_class}">{item['source']}</span>
                    <img src="{img_src}" alt="{safe_title}" onerror="this.onerror=null; this.src='https://img.yec.tw/ma/auc/item/icon/item-no-image.svg'">
                </div>
                <div class="product-details">
                    <div class="product-title" title="{safe_title}">{safe_title}</div>
                    <div style="margin-top: auto;">
                        {price_html}
                        <div style="margin-top: 6px;">{sales_html}</div>
                    </div>
                </div>
            </a>
            """
        cards_html += '</div>'
        st.markdown(cards_html, unsafe_allow_html=True)

        # ── Pagination Controls ──
        if total_pages > 1:
            st.markdown("<br>", unsafe_allow_html=True)
            nav_cols = st.columns([1, 1, 2, 1, 1])
            with nav_cols[0]:
                if st.button("← 上一頁", disabled=(st.session_state.current_page <= 1), key="prev"):
                    st.session_state.current_page -= 1
                    st.rerun()
            with nav_cols[2]:
                st.markdown(
                    f'<div style="text-align: center; color: #6b7280; padding: 8px;">第 {st.session_state.current_page} / {total_pages} 頁 (共 {len(processed)} 筆商品)</div>',
                    unsafe_allow_html=True
                )
            with nav_cols[4]:
                if st.button("下一頁 →", disabled=(st.session_state.current_page >= total_pages), key="next"):
                    st.session_state.current_page += 1
                    st.rerun()

    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">🔍</div>
            <div class="empty-title">沒有符合的商品</div>
            <div class="empty-desc">試著修改篩選條件，或輸入新關鍵字重新即時比價。</div>
        </div>
        """, unsafe_allow_html=True)

elif not st.session_state.searched:
    # Welcome state
    st.markdown("""
    <div class="empty-state">
        <div class="empty-icon">💡</div>
        <div class="empty-title">歡迎使用即時比價系統</div>
        <div class="empty-desc">請在上方輸入您感興趣的關鍵字，並點選「即時比價」來獲取最新價格！<br><br>
        支援平台：PChome 24h、Yahoo 購物中心、Amazon 亞馬遜 (日本)</div>
    </div>
    """, unsafe_allow_html=True)
