"""
使用例: LangGraph搭載 自律型リサーチエージェント

基本的な使用方法を示す例
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
# このファイルは examples/ ディレクトリにあるため、親ディレクトリを追加
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# .envファイルを読み込む（プロジェクトルートから）
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # .envファイルがない場合、親ディレクトリを探す
    parent_env = project_root.parent.parent.parent / "API.env"
    if parent_env.exists():
        load_dotenv(parent_env)

from langchain_core.messages import HumanMessage
from src.graph.graph_builder import build_graph
from src.graph.state import ResearchState
from src.utils.logger import setup_logger

# ロガー設定
logger = setup_logger()


def create_initial_state(theme: str) -> ResearchState:
    """
    初期ステートを作成
    
    Args:
        theme: 調査テーマ
    
    Returns:
        初期ステート
    """
    
    return {
        "messages": [HumanMessage(content=theme)],
        "task_plan": None,
        "research_data": [],
        "current_draft": None,
        "feedback": None,
        "iteration_count": 0,
        "next_action": "research",
        "human_input_required": False,
        "human_input": None
    }


def main():
    """メイン関数"""
    
    # 環境変数の確認
    if not os.getenv("OPENAI_API_KEY"):
        print("エラー: OPENAI_API_KEY環境変数が設定されていません")
        return
    
    if not os.getenv("TAVILY_API_KEY"):
        print("エラー: TAVILY_API_KEY環境変数が設定されていません")
        return
    
    # グラフを構築
    print("グラフを構築中...")
    graph = build_graph()
    
    # 初期ステートを作成
    theme = "LangGraphについて調査してください"
    initial_state = create_initial_state(theme)
    
    # 設定
    config = {
        "configurable": {
            "thread_id": "example-thread-1",
            "recursion_limit": 50  # 再帰制限を増やす（デフォルトは25）
        }
    }
    
    # 実行
    print(f"リサーチを開始: テーマ='{theme}'")
    print("=" * 50)
    
    try:
        result = graph.invoke(initial_state, config)
        
        print("\n" + "=" * 50)
        print("リサーチ完了!")
        print(f"イテレーション回数: {result['iteration_count']}")
        print(f"収集データ数: {len(result['research_data'])}")
        
        if result.get("current_draft"):
            print("\n" + "=" * 50)
            print("生成されたレポート:")
            print("=" * 50)
            print(result["current_draft"])
            
            # レポートをMarkdownファイルに保存
            output_dir = project_root / "output"
            output_dir.mkdir(exist_ok=True)
            
            # ファイル名を生成（テーマとタイムスタンプから）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_theme = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in theme[:30])
            filename = f"report_{safe_theme}_{timestamp}.md"
            filepath = output_dir / filename
            
            # レポートをMarkdown形式で構築
            markdown_content = f"""# {theme}

## レポート情報

- **作成日時**: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}
- **イテレーション回数**: {result['iteration_count']}
- **収集データ数**: {len(result['research_data'])}

## 調査計画

"""
            
            # 調査計画を追加
            if result.get("task_plan"):
                plan = result["task_plan"]
                markdown_content += f"**テーマ**: {plan.theme}\n\n"
                markdown_content += "**調査観点**:\n"
                for point in plan.investigation_points:
                    markdown_content += f"- {point}\n"
                markdown_content += "\n**検索クエリ**:\n"
                for query in plan.search_queries:
                    markdown_content += f"- {query}\n"
                markdown_content += "\n"
            
            # レポート本文を追加
            markdown_content += "---\n\n"
            markdown_content += result["current_draft"]
            
            # 参照ソースを追加
            if result.get("research_data"):
                markdown_content += "\n\n---\n\n## 参照ソース\n\n"
                for i, source in enumerate(result["research_data"], 1):
                    markdown_content += f"{i}. **{source.title}**\n"
                    markdown_content += f"   - URL: {source.url}\n"
                    if source.summary:
                        summary_preview = source.summary[:200] + "..." if len(source.summary) > 200 else source.summary
                        markdown_content += f"   - 要約: {summary_preview}\n"
                    if source.relevance_score is not None:
                        markdown_content += f"   - 関連性スコア: {source.relevance_score:.2f}\n"
                    markdown_content += "\n"
            
            # ファイルに書き込み
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            
            print(f"\nレポートを保存しました: {filepath}")
        else:
            print("\n警告: ドラフトが生成されませんでした")
        
    except Exception as e:
        logger.error(f"実行エラー: {e}", exc_info=True)
        print(f"\nエラーが発生しました: {e}")


if __name__ == "__main__":
    main()

