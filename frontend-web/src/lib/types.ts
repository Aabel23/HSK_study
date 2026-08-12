export type HskLevel = "1" | "2" | "3" | "4" | "5" | "6" | "7-9";

export const HSK_LEVELS: HskLevel[] = ["1", "2", "3", "4", "5", "6", "7-9"];

export type ProgressStatus = "new" | "learning" | "review" | "mastered";

export interface VocabularyItem {
  id: number;
  hanzi: string;
  pinyin: string;
  meaning: string;
  example: string | null;
  example_pinyin: string | null;
  example_meaning: string | null;
  topic: string | null;
  hsk_level: HskLevel;
  meaning_en: string | null;
  traditional: string | null;
  pos: string | null;
  pos_vi: string | null;
  classifiers: string | null;
  frequency: number | null;
  status: ProgressStatus;
  review_count: number;
  correct_count: number;
  incorrect_count: number;
  last_reviewed_at: string | null;
  ease_factor: number;
  interval_days: number;
  repetitions: number;
  lapses: number;
  is_favorite: boolean | number;
  due_at: string | null;
  note: string | null;
}

export type ReviewRating = "again" | "hard" | "good" | "easy";

export interface ReviewQueue {
  items: VocabularyItem[];
  due_count: number;
  new_count: number;
  returned: number;
}

export interface ReviewResult {
  vocabulary_id: number;
  rating: ReviewRating;
  status: ProgressStatus;
  ease_factor: number;
  interval_days: number;
  repetitions: number;
  lapses: number;
  due_at: string;
}

export interface ForecastPoint {
  date: string;
  offset: number;
  count: number;
}

export interface ReviewStats {
  due_now: number;
  in_rotation: number;
  mastered: number;
  total_vocabulary: number;
  total_reviews: number;
  average_ease: number;
  favorites: number;
  retention_percentage: number;
  forecast: ForecastPoint[];
}

export interface HeatmapDay {
  date: string;
  count: number;
}

export interface StreakSummary {
  current_streak: number;
  longest_streak: number;
  active_days: number;
  total_xp: number;
  level: number;
  xp_into_level: number;
  xp_per_level: number;
  daily_goal: number;
  today_reviews: number;
  today_correct: number;
  today_incorrect: number;
  today_new_learned: number;
  today_xp: number;
  goal_percentage: number;
  goal_met: boolean;
  heatmap: HeatmapDay[];
  history: Array<{
    activity_date: string;
    reviews_done: number;
    correct_count: number;
    incorrect_count: number;
    new_learned: number;
    study_seconds: number;
    xp: number;
  }>;
}

export interface AchievementItem {
  code: string;
  title: string;
  description: string;
  icon: string;
  tier: "bronze" | "silver" | "gold" | "diamond";
  target: number;
  progress: number;
  percentage: number;
  unlocked: boolean;
  unlocked_at: string | null;
}

export interface AchievementsResponse {
  items: AchievementItem[];
  unlocked_count: number;
  total_count: number;
  newly_unlocked: string[];
}

export interface AppSettings {
  daily_goal: number;
  new_words_per_day: number;
  session_size: number;
  theme: "dark" | "light";
  audio_voice: "female" | "male";
  autoplay_audio: boolean;
  show_pinyin: boolean;
  show_traditional: boolean;
  reduced_motion: boolean;
  sound_effects: boolean;
  preferred_level: string;
}

