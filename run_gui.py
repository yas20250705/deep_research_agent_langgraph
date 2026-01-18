"""
GUIアプリケーション起動スクリプト

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
            print(f"  確認したパス:")
            print(f"    - {env_path}")
            print(f"    - {parent_env}")
except ImportError:
    print("警告: python-dotenvがインストールされていません。.envファイルを読み込めません。")

# Streamlitアプリケーションを起動
if __name__ == "__main__":
    import subprocess
    
    # GUIアプリケーションファイルのパス
    gui_file = project_root / "examples" / "api_usage_with_chat_gui.py"
    
    if not gui_file.exists():
        print(f"エラー: GUIファイルが見つかりません: {gui_file}")
        sys.exit(1)
    
    print("=" * 60)
    print("GUIアプリケーションを起動しています...")
    print(f"プロジェクトルート: {project_root}")
    print("=" * 60)
    print("\n注意: APIサーバーが起動していることを確認してください")
    print("  APIサーバーの起動: python run_api_server.py")
    print("\nブラウザが自動的に開きます")
    print("停止するには Ctrl+C を押してください")
    print("=" * 60)
    print()
    
    # Streamlitを起動（ブラウザを自動的に開く設定）
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(gui_file),
        "--server.port", "8501",
        "--server.address", "localhost",
        "--server.headless", "false",
        "--browser.serverAddress", "localhost",
        "--browser.serverPort", "8501"
    ])

