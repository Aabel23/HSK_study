import { useMemo, useState } from "react";
import clsx from "clsx";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../lib/api";
import { useToast } from "../lib/toast";
import type { ReadingPart, ReadingQuestion, ReadingSection, ReadingVerdict } from "../lib/types";
import { Badge, Button, Card, ProgressBar } from "../components/ui";
import { IconCheck, IconX } from "../components/icons";

/** One question paired with the part it belongs to, so the runner is a flat list. */
interface Slot {
  part: ReadingPart;
  question: ReadingQuestion;
}

const TYPE_LABEL: Record<ReadingPart["question_type"], string> = {
  judge_true_false: "Đúng / Sai",
  fill_in_blank_sentence: "Chọn từ điền vào chỗ trống",
  multiple_choice_dialogue: "Đọc hội thoại chọn đáp án",
  reading_comprehension: "Đọc hiểu đoạn văn",
  sentence_reordering: "Sắp xếp câu",
};

function flatten(section: ReadingSection): Slot[] {
  return section.parts.flatMap((part) => part.questions.map((question) => ({ part, question })));
}

/**
 * The reading half of the mock exam.
 *
 * Every answer is decided by the server — this component only reports what was
 * picked and renders the verdict that comes back, so the answer key is never in
 * the page. Each question type gets the layout the real paper uses.
 */
