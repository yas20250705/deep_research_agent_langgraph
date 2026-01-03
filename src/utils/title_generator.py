"""
LLMタイトル生成ユーティリティ

OpenAI APIを使用してタイトルを生成
"""

from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.config.settings import Settings
from src.utils.logger import setup_logger

logger = setup_logger()
settings = Settings()


def generate_title_with_llm(
    theme: str,
    draft_content: Optional[str] = None,
    max_length: int = 50
) -> str:
    """
    LLMを使用してタイトルを生成
    
    Args:
        theme: 調査テーマ
        draft_content: レポートのドラフト内容（オプション）
        max_length: 最大文字数
    
    Returns:
        生成されたタイトル
    """
    try:
        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.3,  # 創造性を抑える
            api_key=settings.OPENAI_API_KEY
        )
        
        # プロンプトテンプレート
        if draft_content:
            # レポート内容からタイトルを生成
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", """あなたは専門的なレポートのタイトルを生成するアシスタントです。
以下の調査テーマとレポート内容を基に、簡潔で分かりやすいタイトルを生成してください。
タイトルは{max_length}文字以内で、調査の内容を的確に表現するものにしてください。

例:
- テーマ: "LangGraphについて調査してください"
- タイトル: "LangGraphの概要と活用方法"

- テーマ: "Pythonの非同期処理について"
- タイトル: "Python非同期処理の基礎と実践"
"""),
                ("human", """調査テーマ: {theme}

レポート内容（最初の500文字）:
{draft_preview}

上記の内容を基に、簡潔で分かりやすいタイトルを生成してください。タイトルだけを返してください。""")
            ])
            
            # ドラフトの最初の500文字を取得
            draft_preview = draft_content[:500] if draft_content else ""
            
            prompt = prompt_template.format_messages(
                theme=theme,
                draft_preview=draft_preview,
                max_length=max_length
            )
        else:
            # テーマのみからタイトルを生成
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", """あなたは専門的なレポートのタイトルを生成するアシスタントです。
以下の調査テーマを基に、簡潔で分かりやすいタイトルを生成してください。
タイトルは{max_length}文字以内で、調査の内容を的確に表現するものにしてください。

例:
- テーマ: "LangGraphについて調査してください"
- タイトル: "LangGraphの概要と活用方法"

- テーマ: "Pythonの非同期処理について"
- タイトル: "Python非同期処理の基礎と実践"
"""),
                ("human", """調査テーマ: {theme}

上記のテーマを基に、簡潔で分かりやすいタイトルを生成してください。タイトルだけを返してください。""")
            ])
            
            prompt = prompt_template.format_messages(
                theme=theme,
                max_length=max_length
            )
        
        # LLMを呼び出し
        response = llm.invoke(prompt)
        title = response.content.strip()
        
        # 引用符を削除
        title = title.strip('"').strip("'")
        
        # 最大文字数で切り詰め
        if len(title) > max_length:
            title = title[:max_length - 3] + "..."
        
        logger.info(f"LLMタイトル生成成功: {title}")
        return title
        
    except Exception as e:
        logger.error(f"LLMタイトル生成エラー: {e}", exc_info=True)
        # フォールバック: テーマから簡単なタイトルを生成
        return generate_title_fallback(theme, max_length)


def generate_title_fallback(theme: str, max_length: int = 50) -> str:
    """
    フォールバック: テーマから簡単なタイトルを生成
    
    Args:
        theme: 調査テーマ
        max_length: 最大文字数
    
    Returns:
        生成されたタイトル
    """
    # 「について調査してください」などの末尾を削除
    title = theme.replace("について調査してください", "")
    title = title.replace("について", "")
    title = title.strip()
    
    # 長い場合は切り詰める
    if len(title) > max_length:
        title = title[:max_length - 3] + "..."
    
    return title if title else theme[:max_length]

