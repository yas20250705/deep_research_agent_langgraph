# API仕様書：LangGraph搭載 自律型リサーチエージェント

## 1. ドキュメント情報

- **文書名**: API仕様書
- **バージョン**: 1.1
- **作成日**: 2024-12-27
- **最終更新日**: 2025-02-01
- **対象システム**: LangGraph搭載 自律型リサーチエージェント
- **APIバージョン**: v1
- **ベースURL（ローカル）**: `http://localhost:8000`（`python run_api_server.py` または `start_api_server.bat` / `uvicorn src.api.main:app --reload` で起動）
- **参照文書**: 要求定義書、基本設計書、詳細設計書

---

## 2. API概要

### 2.1 目的

本APIは、LangGraphを活用した自律型リサーチエージェントの機能を提供します。ユーザーがテーマを入力すると、Web上の情報を収集・分析し、高品質なレポートを生成します。

### 2.2 技術スタック

- **フレームワーク**: FastAPI
- **言語**: Python 3.10以上
- **データ形式**: JSON
- **認証**: API Key（将来実装）

### 2.3 エンドポイント一覧

| メソッド | エンドポイント | 説明 | 認証 |
|---------|--------------|------|------|
| POST | `/research` | リサーチを開始 | 不要 |
| GET | `/research/{research_id}` | リサーチ結果を取得 | 不要 |
| GET | `/research/{research_id}/status` | リサーチの状態を取得 | 不要 |
| POST | `/research/{research_id}/resume` | 中断されたリサーチを再開 | 不要 |
| DELETE | `/research/{research_id}` | リサーチを削除 | 不要 |
| GET | `/health` | ヘルスチェック | 不要 |

---

## 3. エンドポイント詳細

### 3.1 POST /research

リサーチを開始します。

#### リクエスト

**URL**: `/research`

**メソッド**: `POST`

**Content-Type**: `application/json`

**リクエストボディ**:

```json
{
  "theme": "LangGraphについて調査してください",
  "max_iterations": 5,
  "enable_human_intervention": false,
  "checkpointer_type": "memory"
}
```

**リクエストスキーマ**:

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|----------|------|
| theme | string | はい | - | 調査テーマ |
| max_iterations | integer | いいえ | 5 | 最大イテレーション数（1-10） |
| enable_human_intervention | boolean | いいえ | false | 人間介入を有効化するか |
| checkpointer_type | string | いいえ | "memory" | チェックポイントタイプ（"memory" or "redis"） |

**リクエスト例**:

```bash
curl -X POST "https://api.example.com/v1/research" \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "LangGraphについて調査してください",
    "max_iterations": 5
  }'
```

#### レスポンス

**ステータスコード**: `201 Created`

**レスポンスボディ**:

```json
{
  "research_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "started",
  "message": "リサーチを開始しました",
  "created_at": "2024-12-27T10:00:00Z",
  "estimated_completion_time": "2024-12-27T10:05:00Z"
}
```

**レスポンススキーマ**:

| フィールド | 型 | 説明 |
|-----------|-----|------|
| research_id | string (UUID) | リサーチID |
| status | string | ステータス（"started", "processing", "completed", "failed", "interrupted"） |
| message | string | メッセージ |
| created_at | string (ISO 8601) | 作成日時 |
| estimated_completion_time | string (ISO 8601) | 推定完了時刻 |

**エラーレスポンス**:

**400 Bad Request**:

```json
{
  "error": "validation_error",
  "message": "リクエストの検証に失敗しました",
  "details": [
    {
      "field": "theme",
      "message": "themeは必須です"
    }
  ]
}
```

**500 Internal Server Error**:

