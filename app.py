from flask import Flask, request, jsonify, send_from_directory
import requests
import os
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup

app = Flask(__name__, static_folder='.')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
}

def scrape_pchome(keyword):
    url = f"https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={requests.utils.quote(keyword)}&page=1"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        data = res.json()
        products = []
        for prod in data.get('prods', []):
            products.append({
                'title': prod.get('name', '').strip(),
                'price': float(prod.get('price', 0)),
                'link': f"https://24h.pchome.com.tw/prod/{prod.get('Id')}",
                'source': 'PChome 24h'
            })
        return products
    except Exception:
        return []

def scrape_surugaya(keyword):
    """駿河屋搜尋爬蟲"""
    # 駿河屋搜尋網址
    url = f"https://www.suruga-ya.jp/search?category=&search_word={requests.utils.quote(keyword)}&inStock=on"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        products = []
        # 需根據駿河屋當前的 HTML 結構調整選擇器
        items = soup.select('.item_list_box') # 取前 5 個結果[:5]
        for item in items:
            title = item.select_one('.title a').text.strip()
            price_str = item.select_one('.price').text.replace('￥', '').replace(',', '').strip()
            link = "https://www.suruga-ya.jp" + item.select_one('.title a')['href']
            products.append({
                'title': title,
                'price': float(price_str) * 0.22, # 簡易匯率換算 (日幣轉台幣)
                'link': link,
                'source': '駿河屋 (Surugaya)'
            })
        return products
    except Exception:
        return []

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/compare')
def compare():
    keyword = request.args.get('q', '')
    if not keyword:
        return jsonify({'error': '請輸入關鍵字'}), 400
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(scrape_pchome, keyword)
        f2 = executor.submit(scrape_surugaya, keyword)
        items = f1.result() + f2.result()
        
    items.sort(key=lambda x: x['price'])
    return jsonify({'keyword': keyword, 'items': items})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
