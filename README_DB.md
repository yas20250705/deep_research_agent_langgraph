# データベース永続化機能

## 概要

PostgreSQLを使用して会話履歴とリサーチ履歴を永続化する機能です。

## セットアップ

### 1. PostgreSQLのインストール

PostgreSQLをインストールし、データベースを作成します。

```bash
# PostgreSQLのインストール（例: Ubuntu）
sudo apt-get install postgresql postgresql-contrib

# PostgreSQLに接続
sudo -u postgres psql

# データベースとユーザーを作成
CREATE DATABASE research_agent;
CREATE USER research_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE research_agent TO research_user;
\q
```

### 2. 環境変数の設定

`.env`ファイルまたは環境変数に以下を設定します：

```env
# データベース設定
DATABASE_URL=postgresql://research_user:your_password@localhost:5432/research_agent
ENABLE_DB_PERSISTENCE=true

# OpenAI設定（LLMタイトル生成用）
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o
```

### 3. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 4. データベースの初期化

データベーステーブルを作成します：

```python
from src.db import init_db

init_db()
```

または、GUIアプリケーションを起動すると自動的に初期化されます。

## データベーススキーマ

### conversations テーブル

会話履歴を保存します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | Integer | 主キー |
| conversation_id | String(255) | 会話ID（UUID） |
| title | String(255) | 会話タイトル |
| created_at | DateTime | 作成日時 |
| updated_at | DateTime | 更新日時 |

### messages テーブル

メッセージを保存します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | Integer | 主キー |
| conversation_id | String(255) | 会話ID（外部キー） |
| role | String(50) | ロール（"user" or "assistant"） |
| content | Text | メッセージ内容 |
| created_at | DateTime | 作成日時 |

### research_history テーブル

リサーチ履歴を保存します。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | Integer | 主キー |
| research_id | String(255) | リサーチID（UUID） |
| theme | Text | 調査テーマ |
| title | String(255) | タイトル |
| status | String(50) | ステータス |
| created_at | DateTime | 作成日時 |
| updated_at | DateTime | 更新日時 |
| completed_at | DateTime | 完了日時 |
| metadata_json | JSON | メタデータ（統計情報等） |

## 使用方法

### GUIアプリケーションでの使用

1. 環境変数を設定します
2. GUIアプリケーションを起動します：

```bash
streamlit run examples/api_usage_with_chat_gui.py
```

3. サイドバーの「🔄 DBから履歴を読み込み」ボタンでデータベースから履歴を読み込めます

### プログラムでの使用

```python
from src.db import (
    get_db_session,
    create_conversation,
    add_message,
    get_messages,
    save_research_history
)

# 会話を作成
db_gen = get_db_session()
db = next(db_gen)
try:
    conversation = create_conversation(db, "conversation-123", "タイトル")
    add_message(db, "conversation-123", "user", "こんにちは")
    add_message(db, "conversation-123", "assistant", "こんにちは！")
finally:
    db.close()

# メッセージを取得
db_gen = get_db_session()
db = next(db_gen)
try:
    messages = get_messages(db, "conversation-123")
    for msg in messages:
        print(f"{msg.role}: {msg.content}")
finally:
    db.close()
```

## LLMタイトル生成機能

リサーチ完了時に、OpenAI APIを使用してタイトルを自動生成します。

### 設定

GUIのサイドバーで「タイトルを自動生成」チェックボックスを有効にします。

### 動作

1. リサーチが完了すると、レポート内容を分析
2. OpenAI APIを使用してタイトルを生成
3. データベースとセッション状態の両方に保存

### フォールバック

LLMタイトル生成に失敗した場合、テーマから簡単なタイトルを生成します。

## トラブルシューティング

### データベース接続エラー

- `DATABASE_URL`が正しく設定されているか確認
- PostgreSQLが起動しているか確認
- データベースとユーザーが作成されているか確認

### テーブルが作成されない

- `ENABLE_DB_PERSISTENCE=true`が設定されているか確認
- `init_db()`が呼び出されているか確認

### LLMタイトル生成エラー

- `OPENAI_API_KEY`が設定されているか確認
- APIキーが有効か確認
- エラー時はフォールバック機能が動作します

## 注意事項

- データベース永続化はオプション機能です。`ENABLE_DB_PERSISTENCE=false`の場合は動作しません
- データベース接続エラーが発生しても、GUIアプリケーションは動作します（警告が表示されます）
- 大量のデータを扱う場合は、適切なインデックスを追加することを推奨します

