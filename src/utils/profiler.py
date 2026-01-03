"""
プロファイリングユーティリティ

パフォーマンス測定とボトルネック特定のためのツール
"""

import time
import functools
import cProfile
import pstats
import io
from typing import Callable, TypeVar, Any, Dict
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class PerformanceProfiler:
    """パフォーマンスプロファイラー"""
    
    def __init__(self):
        self.profiler = cProfile.Profile()
        self.stats: Dict[str, float] = {}
    
    def start(self):
        """プロファイリングを開始"""
        self.profiler.enable()
    
    def stop(self):
        """プロファイリングを停止"""
        self.profiler.disable()
    
    def get_stats(self) -> str:
        """統計情報を取得"""
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(20)  # 上位20件
        return s.getvalue()
    
    def get_summary(self) -> Dict[str, Any]:
        """サマリー情報を取得"""
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s)
        ps.print_stats()
        
        # 統計情報を解析
        total_time = ps.total_tt
        total_calls = ps.total_calls
        
        return {
            "total_time": total_time,
            "total_calls": total_calls,
            "average_time_per_call": total_time / total_calls if total_calls > 0 else 0
        }


def profile_function(func: Callable[..., T]) -> Callable[..., T]:
    """
    関数の実行時間を測定するデコレータ
    
    Usage:
        @profile_function
        def my_function():
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"{func.__name__} 実行時間: {elapsed_time:.3f}秒")
    
    return wrapper


def measure_time(func: Callable[..., T]) -> Callable[..., T]:
    """
    関数の実行時間を測定し、結果を返すデコレータ
    
    Usage:
        @measure_time
        def my_function():
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed_time = time.perf_counter() - start_time
            logger.debug(f"{func.__name__} 実行時間: {elapsed_time:.6f}秒")
    
    return wrapper


class Timer:
    """コンテキストマネージャーとして使用できるタイマー"""
    
    def __init__(self, name: str = "Timer"):
        self.name = name
        self.start_time = None
        self.elapsed_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed_time = time.perf_counter() - self.start_time
        logger.info(f"{self.name} 実行時間: {self.elapsed_time:.6f}秒")
        return False
    
    def get_elapsed(self) -> float:
        """経過時間を取得"""
        if self.elapsed_time is None:
            return time.perf_counter() - self.start_time
        return self.elapsed_time

