"""
API使用例: LangGraph搭載 自律型リサーチエージェント - StreamlitチャットGUI

FastAPIエンドポイントを使用したリサーチの実行例（チャットUI付き）
"""

import os
import sys
import time
import json
import requests
import uuid
import base64
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
from dotenv import load_dotenv
import streamlit as st
from io import BytesIO
import re

# Webスクレイピング用のインポート
try:
    from bs4 import BeautifulSoup
    SCRAPING_AVAILABLE = True
except ImportError:
    SCRAPING_AVAILABLE = False

# 記事抽出用のインポート
try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

# PDFテキスト抽出用のインポート
try:
    import PyPDF2
    PDF_TEXT_EXTRACTION_AVAILABLE = True
except ImportError:
    PDF_TEXT_EXTRACTION_AVAILABLE = False

# PDF生成用のインポート
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    if 'st' in globals():
        st.warning("PDF生成機能を使用するにはreportlabをインストールしてください: pip install reportlab")

# プロジェクトルートをパスに追加（インポートの前に実行）
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# データベース関連のインポート（パス追加後に実行）
DB_AVAILABLE = False
try:
    from src.db import (
        init_db,
        get_db_session,
        create_conversation,
        get_conversation,
        get_all_conversations,
        add_message,
        get_messages,
        save_research_history as db_save_research_history,
        get_all_research_history as db_get_all_research_history
    )
    from src.utils.title_generator import generate_title_with_llm, generate_title_fallback
    DB_AVAILABLE = True
except ImportError as e:
    # 警告は後で表示（stが利用可能になってから）
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"データベースモジュールのインポートに失敗しました: {e}")
    DB_AVAILABLE = False
except Exception as e:
    # その他のエラーもキャッチ
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"データベースモジュールの初期化エラー: {e}")
    DB_AVAILABLE = False

# .envファイルを読み込む
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    parent_env = project_root.parent.parent.parent / "API.env"
    if parent_env.exists():
        load_dotenv(parent_env)

# 設定を読み込む
try:
    from src.config.settings import Settings
    settings = Settings()
    ENABLE_DB_PERSISTENCE = settings.ENABLE_DB_PERSISTENCE
except ImportError:
    ENABLE_DB_PERSISTENCE = False

# APIサーバーのベースURL（デフォルトはローカル）
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# ロガー設定
try:
    from src.utils.logger import setup_logger
    logger = setup_logger()
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

