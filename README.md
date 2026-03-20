# ZeroJudge 學生進度追蹤器 (ZeroJudge Student Progress Tracker)

這是一個自動化工具，用於抓取 ZeroJudge 課程頁面的學生練習進度，並將資料同步到 Google Sheets。

## 安裝步驟

1. 確保電腦已安裝 Python 3.8+。
2. 進入專案目錄並啟動虛擬環境：
   ```powershell
   cd zj_tracker
   .\venv\Scripts\activate
   ```
3. 設定設定檔：
   編輯 `config.yaml`，填寫您的課程 `course_id` 與 `course_url`。
4. 準備 Google API 憑證：
   將您的 Google Service Account JSON 檔案命名為 `service_account.json` 並放在本目錄下。

### 1. 設定與驗證
*   **ZeroJudge 驗證**：
    - 程式執行時，會於終端機主動提示您**輸入帳號與密碼**進行自動登入。
    - **安全性**：帳號與密碼不會被儲存在任何設定檔中。
    - **進階用法 (選用)**：若需要全自動執行免輸入，可以選擇設定系統環境變數 `ZJ_ACCOUNT` 與 `ZJ_PASSWORD`。
*   **Google Sheets 驗證**：確保目錄下有 `service_account.json`。

### 2. 執行同步
```powershell
.\venv\Scripts\python main.py
```

### 3. 注意事項
*   **標題規則**：程式預設只會抓取標題包含「【」符號的作業。
*   **欄位自動建立**：如果試算表沒有對應標題，程式會自動新增欄位。
*   **資料格式**：進度會以 `分數 / 時間` 顯示在單一儲存格中。
- 請確保 Google Sheet 已分享編輯權限給 Service Account 的信箱。
