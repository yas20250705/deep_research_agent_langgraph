"""
Supervisorノード実装

計画立案とルーティング決定を行うノード
"""

from typing import Dict, Any, Tuple
import json
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from src.graph.state import ResearchState
from src.schemas.data_models import ResearchPlan, ensure_research_plan
from src.prompts.supervisor_prompt import SUPERVISOR_PLANNING_PROMPT, SUPERVISOR_ROUTING_PROMPT
from src.config.settings import Settings
from src.utils.error_handler import handle_node_errors
from src.utils.retry import call_llm_with_retry
from src.utils.llm_factory import get_llm_from_settings

logger = logging.getLogger(__name__)

def get_settings() -> Settings:
    """Settingsインスタンスを取得（遅延初期化）"""
    return Settings()


def extract_user_message(messages: list) -> str:
    """
    メッセージ履歴からユーザーメッセージを抽出
    
    Args:
        messages: メッセージ履歴（HumanMessage のリスト、またはチェックポイント復元時の dict のリスト）
    
    Returns:
        ユーザーメッセージの内容
    """
    for message in reversed(messages or []):
        if isinstance(message, HumanMessage):
            return message.content or ""
        if isinstance(message, dict):
            content = message.get("content") or (message.get("data") or {}).get("content")
            if content is not None:
                return content if isinstance(content, str) else str(content)
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
    llm: BaseChatModel
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
    
    # ユーザーからの追加指示（再計画で蓄積された内容を含む）。長い場合は先頭2000文字に制限
    human_input = (state.get("human_input") or "").strip()
    if human_input and len(human_input) > 2000:
        human_input = human_input[:2000] + "..."

    # 同一チャット内の既存レポートが含まれる場合は、調査テーマと既存レポートを明示セクションで分け、LLMが確実に参照するようにする
    marker = "【同一チャット内の既存調査レポート"
    if marker in theme:
        parts = theme.split(marker, 1)
        main_theme = (parts[0] or "").strip()
        # parts[1] は "（考慮し...）】\n" + 既存レポート本文
        reports_block = (parts[1] or "").strip()
        end_bracket = "）】"
        if end_bracket in reports_block:
            reports_block = reports_block.split(end_bracket, 1)[-1].strip()
        human_msg = "## 調査テーマ（今回のテーマのみ記載すること）\n" + main_theme
        human_msg += "\n\n## 同一チャット内の既存調査レポート（必ず参照し、既存の観点を活用・深掘り・補足すること）\n" + reports_block
    else:
        human_msg = f"テーマ: {theme}"
    if human_input:
        human_msg += f"\n\nユーザーからの追加指示（テーマの絞り込み・強調したい点・避けたい表現など）:\n{human_input}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", SUPERVISOR_PLANNING_PROMPT),
        ("human", human_msg)
    ])
    
    chain = prompt | llm
    
    # LLM呼び出し（リトライ付き）（human_msg に theme は既に含まれている）
    response = call_llm_with_retry(chain.invoke, {})
    
    # JSONパース
    try:
        content = response.content
        # リストの場合は各要素を処理
        if isinstance(content, list):
            extracted_texts = []
            for item in content:
                if isinstance(item, dict) and 'text' in item:
                    extracted_texts.append(item['text'])
                elif item:
                    extracted_texts.append(str(item))
            content = "".join(extracted_texts)
        # 辞書形式の場合は'text'キーから取得
        elif isinstance(content, dict):
            if 'text' in content:
                content = content['text']
            elif 'content' in content:
                content = content['content']
            else:
                # 辞書全体を文字列に変換
                content = str(content)
        else:
            content = str(content) if content else ""
        
        # 空文字列チェック
        if not content or not content.strip():
            logger.warning(f"LLM応答が空です: response.content={response.content}")
            raise ValueError("LLM応答が空です")
        
        # JSONコードブロックを除去
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # 再チェック（コードブロック除去後）
        if not content or not content.strip():
            logger.warning(f"コードブロック除去後、コンテンツが空です。元の応答: {response.content}")
            raise ValueError("コンテンツが空です")
        
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
        
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"計画生成のパースエラー: {e}, response.content={response.content if hasattr(response, 'content') else 'N/A'}")
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
    plan = ensure_research_plan(state.get("task_plan"))
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
    llm: BaseChatModel
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
    routing_msg = f"""
        現在の状態:
        - 収集データ数: {progress['data_count']}
        - データ品質スコア: {progress['data_quality']:.2f}
        - イテレーション回数: {state['iteration_count']}
        - 最大イテレーション数: {settings.MAX_ITERATIONS}
        - ドラフト状態: {draft_status}
        """
    human_input_routing = (state.get("human_input") or "").strip()
    if human_input_routing and len(human_input_routing) > 500:
        human_input_routing = human_input_routing[:500] + "..."
    if human_input_routing:
        routing_msg += f"\n\nユーザーからの指示: {human_input_routing}\nこの指示を考慮して next_action を決定すること。"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SUPERVISOR_ROUTING_PROMPT),
        ("human", routing_msg)
    ])
    
    chain = prompt | llm
    
    try:
        response = call_llm_with_retry(chain.invoke, {})
        content = response.content
        
        # リストの場合は各要素を処理
        if isinstance(content, list):
            extracted_texts = []
            for item in content:
                if isinstance(item, dict) and 'text' in item:
                    extracted_texts.append(item['text'])
                elif item:
                    extracted_texts.append(str(item))
            content = "".join(extracted_texts)
        # 辞書形式の場合は'text'キーから取得
        elif isinstance(content, dict):
            if 'text' in content:
                content = content['text']
            elif 'content' in content:
                content = content['content']
            else:
                # 辞書全体を文字列に変換
                content = str(content)
        else:
            content = str(content) if content else ""
        
        # 空文字列チェック
        if not content or not content.strip():
            logger.warning(f"LLM応答が空です: response.content={response.content}")
            raise ValueError("LLM応答が空です")
        
        # JSONパース
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # 再チェック
        if not content or not content.strip():
            logger.warning(f"コードブロック除去後、コンテンツが空です。元の応答: {response.content}")
            raise ValueError("コンテンツが空です")
        
        result = json.loads(content)
        next_action = result.get("next_action", "research")
        reasoning = result.get("reasoning", "LLMによる判断")
        
        return next_action, reasoning
        
    except Exception as e:
        logger.error(f"ルーティング決定エラー: {e}, response.content={response.content if hasattr(response, 'content') else 'N/A'}")
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
    llm = get_llm_from_settings(settings, temperature=0)
    
    # ステップ1: テーマ抽出
    user_message = extract_user_message(state["messages"])
    theme = extract_theme(user_message)
    
    # ステップ2: 計画生成（未設定の場合）
    if state.get("task_plan") is None:
        plan = generate_research_plan(theme, state, llm)
        state["task_plan"] = plan
        logger.info(f"調査計画を生成: {plan.theme}")
        state["human_input"] = None  # 使用済みの追加指示をクリア
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
    
    # ルーティング時にも human_input を使った場合はここでクリア
    state["human_input"] = None
    
    logger.info(f"Supervisor実行完了: next_action={next_action}, iteration={state['iteration_count']}")
    
    return state


