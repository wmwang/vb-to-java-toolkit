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

### 3. 執行服務與測試

```bash
# 啟動 API 服務
python -m uvicorn src.api.main:app --reload

# 執行測試
python run_tests.py
```

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/analyze` | 分析 VB 專案 |
| POST | `/translate` | 翻譯程式碼 (SSE) |
| POST | `/generate` | 生成 Java 專案 |
| GET | `/status/{job_id}` | 查詢任務狀態 |
| GET | `/stream/{job_id}` | SSE 串流進度 |

啟動後訪問 `http://localhost:8000/docs` 查看 Swagger 文件。

## 環境變數

| 變數名稱 | 用途 | 必要 |
|----------|------|------|
| `OPENAI_API_KEY` | OpenAI API 金鑰 | LLM 功能必要 |
| `LLM_BASE_URL` | API Endpoint | 可選 |
| `LLM_MODEL` | 模型名稱 | 可選（預設 gpt-4o-mini）|

## 授權

MIT License
