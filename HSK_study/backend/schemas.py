"""Pydantic request models for the REST API."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ProgressStatus(str, Enum):
    new = "new"
    learning = "learning"
    review = "review"
    mastered = "mastered"


class FlashcardResult(str, Enum):
    forgot = "forgot"
    hard = "hard"
    remembered = "remembered"


class MatchingMode(str, Enum):
    meaning = "meaning"
    pinyin = "pinyin"


class HskLevel(str, Enum):
    l1 = "1"
    l2 = "2"
    l3 = "3"
    l4 = "4"
    l5 = "5"
    l6 = "6"
    l7_9 = "7-9"


class QuestionType(str, Enum):
    mcq_meaning = "mcq_meaning"
    mcq_hanzi = "mcq_hanzi"
    mcq_pinyin = "mcq_pinyin"
    mcq_audio = "mcq_audio"


class ListeningMode(str, Enum):
    audio_to_meaning = "audio_to_meaning"
    audio_to_hanzi = "audio_to_hanzi"


class FlashcardSessionCreate(BaseModel):
    count: int = Field(default=10, ge=1, le=30)
    include_mastered: bool = False


class FlashcardReviewCreate(BaseModel):
    session_id: int = Field(gt=0)
    vocabulary_id: int = Field(gt=0)
    result: FlashcardResult


class SessionComplete(BaseModel):
    total_items: int = Field(ge=0)
    correct_items: int = Field(ge=0)
    incorrect_items: int = Field(ge=0)


class MatchingSessionCreate(BaseModel):
    mode: MatchingMode = MatchingMode.meaning
    count: int = Field(default=6, ge=2, le=10)


class MatchingAttemptCreate(BaseModel):
    session_id: int = Field(gt=0)
    vocabulary_id: int = Field(gt=0)
    mode: MatchingMode
    is_correct: bool


class ProgressStatusUpdate(BaseModel):
    vocabulary_id: int = Field(gt=0)
    status: ProgressStatus


class SentenceSessionCreate(BaseModel):
    count: int = Field(default=10, ge=1, le=20)
    topic: str | None = Field(default=None, max_length=80)


class SentenceAttemptCreate(BaseModel):
    session_id: int = Field(gt=0)
    sentence_id: int = Field(gt=0)
    ordered_positions: list[int] = Field(min_length=1, max_length=20)


class QuizSessionCreate(BaseModel):
    hsk_level: HskLevel | None = None
    question_types: list[QuestionType] = Field(default_factory=list)
    count: int = Field(default=10, ge=1, le=50)


class QuizAttemptCreate(BaseModel):
    session_id: int = Field(gt=0)
    vocabulary_id: int = Field(gt=0)
    question_type: QuestionType
    is_correct: bool


class ListeningSessionCreate(BaseModel):
    hsk_level: HskLevel | None = None
    mode: ListeningMode = ListeningMode.audio_to_meaning
    count: int = Field(default=10, ge=1, le=30)


class ListeningAttemptCreate(BaseModel):
    session_id: int = Field(gt=0)
    vocabulary_id: int = Field(gt=0)
    mode: ListeningMode
    is_correct: bool


class WritingSessionCreate(BaseModel):
    hsk_level: HskLevel | None = None
    count: int = Field(default=10, ge=1, le=30)


class WritingAttemptCreate(BaseModel):
    session_id: int = Field(gt=0)
    character: str = Field(min_length=1, max_length=4)
    mistakes: int = Field(default=0, ge=0)
    is_correct: bool

