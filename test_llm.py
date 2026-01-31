#!/usr/bin/env python3
"""
LLM 整合測試腳本 - 測試業務邏輯解說和 Java 轉譯功能

使用方式：
    export OPENAI_API_KEY=your_api_key
    poetry run python test_llm.py
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent))

from src.analyzer import VBProjectAnalyzer
from src.llm import create_llm_client, BusinessLogicExplainer, JavaCodeTranslator, JavaLayer


async def main():
    """執行 LLM 整合測試"""
    print("=" * 60)
    print("🤖 VB to Java Toolkit - LLM 整合測試")
    print("=" * 60)
    print()
    
    # 檢查 API Key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ 錯誤：請設定 OPENAI_API_KEY 環境變數")
        print("   export OPENAI_API_KEY=your_api_key")
        return 1
    
    # 範例專案路徑
    sample_project = Path(__file__).parent / "examples" / "sample-erp"
    
    if not sample_project.exists():
        print(f"❌ 找不到範例專案: {sample_project}")
        return 1
    
    # 1. 分析專案
    print("📝 步驟 1: 分析 VB 專案...")
    analyzer = VBProjectAnalyzer(str(sample_project))
    analyzer.analyze(recursive=True)
    
    # 2. 建立 LLM Client
    print("\n🔗 步驟 2: 建立 LLM Client (OpenAI + SSE Streaming)...")
    llm_client = create_llm_client(
        api_key=api_key,
        model="gpt-4o-mini",
    )
    
    # 3. 測試業務邏輯解說
    print("\n💼 步驟 3: 測試業務邏輯解說...")
    if analyzer.ble.rules:
        explainer = BusinessLogicExplainer(llm_client)
        
        # 只測試第一條規則（避免消耗太多 API 額度）
        rule = analyzer.ble.rules[0]
        print(f"   分析規則: {rule.name}")
        print("   " + "-" * 40)
        
        # Streaming 輸出
        def on_chunk(chunk: str):
            print(chunk, end="", flush=True)
        
        explanation = await explainer.explain_rule(rule, on_chunk=on_chunk)
        print("\n")
    else:
        print("   ⚠️ 沒有找到業務規則")
    
    # 4. 測試 Java 轉譯
    print("\n☕ 步驟 4: 測試 Java 程式碼轉譯...")
    translator = JavaCodeTranslator(llm_client)
    
    # 找一個有業務邏輯的函數來轉譯
    for vb_file in analyzer.vb_files:
        if vb_file.module:
            for func in vb_file.module.functions:
                if "Calculate" in func.name or "Discount" in func.name:
                    print(f"   轉譯函數: {func.name}")
                    print("   " + "-" * 40)
                    
                    def on_chunk(chunk: str):
                        print(chunk, end="", flush=True)
                    
                    result = await translator.translate_function(
                        vb_code=func.body,
                        function_name=func.name,
                        target_layer=JavaLayer.USE_CASE,
                        on_chunk=on_chunk,
                    )
                    print("\n")
                    break
            else:
                continue
            break
    
    # 5. 輸出 Token 使用量
    print("\n📊 Token 使用統計:")
    print(f"   估計使用: {llm_client.get_token_usage()} tokens")
    
    print("\n" + "=" * 60)
    print("✅ LLM 整合測試完成！")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