export interface VocabularyListResponse {
  items: VocabularyItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface HskLevelSummary {
  level: HskLevel;
  total: number;
  mastered: number;
}

export interface DashboardData {
  total_vocabulary: number;
  viewed_vocabulary: number;
  learning_vocabulary: number;
  review_vocabulary: number;
  mastered_vocabulary: number;
  matching_sessions: number;
  matching_correct: number;
  matching_incorrect: number;
  matching_accuracy: number;
  sentence_sessions: number;
  sentence_correct: number;
  sentence_incorrect: number;
  sentence_accuracy: number;
  quiz_sessions: number;
  quiz_correct: number;
  quiz_incorrect: number;
  quiz_accuracy: number;
  listening_sessions: number;
  listening_correct: number;
  listening_incorrect: number;
  listening_accuracy: number;
  writing_practiced: number;
  writing_learning: number;
  writing_mastered: number;
  hsk_levels: HskLevelSummary[];
  recent_vocabulary: Array<{
    id: number;
    hanzi: string;
    pinyin: string;
    meaning: string;
    status: ProgressStatus;
    last_reviewed_at: string | null;
  }>;
  recent_sessions: Array<{
    id: number;
    session_type: string;
    started_at: string;
    ended_at: string | null;
    total_items: number;
    correct_items: number;
    incorrect_items: number;
  }>;
}

export interface FlashcardSession {
  session_id: number;
  items: VocabularyItem[];
}

export interface MatchingItem {
  vocabulary_id: number;
  text: string;
}

export interface MatchingSession {
  session_id: number;
  mode: "meaning" | "pinyin";
  left_items: MatchingItem[];
  right_items: MatchingItem[];
}

export interface SentenceToken {
  token_id: string;
  position: number;
  text: string;
  pinyin: string;
}

export interface SentenceItem {
  id: number;
  hanzi: string;
  pinyin: string;
  meaning: string;
  topic: string | null;
  hsk_level: HskLevel;
  difficulty: number;
  tokens: SentenceToken[];
}

export interface SentenceSession {
  session_id: number;
  items: SentenceItem[];
}

export type QuestionType = "mcq_meaning" | "mcq_hanzi" | "mcq_pinyin" | "mcq_audio";

export interface QuizOption {
  vocabulary_id: number;
  label: string;
}

export interface QuizQuestion {
  question_id: number;
  question_type: QuestionType;
  target_vocabulary_id: number;
  prompt: {
    hanzi?: string;
    pinyin?: string;
    meaning?: string;
    audio_text?: string;
  };
  options: QuizOption[];
}

export interface QuizSession {
  session_id: number;
  hsk_level: string;
  questions: QuizQuestion[];
}

export type ListeningMode = "audio_to_meaning" | "audio_to_hanzi";

export interface ListeningItem {
  item_id: number;
  mode: ListeningMode;
  target_vocabulary_id: number;
  audio_text: string;
  options: QuizOption[];
}

export interface ListeningSession {
  session_id: number;
  hsk_level: string;
  mode: ListeningMode;
  items: ListeningItem[];
}

export interface WritingCharacter {
  character: string;
  word: string;
  pinyin: string;
  meaning: string;
  status: "new" | "learning" | "mastered";
  practice_count: number;
  success_count: number;
}

export interface WritingSession {
  session_id: number;
  hsk_level: string;
  characters: WritingCharacter[];
}

export interface WritingProgressSummary {
  practiced_count: number;
  learning_count: number;
  mastered_count: number;
  recent_characters: Array<{
    character: string;
    status: string;
    practice_count: number;
    success_count: number;
    last_practiced_at: string | null;
  }>;
}

export interface ProgressSummary {
  total_vocabulary: number;
  new_count: number;
  learning_count: number;
  review_count: number;
  mastered_count: number;
  completion_percentage: number;
  review_items: VocabularyItem[];
  mastered_items: VocabularyItem[];
  recent_sessions: DashboardData["recent_sessions"];
}

export type TypingMode =
  | "hanzi_to_pinyin"
  | "audio_to_pinyin"
  | "meaning_to_pinyin"
  | "audio_to_hanzi"
  | "meaning_to_hanzi";

export interface TypingItem {
  item_id: number;
  vocabulary_id: number;
  mode: TypingMode;
  hsk_level: HskLevel;
  prompt: {
    hanzi?: string;
    pinyin?: string;
    meaning?: string;
    audio_text?: string;
  };
}

export interface TypingSession {
  session_id: number;
  mode: TypingMode;
  hsk_level: string;
  items: TypingItem[];
}

export interface CharacterDiff {
  expected: string;
  typed: string | null;
  correct: boolean;
}

export interface AnswerResult {
  is_correct: boolean;
  tones_correct: boolean;
  tones_provided: boolean;
  expected: string;
  answer: string;
  character_diff: CharacterDiff[];
  reveal: { hanzi: string; pinyin: string; meaning: string };
}

export type DictationMode = "word_pinyin" | "word_hanzi" | "sentence_hanzi";

export interface DictationItem {
  item_id: number;
  mode: DictationMode;
  target_id: number;
  is_sentence: boolean;
  audio_text: string;
  hsk_level: HskLevel;
  hint: { length: number; meaning: string | null };
}

export interface DictationSession {
  session_id: number;
  mode: DictationMode;
  hsk_level: string;
  items: DictationItem[];
}

export interface ListeningStats {
  sessions: number;
  correct: number;
  incorrect: number;
  accuracy: number;
}

export interface DictationStats {
  sessions: number;
  attempts: number;
  correct: number;
  incorrect: number;
  accuracy: number;
  average_replays: number;
  first_listen_correct: number;
  first_listen_rate: number;
}

export interface TypingStats {
  sessions: number;
  attempts: number;
  correct: number;
  incorrect: number;
  accuracy: number;
  modes: Array<{ mode: TypingMode; label: string; attempts: number; correct: number; accuracy: number }>;
}

export interface SentenceLevelSummary {
  level: HskLevel;
  total: number;
  min_tokens: number;
  max_tokens: number;
}
