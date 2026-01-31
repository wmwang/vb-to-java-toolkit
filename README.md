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

```bash
# 方法 1: 使用 pip（推薦）
pip install -r requirements.txt

# 方法 2: 使用 Poetry（可選）
poetry install

# 執行測試
pytest tests/ -v

# 啟動 API 服務
uvicorn src.api.main:app --reload

# 或使用 python 直接啟動
python -m uvicorn src.api.main:app --reload

# 執行基本分析測試
python run_test.py
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
