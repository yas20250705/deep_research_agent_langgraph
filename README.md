# LangGraph搭載 自律型リサーチエージェント

LangGraphを活用した自律型リサーチエージェントシステム。ユーザーがテーマを入力すると、Web上の情報を収集・分析し、高品質なレポートを生成します。

## 機能

- **Supervisor**: 計画立案とルーティング決定
- **Researcher**: Web検索と情報収集
- **Writer**: レポートドラフト作成
- **Reviewer**: ドラフト評価とフィードバック
- **チェックポイント機能**: 実行状態の永続化（MemorySaver / RedisCheckpointer）
- **Human-in-the-Loop**: 人間介入による制御
- **REST API**: FastAPIによるHTTP API

## 技術スタック

- **フレームワーク**: LangGraph (LangChain 1.0以上)
- **LLM**: OpenAI GPT-4o
- **検索API**: Tavily Search API
- **言語**: Python 3.10以上

## セットアップ

### 1. 仮想環境の作成

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 3. 環境変数の設定

`.env.example`をコピーして`.env`を作成し、APIキーを設定してください。

```bash
cp .env.example .env
# .envファイルを編集してAPIキーを設定
```

ダウンロードするレポートMD・参照ソースPDFの保存先をサーバー側にも残したい場合は、`.env` で `DOWNLOAD_SAVE_DIR` を設定してください（履歴の永続化先 `data/researches` とは別の設定です）。

### 4. 実行

#### 基本的な使用例（直接実行）

```bash
python examples/example_usage.py
```

#### APIサーバーの起動

##### Windows: バッチファイルを使用（推奨）

```batch
start_api_server.bat
```

##### Pythonスクリプトを使用

```bash
python run_api_server.py
```

##### uvicornを直接実行

```bash
# プロジェクトルートディレクトリから実行
uvicorn src.api.main:app --reload

# または、Pythonモジュールとして実行
python -m uvicorn src.api.main:app --reload
```

**注意**: プロジェクトルートディレクトリ（`deep_research_agent_langgraph/`）から実行してください。

APIサーバーが起動したら、ブラウザで `http://localhost:8000/docs` にアクセスしてAPIドキュメントを確認できます。

#### GUIアプリケーションの起動

##### Windows: GUIバッチファイルを使用（推奨）

```batch
start_gui.bat
```

##### GUI Pythonスクリプトを使用

```bash
python run_gui.py
```

##### Streamlitを直接実行

```bash
streamlit run examples/api_usage_with_chat_gui.py
```

**注意**:

- APIサーバーを先に起動してください
- プロジェクトルートディレクトリから実行してください

#### 一括起動（Windows）

##### すべてのサービスを一度に起動

```batch
start_all.bat
```

このバッチファイルを実行すると、以下のオプションが表示されます：

1. APIサーバーのみ起動
2. GUIアプリケーションのみ起動
3. APIサーバーとGUIアプリケーションを両方起動（推奨）
4. 終了

#### APIを使用した実行例

```bash
python examples/example_api_usage.py
```

環境変数 `API_BASE_URL` を設定することで、異なるサーバーに接続できます：

```bash
export API_BASE_URL=http://localhost:8000
python examples/example_api_usage.py
```

## プロジェクト構造

```text
deep_research_agent_langgraph/
├── src/
│   ├── graph/          # グラフ構築とステート管理
│   ├── nodes/          # 各ノードの実装
│   ├── tools/          # 外部ツール（検索、スクレイピング）
│   ├── schemas/        # データモデル
│   ├── prompts/        # プロンプトテンプレート
│   ├── utils/          # ユーティリティ関数
│   └── config/         # 設定管理
├── tests/              # テストコード
├── examples/           # 使用例
└── docs/               # ドキュメント
```

## APIエンドポイント

- `POST /research` - リサーチを開始
- `GET /research/{id}` - リサーチ結果を取得
- `GET /research/{id}/status` - リサーチのステータスを取得
- `POST /research/{id}/resume` - 中断されたリサーチを再開
- `DELETE /research/{id}` - リサーチを削除
- `GET /health` - ヘルスチェック

詳細は `http://localhost:8000/docs` のAPIドキュメントを参照してください。

## 開発

### テストの実行

#### すべてのテストを実行

```bash
pytest
```

#### カバレッジレポート付きで実行

```bash
pytest --cov=src --cov-report=html
```

#### E2Eテストの実行（実際のAPIキーが必要）

```bash
# 環境変数にAPIキーを設定
export OPENAI_API_KEY=your-openai-key
export TAVILY_API_KEY=your-tavily-key

# E2Eテストを実行
pytest tests/test_e2e_api.py -v
```

**注意**: E2Eテストは実際のAPIキーを使用するため、APIコストが発生します。テスト用のテーマとイテレーション数を設定していますが、実行には時間がかかります。

### コードフォーマット

```bash
black src tests
flake8 src tests
mypy src
```

## ライセンス

MIT License
