"""
FastAPI 服務單元測試
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from src.api.main import app


@pytest.fixture
def client():
    """建立測試用的 API Client"""
    return TestClient(app)


class TestAPIRoot:
    """根路徑測試"""
    
    def test_root(self, client):
        """測試根路徑"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "VB to Java Migration API"
        assert "endpoints" in data


class TestHealthCheck:
    """健康檢查測試"""
    
    def test_health(self, client):
        """測試健康檢查"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestAnalyzeEndpoint:
    """分析端點測試"""
    
    def test_analyze_invalid_path(self, client):
        """測試無效路徑"""
        response = client.post("/analyze", json={
            "project_path": "/nonexistent/path",
        })
        
        assert response.status_code == 400
        assert "不存在" in response.json()["detail"]
    
    def test_analyze_valid_path(self, client, tmp_path):
        """測試有效路徑"""
        # 建立臨時 VB 檔案
        vb_file = tmp_path / "test.cls"
        vb_file.write_text("VERSION 1.0 CLASS\nAttribute VB_Name = \"Test\"")
        
        response = client.post("/analyze", json={
            "project_path": str(tmp_path),
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"


class TestTranslateEndpoint:
    """翻譯端點測試"""
    
    def test_translate_without_api_key(self, client, monkeypatch):
        """測試無 API Key 時的錯誤處理"""
        # 確保沒有設定 API Key
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        
        response = client.post("/translate", json={
            "vb_code": "Function Test()\nEnd Function",
            "function_name": "Test",
        })
        
        # 應該返回錯誤（需要 API Key）
        assert response.status_code == 400
        assert "OPENAI_API_KEY" in response.json()["detail"]


class TestGenerateEndpoint:
    """專案生成端點測試"""
    
    def test_generate_invalid_path(self, client):
        """測試無效路徑"""
        response = client.post("/generate", json={
            "project_path": "/nonexistent/path",
            "output_dir": "/tmp/output",
        })
        
        assert response.status_code == 400
        assert "不存在" in response.json()["detail"]
    
    def test_generate_valid_path(self, client, tmp_path):
        """測試有效路徑"""
        # 建立臨時 VB 檔案
        vb_file = tmp_path / "test.cls"
        vb_file.write_text("VERSION 1.0 CLASS\nAttribute VB_Name = \"Test\"")
        
        output_dir = tmp_path / "output"
        
        response = client.post("/generate", json={
            "project_path": str(tmp_path),
            "output_dir": str(output_dir),
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data


class TestStatusEndpoint:
    """狀態查詢端點測試"""
    
    def test_status_not_found(self, client):
        """測試查詢不存在的任務"""
        response = client.get("/status/nonexistent-id")
        
        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]


class TestStreamEndpoint:
    """SSE 串流端點測試"""
    
    def test_stream_not_found(self, client):
        """測試串流不存在的任務"""
        response = client.get("/stream/nonexistent-id")
        
        assert response.status_code == 404
