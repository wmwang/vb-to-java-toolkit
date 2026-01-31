# API 參考文件

## 快速開始

```python
from src.analyzer import analyze_project

# 一鍵分析 VB 專案
results = analyze_project(
    project_path="/path/to/vb/project",
    output_dir="/path/to/output"
)
```

---

## Parsers 模組

### VBScanner

掃描目錄中的 VB 檔案。

```python
from src.parsers import VBScanner

scanner = VBScanner(root_path: str)
```

| 方法 | 參數 | 回傳 | 說明 |
|------|------|------|------|
| `scan()` | `recursive: bool = True` | `List[VBFile]` | 掃描 VB 檔案 |
| `get_statistics()` | `vb_files: List[VBFile]` | `dict` | 取得統計資訊 |

### VBParser

解析 VB 檔案結構。

```python
from src.parsers import VBParser

parser = VBParser()
```

| 方法 | 參數 | 回傳 | 說明 |
|------|------|------|------|
| `parse()` | `vb_file: VBFile` | `VBFile` | 解析檔案並填充 module |

### 資料模型

```python
from src.parsers import (
    VBFile,      # 檔案
    VBModule,    # 模組
    VBFunction,  # 函數
    VBVariable,  # 變數
    VBProperty,  # 屬性
    VBFileType,  # 檔案類型 (CLASS, MODULE, FORM)
    VBVisibility # 可見性 (PUBLIC, PRIVATE, FRIEND)
)
```

---

## Extractors 模組

### SQLExtractor

從 VB 程式碼萃取 SQL 語句。

```python
from src.extractors import SQLExtractor

extractor = SQLExtractor()
```

| 方法 | 參數 | 回傳 |
|------|------|------|
| `extract_from_code()` | `code, source_file, source_function` | `List[ExtractedSQL]` |
| `get_summary()` | - | `dict` |

| 屬性 | 類型 | 說明 |
|------|------|------|
| `tables` | `Dict[str, ExtractedTable]` | 識別的表格 |
| `columns` | `Dict[str, ExtractedColumn]` | 識別的欄位 |

### SchemaInferrer

推斷資料庫 Schema。

```python
from src.extractors import SchemaInferrer

inferrer = SchemaInferrer()
```

| 方法 | 參數 | 回傳 |
|------|------|------|
| `process_sql_extractor_results()` | `sql_extractor` | `None` |
| `infer_additional_types()` | - | `None` |
| `export_json()` | `filepath: str` | `None` |
| `generate_mermaid_erd()` | - | `str` |
| `generate_java_entities()` | - | `Dict[str, str]` |

### BusinessLogicExtractor

萃取業務邏輯規則。

```python
from src.extractors import BusinessLogicExtractor

ble = BusinessLogicExtractor()
```

| 方法 | 參數 | 回傳 |
|------|------|------|
| `extract_from_function()` | `func_name, func_body, source_file` | `List[BusinessRule]` |
| `generate_decision_table_markdown()` | `rule: BusinessRule` | `str` |
| `get_summary()` | - | `dict` |

---

## LLM 模組

> ⚠️ **所有 LLM 呼叫必須使用 SSE Streaming**

### LLMClient

```python
from src.llm import create_llm_client, LLMConfig

# 快速建立
llm = create_llm_client(
    api_key: str,
    base_url: Optional[str] = None,
    model: str = "gpt-4o-mini"
)

# 或使用 Config
config = LLMConfig(
    api_key="...",
    base_url=None,
    model="gpt-4o-mini",
    temperature=0.3,
    max_tokens=4000
)
llm = LLMClient(config)
```

| 方法 | 參數 | 回傳 |
|------|------|------|
| `generate()` | `user_prompt, system_prompt, on_chunk` | `str` (async) |
| `generate_stream()` | `user_prompt, system_prompt` | `AsyncGenerator[str]` |
| `get_token_usage()` | - | `int` |

### BusinessLogicExplainer

```python
from src.llm import BusinessLogicExplainer

explainer = BusinessLogicExplainer(llm_client: LLMClient)
```

| 方法 | 參數 | 回傳 |
|------|------|------|
| `explain_rule()` | `rule, on_chunk` | `BusinessRuleExplanation` (async) |
| `explain_rules_batch()` | `rules, on_progress` | `List[BusinessRuleExplanation]` (async) |
| `export_explanations_markdown()` | - | `str` |

### JavaCodeTranslator

```python
from src.llm import JavaCodeTranslator, JavaLayer

translator = JavaCodeTranslator(llm_client: LLMClient)
```

| 方法 | 參數 | 回傳 |
|------|------|------|
| `translate_function()` | `vb_code, function_name, target_layer, context, on_chunk` | `TranslationResult` (async) |
| `translate_to_entity()` | `vb_class_code, class_name, inferred_columns, on_chunk` | `TranslationResult` (async) |

