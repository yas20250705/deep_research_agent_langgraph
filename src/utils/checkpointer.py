"""
チェックポイント機能

グラフの実行状態を永続化し、後から復元できるようにする機能
"""

from typing import Optional, Dict, Any
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver
import logging
from src.config.settings import Settings
from src.graph.state import ResearchState

# redisはオプション
try:
    import redis
except ImportError:
    redis = None

# RedisCheckpointerはオプション（LangGraphのバージョンによっては利用できない）
try:
    from langgraph.checkpoint.redis import RedisCheckpointer
    REDIS_CHECKPOINTER_AVAILABLE = True
except ImportError:
    REDIS_CHECKPOINTER_AVAILABLE = False
    RedisCheckpointer = None

logger = logging.getLogger(__name__)


def create_checkpointer(
    checkpointer_type: str = "memory",
    redis_config: Optional[Dict] = None
) -> BaseCheckpointSaver:
    """
    チェックポインターを作成
    
    Args:
        checkpointer_type: "memory" または "redis"
        redis_config: Redis設定（redis使用時）
    
    Returns:
        Checkpointerインスタンス
    
    Raises:
        ValueError: 無効なcheckpointer_typeの場合
    """
    
    if checkpointer_type == "memory":
        logger.info("MemorySaverチェックポイントを作成")
        return MemorySaver()
    
    elif checkpointer_type == "redis":
        if redis is None:
            logger.warning("redisライブラリがインストールされていません。MemorySaverを使用します")
            return MemorySaver()
        
        if not REDIS_CHECKPOINTER_AVAILABLE:
            logger.warning(
                "langgraph.checkpoint.redisが利用できません。"
                "LangGraphのバージョンを確認してください。MemorySaverを使用します"
            )
            return MemorySaver()
        
        if redis_config is None:
            settings = Settings()
            redis_config = {
                "host": settings.REDIS_HOST,
                "port": settings.REDIS_PORT,
                "db": settings.REDIS_DB
            }
        
        try:
            redis_client = redis.Redis(**redis_config)
            # 接続テスト
            redis_client.ping()
            
            # RedisCheckpointerを作成
            logger.info(f"RedisCheckpointerを作成: {redis_config}")
            checkpointer = RedisCheckpointer(redis_client)
            logger.info("RedisCheckpointerの作成に成功しました")
            return checkpointer
            
        except redis.ConnectionError as e:
            logger.error(f"Redis接続エラー: {e}")
            logger.warning("MemorySaverにフォールバックします")
            return MemorySaver()
        except Exception as e:
            logger.error(f"RedisCheckpointer作成エラー: {e}")
            logger.warning("MemorySaverにフォールバックします")
            return MemorySaver()
    
    else:
        raise ValueError(f"Unknown checkpointer type: {checkpointer_type}")


def save_checkpoint(
    graph: Any,  # CompiledGraph
    config: Dict,
    state: ResearchState
) -> None:
    """
    チェックポイントを保存（明示的）
    
    通常はLangGraphが自動的に保存するが、
    重要なポイントで明示的に保存することも可能
    
    Args:
        graph: コンパイル済みグラフ
        config: 設定
        state: ステート
    """
    
    try:
        graph.update_state(config, state)
        logger.debug("チェックポイントを明示的に保存しました")
    except Exception as e:
        logger.error(f"チェックポイント保存エラー: {e}")


def load_checkpoint(
    graph: Any,  # CompiledGraph
    config: Dict
) -> Optional[ResearchState]:
    """
    チェックポイントから状態を復元
    
    Args:
        graph: コンパイル済みグラフ
        config: 設定
    
    Returns:
        復元されたステート、またはNone
    """
    
    try:
        state = graph.get_state(config)
        if state.values:
            logger.info("チェックポイントから状態を復元しました")
            return state.values
        return None
    except Exception as e:
        logger.error(f"チェックポイント復元エラー: {e}")
        return None

