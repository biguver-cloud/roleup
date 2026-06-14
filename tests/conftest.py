import sys
import os
import pytest
from unittest.mock import MagicMock

# app ディレクトリを Python のモジュール検索パスに追加
# （tests/ から見て ../app/ にある api.py などを import できるようにする）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

# ===== 外部依存のモック化（インポートより前に実行する必要がある） =====
#
# agent.py はインポートされた瞬間に以下の重い処理を実行する：
#   - OpenAI API への接続（ChatOpenAI の初期化）
#   - PDF を読み込んで FAISS のベクトルDBを構築
#
# テストでは本物の API を呼ばず、決まった値を返す「偽物（モック）」に差し替える。
# これにより API キーなしでも高速にテストできる。

_agent_mock = MagicMock()
_agent_mock.get_roleplay_response.return_value = "テスト用の顧客メッセージです。"
_agent_mock.get_feedback.return_value = "テスト用のフィードバックです。"

sys.modules['agent'] = _agent_mock


# ===== アプリ本体のインポート（モック化の後に行う） =====
from fastapi.testclient import TestClient  # noqa: E402
from api import app                         # noqa: E402
import api_routes                           # noqa: E402


# ===== フィクスチャ定義 =====
#
# フィクスチャとは「テストの事前準備・後片付けをまとめた部品」のこと。
# テスト関数の引数に書くと pytest が自動で注入してくれる。

@pytest.fixture(autouse=True)
def clear_sessions():
    """
    テストごとにセッションデータをリセットする。

    api_routes._sessions はモジュールレベルの dict なので、
    テストをまたいでデータが残り続ける。
    autouse=True にすると全テストで自動的に呼ばれる。
    """
    api_routes._sessions.clear()
    yield
    api_routes._sessions.clear()


@pytest.fixture
def client():
    """テスト用の HTTP クライアントを返す。"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def session_id(client):
    """セッションを作成して session_id を返す。"""
    resp = client.post("/api/v1/sessions")
    return resp.json()["session_id"]


@pytest.fixture
def started_session(client, session_id):
    """
    ロールプレイを開始済みのセッション ID を返す。

    /start を呼ぶことで is_active=True になり、
    /messages や /feedback を呼べる状態になる。
    """
    client.post(
        f"/api/v1/sessions/{session_id}/start",
        json={"difficulty": "初級", "scenario": "解約引き止め"},
    )
    return session_id
