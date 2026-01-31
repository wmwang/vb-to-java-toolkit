"""VB 專案分析主程式"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from .parsers import VBScanner, VBParser
from .extractors import SQLExtractor, SchemaInferrer, BusinessLogicExtractor


class VBProjectAnalyzer:
    """VB 專案分析器 - 整合所有工具"""
    
    def __init__(self, project_path: str):
        """
        初始化分析器
        
        Args:
            project_path: VB 專案路徑
        """
        self.project_path = Path(project_path)
        self.scanner = VBScanner(project_path)
        self.parser = VBParser()
        self.sql_extractor = SQLExtractor()
        self.schema_inferrer = SchemaInferrer()
        self.ble = BusinessLogicExtractor()
        
        # 分析結果
        self.vb_files = []
        self.analysis_results = {}
    
    def analyze(self, recursive: bool = True) -> Dict[str, Any]:
        """
        執行完整分析
        
        Args:
            recursive: 是否遞迴掃描子目錄
            
        Returns:
            分析結果
        """
        print(f"🔍 掃描專案: {self.project_path}")
        
        # 1. 掃描檔案
        self.vb_files = self.scanner.scan(recursive)
        print(f"   找到 {len(self.vb_files)} 個 VB 檔案")
        
        # 2. 解析每個檔案
        print("📝 解析程式碼...")
        for vb_file in self.vb_files:
            self.parser.parse(vb_file)
        
        # 3. 萃取 SQL 和 Schema
        print("🗄️ 萃取 SQL/Schema...")
        for vb_file in self.vb_files:
            if vb_file.module:
                for func in vb_file.module.functions:
                    # 從函數體萃取 SQL
                    self.sql_extractor.extract_from_code(
                        func.body,
                        source_file=vb_file.filename,
                        source_function=func.name,
                    )
        
        # 4. 推斷 Schema
        self.schema_inferrer.process_sql_extractor_results(self.sql_extractor)
        self.schema_inferrer.infer_additional_types()
        
        # 5. 萃取業務邏輯
        print("💼 萃取業務邏輯...")
        for vb_file in self.vb_files:
            if vb_file.module:
                for func in vb_file.module.functions:
                    self.ble.extract_from_function(
                        func.name,
                        func.body,
                        source_file=vb_file.filename,
                    )
        
        # 6. 組裝結果
        self.analysis_results = {
            "project_path": str(self.project_path),
            "file_statistics": self.scanner.get_statistics(self.vb_files),
            "modules": [
                vb_file.module.to_dict() 
                for vb_file in self.vb_files 
                if vb_file.module
            ],
            "sql_summary": self.sql_extractor.get_summary(),
            "schema": self.schema_inferrer.to_dict(),
            "business_rules": self.ble.get_summary(),
        }
        
        print("✅ 分析完成！")
        return self.analysis_results
    
    def export_results(self, output_dir: str) -> None:
        """
        匯出分析結果
        
        Args:
            output_dir: 輸出目錄
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 1. 匯出完整 JSON 報告
        with open(output_path / "analysis_report.json", "w", encoding="utf-8") as f:
            json.dump(self.analysis_results, f, indent=2, ensure_ascii=False)
        print(f"📄 匯出 JSON 報告: {output_path / 'analysis_report.json'}")
        
        # 2. 匯出 Schema JSON
        self.schema_inferrer.export_json(str(output_path / "inferred_schema.json"))
        print(f"📄 匯出 Schema: {output_path / 'inferred_schema.json'}")
        
        # 3. 匯出 Mermaid ER 圖
        erd = self.schema_inferrer.generate_mermaid_erd()
        with open(output_path / "entity_diagram.mermaid", "w", encoding="utf-8") as f:
            f.write(erd)
        print(f"📄 匯出 ER 圖: {output_path / 'entity_diagram.mermaid'}")
        
        # 4. 匯出業務規則文件
        self._export_business_rules(output_path / "business_rules.md")
        print(f"📄 匯出業務規則: {output_path / 'business_rules.md'}")
        
        # 5. 匯出 Java Entity
        entities = self.schema_inferrer.generate_java_entities()
        entities_dir = output_path / "java_entities"
        entities_dir.mkdir(exist_ok=True)
        for table_name, code in entities.items():
            class_name = self._to_pascal_case(table_name)
            with open(entities_dir / f"{class_name}.java", "w", encoding="utf-8") as f:
                f.write(code)
        print(f"📄 匯出 Java Entity: {entities_dir}")
    
    def _export_business_rules(self, filepath: Path) -> None:
        """匯出業務規則文件"""
        lines = [
            "# 業務規則文件",
            "",
            f"**專案**: {self.project_path.name}",
            "",
            "---",
            "",
        ]
        
        for rule in self.ble.rules:
            lines.append(self.ble.generate_decision_table_markdown(rule))
            lines.append("")
            lines.append("---")
            lines.append("")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    
    def _to_pascal_case(self, name: str) -> str:
        """轉換為 PascalCase"""
        words = name.replace("_", " ").split()
        return "".join(word.capitalize() for word in words)
    
    def print_summary(self) -> None:
        """列印分析摘要"""
        print("\n" + "=" * 60)
        print("📊 分析摘要")
        print("=" * 60)
        
        stats = self.analysis_results.get("file_statistics", {})
        print(f"\n📁 檔案統計:")
        print(f"   總檔案數: {stats.get('total_files', 0)}")
        print(f"   類別模組: {stats.get('by_type', {}).get('class', 0)}")
        print(f"   標準模組: {stats.get('by_type', {}).get('module', 0)}")
        print(f"   表單模組: {stats.get('by_type', {}).get('form', 0)}")
        print(f"   總行數: {stats.get('total_lines', 0)}")
        
        sql_summary = self.analysis_results.get("sql_summary", {})
        print(f"\n🗄️ SQL/Schema:")
        print(f"   識別的表格: {sql_summary.get('total_tables', 0)}")
        print(f"   識別的欄位: {sql_summary.get('total_columns', 0)}")
        
        ble_summary = self.analysis_results.get("business_rules", {})
        print(f"\n💼 業務規則:")
        print(f"   總規則數: {ble_summary.get('total_rules', 0)}")
        for rule_type, count in ble_summary.get("by_type", {}).items():
            print(f"   - {rule_type}: {count}")
        
        print("\n" + "=" * 60)


def analyze_project(
    project_path: str, 
    output_dir: Optional[str] = None,
    recursive: bool = True
) -> Dict[str, Any]:
    """
    分析 VB 專案的便捷函數
    
    Args:
        project_path: VB 專案路徑
        output_dir: 輸出目錄（可選）
        recursive: 是否遞迴掃描
        
    Returns:
        分析結果
    """
    analyzer = VBProjectAnalyzer(project_path)
    results = analyzer.analyze(recursive)
    analyzer.print_summary()
    
    if output_dir:
        analyzer.export_results(output_dir)
    
    return results
