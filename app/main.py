import os
import httpx
import chainlit as cl

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")


@cl.on_chat_start
async def on_chat_start():
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{FASTAPI_URL}/api/v1/sessions")
        resp.raise_for_status()
        session_id = resp.json()["session_id"]

    cl.user_session.set("session_id", session_id)
    cl.user_session.set("scenario", None)

    await cl.Message(
        content="🎯 RoleUpへようこそ！\nまず難易度を選択してください。",
        actions=[
            cl.Action(name="difficulty", payload={"value": "初級"}, label="初級"),
            cl.Action(name="difficulty", payload={"value": "中級"}, label="中級"),
            cl.Action(name="difficulty", payload={"value": "上級"}, label="上級"),
        ]
    ).send()


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
        ]
    ).send()


@cl.action_callback("scenario")
async def on_scenario_selected(action: cl.Action):
    value = action.payload["value"]
    cl.user_session.set("scenario", value)

    difficulty = cl.user_session.get("difficulty")
    session_id = cl.user_session.get("session_id")

    await cl.Message(
        content=f"シナリオ「{value}」を選択しました！\nロールプレイを開始します。\n\n※「対応終了」と入力するとフィードバックを表示します。"
    ).send()

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{FASTAPI_URL}/api/v1/sessions/{session_id}/start",
            json={"difficulty": difficulty, "scenario": value}
        )
        resp.raise_for_status()
        first_message = resp.json()["first_message"]

    await cl.Message(content=f"顧客：{first_message}").send()


@cl.on_message
async def on_message(message: cl.Message):
    session_id = cl.user_session.get("session_id")
    scenario = cl.user_session.get("scenario")

    if scenario is None:
        await cl.Message(content="まず難易度とシナリオを選択してください。").send()
        return

    if message.content == "対応終了":
        await cl.Message(content="ロールプレイを終了します。\nフィードバックを生成中...").send()

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{FASTAPI_URL}/api/v1/sessions/{session_id}/feedback")
            resp.raise_for_status()
            feedback = resp.json()["feedback"]

        await cl.Message(content=f"📊 フィードバック\n\n{feedback}").send()
        return

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{FASTAPI_URL}/api/v1/sessions/{session_id}/messages",
            json={"content": message.content}
        )
        resp.raise_for_status()
        response = resp.json()["message"]

    await cl.Message(content=f"顧客：{response}").send()
