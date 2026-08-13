import type {
  AchievementsResponse,
  AppSettings,
  DashboardData,
  FlashcardSession,
  ForecastPoint,
  HskLevel,
  ListeningMode,
  ListeningSession,
  ListeningStats,
  MatchingSession,
  ProgressSummary,
  QuestionType,
  QuizSession,
  ReviewQueue,
  ReviewRating,
  ReviewResult,
  ReviewStats,
  AnswerResult,
  DictationMode,
  DictationSession,
  DictationStats,
  HskkExamLevel,
  HskkLevelFormat,
  HskkPaper,
  HskkResult,
  HskkSelfRating,
  HskkStats,
  DonateConfig,
  DonateSummary,
  Donation,
  SentenceLevelSummary,
  SentenceSession,
  TypingMode,
  TypingSession,
  TypingStats,
  StreakSummary,
  VocabularyItem,
  VocabularyListResponse,
  WritingProgressSummary,
  WritingSession,
} from "./types";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // ignore
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const str = search.toString();
  return str ? `?${str}` : "";
}

export const api = {
  dashboard: () => request<DashboardData>("/api/dashboard"),

  vocabulary: {
    list: (params: {
      search?: string;
      topic?: string;
      status?: string;
      hsk_level?: HskLevel;
      limit?: number;
      offset?: number;
      favorites_only?: boolean;
      sort?: string;
    }) => request<VocabularyListResponse>(`/api/vocabulary${qs(params)}`),
    levels: () => request<{ items: { level: HskLevel; total: number; mastered: number }[] }>(
      "/api/vocabulary/levels"
    ),
    topics: () => request<{ items: string[] }>("/api/vocabulary/topics"),
    random: (params: { count?: number; hsk_level?: HskLevel; status?: string }) =>
      request<{ items: VocabularyItem[] }>(`/api/vocabulary/random${qs(params)}`),
    detail: (id: number) => request<VocabularyItem>(`/api/vocabulary/${id}`),
  },

  progress: {
    summary: () => request<ProgressSummary>("/api/progress"),
    item: (vocabularyId: number) => request<VocabularyItem>(`/api/progress/${vocabularyId}`),
    setStatus: (vocabularyId: number, status: string) =>
      request("/api/progress/status", {
        method: "POST",
        body: JSON.stringify({ vocabulary_id: vocabularyId, status }),
      }),
  },

  flashcard: {
    createSession: (count: number, includeMastered: boolean, hskLevel?: HskLevel | null) =>
      request<FlashcardSession>("/api/flashcard/session", {
        method: "POST",
        body: JSON.stringify({
          count,
          include_mastered: includeMastered,
          hsk_level: hskLevel ?? null,
        }),
      }),
    review: (sessionId: number, vocabularyId: number, result: "forgot" | "hard" | "remembered") =>
      request("/api/flashcard/review", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, vocabulary_id: vocabularyId, result }),
      }),
    complete: (sessionId: number, total: number, correct: number, incorrect: number) =>
      request(`/api/flashcard/session/${sessionId}/complete`, {
        method: "POST",
        body: JSON.stringify({ total_items: total, correct_items: correct, incorrect_items: incorrect }),
      }),
  },

  matching: {
    createSession: (mode: "meaning" | "pinyin", count: number) =>
      request<MatchingSession>("/api/matching/session", {
        method: "POST",
        body: JSON.stringify({ mode, count }),
      }),
    attempt: (sessionId: number, vocabularyId: number, mode: string, isCorrect: boolean) =>
      request("/api/matching/attempt", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, vocabulary_id: vocabularyId, mode, is_correct: isCorrect }),
      }),
    complete: (sessionId: number, total: number, correct: number, incorrect: number) =>
      request(`/api/matching/session/${sessionId}/complete`, {
        method: "POST",
        body: JSON.stringify({ total_items: total, correct_items: correct, incorrect_items: incorrect }),
      }),
  },

  sentences: {
    topics: () => request<{ items: string[] }>("/api/sentences/topics"),
    stats: () => request("/api/sentences/stats"),
    levels: () => request<{ items: SentenceLevelSummary[] }>("/api/sentences/levels"),
    createSession: (
      count: number,
      topic?: string,
      hskLevel?: HskLevel | null,
      maxTokens?: number | null
    ) =>
      request<SentenceSession>("/api/sentences/session", {
        method: "POST",
        body: JSON.stringify({
          count,
          topic: topic || null,
          hsk_level: hskLevel || null,
          max_tokens: maxTokens || null,
        }),
      }),
    attempt: (sessionId: number, sentenceId: number, orderedPositions: number[]) =>
      request<{
        session_id: number;
        sentence_id: number;
        is_correct: boolean;
        answer: { hanzi: string; pinyin: string; meaning: string };
      }>("/api/sentences/attempt", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, sentence_id: sentenceId, ordered_positions: orderedPositions }),
      }),
    complete: (sessionId: number, total: number, correct: number, incorrect: number) =>
      request(`/api/sentences/session/${sessionId}/complete`, {
        method: "POST",
        body: JSON.stringify({ total_items: total, correct_items: correct, incorrect_items: incorrect }),
      }),
  },

  quiz: {
    stats: () => request("/api/quiz/stats"),
    createSession: (hskLevel: HskLevel | null, questionTypes: QuestionType[], count: number) =>
      request<QuizSession>("/api/quiz/session", {
        method: "POST",
        body: JSON.stringify({ hsk_level: hskLevel, question_types: questionTypes, count }),
      }),
    attempt: (sessionId: number, vocabularyId: number, questionType: QuestionType, isCorrect: boolean) =>
      request("/api/quiz/attempt", {
        method: "POST",
        body: JSON.stringify({
          session_id: sessionId,
          vocabulary_id: vocabularyId,
          question_type: questionType,
          is_correct: isCorrect,
        }),
      }),
    complete: (sessionId: number, total: number, correct: number, incorrect: number) =>
      request(`/api/quiz/session/${sessionId}/complete`, {
        method: "POST",
        body: JSON.stringify({ total_items: total, correct_items: correct, incorrect_items: incorrect }),
      }),
  },

  listening: {
    stats: () => request<ListeningStats>("/api/listening/stats"),
    createSession: (hskLevel: HskLevel | null, mode: ListeningMode, count: number) =>
      request<ListeningSession>("/api/listening/session", {
        method: "POST",
        body: JSON.stringify({ hsk_level: hskLevel, mode, count }),
      }),
    attempt: (sessionId: number, vocabularyId: number, mode: ListeningMode, isCorrect: boolean) =>
      request("/api/listening/attempt", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, vocabulary_id: vocabularyId, mode, is_correct: isCorrect }),
      }),
    complete: (sessionId: number, total: number, correct: number, incorrect: number) =>
      request(`/api/listening/session/${sessionId}/complete`, {
        method: "POST",
        body: JSON.stringify({ total_items: total, correct_items: correct, incorrect_items: incorrect }),
      }),
  },

  writing: {
    progress: () => request<WritingProgressSummary>("/api/writing/progress"),
    createSession: (hskLevel: HskLevel | null, count: number) =>
      request<WritingSession>("/api/writing/session", {
        method: "POST",
        body: JSON.stringify({ hsk_level: hskLevel, count }),
      }),
    attempt: (sessionId: number, character: string, mistakes: number, isCorrect: boolean) =>
      request("/api/writing/attempt", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, character, mistakes, is_correct: isCorrect }),
      }),
    complete: (sessionId: number, total: number, correct: number, incorrect: number) =>
      request(`/api/writing/session/${sessionId}/complete`, {
        method: "POST",
        body: JSON.stringify({ total_items: total, correct_items: correct, incorrect_items: incorrect }),
      }),
  },

  review: {
    queue: (params: {
      limit?: number;
      hsk_level?: HskLevel;
      include_new?: boolean;
      new_limit?: number;
    }) => request<ReviewQueue>(`/api/review/queue${qs(params)}`),
    stats: () => request<ReviewStats>("/api/review/stats"),
    forecast: (days = 14) => request<{ items: ForecastPoint[] }>(`/api/review/forecast${qs({ days })}`),
    submit: (vocabularyId: number, rating: ReviewRating, source = "review") =>
      request<ReviewResult>("/api/review/submit", {
        method: "POST",
        body: JSON.stringify({ vocabulary_id: vocabularyId, rating, source }),
      }),
    favorites: () => request<{ items: VocabularyItem[] }>("/api/review/favorites"),
    setFavorite: (vocabularyId: number, isFavorite: boolean) =>
      request<{ vocabulary_id: number; is_favorite: boolean }>("/api/review/favorite", {
        method: "POST",
        body: JSON.stringify({ vocabulary_id: vocabularyId, is_favorite: isFavorite }),
      }),
    setNote: (vocabularyId: number, note: string | null) =>
      request<{ vocabulary_id: number; note: string | null }>("/api/review/note", {
        method: "POST",
        body: JSON.stringify({ vocabulary_id: vocabularyId, note }),
      }),
  },

  streak: (heatmapDays = 182) =>
    request<StreakSummary>(`/api/streak${qs({ heatmap_days: heatmapDays })}`),

  achievements: () => request<AchievementsResponse>("/api/achievements"),

  settings: {
    get: () => request<{ settings: AppSettings; defaults: AppSettings }>("/api/settings"),
    update: (patch: Partial<AppSettings>) =>
      request<{ settings: AppSettings }>("/api/settings", {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    reset: () => request<{ settings: AppSettings }>("/api/settings/reset", { method: "POST" }),
  },

  backup: {
    export: () => request<Record<string, unknown>>("/api/backup/export"),
    import: (payload: unknown) =>
      request<{ imported: Record<string, number>; restored_at: string }>("/api/backup/import", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },

  typing: {
    stats: () => request<TypingStats>("/api/typing/stats"),
    createSession: (hskLevel: HskLevel | null, mode: TypingMode, count: number, onlyDue = false) =>
      request<TypingSession>("/api/typing/session", {
        method: "POST",
        body: JSON.stringify({ hsk_level: hskLevel, mode, count, only_due: onlyDue }),
      }),
    check: (sessionId: number | null, vocabularyId: number, mode: TypingMode, answer: string) =>
      request<AnswerResult & { vocabulary_id: number }>("/api/typing/check", {
        method: "POST",
        body: JSON.stringify({
          session_id: sessionId,
          vocabulary_id: vocabularyId,
          mode,
          answer,
        }),
      }),
    complete: (sessionId: number, total: number, correct: number, incorrect: number) =>
      request(`/api/typing/session/${sessionId}/complete`, {
        method: "POST",
        body: JSON.stringify({ total_items: total, correct_items: correct, incorrect_items: incorrect }),
      }),
  },

  dictation: {
    stats: () => request<DictationStats>("/api/dictation/stats"),
    createSession: (hskLevel: HskLevel | null, mode: DictationMode, count: number) =>
      request<DictationSession>("/api/dictation/session", {
        method: "POST",
        body: JSON.stringify({ hsk_level: hskLevel, mode, count }),
      }),
    check: (
      sessionId: number | null,
      targetId: number,
      mode: DictationMode,
      answer: string,
      replays: number
    ) =>
      request<AnswerResult & { target_id: number; replays: number }>("/api/dictation/check", {
        method: "POST",
        body: JSON.stringify({
          session_id: sessionId,
          target_id: targetId,
          mode,
          answer,
          replays,
        }),
      }),
    complete: (sessionId: number, total: number, correct: number, incorrect: number) =>
      request(`/api/dictation/session/${sessionId}/complete`, {
        method: "POST",
        body: JSON.stringify({ total_items: total, correct_items: correct, incorrect_items: incorrect }),
      }),
  },

  hskk: {
    levels: () => request<{ items: HskkLevelFormat[] }>("/api/hskk/levels"),
    stats: () => request<HskkStats>("/api/hskk/stats"),
    createSession: (examLevel: HskkExamLevel) =>
      request<HskkPaper>("/api/hskk/session", {
        method: "POST",
        body: JSON.stringify({ exam_level: examLevel }),
      }),
    answer: (
      sessionId: number,
      part: number,
      questionIndex: number,
      questionId: string,
      selfRating: HskkSelfRating,
      spokenSeconds: number
    ) =>
      request<{ score: number; max_score: number }>("/api/hskk/answer", {
        method: "POST",
        body: JSON.stringify({
          session_id: sessionId,
          part,
          question_index: questionIndex,
          question_id: questionId,
          self_rating: selfRating,
          spoken_seconds: spokenSeconds,
        }),
      }),
    complete: (sessionId: number) =>
      request<HskkResult>(`/api/hskk/session/${sessionId}/complete`, { method: "POST" }),
  },

  donate: {
    config: () => request<DonateConfig>("/api/donate/config"),
    summary: () => request<DonateSummary>("/api/donate/summary"),
    recent: (limit = 10) => request<{ items: Donation[] }>(`/api/donate/recent${qs({ limit })}`),
    create: (amount: number, message: string, donorName: string) =>
      request<Donation>("/api/donate/session", {
        method: "POST",
        body: JSON.stringify({ amount, message, donor_name: donorName }),
      }),
    status: (orderCode: number) => request<Donation>(`/api/donate/status/${orderCode}`),
    cancel: (orderCode: number) =>
      request<Donation>(`/api/donate/cancel/${orderCode}`, { method: "POST" }),
  },

  health: () => request<{ status: string; service: string; version: string }>("/api/health"),
};

export function audioUrl(text: string, voice: "female" | "male" = "female"): string {
  return `/api/audio${qs({ text, voice })}`;
}

export { ApiError };
