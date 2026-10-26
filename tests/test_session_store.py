"""
セッションの保存先（session_store.py）のテスト

Firestore には実際に接続せず、Firestore クライアントの「偽物」を使って確認する。
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from google.cloud import firestore
from langchain_core.messages import AIMessage, HumanMessage

import session_store
from session_store import (
    FirestoreSessionStore,
    InMemorySessionStore,
    create_session_store,
    deserialize_history,
    new_session,
    serialize_history,
)


def _started_session() -> dict:
    session = new_session()
    session.update(
        difficulty="初級",
        scenario="解約引き止め",
        is_active=True,
        conversation_history=[AIMessage(content="解約したいのですが"), HumanMessage(content="承知いたしました")],
    )
    return session


def _expire_immediately(monkeypatch):
    """保存した直後に期限切れになるよう、有効期限を過去にする"""
    monkeypatch.setattr(session_store, "SESSION_TTL", timedelta(seconds=-1))


# ===== Firestore クライアントの偽物 =====
# 本物と同じく、コレクションの中身をクライアント同士で共有する（= 共有のデータベース）

class _FakeSnapshot:
    def __init__(self, data):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data)


class _FakeDocument:
    def __init__(self, docs, doc_id):
        self._docs, self._id = docs, doc_id

    async def get(self):
        return _FakeSnapshot(self._docs.get(self._id))

    async def set(self, data):
        self._docs[self._id] = dict(data)


class _FakeCollection:
    def __init__(self, docs):
        self._docs = docs

    def document(self, doc_id):
        return _FakeDocument(self._docs, doc_id)


@pytest.fixture
def fake_firestore(monkeypatch):
    database: dict[str, dict] = {}

    class FakeAsyncClient:
        def collection(self, name):
            return _FakeCollection(database.setdefault(name, {}))

    monkeypatch.setattr(firestore, "AsyncClient", FakeAsyncClient)
    return database


# =============================================================================
# 会話履歴の変換
# =============================================================================
class TestSerialize:

    def test_会話履歴をdictに変換して元に戻せる(self):
        history = [AIMessage(content="こんにちは"), HumanMessage(content="お電話ありがとうございます")]

        items = serialize_history(history)

        assert items == [
            {"role": "ai", "content": "こんにちは"},
            {"role": "human", "content": "お電話ありがとうございます"},
        ]
        assert deserialize_history(items) == history


# =============================================================================
# InMemorySessionStore
# =============================================================================
class TestInMemorySessionStore:

    def test_保存したセッションを取得できる(self):
        store = InMemorySessionStore()
        asyncio.run(store.save("abc", _started_session()))

        assert asyncio.run(store.get("abc")) == _started_session()

    def test_存在しないセッションはNoneになる(self):
        assert asyncio.run(InMemorySessionStore().get("存在しないID")) is None

    def test_取得したセッションを変更しても保存しなければ反映されない(self):
        store = InMemorySessionStore()
        asyncio.run(store.save("abc", _started_session()))

        session = asyncio.run(store.get("abc"))
        session["is_active"] = False

        assert asyncio.run(store.get("abc"))["is_active"] is True

    def test_期限切れのセッションはNoneになる(self, monkeypatch):
        _expire_immediately(monkeypatch)
        store = InMemorySessionStore()
        asyncio.run(store.save("abc", _started_session()))

        assert asyncio.run(store.get("abc")) is None

    def test_保存時に期限切れのセッションが削除される(self, monkeypatch):
        store = InMemorySessionStore()
        with monkeypatch.context() as m:
            _expire_immediately(m)
            asyncio.run(store.save("old", _started_session()))

        asyncio.run(store.save("new", _started_session()))

        assert set(store._records) == {"new"}


# =============================================================================
# FirestoreSessionStore
# =============================================================================
class TestFirestoreSessionStore:

    def test_保存したセッションを取得できる(self, fake_firestore):
        store = FirestoreSessionStore()
        asyncio.run(store.save("abc", _started_session()))

        assert asyncio.run(store.get("abc")) == _started_session()

    def test_有効期限と更新日時を保存する(self, fake_firestore):
        before = datetime.now(timezone.utc)
        asyncio.run(FirestoreSessionStore().save("abc", _started_session()))

        record = fake_firestore["sessions"]["abc"]
        assert record["updated_at"] >= before
        assert record["expires_at"] == record["updated_at"] + session_store.SESSION_TTL

    def test_別のインスタンスで保存したセッションを取得できる(self, fake_firestore):
        # Cloud Run のインスタンスが別々でも、同じ Firestore を見ていれば続きができる
        asyncio.run(FirestoreSessionStore().save("abc", _started_session()))

        assert asyncio.run(FirestoreSessionStore().get("abc")) == _started_session()

    def test_存在しないセッションはNoneになる(self, fake_firestore):
        assert asyncio.run(FirestoreSessionStore().get("存在しないID")) is None

    def test_TTLで削除される前でも期限切れならNoneになる(self, fake_firestore, monkeypatch):
        _expire_immediately(monkeypatch)
        store = FirestoreSessionStore()
        asyncio.run(store.save("abc", _started_session()))

        assert asyncio.run(store.get("abc")) is None


# =============================================================================
# create_session_store
# =============================================================================
class TestCreateSessionStore:

    def test_未設定ならインメモリになる(self, monkeypatch):
        monkeypatch.delenv("SESSION_STORE", raising=False)

        assert isinstance(create_session_store(), InMemorySessionStore)

    def test_firestoreを指定するとFirestoreになる(self, monkeypatch, fake_firestore):
        monkeypatch.setenv("SESSION_STORE", "firestore")

        assert isinstance(create_session_store(), FirestoreSessionStore)

    def test_不明な値ではエラーになる(self, monkeypatch):
        monkeypatch.setenv("SESSION_STORE", "unknown")

        with pytest.raises(ValueError):
            create_session_store()
