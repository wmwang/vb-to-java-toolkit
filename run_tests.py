#!/usr/bin/env python3
"""
執行所有測試
解決 Windows 未將 pytest 加入 PATH 的問題
"""

import sys
import subprocess
from pathlib import Path

def main():
    """執行 pytest"""
    print("=" * 60)
    print("🧪 正在執行所有測試...")
    print("=" * 60)
    
    # 使用當前 Python 解析器執行 pytest模組
    # 這比直接呼叫 'pytest' 更安全，因為只要能執行此腳本，就一定有 Python
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
    
    try:
        # 執行測試命令
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n⚠️ 測試已中斷")
        return 130
    except Exception as e:
        print(f"\n❌ 執行測試時發生錯誤: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
