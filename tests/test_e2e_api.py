"""
エンドツーエンドテスト（API）

実際のAPIエンドポイントを使用したテスト
注意: 実際のAPIキーが必要です（環境変数から読み込み）
"""

import pytest
import os
import time
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.research_manager import research_manager

# テスト用の環境変数を設定
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', 'test-openai-key')
os.environ['TAVILY_API_KEY'] = os.getenv('TAVILY_API_KEY', 'test-tavily-key')

client = TestClient(app)

# 実際のAPIキーが設定されているかチェック
REAL_API_KEYS_AVAILABLE = (
    os.getenv('OPENAI_API_KEY') != 'test-openai-key' and
    os.getenv('OPENAI_API_KEY') is not None and
    os.getenv('TAVILY_API_KEY') != 'test-tavily-key' and
    os.getenv('TAVILY_API_KEY') is not None
)


@pytest.fixture(autouse=True)
def setup_env():
    """すべてのテストで環境変数を設定"""
    yield
    # クリーンアップ: リサーチマネージャーをリセット
    research_manager.researches.clear()
    research_manager.graphs.clear()


@pytest.mark.skipif(
    not REAL_API_KEYS_AVAILABLE,
    reason="実際のAPIキーが必要です。OPENAI_API_KEYとTAVILY_API_KEYを環境変数に設定してください"
)
class TestE2EAPI:
    """エンドツーエンドAPIテスト（実際のAPI呼び出し）"""
    
    def test_create_and_get_research_status(self):
        """リサーチ作成とステータス取得のE2Eテスト"""
        # リサーチを作成
        create_response = client.post(
            "/research",
            json={
                "theme": "Pythonの基本的な使い方について",
                "max_iterations": 2,  # テスト用に少なめに設定
                "enable_human_intervention": False
            }
        )
        
        assert create_response.status_code == 201
        data = create_response.json()
        research_id = data["research_id"]
        assert data["status"] == "started"
        assert "created_at" in data
        
        # ステータスを取得（処理が完了するまで待機）
        max_wait_time = 300  # 最大5分待機
        wait_interval = 5  # 5秒ごとにチェック
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            status_response = client.get(f"/research/{research_id}/status")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            status = status_data["status"]
            
            if status in ["completed", "failed"]:
                break
            
            time.sleep(wait_interval)
            elapsed_time += wait_interval
        
        # 最終ステータスを確認
        final_status_response = client.get(f"/research/{research_id}/status")
        assert final_status_response.status_code == 200
        final_status_data = final_status_response.json()
        
        # 完了または失敗のいずれかであることを確認
        assert final_status_data["status"] in ["completed", "failed"]
        
        # 完了している場合は結果を取得
        if final_status_data["status"] == "completed":
            result_response = client.get(f"/research/{research_id}")
            assert result_response.status_code == 200
            result_data = result_response.json()
            assert result_data["status"] == "completed"
            assert "statistics" in result_data
    
    def test_research_with_human_intervention(self):
        """人間介入ありのリサーチテスト"""
        # リサーチを作成（人間介入を有効化）
        create_response = client.post(
            "/research",
            json={
                "theme": "テストテーマ",
                "max_iterations": 1,
                "enable_human_intervention": True
            }
        )
        
        assert create_response.status_code == 201
        research_id = create_response.json()["research_id"]
        
        # 少し待機してからステータスを確認
        time.sleep(2)
        
        status_response = client.get(f"/research/{research_id}/status")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        # 人間介入が有効な場合、interrupted状態になる可能性がある
        assert status_data["status"] in ["processing", "interrupted", "completed", "failed"]
    
    def test_research_validation(self):
        """リサーチリクエストのバリデーションテスト"""
        # 無効なテーマ（空文字列）
        response = client.post(
            "/research",
            json={
                "theme": "",
                "max_iterations": 5
            }
        )
        assert response.status_code == 422
        
        # 無効なmax_iterations（範囲外）
        response = client.post(
            "/research",
            json={
                "theme": "テストテーマ",
                "max_iterations": 0  # 1未満
            }
        )
        assert response.status_code == 422
        
        response = client.post(
            "/research",
            json={
                "theme": "テストテーマ",
                "max_iterations": 11  # 10超過
            }
        )
        assert response.status_code == 422
    
    def test_research_not_found(self):
        """存在しないリサーチIDのテスト"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        # ステータス取得
        response = client.get(f"/research/{fake_id}/status")
        assert response.status_code == 404
        
        # 結果取得
        response = client.get(f"/research/{fake_id}")
        assert response.status_code == 404
        
        # 削除
        response = client.delete(f"/research/{fake_id}")
        assert response.status_code == 404
    
    def test_health_check(self):
        """ヘルスチェックのテスト"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data
        assert "services" in data
    
    def test_delete_research(self):
        """リサーチ削除のE2Eテスト"""
        # リサーチを作成
        create_response = client.post(
            "/research",
            json={
                "theme": "削除テスト用テーマ",
                "max_iterations": 1
            }
        )
        
        assert create_response.status_code == 201
        research_id = create_response.json()["research_id"]
        
        # 削除
        delete_response = client.delete(f"/research/{research_id}")
        assert delete_response.status_code == 200
        
        # 削除後は404を返す
        get_response = client.get(f"/research/{research_id}")
        assert get_response.status_code == 404


@pytest.mark.skipif(
    not REAL_API_KEYS_AVAILABLE,
    reason="実際のAPIキーが必要です"
)
class TestE2EAPIPerformance:
    """パフォーマンステスト"""
    
    def test_concurrent_research_requests(self):
        """並行リクエストのテスト"""
        import concurrent.futures
        
        def create_research(index: int):
            response = client.post(
                "/research",
                json={
                    "theme": f"並行テストテーマ {index}",
                    "max_iterations": 1
                }
            )
            return response.status_code == 201
        
        # 3つの並行リクエスト
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(create_research, i) for i in range(3)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # すべて成功することを確認
        assert all(results)