```json
{
  "error": "internal_error",
  "message": "サーバー内部エラーが発生しました",
  "research_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### 3.2 GET /research/{research_id}

リサーチ結果を取得します。

#### リクエスト

**URL**: `/research/{research_id}`

**メソッド**: `GET`

**パスパラメータ**:

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| research_id | string (UUID) | リサーチID |

**リクエスト例**:

```bash
curl -X GET "https://api.example.com/v1/research/550e8400-e29b-41d4-a716-446655440000"
```

#### レスポンス

**ステータスコード**: `200 OK`

**レスポンスボディ**:

```json
{
  "research_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "theme": "LangGraphについて調査してください",
  "plan": {
    "theme": "LangGraphについて調査してください",
    "investigation_points": [
      "LangGraphの基本概念と特徴",
      "LangGraphの用途とユースケース",
      "LangGraphとLangChainの関係"
    ],
    "search_queries": [
      "LangGraph framework",
      "LangGraph use cases",
      "LangGraph vs LangChain"
    ],
    "plan_text": "LangGraphについて包括的に調査します...",
    "created_at": "2024-12-27T10:00:00Z"
  },
  "report": {
    "draft": "# LangGraphについて\n\n## Executive Summary\n...",
    "sources": [
      {
        "title": "LangGraph Documentation",
        "summary": "LangGraphの公式ドキュメント...",
        "url": "https://langchain-ai.github.io/langgraph/",
        "source": "tavily",
        "relevance_score": 0.95
      }
    ]
  },
  "statistics": {
    "iterations": 3,
    "sources_collected": 15,
    "processing_time_seconds": 120
  },
  "created_at": "2024-12-27T10:00:00Z",
  "completed_at": "2024-12-27T10:02:00Z"
}
```

**レスポンススキーマ**:

| フィールド | 型 | 説明 |
|-----------|-----|------|
| research_id | string (UUID) | リサーチID |
| status | string | ステータス |
| theme | string | 調査テーマ |
| plan | ResearchPlan | 調査計画 |
| report | ResearchReport | レポート（statusが"completed"の場合のみ） |
| statistics | ResearchStatistics | 統計情報 |
| created_at | string (ISO 8601) | 作成日時 |
| completed_at | string (ISO 8601) | 完了日時（完了時のみ） |

**エラーレスポンス**:

**404 Not Found**:

```json
{
  "error": "not_found",
  "message": "指定されたリサーチIDが見つかりません"
}
```

**422 Unprocessable Entity** (処理中の場合):

```json
{
  "error": "processing",
  "message": "リサーチはまだ処理中です",
  "status": "processing",
  "progress": {
    "current_iteration": 2,
    "max_iterations": 5,
    "current_node": "researcher"
  }
}
```

---

### 3.3 GET /research/{research_id}/status

リサーチの状態を取得します。

#### リクエスト

**URL**: `/research/{research_id}/status`

**メソッド**: `GET`

**パスパラメータ**:

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| research_id | string (UUID) | リサーチID |

**リクエスト例**:

```bash
curl -X GET "https://api.example.com/v1/research/550e8400-e29b-41d4-a716-446655440000/status"
```

#### レスポンス

**ステータスコード**: `200 OK`

**レスポンスボディ**:

```json
{
  "research_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": {
    "current_iteration": 2,
    "max_iterations": 5,
    "current_node": "researcher",
    "nodes_completed": ["supervisor", "researcher"],
    "nodes_remaining": ["writer", "reviewer"]
  },
  "statistics": {
    "sources_collected": 8,
    "processing_time_seconds": 45
  },
  "last_updated": "2024-12-27T10:01:00Z"
}
```

**レスポンススキーマ**:

| フィールド | 型 | 説明 |
|-----------|-----|------|
| research_id | string (UUID) | リサーチID |
| status | string | ステータス |
| progress | ProgressInfo | 進捗情報 |
| statistics | ResearchStatistics | 統計情報 |
| last_updated | string (ISO 8601) | 最終更新日時 |

**ProgressInfoスキーマ**:

| フィールド | 型 | 説明 |
|-----------|-----|------|
| current_iteration | integer | 現在のイテレーション |
| max_iterations | integer | 最大イテレーション数 |
| current_node | string | 現在実行中のノード |
| nodes_completed | array[string] | 完了したノードのリスト |
| nodes_remaining | array[string] | 残りのノードのリスト |

---

### 3.4 POST /research/{research_id}/resume

中断されたリサーチを再開します（Human-in-the-Loop使用時）。

#### リクエスト

**URL**: `/research/{research_id}/resume`

**メソッド**: `POST`

**Content-Type**: `application/json`

**リクエストボディ**:

```json
{
  "human_input": "この方向で進めてください"
}
```

**リクエストスキーマ**:

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| human_input | string | はい | 人間からの入力 |

**リクエスト例**:

```bash
curl -X POST "https://api.example.com/v1/research/550e8400-e29b-41d4-a716-446655440000/resume" \
  -H "Content-Type: application/json" \
  -d '{
    "human_input": "この方向で進めてください"
  }'
