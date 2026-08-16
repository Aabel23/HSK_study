import { useCallback, useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../lib/api";
import { useApi } from "../lib/useApi";
import { useLevel } from "../lib/levelContext";
import { useSettings } from "../lib/settings";
import { useToast } from "../lib/toast";
import { PLAYBACK_RATES, usePlayAudio, type PlaybackRate } from "../lib/useAudio";
import { distinctOptionLabels, formatNumber, formatPercent } from "../lib/format";
import { useShortcuts } from "../lib/useShortcuts";
import type {
  AnswerResult,
  DictationItem,
  DictationMode,
  HskLevel,
  ListeningItem,
  ListeningMode,
  QuizOption,
} from "../lib/types";
import {
  Badge,
  Button,
  Card,
  ErrorState,
  Kbd,
  PageHeader,
  PageSkeleton,
  ProgressBar,
  ProgressRing,
  Segmented,
  StatTile,
} from "../components/ui";
import {
  IconCheck,
  IconHeadphones,
  IconPause,
  IconPlay,
  IconRefresh,
  IconTarget,
  IconX,
} from "../components/icons";

/** Recognition drills answer with a tap; dictation drills answer with the keyboard. */
type Drill =
  | { kind: "choice"; mode: ListeningMode; label: string; blurb: string }
  | { kind: "dictation"; mode: DictationMode; label: string; blurb: string };

const DRILLS: Drill[] = [
  { kind: "choice", mode: "audio_to_meaning", label: "Nghe → chọn nghĩa", blurb: "Khởi động: nhận ra từ vừa nghe" },
  { kind: "choice", mode: "audio_to_hanzi", label: "Nghe → chọn Hán tự", blurb: "Gắn âm thanh với mặt chữ" },
  { kind: "dictation", mode: "word_pinyin", label: "Nghe chép: pinyin", blurb: "Gõ lại cách đọc, không có gợi ý" },
  { kind: "dictation", mode: "word_hanzi", label: "Nghe chép: chữ Hán", blurb: "Nghe từ và viết lại chữ" },
  { kind: "dictation", mode: "sentence_hanzi", label: "Nghe chép cả câu", blurb: "Khó nhất: chép lại nguyên câu" },
];

export default function Listening() {
  const { level } = useLevel();
  const { settings } = useSettings();
  const toast = useToast();
  const { play, playingText, playCount, resetCount } = usePlayAudio();
  const inputRef = useRef<HTMLInputElement>(null);

  const [drill, setDrill] = useState<Drill>(DRILLS[0]);
  const [rate, setRate] = useState<PlaybackRate>(1);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [choiceItems, setChoiceItems] = useState<ListeningItem[]>([]);
  const [dictationItems, setDictationItems] = useState<DictationItem[]>([]);
  const [index, setIndex] = useState(0);
  const [picked, setPicked] = useState<number | null>(null);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [tally, setTally] = useState({ correct: 0, incorrect: 0 });
  const [finished, setFinished] = useState(false);
  const [busy, setBusy] = useState(false);

  const listeningStats = useApi(() => api.listening.stats(), []);
  const dictationStats = useApi(() => api.dictation.stats(), []);

  const isDictation = drill.kind === "dictation";
  const total = isDictation ? dictationItems.length : choiceItems.length;
  const currentChoice = choiceItems[index];
  // Shortened as a set: two options collapsing to the same text would leave the
  // question with no answerable difference between them.
  const choiceLabels = distinctOptionLabels(
    (currentChoice?.options ?? []).map((option) => option.label)
  );
  const currentDictation = dictationItems[index];
  const audioText = isDictation ? currentDictation?.audio_text : currentChoice?.audio_text;

  const start = useCallback(
    async (selected: Drill) => {
      setBusy(true);
      try {
        const hskLevel = level === "all" ? null : (level as HskLevel);
        const count = Math.min(settings.session_size, 20);
        if (selected.kind === "choice") {
          const session = await api.listening.createSession(hskLevel, selected.mode, count);
          setSessionId(session.session_id);
          setChoiceItems(session.items);
          setDictationItems([]);
        } else {
          const session = await api.dictation.createSession(hskLevel, selected.mode, count);
          setSessionId(session.session_id);
          setDictationItems(session.items);
          setChoiceItems([]);
        }
        setDrill(selected);
        setIndex(0);
        setPicked(null);
        setAnswer("");
        setResult(null);
        setTally({ correct: 0, incorrect: 0 });
        setFinished(false);
      } catch (error) {
        toast.error("Không tạo được phiên nghe", error instanceof Error ? error.message : undefined);
      } finally {
        setBusy(false);
      }
    },
    [level, settings.session_size, toast]
  );

  // Autoplay each new item and reset the replay counter that dictation grades on.
  useEffect(() => {
    if (!audioText) return;
    resetCount();
    if (settings.autoplay_audio) play(audioText, { voice: settings.audio_voice, rate });
    if (isDictation) inputRef.current?.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [audioText]);

  async function choose(option: QuizOption) {
    if (!sessionId || picked !== null || !currentChoice) return;
    setPicked(option.vocabulary_id);
    const isCorrect = option.vocabulary_id === currentChoice.target_vocabulary_id;
    setTally((previous) =>
      isCorrect
        ? { ...previous, correct: previous.correct + 1 }
        : { ...previous, incorrect: previous.incorrect + 1 }
    );
    try {
      await api.listening.attempt(
        sessionId,
        currentChoice.target_vocabulary_id,
        drill.mode as ListeningMode,
        isCorrect
      );
    } catch {
      toast.error("Không lưu được kết quả");
    }
  }

  async function submitDictation() {
    if (!sessionId || !currentDictation || result || busy) return;
    setBusy(true);
    try {
      const outcome = await api.dictation.check(
        sessionId,
        currentDictation.target_id,
        drill.mode as DictationMode,
        answer,
        playCount
      );
      setResult(outcome);
      setTally((previous) =>
        outcome.is_correct
          ? { ...previous, correct: previous.correct + 1 }
          : { ...previous, incorrect: previous.incorrect + 1 }
      );
    } catch (error) {
      toast.error("Không chấm được câu trả lời", error instanceof Error ? error.message : undefined);
    } finally {
      setBusy(false);
    }
  }

  // Space cannot mean "confirm" while the caret is in the answer box — a
  // learner typing "ni hao" needs the space bar to type a space, and the hook's
  // typing guard leaves it alone. Once an answer is graded the box is disabled,
  // so from that point Space and Enter both move on, matching every other
  // screen.
  const answered = isDictation ? Boolean(result) : picked !== null;
  useShortcuts({
    enabled: Boolean(sessionId) && !finished,
    onConfirm: () => {
      if (answered) void next();
    },
    onNext: () => {
      if (answered) void next();
    },
    onPick: (choice) => {
      // Only the multiple-choice drills; the dictation ones want the digit
      // typed into the answer box, and the typing guard already sees to that.
      if (isDictation || picked !== null || !currentChoice) return;
      const option = currentChoice.options[choice - 1];
      if (option) void choose(option);
    },
  });

  async function next() {
    if (!sessionId) return;
    if (index + 1 >= total) {
      const complete = isDictation ? api.dictation.complete : api.listening.complete;
      await complete(sessionId, total, tally.correct, tally.incorrect);
      setFinished(true);
      listeningStats.reload();
      dictationStats.reload();
      return;
    }
    setIndex(index + 1);
    setPicked(null);
    setAnswer("");
    setResult(null);
  }

  if (listeningStats.error) {
    return <ErrorState message={listeningStats.error} onRetry={listeningStats.reload} />;
  }
  if (listeningStats.loading && !listeningStats.data && !sessionId) {
    return <PageSkeleton tiles={4} rows={1} />;
  }

  if (!sessionId) {
    return (
      <div className="animate-float-in">
        <PageHeader
          eyebrow="Kỹ năng nghe"
          title="Luyện nghe"
          description="Từ nhận biết đến nghe chép chính tả. Nghe chép là bài tập khó nhất và cũng hiệu quả nhất, vì không có đáp án nào hiện trên màn hình."
        />

        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatTile
            label="Nghe chép đúng"
            value={formatPercent(dictationStats.data?.accuracy, 1)}
            hint={`${formatNumber(dictationStats.data?.attempts)} lượt`}
            accent="jade"
            icon={<IconTarget className="h-4 w-4" />}
          />
          <StatTile
            label="Đúng ngay lần nghe đầu"
            value={formatPercent(dictationStats.data?.first_listen_rate, 1)}
            hint="Không cần nghe lại"
            accent="accent"
            icon={<IconHeadphones className="h-4 w-4" />}
          />
          <StatTile
            label="Số lần nghe lại trung bình"
            value={dictationStats.data ? dictationStats.data.average_replays.toFixed(1) : "—"}
            hint="Càng thấp càng tốt"
            accent="sky"
          />
          <StatTile
            label="Phiên đã hoàn tất"
            value={formatNumber(
              (dictationStats.data?.sessions ?? 0) + (listeningStats.data?.sessions ?? 0)
            )}
            accent="violet"
          />
        </div>

        <Card className="mt-8 p-6">
          <h2 className="font-display text-lg font-bold text-ink">Chọn bài luyện</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {DRILLS.map((entry) => (
              <button
                key={entry.mode}
                onClick={() => setDrill(entry)}
                aria-pressed={drill.mode === entry.mode}
                className={clsx(
                  "rounded-xl border px-4 py-3.5 text-left transition-colors duration-200",
                  drill.mode === entry.mode
                    ? "border-accent bg-accent-soft"
                    : "border-border bg-surface hover:border-border-strong"
                )}
              >
                <div className="flex items-center gap-2">
                  <p className={clsx("text-sm font-semibold", drill.mode === entry.mode ? "text-accent" : "text-ink")}>
                    {entry.label}
                  </p>
                  {entry.kind === "dictation" && <Badge tone="gold">Gõ</Badge>}
                </div>
                <p className="mt-0.5 text-xs text-ink-soft">{entry.blurb}</p>
              </button>
            ))}
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-border-soft pt-4">
            <span className="text-sm text-ink-soft">Tốc độ phát</span>
            <Segmented
              label="Tốc độ phát"
              value={String(rate)}
              onChange={(value) => setRate(Number(value) as PlaybackRate)}
              options={PLAYBACK_RATES.map((value) => ({ value: String(value), label: `${value}×` }))}
            />
            <span className="text-xs text-ink-faint">Nghe chậm giúp tách âm tiết dễ hơn.</span>
          </div>

          <Button size="lg" className="mt-6 w-full sm:w-auto" onClick={() => start(drill)} disabled={busy}>
            <IconPlay className="h-4 w-4" /> Bắt đầu
          </Button>
        </Card>
      </div>
    );
  }

  if (finished) {
    const accuracy = total ? (tally.correct / total) * 100 : 0;
    return (
      <Card className="animate-float-in mx-auto mt-6 flex max-w-md flex-col items-center gap-5 px-6 py-12 text-center">
        <ProgressRing value={accuracy} accent="jade" size={140}>
          <span className="font-display tnum text-3xl font-bold text-jade">{Math.round(accuracy)}%</span>
          <span className="text-xs text-ink-faint">chính xác</span>
        </ProgressRing>
        <div>
          <p className="font-display text-2xl font-bold text-ink">Hoàn thành!</p>
          <p className="mt-1 text-sm text-ink-soft">
            {formatNumber(tally.correct)} đúng · {formatNumber(tally.incorrect)} sai
          </p>
        </div>
        <div className="flex flex-wrap justify-center gap-3">
          <Button onClick={() => start(drill)}>
            <IconRefresh className="h-4 w-4" /> Luyện tiếp
          </Button>
          <Button variant="secondary" onClick={() => setSessionId(null)}>
            Đổi bài luyện
          </Button>
        </div>
      </Card>
    );
  }

  const progress = total ? (index / total) * 100 : 0;

  return (
    <div className="animate-float-in mx-auto max-w-2xl">
      <div className="mb-4 flex items-center gap-4">
        <ProgressBar value={progress} accent="accent" />
        <span className="tnum shrink-0 text-xs font-semibold text-ink-soft">
          {index + 1} / {total}
        </span>
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={`${drill.mode}-${index}`}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -12 }}
          transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
        >
          <Card className="flex flex-col items-center gap-4 p-8">
            <button
              onClick={() => audioText && play(audioText, { voice: settings.audio_voice, rate })}
              className="flex h-20 w-20 items-center justify-center rounded-full bg-accent text-accent-ink shadow-lift transition-transform duration-200 active:scale-95"
              aria-label="Phát lại âm thanh"
            >
              {playingText === audioText ? <IconPause className="h-8 w-8" /> : <IconPlay className="h-8 w-8" />}
            </button>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <span className="text-sm text-ink-faint">Nhấn để nghe lại</span>
              {isDictation && playCount > 0 && (
                <Badge tone={playCount <= 1 ? "jade" : "neutral"}>Đã nghe {playCount} lần</Badge>
              )}
            </div>
            <Segmented
              label="Tốc độ phát"
              value={String(rate)}
              onChange={(value) => setRate(Number(value) as PlaybackRate)}
              options={PLAYBACK_RATES.map((value) => ({ value: String(value), label: `${value}×` }))}
            />
            {isDictation && currentDictation?.hint.meaning && (
              <p className="max-w-md text-center text-sm text-ink-soft">
                Gợi ý nghĩa: {currentDictation.hint.meaning}
              </p>
            )}
          </Card>
        </motion.div>
      </AnimatePresence>

      {isDictation ? (
        <div className="mt-6">
          <input
            ref={inputRef}
            value={answer}
            onChange={(event) => setAnswer(event.target.value)}
            onKeyDown={(event) => {
              if (event.key !== "Enter") return;
              event.preventDefault();
              if (result) void next();
              else void submitDictation();
            }}
            disabled={Boolean(result)}
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
            aria-label="Gõ lại nội dung bạn nghe được"
            placeholder={
              drill.mode === "word_pinyin"
                ? "gõ pinyin, ví dụ ni3hao3"
                : `gõ lại ${currentDictation?.is_sentence ? "câu" : "từ"} bạn nghe được...`
            }
            className={clsx(
              "w-full rounded-xl border bg-surface-2 px-4 py-3.5 text-center text-lg text-ink outline-none transition-colors duration-200 placeholder:text-ink-faint",
              drill.mode !== "word_pinyin" && "hanzi",
              !result && "border-border focus:border-accent",
              result?.is_correct && "border-jade bg-jade-soft",
              result && !result.is_correct && "border-danger bg-danger-soft"
            )}
          />

          {result && (
            <div
              className={clsx(
                "mt-4 rounded-xl border p-4",
                result.is_correct ? "border-jade/40 bg-jade-soft" : "border-danger/40 bg-danger-soft"
              )}
              role="status"
            >
              <div className="flex items-center gap-2">
                {result.is_correct ? (
                  <IconCheck className="h-4 w-4 text-jade" />
                ) : (
                  <IconX className="h-4 w-4 text-danger" />
                )}
                <p className={clsx("text-sm font-semibold", result.is_correct ? "text-jade" : "text-danger")}>
                  {result.is_correct ? "Chính xác!" : "Chưa đúng"}
                </p>
              </div>
              <div className="mt-3 border-t border-black/5 pt-3">
                <p className="hanzi text-xl font-bold text-ink">{result.reveal.hanzi}</p>
                <p className="mt-1 text-sm font-medium text-accent">{result.reveal.pinyin}</p>
                <p className="mt-1 text-sm text-ink-soft">{result.reveal.meaning}</p>
              </div>
              {!result.is_correct && result.character_diff.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {result.character_diff.map((entry, position) => (
                    <span
                      key={position}
                      title={entry.typed ? `Bạn gõ: ${entry.typed}` : "Bạn bỏ trống"}
                      className={clsx(
                        "hanzi inline-flex h-9 w-9 items-center justify-center rounded-lg border text-lg",
                        entry.correct
                          ? "border-jade/50 bg-jade-soft text-jade"
                          : "border-danger/50 bg-surface text-danger"
                      )}
                    >
                      {entry.expected}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="mt-5 flex items-center justify-between gap-3">
            <span className="text-xs text-ink-faint">
              <Kbd>Enter</Kbd> {result ? "để sang câu tiếp theo" : "để kiểm tra"}
            </span>
            {result ? (
              <Button onClick={next}>Tiếp theo</Button>
            ) : (
              <Button onClick={submitDictation} disabled={busy || !answer.trim()}>
                Kiểm tra
              </Button>
            )}
          </div>
        </div>
      ) : (
        <>
          <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {currentChoice?.options.map((option, position) => {
              const isTarget = option.vocabulary_id === currentChoice.target_vocabulary_id;
              const isPicked = picked === option.vocabulary_id;
              const revealed = picked !== null;
              return (
                <button
                  key={option.vocabulary_id}
                  onClick={() => choose(option)}
                  disabled={revealed}
                  className={clsx(
                    "rounded-xl border px-4 py-3.5 text-left text-sm font-medium transition-colors duration-200",
                    drill.mode === "audio_to_hanzi" && "hanzi text-lg",
                    !revealed && "border-border bg-surface text-ink hover:border-accent/50",
                    revealed && isTarget && "border-jade bg-jade-soft text-jade",
                    revealed && isPicked && !isTarget && "border-danger bg-danger-soft text-danger",
                    revealed && !isPicked && !isTarget && "border-border bg-surface text-ink-faint opacity-60"
                  )}
                >
                  {choiceLabels[position]}
                </button>
              );
            })}
          </div>

          {picked !== null && (
            <Button className="mt-6 w-full" size="lg" onClick={next}>
              Tiếp theo
            </Button>
          )}
        </>
      )}
    </div>
  );
}
