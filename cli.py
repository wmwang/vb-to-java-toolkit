#!/usr/bin/env python3
"""
VB to Java Migration Toolkit - CLI 命令列工具

核心命令：
    python cli.py discover ./legacy-vb        # AI 分析依賴，建議遷移順序
    python cli.py understand ./legacy-vb      # AI 解說業務邏輯
    python cli.py analyze ./legacy-vb         # 靜態分析
"""

import sys
import asyncio
import os
from pathlib import Path
from typing import Optional
import argparse

from dotenv import load_dotenv
load_dotenv()

from src.parsers import VBScanner, VBParser
from src.extractors import SQLExtractor, SchemaInferrer, BusinessLogicExtractor
from src.analyzer import VBProjectAnalyzer
from src.migration import DependencyAnalyzer, MigrationAdvisor
from src.llm import LLMClient, LLMConfig, BusinessLogicExplainer


def discover_modules(project_path: Path) -> list[str]:
    """自動發現專案中的模組目錄"""
    vb_extensions = {".cls", ".bas", ".frm"}
    modules = set()
    
    for vb_file in project_path.rglob("*"):
        if vb_file.suffix.lower() in vb_extensions:
            relative = vb_file.relative_to(project_path)
            if len(relative.parts) > 1:
                modules.add(relative.parts[0])
    
    return sorted(modules)


def analyze_by_module(project_path: str, output_dir: str):
    """按模組分批分析"""
    root = Path(project_path)
    output = Path(output_dir)
    
    print("🔍 掃描專案結構...")
    modules = discover_modules(root)
    
    if not modules:
        print("   未發現子模組，將整體分析")
        analyzer = VBProjectAnalyzer(project_path)
        analyzer.analyze()
        analyzer.export_results(str(output))
        analyzer.print_summary()
        return
    
    print(f"   發現 {len(modules)} 個模組: {', '.join(modules)}")
    print()
    
    for i, module_name in enumerate(modules, 1):
        module_path = root / module_name
        module_output = output / module_name
        
        print(f"📁 [{i}/{len(modules)}] 分析模組: {module_name}")
        print("-" * 50)
        
        try:
            analyzer = VBProjectAnalyzer(str(module_path))
            analyzer.analyze()
            analyzer.export_results(str(module_output))
            
            stats = analyzer.analysis_results.get("file_statistics", {})
            rules = analyzer.analysis_results.get("business_rules", {})
            print(f"   ✅ 完成：{stats.get('total_files', 0)} 檔案, {rules.get('total_rules', 0)} 條規則")
        except Exception as e:
            print(f"   ❌ 錯誤: {e}")
        
        print()
    
    print("=" * 50)
    print(f"✅ 全部完成！輸出目錄: {output}")


