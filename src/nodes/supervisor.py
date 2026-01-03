"""
Supervisorノード実装

計画立案とルーティング決定を行うノード
"""

from typing import Dict, Any, Tuple
import json
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage
from src.graph.state import ResearchState
from src.schemas.data_models import ResearchPlan
from src.prompts.supervisor_prompt import SUPERVISOR_PLANNING_PROMPT, SUPERVISOR_ROUTING_PROMPT
from src.config.settings import Settings
from src.utils.error_handler import handle_node_errors
from src.utils.retry import call_llm_with_retry

logger = logging.getLogger(__name__)

def get_settings() -> Settings:
    """Settingsインスタンスを取得（遅延初期化）"""
    return Settings()


def extract_user_message(messages: list) -> str:
    """
    メッセージ履歴からユーザーメッセージを抽出
    
    Args:
        messages: メッセージ履歴
    
    Returns:
        ユーザーメッセージの内容
    """
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return message.content
    return ""


def extract_theme(message: str) -> str:
    """
    メッセージからテーマを抽出
    
    Args:
        message: ユーザーメッセージ
    
    Returns:
        テーマ文字列
    """
    # 簡易的な抽出（実際はLLMで抽出することも可能）
    return message.strip()


def generate_research_plan(
    theme: str,
    state: ResearchState,
    llm: ChatOpenAI
) -> ResearchPlan:
    """
    調査計画を生成
    
    Args:
        theme: 調査テーマ
        state: 現在のステート
        llm: LLMインスタンス
    
    Returns:
        生成された調査計画
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SUPERVISOR_PLANNING_PROMPT),
        ("human", f"テーマ: {theme}")
    ])
    
    chain = prompt | llm
    
    # LLM呼び出し（リトライ付き）
    response = call_llm_with_retry(chain.invoke, {"theme": theme})
    
    # JSONパース
    try:
        content = response.content
        # JSONコードブロックを除去
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        plan_data = json.loads(content)
        
        # ResearchPlanオブジェクトを作成
        plan = ResearchPlan(
            theme=plan_data.get("theme", theme),
            investigation_points=plan_data.get("investigation_points", []),
            search_queries=plan_data.get("search_queries", []),
            plan_text=plan_data.get("plan_text", f"{theme}について調査します")
        )
        
        logger.info(f"調査計画を生成: テーマ={theme}, 観点数={len(plan.investigation_points)}, クエリ数={len(plan.search_queries)}")
        
        return plan
        
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"計画生成のパースエラー: {e}")
        # フォールバック: 簡易計画を作成
        return ResearchPlan(
            theme=theme,
            investigation_points=[f"{theme}の基本情報", f"{theme}の用途", f"{theme}の特徴"],
            search_queries=[theme, f"{theme} use cases", f"{theme} features"],
            plan_text=f"{theme}について包括的に調査します"
        )


def evaluate_progress(state: ResearchState) -> Dict[str, Any]:
    """
    現在の進捗状況を評価
    
    Args:
        state: 現在のステート
    
    Returns:
        進捗評価結果
    """
    
    data_count = len(state.get("research_data", []))
    
    # データ品質スコア（関連性スコアの平均）
    relevance_scores = [
        r.relevance_score for r in state.get("research_data", [])
        if r.relevance_score is not None
    ]
    data_quality = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.5
    
    # 網羅性（計画に対するカバレッジ）
    plan = state.get("task_plan")
    coverage = 0.0
    if plan and plan.search_queries:
        # 簡易的な評価（実際はより複雑なロジック）
        coverage = min(1.0, data_count / (len(plan.search_queries) * 2))
    
    return {
        "data_count": data_count,
        "data_quality": data_quality,
        "coverage": coverage
    }


def decide_next_action(
    state: ResearchState,
    progress: Dict[str, Any],
    llm: ChatOpenAI
) -> Tuple[str, str]:
    """
    次のアクションを決定
    
    Args:
        state: 現在のステート
        progress: 進捗評価結果
        llm: LLMインスタンス
    
    Returns:
        (next_action, reasoning)のタプル
    """
    
    # 最大イテレーション確認
    settings = get_settings()
    if state["iteration_count"] >= settings.MAX_ITERATIONS:
        return "end", "最大イテレーション数に到達しました"
    
    # データ不足
    MIN_RESEARCH_DATA_COUNT = 5
    if progress["data_count"] < MIN_RESEARCH_DATA_COUNT:
        return "research", f"データが不足しています（現在: {progress['data_count']}件）"
    
    # ドラフト未作成でデータが十分
    if state.get("current_draft") is None and progress["data_count"] >= MIN_RESEARCH_DATA_COUNT:
        return "write", "十分なデータが集まりました。ドラフトを作成します"
    
    # LLMに判断を委譲（複雑なケース）
    draft_status = "あり" if state.get("current_draft") else "なし"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SUPERVISOR_ROUTING_PROMPT),
        ("human", f"""
        現在の状態:
        - 収集データ数: {progress['data_count']}
        - データ品質スコア: {progress['data_quality']:.2f}
        - イテレーション回数: {state['iteration_count']}
        - 最大イテレーション数: {settings.MAX_ITERATIONS}
        - ドラフト状態: {draft_status}
        """)
    ])
    
    chain = prompt | llm
    
    try:
        response = call_llm_with_retry(chain.invoke, {})
        content = response.content
        
        # JSONパース
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        next_action = result.get("next_action", "research")
        reasoning = result.get("reasoning", "LLMによる判断")
        
        return next_action, reasoning
        
    except Exception as e:
        logger.error(f"ルーティング決定エラー: {e}")
        # フォールバック: デフォルトアクション
        return "research", "デフォルトアクション（エラー時）"


@handle_node_errors
def supervisor_node(state: ResearchState) -> ResearchState:
    """
    Supervisorノード: 計画立案とルーティング決定
    
    処理ステップ:
    1. メッセージ履歴からユーザーのテーマを抽出
    2. task_planが未設定の場合、調査計画を生成
    3. 現在の進捗を評価
    4. 次のアクションを決定
    5. 判断理由をメッセージに記録
    
    Args:
        state: 現在のステート
    
    Returns:
        更新されたステート
    """
    
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0,
        api_key=settings.OPENAI_API_KEY
    )
    
    # ステップ1: テーマ抽出
    user_message = extract_user_message(state["messages"])
    theme = extract_theme(user_message)
    
    # ステップ2: 計画生成（未設定の場合）
    if state.get("task_plan") is None:
        plan = generate_research_plan(theme, state, llm)
        state["task_plan"] = plan
        logger.info(f"調査計画を生成: {plan.theme}")
    else:
        plan = state["task_plan"]
    
    # ステップ3: 進捗評価
    progress = evaluate_progress(state)
    
    # ステップ4: ルーティング決定
    next_action, reasoning = decide_next_action(state, progress, llm)
    
    # ステップ5: メッセージ記録
    state["messages"].append(
        AIMessage(content=f"次のアクション: {next_action}\n理由: {reasoning}")
    )
    
    state["next_action"] = next_action
    
    logger.info(f"Supervisor実行完了: next_action={next_action}, iteration={state['iteration_count']}")
    
    return state

