# AI 開發 Prompt 與技術指令設計指南 (AI Development Prompts & Guidelines)

本專案由 AI 助理 (Antigravity) 與開發者 pair programming 共同協作完成。本文件記錄了用於引導 AI 建構此系統的核心 Prompt 設計、功能疊代邏輯與防爬蟲反制作業的最佳實踐，旨在方便未來系統重構、平台新增與功能擴充。

---

## 💡 功能設計 Prompt 演進脈絡

### 1. 基礎核心構建 Prompt (時鐘主頁 + 比價靜態原型)
> **Prompt 範例**：
> 「請幫我建立一個靜態比價網頁與即時時鐘主頁。使用 Vanilla HTML/CSS/JavaScript，頁面設計必須具備現代科技感、暗黑模式，並使用 `zh-TW` 語系呈現 24 小時制的時鐘。比價頁面先讀取本地 results.js 商品資料，展示 PChome 24h 與 Yahoo 購物中心的商品列表，支援價格由低到高排序與搜尋框過濾。」

* **技術成果**：建構出 [index.html](file:///d:/data/index.html) 比價首頁的基礎設計系統、磨砂玻璃視覺風格 (Glassmorphic Card) 與基本的商品資料格點渲染。

---

### 2. 後端伺服器化 Prompt (Parallel Thread Scrapers)
> **Prompt 範例**：
> 「我們不希望每次都讀取靜態本地檔案，請幫我用 Python 標準程式庫建構一個極簡的 Web 伺服器 `server.py`。
> 1. 當使用者訪問 `/` 時，靜態託管 `index.html`。
> 2. 提供 `/api/compare?q=關鍵字&pages=頁數` API 端點。
> 3. 後端使用 `ThreadPoolExecutor` (執行緒池) 以平行並發方式同時向 PChome (JSON API) 與 Yahoo 購物中心 (BeautifulSoup HTML 解析) 爬取指定頁數 (預設 3 頁)，並將結果合併排序後以 JSON 格式回傳給前端。
> 4. 前端新增一個玻璃霧面的 Loading Overlay 載入動畫，點選『即時比價』按鈕時發送 fetch 請求更新數據，無須重載頁面。」

* **技術成果**：實作了並行爬取架構，在不依賴 Flask/FastAPI 的情況下，僅用 Python `http.server` 即實作出動態 HTTP API。

---

### 3. 日本駿河屋與 Cloudflare 繞過 Prompt (Playwright Headful Scraper)
> **Prompt 範例**：
> 「我想要引入日本駿河屋 (Surugaya) 的中古商品進行比價。因為該網站採用了 Cloudflare Turnstile 驗證，普通的 urllib 請求會被阻擋。
> 1. 請在後端增加 `scrape_surugaya` 函式，使用 `playwright` 啟動 headful 瀏覽器 (`headless=False`)，並在頁面初始化時注入 webdriver 隱身指令 (`Object.defineProperty(navigator, 'webdriver', {get: () => undefined})`)。
> 2. 爬蟲開啟搜尋網頁後，不使用靜態 sleep，而是動態 `wait_for_selector` 監聽 `.search_result_item` 的出現 (設定 30 秒逾時時間)，讓使用者在觸發人機驗證時能手動點選，完成後自動提取商品名稱、日幣價格與連結。
> 3. 前端儀表板新增『日幣匯率即時滑桿 (TWD/JPY)』，並將駿河屋的日幣計價商品在前端即時換算成台幣進行全局混合排序，但保留卡片上的原幣價格標示。」

---

### 4. 蝦皮購物會話保持與亞馬遜日幣提取 Prompt (Shopee Persistent Session)
> **Prompt 範例**：
> 「我希望在系統中新增蝦皮購物 (Shopee) 與日本亞馬遜 (Amazon JP) 平台支援。這兩個平台的難點如下，請精準實作：
> 1. **日本亞馬遜**：搜尋結果可能因為伺服器地區而將部分價格輸出為台幣 (TWD) 或日幣 (JPY)，請在 class 解析時偵測幣種標誌 (`$` 或 `TWD`) 並給予正確的 `currency` 欄位；使用正則表達式解析 `過去1個月以上購入` 的熱銷數量並記錄。
> 2. **蝦皮購物**：蝦皮有極為嚴格的登入與語言驗證牆。請利用 Playwright 的 `launch_persistent_context` 將使用者會話保存在 `d:\\data\\.shopee_user_data` 資料夾。如果檢測到『登入以繼續』或『頁面無法顯示』，後端暫停等待最多 60 秒，讓使用者完成一次性登入，之後的抓取則自動重用 Session 進行背景無縫抓取；另外實作銷售量轉換器將 `已售出 1.2萬` 及 `3.5k` 等不同文字格式精確轉為整數。
> 3. **防封鎖機制**：當使用者勾選搜尋 50 頁或 100 頁時，為防止 IP 遭封鎖，請實作 Batch Delay 爬取機制：每爬完 10 頁延遲暫停 `0.5s`。」

---

## 🛠️ 常見爬蟲反制與 Playwright 偵錯指南

1. **Playwright 隱身設置 (Playwright Stealth)**:
   在啟動頁面後，務必注入以下 JavaScript 腳本，否則會輕易被 Cloudflare / Shopee 偵測為自動化工具：
   ```python
   STEALTH_JS = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
   page.add_init_script(STEALTH_JS)
   ```

2. **Windows 終端機編碼崩潰問題 (Console CP950 Encoding)**:
   在 Windows 終端機中執行 Python 印出含有日文字元 (如 `~`、`￥`) 或特殊符號的字串時，常會因為 CP950 編碼問題而崩潰。
   * **反制方案**：後端程式碼在執行 print 時進行 try-except 容錯處理，或啟動服務時以 `python -u server.py` 方式執行；Web UI 處理所有字元顯示，後端避免直接在 CLI 印出未經處理的 HTML。

3. **過濾 $0 假價格商品**:
   有些平台未發售的商品 (如預約中的 Switch 2) 或已下架缺貨商品會標示為 $0 元，這會使價格「由低到高」排序時出現大量干擾。
   * **反制方案**：在 `index.html` 的 `render` 函式過濾階段加入：
     ```javascript
     if (item.price <= 0) return false;
     ```
