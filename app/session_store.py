# セッション（難易度・シナリオ・会話履歴・進行状態）の保存先を管理するファイル
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

# 最後に更新してからこの時間が経ったセッションは削除する
SESSION_TTL = timedelta(hours=float(os.getenv("SESSION_TTL_HOURS", "24")))


# ===== 会話履歴の変換 =====
# LangChain のメッセージはそのまま保存できないため、{"role", "content"} の dict に変換する

def serialize_history(history: list[BaseMessage]) -> list[dict]:
    return [
        {"role": "human" if isinstance(m, HumanMessage) else "ai", "content": m.content}
        for m in history
    ]


def deserialize_history(items: list[dict]) -> list[BaseMessage]:
    return [
        HumanMessage(content=item["content"]) if item["role"] == "human" else AIMessage(content=item["content"])
        for item in items
    ]


def _to_record(session: dict, now: datetime) -> dict:
    return {
        "difficulty": session["difficulty"],
        "scenario": session["scenario"],
        "is_active": session["is_active"],
        "conversation_history": serialize_history(session["conversation_history"]),
        "updated_at": now,
        "expires_at": now + SESSION_TTL,
    }


def _from_record(record: dict) -> dict:
    return {
        "difficulty": record["difficulty"],
        "scenario": record["scenario"],
        "is_active": record["is_active"],
        "conversation_history": deserialize_history(record["conversation_history"]),
    }


def new_session() -> dict:
    return {
        "conversation_history": [],
        "difficulty": None,
        "scenario": None,
        "is_active": False,
    }


# ===== ストア =====

class SessionStore(ABC):
    @abstractmethod
    async def get(self, session_id: str) -> dict | None:
        """セッションを取得する。存在しない・期限切れの場合は None を返す"""

    @abstractmethod
    async def save(self, session_id: str, session: dict) -> None:
        """セッションを保存し、有効期限を延長する"""


class InMemorySessionStore(SessionStore):
    """プロセス内のメモリに保存する（ローカル開発・テスト用）"""

    def __init__(self):
        self._records: dict[str, dict] = {}

    async def get(self, session_id: str) -> dict | None:
        record = self._records.get(session_id)
        if record is None:
            return None
        if record["expires_at"] <= datetime.now(timezone.utc):
            del self._records[session_id]
            return None
        return _from_record(record)

    async def save(self, session_id: str, session: dict) -> None:
        now = datetime.now(timezone.utc)
        self._purge_expired(now)
        self._records[session_id] = _to_record(session, now)

    def _purge_expired(self, now: datetime) -> None:
        # 期限切れのセッションを削除し、メモリが増え続けないようにする
        expired = [sid for sid, r in self._records.items() if r["expires_at"] <= now]
        for sid in expired:
            del self._records[sid]


class FirestoreSessionStore(SessionStore):
    """Firestore に保存する（Cloud Run 用）

    期限切れのドキュメントは、expires_at フィールドに設定した TTL ポリシーで Firestore が自動削除する。
    TTL による削除は即時ではないため、取得時にも有効期限を確認する。
    """

    def __init__(self, collection: str = "sessions"):
        # Firestore を使わない環境（テストなど）で読み込まずに済むよう、ここで import する
        from google.cloud import firestore

        self._collection = firestore.AsyncClient().collection(collection)

    async def get(self, session_id: str) -> dict | None:
        snapshot = await self._collection.document(session_id).get()
        if not snapshot.exists:
            return None
        record = snapshot.to_dict()
        if record["expires_at"] <= datetime.now(timezone.utc):
            return None
        return _from_record(record)

    async def save(self, session_id: str, session: dict) -> None:
        now = datetime.now(timezone.utc)
        await self._collection.document(session_id).set(_to_record(session, now))


def create_session_store() -> SessionStore:
    """環境変数 SESSION_STORE（memory / firestore）に応じてストアを作る"""
    kind = os.getenv("SESSION_STORE", "memory")
    if kind == "memory":
        return InMemorySessionStore()
    if kind == "firestore":
        return FirestoreSessionStore(os.getenv("FIRESTORE_COLLECTION", "sessions"))
    raise ValueError(f"Unknown SESSION_STORE: {kind}")
