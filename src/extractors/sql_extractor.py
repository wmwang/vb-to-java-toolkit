"""SQL 語句萃取器 - 從 VB 程式碼中萃取 SQL 語句"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any
from enum import Enum


class SQLStatementType(Enum):
    """SQL 語句類型"""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    EXECUTE = "EXECUTE"  # 存儲過程調用
    UNKNOWN = "UNKNOWN"


@dataclass
class ExtractedTable:
    """萃取的表格資訊"""
    name: str
    alias: Optional[str] = None
    usage_type: str = ""  # "SELECT", "INSERT", "UPDATE", "DELETE", "JOIN"
    source_file: str = ""
    source_function: str = ""
    line_number: int = 0


@dataclass
class ExtractedColumn:
    """萃取的欄位資訊"""
    name: str
    table_name: Optional[str] = None
    inferred_type: Optional[str] = None  # 從程式碼推斷的型別
    is_nullable: bool = False
    source_file: str = ""
    source_function: str = ""


@dataclass
class ExtractedSQL:
    """萃取的 SQL 語句"""
    raw_sql: str
    statement_type: SQLStatementType
    tables: List[str] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    where_columns: List[str] = field(default_factory=list)
    join_info: List[Dict[str, str]] = field(default_factory=list)
    source_file: str = ""
    source_function: str = ""
    line_number: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_sql": self.raw_sql,
            "statement_type": self.statement_type.value,
            "tables": self.tables,
            "columns": self.columns,
            "where_columns": self.where_columns,
            "join_info": self.join_info,
            "source_file": self.source_file,
            "source_function": self.source_function,
        }


class SQLExtractor:
    """SQL 語句萃取器"""
    
    # SQL 語句識別模式
    SQL_PATTERNS = {
        SQLStatementType.SELECT: re.compile(
            r"SELECT\s+(.+?)\s+FROM\s+(\w+)",
            re.IGNORECASE | re.DOTALL
        ),
        SQLStatementType.INSERT: re.compile(
            r"INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)",
            re.IGNORECASE
        ),
        SQLStatementType.UPDATE: re.compile(
            r"UPDATE\s+(\w+)\s+SET",
            re.IGNORECASE
        ),
        SQLStatementType.DELETE: re.compile(
            r"DELETE\s+FROM\s+(\w+)",
            re.IGNORECASE
        ),
        SQLStatementType.EXECUTE: re.compile(
            r"(?:EXEC|EXECUTE|CALL)\s+(\w+)",
            re.IGNORECASE
        ),
    }
    
    # 從 VB 程式碼中識別 SQL 語句的模式
    VB_SQL_PATTERNS = [
        # sql = "SELECT ..."
        re.compile(r'(["\'])(SELECT\s+.+?)\1', re.IGNORECASE | re.DOTALL),
        re.compile(r'(["\'])(INSERT\s+INTO\s+.+?)\1', re.IGNORECASE | re.DOTALL),
        re.compile(r'(["\'])(UPDATE\s+.+?SET.+?)\1', re.IGNORECASE | re.DOTALL),
        re.compile(r'(["\'])(DELETE\s+FROM\s+.+?)\1', re.IGNORECASE | re.DOTALL),
    ]
    
    # RecordSet 欄位存取模式
    RS_COLUMN_PATTERN = re.compile(
        r'rs\s*\(\s*["\'](\w+)["\']\s*\)',
        re.IGNORECASE
    )
    
    # 型別轉換模式（用於推斷欄位型別）
    TYPE_CONVERSION_PATTERNS = {
        "Long": re.compile(r'CLng\s*\(\s*rs\s*\(\s*["\'](\w+)["\']\s*\)\s*\)', re.IGNORECASE),
        "Integer": re.compile(r'CInt\s*\(\s*rs\s*\(\s*["\'](\w+)["\']\s*\)\s*\)', re.IGNORECASE),
        "String": re.compile(r'CStr\s*\(\s*rs\s*\(\s*["\'](\w+)["\']\s*\)\s*\)', re.IGNORECASE),
        "Double": re.compile(r'CDbl\s*\(\s*rs\s*\(\s*["\'](\w+)["\']\s*\)\s*\)', re.IGNORECASE),
        "Date": re.compile(r'CDate\s*\(\s*rs\s*\(\s*["\'](\w+)["\']\s*\)\s*\)', re.IGNORECASE),
        "Boolean": re.compile(r'CBool\s*\(\s*rs\s*\(\s*["\'](\w+)["\']\s*\)\s*\)', re.IGNORECASE),
        "Currency": re.compile(r'CCur\s*\(\s*rs\s*\(\s*["\'](\w+)["\']\s*\)\s*\)', re.IGNORECASE),
    }
    
    # IsNull 模式（用於識別可為 null 的欄位）
    ISNULL_PATTERN = re.compile(
        r'IsNull\s*\(\s*rs\s*\(\s*["\'](\w+)["\']\s*\)\s*\)',
        re.IGNORECASE
    )
    
    def __init__(self):
        """初始化萃取器"""
        self.extracted_sqls: List[ExtractedSQL] = []
        self.tables: Dict[str, ExtractedTable] = {}
        self.columns: Dict[str, ExtractedColumn] = {}
    
    def extract_from_code(
        self, 
        code: str, 
        source_file: str = "", 
        source_function: str = ""
    ) -> List[ExtractedSQL]:
        """
        從 VB 程式碼中萃取 SQL 語句
        
        Args:
            code: VB 程式碼
            source_file: 來源檔案名稱
            source_function: 來源函數名稱
            
        Returns:
            萃取的 SQL 語句列表
        """
        extracted = []
        
        # 處理字串串接（VB 使用 & 和 _ 進行多行串接）
        # 先移除行繼續符號
        code = self._normalize_string_concatenation(code)
        
        # 尋找 SQL 語句字串
        for pattern in self.VB_SQL_PATTERNS:
            for match in pattern.finditer(code):
                raw_sql = match.group(2)
                sql_obj = self._parse_sql(raw_sql, source_file, source_function)
                if sql_obj:
                    extracted.append(sql_obj)
        
        # 萃取 RecordSet 欄位存取
        self._extract_rs_columns(code, source_file, source_function)
        
        return extracted
    
    def _normalize_string_concatenation(self, code: str) -> str:
        """正規化 VB 字串串接"""
        # 移除行繼續符號 (& _)
        code = re.sub(r'\s*&\s*_\s*\n\s*', ' ', code)
        code = re.sub(r'\s*_\s*\n\s*', ' ', code)
        # 合併相鄰字串
        code = re.sub(r'"\s*&\s*"', '', code)
        return code
    
    def _parse_sql(
        self, 
        raw_sql: str, 
        source_file: str, 
        source_function: str
    ) -> Optional[ExtractedSQL]:
        """解析 SQL 語句"""
        # 判斷 SQL 類型
        statement_type = SQLStatementType.UNKNOWN
        for sql_type, pattern in self.SQL_PATTERNS.items():
            if pattern.search(raw_sql):
                statement_type = sql_type
                break
        
        if statement_type == SQLStatementType.UNKNOWN:
            return None
        
        tables = self._extract_tables(raw_sql)
        columns = self._extract_columns(raw_sql)
        where_columns = self._extract_where_columns(raw_sql)
        join_info = self._extract_joins(raw_sql)
        
        # 記錄表格
        for table in tables:
            if table not in self.tables:
                self.tables[table] = ExtractedTable(
                    name=table,
                    usage_type=statement_type.value,
                    source_file=source_file,
                    source_function=source_function,
                )
        
        return ExtractedSQL(
            raw_sql=raw_sql,
            statement_type=statement_type,
            tables=tables,
            columns=columns,
            where_columns=where_columns,
            join_info=join_info,
            source_file=source_file,
            source_function=source_function,
        )
    
    def _extract_tables(self, sql: str) -> List[str]:
        """從 SQL 中萃取表格名稱"""
        tables = []
        
        # FROM clause
        from_match = re.search(r'\bFROM\s+(\w+)', sql, re.IGNORECASE)
        if from_match:
            tables.append(from_match.group(1))
        
        # JOIN clauses
        join_pattern = re.compile(r'\bJOIN\s+(\w+)', re.IGNORECASE)
        for match in join_pattern.finditer(sql):
            tables.append(match.group(1))
        
        # INSERT INTO
        insert_match = re.search(r'\bINSERT\s+INTO\s+(\w+)', sql, re.IGNORECASE)
        if insert_match:
            tables.append(insert_match.group(1))
        
        # UPDATE
        update_match = re.search(r'\bUPDATE\s+(\w+)', sql, re.IGNORECASE)
        if update_match:
            tables.append(update_match.group(1))
        
        # DELETE FROM
        delete_match = re.search(r'\bDELETE\s+FROM\s+(\w+)', sql, re.IGNORECASE)
        if delete_match:
            tables.append(delete_match.group(1))
        
        return list(set(tables))  # 去重
    
    def _extract_columns(self, sql: str) -> List[str]:
        """從 SQL 中萃取欄位名稱"""
        columns = []
        
        # SELECT 欄位列表
        select_match = re.search(r'\bSELECT\s+(.+?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            cols_str = select_match.group(1)
            if cols_str.strip() != '*':
                # 分割欄位（處理別名和函數）
                for col in cols_str.split(','):
                    col = col.strip()
                    # 移除別名 (AS xxx)
                    col = re.sub(r'\s+AS\s+\w+', '', col, flags=re.IGNORECASE)
                    # 移除表格前綴 (table.column)
                    if '.' in col:
                        col = col.split('.')[-1]
                    # 移除函數包裹 (COUNT(xxx))
                    func_match = re.search(r'\w+\s*\(\s*(\w+)\s*\)', col)
                    if func_match:
                        col = func_match.group(1)
                    if col and col != '*':
                        columns.append(col.strip())
        
        # INSERT 欄位列表
        insert_match = re.search(r'\bINSERT\s+INTO\s+\w+\s*\(([^)]+)\)', sql, re.IGNORECASE)
        if insert_match:
            for col in insert_match.group(1).split(','):
                columns.append(col.strip())
        
        # UPDATE SET 欄位
        set_match = re.search(r'\bSET\s+(.+?)(?:\s+WHERE|$)', sql, re.IGNORECASE | re.DOTALL)
        if set_match:
            for assignment in set_match.group(1).split(','):
                if '=' in assignment:
                    col = assignment.split('=')[0].strip()
                    columns.append(col)
        
        return list(set(columns))  # 去重
    
    def _extract_where_columns(self, sql: str) -> List[str]:
        """從 WHERE 子句中萃取欄位"""
        columns = []
        
        where_match = re.search(r'\bWHERE\s+(.+?)(?:\s+ORDER|\s+GROUP|$)', sql, re.IGNORECASE | re.DOTALL)
        if where_match:
            where_clause = where_match.group(1)
            # 尋找比較運算中的欄位
            col_pattern = re.compile(r'(\w+)\s*(?:=|<>|<|>|<=|>=|LIKE|IN|IS)', re.IGNORECASE)
            for match in col_pattern.finditer(where_clause):
                col = match.group(1)
                if col.upper() not in ('AND', 'OR', 'NOT', 'NULL'):
                    columns.append(col)
        
        return list(set(columns))
    
    def _extract_joins(self, sql: str) -> List[Dict[str, str]]:
        """萃取 JOIN 資訊"""
        joins = []
        
        join_pattern = re.compile(
            r'(INNER|LEFT|RIGHT|FULL|OUTER)?\s*JOIN\s+(\w+)\s+(?:AS\s+)?(\w+)?\s+ON\s+(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)',
            re.IGNORECASE
        )
        
        for match in join_pattern.finditer(sql):
            joins.append({
                "type": match.group(1) or "INNER",
                "table": match.group(2),
                "alias": match.group(3),
                "left_table": match.group(4),
                "left_column": match.group(5),
                "right_table": match.group(6),
                "right_column": match.group(7),
            })
        
        return joins
    
    def _extract_rs_columns(
        self, 
        code: str, 
        source_file: str, 
        source_function: str
    ):
        """從 RecordSet 欄位存取中萃取欄位資訊"""
        # 基本欄位存取
        for match in self.RS_COLUMN_PATTERN.finditer(code):
            col_name = match.group(1)
            if col_name not in self.columns:
                self.columns[col_name] = ExtractedColumn(
                    name=col_name,
                    source_file=source_file,
                    source_function=source_function,
                )
        
        # 從型別轉換推斷型別
        for vb_type, pattern in self.TYPE_CONVERSION_PATTERNS.items():
            for match in pattern.finditer(code):
                col_name = match.group(1)
                if col_name not in self.columns:
                    self.columns[col_name] = ExtractedColumn(
                        name=col_name,
                        inferred_type=vb_type,
                        source_file=source_file,
                        source_function=source_function,
                    )
                else:
                    self.columns[col_name].inferred_type = vb_type
        
        # 從 IsNull 識別可為 null 的欄位
        for match in self.ISNULL_PATTERN.finditer(code):
            col_name = match.group(1)
            if col_name in self.columns:
                self.columns[col_name].is_nullable = True
            else:
                self.columns[col_name] = ExtractedColumn(
                    name=col_name,
                    is_nullable=True,
                    source_file=source_file,
                    source_function=source_function,
                )
    
    def get_summary(self) -> Dict[str, Any]:
        """取得萃取摘要"""
        return {
            "total_sql_statements": len(self.extracted_sqls),
            "total_tables": len(self.tables),
            "total_columns": len(self.columns),
            "tables": list(self.tables.keys()),
            "columns_with_types": {
                name: {
                    "type": col.inferred_type or "Unknown",
                    "nullable": col.is_nullable,
                }
                for name, col in self.columns.items()
            },
        }
