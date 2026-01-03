# 変更履歴

## [0.1.0] - 2024-12-27

### 追加
- フェーズ1: 基盤構築
  - プロジェクトセットアップ（requirements.txt, pyproject.toml, .gitignore, README.md）
  - データモデル実装（ResearchPlan, SearchResult, ResearchReport）
  - 設定管理実装（Settings）
  - ロギング機能実装
  - ステートスキーマ定義（ResearchState）

- フェーズ2: コア機能実装
  - プロンプトテンプレート（Supervisor, Writer, Reviewer）
  - 検索ツール（Tavily）
  - スクレイピングツール
  - Supervisorノード（計画生成・ルーティング）
  - Researcherノード（検索・情報収集）
  - Writerノード（ドラフト生成）
  - Reviewerノード（評価・フィードバック）
  - エラーハンドリング（リトライ・エラーハンドリングデコレータ）
  - グラフ構築・ルーティング

- フェーズ3: 統合・API実装
  - チェックポイント機能（MemorySaver / RedisCheckpointer対応）
  - Human-in-the-Loop機能
  - FastAPI実装（全エンドポイント）
  - APIテスト
  - E2Eテスト（実際のAPI呼び出し）
  - API使用例（example_api_usage.py）

### テスト
- データモデルテスト: 13件
- ノードテスト: 8件
- グラフテスト: 6件
- 統合テスト: 3件
- APIテスト: 8件
- E2Eテスト: 6件（実際のAPIキーが必要）
- **合計: 44件のテスト（E2Eテストは条件付き）**

## [0.3.0] - 2024-12-27

### 追加
- RedisCheckpointerの実装（langgraph.checkpoint.redisが利用可能な場合）
- E2Eテストの追加（実際のAPI呼び出しを使用）
- API使用例の追加（example_api_usage.py）
- README.mdの更新（API使用方法、E2Eテストの説明を追加）

### 改善
- チェックポイント機能のエラーハンドリングを改善
- RedisCheckpointerのフォールバック処理を改善

## [0.4.0] - 2024-12-27

### 追加
- フェーズ4: 最適化・拡張
  - セキュリティ機能（入力検証、SQLインジェクション/XSS対策、エラーメッセージのサニタイズ）
  - 並列検索機能（複数クエリの同時実行）
  - キャッシュ機能（検索結果とLLM応答のキャッシュ）
  - API認証機能（API Key認証）
  - レート制限機能（リクエスト制限）
  - ストリーミング出力（Server-Sent Events）
  - プロファイリングツール（パフォーマンス測定）
  - CORS設定
  - セキュリティヘッダーの追加

### 改善
- Researcherノードのパフォーマンス向上（並列検索）
- 検索ツールにキャッシュ機能を統合
- APIエンドポイントにセキュリティミドルウェアを追加
- エラーメッセージの情報漏洩対策
- 入力検証の強化

### 新機能
- `/research/{id}/stream` エンドポイント（進捗のストリーミング）
- プロファイリングデコレータ（`@profile_function`, `@measure_time`）
- キャッシュ統計情報の取得機能

