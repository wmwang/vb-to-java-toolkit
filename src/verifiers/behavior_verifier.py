"""
行為驗證器 - 驗證 VB 到 Java 遷移的正確性

功能：
1. 輸入/輸出對比驗證
2. 邊界條件測試生成
3. 業務規則一致性檢查
4. LLM 輔助驗證報告生成
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
import json

from ..extractors.business_logic_extractor import BusinessRule, BusinessRuleType, DecisionCondition
from ..llm.llm_client import LLMClient


class VerificationStatus(Enum):
    """驗證狀態"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class TestCase:
    """測試案例"""
    name: str
    description: str
    inputs: Dict[str, Any]
    expected_output: Any
    source_rule: str  # 來源業務規則名稱
    is_boundary_case: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputs": self.inputs,
            "expected_output": self.expected_output,
            "source_rule": self.source_rule,
            "is_boundary_case": self.is_boundary_case,
        }


@dataclass
class VerificationResult:
    """驗證結果"""
    rule_name: str
    status: VerificationStatus
    message: str
    test_cases: List[TestCase] = field(default_factory=list)
    java_code_issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "rule_name": self.rule_name,
            "status": self.status.value,
            "message": self.message,
            "test_cases": [tc.to_dict() for tc in self.test_cases],
            "java_code_issues": self.java_code_issues,
            "suggestions": self.suggestions,
        }


# LLM 驗證 System Prompt
VERIFIER_SYSTEM_PROMPT = """你是一位專精於程式碼遷移驗證的 QA 工程師。

你的任務是：
1. 比較原始 VB 程式碼和轉譯後的 Java 程式碼
2. 驗證業務邏輯是否正確保留
3. 識別潛在問題和邊界條件
4. 生成測試案例建議

回應格式為 JSON：
{
    "status": "passed" | "failed" | "warning",
    "message": "驗證結論",
    "issues": ["問題1", "問題2"],
    "test_cases": [
        {
            "name": "測試案例名稱",
            "description": "測試說明",
            "inputs": {"param1": "value1"},
            "expected_output": "預期結果",
            "is_boundary_case": true/false
        }
    ],
    "suggestions": ["建議1", "建議2"]
}

使用繁體中文回應。"""


