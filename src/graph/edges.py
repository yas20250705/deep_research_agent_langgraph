"""
エッジ/ルーティング関数

グラフの条件分岐を実装
"""

import logging
from src.graph.state import ResearchState
from src.config.settings import Settings

logger = logging.getLogger(__name__)

def get_settings() -> Settings:
    """Settingsインスタンスを取得（遅延初期化）"""
    return Settings()


def route_supervisor(state: ResearchState) -> str:
    """
    Supervisorからのルーティング
    
    単純にnext_actionを返す
    
    Args:
        state: 現在のステート
    
    Returns:
        次のノード名
    """
    
    next_action = state.get("next_action", "research")
    logger.debug(f"Supervisorルーティング: {next_action}")
    return next_action


def route_reviewer(state: ResearchState) -> str:
    """
    Reviewerからのルーティング
    
    最大イテレーション確認を含む
    
    Args:
        state: 現在のステート
    
    Returns:
        次のノード名
    """
    
    # 最大イテレーション確認
    settings = get_settings()
    iteration_count = state.get("iteration_count", 0)
    if iteration_count >= settings.MAX_ITERATIONS:
        logger.warning(f"最大イテレーション到達: {iteration_count}")
        return "end"
    
    next_action = state.get("next_action", "research")
    logger.debug(f"Reviewerルーティング: {next_action}")
    return next_action