# ページ設定
st.set_page_config(
    page_title="リサーチエージェント - チャット",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSSスタイル
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
    }
    .main .block-container {
        max-width: 1350px;
        padding: 2rem 1rem;
    }
    /* 結果表示部分を中央揃えで適切な幅に制限（1.5倍に拡大） */
    .stMarkdown {
        max-width: 1200px;
        margin: 0 auto;
    }
    /* レポート表示部分の幅を制限（1.5倍に拡大） */
    div[data-testid="stVerticalBlock"] {
        max-width: 1200px;
        margin: 0 auto;
    }
    /* メトリクス表示の幅を制限（1.5倍に拡大） */
    div[data-testid="stMetricContainer"] {
        max-width: 1200px;
        margin: 0 auto;
    }
    .sidebar .sidebar-content {
        background-color: #f0f2f6;
    }
    .research-status {
        padding: 0.5rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .status-processing {
        background-color: #e3f2fd;
        color: #1976d2;
    }
    .status-completed {
        background-color: #e8f5e9;
        color: #388e3c;
    }
    .status-failed {
        background-color: #ffebee;
        color: #d32f2f;
    }
    /* コードブロックのスタイル改善 */
    .stMarkdown code {
        background-color: #f4f4f4;
        padding: 0.2em 0.4em;
        border-radius: 3px;
        font-size: 0.9em;
    }
    .stMarkdown pre {
        background-color: #f8f8f8;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        padding: 1em;
        overflow-x: auto;
    }
    /* ボタンのスタイル改善 */
    .stButton > button {
        border-radius: 5px;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    /* レスポンシブデザイン */
    @media (max-width: 768px) {
        .main .block-container {
            max-width: 100%;
            padding: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)


# セッション状態の初期化
def init_session_state():
    """セッション状態を初期化"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "research_history" not in st.session_state:
        st.session_state.research_history = []
    
    if "current_research_id" not in st.session_state:
        st.session_state.current_research_id = None
    
    if "research_status" not in st.session_state:
        st.session_state.research_status = None
    
    if "streaming_enabled" not in st.session_state:
        st.session_state.streaming_enabled = True
    
    if "regenerate_prompt" not in st.session_state:
        st.session_state.regenerate_prompt = None
    
    if "regenerate_theme" not in st.session_state:
        st.session_state.regenerate_theme = None
    
    if "regenerate_research_id" not in st.session_state:
        st.session_state.regenerate_research_id = None
    
    if "stop_requested" not in st.session_state:
        st.session_state.stop_requested = False
    
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = str(uuid.uuid4())
    
    if "messages_loaded_from_db" not in st.session_state:
        st.session_state.messages_loaded_from_db = False
    
    if "db_warning_shown" not in st.session_state:
        st.session_state.db_warning_shown = False
    
    # データベース初期化
    if DB_AVAILABLE and ENABLE_DB_PERSISTENCE:
        try:
            init_db()
        except Exception as e:
            logger.warning(f"データベース初期化エラー: {e}")


# API関数
def create_research(theme: str, max_iterations: int = 5, enable_human_intervention: bool = False) -> Optional[str]:
    """リサーチを開始"""
    url = f"{API_BASE_URL}/research"
    payload = {
        "theme": theme,
        "max_iterations": max_iterations,
        "enable_human_intervention": enable_human_intervention,
        "checkpointer_type": "memory"
    }
    
    try:
        # リサーチ作成は時間がかかる可能性があるため、タイムアウトを延長（300秒）
        # LLM要約処理を含むため、十分な時間を確保
        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()
        return data["research_id"]
    except requests.exceptions.ConnectionError as e:
        # 接続エラーの場合、より分かりやすいメッセージを表示
        error_msg = f"""
**❌ APIサーバーに接続できません**

APIサーバーが起動していない可能性があります。

**解決方法:**
1. 別のターミナルでAPIサーバーを起動してください:
   ```bash
   uvicorn src.api.main:app --reload
   ```
2. APIサーバーが起動したら、以下のURLにアクセスできることを確認してください:
   - {API_BASE_URL}/health
   - {API_BASE_URL}/docs
3. サイドバーの「🏥 ヘルスチェック」ボタンで接続を確認できます

**現在のAPI URL**: `{API_BASE_URL}`
"""
        st.error(error_msg)
        logger.error(f"APIサーバー接続エラー: {e}")
        return None
    except requests.exceptions.Timeout as e:
        error_msg = f"""
**⏰ タイムアウトエラー**: APIサーバーからの応答がありませんでした（300秒以内）

APIサーバーがリクエストを処理中である可能性があります。

**解決方法:**
1. APIサーバーのログを確認してください
2. リサーチが長時間実行されている場合は、ステータスを確認してください
3. APIサーバーが正常に動作しているか確認してください: `{API_BASE_URL}/health`

**現在のAPI URL**: `{API_BASE_URL}`
"""
        st.error(error_msg)
        logger.error(f"APIサーバータイムアウト: {e}")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"**HTTPエラー**: APIサーバーからエラーレスポンスが返されました。\n\nステータスコード: {response.status_code}\n詳細: {e}")
        logger.error(f"APIサーバーHTTPエラー: {e}")
        return None
    except Exception as e:
        st.error(f"**リサーチ作成エラー**: {e}\n\nAPIサーバーが起動しているか確認してください: `{API_BASE_URL}`")
        logger.error(f"リサーチ作成エラー: {e}", exc_info=True)
        return None


def get_research_status(research_id: str) -> Optional[dict]:
    """リサーチのステータスを取得"""
    url = f"{API_BASE_URL}/research/{research_id}/status"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def get_research_result(research_id: str) -> Optional[dict]:
    """リサーチ結果を取得"""
    url = f"{API_BASE_URL}/research/{research_id}"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 422:
            return None
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def resume_research(research_id: str, human_input: str) -> bool:
    """中断されたリサーチを再開"""
    url = f"{API_BASE_URL}/research/{research_id}/resume"
    payload = {"human_input": human_input}
    
    try:
        # リサーチ再開も時間がかかる可能性があるため、タイムアウトを延長（300秒）
        # LLM要約処理を含むため、十分な時間を確保
        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        return True
    except Exception:
        return False


def delete_research(research_id: str) -> bool:
    """リサーチを削除"""
    url = f"{API_BASE_URL}/research/{research_id}"
    
    try:
        response = requests.delete(url, timeout=5)
        response.raise_for_status()
        return True
    except Exception:
        return False


def check_health() -> tuple[bool, str]:
    """
    ヘルスチェック
    
    Returns:
        (is_healthy, message): ヘルスチェック結果とメッセージ
    """
    url = f"{API_BASE_URL}/health"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "healthy":
            return True, "✅ APIサーバーは正常です"
        else:
            return False, f"⚠️ APIサーバーのステータス: {data.get('status', 'unknown')}"
    except requests.exceptions.ConnectionError:
        return False, f"❌ APIサーバーに接続できません\n\nAPIサーバーを起動してください:\n```bash\nuvicorn src.api.main:app --reload\n```\n\n現在のAPI URL: `{API_BASE_URL}`"
    except requests.exceptions.Timeout:
        return False, f"⏰ タイムアウト: APIサーバーからの応答がありません\n\nAPI URL: `{API_BASE_URL}`"
    except Exception as e:
        return False, f"❌ エラー: {str(e)}\n\nAPI URL: `{API_BASE_URL}`"


def generate_title_from_theme(theme: str, max_length: int = 50, use_llm: bool = False, draft_content: Optional[str] = None) -> str:
    """
    テーマからタイトルを生成
    
    Args:
        theme: 調査テーマ
        max_length: 最大文字数
        use_llm: LLMを使用するか
        draft_content: レポートのドラフト内容（LLM使用時）
    
    Returns:
        生成されたタイトル
    """
    if use_llm and DB_AVAILABLE:
        try:
            return generate_title_with_llm(theme, draft_content, max_length)
        except Exception as e:
            st.warning(f"LLMタイトル生成エラー: {e}。フォールバックを使用します。")
            return generate_title_fallback(theme, max_length)
    else:
        return generate_title_fallback(theme, max_length)


def format_research_for_history(research_id: str, theme: str, status: str, title: Optional[str] = None) -> Dict:
    """履歴用にリサーチ情報をフォーマット"""
    if title is None:
        title = generate_title_from_theme(theme)
    
    return {
        "research_id": research_id,
        "theme": theme,
        "status": status,
        "created_at": datetime.now().isoformat(),
        "title": title
    }


def save_research_to_history(research_info: Dict):
    """リサーチ履歴に保存（セッション状態とDB）"""
    # セッション状態に保存
    if research_info not in st.session_state.research_history:
        st.session_state.research_history.insert(0, research_info)
        # 履歴は最大50件まで保持
        if len(st.session_state.research_history) > 50:
            st.session_state.research_history = st.session_state.research_history[:50]
    
    # データベースに保存
    if DB_AVAILABLE and ENABLE_DB_PERSISTENCE:
        try:
            db_gen = get_db_session()
            db = next(db_gen, None)
            if db is not None:
                try:
                    db_save_research_history(
                        db=db,
                        research_id=research_info["research_id"],
                        theme=research_info["theme"],
                        status=research_info["status"],
                        title=research_info.get("title"),
                        metadata_json={
                            "created_at": research_info.get("created_at")
                        }
                    )
                finally:
                    db.close()
        except Exception as e:
            logger.warning(f"データベース保存エラー: {e}")


def load_research_history_from_db():
    """データベースからリサーチ履歴を読み込む"""
    if not DB_AVAILABLE or not ENABLE_DB_PERSISTENCE:
        return
    
    try:
        db_gen = get_db_session()
        db = next(db_gen, None)
        if db is not None:
            try:
                db_history = db_get_all_research_history(db, limit=50)
                # セッション状態に反映
                for research in db_history:
                    research_info = {
                        "research_id": research.research_id,
                        "theme": research.theme,
                        "status": research.status,
                        "created_at": research.created_at.isoformat() if research.created_at else datetime.now().isoformat(),
                        "title": research.title or research.theme[:50] + "..." if len(research.theme) > 50 else research.theme
                    }
                    # 重複チェック
                    if not any(h["research_id"] == research_info["research_id"] for h in st.session_state.research_history):
                        st.session_state.research_history.append(research_info)
            finally:
                db.close()
    except Exception as e:
        logger.warning(f"データベース読み込みエラー: {e}")


def display_research_result(result: dict, research_id: str = None):
    """リサーチ結果を表示"""
    if not result:
        return
    
    # 結果表示を中央揃えで適切な幅に制限するためのコンテナ
    # コンテナを使用せず、直接表示（チェックボックス変更時の表示問題を回避）
    st.markdown("### 📊 リサーチ結果")
    
    # 統計情報
    if result.get("statistics"):
        stats = result["statistics"]
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("イテレーション回数", stats.get("iterations", 0))
        with col2:
            st.metric("収集ソース数", stats.get("sources_collected", 0))
        with col3:
            st.metric("処理時間", f"{stats.get('processing_time_seconds', 0)}秒")
    
    # レポート
    if result.get("report") and result["report"].get("draft"):
        st.markdown("### 📄 レポート")
        
        # アクションボタン（再生成、停止）
        col1, col2 = st.columns([1, 4])
        with col1:
            if research_id and st.button("🔄 再生成", key=f"regenerate_{research_id}", use_container_width=True):
                # 再生成機能
                theme = result.get("theme", "")
                if theme:
                    st.session_state.regenerate_theme = theme
                    st.session_state.regenerate_research_id = research_id
                    st.rerun()
        
        # レポート本文を処理（Footnotesを参照ソースへのリンクに変換）
        report_draft = result["report"]["draft"]
        
        # Footnotesセクション（## 参考文献）を削除
        # Footnotesセクションは「## 参考文献」から始まり、次のセクション（---）まで
        import re
        # Footnotesセクションを削除
        report_draft = re.sub(r'## 参考文献.*?(?=\n---|\n## |\Z)', '', report_draft, flags=re.DOTALL)
        
        # Footnotes形式（[^1], [^2]など）を参照ソースへのリンクに変換
        if result["report"].get("sources"):
            sources = result["report"]["sources"]
            # 各Footnotesを参照ソースへのリンクに変換
            for i, source in enumerate(sources, 1):
                url = source.get('url', 'N/A')
                # [^数字]形式を[数字](URL)形式に変換
                footnote_pattern = rf'\[\^{i}\]'
                link_replacement = f'[{i}]({url})'
                report_draft = re.sub(footnote_pattern, link_replacement, report_draft)
        
        # Markdownレンダリング（コードブロックのハイライトを含む）
        # Streamlitは自動的にコードブロックをハイライトします
        st.markdown(report_draft, unsafe_allow_html=False)
        
        # ダウンロードボタン
        draft_content = report_draft
        
        # 参照ソース情報を追加（Footnotesセクションは表示しない）
        if result["report"].get("sources"):
            draft_content += "\n\n---\n\n## 📚 参照ソース\n\n"
            draft_content += f"本レポートの作成にあたり、以下の {len(result['report']['sources'])} 件のソースを参照しました。\n\n"
            
            for i, source in enumerate(result["report"]["sources"], 1):
                draft_content += f"### {i}. {source.get('title', 'N/A')}\n\n"
                draft_content += f"- **URL**: [{source.get('url', 'N/A')}]({source.get('url', 'N/A')})\n"
                if source.get("summary"):
                    # 要約は全文を表示
                    draft_content += f"- **要約**: {source['summary']}\n"
                if source.get("relevance_score") is not None:
                    draft_content += f"- **関連性スコア**: {source['relevance_score']:.2f}\n"
                if source.get("source"):
                    draft_content += f"- **ソース**: {source['source']}\n"
                draft_content += "\n"
        
        st.download_button(
            label="📥 レポートをダウンロード",
            data=draft_content,
            file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )
        
        # 参照ソース
        if result["report"].get("sources"):
            sources = result["report"]["sources"]
            sources_key = f"sources_selection_{research_id if research_id else 'default'}"
            expander_state_key = f"expander_open_{sources_key}"
            
            # expanderの開閉状態を明示的に管理（デフォルトで開く）
            if expander_state_key not in st.session_state:
                st.session_state[expander_state_key] = True
            
            with st.expander(f"📚 参照ソース ({len(sources)}件)", expanded=st.session_state[expander_state_key]):
                    # 選択状態の初期化
                    if sources_key not in st.session_state:
                        st.session_state[sources_key] = []
                    
                    # 全選択/全解除ボタン
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ すべて選択", key=f"select_all_{sources_key}"):
                            st.session_state[sources_key] = list(range(len(sources)))
                            # チェックボックスのkeyで管理されている状態も同期（ウィジェット作成前に設定）
                            for i in range(len(sources)):
                                checkbox_key = f"source_check_{sources_key}_{i}"
                                st.session_state[checkbox_key] = True
                            st.rerun()
                    with col2:
                        if st.button("❌ すべて解除", key=f"deselect_all_{sources_key}"):
                            st.session_state[sources_key] = []
                            # チェックボックスのkeyで管理されている状態も同期（ウィジェット作成前に設定）
                            for i in range(len(sources)):
                                checkbox_key = f"source_check_{sources_key}_{i}"
                                st.session_state[checkbox_key] = False
                            st.rerun()
                    
                    # 選択されたソース数を表示
                    selected_count = len(st.session_state[sources_key])
                    if selected_count > 0:
                        st.info(f"📌 {selected_count}件のソースが選択されています")
                    
                    # 各ソースにチェックボックスを追加
                    # チェックボックスの状態変更を効率的に処理（高速化）
                    for i, source in enumerate(sources):
                        col_check, col_content = st.columns([1, 20])
                        with col_check:
                            # チェックボックスのキー（Streamlitの状態管理に使用）
                            checkbox_key = f"source_check_{sources_key}_{i}"
                            
                            # チェックボックスの現在の状態を取得（sources_keyリストから判断）
                            is_selected = i in st.session_state[sources_key]
                            
                            # チェックボックスの初期状態を設定（初回のみ、ウィジェット作成前に設定）
                            # 注意: ウィジェット作成後にst.session_stateで値を設定すると警告が表示される
                            if checkbox_key not in st.session_state:
                                st.session_state[checkbox_key] = is_selected
                            
                            # チェックボックスを表示
                            # valueパラメータを使用する場合は、st.session_stateで値を変更しない
                            new_selected = st.checkbox(
                                "",
                                value=is_selected,  # sources_keyリストから直接判断した値を使用
                                key=checkbox_key,
                                label_visibility="collapsed"
                            )
                            
                            # 状態が変更された場合のみsession_stateを更新
                            if new_selected != is_selected:
                                # sources_keyリストを更新
                                if new_selected:
                                    # 追加（重複チェックを避ける）
                                    if i not in st.session_state[sources_key]:
                                        st.session_state[sources_key].append(i)
                                else:
                                    # 削除（効率的に）
                                    try:
                                        st.session_state[sources_key].remove(i)
                                    except ValueError:
                                        pass  # 既に削除されている場合は何もしない
                                # expanderの開閉状態を保持（開いたままにする）
                                st.session_state[expander_state_key] = True
                                st.rerun()
                        
                        with col_content:
                            st.markdown(f"**{i+1}. {source.get('title', 'N/A')}**")
                            url = source.get('url', 'N/A')
                            st.markdown(f"- URL: {url}")
                            
                            if source.get("summary"):
                                st.caption(source["summary"][:200] + "..." if len(source["summary"]) > 200 else source["summary"])
                            if source.get("relevance_score"):
                                st.caption(f"関連性スコア: {source['relevance_score']:.2f}")
                            
                            # PDFファイルの場合は関連性スコアの後にダウンロードボタンを表示
                            is_pdf_url = url.lower().endswith('.pdf') or '.pdf' in url.lower() if url != 'N/A' else False
                            if is_pdf_url and url != 'N/A':
                                pdf_download_key = f"pdf_download_{sources_key}_{i}"
                                if pdf_download_key not in st.session_state:
                                    st.session_state[pdf_download_key] = None
                                
                                if st.button(f"📥 PDFをダウンロード", key=f"fetch_pdf_{sources_key}_{i}", use_container_width=False):
                                    try:
                                        with st.spinner("PDFファイルを取得中..."):
                                            headers = {
                                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                                                "Accept": "application/pdf,application/octet-stream,*/*",
                                            }
                                            response = requests.get(url, timeout=30, headers=headers, allow_redirects=True)
                                            response.raise_for_status()
                                            st.session_state[pdf_download_key] = response.content
                                            st.success("PDFファイルを取得しました。")
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"PDFファイルの取得に失敗しました: {e}")
                                
                                # PDFファイルが取得済みの場合はダウンロードボタンを表示
                                if st.session_state[pdf_download_key] is not None:
                                    pdf_filename = url.split('/')[-1].split('?')[0] or f"source_{i+1}.pdf"
                                    st.download_button(
                                        label=f"📥 {pdf_filename}をダウンロード",
                                        data=st.session_state[pdf_download_key],
                                        file_name=pdf_filename,
                                        mime="application/pdf",
                                        key=f"download_pdf_file_{sources_key}_{i}",
                                        use_container_width=False
                                    )
                    
                    # PDFダウンロードボタン
                    st.divider()
                    selected_count = len(st.session_state[sources_key])
                    if selected_count > 0:
                        if PDF_AVAILABLE:
                            # PDF生成とダウンロード
                            pdf_key = f"pdf_buffer_{sources_key}"
                            pdf_filename_key = f"pdf_filename_{sources_key}"
                            
                            # PDF生成ボタン（各ソースごとに個別のPDFを生成）
                            if st.button(
                                f"📥 選択した{selected_count}件のソースページをPDFで生成",
                                key=f"generate_pdf_{sources_key}",
                                use_container_width=True
                            ):
                                try:
                                    with st.spinner(f"📄 PDFを生成中... 各URL先のページを取得しています (0/{selected_count})"):
                                        # 各ソースごとに個別のPDFを生成
                                        pdf_buffers_key = f"pdf_buffers_{sources_key}"
                                        pdf_filenames_key = f"pdf_filenames_{sources_key}"
                                        
                                        pdf_buffers = {}
                                        pdf_filenames = {}
                                        
                                        selected_indices = st.session_state[sources_key]
                                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        
                                        for idx, source_idx in enumerate(selected_indices, 1):
                                            if source_idx < 0 or source_idx >= len(sources):
                                                continue
                                            
                                            source = sources[source_idx]
                                            source_title = source.get('title', 'source')
                                            source_safe = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in source_title[:50])
                                            
                                            # 単一ソース用のPDFを生成
                                            pdf_buffer = generate_single_source_pdf(
                                                source,
                                                source_idx,
                                                result.get("theme", "リサーチ")
                                            )
                                            
                                            filename = f"{source_safe}_{timestamp}.pdf"
                                            pdf_buffers[source_idx] = pdf_buffer.getvalue()
                                            pdf_filenames[source_idx] = filename
                                        
                                        # セッションステートに保存
                                        st.session_state[pdf_buffers_key] = pdf_buffers
                                        st.session_state[pdf_filenames_key] = pdf_filenames
                                        
                                        st.success(f"✅ {len(pdf_buffers)}件のPDFの生成が完了しました。")
                                except Exception as e:
                                    st.error(f"PDF生成エラー: {e}")
                                    logger.error(f"PDF生成エラー: {e}", exc_info=True)
                            
                            # 生成されたPDFのダウンロードボタンを表示
                            pdf_buffers_key = f"pdf_buffers_{sources_key}"
                            pdf_filenames_key = f"pdf_filenames_{sources_key}"
                            
                            if pdf_buffers_key in st.session_state and pdf_filenames_key in st.session_state:
                                pdf_buffers = st.session_state[pdf_buffers_key]
                                pdf_filenames = st.session_state[pdf_filenames_key]
                                
                                if pdf_buffers and pdf_filenames:
                                    st.markdown("### 📥 生成されたPDFをダウンロード")
                                    for source_idx in st.session_state[sources_key]:
                                        if source_idx in pdf_buffers and source_idx in pdf_filenames:
                                            source = sources[source_idx]
                                            source_title = source.get('title', 'N/A')
                                            filename = pdf_filenames[source_idx]
                                            
                                            st.download_button(
                                                label=f"📥 {source_title} をダウンロード",
                                                data=pdf_buffers[source_idx],
                                                file_name=filename,
                                                mime="application/pdf",
                                                key=f"download_pdf_{sources_key}_{source_idx}",
                                                use_container_width=False
                                            )
                        else:
                            st.warning("PDF生成機能を使用するにはreportlabをインストールしてください: pip install reportlab")
                    else:
                        st.info("📌 PDFをダウンロードするには、上記のソースを選択してください。")


def display_progress(status_data: dict):
    """進捗情報を表示"""
    if not status_data:
        return
    
    status = status_data.get("status", "unknown")
    
    # ステータスに応じたスタイル
    status_colors = {
        "processing": ("処理中", "status-processing"),
        "completed": ("完了", "status-completed"),
        "failed": ("失敗", "status-failed"),
        "started": ("開始", "status-processing"),
        "interrupted": ("中断", "status-processing")
    }
    
    status_text, status_class = status_colors.get(status, ("不明", ""))
    
    if status_data.get("progress"):
        progress = status_data["progress"]
        st.markdown(f'<div class="research-status {status_class}">', unsafe_allow_html=True)
        st.write(f"**ステータス**: {status_text}")
        st.write(f"**進捗**: {progress.get('current_iteration', 0)}/{progress.get('max_iterations', 0)} イテレーション")
        st.write(f"**現在のノード**: {progress.get('current_node', 'unknown')}")
        
        if status_data.get("statistics"):
            stats = status_data["statistics"]
            st.write(f"**収集ソース数**: {stats.get('sources_collected', 0)}")
        st.markdown('</div>', unsafe_allow_html=True)


# サイドバー
def render_sidebar():
    """サイドバーをレンダリング"""
    with st.sidebar:
        st.title("🔍 リサーチエージェント")
        
        # 新規チャットボタン
        if st.button("➕ 新規チャット", use_container_width=True):
            st.session_state.messages = []
            st.session_state.current_research_id = None
            st.session_state.research_status = None
            st.session_state.conversation_id = str(uuid.uuid4())
            st.rerun()
        
        # DBから履歴を読み込むボタン
        if DB_AVAILABLE and ENABLE_DB_PERSISTENCE:
            if st.button("🔄 DBから履歴を読み込み", use_container_width=True):
                load_research_history_from_db()
                st.success("データベースから履歴を読み込みました")
                st.rerun()
        elif not ENABLE_DB_PERSISTENCE:
            # データベースが利用できない場合の情報表示
            st.info("ℹ️ データベース永続化は無効です。設定方法はREADME_DB.mdを参照してください。")
        
        st.divider()
        
        # 履歴セクション
        st.subheader("📜 履歴")
        
        if st.session_state.research_history:
            for idx, research in enumerate(st.session_state.research_history):
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(
                        research["title"],
                        key=f"history_{research['research_id']}",
                        use_container_width=True
                    ):
                        st.session_state.current_research_id = research["research_id"]
                        st.rerun()
                
                with col2:
                    if st.button("🗑️", key=f"delete_{research['research_id']}"):
                        delete_research(research["research_id"])
                        st.session_state.research_history = [
                            h for h in st.session_state.research_history
                            if h["research_id"] != research["research_id"]
                        ]
                        if st.session_state.current_research_id == research["research_id"]:
                            st.session_state.current_research_id = None
                        st.rerun()
        else:
            st.caption("履歴がありません")
        
        st.divider()
        
        # 設定セクション
        st.subheader("⚙️ 設定")
        
        max_iterations = st.slider(
            "最大イテレーション数",
            min_value=1,
            max_value=10,
            value=5,
            key="max_iterations"
        )
        
        enable_human_intervention = st.checkbox(
            "人間介入を有効化",
            value=False,
            key="enable_human_intervention"
        )
        
        # タイトル自動生成の設定
        auto_generate_title = st.checkbox(
            "タイトルを自動生成",
            value=True,
            key="auto_generate_title",
            help="リサーチ完了時にLLMを使用してタイトルを自動生成します"
        )
        
        st.divider()
        
        # ヘルスチェック
        if st.button("🏥 ヘルスチェック", use_container_width=True):
            is_healthy, message = check_health()
            if is_healthy:
                st.success(message)
            else:
                st.error(message)
                st.markdown("---")
                st.markdown("### 📝 起動手順")
                st.code(f"""
# 方法1: 起動スクリプトを使用（推奨）
python run_api_server.py

# 方法2: uvicornを直接実行
# プロジェクトルートディレクトリから実行してください
cd {project_root}
uvicorn src.api.main:app --reload

# 方法3: Pythonモジュールとして実行
python -m uvicorn src.api.main:app --reload
""", language="bash")
                st.info(f"**現在のAPI URL**: `{API_BASE_URL}`\n\n環境変数 `API_BASE_URL` で変更できます。")


# メインコンテンツ
def render_main_content():
    """メインコンテンツをレンダリング"""
    st.title("🔍 リサーチエージェント - チャット")
    
    # APIサーバーの接続状態を表示
    is_healthy, health_message = check_health()
    if not is_healthy:
        with st.expander("⚠️ APIサーバーに接続できません - 起動方法", expanded=True):
            st.error(health_message)
            st.markdown("### 📝 起動手順")
            st.code(f"""
# Windows: バッチファイルを使用（推奨）
start_api_server.bat

# または、Pythonスクリプトを使用
python run_api_server.py

# または、uvicornを直接実行
# プロジェクトルートディレクトリから実行してください
cd {project_root}
uvicorn src.api.main:app --reload

# または、Pythonモジュールとして実行
python -m uvicorn src.api.main:app --reload
""", language="bash")
            st.info(f"**現在のAPI URL**: `{API_BASE_URL}`\n\n環境変数 `API_BASE_URL` で変更できます。")
            st.markdown("---")
    
    # DBからメッセージを読み込む（初回のみ）
    if DB_AVAILABLE and ENABLE_DB_PERSISTENCE and not st.session_state.get("messages_loaded_from_db", False):
        try:
            db_gen = get_db_session()
            db = next(db_gen, None)
            if db is not None:
                try:
                    db_messages = get_messages(db, st.session_state.conversation_id)
                    if db_messages and not st.session_state.messages:
                        # DBからメッセージを読み込む
                        for db_msg in db_messages:
                            st.session_state.messages.append({
                                "role": db_msg.role,
                                "content": db_msg.content
                            })
                finally:
                    db.close()
            st.session_state.messages_loaded_from_db = True
        except Exception as e:
            logger.warning(f"DBメッセージ読み込みエラー: {e}")
    
    # メッセージ履歴を表示
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            # Markdownレンダリング（コードブロックのハイライトを含む）
            # Streamlitは自動的にコードブロックをシンタックスハイライトします
            st.markdown(msg["content"], unsafe_allow_html=False)
            
            # アシスタントメッセージに再生成ボタンを追加
            if msg["role"] == "assistant" and idx > 0:
                # 直前のユーザーメッセージを取得
                if idx > 0 and st.session_state.messages[idx - 1]["role"] == "user":
                    user_prompt = st.session_state.messages[idx - 1]["content"]
                    if st.button("🔄 再生成", key=f"regenerate_msg_{idx}", use_container_width=False):
                        st.session_state.regenerate_prompt = user_prompt
                        st.rerun()
    
    # 現在のリサーチの進捗を表示（進捗表示は非表示、結果表示は表示）
    if st.session_state.current_research_id:
        status_data = get_research_status(st.session_state.current_research_id)
        if status_data:
            # display_progress(status_data)  # 進捗表示は非表示
            
            # 完了した場合は結果を表示
            if status_data.get("status") == "completed":
                result = get_research_result(st.session_state.current_research_id)
                if result:
                    display_research_result(result, st.session_state.current_research_id)
            
            # 中断された場合
            elif status_data.get("status") == "interrupted":
                st.warning("⏸️ リサーチが中断されました。人間の入力が必要です。")
                human_input = st.text_input("入力してください:", key="human_input")
                if st.button("再開"):
                    if human_input:
                        if resume_research(st.session_state.current_research_id, human_input):
                            st.success("リサーチを再開しました")
                            st.rerun()
    
    # 再生成処理（優先度: 再生成 > チャット入力）
    regenerate_prompt = st.session_state.get("regenerate_prompt")
    regenerate_theme = st.session_state.get("regenerate_theme")
    
    if regenerate_prompt:
        prompt = regenerate_prompt
        st.session_state.regenerate_prompt = None
        # 最後のアシスタントメッセージを削除
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
            st.session_state.messages.pop()
    elif regenerate_theme:
        prompt = regenerate_theme
        st.session_state.regenerate_theme = None
        st.session_state.regenerate_research_id = None
    else:
        prompt = None
    
    # チャット入力
    chat_input = st.chat_input("調査テーマを入力してください...")
    if chat_input:
        prompt = chat_input
    
    # リサーチを開始（再生成または新規入力）
    if prompt:
        # ユーザーメッセージを追加（新規の場合のみ）
        if not any(msg["content"] == prompt for msg in st.session_state.messages if msg["role"] == "user"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # DBにメッセージを保存
            if DB_AVAILABLE and ENABLE_DB_PERSISTENCE:
                try:
                    db_gen = get_db_session()
                    db = next(db_gen, None)
                    if db is not None:
                        try:
                            add_message(db, st.session_state.conversation_id, "user", prompt)
                        finally:
                            db.close()
                except Exception as e:
                    logger.warning(f"DBメッセージ保存エラー: {e}")
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # リサーチを開始
        with st.chat_message("assistant"):
            with st.spinner("リサーチを開始しています..."):
                research_id = create_research(
                    theme=prompt,
                    max_iterations=st.session_state.get("max_iterations", 5),
                    enable_human_intervention=st.session_state.get("enable_human_intervention", False)
                )
                
                if research_id:
                    st.session_state.current_research_id = research_id
                    
                    # 履歴に保存
                    title = None
                    if st.session_state.get("auto_generate_title", True):
                        # タイトルは後で生成（完了時に）
                        title = generate_title_from_theme(prompt, use_llm=False)
                    research_info = format_research_for_history(
                        research_id, prompt, "started", title=title
                    )
                    save_research_to_history(research_info)
                    
                    # アシスタントメッセージ
                    response = f"リサーチを開始しました。\n\n**リサーチID**: `{research_id}`\n\n進捗を監視しています..."
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                    # DBにメッセージを保存
                    if DB_AVAILABLE and ENABLE_DB_PERSISTENCE:
                        try:
                            db_gen = get_db_session()
                            db = next(db_gen, None)
                            if db is not None:
                                try:
                                    add_message(db, st.session_state.conversation_id, "assistant", response)
                                finally:
                                    db.close()
                        except Exception as e:
                            logger.warning(f"DBメッセージ保存エラー: {e}")
                    
                    # 進捗を監視
                    monitor_research_progress(research_id)
                else:
                    # エラーメッセージは既にcreate_research()で表示されている
                    error_msg = f"リサーチの作成に失敗しました。\n\n**APIサーバーが起動しているか確認してください。**\n\n起動方法:\n```bash\nuvicorn src.api.main:app --reload\n```\n\nAPI URL: `{API_BASE_URL}`"
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})


def stop_research(research_id: str) -> bool:
    """リサーチを停止（削除）"""
    # 現状はDELETEエンドポイントを使用
    # 将来的には専用の停止エンドポイントを実装
    return delete_research(research_id)


def monitor_research_progress(research_id: str):
    """リサーチの進捗を監視（ストリーミング対応）"""
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    max_wait_time = 600  # 10分
    check_interval = 1  # 1秒（よりリアルタイムに更新）
    elapsed_time = 0
    last_iteration = -1
    last_sources_count = -1
    last_node = None
    
    # プログレスバー
    progress_bar = st.progress(0)
    
    # 停止ボタン
    stop_button_placeholder = st.empty()
    
    # リアルタイム更新用のコンテナ
    realtime_info = st.empty()
    
    while elapsed_time < max_wait_time:
        # 停止ボタンの表示（処理中の場合のみ）
        status_data = get_research_status(research_id)
        
        if not status_data:
            break
        
        status = status_data.get("status")
        
        # 停止ボタン（処理中の場合のみ表示）
        if status in ["processing", "started"]:
            with stop_button_placeholder.container():
                if st.button("⏹️ 停止", key=f"stop_{research_id}", use_container_width=True):
                    if stop_research(research_id):
                        st.warning("リサーチを停止しました")
                        st.session_state.stop_requested = True
                        break
        
        # 進捗を表示（非表示）
        # with progress_placeholder.container():
        #     display_progress(status_data)
        
        # プログレスバーを更新
        if status_data.get("progress"):
            progress = status_data["progress"]
            current_iter = progress.get("current_iteration", 0)
            max_iter = progress.get("max_iterations", 1)
            current_node = progress.get("current_node", "unknown")
            progress_value = min(current_iter / max_iter, 1.0) if max_iter > 0 else 0
            progress_bar.progress(progress_value)
            
            # リアルタイム情報を更新
            sources_count = 0
            if status_data.get("statistics"):
                sources_count = status_data["statistics"].get("sources_collected", 0)
            
            # 変更があった場合のみ更新（パフォーマンス向上）
            if (current_iter > last_iteration or 
                sources_count > last_sources_count or 
                current_node != last_node):
                
                with realtime_info.container():
                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption(f"📊 イテレーション: {current_iter}/{max_iter}")
                    with col2:
                        st.caption(f"📚 ソース数: {sources_count}")
                    if current_node != "unknown":
                        st.caption(f"⚙️ 現在のノード: {current_node}")
                
                # イテレーションが進んだ場合、メッセージを更新
                if current_iter > last_iteration:
                    with status_placeholder.container():
                        st.info(f"🔄 イテレーション {current_iter}/{max_iter} を実行中...")
                    last_iteration = current_iter
                
                last_sources_count = sources_count
                last_node = current_node
        
        # 完了または失敗
        if status in ["completed", "failed"]:
            stop_button_placeholder.empty()
            progress_bar.empty()
            status_placeholder.empty()
            realtime_info.empty()
            
            if status == "completed":
                result = get_research_result(research_id)
                if result:
                    st.success("✅ リサーチが完了しました！")
                    display_research_result(result)  # 調査結果を表示
                    
                    # レポートをMarkdownファイルに保存
                    save_report_to_file(result, research_id)
                    
                    # 履歴を更新（タイトルも更新）
                    for research in st.session_state.research_history:
                        if research["research_id"] == research_id:
                            research["status"] = "completed"
                            # タイトル自動生成が有効な場合、より良いタイトルを生成
                            if st.session_state.get("auto_generate_title", True):
                                # テーマと結果からタイトルを生成
                                theme = result.get("theme", research.get("theme", ""))
                                draft_content = None
                                if result.get("report") and result["report"].get("draft"):
                                    draft_content = result["report"]["draft"]
                                
                                # LLMを使用してタイトルを生成
                                title = generate_title_from_theme(
                                    theme,
                                    use_llm=True,
                                    draft_content=draft_content
                                )
                                research["title"] = title
                                
                                # DBのタイトルも更新
                                if DB_AVAILABLE and ENABLE_DB_PERSISTENCE:
                                    try:
                                        db_gen = get_db_session()
                                        db = next(db_gen, None)
                                        if db is not None:
                                            try:
                                                db_save_research_history(
                                                    db=db,
                                                    research_id=research_id,
                                                    theme=theme,
                                                    status="completed",
                                                    title=title,
                                                    metadata_json=result.get("statistics")
                                                )
                                            finally:
                                                db.close()
                                    except Exception as e:
                                        logger.warning(f"DBタイトル更新エラー: {e}")
                            break
                    
                    # 完了メッセージを追加
                    completion_msg = f"✅ リサーチが完了しました！\n\n"
                    completion_msg += f"- イテレーション回数: {result.get('statistics', {}).get('iterations', 0)}\n"
                    completion_msg += f"- 収集ソース数: {result.get('statistics', {}).get('sources_collected', 0)}\n"
                    if result.get("report") and result["report"].get("draft"):
                        completion_msg += f"\nレポートが生成されました。上記の結果セクションをご確認ください。"
                    
                    st.session_state.messages.append({"role": "assistant", "content": completion_msg})
                    
                    # DBにメッセージを保存
                    if DB_AVAILABLE and ENABLE_DB_PERSISTENCE:
                        try:
                            db_gen = get_db_session()
                            db = next(db_gen, None)
                            if db is not None:
                                try:
                                    add_message(db, st.session_state.conversation_id, "assistant", completion_msg)
                                finally:
                                    db.close()
                        except Exception as e:
                            logger.warning(f"DBメッセージ保存エラー: {e}")
                else:
                    st.error("結果の取得に失敗しました")
            else:
                st.error("❌ リサーチが失敗しました")
                st.session_state.messages.append({"role": "assistant", "content": "❌ リサーチが失敗しました"})
            
            break
        
        # 中断
        elif status == "interrupted":
            progress_bar.empty()
            stop_button_placeholder.empty()
            realtime_info.empty()
            st.warning("⏸️ リサーチが中断されました")
            break
        
        # 停止リクエストが来た場合
        if st.session_state.get("stop_requested"):
            progress_bar.empty()
            stop_button_placeholder.empty()
            realtime_info.empty()
            break
        
        time.sleep(check_interval)
        elapsed_time += check_interval
    
    if elapsed_time >= max_wait_time:
        progress_bar.empty()
        stop_button_placeholder.empty()
        realtime_info.empty()
        st.warning("⏰ タイムアウト: 最大待機時間を超過しました")
    
    # 停止フラグをリセット
    st.session_state.stop_requested = False


def _register_japanese_font():
    """日本語フォントを登録"""
    # UnicodeCIDFontを使用（日本語対応の組み込みフォント）
    try:
        # HeiseiKakuGo-W5（平成角ゴシック）を試す
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
        return 'HeiseiKakuGo-W5'
    except Exception as e1:
        try:
            # HeiseiMin-W3（平成明朝）を試す
            pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
            return 'HeiseiMin-W3'
        except Exception as e2:
            # WindowsのTTFフォントを試す
            font_paths = [
                'C:/Windows/Fonts/msgothic.ttf',
                'C:/Windows/Fonts/meiryo.ttf',
                'C:/Windows/Fonts/msmincho.ttf',
            ]
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('JapaneseFont', font_path))
                        return 'JapaneseFont'
                    except Exception:
                        continue
            
            # 最後の手段として、UnicodeCIDFontのデフォルトを試す
            try:
                pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
                return 'HeiseiKakuGo-W5'
            except:
                # フォントが見つからない場合は警告を出してHelveticaを使用
                import logging
                logging.warning("日本語フォントの登録に失敗しました。日本語が正しく表示されない可能性があります。")
                return 'Helvetica'


def _fetch_url_content(url: str) -> str:
    """URL先のページコンテンツを取得（HTMLの場合はtrafilaturaで記事を抽出）"""
    if not SCRAPING_AVAILABLE and not TRAFILATURA_AVAILABLE:
        return "スクレイピング機能が利用できません（BeautifulSoupまたはtrafilaturaが必要です）"
    
    # URLがPDFファイルかどうかをチェック
    is_pdf = url.lower().endswith('.pdf') or '.pdf' in url.lower()
    
    try:
        # より一般的なブラウザのUser-Agentを使用（403エラーを回避）
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }
        
        # PDFファイルの場合はAcceptヘッダーを変更
        if is_pdf:
            headers["Accept"] = "application/pdf,application/octet-stream,*/*"
        
        response = requests.get(url, timeout=30, headers=headers, allow_redirects=True)
        response.raise_for_status()
        
        # Content-Typeをチェック
        content_type = response.headers.get('Content-Type', '').lower()
        
        # PDFファイルの場合
        if is_pdf or 'application/pdf' in content_type:
            if PDF_TEXT_EXTRACTION_AVAILABLE:
                try:
                    # PyPDF2でPDFからテキストを抽出
                    pdf_reader = PyPDF2.PdfReader(BytesIO(response.content))
                    text_content = ""
                    max_pages = min(len(pdf_reader.pages), 10)  # 最大10ページまで
                    for i in range(max_pages):
                        page = pdf_reader.pages[i]
                        page_text = page.extract_text()
                        if page_text:
                            text_content += f"--- ページ {i+1} ---\n\n{page_text}\n\n"
                    
                    if text_content.strip():
                        return text_content.strip()
                    else:
                        return f"PDFファイルを取得しましたが、テキスト抽出に失敗しました。\nURL: {url}\n\n（このPDFは画像ベースのPDFの可能性があります。OCR処理が必要な場合があります）"
                except Exception as e:
                    return f"PDFファイルのテキスト抽出に失敗しました: {str(e)}\nURL: {url}"
            else:
                return f"PDFファイルを取得しましたが、テキスト抽出にはPyPDF2が必要です。\nURL: {url}\n\nインストール方法: pip install PyPDF2\n\n（PDFファイルの内容をPDFに含めるには、PyPDF2をインストールしてください）"
        
        # HTMLページの場合 - trafilaturaを使用して記事を抽出
        if TRAFILATURA_AVAILABLE:
            try:
                # 文字エンコーディングを検出
                if response.encoding is None or response.encoding == 'ISO-8859-1':
                    response.encoding = response.apparent_encoding or 'utf-8'
                
                # trafilaturaで記事コンテンツを抽出
                extracted_text = trafilatura.extract(
                    response.text,
                    url=url,
                    include_comments=False,
                    include_tables=True,
                    include_images=False,
                    include_links=False,
                    output_format='plaintext'
                )
                
                if extracted_text and extracted_text.strip():
                    # テキストクリーンアップ
                    content = re.sub(r'\s+', ' ', extracted_text)
                    content = re.sub(r'\n\s*\n', '\n\n', content)
                    return content.strip()
            except Exception as e:
                # trafilaturaで抽出に失敗した場合は、BeautifulSoupにフォールバック
                import logging
                logging.warning(f"trafilaturaでの抽出に失敗しました: {e}。BeautifulSoupにフォールバックします。")
        
        # trafilaturaが利用できない場合、または抽出に失敗した場合はBeautifulSoupを使用
        if SCRAPING_AVAILABLE:
            # 文字エンコーディングを検出
            if response.encoding is None or response.encoding == 'ISO-8859-1':
                response.encoding = response.apparent_encoding or 'utf-8'
            
            soup = BeautifulSoup(response.content, "html.parser", from_encoding=response.encoding)
            
            # スクリプトとスタイルを除去
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()
            
            # メインコンテンツを抽出
            main = soup.find("main")
            if main:
                content = main.get_text(separator="\n", strip=True)
            else:
                article = soup.find("article")
                if article:
                    content = article.get_text(separator="\n", strip=True)
                else:
                    body = soup.find("body")
                    if body:
                        content = body.get_text(separator="\n", strip=True)
                    else:
                        content = soup.get_text(separator="\n", strip=True)
            
            # テキストクリーンアップ
            content = re.sub(r'\s+', ' ', content)
            content = re.sub(r'\n\s*\n', '\n\n', content)
            
            if not content.strip():
                return f"ページを取得しましたが、コンテンツが見つかりませんでした。\nURL: {url}"
            
            return content.strip()
        else:
            return f"スクレイピング機能が利用できません（BeautifulSoupが必要です）。\nURL: {url}"
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            return f"ページへのアクセスが拒否されました（403 Forbidden）。\nURL: {url}\n\nこのページはアクセス制限されている可能性があります。ブラウザで直接アクセスして確認してください。"
        elif e.response.status_code == 404:
            return f"ページが見つかりませんでした（404 Not Found）。\nURL: {url}"
        else:
            return f"HTTPエラー ({e.response.status_code}): {str(e)}\nURL: {url}"
    except requests.exceptions.Timeout:
        return f"リクエストがタイムアウトしました（30秒）。\nURL: {url}"
    except requests.exceptions.RequestException as e:
        return f"ページの取得に失敗しました: {str(e)}\nURL: {url}"
    except Exception as e:
        return f"エラーが発生しました: {str(e)}\nURL: {url}"


def _download_pdf_file(url: str) -> Optional[bytes]:
    """PDFファイルをダウンロード"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/pdf,application/octet-stream,*/*",
        }
        response = requests.get(url, timeout=30, headers=headers, allow_redirects=True)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/pdf' in content_type or url.lower().endswith('.pdf'):
            return response.content
        return None
    except Exception as e:
        import logging
        logging.warning(f"PDFファイルのダウンロードに失敗: {url}, エラー: {e}")
        return None


def generate_sources_pdf(sources: List[Dict], selected_indices: List[int], theme: str = "参照ソース", progress_callback=None) -> BytesIO:
    """選択された参照ソースのURL先ページをPDF形式で生成（PDFファイルの場合はそのまま埋め込む）"""
    if not PDF_AVAILABLE:
        raise ImportError("reportlabがインストールされていません")
    
    # まず、PDFファイルのURLを検出
    pdf_files = []
    html_sources = []
    
    for source_idx in selected_indices:
        if source_idx < 0 or source_idx >= len(sources):
            continue
        source = sources[source_idx]
        url = source.get('url', '')
        if url and (url.lower().endswith('.pdf') or '.pdf' in url.lower()):
            pdf_content = _download_pdf_file(url)
            if pdf_content:
                pdf_files.append((source_idx, pdf_content, source))
            else:
                html_sources.append((source_idx, source))
        else:
            html_sources.append((source_idx, source))
    
    # PDFファイルのみが選択されている場合、それらを結合
    if pdf_files and len(pdf_files) == len(selected_indices) and PDF_TEXT_EXTRACTION_AVAILABLE:
        try:
            from PyPDF2 import PdfMerger
            pdf_merger = PdfMerger()
            
            for source_idx, pdf_content, source in pdf_files:
                pdf_merger.append(BytesIO(pdf_content))
            
            # 結合されたPDFを返す
            merged_buffer = BytesIO()
            pdf_merger.write(merged_buffer)
            pdf_merger.close()
            merged_buffer.seek(0)
            return merged_buffer
        except Exception as e:
            import logging
            logging.warning(f"PDF結合エラー: {e}。テキスト形式で生成します。")
    
    # テキスト形式でPDFを生成（HTMLページまたはPDFファイルとHTMLページの混合）
    # 日本語フォントを登録
    japanese_font = _register_japanese_font()
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # カスタムスタイル（日本語フォントを使用）
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=japanese_font,
        fontSize=18,
        textColor=(0, 0, 0),
        spaceAfter=30,
        alignment=TA_LEFT
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=japanese_font,
        fontSize=14,
        textColor=(0, 0, 0),
        spaceAfter=12,
        spaceBefore=12,
        alignment=TA_LEFT
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=japanese_font,
        fontSize=10,
        textColor=(0, 0, 0),
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        leading=14
    )
    
    url_style = ParagraphStyle(
        'CustomURL',
        parent=styles['Normal'],
        fontName=japanese_font,
        fontSize=9,
        textColor=(0, 0, 0.8),
        spaceAfter=6,
        alignment=TA_LEFT
    )
    
    content_style = ParagraphStyle(
        'CustomContent',
        parent=styles['Normal'],
        fontName=japanese_font,
        fontSize=9,
        textColor=(0, 0, 0),
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        leading=12
    )
    
    # タイトル
    story.append(Paragraph(f"<b>{theme} - 参照ソースページ内容</b>", title_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"作成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}", normal_style))
    story.append(Paragraph(f"選択されたソース数: {len(selected_indices)}件", normal_style))
    story.append(Spacer(1, 20))
    
    # 選択されたソースのURL先ページを取得して追加
    total = len(selected_indices)
    pdf_files_to_merge = []  # 結合するPDFファイル
    
    for idx, source_idx in enumerate(selected_indices, 1):
        if source_idx < 0 or source_idx >= len(sources):
            continue
        
        source = sources[source_idx]
        title = source.get('title', 'N/A')
        url = source.get('url', 'N/A')
        summary = source.get('summary', '')
        relevance_score = source.get('relevance_score')
        source_type = source.get('source', '')
        
        # 進捗コールバック
        if progress_callback:
            progress_callback(idx, total, title)
        
        # PDFファイルのURLかどうかをチェック
        is_pdf_url = url != 'N/A' and (url.lower().endswith('.pdf') or '.pdf' in url.lower())
        
        if is_pdf_url:
            # PDFファイルの場合は、そのままダウンロードして結合用に保存
            pdf_content = _download_pdf_file(url)
            if pdf_content:
                pdf_files_to_merge.append((source_idx, pdf_content, source))
                # PDFファイルの情報をテキストPDFに追加（結合できない場合のため）
                story.append(Paragraph(f"<b>{idx}. {title}</b>", heading_style))
                story.append(Paragraph(f"<b>URL:</b> {url}", url_style))
                if PDF_TEXT_EXTRACTION_AVAILABLE:
                    try:
                        from PyPDF2 import PdfReader
                        pdf_reader = PdfReader(BytesIO(pdf_content))
                        story.append(Paragraph(f"<b>PDFファイル:</b> {len(pdf_reader.pages)}ページ", normal_style))
                    except:
                        story.append(Paragraph("<b>PDFファイル:</b> 取得済み", normal_style))
                story.append(Paragraph("（このPDFファイルは結合されたPDFに含まれます）", normal_style))
                story.append(Spacer(1, 12))
                continue
        
        # HTMLページの場合
        # ソース番号とタイトル
        story.append(Paragraph(f"<b>{idx}. {title}</b>", heading_style))
        
        # URL
        if url != 'N/A':
            story.append(Paragraph(f"<b>URL:</b> {url}", url_style))
            
            # URL先のページコンテンツを取得
            story.append(Spacer(1, 6))
            story.append(Paragraph("<b>ページ内容:</b>", normal_style))
            
            page_content = _fetch_url_content(url)
            if page_content:
                # 長いコンテンツを適切に分割（PDFの制限を考慮）
                # HTMLエスケープ処理
                page_content_escaped = page_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                # 長すぎる場合は切り詰め（10000文字程度）
                if len(page_content_escaped) > 10000:
                    page_content_escaped = page_content_escaped[:10000] + "\n\n... (内容が長いため一部を省略しています)"
                
                # 段落ごとに分割して追加（長いテキストを適切に処理）
                paragraphs = page_content_escaped.split('\n\n')
                for para in paragraphs[:50]:  # 最大50段落まで
                    if para.strip():
                        story.append(Paragraph(para.strip(), content_style))
                        story.append(Spacer(1, 3))
            else:
                story.append(Paragraph("ページ内容の取得に失敗しました", content_style))
        
        # 要約（元の要約も表示）
        if summary:
            story.append(Spacer(1, 6))
            summary_escaped = summary.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(f"<b>要約:</b> {summary_escaped}", normal_style))
        
        # 関連性スコア
        if relevance_score is not None:
            story.append(Paragraph(f"<b>関連性スコア:</b> {relevance_score:.2f}", normal_style))
        
        # ソースタイプ
        if source_type:
            story.append(Paragraph(f"<b>ソース:</b> {source_type}", normal_style))
        
        # ページ区切り（最後の項目以外）
        if idx < len(selected_indices):
            story.append(PageBreak())
    
    # PDFファイルがある場合、テキストPDFの後に結合
    if pdf_files_to_merge and PDF_TEXT_EXTRACTION_AVAILABLE:
        try:
            from PyPDF2 import PdfMerger
            # まずテキストPDFを生成
            doc.build(story)
            buffer.seek(0)
            
            # PDFファイルを結合
            pdf_merger = PdfMerger()
            pdf_merger.append(buffer)  # テキストPDFを追加
            
            for source_idx, pdf_content, source in pdf_files_to_merge:
                pdf_merger.append(BytesIO(pdf_content))
            
            # 結合されたPDFを返す
            merged_buffer = BytesIO()
            pdf_merger.write(merged_buffer)
            pdf_merger.close()
            merged_buffer.seek(0)
            return merged_buffer
        except Exception as e:
            import logging
            logging.warning(f"PDF結合エラー: {e}。テキストPDFのみを返します。")
            buffer.seek(0)
            return buffer
        
        # 要約（元の要約も表示）
        if summary:
            story.append(Spacer(1, 6))
            summary_escaped = summary.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(f"<b>要約:</b> {summary_escaped}", normal_style))
        
        # 関連性スコア
        if relevance_score is not None:
            story.append(Paragraph(f"<b>関連性スコア:</b> {relevance_score:.2f}", normal_style))
        
        # ソースタイプ
        if source_type:
            story.append(Paragraph(f"<b>ソース:</b> {source_type}", normal_style))
        
        # ページ区切り（最後の項目以外）
        if idx < len(selected_indices):
            story.append(PageBreak())
    
    # PDFを生成
    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_single_source_pdf(source: Dict, source_idx: int, theme: str = "参照ソース") -> BytesIO:
    """単一の参照ソースのURL先ページをPDF形式で生成（PDFファイルの場合はそのまま埋め込む）"""
    if not PDF_AVAILABLE:
        raise ImportError("reportlabがインストールされていません")
    
    title = source.get('title', 'N/A')
    url = source.get('url', 'N/A')
    summary = source.get('summary', '')
    relevance_score = source.get('relevance_score')
    source_type = source.get('source', '')
    
    # PDFファイルのURLかどうかをチェック
    is_pdf_url = url != 'N/A' and (url.lower().endswith('.pdf') or '.pdf' in url.lower())
    
    # PDFファイルの場合は、そのままダウンロードして返す
    if is_pdf_url and PDF_TEXT_EXTRACTION_AVAILABLE:
        pdf_content = _download_pdf_file(url)
        if pdf_content:
            return BytesIO(pdf_content)
    
    # HTMLページまたはPDFファイルの取得に失敗した場合、テキスト形式でPDFを生成
    # 日本語フォントを登録
    japanese_font = _register_japanese_font()
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # カスタムスタイル（日本語フォントを使用）
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=japanese_font,
        fontSize=18,
        textColor=(0, 0, 0),
        spaceAfter=30,
        alignment=TA_LEFT
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=japanese_font,
        fontSize=14,
        textColor=(0, 0, 0),
        spaceAfter=12,
        spaceBefore=12,
        alignment=TA_LEFT
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=japanese_font,
        fontSize=10,
        textColor=(0, 0, 0),
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        leading=14
    )
    
    url_style = ParagraphStyle(
        'CustomURL',
        parent=styles['Normal'],
        fontName=japanese_font,
        fontSize=9,
        textColor=(0, 0, 0.8),
        spaceAfter=6,
        alignment=TA_LEFT
    )
    
    content_style = ParagraphStyle(
        'CustomContent',
        parent=styles['Normal'],
        fontName=japanese_font,
        fontSize=9,
        textColor=(0, 0, 0),
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        leading=12
    )
    
    # タイトル
    story.append(Paragraph(f"<b>{theme} - 参照ソースページ内容</b>", title_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"作成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}", normal_style))
    story.append(Spacer(1, 20))
    
    # ソース情報
    story.append(Paragraph(f"<b>{title}</b>", heading_style))
    
    # URL
    if url != 'N/A':
        story.append(Paragraph(f"<b>URL:</b> {url}", url_style))
        
        # PDFファイルの場合は情報のみ表示
        if is_pdf_url:
            pdf_content = _download_pdf_file(url)
            if pdf_content and PDF_TEXT_EXTRACTION_AVAILABLE:
                try:
                    from PyPDF2 import PdfReader
                    pdf_reader = PdfReader(BytesIO(pdf_content))
                    story.append(Paragraph(f"<b>PDFファイル:</b> {len(pdf_reader.pages)}ページ", normal_style))
                except:
                    story.append(Paragraph("<b>PDFファイル:</b> 取得済み", normal_style))
                story.append(Paragraph("（このPDFファイルはそのまま含まれています）", normal_style))
    
    # 要約（ページ内容の前に表示）
    if summary:
        story.append(Spacer(1, 6))
        summary_escaped = summary.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        story.append(Paragraph(f"<b>要約:</b> {summary_escaped}", normal_style))
    
    # ページ内容（要約の後に表示）
    if url != 'N/A' and not is_pdf_url:
        story.append(Spacer(1, 6))
        story.append(Paragraph("<b>ページ内容:</b>", normal_style))
        
        page_content = _fetch_url_content(url)
        if page_content:
            # 長いコンテンツを適切に分割（PDFの制限を考慮）
            # HTMLエスケープ処理
            page_content_escaped = page_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            # 長すぎる場合は切り詰め（10000文字程度）
            if len(page_content_escaped) > 10000:
                page_content_escaped = page_content_escaped[:10000] + "\n\n... (内容が長いため一部を省略しています)"
            
            # 段落ごとに分割して追加（長いテキストを適切に処理）
            paragraphs = page_content_escaped.split('\n\n')
            for para in paragraphs[:50]:  # 最大50段落まで
                if para.strip():
                    story.append(Paragraph(para.strip(), content_style))
                    story.append(Spacer(1, 3))
        else:
            story.append(Paragraph("ページ内容の取得に失敗しました", content_style))
    
    # 関連性スコア
    if relevance_score is not None:
        story.append(Paragraph(f"<b>関連性スコア:</b> {relevance_score:.2f}", normal_style))
    
    # ソースタイプ
    if source_type:
        story.append(Paragraph(f"<b>ソース:</b> {source_type}", normal_style))
    
    # PDFを生成
    doc.build(story)
    buffer.seek(0)
    return buffer


