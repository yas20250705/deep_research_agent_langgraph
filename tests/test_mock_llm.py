"""Mock LLM (LLM_PROVIDER=mock) の動作確認テスト"""

import os
import pytest


@pytest.fixture(autouse=True)
def set_mock_provider():
    os.environ["LLM_PROVIDER"] = "mock"
    yield
    if "LLM_PROVIDER" in os.environ and os.environ["LLM_PROVIDER"] == "mock":
        del os.environ["LLM_PROVIDER"]


def test_mock_llm_instantiation():
    from src.config.settings import Settings
    from src.utils.llm_factory import get_llm_from_settings

    s = Settings()
    assert s.LLM_PROVIDER.lower() == "mock"
    llm = get_llm_from_settings(s, temperature=0.3)
    assert llm._llm_type == "mock"


def test_mock_llm_plan_response():
    from src.config.settings import Settings
    from src.utils.llm_factory import get_llm_from_settings
    from langchain_core.messages import HumanMessage, SystemMessage

    s = Settings()
    llm = get_llm_from_settings(s, temperature=0.3)
    messages = [
        SystemMessage(content="You are a Supervisor. Create a research plan. Output JSON with theme, investigation_points, search_queries, plan_text."),
        HumanMessage(content="Theme: LangGraph"),
    ]
    r = llm.invoke(messages)
    content = r.content if hasattr(r, "content") else str(r)
    assert "theme" in content or "investigation_points" in content or "search_queries" in content
    assert len(content) > 50


def test_mock_llm_routing_response():
    from src.config.settings import Settings
    from src.utils.llm_factory import get_llm_from_settings
    from langchain_core.messages import HumanMessage, SystemMessage

    s = Settings()
    llm = get_llm_from_settings(s, temperature=0.3)
    messages = [
        SystemMessage(content="Decide next_action. Output JSON with next_action and reasoning."),
        HumanMessage(content="Data count: 5. Draft: none."),
    ]
    r = llm.invoke(messages)
    content = r.content if hasattr(r, "content") else str(r)
    assert "next_action" in content
    assert "reasoning" in content or "write" in content or "research" in content
