"""
RoleUp API エンドポイントのテスト

【テストの基本的な考え方】
  テストは「正常に動くケース（正常系）」と「エラーになるケース（異常系）」の
  両方を確認するのが基本。

  FastAPI の TestClient を使うと、実際に HTTP サーバーを立てなくても
  リクエストを送ったのと同じ結果を得られる。

  外部 API（OpenAI）はモック（偽物）を使うので、
  API キーなしでも高速にテストを実行できる。

【ファイル構成】
  conftest.py  ← モック設定とフィクスチャ（事前準備の部品）を定義
  test_api_routes.py ← このファイル。各エンドポイントのテストケースを定義

【HTTP ステータスコードの基本】
  200: OK（正常に取得できた）
  201: Created（新しいリソースが作成された）
  400: Bad Request（リクエストの内容が不正）
  404: Not Found（指定したリソースが存在しない）
  422: Unprocessable Entity（バリデーションエラー。値の形式が間違っている）
"""

import uuid


# =============================================================================
# GET /api/v1/health
# =============================================================================
class TestHealth:
    """サーバーの死活確認エンドポイントのテスト"""

    def test_200と正常ステータスが返る(self, client):
        resp = client.get("/api/v1/health")

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# =============================================================================
# GET /api/v1/options
# =============================================================================
class TestOptions:
    """難易度・シナリオの選択肢取得エンドポイントのテスト"""

    def test_200とdifficultiesとscenariosが返る(self, client):
        resp = client.get("/api/v1/options")

        assert resp.status_code == 200
        data = resp.json()
        assert "difficulties" in data
        assert "scenarios" in data

    def test_難易度に初級中級上級が含まれる(self, client):
        resp = client.get("/api/v1/options")

        difficulties = resp.json()["difficulties"]
        assert "初級" in difficulties
        assert "中級" in difficulties
        assert "上級" in difficulties

    def test_シナリオに全5種類が含まれる(self, client):
        resp = client.get("/api/v1/options")

        scenarios = resp.json()["scenarios"]
        assert "解約引き止め" in scenarios
        assert "請求トラブル" in scenarios
        assert "初歩的な使い方質問" in scenarios
        assert "クレーム対応" in scenarios
        assert "新規契約・CV獲得" in scenarios


# =============================================================================
# POST /api/v1/sessions
# =============================================================================
class TestCreateSession:
    """セッション作成エンドポイントのテスト"""

    def test_201とsession_idが返る(self, client):
        resp = client.post("/api/v1/sessions")

        assert resp.status_code == 201
        assert "session_id" in resp.json()

    def test_session_idがUUID形式である(self, client):
        resp = client.post("/api/v1/sessions")

        session_id = resp.json()["session_id"]
        # uuid.UUID() は不正な文字列を渡すと ValueError を raise する
        # → 例外が起きなければ正しい UUID 形式と判定できる
        uuid.UUID(session_id)

    def test_リクエストのたびに異なるsession_idが返る(self, client):
        id1 = client.post("/api/v1/sessions").json()["session_id"]
        id2 = client.post("/api/v1/sessions").json()["session_id"]

        assert id1 != id2


