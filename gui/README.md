# HTML/CSS/JavaScript GUI

Streamlitアプリケーションを置き換える、Vanilla JavaScriptで実装されたWeb GUIです。

## ファイル構成

```
gui/
├── index.html          # メインHTMLファイル
├── css/
│   └── style.css      # スタイルシート
├── js/
│   ├── app.js         # メインアプリケーション
│   ├── api.js         # API通信モジュール
│   └── ui.js          # UI操作モジュール
└── README.md          # このファイル
```

## 使用方法

### 1. APIサーバーの起動

まず、FastAPIサーバーを起動してください：

```bash
python run_api_server.py
```

または

```bash
uvicorn src.api.main:app --reload
```

APIサーバーは `http://localhost:8000` で起動します。

### 2. GUIの起動

#### 方法1: ローカルファイルとして開く

`gui/index.html` をブラウザで直接開きます。

**注意**: 一部のブラウザでは、ローカルファイルからのAPIリクエストがCORSポリシーによりブロックされる場合があります。その場合は、方法2を使用してください。

#### 方法2: ローカルWebサーバーで起動

Pythonの簡易HTTPサーバーを使用：

```bash
cd gui
python -m http.server 8080
```

その後、ブラウザで `http://localhost:8080` にアクセスします。

#### 方法3: FastAPIで静的ファイルを配信

FastAPIアプリケーションに静的ファイル配信機能を追加する場合：

```python
from fastapi.staticfiles import StaticFiles

app.mount("/gui", StaticFiles(directory="gui", html=True), name="gui")
```

その後、`http://localhost:8000/gui/` にアクセスします。

## 機能

### チャットインターフェース
- メッセージの送信・表示
- Markdownレンダリング
- コードブロックのシンタックスハイライト

### リサーチ機能
- リサーチの開始
- リアルタイム進捗表示
- 停止機能
- 再生成機能

### 結果表示
- レポート表示（Markdown形式）
- 統計情報（イテレーション数、ソース数、処理時間）
- 参照ソース一覧
- レポートのダウンロード（Markdown形式）

### 履歴管理
- リサーチ履歴の保存（ローカルストレージ）
- 履歴からの結果再表示
- 履歴の削除

### 設定
- 最大イテレーション数の設定
- 人間介入の有効化/無効化
- API URLの設定

## 設定

設定はブラウザのローカルストレージに保存されます：

- `apiUrl`: APIサーバーのURL（デフォルト: `http://localhost:8000`）
- `maxIterations`: 最大イテレーション数（デフォルト: 5）
- `enableHumanIntervention`: 人間介入の有効化（デフォルト: false）
- `researchHistory`: リサーチ履歴（最大50件）

## トラブルシューティング

### APIサーバーに接続できない

#### 症状
- 接続ステータスが「❌ APIサーバーに接続できません」と表示される
- リサーチを開始できない

#### 解決方法

1. **APIサーバーが起動しているか確認**
   ```bash
   python run_api_server.py
   ```
   または
   ```bash
   start_api_server.bat
   ```

2. **ローカルファイルから開いている場合（CORSエラー）**
   
   `file://`プロトコルで直接HTMLファイルを開いている場合、ブラウザのセキュリティポリシーによりAPIサーバーへのリクエストがブロックされます。
   
   **解決方法**: ローカルWebサーバーを使用してください
   ```bash
   cd gui
   python -m http.server 8080
   ```
   その後、ブラウザで `http://localhost:8080` にアクセスします。
   
   **注意**: `deep_research_agent_langgraph.bat` を実行すると、自動的にローカルWebサーバーが起動します。

3. **API URLの設定を確認**
   - サイドバーの「API URL」設定が `http://localhost:8000` になっているか確認
   - 別のポートを使用している場合は、設定を変更してください

4. **ヘルスチェックで接続を確認**
   - サイドバーの「🏥 ヘルスチェック」ボタンをクリック
   - 接続ステータスをクリックすると、詳細なエラーメッセージが表示されます

5. **ブラウザのコンソールでエラーを確認**
   - ブラウザの開発者ツール（F12）を開く
   - Consoleタブでエラーメッセージを確認

### CORSエラーが発生する

FastAPIのCORS設定は既に適切に設定されています（`src/api/middleware.py`）。それでもエラーが発生する場合は、ローカルWebサーバーを使用してください（上記参照）。

### 履歴が表示されない

ブラウザのローカルストレージが無効になっている可能性があります。ブラウザの設定を確認してください。

## 技術スタック

- **HTML5**: 構造
- **CSS3**: スタイリング（Flexbox/Grid）
- **Vanilla JavaScript (ES6+)**: ロジック
- **marked.js**: Markdownパーサー（CDN）
- **highlight.js**: コードシンタックスハイライト（CDN）

## ブラウザ対応

以下のモダンブラウザで動作します：

- Chrome (最新版)
- Firefox (最新版)
- Safari (最新版)
- Edge (最新版)

## ライセンス

MIT License
