import uuid
import random
from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, AIMessage

from schemas import (
    CreateSessionResponse,
    StartRoleplayRequest,
    StartRoleplayResponse,
    SendMessageRequest,
    SendMessageResponse,
    FeedbackResponse,
    OptionsResponse,
)
from agent import get_roleplay_response, get_feedback
from prompts import DIFFICULTY_SETTINGS, SCENARIO_SETTINGS
from session_store import create_session_store, new_session

# セッションの保存先（環境変数 SESSION_STORE で memory / firestore を切り替える）
session_store = create_session_store()

router = APIRouter(prefix="/api/v1", tags=["roleplay"])


async def _get_session_or_404(session_id: str) -> dict:
    session = await session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/options", response_model=OptionsResponse)
async def get_options():
    return OptionsResponse(
        difficulties=list(DIFFICULTY_SETTINGS.keys()),
        scenarios=list(SCENARIO_SETTINGS.keys()) + ["ランダム"],
    )


@router.post("/sessions", response_model=CreateSessionResponse, status_code=201)
async def create_session():
    session_id = str(uuid.uuid4())
    await session_store.save(session_id, new_session())
    return CreateSessionResponse(session_id=session_id)


@router.post("/sessions/{session_id}/start", response_model=StartRoleplayResponse)
async def start_roleplay(session_id: str, body: StartRoleplayRequest):
    session = await _get_session_or_404(session_id)

    scenario = (
        random.choice(list(SCENARIO_SETTINGS.keys()))
        if body.scenario == "ランダム"
        else body.scenario
    )

    # 応答生成に失敗した場合にセッションを中途半端な状態にしないよう、成功後に更新する
    first_message = get_roleplay_response(body.difficulty, scenario, [])

    session["difficulty"] = body.difficulty
    session["scenario"] = scenario
    session["is_active"] = True
    session["conversation_history"] = [AIMessage(content=first_message)]
    await session_store.save(session_id, session)

    return StartRoleplayResponse(session_id=session_id, first_message=first_message)


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(session_id: str, body: SendMessageRequest):
    session = await _get_session_or_404(session_id)
    if not session["is_active"]:
        raise HTTPException(status_code=400, detail="Roleplay is not active. Call /start first.")

    # 応答生成に失敗した場合は履歴に残さず、同じメッセージを再送できるようにする
    user_message = HumanMessage(content=body.content)
    response = get_roleplay_response(
        session["difficulty"],
        session["scenario"],
        session["conversation_history"] + [user_message],
    )
    session["conversation_history"] += [user_message, AIMessage(content=response)]
    await session_store.save(session_id, session)

    return SendMessageResponse(session_id=session_id, message=response)


@router.post("/sessions/{session_id}/feedback", response_model=FeedbackResponse)
async def get_session_feedback(session_id: str):
    session = await _get_session_or_404(session_id)
    if not session["conversation_history"]:
        raise HTTPException(status_code=400, detail="No conversation history to evaluate.")

    # 生成に失敗した場合はロールプレイを続行できるよう、成功後に非アクティブにする
    feedback = get_feedback(session["conversation_history"])
    session["is_active"] = False
    await session_store.save(session_id, session)

    return FeedbackResponse(session_id=session_id, feedback=feedback)
