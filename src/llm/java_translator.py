"""
Java 程式碼轉譯器 - 使用 LLM 將 VB 轉換為 Java Clean Architecture

功能：
1. 將 VB 函數轉譯為 Java 方法
2. 生成符合 Clean Architecture 的程式碼結構
3. 保留業務邏輯的完整性
"""

from typing import Optional, Callable, Dict
from dataclasses import dataclass
from enum import Enum

from .llm_client import LLMClient


class JavaLayer(Enum):
    """Java Clean Architecture 層級"""
    ENTITY = "entity"
    USE_CASE = "usecase"
    REPOSITORY = "repository"
    CONTROLLER = "controller"
    DTO = "dto"


# System Prompt 模板
JAVA_TRANSLATOR_SYSTEM_PROMPT = """你是一位專精於 Java Clean Architecture 的資深軟體工程師。

你的任務是將 VB6 程式碼轉譯為現代 Java 程式碼，遵循以下原則：

## 架構原則
1. 使用 Clean Architecture 分層
2. Entity 層：純業務邏輯，無外部依賴
3. Use Case 層：應用邏輯，協調 Entity 和 Repository
4. Repository 層：資料存取介面
5. Controller 層：API 端點

## 程式碼規範
1. 使用 Java 17+ 語法
2. 使用 Spring Boot 框架
3. 使用 JPA/Hibernate 進行資料存取
4. 使用 Lombok 減少樣板程式碼
5. 遵循 Java 命名慣例（camelCase）

## 輸出格式
請提供完整的 Java 程式碼，包含：
1. Package 宣告
2. Import 語句
3. 類別/介面定義
4. 方法實作
5. 必要的註解說明業務邏輯

使用繁體中文撰寫註解。"""


@dataclass
class TranslationResult:
    """轉譯結果"""
    original_vb_code: str
    java_code: str
    target_layer: JavaLayer
    class_name: str
    source_function: str


class JavaCodeTranslator:
    """Java 程式碼轉譯器"""
    
    def __init__(self, llm_client: LLMClient):
        """
        初始化轉譯器
        
        Args:
            llm_client: LLM Client 實例
        """
        self.llm_client = llm_client
        self.translations: Dict[str, TranslationResult] = {}
    
    async def translate_function(
        self,
        vb_code: str,
        function_name: str,
        target_layer: JavaLayer = JavaLayer.USE_CASE,
        context: Optional[str] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> TranslationResult:
        """
        轉譯單一 VB 函數為 Java
        
        Args:
            vb_code: VB 程式碼
            function_name: 函數名稱
            target_layer: 目標 Clean Architecture 層級
            context: 可選的額外上下文（如相關的 SQL、業務規則說明）
            on_chunk: 可選的 streaming 回調
            
        Returns:
            轉譯結果
        """
        user_prompt = self._build_user_prompt(
            vb_code, function_name, target_layer, context
        )
        
        java_code = await self.llm_client.generate(
            user_prompt=user_prompt,
            system_prompt=JAVA_TRANSLATOR_SYSTEM_PROMPT,
            on_chunk=on_chunk,
        )
        
        # 推斷 class name
        class_name = self._infer_class_name(function_name, target_layer)
        
        result = TranslationResult(
            original_vb_code=vb_code,
            java_code=java_code,
            target_layer=target_layer,
            class_name=class_name,
            source_function=function_name,
        )
        
        self.translations[function_name] = result
        return result
    
    async def translate_to_entity(
        self,
        vb_class_code: str,
        class_name: str,
        inferred_columns: Optional[Dict] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> TranslationResult:
        """
        將 VB 類別轉譯為 Java Entity
        
        Args:
            vb_class_code: VB 類別程式碼
            class_name: 類別名稱
            inferred_columns: 從 Schema 推斷的欄位資訊
            on_chunk: 可選的 streaming 回調
            
        Returns:
            轉譯結果
        """
        user_prompt = self._build_entity_prompt(
            vb_class_code, class_name, inferred_columns
        )
        
        java_code = await self.llm_client.generate(
            user_prompt=user_prompt,
            system_prompt=JAVA_TRANSLATOR_SYSTEM_PROMPT,
            on_chunk=on_chunk,
        )
        
        result = TranslationResult(
            original_vb_code=vb_class_code,
            java_code=java_code,
            target_layer=JavaLayer.ENTITY,
            class_name=class_name,
            source_function="",
        )
        
        self.translations[f"Entity_{class_name}"] = result
        return result
    
    def _build_user_prompt(
        self,
        vb_code: str,
        function_name: str,
        target_layer: JavaLayer,
        context: Optional[str],
    ) -> str:
        """組裝函數轉譯的 User Prompt"""
        layer_guidance = {
            JavaLayer.ENTITY: "純領域邏輯，不依賴任何框架",
            JavaLayer.USE_CASE: "應用服務，協調 Entity 和 Repository",
            JavaLayer.REPOSITORY: "資料存取介面，使用 Spring Data JPA",
            JavaLayer.CONTROLLER: "REST API 端點，使用 Spring MVC",
            JavaLayer.DTO: "資料傳輸物件，用於 API 請求/回應",
        }
        
        lines = [
            f"請將以下 VB 函數轉譯為 Java，放置於 **{target_layer.value}** 層。",
            f"",
            f"## 層級說明",
            f"{layer_guidance.get(target_layer, '')}",
            f"",
            f"## VB 函數名稱",
            f"`{function_name}`",
            f"",
            f"## VB 程式碼",
            f"```vb",
            vb_code,
            f"```",
        ]
        
        if context:
            lines.append(f"")
            lines.append(f"## 額外上下文")
            lines.append(context)
        
        return "\n".join(lines)
    
    def _build_entity_prompt(
        self,
        vb_class_code: str,
        class_name: str,
        inferred_columns: Optional[Dict],
    ) -> str:
        """組裝 Entity 轉譯的 User Prompt"""
        lines = [
            f"請將以下 VB 類別轉譯為 Java JPA Entity。",
            f"",
            f"## 類別名稱",
            f"`{class_name}`",
            f"",
            f"## VB 程式碼",
            f"```vb",
            vb_class_code[:2000],  # 限制長度
            f"```",
        ]
        
        if inferred_columns:
            lines.append(f"")
            lines.append(f"## 推斷的欄位資訊")
            for col_name, col_info in inferred_columns.items():
                lines.append(f"- `{col_name}`: {col_info.get('type', 'Unknown')}, nullable={col_info.get('nullable', False)}")
        
        return "\n".join(lines)
    
    def _infer_class_name(self, function_name: str, layer: JavaLayer) -> str:
        """推斷 Java 類別名稱"""
        base_name = function_name.replace("_", "")
        
        if layer == JavaLayer.USE_CASE:
            return f"{base_name}UseCase"
        elif layer == JavaLayer.REPOSITORY:
            return f"{base_name}Repository"
        elif layer == JavaLayer.CONTROLLER:
            return f"{base_name}Controller"
        elif layer == JavaLayer.DTO:
            return f"{base_name}DTO"
        else:
            return base_name
    
    def get_all_translations(self) -> Dict[str, TranslationResult]:
        """取得所有轉譯結果"""
        return self.translations
