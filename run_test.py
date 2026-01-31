#!/usr/bin/env python3
"""
測試腳本 - 使用 sample-erp 範例測試工具套件
"""

import sys
from pathlib import Path

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent))

from src.analyzer import analyze_project


def main():
    """執行測試分析"""
    # 範例專案路徑
    sample_project = Path(__file__).parent / "examples" / "sample-erp"
    
    if not sample_project.exists():
        print(f"❌ 找不到範例專案: {sample_project}")
        return 1
    
    # 輸出目錄
    output_dir = Path(__file__).parent / "output" / "sample-erp-analysis"
    
    print("=" * 60)
    print("🚀 VB to Java Migration Toolkit - 測試分析")
    print("=" * 60)
    print()
    
    # 執行分析
    results = analyze_project(
        project_path=str(sample_project),
        output_dir=str(output_dir),
        recursive=True,
    )
    
    print()
    print(f"📂 輸出目錄: {output_dir}")
    print()
    print("✅ 測試完成！")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
