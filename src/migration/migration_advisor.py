"""
AI 遷移顧問 - 使用 LLM 分析依賴並建議遷移策略

功能：
1. 分析依賴圖，識別遷移風險
2. 建議最佳遷移順序
3. 識別潛在的問題模組
"""

from typing import Optional, Callable, List
from dataclasses import dataclass

from ..llm import LLMClient
from .dependency_analyzer import DependencyGraph


# System Prompt
MIGRATION_ADVISOR_SYSTEM_PROMPT = """你是一位資深的軟體架構師，專門負責大型遺留系統的現代化遷移。

你的任務是分析 VB 專案的模組依賴關係，並提供遷移建議。

請遵循以下原則：
1. 優先遷移獨立模組（沒有依賴其他模組的葉節點）
2. 避免先遷移被大量依賴的核心模組
3. 識別技術債高的模組（外部依賴多、複雜度高）
4. 考慮業務價值與風險的平衡

請使用繁體中文回答，格式如下：

## 專案概覽
[簡述專案結構與規模]

## 遷移順序建議
按優先順序列出模組，說明理由：
1. **模組名稱** - 遷移理由
2. ...

## 風險模組
[列出需要特別注意的高風險模組及原因]

## 遷移策略建議
[整體遷移策略建議，例如分批次、並行開發等]"""


@dataclass
class MigrationAdvice:
    """遷移建議結果"""
    analysis: str                    # AI 分析結果
    suggested_order: List[str]       # 建議的遷移順序
    high_risk_modules: List[str]     # 高風險模組


class MigrationAdvisor:
    """AI 遷移顧問"""
    
    def __init__(self, llm_client: LLMClient):
        """
        初始化遷移顧問
        
        Args:
            llm_client: LLM Client 實例
        """
        self.llm_client = llm_client
    
    async def analyze_and_advise(
        self,
        graph: DependencyGraph,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> MigrationAdvice:
        """
        分析依賴圖並提供遷移建議
        
        Args:
            graph: 依賴圖
            on_chunk: 可選的 streaming 回調
            
        Returns:
            遷移建議
        """
        # 組裝 User Prompt
        user_prompt = self._build_prompt(graph)
        
        # 呼叫 LLM（SSE Streaming）
        analysis = await self.llm_client.generate(
            user_prompt=user_prompt,
            system_prompt=MIGRATION_ADVISOR_SYSTEM_PROMPT,
            on_chunk=on_chunk,
        )
        
        # 解析建議的遷移順序（從 AI 回應中提取）
        suggested_order = self._extract_suggested_order(analysis, graph)
        
        # 識別高風險模組
        high_risk = self._identify_high_risk(graph)
        
        return MigrationAdvice(
            analysis=analysis,
            suggested_order=suggested_order,
            high_risk_modules=high_risk,
        )
    
    def _build_prompt(self, graph: DependencyGraph) -> str:
        """組裝分析請求"""
        stats = graph.to_dict()["statistics"]
        
        lines = [
            "請分析以下 VB 專案的模組依賴關係，並提供遷移建議。",
            "",
            "## 專案統計",
            f"- 總模組數：{stats['total_modules']}",
            f"- 總依賴關係：{stats['total_edges']}",
            f"- 根模組（入口點）：{', '.join(stats['root_modules']) or '無'}",
            f"- 葉模組（無依賴）：{', '.join(stats['leaf_modules']) or '無'}",
            "",
            "## 模組清單",
        ]
        
        # 列出每個模組的資訊
        for name, module in graph.modules.items():
            complexity = graph.get_complexity_score(name)
            lines.append(f"### {name}")
            lines.append(f"- 類型：{module.module_type}")
            lines.append(f"- 函數數量：{len(module.functions)}")
            lines.append(f"- 呼叫模組：{', '.join(module.calls_to) or '無'}")
            lines.append(f"- 被呼叫：{', '.join(module.called_by) or '無'}")
            lines.append(f"- 外部依賴：{', '.join(module.external_refs) or '無'}")
            lines.append(f"- 複雜度分數：{complexity}")
            lines.append("")
        
        # 依賴關係
        lines.append("## 依賴關係")
        if graph.edges:
            for from_mod, to_mod, call_type in graph.edges:
                lines.append(f"- {from_mod} → {to_mod} ({call_type})")
        else:
            lines.append("- 無模組間依賴")
        
        return "\n".join(lines)
    
    def _extract_suggested_order(self, analysis: str, graph: DependencyGraph) -> List[str]:
        """從 AI 回應中提取建議的遷移順序"""
        # 簡單實作：按複雜度排序作為備選
        modules = list(graph.modules.keys())
        modules.sort(key=lambda m: graph.get_complexity_score(m))
        return modules
    
    def _identify_high_risk(self, graph: DependencyGraph) -> List[str]:
        """識別高風險模組"""
        high_risk = []
        for name, module in graph.modules.items():
            # 高風險條件：被很多模組依賴 或 有很多外部依賴
            if len(module.called_by) >= 3 or len(module.external_refs) >= 2:
                high_risk.append(name)
        return high_risk
