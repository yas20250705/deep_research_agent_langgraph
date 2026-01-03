"""
APIテスト

FastAPIエンドポイントのテスト
"""

import pytest
import os
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.research_manager import research_manager

# テスト用の環境変数を設定
os.environ['OPENAI_API_KEY'] = 'test-openai-key'
os.environ['TAVILY_API_KEY'] = 'test-tavily-key'

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_env():
    """すべてのテストで環境変数を設定"""
    os.environ['OPENAI_API_KEY'] = 'test-openai-key'
    os.environ['TAVILY_API_KEY'] = 'test-tavily-key'
    yield
    # クリーンアップ: リサーチマネージャーをリセット
    research_manager.researches.clear()
    research_manager.graphs.clear()


class TestResearchAPI:
    """リサーチAPIのテスト"""
    
    def test_create_research(self):
        """リサーチ開始APIのテスト"""
        response = client.post(
            "/research",
            json={
                "theme": "テストテーマ",
                "max_iterations": 5
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "research_id" in data
        assert data["status"] == "started"
        assert "created_at" in data
    
    def test_create_research_validation_error(self):
        """バリデーションエラーのテスト"""
        response = client.post(
            "/research",
            json={
                "theme": "",  # 無効（空文字列）
                "max_iterations": 5
            }
        )
        
        assert response.status_code == 422
    
    def test_get_research_not_found(self):
        """存在しないリサーチIDのテスト"""
        response = client.get("/research/00000000-0000-0000-0000-000000000000")
        
        assert response.status_code == 404
    
    def test_get_research_status(self):
        """状態取得APIのテスト"""
        # リサーチを作成
        create_response = client.post(
            "/research",
            json={"theme": "テストテーマ"}
        )
        research_id = create_response.json()["research_id"]
        
        # 状態を取得
        response = client.get(f"/research/{research_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "research_id" in data
    
    def test_delete_research(self):
        """リサーチ削除APIのテスト"""
        # リサーチを作成
        create_response = client.post(
            "/research",
            json={"theme": "テストテーマ"}
        )
        research_id = create_response.json()["research_id"]
        
        # 削除
        response = client.delete(f"/research/{research_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "リサーチが削除されました"
        
        # 削除後は404を返す
        get_response = client.get(f"/research/{research_id}")
        assert get_response.status_code == 404


class TestHealthAPI:
    """ヘルスチェックAPIのテスト"""
    
    def test_health_check(self):
        """ヘルスチェックAPIのテスト"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data
        assert "services" in data


class TestResumeAPI:
    """再開APIのテスト"""
    
    def test_resume_research_not_found(self):
        """存在しないリサーチIDで再開を試みる"""
        response = client.post(
            "/research/00000000-0000-0000-0000-000000000000/resume",
            json={"human_input": "続けてください"}
        )
        
        assert response.status_code == 404
    
    def test_resume_research_not_interrupted(self):
        """中断されていないリサーチを再開しようとする"""
        # リサーチを作成（人間介入なし）
        create_response = client.post(
            "/research",
            json={
                "theme": "テストテーマ",
                "enable_human_intervention": False
            }
        )
        research_id = create_response.json()["research_id"]
        
        # 再開を試みる
        response = client.post(
            f"/research/{research_id}/resume",
            json={"human_input": "続けてください"}
        )
        
        # 中断されていない場合は400を返す
        assert response.status_code == 400









