# AIとの会話処理を管理するファイル
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from prompts import build_roleplay_prompt, build_feedback_prompt
from rag import build_vectorstore, search_knowledge

# アプリ起動時にベクトルDBを構築する
print("ベクトルDB構築中...")
vectorstore = build_vectorstore()
print("ベクトルDB構築完了！")

# AIモデルの設定
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
)

# ロールプレイの返答を生成する関数
def get_roleplay_response(
    difficulty: str,
    scenario: str,
    conversation_history: list
) -> str:

    # 直近のオペレーターの発言を取得（RAG検索用）
    query = ""
    for message in reversed(conversation_history):
        if isinstance(message, HumanMessage):
            query = message.content
            break

    # ナレッジを検索（発言がある場合のみ）
    knowledge = ""
    if query:
        knowledge = search_knowledge(vectorstore, query)

    # システムプロンプトを組み立てる
    system_prompt = build_roleplay_prompt(difficulty, scenario, knowledge)

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