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
- **GUI**: HTML/JavaScript版（API連携）、Streamlit版（スクリプト用意時）

## 技術スタック

- **フレームワーク**: LangGraph（LangChain 1.x）
- **LLM**: OpenAI（GPT-4o等）、Google Gemini（オプション）、Mock（開発・テスト用）
- **検索API**: Tavily Search API
- **言語**: Python 3.10以上

## セットアップ

### 1. 仮想環境の作成

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate
```

### 2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 3. 環境変数の設定

`.env_example` をコピーして `.env` を作成し、APIキーなどを設定してください。

```bash
# Windows (PowerShell)
copy .env_example .env

# Linux / macOS
cp .env_example .env
```

`.env` を編集して以下を設定します。

- **必須**: `OPENAI_API_KEY`（OpenAI利用時）、`TAVILY_API_KEY`（検索利用時）
- **オプション**: `GEMINI_API_KEY`（Gemini利用時）、`LLM_PROVIDER`（`openai` / `gemini` / `mock`）
- ダウンロードするレポートMD・参照ソースPDFの保存先をサーバー側に残す場合は `DOWNLOAD_SAVE_DIR` を設定（履歴の永続化先 `data/researches` とは別です）

## 実行

### 基本的な使用例（直接実行）

```bash
python examples/example_usage.py
```

### APIサーバーの起動

#### Windows: バッチファイル（推奨）

```batch
start_api_server.bat
```

#### Pythonスクリプト

```bash
python run_api_server.py
```

#### uvicorn で直接起動

```bash
# プロジェクトルートから実行
uvicorn src.api.main:app --reload
```

プロジェクトルート（`deep_research_agent_langgraph/`）で実行してください。起動後、ブラウザで `http://localhost:8000/docs` にアクセスするとAPIドキュメントを確認できます。

### GUIの起動

#### HTML GUI（推奨）

APIサーバーを起動したうえで、次のいずれかで利用できます。

- **Windows**: `start_html_gui.bat` を実行（ブラウザで `gui/index.html` を開く）
- **手動**: ブラウザで `gui/index.html` を開く（ファイルプロトコル）
- **簡易Webサーバー**: `cd gui` のあと `python -m http.server 8080` で `http://localhost:8080` にアクセス

詳細は `gui/README.md` を参照してください。

#### 一括起動（Windows）

APIサーバーとHTML GUI用の簡易サーバーをまとめて起動する場合:

```batch
deep_research_agent_langgraph.bat
```

APIサーバーが起動し、`gui` 用のローカルサーバー（ポート8080）が立ち上がり、ブラウザで `http://localhost:8080` が開きます。

#### Streamlit GUI（オプション）

`examples/api_usage_with_chat_gui.py` を用意している場合は、次のいずれかで起動できます。

- **Windows**: `start_gui.bat`
- **コマンド**: `python run_gui.py`

いずれもAPIサーバーを先に起動してください。

## プロジェクト構造

```text
deep_research_agent_langgraph/
├── src/
│   ├── api/            # FastAPI ルート・ミドルウェア・ストリーミング
│   ├── config/         # 設定（pydantic-settings）
│   ├── db/              # DB（SQLAlchemy / CRUD）
│   ├── graph/           # LangGraph グラフ・ステート・エッジ
│   ├── nodes/           # ノード（Supervisor, Researcher, Writer, Reviewer）
│   ├── prompts/         # プロンプトテンプレート
│   ├── schemas/         # データモデル（Pydantic）
│   ├── tools/           # ツール（検索・スクレイピング）
│   └── utils/           # ユーティリティ（LLM、PDF、リトライ等）
├── gui/                 # HTML/CSS/JavaScript GUI
├── examples/            # 使用例（example_usage.py 等）
├── tests/               # テスト
├── spec_doc/            # 仕様・設計ドキュメント
├── run_api_server.py    # APIサーバー起動
├── run_gui.py           # Streamlit GUI 起動
├── start_api_server.bat
├── start_html_gui.bat
└── deep_research_agent_langgraph.bat  # API + HTML GUI 一括起動
```

## APIエンドポイント（概要）

- `POST /research` - リサーチ開始
- `GET /research/{id}` - リサーチ結果取得
- `GET /research/{id}/status` - ステータス取得
- `POST /research/{id}/resume` - 中断したリサーチの再開
- `DELETE /research/{id}` - リサーチ削除
- `GET /health` - ヘルスチェック

詳細は起動後の `http://localhost:8000/docs` を参照してください。

## 開発

### テストの実行

```bash
# 全テスト
pytest

# カバレッジ付き
pytest --cov=src --cov-report=html
```

E2Eテスト（実際のAPIキーを使用）:

```bash
# Windows (cmd)
set OPENAI_API_KEY=your-openai-key
set TAVILY_API_KEY=your-tavily-key

# Linux / macOS
export OPENAI_API_KEY=your-openai-key
export TAVILY_API_KEY=your-tavily-key

pytest tests/test_e2e_api.py -v
```

※E2EテストはAPIコストがかかり、実行にも時間がかかります。

### コードフォーマット・静的解析

```bash
black src tests
flake8 src tests
mypy src
ruff check src tests
```

## 関連ドキュメント

- `README_DB.md` - データベース（PostgreSQL等）の利用
- `gui/README.md` - HTML GUI の使い方
- `spec_doc/` - API仕様書、GUI要件定義書、設計書など
- `取り扱い手順書.md` - 運用・トラブルシュート

## ライセンス

MIT License
