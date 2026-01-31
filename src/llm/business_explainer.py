"""
業務邏輯解說器 - 使用 LLM 解讀萃取的業務規則

功能：
1. 將決策表轉換為人類可讀的業務說明
2. 識別潛在的業務風險或邊界條件
3. 生成測試案例建議
"""

from typing import List, Optional, Callable
from dataclasses import dataclass

from ..extractors.business_logic_extractor import BusinessRule, BusinessRuleType
from .llm_client import LLMClient


# System Prompt 模板
BUSINESS_ANALYST_SYSTEM_PROMPT = """你是一位資深業務分析師，專門將程式碼中的業務邏輯轉換為清晰的業務規則說明。

你的任務是：
1. 分析提供的決策表和偽代碼
2. 用業務語言解釋這些規則的含義
3. 識別潛在的邊界條件或風險
4. 建議需要驗證的測試案例

請使用繁體中文回答，格式如下：

## 業務規則說明
[用業務語言清楚描述這個邏輯的目的和行為]

## 決策邏輯
[以條列方式說明每個決策分支]

## 邊界條件與風險
[列出可能的邊界條件或需要注意的風險]

## 建議測試案例
[列出應該測試的情境]"""


@dataclass
class BusinessRuleExplanation:
    """業務規則解說結果"""
    rule_name: str
    explanation: str
    source_function: str
    source_file: str


class BusinessLogicExplainer:
    """業務邏輯解說器"""
    
    def __init__(self, llm_client: LLMClient):
        """
        初始化解說器
        
        Args:
            llm_client: LLM Client 實例
        """
        self.llm_client = llm_client
        self.explanations: List[BusinessRuleExplanation] = []
    
    async def explain_rule(
        self,
        rule: BusinessRule,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> BusinessRuleExplanation:
        """
        解說單一業務規則
        
        Args:
            rule: 業務規則物件
            on_chunk: 可選的 streaming 回調
            
        Returns:
            業務規則解說結果
        """
        # 組裝 User Prompt
        user_prompt = self._build_user_prompt(rule)
        
        # 呼叫 LLM（強制 SSE Streaming）
        explanation = await self.llm_client.generate(
            user_prompt=user_prompt,
            system_prompt=BUSINESS_ANALYST_SYSTEM_PROMPT,
            on_chunk=on_chunk,
        )
        
        result = BusinessRuleExplanation(
            rule_name=rule.name,
            explanation=explanation,
            source_function=rule.source_function,
            source_file=rule.source_file,
        )
        
        self.explanations.append(result)
        return result
    
    async def explain_rules_batch(
        self,
        rules: List[BusinessRule],
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[BusinessRuleExplanation]:
        """
        批次解說多個業務規則
        
        Args:
            rules: 業務規則列表
            on_progress: 可選的進度回調 (current, total, rule_name)
            
        Returns:
            業務規則解說結果列表
        """
        results = []
        
        for i, rule in enumerate(rules):
            if on_progress:
                on_progress(i + 1, len(rules), rule.name)
            
            result = await self.explain_rule(rule)
            results.append(result)
        
        return results
    
    def _build_user_prompt(self, rule: BusinessRule) -> str:
        """組裝 User Prompt"""
        lines = [
            f"請分析以下業務規則：",
            f"",
            f"**規則名稱**: {rule.name}",
            f"**來源**: {rule.source_file} / {rule.source_function}",
            f"**規則類型**: {rule.rule_type.value}",
            f"",
        ]
        
        # 決策表
        if rule.decision_table:
            lines.append("**決策表**:")
            lines.append("| 條件 | 結果 |")
            lines.append("|------|------|")
            for decision in rule.decision_table:
                lines.append(f"| {decision.condition} | {decision.result} |")
            lines.append("")
        
        # 偽代碼
        if rule.pseudocode:
            lines.append("**偽代碼**:")
            lines.append("```")
            lines.append(rule.pseudocode)
            lines.append("```")
            lines.append("")
        
        # 計算公式
        if rule.formula:
            lines.append(f"**計算公式**: {rule.output_variable} = {rule.formula}")
            if rule.input_variables:
                lines.append(f"**輸入變數**: {', '.join(rule.input_variables)}")
            lines.append("")
        
        # 原始程式碼
        if rule.raw_code:
            lines.append("**原始 VB 程式碼**:")
            lines.append("```vb")
            lines.append(rule.raw_code[:500])  # 限制長度
            lines.append("```")
        
        return "\n".join(lines)
    
    def export_explanations_markdown(self) -> str:
        """匯出所有解說為 Markdown 格式"""
        lines = [
            "# 業務規則解說報告",
            "",
            f"共分析 {len(self.explanations)} 條業務規則",
            "",
            "---",
            "",
        ]
        
        for exp in self.explanations:
            lines.append(f"# {exp.rule_name}")
            lines.append(f"")
            lines.append(f"**來源**: `{exp.source_file}` / `{exp.source_function}`")
            lines.append("")
            lines.append(exp.explanation)
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