export function ReadingRunner({
  sessionId,
  section,
  onFinish,
  onSessionLost,
}: {
  sessionId: number;
  section: ReadingSection;
  onFinish: (correct: number) => void;
  onSessionLost: () => void;
}) {
  const toast = useToast();
  const slots = useMemo(() => flatten(section), [section]);

  const [index, setIndex] = useState(0);
  const [verdict, setVerdict] = useState<ReadingVerdict | null>(null);
  const [correct, setCorrect] = useState(0);
  const [busy, setBusy] = useState(false);
  /** Clause order the learner has built so far, for reordering questions. */
  const [ordered, setOrdered] = useState<string[]>([]);
  const [picked, setPicked] = useState<string | null>(null);

  const slot = slots[index];
  if (!slot) return null;
  const { part, question } = slot;

  async function submit(answer: boolean | string | string[]) {
    if (busy || verdict) return;
    setBusy(true);
    try {
      const outcome = await api.hskk.reading(sessionId, index, question.id, answer);
      setVerdict(outcome);
      if (outcome.is_correct) setCorrect((value) => value + 1);
    } catch (error) {
      if (error instanceof Error && error.message.includes("Không tìm thấy bài thi")) onSessionLost();
      else toast.error("Không chấm được câu này", error instanceof Error ? error.message : undefined);
    } finally {
      setBusy(false);
    }
  }

  function next() {
    if (index + 1 >= slots.length) {
      onFinish(correct);
      return;
    }
    setIndex(index + 1);
    setVerdict(null);
    setOrdered([]);
    setPicked(null);
  }

  function toggleClause(clause: string) {
    if (verdict) return;
    setOrdered((current) =>
      current.includes(clause) ? current.filter((entry) => entry !== clause) : [...current, clause]
    );
  }

  const answered = Boolean(verdict);

  return (
    <div className="animate-float-in mx-auto max-w-2xl">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Badge tone="sky">
          阅读 · Phần {part.part_number} · {TYPE_LABEL[part.question_type]}
        </Badge>
        <span className="tnum text-xs font-semibold text-ink-soft">
          Câu {index + 1}/{slots.length}
        </span>
        <span className="ml-auto tnum text-xs text-ink-faint">Đúng {correct}/{index + (answered ? 1 : 0)}</span>
      </div>
      <ProgressBar value={(index / slots.length) * 100} accent="sky" />
      <p className="mt-3 text-xs text-ink-faint">
        {part.instruction_zh} — {part.instruction_vi}
      </p>

      <AnimatePresence mode="wait">
        <motion.div
          key={question.id}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -12 }}
          transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
        >
          <Card className="mt-4 p-6">
            {question.passage_zh && (
              <p className="hanzi whitespace-pre-line text-lg leading-relaxed text-ink">
                {question.passage_zh}
              </p>
            )}
            {question.statement_zh && (
              <p className="hanzi mt-4 border-t border-border-soft pt-4 text-lg font-semibold text-ink">
                {question.statement_zh}
              </p>
            )}
            {question.sentence_zh && (
              <p className="hanzi text-xl leading-relaxed text-ink">{question.sentence_zh}</p>
            )}
            {question.question_zh && (
              <p className="hanzi mt-4 border-t border-border-soft pt-4 text-base font-semibold text-ink">
                {question.question_zh}
              </p>
            )}
            {part.question_type === "sentence_reordering" && (
              <p className="text-sm text-ink-soft">
                Bấm các vế theo thứ tự đúng để ghép thành đoạn có nghĩa.
              </p>
            )}
          </Card>
        </motion.div>
      </AnimatePresence>

      {/* ---------------------------------------------------- true / false -- */}
      {part.question_type === "judge_true_false" && (
        <div className="mt-4 grid grid-cols-2 gap-3">
          {[
            { value: true, label: "Đúng", zh: "对" },
            { value: false, label: "Sai", zh: "错" },
          ].map((choice) => (
            <button
              key={choice.zh}
              onClick={() => void submit(choice.value)}
              disabled={answered || busy}
              className={clsx(
                "rounded-xl border px-4 py-4 text-center transition-colors duration-200",
                !answered && "border-border bg-surface text-ink hover:border-accent/50",
                answered && "border-border bg-surface text-ink-faint opacity-70"
              )}
            >
              <span className="hanzi block text-xl font-bold">{choice.zh}</span>
              <span className="mt-0.5 block text-xs">{choice.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* --------------------------------------------------- word bank fill -- */}
      {part.question_type === "fill_in_blank_sentence" && part.word_bank && (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {part.word_bank.map((word) => (
            <button
              key={word.key}
              onClick={() => {
                setPicked(word.word_zh);
                void submit(word.word_zh);
              }}
              disabled={answered || busy}
              className={clsx(
                "rounded-xl border px-3 py-3 text-center transition-colors duration-200",
                !answered && "border-border bg-surface hover:border-accent/50",
                answered && picked === word.word_zh && verdict?.is_correct && "border-jade bg-jade-soft",
                answered && picked === word.word_zh && !verdict?.is_correct && "border-danger bg-danger-soft",
                answered && picked !== word.word_zh && "border-border bg-surface opacity-60"
              )}
            >
              <span className="text-[11px] font-semibold text-ink-faint">{word.key}</span>
              <span className="hanzi mt-0.5 block text-base font-semibold text-ink">{word.word_zh}</span>
            </button>
          ))}
        </div>
      )}

      {/* ------------------------------------------------------ multiple choice -- */}
      {question.options && (
        <div className="mt-4 grid grid-cols-1 gap-3">
          {question.options.map((option) => (
            <button
              key={option.key}
              onClick={() => {
                setPicked(option.text_zh);
                void submit(option.text_zh);
              }}
              disabled={answered || busy}
              className={clsx(
                "flex items-center gap-3 rounded-xl border px-4 py-3.5 text-left transition-colors duration-200",
                !answered && "border-border bg-surface hover:border-accent/50",
                answered && picked === option.text_zh && verdict?.is_correct && "border-jade bg-jade-soft",
                answered && picked === option.text_zh && !verdict?.is_correct && "border-danger bg-danger-soft",
                answered && picked !== option.text_zh && "border-border bg-surface opacity-60"
              )}
            >
              <span className="text-xs font-bold text-ink-faint">{option.key}</span>
              <span className="hanzi text-base text-ink">{option.text_zh}</span>
            </button>
          ))}
        </div>
      )}

      {/* --------------------------------------------------------- reordering -- */}
      {part.question_type === "sentence_reordering" && question.words_zh && (
        <>
          <div className="mt-4 space-y-2">
            {question.words_zh.map((clause) => {
              const position = ordered.indexOf(clause);
              return (
                <button
                  key={clause}
                  onClick={() => toggleClause(clause)}
                  disabled={answered}
                  className={clsx(
                    "flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left transition-colors duration-200",
                    position >= 0
                      ? "border-accent bg-accent-soft"
                      : "border-border bg-surface hover:border-accent/50",
                    answered && "opacity-70"
                  )}
                >
                  <span
                    className={clsx(
                      "tnum flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold",
                      position >= 0 ? "bg-accent text-accent-ink" : "bg-surface-2 text-ink-faint"
                    )}
                  >
                    {position >= 0 ? position + 1 : "·"}
                  </span>
                  <span className="hanzi text-base text-ink">{clause}</span>
                </button>
              );
            })}
          </div>
          {!answered && (
            <Button
              className="mt-4 w-full"
              size="lg"
              onClick={() => void submit(ordered)}
              disabled={busy || ordered.length !== question.words_zh.length}
            >
              {ordered.length === question.words_zh.length
                ? "Kiểm tra thứ tự"
                : `Còn ${question.words_zh.length - ordered.length} vế chưa chọn`}
            </Button>
          )}
        </>
      )}

      {verdict && (
        <Card
          className={clsx("mt-4 p-5", verdict.is_correct ? "border-jade/40" : "border-danger/40")}
          role="status"
        >
          <div className="flex items-center gap-2">
            {verdict.is_correct ? (
              <IconCheck className="h-4 w-4 text-jade" />
            ) : (
              <IconX className="h-4 w-4 text-danger" />
            )}
            <p className={clsx("text-sm font-semibold", verdict.is_correct ? "text-jade" : "text-danger")}>
              {verdict.is_correct ? "Chính xác" : "Chưa đúng"}
            </p>
          </div>
          {!verdict.is_correct && (
            <p className="hanzi mt-2 text-base text-ink">Đáp án: {verdict.correct_answer}</p>
          )}
          <p className="mt-2 text-sm text-ink-soft">{verdict.explanation_vi}</p>
        </Card>
      )}

      {answered && (
        <Button className="mt-4 w-full" size="lg" onClick={next}>
          {index + 1 >= slots.length ? "Sang phần thi nói" : "Câu tiếp theo"}
        </Button>
      )}
    </div>
  );
}
