from typing import Any
from pydantic import BaseModel, Field


class AnswerValue(BaseModel):
    question_id: str
    value: Any


class SubmitRequest(BaseModel):
    # Cap the answer count so a single submission can't carry an unbounded list;
    # the overall body size is bounded by the middleware in main.py.
    answers: list[AnswerValue] = Field(max_length=1000)
