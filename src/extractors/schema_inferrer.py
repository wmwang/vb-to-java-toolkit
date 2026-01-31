"""Schema 推斷器 - 從萃取的 SQL 資訊推斷資料庫 Schema"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import json
from pathlib import Path


@dataclass
class InferredColumn:
    """推斷的欄位"""
    name: str
    data_type: str = "Unknown"
    java_type: str = "Object"
    is_nullable: bool = False
    is_primary_key: bool = False
    is_foreign_key: bool = False
    references_table: Optional[str] = None
    references_column: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "data_type": self.data_type,
            "java_type": self.java_type,
            "is_nullable": self.is_nullable,
            "is_primary_key": self.is_primary_key,
            "is_foreign_key": self.is_foreign_key,
            "references": {
                "table": self.references_table,
                "column": self.references_column,
            } if self.is_foreign_key else None,
        }


@dataclass
class InferredTable:
    """推斷的表格"""
    name: str
    columns: Dict[str, InferredColumn] = field(default_factory=dict)
    usage_count: int = 0
    source_files: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "columns": {name: col.to_dict() for name, col in self.columns.items()},
            "usage_count": self.usage_count,
            "source_files": self.source_files,
        }


class SchemaInferrer:
    """Schema 推斷器"""
    
    # VB 型別到 Java 型別的對應
    VB_TO_JAVA_TYPE = {
        "Long": "Long",
        "Integer": "Integer",
        "String": "String",
        "Double": "Double",
        "Single": "Float",
        "Date": "LocalDateTime",
        "Boolean": "Boolean",
        "Currency": "BigDecimal",
        "Variant": "Object",
        "Byte": "Byte",
    }
    
    # VB 型別到 SQL 型別的對應
    VB_TO_SQL_TYPE = {
        "Long": "BIGINT",
        "Integer": "INT",
        "String": "VARCHAR(255)",
        "Double": "DECIMAL(18,4)",
        "Single": "FLOAT",
        "Date": "DATETIME",
        "Boolean": "BIT",
        "Currency": "DECIMAL(18,4)",
        "Variant": "VARCHAR(MAX)",
        "Byte": "TINYINT",
    }
    
    def __init__(self):
        """初始化推斷器"""
        self.tables: Dict[str, InferredTable] = {}
        self.column_table_map: Dict[str, List[str]] = {}  # 欄位可能屬於哪些表格
    
    def process_sql_extractor_results(self, sql_extractor) -> None:
        """
        處理 SQLExtractor 的萃取結果
        
        Args:
            sql_extractor: SQLExtractor 實例
        """
        # 處理表格
        for table_name, table_info in sql_extractor.tables.items():
            self._add_or_update_table(
                table_name,
                source_file=table_info.source_file,
            )
        
        # 處理萃取的 SQL 語句中的欄位
        for sql_obj in sql_extractor.extracted_sqls:
            for table in sql_obj.tables:
                for col in sql_obj.columns:
                    self._add_column_to_table(table, col)
                for col in sql_obj.where_columns:
                    self._add_column_to_table(table, col)
            
            # 處理 JOIN 資訊（用於推斷外鍵）
            for join in sql_obj.join_info:
                self._process_join_as_fk(join)
        
        # 處理 RecordSet 欄位
        for col_name, col_info in sql_extractor.columns.items():
            # 如果無法確定表格，先加到 column_table_map
            if col_name not in self.column_table_map:
                self.column_table_map[col_name] = []
            
            # 如果有推斷的型別，更新所有可能的表格
            if col_info.inferred_type:
                self._update_column_type(
                    col_name,
                    col_info.inferred_type,
                    col_info.is_nullable,
                )
    
    def _add_or_update_table(self, table_name: str, source_file: str = ""):
        """新增或更新表格"""
        if table_name not in self.tables:
            self.tables[table_name] = InferredTable(name=table_name)
        
        self.tables[table_name].usage_count += 1
        
        if source_file and source_file not in self.tables[table_name].source_files:
            self.tables[table_name].source_files.append(source_file)
    
    def _add_column_to_table(self, table_name: str, column_name: str):
        """新增欄位到表格"""
        if table_name not in self.tables:
            self.tables[table_name] = InferredTable(name=table_name)
        
        if column_name not in self.tables[table_name].columns:
            self.tables[table_name].columns[column_name] = InferredColumn(name=column_name)
        
        # 記錄欄位可能屬於的表格
        if column_name not in self.column_table_map:
            self.column_table_map[column_name] = []
        if table_name not in self.column_table_map[column_name]:
            self.column_table_map[column_name].append(table_name)
        
        # 推斷主鍵（根據命名慣例）
        if column_name.lower() == f"{table_name.lower()}id" or column_name.lower() == "id":
            self.tables[table_name].columns[column_name].is_primary_key = True
            self.tables[table_name].columns[column_name].data_type = "BIGINT"
            self.tables[table_name].columns[column_name].java_type = "Long"
    
    def _update_column_type(
        self, 
        column_name: str, 
        vb_type: str, 
        is_nullable: bool
    ):
        """更新欄位型別"""
        java_type = self.VB_TO_JAVA_TYPE.get(vb_type, "Object")
        sql_type = self.VB_TO_SQL_TYPE.get(vb_type, "VARCHAR(255)")
        
        # 更新所有可能的表格中的該欄位
        for table_name in self.column_table_map.get(column_name, []):
            if table_name in self.tables:
                col = self.tables[table_name].columns.get(column_name)
                if col:
                    col.data_type = sql_type
                    col.java_type = java_type
                    if is_nullable:
                        col.is_nullable = True
    
    def _process_join_as_fk(self, join_info: Dict[str, str]):
        """從 JOIN 資訊推斷外鍵關係"""
        left_table = join_info.get("left_table", "")
        left_col = join_info.get("left_column", "")
        right_table = join_info.get("right_table", "")
        right_col = join_info.get("right_column", "")
        
        if not all([left_table, left_col, right_table, right_col]):
            return
        
        # 判斷哪邊是外鍵（通常欄位名稱包含 "ID" 且不是 PK 的那邊是 FK）
        # 簡化判斷：如果欄位名稱像 "CustomerID" 且表格是 "Orders"，則 Orders.CustomerID 是 FK
        if left_col.lower().endswith("id") and left_col.lower() != f"{left_table.lower()}id":
            self._mark_as_foreign_key(left_table, left_col, right_table, right_col)
        elif right_col.lower().endswith("id") and right_col.lower() != f"{right_table.lower()}id":
            self._mark_as_foreign_key(right_table, right_col, left_table, left_col)
    
    def _mark_as_foreign_key(
        self, 
        table: str, 
        column: str, 
        ref_table: str, 
        ref_column: str
    ):
        """標記外鍵"""
        if table in self.tables and column in self.tables[table].columns:
            col = self.tables[table].columns[column]
            col.is_foreign_key = True
            col.references_table = ref_table
            col.references_column = ref_column
    
    def infer_additional_types(self):
        """根據欄位命名慣例推斷額外的型別"""
        for table in self.tables.values():
            for col in table.columns.values():
                if col.data_type == "Unknown":
                    col.data_type, col.java_type = self._infer_type_from_name(col.name)
    
    def _infer_type_from_name(self, column_name: str) -> tuple[str, str]:
        """根據欄位名稱推斷型別"""
        name_lower = column_name.lower()
        
        # ID 欄位
        if name_lower.endswith("id"):
            return "BIGINT", "Long"
        
        # 日期欄位
        if any(suffix in name_lower for suffix in ["date", "time", "at", "createdat", "updatedat"]):
            return "DATETIME", "LocalDateTime"
        
        # 金額欄位
        if any(suffix in name_lower for suffix in ["amount", "price", "cost", "total", "balance"]):
            return "DECIMAL(18,4)", "BigDecimal"
        
        # 數量欄位
        if any(suffix in name_lower for suffix in ["count", "quantity", "qty", "number", "num"]):
            return "INT", "Integer"
        
        # 布林欄位
        if any(prefix in name_lower for prefix in ["is", "has", "can", "should", "active", "enabled"]):
            return "BIT", "Boolean"
        
        # 預設為字串
        return "VARCHAR(255)", "String"
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "tables": {name: table.to_dict() for name, table in self.tables.items()},
            "summary": {
                "total_tables": len(self.tables),
                "total_columns": sum(len(t.columns) for t in self.tables.values()),
            }
        }
    
    def export_json(self, filepath: str):
        """匯出為 JSON 檔案"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    def generate_mermaid_erd(self) -> str:
        """生成 Mermaid ER 圖"""
        lines = ["erDiagram"]
        
        # 先輸出表格和欄位
        for table_name, table in self.tables.items():
            lines.append(f"    {table_name} {{")
            for col_name, col in table.columns.items():
                pk = "PK" if col.is_primary_key else ""
                fk = "FK" if col.is_foreign_key else ""
                key_marker = f" {pk}{fk}".strip()
                sql_type = col.data_type.split("(")[0]  # 移除長度標記
                lines.append(f"        {sql_type} {col_name}{key_marker}")
            lines.append("    }")
        
        # 輸出關聯
        for table_name, table in self.tables.items():
            for col_name, col in table.columns.items():
                if col.is_foreign_key and col.references_table:
                    lines.append(f"    {col.references_table} ||--o{{ {table_name} : has")
        
        return "\n".join(lines)
    
    def generate_java_entities(self) -> Dict[str, str]:
        """生成 Java Entity 類別程式碼"""
        entities = {}
        
        for table_name, table in self.tables.items():
            entity_code = self._generate_entity_class(table_name, table)
            entities[table_name] = entity_code
        
        return entities
    
    def _generate_entity_class(self, table_name: str, table: InferredTable) -> str:
        """生成單一 Entity 類別"""
        class_name = self._to_pascal_case(table_name)
        
        lines = [
            "package com.example.domain.entity;",
            "",
            "import jakarta.persistence.*;",
            "import java.time.LocalDateTime;",
            "import java.math.BigDecimal;",
            "",
            "@Entity",
            f"@Table(name = \"{table_name}\")",
            f"public class {class_name} {{",
            "",
        ]
        
        # 欄位
        for col_name, col in table.columns.items():
            field_name = self._to_camel_case(col_name)
            
            # 註解
            if col.is_primary_key:
                lines.append("    @Id")
                lines.append("    @GeneratedValue(strategy = GenerationType.IDENTITY)")
            
            if col.is_foreign_key:
                ref_class = self._to_pascal_case(col.references_table or "")
                lines.append(f"    @ManyToOne(fetch = FetchType.LAZY)")
                lines.append(f"    @JoinColumn(name = \"{col_name}\")")
                lines.append(f"    private {ref_class} {self._to_camel_case(col.references_table or '')}Ref;")
                lines.append("")
                continue
            
            lines.append(f"    @Column(name = \"{col_name}\")")
            lines.append(f"    private {col.java_type} {field_name};")
            lines.append("")
        
        # Getter/Setter
        lines.append("    // Getters and Setters")
        for col_name, col in table.columns.items():
            if col.is_foreign_key:
                continue
            field_name = self._to_camel_case(col_name)
            pascal_name = self._to_pascal_case(col_name)
            
            lines.append(f"    public {col.java_type} get{pascal_name}() {{ return {field_name}; }}")
            lines.append(f"    public void set{pascal_name}({col.java_type} {field_name}) {{ this.{field_name} = {field_name}; }}")
            lines.append("")
        
        lines.append("}")
        
        return "\n".join(lines)
    
    def _to_pascal_case(self, name: str) -> str:
        """轉換為 PascalCase"""
        # 處理 snake_case 或 單字
        words = name.replace("_", " ").split()
        return "".join(word.capitalize() for word in words)
    
    def _to_camel_case(self, name: str) -> str:
        """轉換為 camelCase"""
        pascal = self._to_pascal_case(name)
        return pascal[0].lower() + pascal[1:] if pascal else ""
