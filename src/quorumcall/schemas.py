from typing import Any
from pydantic import BaseModel


class AnswerValue(BaseModel):
    question_id: str
    value: Any


class SubmitRequest(BaseModel):
    answers: list[AnswerValue]
