"""
並列処理ユーティリティ

複数のタスクを並列実行するためのユーティリティ
"""

import asyncio
from typing import List, Callable, TypeVar, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


async def run_parallel_async(
    tasks: List[Callable[[], T]],
    max_workers: Optional[int] = None
) -> List[T]:
    """
    非同期タスクを並列実行
    
    Args:
        tasks: 実行するタスクのリスト
        max_workers: 最大ワーカー数（Noneの場合は制限なし）
    
    Returns:
        結果のリスト（順序は保証されない）
    """
    if not tasks:
        return []
    
    # 非同期タスクとして実行
    async_tasks = [asyncio.to_thread(task) for task in tasks]
    results = await asyncio.gather(*async_tasks, return_exceptions=True)
    
    # エラーをログに記録
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"並列タスク {i} でエラーが発生: {result}")
    
    return results


def run_parallel_sync(
    tasks: List[Callable[[], T]],
    max_workers: Optional[int] = None
) -> List[T]:
    """
    同期タスクを並列実行（スレッドプール使用）
    
    Args:
        tasks: 実行するタスクのリスト
        max_workers: 最大ワーカー数（Noneの場合はCPU数）
    
    Returns:
        結果のリスト（順序は保証されない）
    """
    if not tasks:
        return []
    
    if max_workers is None:
        import os
        max_workers = min(len(tasks), os.cpu_count() or 1)
    
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # すべてのタスクを送信
        future_to_task = {executor.submit(task): i for i, task in enumerate(tasks)}
        
        # 完了したタスクから結果を取得
        for future in as_completed(future_to_task):
            task_index = future_to_task[future]
            try:
                result = future.result()
                results.append((task_index, result))
            except Exception as e:
                logger.error(f"並列タスク {task_index} でエラーが発生: {e}")
                results.append((task_index, None))
    
    # インデックス順にソート
    results.sort(key=lambda x: x[0])
    return [result for _, result in results]


async def run_with_timeout(
    coro: Callable[[], T],
    timeout: float,
    default: Optional[T] = None
) -> Optional[T]:
    """
    タイムアウト付きで非同期タスクを実行
    
    Args:
        coro: 実行するコルーチン
        timeout: タイムアウト（秒）
        default: タイムアウト時のデフォルト値
    
    Returns:
        結果、またはデフォルト値
    """
    try:
        return await asyncio.wait_for(coro(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"タスクがタイムアウトしました: {timeout}秒")
        return default
    except Exception as e:
        logger.error(f"タスク実行エラー: {e}")
        return default

