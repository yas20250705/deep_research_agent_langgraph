"""
Reviewerノード実装

ドラフト評価とフィードバック生成を行うノード
"""

import json
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from src.graph.state import ResearchState
from src.prompts.reviewer_prompt import REVIEWER_SYSTEM_PROMPT, REVIEWER_USER_PROMPT
from src.config.settings import Settings
from src.utils.error_handler import handle_node_errors
from src.utils.retry import call_llm_with_retry
from src.utils.llm_factory import get_llm_from_settings

logger = logging.getLogger(__name__)

def get_settings() -> Settings:
    """Settingsインスタンスを取得（遅延初期化）"""
    return Settings()


def format_research_data_for_review(research_data: list) -> str:
    """
    レビュー用に研究データをフォーマット
    
    Args:
        research_data: 検索結果のリスト
    
    Returns:
        フォーマットされたテキスト
    """
    
    formatted_items = []
    for i, result in enumerate(research_data, 1):
        item = f"[{i}] {result.title}\n"
        item += f"   URL: {result.url}\n"
        item += f"   要約: {result.summary[:200]}...\n"
        formatted_items.append(item)
    
    return "\n".join(formatted_items)


def format_task_plan_for_review(plan) -> str:
    """
    レビュー用に調査計画をフォーマット
    
    Args:
        plan: 調査計画
    
    Returns:
        フォーマットされたテキスト
    """
    
    if plan is None:
        return "計画なし"
    
    text = f"テーマ: {plan.theme}\n"
    text += f"調査観点:\n"
    for point in plan.investigation_points:
        text += f"  - {point}\n"
    text += f"検索クエリ: {', '.join(plan.search_queries)}"
    
    return text


def parse_evaluation_result(evaluation_text) -> dict:
    """
    評価結果をパース
    
    Args:
        evaluation_text: LLMの評価応答（文字列またはリスト）
    
    Returns:
        パースされた評価結果
    """
    
    try:
        # リストの場合は各要素を処理
        if isinstance(evaluation_text, list):
            extracted_texts = []
            for item in evaluation_text:
                if isinstance(item, dict) and 'text' in item:
                    extracted_texts.append(item['text'])
                elif item:
                    extracted_texts.append(str(item))
            content = "".join(extracted_texts)
        # 辞書形式の場合は'text'キーから取得
        elif isinstance(evaluation_text, dict):
            if 'text' in evaluation_text:
                content = evaluation_text['text']
            elif 'content' in evaluation_text:
                content = evaluation_text['content']
            else:
                # 辞書全体を文字列に変換
                content = str(evaluation_text)
        else:
            content = str(evaluation_text) if evaluation_text else ""
        
        # 空文字列チェック
        if not content or not content.strip():
            logger.warning(f"評価結果テキストが空です: evaluation_text={evaluation_text}")
            raise ValueError("評価結果テキストが空です")
        
        # JSONコードブロックを除去
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            parts = content.split("```")
            if len(parts) >= 3:
                content = parts[1].split("\n", 1)[1] if "\n" in parts[1] else parts[2]
                content = content.rsplit("```", 1)[0].strip()
        
        # 再チェック（コードブロック除去後）
        if not content or not content.strip():
            logger.warning(f"コードブロック除去後、コンテンツが空です。元の応答: {evaluation_text}")
            raise ValueError("コンテンツが空です")
        
        result = json.loads(content)
        
        # デフォルト値の設定
        return {
            "approved": result.get("approved", False),
            "overall_score": result.get("overall_score", 0.0),
            "scores": result.get("scores", {
                "fact_check": 0.0,
                "completeness": 0.0,
                "logic": 0.0,
                "format": 0.0
            }),
            "feedback": result.get("feedback", ""),
            "suggested_action": result.get("suggested_action", "research"),
            "issues": result.get("issues", [])
        }
        
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"評価結果パースエラー: {e}, evaluation_text={evaluation_text if evaluation_text else 'N/A'}")
        # フォールバック: デフォルト評価
        return {
            "approved": False,
            "overall_score": 0.5,
            "scores": {
                "fact_check": 0.5,
                "completeness": 0.5,
                "logic": 0.5,
                "format": 0.5
            },
            "feedback": "評価結果のパースに失敗しました。再評価が必要です。",
            "suggested_action": "write",
            "issues": []
        }


@handle_node_errors
def reviewer_node(state: ResearchState) -> ResearchState:
    """
    Reviewerノード: ドラフト評価とフィードバック
    
    処理ステップ:
    1. ドラフトの存在確認
    2. ファクトチェック（出典との整合性）
    3. 網羅性チェック（計画との整合性）
    4. 論理的一貫性チェック
    5. 総合評価とフィードバック生成
    6. 次のアクション決定
    
    Args:
        state: 現在のステート
    
    Returns:
        更新されたステート
    """
    
    draft = state.get("current_draft")
    if draft is None:
        logger.error("current_draftが設定されていません")
        state["messages"].append(
            AIMessage(content="エラー: ドラフトが設定されていません")
        )
        state["next_action"] = "write"
        return state
    
    settings = get_settings()
    llm = get_llm_from_settings(settings, temperature=0)  # 厳密な評価のため
    
    # 評価プロンプト構築
    research_data_text = format_research_data_for_review(state.get("research_data", []))
    task_plan_text = format_task_plan_for_review(state.get("task_plan"))
    
    # プロンプトテンプレート構築（LangChainのテンプレート変数を使用）
    prompt = ChatPromptTemplate.from_messages([
        ("system", REVIEWER_SYSTEM_PROMPT),
        ("human", REVIEWER_USER_PROMPT)
    ])
    
    # チェーンを作成
    chain = prompt | llm
    
    # LLM呼び出し
    try:
        response = call_llm_with_retry(
            chain.invoke,
            {
                "draft": draft,
                "research_data": research_data_text,
                "task_plan": task_plan_text
            }
        )
        
        # 評価結果をパース
        eval_result = parse_evaluation_result(response.content)
        
        # 次のアクション決定
        if eval_result["approved"]:
            state["next_action"] = "end"
            state["feedback"] = None
            state["messages"].append(
                AIMessage(content=f"レビュー完了: ドラフトは承認されました（総合スコア: {eval_result['overall_score']:.2f}）")
            )
        else:
            state["next_action"] = eval_result["suggested_action"]
            state["feedback"] = eval_result["feedback"]
            state["messages"].append(
                AIMessage(content=f"レビュー結果: 改善が必要\n総合スコア: {eval_result['overall_score']:.2f}\nフィードバック: {eval_result['feedback']}")
            )
        
        state["iteration_count"] = state.get("iteration_count", 0) + 1
        
        logger.info(f"Reviewer実行完了: approved={eval_result['approved']}, score={eval_result['overall_score']:.2f}")
        
    except Exception as e:
        logger.error(f"評価エラー: {e}")
        state["messages"].append(
            AIMessage(content=f"評価エラー: {str(e)}")
        )
        # エラー時は再執筆を試みる
        state["next_action"] = "write"
    
    return state