class BehaviorVerifier:
    """行為驗證器"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        初始化驗證器
        
        Args:
            llm_client: LLM Client 實例（用於 AI 輔助驗證）
        """
        self.llm_client = llm_client
        self.results: List[VerificationResult] = []
    
    def generate_test_cases_from_rules(
        self,
        rules: List[BusinessRule],
    ) -> List[TestCase]:
        """
        從業務規則生成測試案例
        
        Args:
            rules: 業務規則列表
            
        Returns:
            測試案例列表
        """
        test_cases = []
        
        for rule in rules:
            cases = self._generate_cases_for_rule(rule)
            test_cases.extend(cases)
        
        return test_cases
    
    def _generate_cases_for_rule(self, rule: BusinessRule) -> List[TestCase]:
        """為單一規則生成測試案例"""
        cases = []
        
        if rule.rule_type == BusinessRuleType.DECISION:
            cases.extend(self._generate_decision_test_cases(rule))
        elif rule.rule_type == BusinessRuleType.CALCULATION:
            cases.extend(self._generate_calculation_test_cases(rule))
        elif rule.rule_type == BusinessRuleType.VALIDATION:
            cases.extend(self._generate_validation_test_cases(rule))
        
        return cases
    
    def _generate_decision_test_cases(self, rule: BusinessRule) -> List[TestCase]:
        """從決策規則生成測試案例"""
        cases = []
        
        for i, condition in enumerate(rule.decision_table):
            # 基本案例
            case = TestCase(
                name=f"{rule.name}_Case_{i+1}",
                description=f"測試條件: {condition.condition}",
                inputs=self._parse_condition_inputs(condition.condition),
                expected_output=condition.result.strip(),
                source_rule=rule.name,
                is_boundary_case=False,
            )
            cases.append(case)
            
            # 邊界案例
            boundary_case = self._generate_boundary_case(rule.name, condition, i)
            if boundary_case:
                cases.append(boundary_case)
        
        return cases
    
    def _generate_calculation_test_cases(self, rule: BusinessRule) -> List[TestCase]:
        """從計算規則生成測試案例"""
        cases = []
        
        # 基本案例
        basic_inputs = {var: "測試值" for var in rule.input_variables}
        cases.append(TestCase(
            name=f"{rule.name}_Basic",
            description=f"基本計算測試: {rule.formula}",
            inputs=basic_inputs,
            expected_output="根據公式計算",
            source_rule=rule.name,
            is_boundary_case=False,
        ))
        
        # 零值邊界
        zero_inputs = {var: 0 for var in rule.input_variables}
        cases.append(TestCase(
            name=f"{rule.name}_Zero",
            description="零值邊界測試",
            inputs=zero_inputs,
            expected_output="驗證零值處理",
            source_rule=rule.name,
            is_boundary_case=True,
        ))
        
        # 負值邊界
        negative_inputs = {var: -1 for var in rule.input_variables}
        cases.append(TestCase(
            name=f"{rule.name}_Negative",
            description="負值邊界測試",
            inputs=negative_inputs,
            expected_output="驗證負值處理",
            source_rule=rule.name,
            is_boundary_case=True,
        ))
        
        return cases
    
    def _generate_validation_test_cases(self, rule: BusinessRule) -> List[TestCase]:
        """從驗證規則生成測試案例"""
        cases = []
        
        # 有效輸入
        cases.append(TestCase(
            name=f"{rule.name}_Valid",
            description="有效輸入測試",
            inputs={"input": "有效值"},
            expected_output="驗證通過",
            source_rule=rule.name,
            is_boundary_case=False,
        ))
        
        # 無效輸入
        cases.append(TestCase(
            name=f"{rule.name}_Invalid",
            description="無效輸入測試",
            inputs={"input": "無效值"},
            expected_output="驗證失敗",
            source_rule=rule.name,
            is_boundary_case=True,
        ))
        
        # 空值
        cases.append(TestCase(
            name=f"{rule.name}_Empty",
            description="空值測試",
            inputs={"input": None},
            expected_output="處理空值",
            source_rule=rule.name,
            is_boundary_case=True,
        ))
        
        return cases
    
    def _parse_condition_inputs(self, condition: str) -> Dict[str, Any]:
        """解析條件字串為輸入參數"""
        # 簡單解析，實際情況可能需要更複雜的邏輯
        inputs = {}
        
        # 解析比較運算式，例如 "x > 10" => {"x": 11}
        import re
        patterns = [
            (r"(\w+)\s*[>=]+\s*(\d+)", lambda m: {m.group(1): int(m.group(2))}),
            (r"(\w+)\s*[<=]+\s*(\d+)", lambda m: {m.group(1): int(m.group(2))}),
            (r"(\w+)\s*=\s*[\"']([^\"']+)[\"']", lambda m: {m.group(1): m.group(2)}),
        ]
        
        for pattern, handler in patterns:
            match = re.search(pattern, condition, re.IGNORECASE)
            if match:
                inputs.update(handler(match))
        
        if not inputs:
            inputs["condition"] = condition
        
        return inputs
    
    def _generate_boundary_case(
        self, 
        rule_name: str, 
        condition: DecisionCondition, 
        index: int
    ) -> Optional[TestCase]:
        """生成邊界測試案例"""
        import re
        
        # 尋找數值比較
        match = re.search(r"(\w+)\s*([><=]+)\s*(\d+)", condition.condition)
        if match:
            var_name = match.group(1)
            operator = match.group(2)
            value = int(match.group(3))
            
            # 根據運算子生成邊界值
            if ">" in operator:
                boundary_value = value  # 剛好等於的邊界
            elif "<" in operator:
                boundary_value = value  # 剛好等於的邊界
            else:
                boundary_value = value + 1  # 超過一點
            
            return TestCase(
                name=f"{rule_name}_Boundary_{index+1}",
                description=f"邊界值測試: {var_name} = {boundary_value}",
                inputs={var_name: boundary_value},
                expected_output="驗證邊界行為",
                source_rule=rule_name,
                is_boundary_case=True,
            )
        
        return None
    
    async def verify_with_llm(
        self,
        vb_code: str,
        java_code: str,
        rule: BusinessRule,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> VerificationResult:
        """
        使用 LLM 進行深度驗證
        
        Args:
            vb_code: 原始 VB 程式碼
            java_code: 轉譯後的 Java 程式碼
            rule: 相關業務規則
            on_chunk: LLM streaming 回調
            
        Returns:
            驗證結果
        """
        if not self.llm_client:
            return VerificationResult(
                rule_name=rule.name,
                status=VerificationStatus.SKIPPED,
                message="需要 LLM Client 才能進行深度驗證",
            )
        
        user_prompt = self._build_verification_prompt(vb_code, java_code, rule)
        
        response = await self.llm_client.generate(
            user_prompt=user_prompt,
            system_prompt=VERIFIER_SYSTEM_PROMPT,
            on_chunk=on_chunk,
        )
        
        # 解析 LLM 回應
        result = self._parse_llm_response(response, rule.name)
        self.results.append(result)
        
        return result
    
    def _build_verification_prompt(
        self, 
        vb_code: str, 
        java_code: str, 
        rule: BusinessRule
    ) -> str:
        """建構驗證用的 User Prompt"""
        decision_table_md = ""
        if rule.decision_table:
            decision_table_md = "\n## 決策表\n"
            for cond in rule.decision_table:
                decision_table_md += f"- 條件: {cond.condition} → 結果: {cond.result}\n"
        
        return f"""請驗證以下程式碼遷移的正確性。

## 業務規則
- 名稱: {rule.name}
- 類型: {rule.rule_type.value}
- 說明: {rule.description}
{decision_table_md}

## 原始 VB 程式碼
```vb
{vb_code[:3000]}
```

## 轉譯後的 Java 程式碼
```java
{java_code[:3000]}
```

請分析：
1. 業務邏輯是否正確保留？
2. 有無遺漏的邊界條件處理？
3. Java 程式碼是否有潛在問題？
4. 建議的測試案例

以 JSON 格式回應。"""
    
    def _parse_llm_response(self, response: str, rule_name: str) -> VerificationResult:
        """解析 LLM 回應"""
        try:
            # 嘗試從回應中提取 JSON
            import re
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError("無法找到 JSON")
            
            # 轉換狀態
            status_map = {
                "passed": VerificationStatus.PASSED,
                "failed": VerificationStatus.FAILED,
                "warning": VerificationStatus.WARNING,
            }
            status = status_map.get(data.get("status", "warning"), VerificationStatus.WARNING)
            
            # 轉換測試案例
            test_cases = []
            for tc_data in data.get("test_cases", []):
                test_cases.append(TestCase(
                    name=tc_data.get("name", "Unknown"),
                    description=tc_data.get("description", ""),
                    inputs=tc_data.get("inputs", {}),
                    expected_output=tc_data.get("expected_output", ""),
                    source_rule=rule_name,
                    is_boundary_case=tc_data.get("is_boundary_case", False),
                ))
            
            return VerificationResult(
                rule_name=rule_name,
                status=status,
                message=data.get("message", ""),
                test_cases=test_cases,
                java_code_issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
            )
        
        except (json.JSONDecodeError, ValueError) as e:
            return VerificationResult(
                rule_name=rule_name,
                status=VerificationStatus.WARNING,
                message=f"無法解析 LLM 回應: {str(e)}",
                suggestions=[response[:500]],  # 保留原始回應片段
            )
    
    def verify_consistency(
        self,
        rules: List[BusinessRule],
        java_translations: Dict[str, str],
    ) -> List[VerificationResult]:
        """
        驗證業務規則一致性（靜態分析）
        
        Args:
            rules: 業務規則列表
            java_translations: Java 轉譯結果 {function_name: java_code}
            
        Returns:
            驗證結果列表
        """
        results = []
        
        for rule in rules:
            java_code = java_translations.get(rule.source_function, "")
            
            if not java_code:
                results.append(VerificationResult(
                    rule_name=rule.name,
                    status=VerificationStatus.WARNING,
                    message=f"找不到對應的 Java 程式碼: {rule.source_function}",
                ))
                continue
            
            # 基本一致性檢查
            issues = self._check_basic_consistency(rule, java_code)
            
            if issues:
                results.append(VerificationResult(
                    rule_name=rule.name,
                    status=VerificationStatus.WARNING,
                    message="發現潛在一致性問題",
                    java_code_issues=issues,
                ))
            else:
                results.append(VerificationResult(
                    rule_name=rule.name,
                    status=VerificationStatus.PASSED,
                    message="基本一致性檢查通過",
                ))
        
        self.results.extend(results)
        return results
    
    def _check_basic_consistency(self, rule: BusinessRule, java_code: str) -> List[str]:
        """基本一致性檢查"""
        issues = []
        java_lower = java_code.lower()
        
        # 檢查決策邏輯
        if rule.rule_type == BusinessRuleType.DECISION:
            if "if" not in java_lower and "switch" not in java_lower:
                issues.append("Java 程式碼中缺少條件判斷邏輯")
        
        # 檢查輸入變數
        for var in rule.input_variables:
            var_camel = self._to_camel_case(var)
            if var_camel.lower() not in java_lower and var.lower() not in java_lower:
                issues.append(f"可能缺少輸入變數: {var}")
        
        # 檢查輸出變數
        if rule.output_variable:
            out_camel = self._to_camel_case(rule.output_variable)
            if out_camel.lower() not in java_lower and rule.output_variable.lower() not in java_lower:
                issues.append(f"可能缺少輸出變數: {rule.output_variable}")
        
        return issues
    
    def _to_camel_case(self, name: str) -> str:
        """轉換為 camelCase"""
        words = name.replace("_", " ").replace("-", " ").split()
        if not words:
            return ""
        result = words[0].lower()
        for word in words[1:]:
            result += word.capitalize()
        return result
    
    def export_test_cases_junit(self, test_cases: List[TestCase], class_name: str) -> str:
        """
        將測試案例匯出為 JUnit 測試程式碼
        
        Args:
            test_cases: 測試案例列表
            class_name: 測試類別名稱
            
        Returns:
            JUnit 測試程式碼
        """
        lines = [
            "package com.example.app.test;",
            "",
            "import org.junit.jupiter.api.Test;",
            "import org.junit.jupiter.api.DisplayName;",
            "import static org.junit.jupiter.api.Assertions.*;",
            "",
            f"/**",
            f" * {class_name} 自動生成的測試案例",
            f" * 來源：行為驗證器",
            f" */",
            f"public class {class_name}Test {{",
            "",
        ]
        
        for tc in test_cases:
            test_method_name = self._to_camel_case(tc.name)
            
            lines.append(f"    @Test")
            lines.append(f'    @DisplayName("{tc.description}")')
            lines.append(f"    void {test_method_name}() {{")
            lines.append(f"        // 輸入: {json.dumps(tc.inputs, ensure_ascii=False)}")
            lines.append(f"        // 預期輸出: {tc.expected_output}")
            lines.append(f"        ")
            lines.append(f"        // TODO: 實作測試邏輯")
            if tc.is_boundary_case:
                lines.append(f"        // 注意: 這是邊界測試案例")
            lines.append(f"        fail(\"尚未實作\");")
            lines.append(f"    }}")
            lines.append("")
        
        lines.append("}")
        
        return "\n".join(lines)
    
    def generate_report_markdown(self) -> str:
        """生成驗證報告 Markdown"""
        lines = [
            "# 行為驗證報告",
            "",
            "## 摘要",
            "",
            f"- 總驗證項目: {len(self.results)}",
            f"- 通過: {sum(1 for r in self.results if r.status == VerificationStatus.PASSED)}",
            f"- 失敗: {sum(1 for r in self.results if r.status == VerificationStatus.FAILED)}",
            f"- 警告: {sum(1 for r in self.results if r.status == VerificationStatus.WARNING)}",
            f"- 略過: {sum(1 for r in self.results if r.status == VerificationStatus.SKIPPED)}",
            "",
            "## 詳細結果",
            "",
        ]
        
        status_emoji = {
            VerificationStatus.PASSED: "✅",
            VerificationStatus.FAILED: "❌",
            VerificationStatus.WARNING: "⚠️",
            VerificationStatus.SKIPPED: "⏭️",
        }
        
        for result in self.results:
            emoji = status_emoji.get(result.status, "❓")
            lines.append(f"### {emoji} {result.rule_name}")
            lines.append("")
            lines.append(f"**狀態**: {result.status.value}")
            lines.append(f"**訊息**: {result.message}")
            lines.append("")
            
            if result.java_code_issues:
                lines.append("**發現的問題:**")
                for issue in result.java_code_issues:
                    lines.append(f"- {issue}")
                lines.append("")
            
            if result.suggestions:
                lines.append("**建議:**")
                for suggestion in result.suggestions:
                    lines.append(f"- {suggestion}")
                lines.append("")
            
            if result.test_cases:
                lines.append("**測試案例:**")
                lines.append("")
                lines.append("| 名稱 | 說明 | 邊界案例 |")
                lines.append("|------|------|----------|")
                for tc in result.test_cases:
                    boundary = "是" if tc.is_boundary_case else "否"
                    lines.append(f"| {tc.name} | {tc.description} | {boundary} |")
                lines.append("")
        
        return "\n".join(lines)
    
    def get_all_results(self) -> List[VerificationResult]:
        """取得所有驗證結果"""
        return self.results
