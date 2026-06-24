# 商品即時比價與多功能儀表板系統 (Real-time Price Comparison & Dashboard)

**網頁DEMO連結：https://jimm1218.github.io/Price_inquiry/**

這是一個基於 Python 後端爬蟲與前端單頁面 (SPA) 互動設計的商品即時比價系統。本專案整合了 **PChome 24h**、**Yahoo 購物中心**、**Amazon 日本亞馬遜**、**蝦皮購物 (Shopee)** 與 **駿河屋 (Surugaya)** 五大電商平台，實現跨平台、跨幣種的商品價格、銷量、圖片與即時比價數據整合儀表板。

---

## 📂 專案資料夾架構 (Project Directory Structure)

```text
d:\data
├── index.html                   # 主頁入口：即時比價前端儀表板 (極致磨砂玻璃風、支援即時搜尋與分頁/排序)
├── server.py                    # 後端極簡 HTTP 伺服器 (提供 /api/compare 即時比價 API)
├── crawler.py                   # 後端命令列比價爬蟲 (支援將結果寫入 results.js 作為靜態備用數據)
├── results.js                   # 比價結果快取備用檔案
├── work_report.md               # 專案開發工作日誌與架構設計報告
├── README.md                    # 本專案的說明文件 (本檔案)
├── prompt.md                    # 引導 AI 助理開發此專案的 Prompt 紀錄與指令設計
│
├── practice/                    # 課堂練習與 Tkinter/Regex 等 Python 腳本練習資料夾
├── media/                       # 專案多媒體資源 (圖片與動畫 SVG 檔案)
└── ssh/                         # 雲端部署相關安全金鑰存放區 (GCP SSH 金鑰等)
```

---

## ✨ 核心特色與功能 (Core Features)

1. **五大電商整合**：
   - **PChome 24h & Yahoo 購物中心**：採用並行執行緒 (Thread Pool) 進行 HTTP 抓取，效率極高。
   - **Amazon 亞馬遜 (日本)**：即時解析日幣價格，支援月銷量數據正則表達式提取。
   - **蝦皮購物 & 駿河屋**：整合 Playwright 自動化爬蟲，並利用 `Stealth.js` 規避 Cloudflare 與 Turnstile 人機驗證防爬。
2. **蝦皮一鍵會話保持**：
   - 使用 Playwright 持久化瀏覽器設定檔 (`.shopee_user_data`)。首次登入後，後續自動重用登入工作階段，完全免去每次爬取皆需手動登入或解 OTP 的繁瑣步驟。
3. **安全抓取設計 (防封鎖)**：
   - 內建**分批安全延遲 (Chunk Delay)** 爬取機制。當請求大量頁面 (e.g. 50 頁、100 頁) 時，自動以 10 頁為單位進行批次排程，並加入 `0.5s` 安全停頓延遲，避免 IP 遭到購物網站阻擋。
4. **極致動態前端 UI**：
   - 使用 **Outfit & Plus Jakarta Sans** 雙字體。
   - **極致磨砂玻璃材質感 (Backdrop Blur Glassmorphism)** 視覺風格。
   - 包含當前最低價、平均價格、平台商品數量分佈的動態統計卡片。
   - 支援**日幣匯率 (TWD/JPY) 即時滑桿調整**，前端商品價格卡片秒級同步重新換算渲染。
   - 支援**商品雙向銷量排序 (高至低、低至高)**、多平台即時篩選、搜尋名稱過濾與 24 筆/頁的暗黑分頁模組。
   - 自動過濾 `Price <= 0` 的無效或未上市/缺貨占位商品。

---

## 🛠️ 開發環境與依賴安裝 (Setup & Installation)

請確保本機已安裝 **Python 3.x**，並依序執行以下命令安裝爬蟲與 Playwright 相關套件：

```bash
# 安裝 Beautiful Soup 4 及 Playwright
pip install beautifulsoup4 playwright

# 初始化 Playwright 瀏覽器核心 (會下載 Chromium 瀏覽器驅動)
playwright install
```

---

## 🚀 執行與使用說明 (Running the Project)

### 1. 啟動比價 Web 服務 (推薦)
在工作目錄 (`d:\data`) 中執行：
```bash
python server.py
```
伺服器啟動後，將自動開啟預設瀏覽器，或手動造訪：
👉 **`http://localhost:8000/index.html`**

#### 🦐 首次使用蝦皮購物爬取設定：
由於蝦皮設有嚴格的登入防爬牆，請先在命令列手動執行一次以下指令，在彈出的瀏覽器視窗中**完成蝦皮登入/OTP 驗證**：
```bash
python crawler.py --shopee -k "switch" -p 1
```
登入完成後即可關閉該瀏覽器。以後在網頁 UI 勾選「同步搜尋蝦皮購物」時即可在背景直接抓取資料。

---

### 2. 獨立使用 CLI 命令行爬蟲
您可以直接在命令列執行 `crawler.py` 來單獨進行比價與產生快取資料：
```bash
# 基礎搜尋：搜尋 PChome 與 Yahoo 並爬取前 3 頁
python crawler.py -k "Switch主機" -p 3

# 進階搜尋：加上日本亞馬遜與日本駿河屋商品
python crawler.py -k "PS5" -p 3 --amazon --surugaya

# 完整抓取：搜尋所有平台 (含蝦皮購物)
python crawler.py -k "LEGO 10333" -p 5 --amazon --shopee --surugaya
```
爬取結果會自動格式化寫入 `results.js`，供離線模式讀取。
