import uuid
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

# セッション状態をメモリで管理（インスタンス内有効）
_sessions: dict[str, dict] = {}

router = APIRouter(prefix="/api/v1", tags=["roleplay"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/options", response_model=OptionsResponse)
async def get_options():
    return OptionsResponse(
        difficulties=list(DIFFICULTY_SETTINGS.keys()),
        scenarios=list(SCENARIO_SETTINGS.keys()),
    )


@router.post("/sessions", response_model=CreateSessionResponse, status_code=201)
async def create_session():
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "conversation_history": [],
        "difficulty": None,
        "scenario": None,
        "is_active": False,
    }
    return CreateSessionResponse(session_id=session_id)


@router.post("/sessions/{session_id}/start", response_model=StartRoleplayResponse)
async def start_roleplay(session_id: str, body: StartRoleplayRequest):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session["difficulty"] = body.difficulty
    session["scenario"] = body.scenario
    session["is_active"] = True
    session["conversation_history"] = []

    first_message = get_roleplay_response(body.difficulty, body.scenario, [])
    session["conversation_history"].append(AIMessage(content=first_message))

    return StartRoleplayResponse(session_id=session_id, first_message=first_message)


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(session_id: str, body: SendMessageRequest):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session["is_active"]:
        raise HTTPException(status_code=400, detail="Roleplay is not active. Call /start first.")

    history = session["conversation_history"]
    history.append(HumanMessage(content=body.content))

    response = get_roleplay_response(
        session["difficulty"],
        session["scenario"],
        history,
    )
    history.append(AIMessage(content=response))

    return SendMessageResponse(session_id=session_id, message=response)


@router.post("/sessions/{session_id}/feedback", response_model=FeedbackResponse)
async def get_session_feedback(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session["conversation_history"]:
        raise HTTPException(status_code=400, detail="No conversation history to evaluate.")

    session["is_active"] = False
    feedback = get_feedback(session["conversation_history"])

    return FeedbackResponse(session_id=session_id, feedback=feedback)
