"""VB 程式碼解析資料模型"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class VBFileType(Enum):
    """VB 檔案類型"""
    CLASS = "cls"      # 類別模組
    MODULE = "bas"     # 標準模組
    FORM = "frm"       # 表單模組
    UNKNOWN = "unknown"


class VBVisibility(Enum):
    """可見性修飾符"""
    PUBLIC = "Public"
    PRIVATE = "Private"
    FRIEND = "Friend"


class VBDataType(Enum):
    """VB 資料型別"""
    STRING = "String"
    INTEGER = "Integer"
    LONG = "Long"
    DOUBLE = "Double"
    SINGLE = "Single"
    DATE = "Date"
    BOOLEAN = "Boolean"
    VARIANT = "Variant"
    OBJECT = "Object"
    CURRENCY = "Currency"
    BYTE = "Byte"
    CUSTOM = "Custom"  # 自訂類型


@dataclass
class VBVariable:
    """VB 變數定義"""
    name: str
    data_type: str
    visibility: VBVisibility = VBVisibility.PRIVATE
    is_array: bool = False
    default_value: Optional[str] = None
    line_number: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "data_type": self.data_type,
            "visibility": self.visibility.value,
            "is_array": self.is_array,
            "default_value": self.default_value,
            "line_number": self.line_number,
        }


@dataclass
class VBParameter:
    """VB 函數參數"""
    name: str
    data_type: str
    is_optional: bool = False
    is_byref: bool = True  # VB 預設是 ByRef
    default_value: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "data_type": self.data_type,
            "is_optional": self.is_optional,
            "is_byref": self.is_byref,
            "default_value": self.default_value,
        }


@dataclass
class VBFunction:
    """VB 函數/子程序定義"""
    name: str
    visibility: VBVisibility = VBVisibility.PUBLIC
    is_sub: bool = True  # True = Sub, False = Function
    return_type: Optional[str] = None
    parameters: List[VBParameter] = field(default_factory=list)
    body: str = ""
    start_line: int = 0
    end_line: int = 0
    
    # 萃取的資訊
    sql_statements: List[str] = field(default_factory=list)
    called_functions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "visibility": self.visibility.value,
            "is_sub": self.is_sub,
            "return_type": self.return_type,
            "parameters": [p.to_dict() for p in self.parameters],
            "start_line": self.start_line,
            "end_line": self.end_line,
            "sql_statements": self.sql_statements,
            "called_functions": self.called_functions,
        }


@dataclass
class VBProperty:
    """VB 屬性存取器"""
    name: str
    data_type: str
    has_get: bool = False
    has_let: bool = False
    has_set: bool = False
    visibility: VBVisibility = VBVisibility.PUBLIC
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "data_type": self.data_type,
            "has_get": self.has_get,
            "has_let": self.has_let,
            "has_set": self.has_set,
            "visibility": self.visibility.value,
        }


@dataclass
class VBModule:
    """VB 模組（代表一個 .cls, .bas, .frm 的內容）"""
    name: str
    file_type: VBFileType
    
    # 模組級元素
    variables: List[VBVariable] = field(default_factory=list)
    constants: List[VBVariable] = field(default_factory=list)
    functions: List[VBFunction] = field(default_factory=list)
    properties: List[VBProperty] = field(default_factory=list)
    
    # 依賴關係
    references: List[str] = field(default_factory=list)  # 引用的外部類型
    
    # 選項設定
    option_explicit: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "file_type": self.file_type.value,
            "variables": [v.to_dict() for v in self.variables],
            "constants": [c.to_dict() for c in self.constants],
            "functions": [f.to_dict() for f in self.functions],
            "properties": [p.to_dict() for p in self.properties],
            "references": self.references,
            "option_explicit": self.option_explicit,
        }


@dataclass
class VBFile:
    """VB 檔案"""
    filepath: str
    filename: str
    file_type: VBFileType
    module: Optional[VBModule] = None
    raw_content: str = ""
    encoding: str = "utf-8"
    parse_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "filepath": self.filepath,
            "filename": self.filename,
            "file_type": self.file_type.value,
            "module": self.module.to_dict() if self.module else None,
            "encoding": self.encoding,
            "parse_errors": self.parse_errors,
        }


@dataclass
class VBProject:
    """VB 專案"""
    name: str
    root_path: str
    files: List[VBFile] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "root_path": self.root_path,
            "files": [f.to_dict() for f in self.files],
            "total_files": len(self.files),
            "file_types": {
                "classes": len([f for f in self.files if f.file_type == VBFileType.CLASS]),
                "modules": len([f for f in self.files if f.file_type == VBFileType.MODULE]),
                "forms": len([f for f in self.files if f.file_type == VBFileType.FORM]),
            }
        }
