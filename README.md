# L2C1

簡單純前端網頁專案，展示英文名字 `chin chun ping`、`HELLO` 文字，並顯示每秒更新的即時時間。

## 專案內容

- `index.html`: 主頁面，包含樣式、歡迎文案與實時時鐘。
- `0527.py`: 另存的一個 Python 範例檔案。
- `test1.html`、`weather_time.html`: 可能是其他測試或練習用網頁。
- `work_report.md`: 本次專案的報告摘要與執行紀錄。

## 功能

- 以純前端 HTML/CSS/JavaScript 製作頁面，頁面本身為靜態內容，但時鐘為動態更新。
- 顯示中央卡片式樣式內容。
- 每秒更新 `即時時間` 顯示。
- 支援行動裝置與桌機螢幕。

## 使用方式

1. 開啟本專案資料夾。
2. 直接在瀏覽器開啟 `index.html`。
3. 或在本機執行本地伺服器：

```bash
python -m http.server 8000 --directory d:/data
```

4. 開啟瀏覽器並前往：

```text
http://localhost:8000
```

## 開發說明

- `index.html` 內含一段 JavaScript，用 `setInterval` 每秒更新 `#clock` 的文字。
- 時間格式使用 `toLocaleTimeString('zh-TW', ...)`，顯示 24 小時制。
- CSS 以深色背景與霧化卡片效果呈現。

## GitHub 部署

若要發布為 GitHub Pages，可將倉庫 `main` 分支設為公開網頁來源，並選擇根目錄 (`/(root)`)。

預期網址格式：

```text
https://jimm1218.github.io/L2C1/
```

## 其他

如果你想我協助補上 `weather_time.html` 或 `test1.html` 的說明，也可以再告訴我。
