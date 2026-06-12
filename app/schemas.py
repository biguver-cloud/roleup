from pydantic import BaseModel
from typing import Literal

Difficulty = Literal["初級", "中級", "上級"]
Scenario = Literal["解約引き止め", "請求トラブル", "初歩的な使い方質問", "クレーム対応", "新規契約・CV獲得"]


class CreateSessionResponse(BaseModel):
    session_id: str


class StartRoleplayRequest(BaseModel):
    difficulty: Difficulty
    scenario: Scenario


class StartRoleplayResponse(BaseModel):
    session_id: str
    first_message: str


class SendMessageRequest(BaseModel):
    content: str


class SendMessageResponse(BaseModel):
    session_id: str
    message: str


class FeedbackResponse(BaseModel):
    session_id: str
    feedback: str


class OptionsResponse(BaseModel):
    difficulties: list[str]
    scenarios: list[str]
