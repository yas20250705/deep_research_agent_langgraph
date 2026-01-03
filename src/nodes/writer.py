"""
Writerノード実装

レポートドラフト作成を行うノード
"""

import re
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from src.graph.state import ResearchState
from src.prompts.writer_prompt import WRITER_SYSTEM_PROMPT, WRITER_USER_PROMPT
from src.config.settings import Settings
from src.utils.error_handler import handle_node_errors
from src.utils.retry import call_llm_with_retry

logger = logging.getLogger(__name__)

def get_settings() -> Settings:
    """Settingsインスタンスを取得（遅延初期化）"""
    return Settings()


def format_research_data(research_data: list) -> str:
    """
    検索結果を構造化テキストに変換
    
    Args:
        research_data: 検索結果のリスト
    
    Returns:
        構造化されたテキスト
    """
    
    formatted_items = []
    for i, result in enumerate(research_data, 1):
        item = f"[ソース{i}]\n"
        item += f"タイトル: {result.title}\n"
        item += f"URL: {result.url}\n"
        item += f"要約: {result.summary}\n"
        if result.relevance_score is not None:
            item += f"関連性スコア: {result.relevance_score:.2f}\n"
        item += "\n"
        formatted_items.append(item)
    
    return "\n".join(formatted_items)


def extract_markdown_content(response_content: str) -> str:
    """
    LLMの応答からマークダウンコンテンツを抽出
    
    Args:
        response_content: LLMの応答
    
    Returns:
        マークダウンのみのコンテンツ
    """
    
    content = response_content
    
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
    
    plan = state.get("task_plan")
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
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.3,
        api_key=settings.OPENAI_API_KEY
    )
    
    # 研究データをテキストに変換
    research_text = format_research_data(research_data)
    
    # フィードバックの考慮
    feedback_context = ""
    if state.get("feedback"):
        feedback_context = f"\n\n前回のフィードバック:\n{state['feedback']}\n\nこのフィードバックを反映してください。"
    
    # 調査観点をフォーマット
    investigation_points_text = "\n".join(
        f"- {point}" for point in plan.investigation_points
    )
    
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
        draft = extract_markdown_content(response.content)
        state["current_draft"] = draft
        state["iteration_count"] = state.get("iteration_count", 0) + 1
        
        # メッセージ記録
        state["messages"].append(
            AIMessage(content=f"ドラフトを生成しました（長さ: {len(draft)}文字）")
        )
        
        logger.info(f"Writer実行完了: ドラフト長={len(draft)}文字")
        
    except Exception as e:
        logger.error(f"ドラフト生成エラー: {e}")
        state["messages"].append(
            AIMessage(content=f"ドラフト生成エラー: {str(e)}")
        )
        state["next_action"] = "end"
    
    return state

