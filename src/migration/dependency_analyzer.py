"""
依賴分析器 - 分析 VB 模組間的依賴關係

功能：
1. 掃描 VB 檔案間的呼叫關係
2. 建立依賴圖
3. 識別模組邊界
4. 輸出 Mermaid 圖表
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from collections import defaultdict

from ..parsers import VBScanner, VBParser


@dataclass
class ModuleDependency:
    """模組依賴資訊"""
    name: str                          # 模組名稱
    file_path: str                     # 檔案路徑
    module_type: str                   # class/module/form
    calls_to: Set[str] = field(default_factory=set)      # 呼叫的其他模組
    called_by: Set[str] = field(default_factory=set)     # 被哪些模組呼叫
    functions: List[str] = field(default_factory=list)   # 包含的函數
    external_refs: Set[str] = field(default_factory=set) # 外部參考（COM/DLL）


@dataclass
class DependencyGraph:
    """依賴圖"""
    modules: Dict[str, ModuleDependency] = field(default_factory=dict)
    edges: List[tuple] = field(default_factory=list)  # (from, to, call_type)
    
    def get_root_modules(self) -> List[str]:
        """取得根模組（沒有被其他模組呼叫的）"""
        all_modules = set(self.modules.keys())
        called_modules = set()
        for module in self.modules.values():
            called_modules.update(module.calls_to)
        return list(all_modules - called_modules)
    
    def get_leaf_modules(self) -> List[str]:
        """取得葉模組（沒有呼叫其他模組的）"""
        return [
            name for name, module in self.modules.items()
            if not module.calls_to
        ]
    
    def get_complexity_score(self, module_name: str) -> int:
        """計算模組複雜度分數"""
        if module_name not in self.modules:
            return 0
        module = self.modules[module_name]
        return (
            len(module.calls_to) * 2 +
            len(module.called_by) * 3 +
            len(module.functions) +
            len(module.external_refs) * 5
        )
    
    def to_dict(self) -> Dict:
        """轉換為字典格式"""
        return {
            "modules": {
                name: {
                    "name": m.name,
                    "file_path": m.file_path,
                    "module_type": m.module_type,
                    "calls_to": list(m.calls_to),
                    "called_by": list(m.called_by),
                    "functions": m.functions,
                    "external_refs": list(m.external_refs),
                    "complexity_score": self.get_complexity_score(name),
                }
                for name, m in self.modules.items()
            },
            "edges": self.edges,
            "statistics": {
                "total_modules": len(self.modules),
                "total_edges": len(self.edges),
                "root_modules": self.get_root_modules(),
                "leaf_modules": self.get_leaf_modules(),
            }
        }
    
    def to_mermaid(self) -> str:
        """生成 Mermaid 流程圖"""
        lines = ["graph TD"]
        
        # 節點樣式
        for name, module in self.modules.items():
            safe_name = name.replace(" ", "_").replace("-", "_")
            if module.module_type == "form":
                lines.append(f"    {safe_name}[📝 {name}]")
            elif module.module_type == "class":
                lines.append(f"    {safe_name}[📦 {name}]")
            else:
                lines.append(f"    {safe_name}[📄 {name}]")
        
        # 邊
        for from_mod, to_mod, _ in self.edges:
            safe_from = from_mod.replace(" ", "_").replace("-", "_")
            safe_to = to_mod.replace(" ", "_").replace("-", "_")
            lines.append(f"    {safe_from} --> {safe_to}")
        
        return "\n".join(lines)


class DependencyAnalyzer:
    """依賴分析器"""
    
    # VB 呼叫模式
    CALL_PATTERNS = [
        r'\b([A-Z][a-zA-Z0-9_]+)\s*\.\s*([A-Z][a-zA-Z0-9_]+)\s*\(',  # Module.Function()
        r'\bCall\s+([A-Z][a-zA-Z0-9_]+)\s*\(',                        # Call Function()
        r'\bNew\s+([A-Z][a-zA-Z0-9_]+)',                              # New ClassName
        r'\bCreateObject\s*\(\s*"([^"]+)"',                            # CreateObject("...")
    ]
    
    def __init__(self, project_path: str):
        """
        初始化依賴分析器
        
        Args:
            project_path: VB 專案路徑
        """
        self.project_path = Path(project_path)
        self.scanner = VBScanner(project_path)
        self.parser = VBParser()
        self.graph = DependencyGraph()
        
        # 模組名稱對應
        self._module_map: Dict[str, str] = {}  # function_name -> module_name
    
    def analyze(self) -> DependencyGraph:
        """
        執行依賴分析
        
        Returns:
            依賴圖
        """
        print("🔍 掃描 VB 檔案...")
        vb_files = self.scanner.scan()
        print(f"   找到 {len(vb_files)} 個檔案")
        
        # Phase 1: 解析所有檔案，建立模組清單
        print("📝 解析模組結構...")
        for vb_file in vb_files:
            self.parser.parse(vb_file)
            if vb_file.module:
                module_name = vb_file.module.name
                module_dep = ModuleDependency(
                    name=module_name,
                    file_path=vb_file.filepath,
                    module_type=vb_file.module.file_type.value,
                    functions=[f.name for f in vb_file.module.functions],
                )
                self.graph.modules[module_name] = module_dep
                
                # 建立函數對應表
                for func in vb_file.module.functions:
                    self._module_map[func.name] = module_name
        
        # Phase 2: 分析呼叫關係
        print("🔗 分析依賴關係...")
        for vb_file in vb_files:
            if vb_file.module:
                self._analyze_calls(vb_file)
        
        # Phase 3: 識別外部參考
        print("📦 識別外部參考...")
        for vb_file in vb_files:
            if vb_file.module:
                self._analyze_external_refs(vb_file)
        
        print(f"✅ 分析完成：{len(self.graph.modules)} 模組，{len(self.graph.edges)} 依賴關係")
        return self.graph
    
    def _analyze_calls(self, vb_file) -> None:
        """分析檔案中的呼叫關係"""
        if not vb_file.module:
            return
        
        current_module = vb_file.module.name
        
        for func in vb_file.module.functions:
            code = func.body
            
            # 模式 1: Module.Function()
            for match in re.finditer(r'\b([A-Z][a-zA-Z0-9_]+)\s*\.\s*([A-Z][a-zA-Z0-9_]+)\s*\(', code):
                target_module = match.group(1)
                if target_module in self.graph.modules and target_module != current_module:
                    self._add_edge(current_module, target_module, "method_call")
            
            # 模式 2: 直接呼叫其他模組的函數
            for func_name, owner_module in self._module_map.items():
                if owner_module != current_module:
                    # 檢查是否呼叫此函數
                    pattern = rf'\b{re.escape(func_name)}\s*\('
                    if re.search(pattern, code):
                        self._add_edge(current_module, owner_module, "function_call")
            
            # 模式 3: New ClassName
            for match in re.finditer(r'\bNew\s+([A-Z][a-zA-Z0-9_]+)', code):
                target_class = match.group(1)
                if target_class in self.graph.modules and target_class != current_module:
                    self._add_edge(current_module, target_class, "instantiation")
    
    def _analyze_external_refs(self, vb_file) -> None:
        """分析外部參考（COM/DLL）"""
        if not vb_file.module:
            return
        
        module_name = vb_file.module.name
        
        for func in vb_file.module.functions:
            code = func.body
            
            # CreateObject
            for match in re.finditer(r'CreateObject\s*\(\s*"([^"]+)"', code):
                ref = match.group(1)
                self.graph.modules[module_name].external_refs.add(ref)
            
            # 常見的 VB 外部物件
            external_patterns = [
                r'\bADODB\.', r'\bScripting\.', r'\bMSXML2?\.',
                r'\bExcel\.', r'\bWord\.', r'\bOutlook\.',
            ]
            for pattern in external_patterns:
                if re.search(pattern, code):
                    ref = pattern.replace(r'\b', '').replace(r'\.', '')
                    self.graph.modules[module_name].external_refs.add(ref)
    
    def _add_edge(self, from_module: str, to_module: str, call_type: str) -> None:
        """新增依賴邊"""
        if from_module not in self.graph.modules or to_module not in self.graph.modules:
            return
        
        edge = (from_module, to_module, call_type)
        if edge not in self.graph.edges:
            self.graph.edges.append(edge)
            self.graph.modules[from_module].calls_to.add(to_module)
            self.graph.modules[to_module].called_by.add(from_module)
    
    def export_json(self, output_path: str) -> None:
        """匯出 JSON 格式"""
        import json
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.graph.to_dict(), f, indent=2, ensure_ascii=False)
    
    def export_mermaid(self, output_path: str) -> None:
        """匯出 Mermaid 格式"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.graph.to_mermaid())
