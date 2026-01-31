"""VB 檔案掃描器 - 掃描目錄並識別 VB 檔案"""

import os
from pathlib import Path
from typing import List, Optional, Generator
import chardet

from .models import VBFile, VBFileType


class VBScanner:
    """VB 專案檔案掃描器"""
    
    # 支援的 VB 檔案副檔名
    SUPPORTED_EXTENSIONS = {
        ".cls": VBFileType.CLASS,
        ".bas": VBFileType.MODULE,
        ".frm": VBFileType.FORM,
        ".vb": VBFileType.CLASS,  # VB.NET 也支援
    }
    
    def __init__(self, root_path: str):
        """
        初始化掃描器
        
        Args:
            root_path: VB 專案根目錄路徑
        """
        self.root_path = Path(root_path)
        if not self.root_path.exists():
            raise FileNotFoundError(f"路徑不存在: {root_path}")
    
    def scan(self, recursive: bool = True) -> List[VBFile]:
        """
        掃描目錄中的所有 VB 檔案
        
        Args:
            recursive: 是否遞迴掃描子目錄
            
        Returns:
            VB 檔案列表
        """
        vb_files = []
        
        for vb_file in self._scan_files(recursive):
            vb_files.append(vb_file)
        
        return vb_files
    
    def _scan_files(self, recursive: bool) -> Generator[VBFile, None, None]:
        """產生器：逐一掃描檔案"""
        pattern = "**/*" if recursive else "*"
        
        for filepath in self.root_path.glob(pattern):
            if not filepath.is_file():
                continue
            
            ext = filepath.suffix.lower()
            if ext not in self.SUPPORTED_EXTENSIONS:
                continue
            
            file_type = self.SUPPORTED_EXTENSIONS[ext]
            
            # 讀取檔案內容並自動偵測編碼
            content, encoding = self._read_file(filepath)
            
            yield VBFile(
                filepath=str(filepath),
                filename=filepath.name,
                file_type=file_type,
                raw_content=content,
                encoding=encoding,
            )
    
    def _read_file(self, filepath: Path) -> tuple[str, str]:
        """
        讀取檔案並自動偵測編碼
        
        Args:
            filepath: 檔案路徑
            
        Returns:
            (檔案內容, 編碼)
        """
        # 先嘗試讀取原始位元組來偵測編碼
        try:
            with open(filepath, "rb") as f:
                raw_bytes = f.read()
            
            # 使用 chardet 偵測編碼
            detected = chardet.detect(raw_bytes)
            encoding = detected.get("encoding", "utf-8") or "utf-8"
            
            # 嘗試用偵測到的編碼解碼
            try:
                content = raw_bytes.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                # 如果失敗，嘗試常見編碼
                for fallback_encoding in ["utf-8", "big5", "gb2312", "cp1252", "latin-1"]:
                    try:
                        content = raw_bytes.decode(fallback_encoding)
                        encoding = fallback_encoding
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    # 最後手段：忽略錯誤
                    content = raw_bytes.decode("utf-8", errors="replace")
                    encoding = "utf-8"
            
            return content, encoding
            
        except Exception as e:
            return f"[讀取錯誤: {str(e)}]", "unknown"
    
    def get_statistics(self, vb_files: Optional[List[VBFile]] = None) -> dict:
        """
        取得掃描統計資訊
        
        Args:
            vb_files: VB 檔案列表（如果為 None，會重新掃描）
            
        Returns:
            統計資訊字典
        """
        if vb_files is None:
            vb_files = self.scan()
        
        stats = {
            "total_files": len(vb_files),
            "by_type": {
                "class": 0,
                "module": 0,
                "form": 0,
            },
            "total_lines": 0,
            "encodings": {},
        }
        
        for vb_file in vb_files:
            # 按類型統計
            if vb_file.file_type == VBFileType.CLASS:
                stats["by_type"]["class"] += 1
            elif vb_file.file_type == VBFileType.MODULE:
                stats["by_type"]["module"] += 1
            elif vb_file.file_type == VBFileType.FORM:
                stats["by_type"]["form"] += 1
            
            # 統計行數
            stats["total_lines"] += vb_file.raw_content.count("\n") + 1
            
            # 統計編碼
            enc = vb_file.encoding
            stats["encodings"][enc] = stats["encodings"].get(enc, 0) + 1
        
        return stats
