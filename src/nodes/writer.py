"""
Writerノード実装

レポートドラフト作成を行うノード
"""

import re
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from src.graph.state import ResearchState
from src.schemas.data_models import ensure_research_plan
from src.prompts.writer_prompt import WRITER_SYSTEM_PROMPT, WRITER_USER_PROMPT
from src.config.settings import Settings
from src.utils.error_handler import handle_node_errors
from src.utils.retry import call_llm_with_retry
from src.utils.llm_factory import get_llm_from_settings

logger = logging.getLogger(__name__)

def get_settings() -> Settings:
    """Settingsインスタンスを取得（遅延初期化）"""
    return Settings()


def format_research_data(research_data: list, max_chars: int = None) -> str:
    """
    検索結果を構造化テキストに変換
    
    Args:
        research_data: 検索結果のリスト
        max_chars: 最大文字数（Noneの場合は制限なし）
    
    Returns:
        構造化されたテキスト
    """
    
    formatted_items = []
    total_chars = 0
    
    for i, result in enumerate(research_data, 1):
        item = f"[ソース{i}]\n"
        item += f"タイトル: {result.title}\n"
        item += f"URL: {result.url}\n"
        
        # 要約を制限（最大500文字）
        summary = result.summary
        if max_chars and len(summary) > 300:
            summary = summary[:300] + "..."
        item += f"要約: {summary}\n"
        
        if result.relevance_score is not None:
            item += f"関連性スコア: {result.relevance_score:.2f}\n"
        item += "\n"
        
        # 文字数制限チェック
        if max_chars:
            item_chars = len(item)
            if total_chars + item_chars > max_chars:
                # 制限に達した場合は、残りのアイテム数を表示して終了
                remaining = len(research_data) - i
                formatted_items.append(f"\n[注意: 残り{remaining}件のソースは省略されました（文字数制限）]\n")
                break
            total_chars += item_chars
        
        formatted_items.append(item)
    
    return "".join(formatted_items)


def extract_markdown_content(response_content) -> str:
    """
    LLMの応答からマークダウンコンテンツを抽出
    
    Args:
        response_content: LLMの応答（文字列、リスト、または辞書）
    
    Returns:
        マークダウンのみのコンテンツ
    """
    
    # リストの場合は各要素を処理
    if isinstance(response_content, list):
        extracted_texts = []
        for item in response_content:
            if isinstance(item, dict) and 'text' in item:
                extracted_texts.append(item['text'])
            elif item:
                extracted_texts.append(str(item))
        content = "".join(extracted_texts)
    # 辞書形式の場合は'text'キーから取得
    elif isinstance(response_content, dict):
        if 'text' in response_content:
            content = response_content['text']
        elif 'content' in response_content:
            content = response_content['content']
        else:
            # 辞書全体を文字列に変換
            content = str(response_content)
    else:
        content = str(response_content) if response_content else ""
    
    # コードブロックを除去
    if "```markdown" in content:
        content = content.split("```markdown")[1].split("```")[0].strip()
    elif "```" in content:
        # 最初のコードブロックを除去
        parts = content.split("```")
        if len(parts) >= 3:
            content = parts[1].split("\n", 1)[1] if "\n" in parts[1] else parts[2]
            content = content.rsplit("```", 1)[0].strip()
    
    return content


