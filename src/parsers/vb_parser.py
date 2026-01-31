"""VB 程式碼解析器 - 解析 VB 檔案結構"""

import re
from typing import List, Optional, Tuple
from dataclasses import dataclass

from .models import (
    VBFile, VBModule, VBFunction, VBVariable, VBParameter, 
    VBProperty, VBFileType, VBVisibility
)


class VBParser:
    """VB 程式碼解析器"""
    
    # 正則表達式模式
    PATTERNS = {
        # Option Explicit
        "option_explicit": re.compile(r"^\s*Option\s+Explicit\s*$", re.IGNORECASE | re.MULTILINE),
        
        # 變數宣告: Dim/Private/Public varName As Type
        "variable": re.compile(
            r"^\s*(Dim|Private|Public|Global)\s+(\w+)(?:\(.*?\))?\s+As\s+(\w+(?:\.\w+)?)",
            re.IGNORECASE | re.MULTILINE
        ),
        
        # 常數宣告: Const NAME = value 或 Private Const NAME As Type = value
        "constant": re.compile(
            r"^\s*(Private|Public)?\s*Const\s+(\w+)(?:\s+As\s+(\w+))?\s*=\s*(.+)$",
            re.IGNORECASE | re.MULTILINE
        ),
        
        # 函數/子程序開始
        "function_start": re.compile(
            r"^\s*(Public|Private|Friend)?\s*(Function|Sub)\s+(\w+)\s*\(([^)]*)\)(?:\s+As\s+(\w+))?",
            re.IGNORECASE | re.MULTILINE
        ),
        
        # 函數/子程序結束
        "function_end": re.compile(
            r"^\s*End\s+(Function|Sub)\s*$",
            re.IGNORECASE | re.MULTILINE
        ),
        
        # 屬性開始 (Property Get/Let/Set)
        "property_start": re.compile(
            r"^\s*(Public|Private)?\s*Property\s+(Get|Let|Set)\s+(\w+)\s*\(([^)]*)\)(?:\s+As\s+(\w+))?",
            re.IGNORECASE | re.MULTILINE
        ),
        
        # 屬性結束
        "property_end": re.compile(
            r"^\s*End\s+Property\s*$",
            re.IGNORECASE | re.MULTILINE
        ),
        
        # 類別屬性 (VB_Name, etc)
        "attribute": re.compile(
            r"^\s*Attribute\s+(\w+)\s*=\s*(.+)$",
            re.IGNORECASE | re.MULTILINE
        ),
    }
    
    def __init__(self):
        """初始化解析器"""
        pass
    
    def parse(self, vb_file: VBFile) -> VBFile:
        """
        解析 VB 檔案
        
        Args:
            vb_file: VB 檔案物件
            
        Returns:
            帶有解析結果的 VB 檔案物件
        """
        try:
            content = vb_file.raw_content
            lines = content.split("\n")
            
            # 建立模組
            module_name = self._extract_module_name(vb_file.filename, content)
            module = VBModule(
                name=module_name,
                file_type=vb_file.file_type,
            )
            
            # 解析各種元素
            module.option_explicit = self._check_option_explicit(content)
            module.variables = self._parse_variables(content, lines)
            module.constants = self._parse_constants(content, lines)
            module.functions = self._parse_functions(content, lines)
            module.properties = self._parse_properties(content, lines)
            module.references = self._extract_references(content)
            
            vb_file.module = module
            
        except Exception as e:
            vb_file.parse_errors.append(f"解析錯誤: {str(e)}")
        
        return vb_file
    
    def _extract_module_name(self, filename: str, content: str) -> str:
        """提取模組名稱"""
        # 嘗試從 Attribute VB_Name 取得
        match = re.search(r'Attribute\s+VB_Name\s*=\s*"([^"]+)"', content, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # 否則使用檔名（去掉副檔名）
        return filename.rsplit(".", 1)[0]
    
    def _check_option_explicit(self, content: str) -> bool:
        """檢查是否有 Option Explicit"""
        return bool(self.PATTERNS["option_explicit"].search(content))
    
    def _parse_variables(self, content: str, lines: List[str]) -> List[VBVariable]:
        """解析變數宣告"""
        variables = []
        
        for match in self.PATTERNS["variable"].finditer(content):
            visibility_str = match.group(1).upper()
            var_name = match.group(2)
            var_type = match.group(3)
            
            # 轉換可見性
            visibility = VBVisibility.PRIVATE
            if visibility_str in ("PUBLIC", "GLOBAL"):
                visibility = VBVisibility.PUBLIC
            
            # 計算行號
            line_number = content[:match.start()].count("\n") + 1
            
            variables.append(VBVariable(
                name=var_name,
                data_type=var_type,
                visibility=visibility,
                is_array="(" in match.group(0),
                line_number=line_number,
            ))
        
        return variables
    
    def _parse_constants(self, content: str, lines: List[str]) -> List[VBVariable]:
        """解析常數宣告"""
        constants = []
        
        for match in self.PATTERNS["constant"].finditer(content):
            visibility_str = match.group(1) or "Private"
            const_name = match.group(2)
            const_type = match.group(3) or "Variant"
            const_value = match.group(4).strip()
            
            visibility = VBVisibility.PUBLIC if visibility_str.upper() == "PUBLIC" else VBVisibility.PRIVATE
            line_number = content[:match.start()].count("\n") + 1
            
            constants.append(VBVariable(
                name=const_name,
                data_type=const_type,
                visibility=visibility,
                default_value=const_value,
                line_number=line_number,
            ))
        
        return constants
    
    def _parse_functions(self, content: str, lines: List[str]) -> List[VBFunction]:
        """解析函數和子程序"""
        functions = []
        
        # 找出所有函數的起始位置
        func_starts = list(self.PATTERNS["function_start"].finditer(content))
        func_ends = list(self.PATTERNS["function_end"].finditer(content))
        
        for start_match in func_starts:
            visibility_str = (start_match.group(1) or "Public").upper()
            func_type = start_match.group(2).upper()
            func_name = start_match.group(3)
            params_str = start_match.group(4)
            return_type = start_match.group(5)
            
            # 解析參數
            parameters = self._parse_parameters(params_str)
            
            # 計算行號
            start_line = content[:start_match.start()].count("\n") + 1
            
            # 找到對應的 End Function/Sub
            end_line = start_line
            func_body = ""
            
            for end_match in func_ends:
                if end_match.start() > start_match.end():
                    end_type = end_match.group(1).upper()
                    if end_type == func_type:
                        end_line = content[:end_match.start()].count("\n") + 1
                        # 提取函數體
                        func_body = content[start_match.end():end_match.start()].strip()
                        break
            
            # 轉換可見性
            visibility = VBVisibility.PRIVATE
            if visibility_str == "PUBLIC":
                visibility = VBVisibility.PUBLIC
            elif visibility_str == "FRIEND":
                visibility = VBVisibility.FRIEND
            
            func = VBFunction(
                name=func_name,
                visibility=visibility,
                is_sub=(func_type == "SUB"),
                return_type=return_type,
                parameters=parameters,
                body=func_body,
                start_line=start_line,
                end_line=end_line,
            )
            
            # 從函數體中萃取 SQL 語句
            func.sql_statements = self._extract_sql_from_body(func_body)
            
            # 從函數體中萃取呼叫的函數
            func.called_functions = self._extract_called_functions(func_body)
            
            functions.append(func)
        
        return functions
    
    def _parse_parameters(self, params_str: str) -> List[VBParameter]:
        """解析函數參數列表"""
        if not params_str or not params_str.strip():
            return []
        
        parameters = []
        
        # 參數格式: [Optional] [ByVal|ByRef] ParamName As Type [= DefaultValue]
        param_pattern = re.compile(
            r"(Optional\s+)?(ByVal|ByRef)?\s*(\w+)(?:\s+As\s+(\w+))?(?:\s*=\s*(.+))?",
            re.IGNORECASE
        )
        
        # 分割參數（注意逗號可能在括號內）
        for param in params_str.split(","):
            param = param.strip()
            if not param:
                continue
            
            match = param_pattern.match(param)
            if match:
                is_optional = bool(match.group(1))
                is_byref = (match.group(2) or "ByRef").upper() == "BYREF"
                param_name = match.group(3)
                param_type = match.group(4) or "Variant"
                default_value = match.group(5)
                
                parameters.append(VBParameter(
                    name=param_name,
                    data_type=param_type,
                    is_optional=is_optional,
                    is_byref=is_byref,
                    default_value=default_value,
                ))
        
        return parameters
    
    def _parse_properties(self, content: str, lines: List[str]) -> List[VBProperty]:
        """解析屬性"""
        properties_dict = {}  # 用字典來合併 Get/Let/Set
        
        for match in self.PATTERNS["property_start"].finditer(content):
            visibility_str = (match.group(1) or "Public").upper()
            prop_type = match.group(2).upper()  # GET, LET, SET
            prop_name = match.group(3)
            return_type = match.group(5) or "Variant"
            
            visibility = VBVisibility.PUBLIC if visibility_str == "PUBLIC" else VBVisibility.PRIVATE
            
            if prop_name not in properties_dict:
                properties_dict[prop_name] = VBProperty(
                    name=prop_name,
                    data_type=return_type,
                    visibility=visibility,
                )
            
            prop = properties_dict[prop_name]
            if prop_type == "GET":
                prop.has_get = True
                prop.data_type = return_type  # 從 Get 取得型別
            elif prop_type == "LET":
                prop.has_let = True
            elif prop_type == "SET":
                prop.has_set = True
        
        return list(properties_dict.values())
    
    def _extract_references(self, content: str) -> List[str]:
        """提取引用的外部類型"""
        references = set()
        
        # 尋找 As SomeType 的模式
        type_pattern = re.compile(r"As\s+(\w+(?:\.\w+)?)", re.IGNORECASE)
        for match in type_pattern.finditer(content):
            type_name = match.group(1)
            # 排除內建類型
            if type_name.upper() not in {
                "STRING", "INTEGER", "LONG", "DOUBLE", "SINGLE", 
                "DATE", "BOOLEAN", "VARIANT", "OBJECT", "BYTE", "CURRENCY"
            }:
                references.add(type_name)
        
        # 尋找 New SomeType 的模式
        new_pattern = re.compile(r"New\s+(\w+(?:\.\w+)?)", re.IGNORECASE)
        for match in new_pattern.finditer(content):
            references.add(match.group(1))
        
        return sorted(list(references))
    
    def _extract_sql_from_body(self, body: str) -> List[str]:
        """從函數體中萃取 SQL 語句"""
        sql_statements = []
        
        # 尋找 SQL 語句模式
        sql_patterns = [
            r"\"SELECT\s+[^\"]+\"",
            r"\"INSERT\s+INTO\s+[^\"]+\"",
            r"\"UPDATE\s+[^\"]+\"",
            r"\"DELETE\s+FROM\s+[^\"]+\"",
        ]
        
        for pattern in sql_patterns:
            for match in re.finditer(pattern, body, re.IGNORECASE):
                sql = match.group(0).strip('"')
                
                # 處理字串串接 (& _)
                # 簡化處理：只取主要部分
                sql = re.sub(r"\s*&\s*_?\s*", " ", sql)
                sql = re.sub(r"'\s*&\s*", " ", sql)
                sql = re.sub(r"\s*&\s*'", " ", sql)
                
                sql_statements.append(sql.strip())
        
        return sql_statements
    
    def _extract_called_functions(self, body: str) -> List[str]:
        """從函數體中萃取呼叫的函數名稱"""
        called = set()
        
        # 簡單的函數呼叫模式: FunctionName(...)
        # 排除關鍵字
        keywords = {
            "IF", "THEN", "ELSE", "END", "FOR", "NEXT", "DO", "LOOP", 
            "WHILE", "WEND", "SELECT", "CASE", "WITH", "SET", "DIM",
            "AND", "OR", "NOT", "MOD", "AS", "NEW", "NOTHING"
        }
        
        call_pattern = re.compile(r"\b([A-Za-z_]\w*)\s*\(", re.IGNORECASE)
        for match in call_pattern.finditer(body):
            func_name = match.group(1)
            if func_name.upper() not in keywords:
                called.add(func_name)
        
        return sorted(list(called))
