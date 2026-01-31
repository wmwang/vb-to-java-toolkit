# VB to Java Migration AI Toolkit

一套 AI 驅動的工具，用於將 VB 專案遷移到 Java Clean Architecture。

## 功能特色

- 🔍 **VB 程式碼解析** - AST 解析 VB 檔案結構
- 📊 **SQL/Schema 萃取** - 從程式碼反推資料庫結構
- 🧠 **業務邏輯提取 (BLE)** - 分離業務意圖與技術實作
- ☕ **Java 程式碼生成** - 轉譯為 Clean Architecture 代碼
- ✅ **行為驗證** - 確保遷移正確性
- 🌐 **REST API** - FastAPI 服務端點

## 專案結構

```
vb-to-java-toolkit/
├── src/
│   ├── parsers/          # VB 程式碼解析器
│   ├── extractors/       # SQL/Schema/BLE 萃取器
│   ├── generators/       # Java 程式碼生成器
│   ├── verifiers/        # 行為驗證器
│   ├── llm/              # LLM 客戶端
│   └── api/              # FastAPI 服務
├── examples/             # 示範 VB 專案
├── tests/                # 測試
└── docs/                 # 文件
```

## 快速開始

### 1. 環境設定（強烈建議使用虛擬環境）

**Windows:**
```powershell
# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境
.\venv\Scripts\activate
```

**macOS / Linux:**
```bash
# 建立虛擬環境
python3 -m venv venv

# 啟動虛擬環境
source venv/bin/activate
```

### 2. 安裝依賴

```bash
# 確保已啟動虛擬環境
pip install -r requirements.txt
```

### 3. 設定環境變數

複製範例設定檔並填入您的 OpenAI API Key：

**Windows:**
```powershell
copy .env.example .env
# 編輯 .env 檔案，填入 OPENAI_API_KEY=sk-...
```

**macOS / Linux:**
```bash
cp .env.example .env
# 編輯 .env 檔案，填入 OPENAI_API_KEY=sk-...
```

---

## 📖 使用指南

本工具提供兩種使用方式：**命令行工具 (CLI)** 與 **Web API**。

### 方式一：使用 CLI 命令列工具
適合本機批次處理或 CI/CD 整合。

#### 1. 掃描專案結構
快速查看專案包含多少檔案與模組。
```bash
python cli.py scan ./examples/sample-erp
```

#### 2. 分析整個專案
執行完整分析（解析、SQL 萃取、Schema 推斷、業務邏輯提取），結果將匯出至 `./output`。
```bash
python cli.py analyze ./examples/sample-erp
```

#### 3. 指定輸出目錄
```bash
python cli.py analyze ./examples/sample-erp -o ./my-analysis-output
```

---

### 方式二：使用 Web API
適合整合至網頁介面或其他系統。

#### 1. 啟動 API 服務
```bash
python -m uvicorn src.api.main:app --reload
```

啟動後，開啟瀏覽器訪問 `http://localhost:8000/docs` 可查看完整的 API 文件與測試介面。

#### 2. 主要 API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/analyze` | 分析 VB 專案 (非同步任務) |
| POST | `/generate` | 生成 Java 專案 |
| GET | `/status/{job_id}` | 查詢任務狀態 |

---

## 開發者資訊

### 執行測試
```bash
python run_tests.py
```

### 授權
MIT License