| JavaLayer 值 | 說明 |
|--------------|------|
| `ENTITY` | JPA Entity |
| `USE_CASE` | 應用服務 |
| `REPOSITORY` | 資料存取 |
| `CONTROLLER` | REST API |
| `DTO` | 資料傳輸物件 |

---

## Analyzer 模組

### VBProjectAnalyzer

整合所有工具的主控分析器。

```python
from src.analyzer import VBProjectAnalyzer

analyzer = VBProjectAnalyzer(project_path: str)
```

| 方法 | 參數 | 回傳 |
|------|------|------|
| `analyze()` | `recursive: bool = True` | `Dict[str, Any]` |
| `export_results()` | `output_dir: str` | `None` |
| `print_summary()` | - | `None` |

| 屬性 | 類型 | 說明 |
|------|------|------|
| `vb_files` | `List[VBFile]` | 掃描的檔案 |
| `scanner` | `VBScanner` | 掃描器實例 |
| `parser` | `VBParser` | 解析器實例 |
| `sql_extractor` | `SQLExtractor` | SQL 萃取器 |
| `schema_inferrer` | `SchemaInferrer` | Schema 推斷器 |
| `ble` | `BusinessLogicExtractor` | 業務邏輯萃取器 |

### 便捷函數

```python
from src.analyzer import analyze_project

results = analyze_project(
    project_path: str,
    output_dir: Optional[str] = None,
    recursive: bool = True
) -> Dict[str, Any]
```

---

## Generators 模組

### JavaProjectGenerator

從 Schema 生成完整的 Java Clean Architecture 專案。

```python
from src.generators import JavaProjectGenerator, JavaProjectConfig

config = JavaProjectConfig(
    group_id="com.example",
    artifact_id="my-app",
    base_package="com.example.app",
)
generator = JavaProjectGenerator(config=config)
```

| 方法 | 參數 | 回傳 |
|------|------|------|
| `generate_from_schema()` | `schema_inferrer, output_dir, on_progress` | `List[GeneratedFile]` |
| `generate_from_vb_functions()` | `vb_functions, output_dir, on_progress, on_chunk` | `List[GeneratedFile]` (async) |
| `get_summary()` | - | `dict` |

### JavaProjectConfig

| 欄位 | 類型 | 預設值 |
|------|------|--------|
| `group_id` | `str` | `"com.example"` |
| `artifact_id` | `str` | `"migrated-app"` |
| `base_package` | `str` | `"com.example.app"` |
| `java_version` | `str` | `"17"` |
| `project_type` | `ProjectType` | `MAVEN` |
| `use_lombok` | `bool` | `True` |
| `use_spring_boot` | `bool` | `True` |

---

## Verifiers 模組

### BehaviorVerifier

驗證遷移正確性並生成測試案例。

```python
from src.verifiers import BehaviorVerifier

verifier = BehaviorVerifier(llm_client=None)  # Optional LLM
```

| 方法 | 參數 | 回傳 |
|------|------|------|
| `generate_test_cases_from_rules()` | `rules: List[BusinessRule]` | `List[TestCase]` |
| `verify_with_llm()` | `vb_code, java_code, rule, on_chunk` | `VerificationResult` (async) |
| `verify_consistency()` | `rules, java_translations` | `List[VerificationResult]` |
| `export_test_cases_junit()` | `test_cases, class_name` | `str` |
| `generate_report_markdown()` | - | `str` |

### VerificationStatus

| 值 | 說明 |
|----|------|
| `PASSED` | 驗證通過 |
| `FAILED` | 驗證失敗 |
| `WARNING` | 有警告 |
| `SKIPPED` | 略過 |

---

## REST API

### 啟動服務

```bash
poetry run uvicorn src.api.main:app --reload
```

### 端點列表

#### POST /analyze

分析 VB 專案。

```json
{
  "project_path": "/path/to/vb/project",
  "output_dir": "/path/to/output",
  "recursive": true
}
```

回應：
```json
{
  "job_id": "uuid",
  "status": "pending"
}
```

#### POST /translate

翻譯程式碼（SSE 串流）。

```json
{
  "vb_code": "Function Test()...",
  "function_name": "Test",
  "target_layer": "usecase",
  "context": "optional context"
}
```

回應：SSE 事件流

#### POST /generate

生成 Java 專案。

```json
{
  "project_path": "/path/to/vb/project",
  "output_dir": "/path/to/output",
  "group_id": "com.example",
  "artifact_id": "my-app",
  "base_package": "com.example.app"
}
```

#### GET /status/{job_id}

查詢任務狀態。

#### GET /stream/{job_id}

SSE 串流任務進度。

#### GET /health

健康檢查。