def save_report_to_file(result: dict, research_id: str):
    """レポートをMarkdownファイルに保存"""
    if not result.get("report") or not result["report"].get("draft"):
        return
    
    try:
        output_dir = project_root / "output"
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        theme = result.get("theme", "リサーチ")
        safe_theme = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in theme[:30])
        filename = f"report_{safe_theme}_{timestamp}.md"
        filepath = output_dir / filename
        
        # レポートをMarkdown形式で構築
        markdown_content = f"""# {theme}

## レポート情報

- **作成日時**: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}
- **リサーチID**: {research_id}
- **イテレーション回数**: {result.get('statistics', {}).get('iterations', 0)}
- **収集データ数**: {result.get('statistics', {}).get('sources_collected', 0)}

## 調査計画

"""
        
        # 調査計画を追加
        if result.get("plan"):
            plan = result["plan"]
            markdown_content += f"**テーマ**: {plan.get('theme', theme)}\n\n"
            if plan.get("investigation_points"):
                markdown_content += "**調査観点**:\n"
                for point in plan["investigation_points"]:
                    markdown_content += f"- {point}\n"
                markdown_content += "\n"
            if plan.get("search_queries"):
                markdown_content += "**検索クエリ**:\n"
                for query in plan["search_queries"]:
                    markdown_content += f"- {query}\n"
                markdown_content += "\n"
        
        # レポート本文を追加
        markdown_content += "---\n\n"
        markdown_content += result["report"]["draft"]
        
        # 参照ソースを追加（レポート本文の最後に確実に追加）
        if result["report"].get("sources"):
            markdown_content += "\n\n---\n\n## 📚 参照ソース\n\n"
            markdown_content += f"本レポートの作成にあたり、以下の {len(result['report']['sources'])} 件のソースを参照しました。\n\n"
            
            for i, source in enumerate(result["report"]["sources"], 1):
                markdown_content += f"### {i}. {source.get('title', 'N/A')}\n\n"
                markdown_content += f"- **URL**: [{source.get('url', 'N/A')}]({source.get('url', 'N/A')})\n"
                if source.get("summary"):
                    # 要約は全文を表示（200文字制限を削除）
                    markdown_content += f"- **要約**: {source['summary']}\n"
                if source.get("relevance_score") is not None:
                    markdown_content += f"- **関連性スコア**: {source['relevance_score']:.2f}\n"
                if source.get("source"):
                    markdown_content += f"- **ソース**: {source['source']}\n"
                markdown_content += "\n"
        
        # ファイルに書き込み
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        
        st.info(f"📄 レポートを保存しました: `{filepath}`")
    except Exception as e:
        st.warning(f"レポートの保存に失敗しました: {e}")


# メイン関数
def main():
    """メイン関数"""
    init_session_state()
    
    # サイドバーをレンダリング
    render_sidebar()
    
    # メインコンテンツをレンダリング
    render_main_content()


if __name__ == "__main__":
    main()
