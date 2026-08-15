import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../lib/api";
import { useApi } from "../lib/useApi";
import { useLevel } from "../lib/levelContext";
import { useSettings } from "../lib/settings";
import { useToast } from "../lib/toast";
import { usePlayAudio, PLAYBACK_RATES, type PlaybackRate } from "../lib/useAudio";
import { formatNumber, formatPercent, shortMeaning } from "../lib/format";
import type { AnswerResult, HskLevel, TypingItem, TypingMode } from "../lib/types";
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
  IconPause,
  IconPlay,
  IconRefresh,
  IconTarget,
  IconX,
} from "../components/icons";

const MODES: Array<{ value: TypingMode; label: string; blurb: string; answer: "pinyin" | "hanzi" }> = [
  { value: "hanzi_to_pinyin", label: "Chữ Hán → pinyin", blurb: "Nhìn chữ, gõ cách đọc", answer: "pinyin" },
  { value: "audio_to_pinyin", label: "Nghe → pinyin", blurb: "Nghe rồi gõ cách đọc", answer: "pinyin" },
  { value: "meaning_to_pinyin", label: "Nghĩa → pinyin", blurb: "Nhớ lại từ từ nghĩa tiếng Việt", answer: "pinyin" },
  { value: "audio_to_hanzi", label: "Nghe → chữ Hán", blurb: "Khó nhất: gõ lại chữ Hán", answer: "hanzi" },
  { value: "meaning_to_hanzi", label: "Nghĩa → chữ Hán", blurb: "Viết chữ Hán từ nghĩa", answer: "hanzi" },
];

const AUDIO_MODES: TypingMode[] = ["audio_to_pinyin", "audio_to_hanzi"];