# =============================================================================
# POST /api/v1/sessions/{session_id}/start
# =============================================================================
class TestStartRoleplay:
    """ロールプレイ開始エンドポイントのテスト"""

    def test_正常系_顧客の第一声が返る(self, client, session_id):
        resp = client.post(
            f"/api/v1/sessions/{session_id}/start",
            json={"difficulty": "初級", "scenario": "解約引き止め"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "first_message" in data
        assert data["first_message"] != ""

    def test_正常系_レスポンスにsession_idが含まれる(self, client, session_id):
        resp = client.post(
            f"/api/v1/sessions/{session_id}/start",
            json={"difficulty": "上級", "scenario": "クレーム対応"},
        )

        assert resp.json()["session_id"] == session_id

    def test_異常系_存在しないセッションIDでは404が返る(self, client):
        resp = client.post(
            "/api/v1/sessions/存在しないID/start",
            json={"difficulty": "初級", "scenario": "解約引き止め"},
        )

        assert resp.status_code == 404

    def test_異常系_無効な難易度では422が返る(self, client, session_id):
        # "超上級" は schemas.py の Difficulty 型に存在しないので、
        # FastAPI のバリデーションが弾いて 422 を返す
        resp = client.post(
            f"/api/v1/sessions/{session_id}/start",
            json={"difficulty": "超上級", "scenario": "解約引き止め"},
        )

        assert resp.status_code == 422

    def test_異常系_無効なシナリオでは422が返る(self, client, session_id):
        resp = client.post(
            f"/api/v1/sessions/{session_id}/start",
            json={"difficulty": "初級", "scenario": "存在しないシナリオ"},
        )

        assert resp.status_code == 422

    def test_異常系_リクエストボディが空では422が返る(self, client, session_id):
        resp = client.post(f"/api/v1/sessions/{session_id}/start", json={})

        assert resp.status_code == 422

    def test_正常系_ランダムシナリオで第一声が返る(self, client, session_id):
        resp = client.post(
            f"/api/v1/sessions/{session_id}/start",
            json={"difficulty": "初級", "scenario": "ランダム"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "first_message" in data
        assert data["first_message"] != ""


# =============================================================================
# POST /api/v1/sessions/{session_id}/messages
# =============================================================================
class TestSendMessage:
    """メッセージ送信エンドポイントのテスト"""

    def test_正常系_顧客の返答が返る(self, client, started_session):
        resp = client.post(
            f"/api/v1/sessions/{started_session}/messages",
            json={"content": "本日はお電話いただきありがとうございます。"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert data["message"] != ""

    def test_正常系_レスポンスにsession_idが含まれる(self, client, started_session):
        resp = client.post(
            f"/api/v1/sessions/{started_session}/messages",
            json={"content": "テストメッセージ"},
        )

        assert resp.json()["session_id"] == started_session

    def test_異常系_存在しないセッションIDでは404が返る(self, client):
        resp = client.post(
            "/api/v1/sessions/存在しないID/messages",
            json={"content": "テスト"},
        )

        assert resp.status_code == 404

    def test_異常系_startを呼ばずにメッセージを送ると400が返る(self, client, session_id):
        # セッションは作ったが /start をまだ呼んでいない（is_active=False）状態
        resp = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"content": "テスト"},
        )

        assert resp.status_code == 400

    def test_異常系_contentがないリクエストでは422が返る(self, client, started_session):
        resp = client.post(
            f"/api/v1/sessions/{started_session}/messages",
            json={},
        )

        assert resp.status_code == 422


# =============================================================================
# POST /api/v1/sessions/{session_id}/feedback
# =============================================================================
class TestFeedback:
    """フィードバック取得エンドポイントのテスト"""

    def test_正常系_フィードバックが返る(self, client, started_session):
        # メッセージを1件やり取りしてからフィードバックを取得
        client.post(
            f"/api/v1/sessions/{started_session}/messages",
            json={"content": "ご不満をおかけして大変申し訳ございません。"},
        )
        resp = client.post(f"/api/v1/sessions/{started_session}/feedback")

        assert resp.status_code == 200
        data = resp.json()
        assert "feedback" in data
        assert data["feedback"] != ""

    def test_正常系_startだけでもフィードバックが取得できる(self, client, started_session):
        # /start を呼ぶと AI の第一声が会話履歴に追加されるため、
        # メッセージを送らなくてもフィードバックは取得できる
        resp = client.post(f"/api/v1/sessions/{started_session}/feedback")

        assert resp.status_code == 200

    def test_正常系_フィードバック後はセッションが非アクティブになる(self, client, started_session):
        client.post(f"/api/v1/sessions/{started_session}/feedback")

        # フィードバック取得後は is_active=False になるので、
        # メッセージを送ると 400 が返るはず
        resp = client.post(
            f"/api/v1/sessions/{started_session}/messages",
            json={"content": "追加メッセージ"},
        )
        assert resp.status_code == 400

    def test_異常系_存在しないセッションIDでは404が返る(self, client):
        resp = client.post("/api/v1/sessions/存在しないID/feedback")

        assert resp.status_code == 404

    def test_異常系_会話履歴がない場合は400が返る(self, client, session_id):
        # /sessions だけ作って /start を呼んでいない状態
        # → conversation_history が空なので 400 になる
        resp = client.post(f"/api/v1/sessions/{session_id}/feedback")

        assert resp.status_code == 400
