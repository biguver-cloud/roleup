# AIとの会話処理を管理するファイル
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from prompts import build_roleplay_prompt, build_feedback_prompt

# AIモデルの設定
llm = ChatOpenAI(
    model="gpt-4o-mini",  # 使用するモデル
    temperature=0.7,       # 返答のランダム性（0〜1）高いほど多様な返答になる
)

# ロールプレイの返答を生成する関数
def get_roleplay_response(
    difficulty: str,
    scenario: str,
    conversation_history: list
) -> str:

    # システムプロンプトを組み立てる
    system_prompt = build_roleplay_prompt(difficulty, scenario)

    # AIに渡すメッセージを組み立てる
    messages = [SystemMessage(content=system_prompt)] + conversation_history

    # AIに投げて返答をもらう
    response = llm.invoke(messages)

    return response.content


# フィードバックを生成する関数
def get_feedback(conversation_history: list) -> str:

    # 会話履歴を一つの文字列にまとめる
    conversation_text = ""
    for message in conversation_history:
        if isinstance(message, HumanMessage):
            conversation_text += f"オペレーター：{message.content}\n"
        else:
            conversation_text += f"顧客：{message.content}\n"

    # フィードバック用プロンプトを組み立てる
    feedback_prompt = build_feedback_prompt(conversation_text)

    # AIにフィードバックを生成させる
    messages = [HumanMessage(content=feedback_prompt)]
    response = llm.invoke(messages)

    return response.content