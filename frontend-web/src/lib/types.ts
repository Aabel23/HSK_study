export type HskLevel = "1" | "2" | "3" | "4" | "5" | "6" | "7-9";

export const HSK_LEVELS: HskLevel[] = ["1", "2", "3", "4", "5", "6", "7-9"];

export type ProgressStatus = "new" | "learning" | "review" | "mastered";

export interface WordExample {
  hanzi: string;
  pinyin: string;
  meaning_vi: string;
  /** 'sentences' | 'grammar' | 'hskk' — which part of the app it came from. */
  source: string;
  source_ref: string;
}

export interface VocabularyItem {
  /** Sentences using this word. Only the single-entry endpoint fills this in;
   *  the list leaves it undefined. */
  examples?: WordExample[];
  /** The word spelled in âm Hán-Việt — 图书馆 → "đồ thư quán". Null when at
   *  least one of its characters has no recorded reading. */
  han_viet?: string | null;
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

/** HSKK is a spoken exam, so the learner grades their own answer. */
export type HskkSelfRating = "good" | "ok" | "bad" | "skipped";

export type HskkExamLevel = "beginner" | "intermediate";

/** repeat = nhắc lại, answer = trả lời câu hỏi, describe = kể theo tình huống, opinion = nêu quan điểm. */
export type HskkPartKind = "repeat" | "answer" | "describe" | "opinion";

export interface HskkPartFormat {
  part: number;
  kind: HskkPartKind;
  title: string;
  instruction_zh: string;
  instruction_vi: string;
  count: number;
  points_per_item: number;
  total_points: number;
  answer_seconds: number;
}

export type ReadingQuestionType =
  | "judge_true_false"
  | "fill_in_blank_sentence"
  | "multiple_choice_dialogue"
  | "reading_comprehension"
  | "sentence_reordering";

export interface ReadingQuestion {
  id: string;
  question_index: number;
  passage_zh?: string;
  statement_zh?: string;
  sentence_zh?: string;
  question_zh?: string;
  options?: Array<{ key: string; text_zh: string }>;
  words_zh?: string[];
}

export interface ReadingPart {
  part_id: string;
  part_number: number;
  question_type: ReadingQuestionType;
  instruction_zh: string;
  instruction_vi: string;
  question_count: number;
  word_bank?: Array<{ key: string; word_zh: string }>;
  options_per_question?: number;
  questions: ReadingQuestion[];
}

export interface ReadingSection {
  section_id: "reading";
  section_name_zh: string;
  section_name_vi: string;
  hsk_level: number;
  time_minutes: number;
  total_questions: number;
  part: number;
  points_per_item: number;
  max_score: number;
  parts: ReadingPart[];
}

export interface HskkReadingFormat {
  hsk_level: number;
  section_name_zh: string;
  section_name_vi: string;
  time_minutes: number;
  total_questions: number;
  total_points: number;
  parts: Array<{
    part_number: number;
    question_type: ReadingQuestionType;
    instruction_zh: string;
    instruction_vi: string;
    count: number;
  }>;
}

/** Server's verdict on one reading answer; the answer key never reaches the client. */
export interface ReadingVerdict {
  question_id: string;
  is_correct: boolean;
  correct_answer: string;
  explanation_vi: string;
  score: number;
}

export interface HskkLevelFormat {
  code: HskkExamLevel;
  label: string;
  hsk_range: string;
  blurb: string;
  prep_seconds: number;
  pass_score: number;
  total_items: number;
  speaking_items: number;
  speaking_points: number;
  reading: HskkReadingFormat;
  parts: HskkPartFormat[];
  /** Parts of the official format this paper leaves out, with the reason why. */
  skipped_parts: Array<{ part: number; title: string; reason: string }>;
  ai_grading: boolean;
}

export interface HskkItem {
  question_index: number;
  question_id: string;
  hanzi: string;
  pinyin: string;
  vi: string;
  hints: string[];
  /** Set only for parts the learner must *hear*; null when the prompt is read. */
  audio_text: string | null;
}

export interface HskkPart {
  part: number;
  kind: HskkPartKind;
  title: string;
  instruction_zh: string;
  instruction_vi: string;
  points_per_item: number;
  answer_seconds: number;
  min_sentences: number | null;
  items: HskkItem[];
}

export interface HskkPaper {
  session_id: number;
  quiz_session_id: number;
  exam_level: HskkExamLevel;
  label: string;
  prep_seconds: number;
  pass_score: number;
  total_items: number;
  max_score: number;
  ai_grading: boolean;
  reading: ReadingSection;
  parts: HskkPart[];
}

/** What Gemini sends back for one spoken answer. */
export interface HskkGrade {
  part: number;
  question_index: number;
  score: number;
  max_score: number;
  percent: number;
  transcript: string;
  expected: string;
  verdict: string;
  strengths: string[];
  fixes: string[];
  pronunciation_percent: number;
  content_percent: number;
  fluency_percent: number;
  graded_by: "ai";
}

export interface HskkResult {
  session_id: number;
  exam_level: HskkExamLevel;
  score: number;
  max_score: number;
  percent: number;
  written_score: number;
  written_max: number;
  written_percent: number;
  overall_percent: number;
  passed: boolean;
  pass_score: number;
  band: string;
  total_items: number;
  answered_items: number;
  parts: Array<{
    part: number;
    title: string;
    answered: number;
    score: number;
    max_score: number;
    spoken_seconds: number;
  }>;
}

export interface HskkStats {
  sessions: number;
  best_percent: number;
  average_percent: number;
  last_percent: number;
  ai_grading: boolean;
  recent: Array<{
    exam_level: HskkExamLevel;
    score: number;
    max_score: number;
    percent: number;
    written_percent: number;
    ended_at: string | null;
  }>;
  ratings: Array<{ self_rating: HskkSelfRating; label: string; total: number }>;
}

export type DonationStatus = "pending" | "paid" | "cancelled" | "expired";

export interface DonateConfig {
  /** False when the server has no PayOS credentials; the page explains instead. */
  enabled: boolean;
  recipient: string;
  min_amount: number;
  max_amount: number;
  suggested_amounts: number[];
  currency: string;
}

export interface Donation {
  order_code: number;
  amount: number;
  message: string;
  donor_name: string;
  status: DonationStatus;
  /** PayOS hosted checkout page, for donors who would rather not scan. */
  checkout_url: string | null;
  /** Raw VietQR payload; the page renders it to a canvas locally. */
  qr_code: string | null;
  created_at: string;
  paid_at: string | null;
}

export interface DonateSummary {
  paid_count: number;
  paid_total: number;
  last_paid_at: string | null;
}

/* --------------------------------------------------------------------------
   The character layer

   Everything above is keyed by word. These are keyed by character, which is
   what the Hán-Việt decoder screen works in.
-------------------------------------------------------------------------- */

export interface RadicalDetail {
  hanzi: string;
  name_vi: string;
  meaning_vi: string;
  mnemonic_vi: string;
}

export interface CharacterWord {
  id: number;
  hanzi: string;
  pinyin: string;
  han_viet: string | null;
  meaning: string;
  hsk_level: HskLevel;
  status: ProgressStatus;
}

export interface CharacterItem {
  hanzi: string;
  pinyin: string;
  han_viet: string;
  /** Which dataset the reading came from, so the page can flag the weaker ones. */
  han_viet_source: string;
  meaning_vi: string;
  meaning_en: string;
  traditional: string | null;
  stroke_count: number | null;
  radical_number: number | null;
  radicals: string[];
  mnemonic_vi: string;
  stroke_hint_vi: string;
  hsk_level: HskLevel | null;
  /** How many words in the bank are built on this character. */
  word_count: number;
  status: "new" | "learning" | "mastered";
  seen_count: number;
  correct_count: number;
  incorrect_count: number;
  is_favorite: number;
  last_seen_at: string | null;
  /** Only present on the single-character lookup. */
  radical_details?: RadicalDetail[];
  words?: CharacterWord[];
}

export interface CharacterListResponse {
  items: CharacterItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface CharacterStats {
  total: number;
  with_reading: number;
  mastered: number;
  learning: number;
  words_decodable: number;
  words_total: number;
  /** Bank words reachable from the characters already marked mastered. */
  words_unlocked: number;
}

export type DecodeMode = "han_viet_to_meaning" | "meaning_to_han_viet" | "character_reading";

export interface DecodeSession {
  session_id: number;
  mode: DecodeMode;
  mode_label: string;
  total: number;
  hsk_level: string;
}

export interface DecodeBreakdownPart {
  hanzi: string;
  pinyin: string;
  han_viet: string;
  meaning_vi: string;
  mnemonic_vi?: string;
  word_count?: number;
}

export interface DecodeQuestion {
  session_id: number;
  mode: DecodeMode;
  mode_label: string;
  vocabulary_id: number | null;
  word: string;
  pinyin: string;
  han_viet: string;
  hsk_level: HskLevel;
  meaning: string;
  breakdown: DecodeBreakdownPart[];
  options: string[];
  prompt: { meaning?: string };
}

export interface DecodeStats {
  sessions: number;
  correct: number;
  incorrect: number;
  accuracy: number;
}
