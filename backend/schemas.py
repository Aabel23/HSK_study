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
    # The ceiling is generous on purpose: a long unbroken run (100 cards or
    # more) is a study style people ask for, and the session only ever holds as
    # many cards as the filtered pool actually contains.
    count: int = Field(default=10, ge=1, le=200)
    include_mastered: bool = False
    hsk_level: HskLevel | None = None


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
    count: int = Field(default=10, ge=1, le=200)
    topic: str | None = Field(default=None, max_length=80)
    hsk_level: HskLevel | None = None
    max_tokens: int | None = Field(default=None, ge=2, le=30)


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


class ReviewRating(str, Enum):
    again = "again"
    hard = "hard"
    good = "good"
    easy = "easy"


class ReviewSubmit(BaseModel):
    vocabulary_id: int = Field(gt=0)
    rating: ReviewRating
    source: str = Field(default="review", max_length=32)


class FavoriteUpdate(BaseModel):
    vocabulary_id: int = Field(gt=0)
    is_favorite: bool


class NoteUpdate(BaseModel):
    vocabulary_id: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=2000)


class SettingsUpdate(BaseModel):
    """Partial settings patch; unknown keys are rejected by the service."""

    model_config = {"extra": "allow"}


class BackupImport(BaseModel):
    model_config = {"extra": "allow"}

    format: str = Field(max_length=64)
    backup_version: int = Field(default=1, ge=1)


class TypingMode(str, Enum):
    hanzi_to_pinyin = "hanzi_to_pinyin"
    audio_to_pinyin = "audio_to_pinyin"
    meaning_to_pinyin = "meaning_to_pinyin"
    audio_to_hanzi = "audio_to_hanzi"
    meaning_to_hanzi = "meaning_to_hanzi"


class TypingSessionCreate(BaseModel):
    hsk_level: HskLevel | None = None
    mode: TypingMode = TypingMode.hanzi_to_pinyin
    count: int = Field(default=10, ge=1, le=50)
    only_due: bool = False


class TypingAnswerCheck(BaseModel):
    session_id: int | None = Field(default=None, gt=0)
    vocabulary_id: int = Field(gt=0)
    mode: TypingMode
    answer: str = Field(default="", max_length=200)


class DictationMode(str, Enum):
    word_pinyin = "word_pinyin"
    word_hanzi = "word_hanzi"
    sentence_hanzi = "sentence_hanzi"


class DictationSessionCreate(BaseModel):
    hsk_level: HskLevel | None = None
    mode: DictationMode = DictationMode.word_pinyin
    count: int = Field(default=10, ge=1, le=50)


class DictationAnswerCheck(BaseModel):
    session_id: int | None = Field(default=None, gt=0)
    target_id: int = Field(gt=0)
    mode: DictationMode
    answer: str = Field(default="", max_length=500)
    replays: int = Field(default=0, ge=0, le=99)


class DonationCreate(BaseModel):
    # The real bounds live in Settings so they stay configurable; these are the
    # outer limits PayOS itself accepts.
    amount: int = Field(ge=1_000, le=500_000_000)
    message: str = Field(default="", max_length=200)
    donor_name: str = Field(default="", max_length=80)

