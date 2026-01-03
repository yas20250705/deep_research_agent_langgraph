"""
APIサーバー起動スクリプト

プロジェクトルートから実行することで、正しくモジュールをインポートできます。
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# .envファイルを読み込む
try:
    from dotenv import load_dotenv
    # プロジェクトルートの.envファイルを読み込む
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f".envファイルを読み込みました: {env_path}")
    else:
        # 親ディレクトリの.envファイルも確認
        parent_env = project_root.parent / ".env"
        if parent_env.exists():
            load_dotenv(parent_env)
            print(f".envファイルを読み込みました: {parent_env}")
        else:
            print("警告: .envファイルが見つかりません")
except ImportError:
    print("警告: python-dotenvがインストールされていません。.envファイルを読み込めません。")

# uvicornをインポートして起動
if __name__ == "__main__":
    import uvicorn
    
    # 環境変数の確認
    if not os.getenv("OPENAI_API_KEY"):
        print("警告: OPENAI_API_KEY環境変数が設定されていません")
    else:
        print("OPENAI_API_KEY: 設定済み")
    
    if not os.getenv("TAVILY_API_KEY"):
        print("警告: TAVILY_API_KEY環境変数が設定されていません")
    else:
        print("TAVILY_API_KEY: 設定済み")
    
    print("=" * 60)
    print("APIサーバーを起動しています...")
    print(f"プロジェクトルート: {project_root}")
    print("=" * 60)
    print("\n以下のURLでアクセスできます:")
    print("  - APIドキュメント: http://localhost:8000/docs")
    print("  - ヘルスチェック: http://localhost:8000/health")
    print("\n停止するには Ctrl+C を押してください")
    print("=" * 60)
    print()
    
    # uvicornを起動
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(project_root / "src")],
        log_level="info"
    )

