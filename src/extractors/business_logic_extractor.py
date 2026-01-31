"""業務邏輯提取器 (BLE) - 從 VB 程式碼中萃取業務規則"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class BusinessRuleType(Enum):
    """業務規則類型"""
    DECISION = "decision"         # 決策邏輯 (IF/CASE)
    CALCULATION = "calculation"   # 計算公式
    VALIDATION = "validation"     # 驗證規則
    WORKFLOW = "workflow"         # 工作流程/狀態轉換
    CONSTRAINT = "constraint"     # 約束條件


@dataclass
class DecisionCondition:
    """決策條件"""
    condition: str
    result: str
    line_number: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition": self.condition,
            "result": self.result,
        }


@dataclass
class BusinessRule:
    """業務規則"""
    name: str
    rule_type: BusinessRuleType
    description: str = ""
    source_function: str = ""
    source_file: str = ""
    start_line: int = 0
    end_line: int = 0
    
    # 決策表（用於 IF/CASE 邏輯）
    decision_table: List[DecisionCondition] = field(default_factory=list)
    
    # 計算公式
    formula: str = ""
    input_variables: List[str] = field(default_factory=list)
    output_variable: str = ""
    
    # 原始程式碼片段
    raw_code: str = ""
    
    # 偽代碼（由 LLM 生成或自動轉換）
    pseudocode: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "rule_type": self.rule_type.value,
            "description": self.description,
            "source_function": self.source_function,
            "source_file": self.source_file,
            "decision_table": [d.to_dict() for d in self.decision_table],
            "formula": self.formula,
            "input_variables": self.input_variables,
            "output_variable": self.output_variable,
            "pseudocode": self.pseudocode,
        }


class BusinessLogicExtractor:
    """業務邏輯提取器"""
    
    # 識別業務邏輯的模式
    PATTERNS = {
        # IF-THEN-ELSE 結構
        "if_block": re.compile(
            r"If\s+(.+?)\s+Then\s*$",
            re.IGNORECASE | re.MULTILINE
        ),
        "elseif": re.compile(
            r"ElseIf\s+(.+?)\s+Then\s*$",
            re.IGNORECASE | re.MULTILINE
        ),
        "else": re.compile(
            r"^\s*Else\s*$",
            re.IGNORECASE | re.MULTILINE
        ),
        "end_if": re.compile(
            r"^\s*End\s+If\s*$",
            re.IGNORECASE | re.MULTILINE
        ),
        
        # SELECT CASE 結構
        "select_case": re.compile(
            r"Select\s+Case\s+(.+?)\s*$",
            re.IGNORECASE | re.MULTILINE
        ),
        "case": re.compile(
            r"^\s*Case\s+(.+?)\s*$",
            re.IGNORECASE | re.MULTILINE
        ),
        "end_select": re.compile(
            r"^\s*End\s+Select\s*$",
            re.IGNORECASE | re.MULTILINE
        ),
        
        # 驗證模式
        "validation": re.compile(
            r"If\s+(?:Len|IsNull|IsEmpty|IsNumeric|IsDate)\s*\(",
            re.IGNORECASE
        ),
        "error_raise": re.compile(
            r"Err\.Raise",
            re.IGNORECASE
        ),
        
        # 計算模式
        "calculation": re.compile(
            r"(\w+)\s*=\s*([^=].+?)(?:\s*$|\s*\')",
            re.IGNORECASE | re.MULTILINE
        ),
    }
    
    # 技術性代碼關鍵字（需要過濾）
    TECHNICAL_KEYWORDS = {
        "rs.open", "rs.close", "connection",
        "msgbox", "form_load", "form_unload",
        "click", "change", "keypress",
        "set ", "dim ", "on error",
    }
    
    def __init__(self):
        """初始化提取器"""
        self.rules: List[BusinessRule] = []
    
    def extract_from_function(
        self, 
        func_name: str,
        func_body: str,
        source_file: str = ""
    ) -> List[BusinessRule]:
        """
        從函數中萃取業務規則
        
        Args:
            func_name: 函數名稱
            func_body: 函數體
            source_file: 來源檔案
            
        Returns:
            萃取的業務規則列表
        """
        rules = []
        
        # 跳過純技術性函數
        if self._is_technical_code(func_name, func_body):
            return rules
        
        # 萃取決策邏輯 (IF-THEN-ELSE)
        if_rules = self._extract_if_logic(func_name, func_body, source_file)
        rules.extend(if_rules)
        
        # 萃取 SELECT CASE 邏輯
        case_rules = self._extract_case_logic(func_name, func_body, source_file)
        rules.extend(case_rules)
        
        # 萃取計算公式
        calc_rules = self._extract_calculations(func_name, func_body, source_file)
        rules.extend(calc_rules)
        
        # 萃取驗證規則
        validation_rules = self._extract_validations(func_name, func_body, source_file)
        rules.extend(validation_rules)
        
        self.rules.extend(rules)
        return rules
    
    def _is_technical_code(self, func_name: str, func_body: str) -> bool:
        """判斷是否為純技術性代碼"""
        # 事件處理器
        if any(suffix in func_name.lower() for suffix in ["_click", "_load", "_change", "_keypress"]):
            return True
        
        # 技術性關鍵字
        body_lower = func_body.lower()
        tech_score = sum(1 for kw in self.TECHNICAL_KEYWORDS if kw in body_lower)
        biz_score = len(self._extract_business_indicators(func_body))
        
        # 如果技術性代碼比重太高
        return tech_score > biz_score * 2
    
    def _extract_business_indicators(self, code: str) -> List[str]:
        """萃取業務指標（用於判斷是否為業務邏輯）"""
        indicators = []
        
        # 業務關鍵字
        business_keywords = [
            "price", "amount", "discount", "total", "tax",
            "quantity", "stock", "balance", "rate",
            "customer", "order", "product", "invoice",
            "calculate", "validate", "check", "verify",
        ]
        
        code_lower = code.lower()
        for kw in business_keywords:
            if kw in code_lower:
                indicators.append(kw)
        
        return indicators
    
    def _extract_if_logic(
        self, 
        func_name: str, 
        func_body: str, 
        source_file: str
    ) -> List[BusinessRule]:
        """萃取 IF-THEN-ELSE 邏輯"""
        rules = []
        
        # 尋找 IF 區塊
        lines = func_body.split("\n")
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if_match = self.PATTERNS["if_block"].search(line)
            if if_match and not self._is_single_line_if(line):
                # 找到 IF 區塊開始
                condition = if_match.group(1).strip()
                decision_table = []
                block_code = [lines[i]]
                
                # 收集 IF 區塊的內容
                result_lines = []
                j = i + 1
                
                while j < len(lines):
                    inner_line = lines[j].strip()
                    block_code.append(lines[j])
                    
                    if self.PATTERNS["end_if"].match(inner_line):
                        # IF 結束
                        if result_lines:
                            result = self._summarize_result(result_lines)
                            decision_table.append(DecisionCondition(
                                condition=condition,
                                result=result,
                            ))
                        break
                    elif self.PATTERNS["elseif"].match(inner_line):
                        # ELSEIF
                        if result_lines:
                            result = self._summarize_result(result_lines)
                            decision_table.append(DecisionCondition(
                                condition=condition,
                                result=result,
                            ))
                        condition = self.PATTERNS["elseif"].match(inner_line).group(1).strip()
                        result_lines = []
                    elif self.PATTERNS["else"].match(inner_line):
                        # ELSE
                        if result_lines:
                            result = self._summarize_result(result_lines)
                            decision_table.append(DecisionCondition(
                                condition=condition,
                                result=result,
                            ))
                        condition = "其他情況"
                        result_lines = []
                    else:
                        result_lines.append(inner_line)
                    
                    j += 1
                
                if decision_table:
                    rule = BusinessRule(
                        name=f"{func_name} 決策邏輯",
                        rule_type=BusinessRuleType.DECISION,
                        source_function=func_name,
                        source_file=source_file,
                        decision_table=decision_table,
                        raw_code="\n".join(block_code),
                        pseudocode=self._generate_pseudocode(decision_table),
                    )
                    rules.append(rule)
                
                i = j + 1
            else:
                i += 1
        
        return rules
    
    def _is_single_line_if(self, line: str) -> bool:
        """判斷是否為單行 IF"""
        # 單行 IF 格式: If condition Then action
        return "then" in line.lower() and not line.strip().endswith("Then")
    
    def _extract_case_logic(
        self, 
        func_name: str, 
        func_body: str, 
        source_file: str
    ) -> List[BusinessRule]:
        """萃取 SELECT CASE 邏輯"""
        rules = []
        
        lines = func_body.split("\n")
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            select_match = self.PATTERNS["select_case"].search(line)
            if select_match:
                case_var = select_match.group(1).strip()
                decision_table = []
                block_code = [lines[i]]
                
                current_case = ""
                result_lines = []
                j = i + 1
                
                while j < len(lines):
                    inner_line = lines[j].strip()
                    block_code.append(lines[j])
                    
                    if self.PATTERNS["end_select"].match(inner_line):
                        if current_case and result_lines:
                            result = self._summarize_result(result_lines)
                            decision_table.append(DecisionCondition(
                                condition=f"{case_var} = {current_case}",
                                result=result,
                            ))
                        break
                    
                    case_match = self.PATTERNS["case"].match(inner_line)
                    if case_match:
                        if current_case and result_lines:
                            result = self._summarize_result(result_lines)
                            decision_table.append(DecisionCondition(
                                condition=f"{case_var} = {current_case}",
                                result=result,
                            ))
                        current_case = case_match.group(1).strip()
                        result_lines = []
                    else:
                        result_lines.append(inner_line)
                    
                    j += 1
                
                if decision_table:
                    rule = BusinessRule(
                        name=f"{func_name} 狀態邏輯 ({case_var})",
                        rule_type=BusinessRuleType.DECISION,
                        source_function=func_name,
                        source_file=source_file,
                        decision_table=decision_table,
                        raw_code="\n".join(block_code),
                        pseudocode=self._generate_pseudocode(decision_table),
                    )
                    rules.append(rule)
                
                i = j + 1
            else:
                i += 1
        
        return rules
    
    def _extract_calculations(
        self, 
        func_name: str, 
        func_body: str, 
        source_file: str
    ) -> List[BusinessRule]:
        """萃取計算公式"""
        rules = []
        
        # 尋找有意義的計算（排除簡單賦值）
        calc_keywords = ["*", "/", "+", "-", "mod", "^"]
        
        for match in self.PATTERNS["calculation"].finditer(func_body):
            var_name = match.group(1).strip()
            expression = match.group(2).strip()
            
            # 檢查是否包含計算運算符
            if any(op in expression.lower() for op in calc_keywords):
                # 排除技術性變數
                if var_name.lower() in ["i", "j", "k", "n", "count", "index"]:
                    continue
                
                # 萃取輸入變數
                input_vars = re.findall(r'\b([a-zA-Z_]\w*)\b', expression)
                input_vars = [v for v in input_vars if v.lower() not in {
                    "and", "or", "not", "mod", "if", "then", "else"
                }]
                
                rule = BusinessRule(
                    name=f"計算: {var_name}",
                    rule_type=BusinessRuleType.CALCULATION,
                    source_function=func_name,
                    source_file=source_file,
                    formula=expression,
                    input_variables=list(set(input_vars)),
                    output_variable=var_name,
                    raw_code=match.group(0),
                )
                rules.append(rule)
        
        return rules
    
    def _extract_validations(
        self, 
        func_name: str, 
        func_body: str, 
        source_file: str
    ) -> List[BusinessRule]:
        """萃取驗證規則"""
        rules = []
        
        # 尋找驗證模式
        validation_patterns = [
            (r"If\s+Len\s*\(\s*(\w+)\s*\)\s*([<>=]+)\s*(\d+)", "長度檢查"),
            (r"If\s+IsNull\s*\(\s*(.+?)\s*\)", "空值檢查"),
            (r"If\s+IsEmpty\s*\(\s*(.+?)\s*\)", "空值檢查"),
            (r"If\s+IsNumeric\s*\(\s*(.+?)\s*\)", "數值驗證"),
            (r"If\s+IsDate\s*\(\s*(.+?)\s*\)", "日期驗證"),
            (r"If\s+(.+?)\s*([<>]=?)\s*0\b", "數值範圍檢查"),
        ]
        
        for pattern, desc in validation_patterns:
            for match in re.finditer(pattern, func_body, re.IGNORECASE):
                rule = BusinessRule(
                    name=f"驗證: {desc}",
                    rule_type=BusinessRuleType.VALIDATION,
                    source_function=func_name,
                    source_file=source_file,
                    description=desc,
                    raw_code=match.group(0),
                )
                rules.append(rule)
        
        return rules
    
    def _summarize_result(self, lines: List[str]) -> str:
        """摘要結果行"""
        # 過濾空行和註解
        meaningful_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("'"):
                meaningful_lines.append(line)
        
        if not meaningful_lines:
            return "(無動作)"
        
        # 如果只有一行，直接返回
        if len(meaningful_lines) == 1:
            return meaningful_lines[0]
        
        # 找出主要動作
        for line in meaningful_lines:
            if "=" in line and not line.startswith("If"):
                return line
        
        return meaningful_lines[0]
    
    def _generate_pseudocode(self, decision_table: List[DecisionCondition]) -> str:
        """生成偽代碼"""
        lines = []
        
        for i, decision in enumerate(decision_table):
            if i == 0:
                lines.append(f"IF {decision.condition} THEN")
            elif decision.condition == "其他情況":
                lines.append(f"ELSE")
            else:
                lines.append(f"ELSE IF {decision.condition} THEN")
            
            lines.append(f"    {decision.result}")
        
        lines.append("END IF")
        
        return "\n".join(lines)
    
    def generate_decision_table_markdown(self, rule: BusinessRule) -> str:
        """生成決策表的 Markdown 格式"""
        if rule.rule_type != BusinessRuleType.DECISION:
            return ""
        
        lines = [
            f"## {rule.name}",
            "",
            f"**來源**: {rule.source_file} / {rule.source_function}",
            "",
            "### 決策表",
            "",
            "| 條件 | 結果 |",
            "|------|------|",
        ]
        
        for decision in rule.decision_table:
            lines.append(f"| {decision.condition} | {decision.result} |")
        
        lines.append("")
        lines.append("### 偽代碼")
        lines.append("```")
        lines.append(rule.pseudocode)
        lines.append("```")
        
        return "\n".join(lines)
    
    def get_summary(self) -> Dict[str, Any]:
        """取得萃取摘要"""
        by_type = {}
        for rule in self.rules:
            rule_type = rule.rule_type.value
            by_type[rule_type] = by_type.get(rule_type, 0) + 1
        
        return {
            "total_rules": len(self.rules),
            "by_type": by_type,
            "rules": [rule.to_dict() for rule in self.rules],
        }