```

#### レスポンス

**ステータスコード**: `200 OK`

**レスポンスボディ**:

```json
{
  "research_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "リサーチを再開しました"
}
```

**エラーレスポンス**:

**400 Bad Request** (中断されていない場合):

```json
{
  "error": "not_interrupted",
  "message": "リサーチは中断されていません"
}
```

**404 Not Found**:

```json
{
  "error": "not_found",
  "message": "指定されたリサーチIDが見つかりません"
}
```

---

### 3.5 DELETE /research/{research_id}

リサーチを削除します。

#### リクエスト

**URL**: `/research/{research_id}`

**メソッド**: `DELETE`

**パスパラメータ**:

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| research_id | string (UUID) | リサーチID |

**リクエスト例**:

```bash
curl -X DELETE "https://api.example.com/v1/research/550e8400-e29b-41d4-a716-446655440000"
```

#### レスポンス

**ステータスコード**: `200 OK`

**レスポンスボディ**:

```json
{
  "message": "リサーチが削除されました",
  "research_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**エラーレスポンス**:

**404 Not Found**:

```json
{
  "error": "not_found",
  "message": "指定されたリサーチIDが見つかりません"
}
```

---

### 3.6 GET /health

ヘルスチェックエンドポイントです。

#### リクエスト

**URL**: `/health`

**メソッド**: `GET`

**リクエスト例**:

```bash
curl -X GET "https://api.example.com/v1/health"
```

#### レスポンス

**ステータスコード**: `200 OK`

**レスポンスボディ**:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-12-27T10:00:00Z",
  "services": {
    "openai": "healthy",
    "tavily": "healthy",
    "redis": "healthy"
  }
}
```

**レスポンススキーマ**:

| フィールド | 型 | 説明 |
|-----------|-----|------|
| status | string | ステータス（"healthy" or "unhealthy"） |
| version | string | APIバージョン |
| timestamp | string (ISO 8601) | チェック時刻 |
| services | object | 各サービスの状態 |

---

## 4. データモデル

### 4.1 ResearchPlan

調査計画モデル。

```json
{
  "theme": "LangGraphについて調査してください",
  "investigation_points": [
    "LangGraphの基本概念と特徴",
    "LangGraphの用途とユースケース"
  ],
  "search_queries": [
    "LangGraph framework",
    "LangGraph use cases"
  ],
  "plan_text": "LangGraphについて包括的に調査します...",
  "created_at": "2024-12-27T10:00:00Z"
}
```

**スキーマ**:

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| theme | string | はい | 調査テーマ |
| investigation_points | array[string] | はい | 調査観点のリスト |
| search_queries | array[string] | はい | 検索クエリのリスト |
| plan_text | string | はい | 計画テキスト |
| created_at | string (ISO 8601) | はい | 作成日時 |

### 4.2 SearchResult

検索結果モデル。

```json
{
  "title": "LangGraph Documentation",
  "summary": "LangGraphの公式ドキュメント...",
  "url": "https://langchain-ai.github.io/langgraph/",
  "source": "tavily",
  "published_date": "2024-01-01",
  "relevance_score": 0.95
}
```

**スキーマ**:

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| title | string | はい | タイトル |
| summary | string | はい | 要約 |
| url | string | はい | URL |
| source | string | はい | 情報源（"tavily" or "arxiv"） |
| published_date | string | いいえ | 公開日 |
| relevance_score | number | いいえ | 関連性スコア（0-1） |

### 4.3 ResearchReport

リサーチレポートモデル。

```json
{
  "theme": "LangGraphについて調査してください",
  "executive_summary": "LangGraphは...",
  "key_findings": [
    "発見1",
    "発見2"
  ],
  "detailed_analysis": "詳細な分析...",
  "constraints_and_challenges": "制約と課題...",
  "sources": [
    {
      "title": "LangGraph Documentation",
      "summary": "...",
      "url": "https://...",
      "source": "tavily",
      "relevance_score": 0.95
    }
  ],
  "generated_at": "2024-12-27T10:02:00Z"
}
```

**スキーマ**:

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| theme | string | はい | 調査テーマ |
| executive_summary | string | はい | エグゼクティブサマリー |
| key_findings | array[string] | はい | 主要発見のリスト |
| detailed_analysis | string | はい | 詳細分析 |
| constraints_and_challenges | string | いいえ | 制約と課題 |
| sources | array[SearchResult] | はい | 参考ソース一覧 |
| generated_at | string (ISO 8601) | はい | 生成日時 |

### 4.4 ResearchStatistics

統計情報モデル。

```json
{
  "iterations": 3,
  "sources_collected": 15,
  "processing_time_seconds": 120
}
```

**スキーマ**:

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| iterations | integer | はい | イテレーション回数 |
| sources_collected | integer | はい | 収集されたソース数 |
| processing_time_seconds | integer | はい | 処理時間（秒） |

---

## 5. エラーレスポンス

### 5.1 エラー形式

すべてのエラーレスポンスは以下の形式です：

```json
{
  "error": "error_code",
  "message": "エラーメッセージ",
  "details": {}
}
```

### 5.2 エラーコード一覧

| エラーコード | HTTPステータス | 説明 |
|------------|--------------|------|
| validation_error | 400 | リクエストの検証エラー |
| not_found | 404 | リソースが見つからない |
| processing | 422 | リサーチが処理中 |
| not_interrupted | 400 | リサーチが中断されていない |
| internal_error | 500 | サーバー内部エラー |
| service_unavailable | 503 | サービスが利用できない |

### 5.3 エラーレスポンス例

**400 Bad Request**:

```json
{
  "error": "validation_error",
  "message": "リクエストの検証に失敗しました",
  "details": {
    "field": "theme",
    "message": "themeは必須です"
  }
}
```

**404 Not Found**:

```json
{
  "error": "not_found",
  "message": "指定されたリサーチIDが見つかりません",
  "details": {
    "research_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**500 Internal Server Error**:

```json
{
  "error": "internal_error",
  "message": "サーバー内部エラーが発生しました",
  "details": {
    "research_id": "550e8400-e29b-41d4-a716-446655440000",
    "error_id": "ERR-2024-12-27-001"
  }
}
```

---

## 6. 認証・認可

### 6.1 認証方式

現在は認証不要ですが、将来的にAPI Key認証を実装予定です。

### 6.2 API Key認証（将来実装）

**ヘッダー**:

```
X-API-Key: your-api-key-here
```

**エラーレスポンス** (401 Unauthorized):

```json
{
  "error": "unauthorized",
  "message": "APIキーが無効です"
}
```

---

## 7. レート制限

### 7.1 制限値

| エンドポイント | 制限 | 期間 |
|--------------|------|------|
| POST /research | 10リクエスト | 1分 |
| GET /research/{id} | 60リクエスト | 1分 |
| GET /research/{id}/status | 120リクエスト | 1分 |
| POST /research/{id}/resume | 10リクエスト | 1分 |

### 7.2 レート制限エラー

**429 Too Many Requests**:

```json
{
  "error": "rate_limit_exceeded",
  "message": "レート制限を超えました",
  "details": {
    "limit": 10,
    "remaining": 0,
    "reset_at": "2024-12-27T10:01:00Z"
  }
}
```

**レスポンスヘッダー**:

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1703672460
```

---

## 8. Webhook（将来実装）

### 8.1 概要

リサーチの完了時にWebhookを送信します。

### 8.2 Webhookペイロード

```json
{
  "event": "research.completed",
  "research_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-12-27T10:02:00Z",
  "data": {
    "status": "completed",
    "theme": "LangGraphについて調査してください"
  }
}
```

---

## 9. 使用例

### 9.1 基本的な使用フロー

```bash
# 1. リサーチを開始
RESPONSE=$(curl -X POST "https://api.example.com/v1/research" \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "LangGraphについて調査してください"
  }')

RESEARCH_ID=$(echo $RESPONSE | jq -r '.research_id')

# 2. 状態を確認（ポーリング）
while true; do
  STATUS=$(curl -s "https://api.example.com/v1/research/$RESEARCH_ID/status" | jq -r '.status')
  
  if [ "$STATUS" = "completed" ]; then
    break
  elif [ "$STATUS" = "failed" ]; then
    echo "リサーチが失敗しました"
    exit 1
  fi
  
  sleep 5
done

# 3. 結果を取得
curl -X GET "https://api.example.com/v1/research/$RESEARCH_ID" | jq '.report.draft'
```

### 9.2 Python使用例

```python
import requests
import time

BASE_URL = "https://api.example.com/v1"

# リサーチを開始
response = requests.post(
    f"{BASE_URL}/research",
    json={
        "theme": "LangGraphについて調査してください",
        "max_iterations": 5
    }
)
research_id = response.json()["research_id"]

# 完了を待つ
while True:
    status_response = requests.get(
        f"{BASE_URL}/research/{research_id}/status"
    )
    status = status_response.json()["status"]
    
    if status == "completed":
        break
    elif status == "failed":
        raise Exception("リサーチが失敗しました")
    
    time.sleep(5)

# 結果を取得
result_response = requests.get(
    f"{BASE_URL}/research/{research_id}"
)
report = result_response.json()["report"]
print(report["draft"])
```

---

## 10. 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| 1.0 | 2024-12-27 | 初版作成 |
| 1.1 | 2025-02-01 | ベースURL・起動方法追記、ドキュメント情報・変更履歴更新 |

---

## 付録A: OpenAPI仕様（Swagger）

OpenAPI 3.0仕様は `/docs` エンドポイントで確認できます。

---

## 付録B: 参考資料

- FastAPI Documentation
- OpenAPI Specification
- JSON Schema

