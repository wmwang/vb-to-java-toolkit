# VB Legacy Analyzer - AI 輔助遷移分析工具

將大型 VB 專案遷移至 Java 前，使用 AI 深入分析舊架構。

## 核心功能（AI 驅動）

| 命令 | 說明 | 輸出 |
|------|------|------|
| `discover` | 分析模組依賴，建議遷移順序 | `migration_advice.md` |
| `understand` | 解說業務邏輯，識別風險 | `business_rules_explained.md` |

## 快速開始

### 1. 環境設定

```bash
# 建立虛擬環境
python -m venv venv

# 啟動（Windows）
.\venv\Scripts\activate

# 啟動（macOS/Linux）
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt
```

### 2. 設定 API Key

```bash
cp .env.example .env
# 編輯 .env，填入 OPENAI_API_KEY
```

### 3. 執行 AI 分析

```bash
# 探索專案依賴，AI 建議遷移順序
python cli.py discover ./your-vb-project

# 深入理解業務邏輯
python cli.py understand ./your-vb-project

# 只分析特定模組
python cli.py understand ./your-vb-project --module Order
```

## 輸出範例

**discover 輸出 (`migration_advice.md`)：**
- 專案概覽
- 遷移順序建議（含理由）
- 風險模組識別
- 遷移策略建議

**understand 輸出 (`business_rules_explained.md`)：**
- 業務規則說明
- 決策邏輯
- 邊界條件與風險
- 建議測試案例

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

> ⚠️ **注意**：CLI 工具目前僅執行靜態分析（AST 解析），**不會** 調用 LLM API，因此不會消耗 Token 額度。

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

> 💡 **提示**：Web API 的 `/translate` 功能會調用 LLM 進行程式碼轉譯，**會消耗 Token 額度**。

#### 1. 啟動 API 服務
```bash
python -m uvicorn src.api.main:app --reload
```

啟動後，開啟瀏覽器訪問 `http://localhost:8000/docs` 可查看完整的 API 文件與測試介面。

#### 2. 主要 API 端點

| 方法 | 路徑 | 說明 | LLM 調用 |
|------|------|------|:---:|
| POST | `/analyze` | 分析 VB 專案 (非同步任務) | ❌ |
| POST | `/translate` | 翻譯程式碼 (SSE) | ✅ |
| POST | `/generate` | 生成 Java 專案 | ❌* |
| GET | `/status/{job_id}` | 查詢任務狀態 | ❌ |

*\*註：generate 目前主要依賴靜態分析結果，但在進階模式下可能會調用 LLM。*

---

## 開發者資訊

### 執行測試
```bash
python run_tests.py
```

### 授權
MIT License
