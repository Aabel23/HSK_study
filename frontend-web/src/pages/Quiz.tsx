import { useState } from "react";
import clsx from "clsx";
import { api } from "../lib/api";
import { useLevel } from "../lib/levelContext";
import { usePlayAudio } from "../lib/useAudio";
import { distinctOptionLabels } from "../lib/format";
import { useShortcuts } from "../lib/useShortcuts";
import type { QuestionType, QuizOption, QuizQuestion } from "../lib/types";
import { Button, Card, PageHeader, ProgressBar, SessionComplete } from "../components/ui";
import { IconCheckSquare, IconPlay, IconRefresh } from "../components/icons";

const TYPE_LABEL: Record<QuestionType, string> = {
  mcq_meaning: "Hán tự → Nghĩa",
  mcq_hanzi: "Nghĩa → Hán tự",
  mcq_pinyin: "Hán tự → Pinyin",
  mcq_audio: "Nghe → Nghĩa",
};

const ALL_TYPES = Object.keys(TYPE_LABEL) as QuestionType[];

export default function Quiz() {
  const { level } = useLevel();
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const [picked, setPicked] = useState<number | null>(null);
  const [stats, setStats] = useState({ correct: 0, incorrect: 0 });
  const [finished, setFinished] = useState(false);
  const [selectedTypes, setSelectedTypes] = useState<QuestionType[]>(ALL_TYPES);
  const { play, playingText } = usePlayAudio();

  async function start() {
    const types = selectedTypes.length ? selectedTypes : ALL_TYPES;
    const session = await api.quiz.createSession(level === "all" ? null : level, types, 10);
    setSessionId(session.session_id);
    setQuestions(session.questions);
    setIndex(0);
    setPicked(null);
    setStats({ correct: 0, incorrect: 0 });
    setFinished(false);
  }

  const current = questions[index];

  async function choose(option: QuizOption) {
    if (!sessionId || picked !== null) return;
    setPicked(option.vocabulary_id);
    const isCorrect = option.vocabulary_id === current.target_vocabulary_id;
    await api.quiz.attempt(sessionId, current.target_vocabulary_id, current.question_type, isCorrect);
    setStats((s) => (isCorrect ? { ...s, correct: s.correct + 1 } : { ...s, incorrect: s.incorrect + 1 }));
  }

  async function next() {
    if (!sessionId) return;
    if (index + 1 >= questions.length) {
      await api.quiz.complete(sessionId, questions.length, stats.correct, stats.incorrect);
      setFinished(true);
      return;
    }
    setIndex(index + 1);
    setPicked(null);
  }

  function toggleType(type: QuestionType) {
    setSelectedTypes((prev) => (prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]));
  }

  // This page had no keyboard at all, which is what made the shortcuts feel
  // arbitrary: Space advanced a flashcard and then did nothing here. Bound
  // above the early returns because hooks cannot be called conditionally.
  useShortcuts({
    enabled: Boolean(sessionId) && !finished,
    onAdvance: () => {
      if (picked !== null) void next();
    },
    onPick: (choice) => {
      if (picked !== null || !current) return;
      const option = current.options[choice - 1];
      if (option) void choose(option);
    },
  });

  if (!sessionId) {
    return (
      <div className="animate-float-in">
        <PageHeader eyebrow="Kiểm tra" title="Bài kiểm tra tổng hợp" description="Trắc nghiệm 10 câu, kết hợp nhiều kỹ năng." />
        <Card className="max-w-lg p-6">
          <p className="mb-3 text-sm font-semibold text-ink">Chọn dạng câu hỏi</p>
          <div className="flex flex-wrap gap-2">
            {ALL_TYPES.map((type) => (
              <button
                key={type}
                onClick={() => toggleType(type)}
                className={clsx(
                  "rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors",
                  selectedTypes.includes(type) ? "border-accent bg-accent-soft text-accent" : "border-border text-ink-faint"
                )}
              >
                {TYPE_LABEL[type]}
              </button>
            ))}
          </div>
          <Button className="mt-6 w-full" size="lg" onClick={start}>
            <IconCheckSquare className="h-4 w-4" /> Bắt đầu kiểm tra
          </Button>
        </Card>
      </div>
    );
  }

  if (finished) {
    return (
      <SessionComplete
        correct={stats.correct}
        total={questions.length}
        unit="câu"
        detail={`${stats.correct} đúng · ${stats.incorrect} sai`}
        primary={
          <Button size="lg" onClick={() => setSessionId(null)}>
            <IconRefresh className="h-4 w-4" /> Làm bài mới
          </Button>
        }
      />
    );
  }

  // Shortened together rather than one by one: two options that collapse to the
  // same text would leave the question with no answerable difference.
  const labels = distinctOptionLabels(current.options.map((option) => option.label));

  return (
    <div className="animate-float-in mx-auto max-w-xl">
      <div className="mb-3 flex items-center justify-between text-sm text-ink-soft">
        <span>
          Câu {index + 1}/{questions.length} · {TYPE_LABEL[current.question_type]}
        </span>
      </div>
      <ProgressBar value={(index / questions.length) * 100} />

      <Card className="mt-6 flex flex-col items-center gap-3 p-8 text-center">
        {current.question_type === "mcq_audio" ? (
          <button
            onClick={() => play(current.prompt.audio_text!)}
            className="flex h-16 w-16 items-center justify-center rounded-full bg-accent text-accent-ink"
          >
            <IconPlay className={clsx("h-6 w-6", playingText === current.prompt.audio_text && "animate-pulse")} />
          </button>
        ) : current.question_type === "mcq_hanzi" ? (
          <p className="text-xl font-semibold text-ink">{current.prompt.meaning}</p>
        ) : (
          <>
            <p className="hanzi text-5xl font-bold text-ink">{current.prompt.hanzi}</p>
            {current.question_type === "mcq_meaning" && current.prompt.pinyin && (
              <p className="text-gold">{current.prompt.pinyin}</p>
            )}
          </>
        )}
      </Card>

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {current.options.map((option, position) => {
          const isTarget = option.vocabulary_id === current.target_vocabulary_id;
          const isPicked = picked === option.vocabulary_id;
          const revealed = picked !== null;
          return (
            <button
              key={option.vocabulary_id}
              onClick={() => choose(option)}
              disabled={revealed}
              className={clsx(
                "rounded-xl border px-4 py-3.5 text-left text-sm font-medium transition-colors",
                current.question_type === "mcq_hanzi" && "hanzi text-lg",
                !revealed && "border-border bg-surface text-ink hover:border-accent/50",
                revealed && isTarget && "border-jade bg-jade-soft text-jade",
                revealed && isPicked && !isTarget && "border-danger bg-danger-soft text-danger",
                revealed && !isPicked && !isTarget && "border-border bg-surface text-ink-faint opacity-60"
              )}
            >
              {labels[position]}
            </button>
          );
        })}
      </div>

      {picked !== null && (
        <Button className="mt-6 w-full" size="lg" onClick={next}>
          Câu tiếp theo
        </Button>
      )}
    </div>
  );
}