@handle_node_errors
def revise_plan_node(state: ResearchState) -> ResearchState:
    """
    Human input に基づいて調査計画を再生成するノード。
    API の replan から呼ばれる場合は常に計画を再生成し、human_input をプロンプトに反映する。
    チェックポイント復元時は messages が dict のリストになるため、_theme_fallback でテーマを補う。
    """
    settings = get_settings()
    llm = get_llm_from_settings(settings, temperature=0)
    # テーマ: messages から取得、空なら task_plan.theme または API が渡した _theme_fallback を使用
    theme = extract_theme(extract_user_message(state.get("messages") or []))
    if not theme and state.get("task_plan"):
        plan_obj = state["task_plan"]
        theme = getattr(plan_obj, "theme", None) or (plan_obj.get("theme") if isinstance(plan_obj, dict) else None) or ""
    if not theme:
        theme = state.get("_theme_fallback") or ""
    plan = generate_research_plan(theme, state, llm)
    state["task_plan"] = plan
    state["human_input"] = None
    logger.info(f"調査計画を再生成（human input 反映）: {plan.theme}")
    return state


def planning_gate_node(state: ResearchState) -> ResearchState:
    """
    計画段階の Human-in-loop 用ゲート。通過のみ（state をそのまま返す）。
    Supervisor → planning_gate の前で中断し、Reviewer → researcher のループではこのノードを経由しないため中断しない。
    """
    return state

