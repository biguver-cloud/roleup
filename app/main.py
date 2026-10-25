import os
import logging
import httpx
import chainlit as cl

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")

logger = logging.getLogger(__name__)

TEMPORARY_ERROR_MESSAGE = "⚠️ 一時的なエラーが発生しました。時間をおいて再度お試しください。"
SESSION_EXPIRED_MESSAGE = "⚠️ セッションの有効期限が切れました。もう一度練習する場合はボタンを押してください。"


def restart_action() -> cl.Action:
    return cl.Action(name="restart", payload={}, label="もう一度練習する")


async def call_api(path: str, json: dict | None = None, timeout: float = 60.0, show_restart: bool = False) -> dict | None:
    """FastAPI を呼び出す。エラー時は案内メッセージを表示して None を返す"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{FASTAPI_URL}/api/v1{path}", json=json)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("API error: POST %s -> %s %s", path, e.response.status_code, e.response.text)
        if e.response.status_code == 404:
            # API 側のセッションが消えているため、ボタンから作り直してもらう
            cl.user_session.set("session_id", None)
            cl.user_session.set("scenario", None)
            await cl.Message(content=SESSION_EXPIRED_MESSAGE, actions=[restart_action()]).send()
            return None
    except httpx.RequestError as e:
        # タイムアウト・接続エラーなど
        logger.error("API request failed: POST %s -> %r", path, e)

    actions = [restart_action()] if show_restart else []
    await cl.Message(content=TEMPORARY_ERROR_MESSAGE, actions=actions).send()
    return None


async def create_session() -> bool:
    data = await call_api("/sessions", timeout=30.0, show_restart=True)
    if data is None:
        return False

    cl.user_session.set("session_id", data["session_id"])
    cl.user_session.set("scenario", None)
    cl.user_session.set("is_finished", False)
    return True


async def send_difficulty_selection(content: str):
    await cl.Message(
        content=content,
        actions=[
            cl.Action(name="difficulty", payload={"value": "初級"}, label="初級"),
            cl.Action(name="difficulty", payload={"value": "中級"}, label="中級"),
            cl.Action(name="difficulty", payload={"value": "上級"}, label="上級"),
        ]
    ).send()


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("session_id", None)

    if not await create_session():
        return

    await send_difficulty_selection("🎯 RoleUpへようこそ！\nまず難易度を選択してください。")


@cl.action_callback("restart")
async def on_restart(action: cl.Action):
    # セッションが消えている場合は作り直す
    # 残っている場合は /start で会話履歴が初期化されるため、既存の session_id をそのまま使う
    if cl.user_session.get("session_id") is None and not await create_session():
        return

    cl.user_session.set("is_finished", False)
    await send_difficulty_selection("難易度を選択してください。")


@cl.action_callback("difficulty")
async def on_difficulty_selected(action: cl.Action):
    value = action.payload["value"]
    cl.user_session.set("difficulty", value)

    await cl.Message(
        content=f"難易度「{value}」を選択しました！\n次にシナリオを選択してください。",
        actions=[
            cl.Action(name="scenario", payload={"value": "解約引き止め"}, label="解約引き止め"),
            cl.Action(name="scenario", payload={"value": "請求トラブル"}, label="請求トラブル"),
            cl.Action(name="scenario", payload={"value": "初歩的な使い方質問"}, label="初歩的な使い方質問"),
            cl.Action(name="scenario", payload={"value": "クレーム対応"}, label="クレーム対応"),
            cl.Action(name="scenario", payload={"value": "新規契約・CV獲得"}, label="新規契約・CV獲得"),
            cl.Action(name="scenario", payload={"value": "ランダム"}, label="ランダム"),
        ]
    ).send()


@cl.action_callback("scenario")
async def on_scenario_selected(action: cl.Action):
    value = action.payload["value"]
    difficulty = cl.user_session.get("difficulty")
    session_id = cl.user_session.get("session_id")

    await cl.Message(
        content=f"シナリオ「{value}」を選択しました！\nロールプレイを開始します。\n\n※「対応終了」と入力するとフィードバックを表示します。"
    ).send()

    data = await call_api(
        f"/sessions/{session_id}/start",
        json={"difficulty": difficulty, "scenario": value},
        show_restart=True,
    )
    if data is None:
        return

    # 開始に成功してからシナリオを確定する
    cl.user_session.set("scenario", value)
    cl.user_session.set("is_finished", False)

    await cl.Message(content=f"顧客：{data['first_message']}").send()


@cl.on_message
async def on_message(message: cl.Message):
    session_id = cl.user_session.get("session_id")
    scenario = cl.user_session.get("scenario")

    if cl.user_session.get("is_finished"):
        await cl.Message(
            content="ロールプレイは終了しました。もう一度練習する場合はボタンを押してください。",
            actions=[restart_action()],
        ).send()
        return

    if session_id is None:
        await cl.Message(
            content="⚠️ 有効なセッションがありません。もう一度練習する場合はボタンを押してください。",
            actions=[restart_action()],
        ).send()
        return

    if scenario is None:
        await cl.Message(content="まず難易度とシナリオを選択してください。").send()
        return

    if message.content == "対応終了":
        await cl.Message(content="ロールプレイを終了します。\nフィードバックを生成中...").send()

        # 失敗した場合は状態を変えないため、もう一度「対応終了」と入力すれば再試行できる
        data = await call_api(f"/sessions/{session_id}/feedback", timeout=120.0)
        if data is None:
            return

        # API側のセッションは非アクティブになるため、終了済みセッションへの送信(400)を防ぐ
        cl.user_session.set("scenario", None)
        cl.user_session.set("is_finished", True)

        await cl.Message(
            content=f"📊 フィードバック\n\n{data['feedback']}",
            actions=[restart_action()],
        ).send()
        return

    data = await call_api(
        f"/sessions/{session_id}/messages",
        json={"content": message.content},
    )
    if data is None:
        return

    await cl.Message(content=f"顧客：{data['message']}").send()