@handle_node_errors
def writer_node(state: ResearchState) -> ResearchState:
    """
    Writerノード: レポートドラフト作成
    
    処理ステップ:
    1. research_dataを構造化テキストに変換
    2. フィードバックがある場合は考慮
    3. LLMにレポート生成を依頼
    4. マークダウン形式で出力
    5. current_draftに保存
    
    Args:
        state: 現在のステート
    
    Returns:
        更新されたステート
    """
    
    plan = ensure_research_plan(state.get("task_plan"))
    if plan is None:
        logger.error("task_planが設定されていません")
        state["messages"].append(
            AIMessage(content="エラー: 調査計画が設定されていません")
        )
        state["next_action"] = "end"
        return state
    
    research_data = state.get("research_data", [])
    if not research_data:
        logger.warning("研究データがありません")
        state["messages"].append(
            AIMessage(content="警告: 研究データが不足しています")
        )
        state["next_action"] = "research"
        return state
    
    settings = get_settings()
    llm = get_llm_from_settings(settings, temperature=0.3)
    
    # 研究データをテキストに変換（トークン数制限を考慮して最大15000文字に制限）
    # 概算: 1トークン ≈ 4文字、制限30000トークン、プロンプトテンプレートで約5000トークン使用
    # 残り25000トークン ≈ 100000文字、安全のため15000文字に制限
    MAX_RESEARCH_DATA_CHARS = 15000
    research_text = format_research_data(research_data, max_chars=MAX_RESEARCH_DATA_CHARS)
    
    # フィードバックの考慮（最大1000文字に制限）
    feedback_context = ""
    if state.get("feedback"):
        feedback = state['feedback']
        if len(feedback) > 1000:
            feedback = feedback[:1000] + "...（省略）"
        feedback_context = f"\n\n前回のフィードバック:\n{feedback}\n\nこのフィードバックを反映してください。"
    # ユーザーからの追加指示（強調したい点・避けたい表現など）。長い場合は先頭1000文字に制限
    human_input = (state.get("human_input") or "").strip()
    if human_input:
        if len(human_input) > 1000:
            human_input = human_input[:1000] + "..."
        feedback_context += f"\n\nユーザーからの追加指示（強調したい点・避けたい表現など）:\n{human_input}\n\nこの追加指示を必ず反映してください。"
    
    # 調査観点をフォーマット（最大2000文字に制限）
    investigation_points = plan.investigation_points
    investigation_points_text = "\n".join(
        f"- {point}" for point in investigation_points
    )
    if len(investigation_points_text) > 2000:
        investigation_points_text = investigation_points_text[:2000] + "...（省略）"
    
    # プロンプト構築
    # 注意: LangChainのテンプレートでは、変数は{変数名}形式で指定
    prompt = ChatPromptTemplate.from_messages([
        ("system", WRITER_SYSTEM_PROMPT),
        ("human", WRITER_USER_PROMPT)
    ])
    
    # チェーンを作成
    chain = prompt | llm
    
    # LLM呼び出し
    try:
        response = call_llm_with_retry(
            chain.invoke,
            {
                "theme": plan.theme,
                "investigation_points": investigation_points_text,
                "research_data": research_text,
                "feedback": feedback_context
            }
        )
        
        # ドラフトを保存
        # response.contentが辞書、リスト、または文字列の場合に対応
        draft = extract_markdown_content(response.content)
        state["current_draft"] = draft
        state["iteration_count"] = state.get("iteration_count", 0) + 1
        state["human_input"] = None  # 使用済みの追加指示をクリア
        
        # メッセージ記録
        state["messages"].append(
            AIMessage(content=f"ドラフトを生成しました（長さ: {len(draft)}文字）")
        )
        
        logger.info(f"Writer実行完了: ドラフト長={len(draft)}文字")
        
    except Exception as e:
        logger.error(f"ドラフト生成エラー: {e}", exc_info=True)
        
        error_str = str(e).lower()
        error_msg = str(e)
        
        # トークン数超過エラーを検出
        if "too large" in error_str or "tokens per min" in error_str or "requested" in error_str:
            # データをさらに削減して再試行
            logger.warning("トークン数超過エラーを検出。研究データを削減して再試行します。")
            # 研究データを半分に削減
            reduced_data = research_data[:len(research_data)//2] if len(research_data) > 1 else research_data
            reduced_text = format_research_data(reduced_data, max_chars=8000)  # さらに制限
            
            try:
                # 再試行（データを削減）
                response = call_llm_with_retry(
                    chain.invoke,
                    {
                        "theme": plan.theme,
                        "investigation_points": investigation_points_text[:1000],  # さらに制限
                        "research_data": reduced_text,
                        "feedback": feedback_context[:500] if feedback_context else ""  # さらに制限
                    }
                )
                
                # response.contentが辞書、リスト、または文字列の場合に対応
                draft = extract_markdown_content(response.content)
                state["current_draft"] = draft
                state["iteration_count"] = state.get("iteration_count", 0) + 1
                state["human_input"] = None  # 使用済みの追加指示をクリア
                state["messages"].append(
                    AIMessage(content=f"⚠️ データを削減してドラフトを生成しました（長さ: {len(draft)}文字）")
                )
                logger.info(f"Writer実行完了（データ削減版）: ドラフト長={len(draft)}文字")
                return state
            except Exception as retry_error:
                # 再試行も失敗した場合はフォールバック
                logger.error(f"データ削減後の再試行も失敗: {retry_error}")
                fallback_draft = f"# {plan.theme}\n\n## 注意\n\nトークン数制限により、収集データを要約してレポートを作成しました。\n\n## 収集データ（要約）\n\n{reduced_text[:2000]}...\n\n## エラー詳細\n\n{error_msg[:500]}"
                state["current_draft"] = fallback_draft
                state["messages"].append(
                    AIMessage(content=f"⚠️ トークン数制限により、要約版ドラフトを生成しました")
                )
                state["next_action"] = "review"
                return state
        
        # RateLimitErrorの場合は、リサーチに戻して再試行
        elif "ratelimit" in error_str or "rate limit" in error_str:
            state["messages"].append(
                AIMessage(content=f"⚠️ APIレート制限に達しました。しばらく待ってから再試行します。")
            )
            state["next_action"] = "research"  # リサーチに戻して待機
        else:
            # その他のエラーの場合は、最小限のドラフトを設定して続行を試みる
            fallback_draft = f"# {plan.theme}\n\n## エラー\n\nドラフト生成中にエラーが発生しました: {error_msg[:500]}\n\n収集されたデータに基づいて、手動でレポートを作成してください。\n\n## 収集データ（要約）\n\n{research_text[:2000]}..."
            state["current_draft"] = fallback_draft
            state["messages"].append(
                AIMessage(content=f"⚠️ ドラフト生成エラーが発生しましたが、フォールバックドラフトを設定しました")
            )
            state["next_action"] = "review"  # レビューに進む
            logger.warning(f"フォールバックドラフトを設定しました")
    
    return state