def analyze_by_batch(project_path: str, output_dir: str, batch_size: int = 50):
    """按檔案數量分批分析"""
    root = Path(project_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    
    print("🔍 掃描所有 VB 檔案...")
    scanner = VBScanner(project_path)
    all_files = scanner.scan()
    
    total_files = len(all_files)
    print(f"   找到 {total_files} 個 VB 檔案")
    print()
    
    if total_files == 0:
        print("❌ 沒有找到 VB 檔案")
        return
    
    # 初始化工具
    parser = VBParser()
    sql_extractor = SQLExtractor()
    schema_inferrer = SchemaInferrer()
    ble = BusinessLogicExtractor()
    
    # 分批處理
    total_batches = (total_files + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, total_files)
        batch = all_files[start_idx:end_idx]
        
        print(f"📦 批次 {batch_num + 1}/{total_batches}: 處理檔案 {start_idx + 1} ~ {end_idx}")
        
        for vb_file in batch:
            # 解析
            parser.parse(vb_file)
            
            # 萃取
            if vb_file.module:
                for func in vb_file.module.functions:
                    sql_extractor.extract_from_code(
                        func.body,
                        source_file=vb_file.filename,
                        source_function=func.name,
                    )
                    ble.extract_from_function(
                        func.name,
                        func.body,
                        source_file=vb_file.filename,
                    )
        
        print(f"   ✅ 完成 {len(batch)} 個檔案")
    
    # Schema 推斷
    print("\n🗄️ 推斷 Schema...")
    schema_inferrer.process_sql_extractor_results(sql_extractor)
    schema_inferrer.infer_additional_types()
    
    # 輸出結果
    print("📄 匯出結果...")
    
    # Schema
    schema_inferrer.export_json(str(output / "inferred_schema.json"))
    
    # ER 圖
    with open(output / "entity_diagram.mermaid", "w", encoding="utf-8") as f:
        f.write(schema_inferrer.generate_mermaid_erd())
    
    # 業務規則
    with open(output / "business_rules.md", "w", encoding="utf-8") as f:
        f.write("# 業務規則\n\n")
        for rule in ble.rules:
            f.write(ble.generate_decision_table_markdown(rule))
            f.write("\n---\n\n")
    
    # 摘要
    print()
    print("=" * 50)
    print("📊 分析摘要")
    print("=" * 50)
    print(f"📁 總檔案數: {total_files}")
    print(f"🗄️ 識別表格: {len(sql_extractor.tables)}")
    print(f"💼 業務規則: {len(ble.rules)}")
    print(f"📂 輸出目錄: {output}")
    print()
    print("✅ 分析完成！")


def analyze_full(project_path: str, output_dir: str):
    """完整分析（不分批）"""
    analyzer = VBProjectAnalyzer(project_path)
    analyzer.analyze()
    analyzer.export_results(output_dir)
    analyzer.print_summary()


def discover_dependencies(project_path: str, output_dir: str):
    """
    [AI] 探索專案依賴關係並建議遷移順序
    """
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("🔍 VB Legacy Analyzer - Discover")
    print("=" * 60)
    print()
    
    # Step 1: 分析依賴關係
    analyzer = DependencyAnalyzer(project_path)
    graph = analyzer.analyze()
    
    # 匯出依賴圖
    analyzer.export_json(str(output / "dependency_graph.json"))
    analyzer.export_mermaid(str(output / "dependency_graph.mermaid"))
    print(f"📄 匯出依賴圖: {output}")
    print()
    
    # Step 2: AI 分析並建議遷移順序
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ 未設定 OPENAI_API_KEY，跳過 AI 分析")
        print("   請在 .env 檔案中設定 OPENAI_API_KEY")
        return
    
    print("🤖 AI 正在分析依賴關係...")
    print("-" * 40)
    
    config = LLMConfig(
        api_key=api_key,
        base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
        model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        debug=True,
    )
    llm_client = LLMClient(config)
    advisor = MigrationAdvisor(llm_client)
    
    # 執行 AI 分析
    async def run_analysis():
        def on_chunk(chunk: str):
            print(chunk, end="", flush=True)
        
        advice = await advisor.analyze_and_advise(graph, on_chunk=on_chunk)
        return advice
    
    advice = asyncio.run(run_analysis())
    print()
    print("-" * 40)
    
    # 儲存 AI 建議
    with open(output / "migration_advice.md", "w", encoding="utf-8") as f:
        f.write("# AI 遷移建議\n\n")
        f.write(advice.analysis)
    
    print(f"\n📄 AI 建議已儲存: {output / 'migration_advice.md'}")
    print(f"\n✅ Discover 完成！")


def understand_module(project_path: str, output_dir: str, module_filter: Optional[str] = None):
    """
    [AI] 深入理解業務邏輯
    """
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("🧠 VB Legacy Analyzer - Understand")
    print("=" * 60)
    print()
    
    # Step 1: 分析專案
    analyzer = VBProjectAnalyzer(project_path)
    analyzer.analyze()
    
    # 取得業務規則
    rules = analyzer.ble.rules
    
    if module_filter:
        rules = [r for r in rules if module_filter.lower() in r.source_file.lower()]
    
    if not rules:
        print("❌ 沒有找到業務規則")
        return
    
    print(f"📋 找到 {len(rules)} 條業務規則")
    print()
    
    # Step 2: AI 解說
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ 未設定 OPENAI_API_KEY，跳過 AI 分析")
        return
    
    print("🤖 AI 正在解說業務邏輯...")
    print("-" * 40)
    
    config = LLMConfig(
        api_key=api_key,
        base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
        model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        debug=True,
    )
    llm_client = LLMClient(config)
    explainer = BusinessLogicExplainer(llm_client)
    
    async def run_explain():
        def on_progress(current: int, total: int, name: str):
            print(f"\n[{current}/{total}] 解說: {name}")
            print("-" * 30)
        
        results = await explainer.explain_rules_batch(rules, on_progress=on_progress)
        return results
    
    asyncio.run(run_explain())
    print()
    print("-" * 40)
    
    # 儲存解說
    markdown = explainer.export_explanations_markdown()
    with open(output / "business_rules_explained.md", "w", encoding="utf-8") as f:
        f.write(markdown)
    
    print(f"\n📄 解說已儲存: {output / 'business_rules_explained.md'}")
    print(f"\n✅ Understand 完成！")


def main():
    parser = argparse.ArgumentParser(
        description="VB to Java Migration Toolkit - AI 輔助遷移工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
核心命令（AI 驅動）:
  python cli.py discover ./legacy-vb     # AI 分析依賴，建議遷移順序
  python cli.py understand ./legacy-vb   # AI 解說業務邏輯

輔助命令:
  python cli.py analyze ./legacy-vb      # 靜態分析（不調用 AI）
  python cli.py scan ./legacy-vb         # 僅掃描專案結構
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # analyze 命令
    analyze_parser = subparsers.add_parser("analyze", help="分析 VB 專案")
    analyze_parser.add_argument("project_path", help="VB 專案路徑")
    analyze_parser.add_argument(
        "-o", "--output",
        default="./output",
        help="輸出目錄（預設: ./output）"
    )
    analyze_parser.add_argument(
        "--by-module",
        action="store_true",
        help="按子目錄（模組）分批分析"
    )
    analyze_parser.add_argument(
        "--batch-size",
        type=int,
        default=0,
        help="按檔案數量分批（指定每批檔案數）"
    )
    
    # scan 命令
    scan_parser = subparsers.add_parser("scan", help="僅掃描專案結構")
    scan_parser.add_argument("project_path", help="VB 專案路徑")
    
    # discover 命令 [AI]
    discover_parser = subparsers.add_parser("discover", help="[AI] 分析依賴，建議遷移順序")
    discover_parser.add_argument("project_path", help="VB 專案路徑")
    discover_parser.add_argument("-o", "--output", default="./output", help="輸出目錄")
    
    # understand 命令 [AI]
    understand_parser = subparsers.add_parser("understand", help="[AI] 解說業務邏輯")
    understand_parser.add_argument("project_path", help="VB 專案路徑")
    understand_parser.add_argument("-o", "--output", default="./output", help="輸出目錄")
    understand_parser.add_argument("--module", help="僅分析包含此關鍵字的模組")
    
    args = parser.parse_args()
    
    if args.command == "analyze":
        project = Path(args.project_path)
        if not project.exists():
            print(f"❌ 路徑不存在: {project}")
            return 1
        
        print("=" * 60)
        print("🚀 VB to Java Migration Toolkit")
        print("=" * 60)
        print()
        
        if args.by_module:
            analyze_by_module(args.project_path, args.output)
        elif args.batch_size > 0:
            analyze_by_batch(args.project_path, args.output, args.batch_size)
        else:
            analyze_full(args.project_path, args.output)
        
        return 0
    
    elif args.command == "scan":
        project = Path(args.project_path)
        if not project.exists():
            print(f"❌ 路徑不存在: {project}")
            return 1
        
        print("🔍 掃描專案...")
        scanner = VBScanner(args.project_path)
        files = scanner.scan()
        stats = scanner.get_statistics(files)
        
        print(f"\n📊 掃描結果:")
        print(f"   總檔案數: {stats['total_files']}")
        print(f"   類別模組 (.cls): {stats['by_type']['class']}")
        print(f"   標準模組 (.bas): {stats['by_type']['module']}")
        print(f"   表單模組 (.frm): {stats['by_type']['form']}")
        print(f"   總行數: {stats['total_lines']}")
        
        modules = discover_modules(project)
        if modules:
            print(f"\n📁 發現模組目錄:")
            for m in modules:
                print(f"   - {m}")
        
        return 0
    
    elif args.command == "discover":
        project = Path(args.project_path)
        if not project.exists():
            print(f"❌ 路徑不存在: {project}")
            return 1
        discover_dependencies(args.project_path, args.output)
        return 0
    
    elif args.command == "understand":
        project = Path(args.project_path)
        if not project.exists():
            print(f"❌ 路徑不存在: {project}")
            return 1
        understand_module(args.project_path, args.output, args.module)
        return 0
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
