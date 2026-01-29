"""
開発・テスト用の疑似LLMモジュール

LLM_PROVIDER=mock で切り替え可能。APIコストゼロで開発・テストを実行できる。
"""

import json
import logging
import time
from typing import Any, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks.manager import CallbackManagerForLLMRun

logger = logging.getLogger(__name__)

# ----- テンプレートレスポンス -----

SUPERVISOR_PLAN_TEMPLATE = json.dumps({
    "theme": "調査テーマ（モック）",
    "investigation_points": [
        "基本情報と概要",
        "主な用途と活用例",
        "特徴と利点",
        "注意点と制約"
    ],
    "search_queries": [
        "テーマ 概要",
        "theme overview",
        "テーマ 使い方",
        "theme use cases"
    ],
    "plan_text": "上記の観点に基づき、収集した情報を統合してレポートを作成します。"
}, ensure_ascii=False)

SUPERVISOR_ACTION_TEMPLATE = json.dumps({
    "next_action": "write",
    "reasoning": "モック: 十分なデータが集まったと判断し、ドラフト作成に進みます。"
}, ensure_ascii=False)

WRITER_DRAFT_TEMPLATE = """# 調査レポート（モック）

## エグゼクティブサマリー

本レポートは開発・テスト用のモックレスポンスです。実際のLLMでは、収集した情報に基づいてエグゼクティブサマリーが生成されます。モックでは固定のサンプルテキストを返しています。

## 主要な発見

- モックモードではAPIコストが発生しません
- 各ノードの期待出力形式に合わせたテンプレートを返します
- 開発・テスト時の動作確認に利用できます

## 詳細な分析

### 概要

疑似LLMモジュールは、LLM_PROVIDER=mock で有効化されます。計画生成、ルーティング、ドラフト作成、レビュー、要約、タイトル生成の各処理で、プロンプト内容に応じたテンプレートレスポンスを返します。

### 活用シーン

開発環境やCIでのテスト実行時、APIキーなしでの動作確認、コストを抑えた反復開発などに利用できます。

## 参考文献

[^1]: （モックのため出典は省略）
"""

REVIEWER_EVAL_TEMPLATE = json.dumps({
    "approved": True,
    "overall_score": 0.85,
    "scores": {
        "fact_check": 0.9,
        "completeness": 0.85,
        "logic": 0.8,
        "format": 0.85
    },
    "feedback": "",
    "suggested_action": "write",
    "issues": []
}, ensure_ascii=False)

SUMMARY_TEMPLATE = "（モック）与えられたコンテンツの要点を要約したテキストです。開発・テスト時は実際のLLMを呼ばずにこの固定文を返します。"

TITLE_TEMPLATE = "調査レポート（モック）"


def _get_prompt_text(messages: List[BaseMessage]) -> str:
    """メッセージリストからプロンプト全文を取得"""
    parts = []
    for m in messages:
        if hasattr(m, "content") and m.content:
            parts.append(m.content if isinstance(m.content, str) else str(m.content))
    return "\n".join(parts)


def _get_mock_response(prompt: str, response_delay: float = 0.0, log_prompts: bool = False) -> str:
    """
    プロンプト内容から呼び出し元を推定し、対応するテンプレートレスポンスを返す。
    """
    prompt_lower = prompt.lower()
    if log_prompts:
        logger.debug("Mock LLM prompt (first 500 chars): %s", prompt[:500])

    # Supervisor: 調査計画（テーマ、調査観点、search_queries 等）
    if "調査計画" in prompt or "investigation_points" in prompt or "search_queries" in prompt:
        if "テーマ:" in prompt and "next_action" not in prompt:
            return SUPERVISOR_PLAN_TEMPLATE

    # Supervisor: ルーティング（next_action, reasoning, 収集データ数, ドラフト状態）
    if "next_action" in prompt or "次のアクション" in prompt or "ドラフト状態" in prompt or "収集データ数" in prompt:
        return SUPERVISOR_ACTION_TEMPLATE

    # Writer: レポート、マークダウン、エグゼクティブサマリー
    if "writer" in prompt_lower or "レポートを執筆" in prompt or "エグゼクティブサマリー" in prompt:
        if "research_data" in prompt or "収集した情報" in prompt:
            return WRITER_DRAFT_TEMPLATE

    # Reviewer: 評価、approved, overall_score
    if "reviewer" in prompt_lower or "評価してください" in prompt or "approved" in prompt or "overall_score" in prompt:
        if "ドラフト:" in prompt or "draft" in prompt_lower:
            return REVIEWER_EVAL_TEMPLATE

    # Summarizer: 要約、要点を、コンテンツの要点
    if "要点を" in prompt and "コンテンツ" in prompt:
        return SUMMARY_TEMPLATE
    if "要約" in prompt and "url" in prompt_lower:
        return SUMMARY_TEMPLATE

    # Title generator: タイトルを生成、調査テーマ
    if "タイトルを生成" in prompt or "タイトルだけを返してください" in prompt:
        return TITLE_TEMPLATE

    # デフォルト: 計画として返す（supervisorの初回にフォールバック）
    return SUPERVISOR_PLAN_TEMPLATE


class MockChatModel(BaseChatModel):
    """開発・テスト用の疑似LLMモデル。APIを呼ばずテンプレートレスポンスを返す。"""

    response_delay: float = 0.0
    log_prompts: bool = False

    @property
    def _llm_type(self) -> str:
        return "mock"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        prompt_text = _get_prompt_text(messages)
        if self.response_delay > 0:
            time.sleep(self.response_delay)
        response_content = _get_mock_response(
            prompt_text,
            response_delay=self.response_delay,
            log_prompts=self.log_prompts,
        )
        message = AIMessage(content=response_content)
        return ChatResult(generations=[ChatGeneration(message=message)])
