# Chainlitのエントリーポイント
import chainlit as cl
from langchain_core.messages import HumanMessage, AIMessage
from agent import get_roleplay_response, get_feedback

# セッション開始時に呼ばれる処理
@cl.on_chat_start
async def on_chat_start():

    # 会話履歴をセッションに保存
    cl.user_session.set("conversation_history", [])
    cl.user_session.set("difficulty", None)
    cl.user_session.set("scenario", None)
    cl.user_session.set("is_roleplay_active", False)

    # 難易度選択のメッセージを表示
    await cl.Message(
        content="🎯 RoleUpへようこそ！\nまず難易度を選択してください。",
        actions=[
            cl.Action(name="difficulty", payload={"value": "初級"}, label="初級"),
            cl.Action(name="difficulty", payload={"value": "中級"}, label="中級"),
            cl.Action(name="difficulty", payload={"value": "上級"}, label="上級"),
        ]
    ).send()


# 難易度選択時の処理
@cl.action_callback("difficulty")
async def on_difficulty_selected(action: cl.Action):

    # 選択した難易度をセッションに保存
    value = action.payload["value"]
    cl.user_session.set("difficulty", value)

    # シナリオ選択のメッセージを表示
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


# シナリオ選択時の処理
@cl.action_callback("scenario")
async def on_scenario_selected(action: cl.Action):

    # 選択したシナリオをセッションに保存
    value = action.payload["value"]
    cl.user_session.set("scenario", value)
    cl.user_session.set("is_roleplay_active", True)

    difficulty = cl.user_session.get("difficulty")

    # ロールプレイ開始メッセージ
    await cl.Message(
        content=f"シナリオ「{value}」を選択しました！\nロールプレイを開始します。\n\n※「対応終了」と入力するとフィードバックを表示します。"
    ).send()

    # 顧客役AIの最初の一言を生成
    conversation_history = cl.user_session.get("conversation_history")
    first_message = get_roleplay_response(difficulty, value, conversation_history)

    # 顧客役AIの発言を履歴に追加
    conversation_history.append(AIMessage(content=first_message))
    cl.user_session.set("conversation_history", conversation_history)

    await cl.Message(content=f"顧客：{first_message}").send()


# メッセージ受信時の処理
@cl.on_message
async def on_message(message: cl.Message):

    is_roleplay_active = cl.user_session.get("is_roleplay_active")

    # ロールプレイが開始されていない場合
    if not is_roleplay_active:
        await cl.Message(content="まず難易度とシナリオを選択してください。").send()
        return

    # 「対応終了」と入力された場合
    if message.content == "対応終了":
        cl.user_session.set("is_roleplay_active", False)
        conversation_history = cl.user_session.get("conversation_history")

        await cl.Message(content="ロールプレイを終了します。\nフィードバックを生成中...").send()

        # フィードバックを生成
        feedback = get_feedback(conversation_history)
        await cl.Message(content=f"📊 フィードバック\n\n{feedback}").send()
        return

    # 通常のメッセージ処理
    conversation_history = cl.user_session.get("conversation_history")
    difficulty = cl.user_session.get("difficulty")
    scenario = cl.user_session.get("scenario")

    # オペレーターの発言を履歴に追加
    conversation_history.append(HumanMessage(content=message.content))

    # 顧客役AIの返答を生成
    response = get_roleplay_response(difficulty, scenario, conversation_history)

    # 顧客役AIの返答を履歴に追加
    conversation_history.append(AIMessage(content=response))
    cl.user_session.set("conversation_history", conversation_history)

    await cl.Message(content=f"顧客：{response}").send()