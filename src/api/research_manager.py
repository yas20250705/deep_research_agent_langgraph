"""
リサーチ管理機能

リサーチの実行と状態管理を行う。
完了したリサーチはファイルに永続化し、サーバー再起動後も履歴から取得できるようにする。
"""

import json
import os
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from langchain_core.messages import HumanMessage
from src.graph.graph_builder import build_graph
from src.graph.state import ResearchState
from src.utils.checkpointer import create_checkpointer
from src.utils.logger import setup_logger
import logging

logger = setup_logger()


def _to_serializable(obj: Any) -> Any:
    """JSON 保存用に datetime 等を変換する（再帰）"""
    if obj is None:
        return None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_serializable(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if hasattr(obj, "model_dump"):
        return _to_serializable(obj.model_dump())
    raise TypeError(f"JSON にシリアライズできません: {type(obj)}")


def _serialize_result(result: Dict) -> Dict[str, Any]:
    """graph.invoke() の戻り値を JSON 保存用の辞書に変換する"""
    if result is None:
        return {}
    out = {}
    if result.get("task_plan") is not None:
        p = result["task_plan"]
        raw = p.model_dump() if hasattr(p, "model_dump") else p
        out["task_plan"] = _to_serializable(raw)
    else:
        out["task_plan"] = None
    out["current_draft"] = result.get("current_draft")
    out["iteration_count"] = result.get("iteration_count", 0)
    out["research_data"] = []
    for r in result.get("research_data", []) or []:
        raw = r.model_dump() if hasattr(r, "model_dump") else r
        out["research_data"].append(_to_serializable(raw) if isinstance(raw, dict) else raw)
    return out


def _deserialize_datetime(obj: Dict, *keys: str) -> None:
    """辞書内の ISO 日時文字列を datetime に復元する（in-place）"""
    for key in keys:
        if key in obj and obj[key] is not None and isinstance(obj[key], str):
            try:
                obj[key] = datetime.fromisoformat(obj[key].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass


class ResearchManager:
    """リサーチ管理クラス"""
    
    def __init__(self, persist_dir: Optional[str] = None):
        """初期化
        
        Args:
            persist_dir: 完了リサーチを保存するディレクトリ。None の場合は
                         プロジェクトルートの data/researches を使用（絶対パスに正規化）。
                         永続化データの保存先はここで固定。ダウンロード用MD/PDFの保存先は DOWNLOAD_SAVE_DIR で別設定。
        """
        self.researches: Dict[str, Dict] = {}
        self.graphs: Dict[str, any] = {}
        base = persist_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", "researches"
        )
        self._persist_dir = os.path.abspath(os.path.normpath(base))
        os.makedirs(self._persist_dir, exist_ok=True)
        logger.info(f"リサーチ永続化ディレクトリ: {self._persist_dir}")
    
    def create_research(
        self,
        theme: str,
        max_iterations: int = 5,
        enable_human_intervention: bool = False,
        checkpointer_type: str = "memory"
    ) -> str:
        """
        リサーチを作成して開始
        
        Args:
            theme: 調査テーマ
            max_iterations: 最大イテレーション数
            enable_human_intervention: 人間介入を有効化するか
            checkpointer_type: チェックポイントタイプ
        
        Returns:
            リサーチID
        """
        
        research_id = str(uuid.uuid4())
        
        # チェックポイント作成
        checkpointer = create_checkpointer(checkpointer_type)
        
        # グラフ構築
        interrupt_before = ["supervisor", "writer"] if enable_human_intervention else None
        graph = build_graph(
            checkpointer=checkpointer,
            interrupt_before=interrupt_before
        )
        
        # 初期ステート作成
        initial_state: ResearchState = {
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
        
        # 設定
        config = {
            "configurable": {
                "thread_id": research_id
            }
        }
        
        # リサーチ情報を保存
        self.researches[research_id] = {
            "research_id": research_id,
            "status": "started",
            "theme": theme,
            "max_iterations": max_iterations,
            "created_at": datetime.now(),
            "config": config,
            "enable_human_intervention": enable_human_intervention
        }
        
        self.graphs[research_id] = graph
        
        # 非同期で実行開始
        asyncio.create_task(self._run_research(research_id, initial_state, config))
        
        logger.info(f"リサーチを作成: research_id={research_id}, theme={theme}")
        
        return research_id
    
    async def _run_research(
        self,
        research_id: str,
        initial_state: ResearchState,
        config: Dict
    ):
        """
        リサーチを実行（非同期）
        
        Args:
            research_id: リサーチID
            initial_state: 初期ステート
            config: 設定
        """
        
        try:
            self.researches[research_id]["status"] = "processing"
            
            graph = self.graphs[research_id]
            
            # 実行
            result = graph.invoke(initial_state, config)
            
            # 結果を保存
            self.researches[research_id].update({
                "status": "completed",
                "result": result,
                "completed_at": datetime.now()
            })
            self._save_research(research_id)
            logger.info(f"リサーチ完了: research_id={research_id}")
            
        except Exception as e:
            logger.error(f"リサーチエラー: research_id={research_id}, error={e}", exc_info=True)
            self.researches[research_id].update({
                "status": "failed",
                "error": str(e)
            })
    
    def _save_research(self, research_id: str) -> None:
        """完了したリサーチをファイルに保存（サーバー再起動後も履歴から取得できるようにする）"""
        research = self.researches.get(research_id)
        if research is None or research.get("status") != "completed" or research.get("result") is None:
            return
        path = os.path.join(self._persist_dir, f"{research_id}.json")
        try:
            payload = {
                "research_id": research_id,
                "status": research["status"],
                "theme": research["theme"],
                "max_iterations": research.get("max_iterations"),
                "created_at": research["created_at"].isoformat() if research.get("created_at") else None,
                "completed_at": research.get("completed_at").isoformat() if research.get("completed_at") else None,
                "result": _serialize_result(research["result"]),
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            logger.info(f"リサーチを永続化しました: research_id={research_id}, path={path}")
        except Exception as e:
            logger.warning(f"リサーチの永続化に失敗: research_id={research_id}, path={path}, error={e}")

    def _load_research(self, research_id: str) -> Optional[Dict]:
        """永続化されたリサーチをファイルから読み込む"""
        path = os.path.join(self._persist_dir, f"{research_id}.json")
        if not os.path.isfile(path):
            logger.debug(f"永続化ファイルがありません: research_id={research_id}, path={path}")
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            _deserialize_datetime(data, "created_at", "completed_at")
            plan = (data.get("result") or {}).get("task_plan")
            if isinstance(plan, dict):
                _deserialize_datetime(plan, "created_at")
            logger.info(f"永続化からリサーチを読み込みました: research_id={research_id}")
            return data
        except json.JSONDecodeError as e:
            logger.warning(
                "永続化ファイルのJSONが不正です（破損または旧形式）: research_id=%s, path=%s, line=%s col=%s, error=%s",
                research_id, path, e.lineno, e.colno, e.msg
            )
            return None
        except Exception as e:
            logger.warning(f"リサーチの読み込みに失敗: research_id={research_id}, path={path}, error={e}")
            return None

    def list_persisted_researches(self) -> list:
        """
        永続化済みリサーチの一覧を返す（サーバー再起動後も履歴を復元するために使用）
        
        Returns:
            [{"research_id", "theme", "created_at", "completed_at", "status"}, ...]
        """
        result = []
        # メモリ上のリサーチを追加
        for rid, r in self.researches.items():
            result.append({
                "research_id": rid,
                "theme": r.get("theme", ""),
                "created_at": r.get("created_at"),
                "completed_at": r.get("completed_at"),
                "status": r.get("status", ""),
            })
        # 永続化ファイルから追加（メモリにないもののみ・メタ情報のみ読み込み）
        try:
            for name in os.listdir(self._persist_dir):
                if name.endswith(".json"):
                    rid = name[:-5]
                    if rid in self.researches:
                        continue
                    path = os.path.join(self._persist_dir, name)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        _deserialize_datetime(data, "created_at", "completed_at")
                        result.append({
                            "research_id": data.get("research_id", rid),
                            "theme": data.get("theme", ""),
                            "created_at": data.get("created_at"),
                            "completed_at": data.get("completed_at"),
                            "status": data.get("status", "completed"),
                        })
                    except json.JSONDecodeError:
                        logger.debug("永続化ファイルのJSONが不正のためスキップ: path=%s", path)
                    except Exception:
                        pass
        except OSError as e:
            logger.warning(f"永続化一覧の取得に失敗: {e}")
        result.sort(key=lambda x: (x.get("created_at") or datetime.min), reverse=True)
        return result
    def get_research(self, research_id: str) -> Optional[Dict]:
        """
        リサーチ情報を取得（メモリになければ永続化ファイルから読み込む）
        
        Args:
            research_id: リサーチID
        
        Returns:
            リサーチ情報、またはNone
        """
        research = self.researches.get(research_id)
        if research is not None:
            return research
        return self._load_research(research_id)
    
    def get_status(self, research_id: str) -> Optional[Dict]:
        """
        リサーチの状態を取得
        
        Args:
            research_id: リサーチID
        
        Returns:
            ステータス情報、またはNone
        """
        
        research = self.researches.get(research_id)
        if research is None:
            return None
        
        graph = self.graphs.get(research_id)
        if graph is None:
            return None
        
        # グラフの状態を取得
        state = graph.get_state(research["config"])
        
        return {
            "research_id": research_id,
            "status": research["status"],
            "state": state.values if state.values else None,
            "next": state.next if hasattr(state, 'next') else None
        }
    
    def resume_research(self, research_id: str, human_input: str) -> bool:
        """
        中断されたリサーチを再開
        
        Args:
            research_id: リサーチID
            human_input: 人間からの入力
        
        Returns:
            成功したかどうか
        """
        
        research = self.researches.get(research_id)
        if research is None:
            return False
        
        if not research.get("enable_human_intervention"):
            return False
        
        graph = self.graphs.get(research_id)
        if graph is None:
            return False
        
        try:
            # ステートを更新
            graph.update_state(research["config"], {"human_input": human_input})
            
            # 再開
            result = graph.invoke(None, research["config"])
            
            # 結果を保存
            research.update({
                "status": "processing",
                "result": result
            })
            
            logger.info(f"リサーチを再開: research_id={research_id}")
            return True
            
        except Exception as e:
            logger.error(f"リサーチ再開エラー: research_id={research_id}, error={e}")
            return False
    
    def delete_research(self, research_id: str) -> bool:
        """
        リサーチを削除
        
        Args:
            research_id: リサーチID
        
        Returns:
            成功したかどうか
        """
        
        if research_id in self.researches:
            del self.researches[research_id]
            if research_id in self.graphs:
                del self.graphs[research_id]
            logger.info(f"リサーチを削除: research_id={research_id}")
            return True
        return False


# グローバルインスタンス
research_manager = ResearchManager()