export default function Typing() {
  const { level } = useLevel();
  const { settings } = useSettings();
  const toast = useToast();
  const { play, playingText } = usePlayAudio();
  const inputRef = useRef<HTMLInputElement>(null);

  const [mode, setMode] = useState<TypingMode>("hanzi_to_pinyin");
  const [rate, setRate] = useState<PlaybackRate>(1);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [items, setItems] = useState<TypingItem[]>([]);
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [tally, setTally] = useState({ correct: 0, incorrect: 0 });
  const [finished, setFinished] = useState(false);
  const [busy, setBusy] = useState(false);

  const stats = useApi(() => api.typing.stats(), []);
  const current = items[index];
  const modeInfo = useMemo(() => MODES.find((entry) => entry.value === mode)!, [mode]);
  const isAudioMode = AUDIO_MODES.includes(mode);

  const start = useCallback(async () => {
    setBusy(true);
    try {
      const session = await api.typing.createSession(
        level === "all" ? null : (level as HskLevel),
        mode,
        settings.session_size
      );
      setSessionId(session.session_id);
      setItems(session.items);
      setIndex(0);
      setAnswer("");
      setResult(null);
      setTally({ correct: 0, incorrect: 0 });
      setFinished(false);
    } catch (error) {
      toast.error(
        "Không tạo được phiên luyện gõ",
        error instanceof Error ? error.message : undefined
      );
    } finally {
      setBusy(false);
    }
  }, [level, mode, settings.session_size, toast]);

  // Autoplay and focus when a new item appears, so the learner can just type.
  useEffect(() => {
    if (!current) return;
    inputRef.current?.focus();
    if (isAudioMode && current.prompt.audio_text && settings.autoplay_audio) {
      play(current.prompt.audio_text, { voice: settings.audio_voice, rate });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.item_id]);

  async function submit() {
    if (!current || result || busy) return;
    setBusy(true);
    try {
      const outcome = await api.typing.check(sessionId, current.vocabulary_id, mode, answer);
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

  async function next() {
    if (!sessionId) return;
    if (index + 1 >= items.length) {
      await api.typing.complete(sessionId, items.length, tally.correct, tally.incorrect);
      setFinished(true);
      stats.reload();
      return;
    }
    setIndex(index + 1);
    setAnswer("");
    setResult(null);
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key !== "Enter") return;
    event.preventDefault();
    if (result) void next();
    else void submit();
  }

  if (stats.error) return <ErrorState message={stats.error} onRetry={stats.reload} />;
  if (stats.loading && !stats.data && !sessionId) return <PageSkeleton tiles={3} rows={1} />;

  if (!sessionId) {
    return (
      <div className="animate-float-in">
        <PageHeader
          eyebrow="Chủ động ghi nhớ"
          title="Luyện gõ"
          description="Trắc nghiệm chỉ cần nhận ra; gõ lại buộc bạn phải nhớ được. Chấp nhận cả pinyin có dấu (nǐ hǎo), số thanh điệu (ni3hao3) hoặc không dấu."
        />

        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatTile label="Lượt đã gõ" value={formatNumber(stats.data?.attempts)} accent="accent" />
          <StatTile label="Chính xác" value={formatPercent(stats.data?.accuracy, 1)} accent="jade" icon={<IconTarget className="h-4 w-4" />} />
          <StatTile label="Phiên hoàn tất" value={formatNumber(stats.data?.sessions)} accent="sky" />
          <StatTile label="Gõ đúng" value={formatNumber(stats.data?.correct)} accent="gold" />
        </div>

        <Card className="mt-8 p-6">
          <h2 className="font-display text-lg font-bold text-ink">Chọn kiểu luyện</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {MODES.map((entry) => (
              <button
                key={entry.value}
                onClick={() => setMode(entry.value)}
                aria-pressed={mode === entry.value}
                className={clsx(
                  "rounded-xl border px-4 py-3.5 text-left transition-colors duration-200",
                  mode === entry.value
                    ? "border-accent bg-accent-soft"
                    : "border-border bg-surface hover:border-border-strong"
                )}
              >
                <p className={clsx("text-sm font-semibold", mode === entry.value ? "text-accent" : "text-ink")}>
                  {entry.label}
                </p>
                <p className="mt-0.5 text-xs text-ink-soft">{entry.blurb}</p>
              </button>
            ))}
          </div>

          {AUDIO_MODES.includes(mode) && (
            <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-border-soft pt-4">
              <span className="text-sm text-ink-soft">Tốc độ phát</span>
              <Segmented
                label="Tốc độ phát"
                value={String(rate)}
                onChange={(value) => setRate(Number(value) as PlaybackRate)}
                options={PLAYBACK_RATES.map((value) => ({ value: String(value), label: `${value}×` }))}
              />
            </div>
          )}

          <Button size="lg" className="mt-6 w-full sm:w-auto" onClick={start} disabled={busy}>
            <IconCheck className="h-4 w-4" /> Bắt đầu {settings.session_size} từ
          </Button>
        </Card>

        {stats.data && stats.data.modes.length > 0 && (
          <Card className="mt-6 p-6">
            <h2 className="font-display text-lg font-bold text-ink">Độ chính xác theo kiểu</h2>
            <div className="mt-4 flex flex-col gap-3">
              {stats.data.modes.map((entry) => (
                <div key={entry.mode}>
                  <div className="mb-1.5 flex items-center justify-between text-sm">
                    <span className="text-ink-soft">{entry.label}</span>
                    <span className="tnum font-semibold text-ink">{formatPercent(entry.accuracy, 1)}</span>
                  </div>
                  <ProgressBar value={entry.accuracy} accent={entry.accuracy >= 80 ? "jade" : "gold"} />
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    );
  }

  if (finished) {
    const accuracy = items.length ? (tally.correct / items.length) * 100 : 0;
    return (
      <Card className="animate-float-in mx-auto mt-6 flex max-w-md flex-col items-center gap-5 px-6 py-12 text-center">
        <ProgressRing value={accuracy} accent="jade" size={140}>
          <span className="font-display tnum text-3xl font-bold text-jade">{Math.round(accuracy)}%</span>
          <span className="text-xs text-ink-faint">chính xác</span>
        </ProgressRing>
        <div>
          <p className="font-display text-2xl font-bold text-ink">Hoàn thành phiên gõ</p>
          <p className="mt-1 text-sm text-ink-soft">
            {formatNumber(tally.correct)} đúng · {formatNumber(tally.incorrect)} sai
          </p>
        </div>
        <div className="flex flex-wrap justify-center gap-3">
          <Button onClick={start}>
            <IconRefresh className="h-4 w-4" /> Luyện tiếp
          </Button>
          <Button variant="secondary" onClick={() => setSessionId(null)}>
            Đổi kiểu luyện
          </Button>
        </div>
      </Card>
    );
  }

  const progress = items.length ? (index / items.length) * 100 : 0;

  return (
    <div className="animate-float-in mx-auto max-w-2xl">
      <div className="mb-4 flex items-center gap-4">
        <ProgressBar value={progress} accent="accent" />
        <span className="tnum shrink-0 text-xs font-semibold text-ink-soft">
          {index + 1} / {items.length}
        </span>
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={current?.item_id}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -12 }}
          transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
        >
          <Card className="p-6 sm:p-8">
            <div className="flex items-center justify-between gap-3">
              <Badge tone="accent">{modeInfo.label}</Badge>
              <Badge tone="neutral">HSK {current?.hsk_level}</Badge>
            </div>

            <div className="flex min-h-[136px] flex-col items-center justify-center gap-3 py-6 text-center">
              {isAudioMode ? (
                <>
                  <button
                    onClick={() =>
                      current?.prompt.audio_text &&
                      play(current.prompt.audio_text, { voice: settings.audio_voice, rate })
                    }
                    className="flex h-20 w-20 items-center justify-center rounded-full bg-accent text-accent-ink shadow-lift transition-transform duration-200 active:scale-95"
                    aria-label="Phát lại âm thanh"
                  >
                    {playingText === current?.prompt.audio_text ? (
                      <IconPause className="h-8 w-8" />
                    ) : (
                      <IconPlay className="h-8 w-8" />
                    )}
                  </button>
                  <Segmented
                    label="Tốc độ phát"
                    value={String(rate)}
                    onChange={(value) => setRate(Number(value) as PlaybackRate)}
                    options={PLAYBACK_RATES.map((value) => ({ value: String(value), label: `${value}×` }))}
                  />
                </>
              ) : (
                <>
                  {current?.prompt.hanzi && (
                    <p className="hanzi text-6xl font-bold leading-none text-ink">{current.prompt.hanzi}</p>
                  )}
                  {current?.prompt.meaning && (
                    <p
                      className={clsx(current?.prompt.hanzi ? "text-sm text-ink-soft" : "text-2xl font-semibold text-ink")}
                      title={current.prompt.meaning}
                    >
                      {/* The prompt has to fit on one screen. A full CVDICT
                          entry set at text-2xl pushes the input box out of
                          view, so the leading senses stand in and the whole
                          gloss is revealed with the answer. */}
                      {shortMeaning(current.prompt.meaning, { senses: 3, chars: 110 })}
                    </p>
                  )}
                  {current?.prompt.pinyin && <p className="text-lg text-accent">{current.prompt.pinyin}</p>}
                </>
              )}
            </div>

            <input
              ref={inputRef}
              value={answer}
              onChange={(event) => setAnswer(event.target.value)}
              onKeyDown={onKeyDown}
              disabled={Boolean(result)}
              autoComplete="off"
              autoCorrect="off"
              spellCheck={false}
              aria-label={modeInfo.answer === "pinyin" ? "Gõ pinyin" : "Gõ chữ Hán"}
              placeholder={modeInfo.answer === "pinyin" ? "ví dụ: ni3hao3 hoặc nǐ hǎo" : "gõ chữ Hán..."}
              className={clsx(
                "w-full rounded-xl border bg-surface-2 px-4 py-3.5 text-center text-lg text-ink outline-none transition-colors duration-200 placeholder:text-ink-faint",
                modeInfo.answer === "hanzi" && "hanzi",
                !result && "border-border focus:border-accent",
                result?.is_correct && "border-jade bg-jade-soft",
                result && !result.is_correct && "border-danger bg-danger-soft"
              )}
            />

            {result && <AnswerFeedback result={result} answerKind={modeInfo.answer} />}

            <div className="mt-5 flex items-center justify-between gap-3">
              <span className="text-xs text-ink-faint">
                <Kbd>Enter</Kbd> {result ? "để tiếp tục" : "để kiểm tra"}
              </span>
              {result ? (
                <Button onClick={next}>Tiếp theo</Button>
              ) : (
                <Button onClick={submit} disabled={busy || !answer.trim()}>
                  Kiểm tra
                </Button>
              )}
            </div>
          </Card>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

function AnswerFeedback({ result, answerKind }: { result: AnswerResult; answerKind: "pinyin" | "hanzi" }) {
  return (
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
          {result.is_correct
            ? result.tones_correct
              ? "Chính xác, cả thanh điệu!"
              : "Đúng âm — nhưng chưa có thanh điệu"
            : "Chưa đúng"}
        </p>
      </div>

      {!result.tones_correct && result.is_correct && answerKind === "pinyin" && (
        <p className="mt-1 text-xs text-ink-soft">
          Thử gõ kèm thanh điệu lần sau, ví dụ <span className="font-mono">ni3hao3</span>.
        </p>
      )}

      <div className="mt-3 flex flex-wrap items-baseline gap-x-3 gap-y-1 border-t border-black/5 pt-3">
        <span className="hanzi text-2xl font-bold text-ink">{result.reveal.hanzi}</span>
        <span className="text-sm font-medium text-accent">{result.reveal.pinyin}</span>
        <span className="text-sm text-ink-soft">{result.reveal.meaning}</span>
      </div>

      {result.character_diff.length > 0 && !result.is_correct && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {result.character_diff.map((entry, position) => (
            <span
              key={position}
              className={clsx(
                "hanzi inline-flex h-9 w-9 items-center justify-center rounded-lg border text-lg",
                entry.correct
                  ? "border-jade/50 bg-jade-soft text-jade"
                  : "border-danger/50 bg-surface text-danger"
              )}
              title={entry.typed ? `Bạn gõ: ${entry.typed}` : "Bạn bỏ trống"}
            >
              {entry.expected}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
