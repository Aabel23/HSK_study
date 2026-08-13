import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../lib/api";
import { useApi } from "../lib/useApi";
import { useSettings } from "../lib/settings";
import { useToast } from "../lib/toast";
import { usePlayAudio } from "../lib/useAudio";
import { useRecorder } from "../lib/useRecorder";
import { formatNumber, formatPercent } from "../lib/format";
import type {
  HskkExamLevel,
  HskkItem,
  HskkLevelFormat,
  HskkPaper,
  HskkPart,
  HskkResult,
  HskkSelfRating,
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
  StatTile,
} from "../components/ui";
import {
  IconCheck,
  IconClipboard,
  IconEye,
  IconMic,
  IconPause,
  IconPlay,
  IconRefresh,
  IconStop,
  IconTarget,
  IconTrophy,
  IconX,
} from "../components/icons";

/** One flattened question plus the part it belongs to, so the runner is a plain list. */
interface Slot {
  part: HskkPart;
  item: HskkItem;
  /** 1-based position across the whole paper, for the progress bar. */
  position: number;
}

const RATINGS: Array<{ value: HskkSelfRating; label: string; hint: string; tone: "jade" | "gold" | "danger" }> = [
  { value: "good", label: "Trôi chảy", hint: "Nói được trọn vẹn, không vấp", tone: "jade" },
  { value: "ok", label: "Tạm được", hint: "Có ngập ngừng hoặc thiếu ý", tone: "gold" },
  { value: "bad", label: "Còn vấp", hint: "Nói được rất ít", tone: "danger" },
];

function flatten(paper: HskkPaper): Slot[] {
  const slots: Slot[] = [];
  for (const part of paper.parts) {
    for (const item of part.items) slots.push({ part, item, position: slots.length + 1 });
  }
  return slots;
}

function clock(totalSeconds: number): string {
  const safe = Math.max(0, Math.round(totalSeconds));
  return `${Math.floor(safe / 60)}:${String(safe % 60).padStart(2, "0")}`;
}

/** Parts 1 and 2 must be *heard* first; parts 3 (and the picture task) are read. */
function isHeard(part: HskkPart): boolean {
  return part.kind === "repeat" || part.kind === "answer";
}

export default function Hskk() {
  const { settings } = useSettings();
  const toast = useToast();
  const { play, playingText } = usePlayAudio();
  const recorder = useRecorder();

  const [examLevel, setExamLevel] = useState<HskkExamLevel>("beginner");
  const [paper, setPaper] = useState<HskkPaper | null>(null);
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [result, setResult] = useState<HskkResult | null>(null);
  const [busy, setBusy] = useState(false);

  const levels = useApi(() => api.hskk.levels(), []);
  const stats = useApi(() => api.hskk.stats(), []);

  const slots = useMemo(() => (paper ? flatten(paper) : []), [paper]);
  const slot = slots[index];
  const format = levels.data?.items.find((entry) => entry.code === examLevel);

  // Countdown for the current question. It mirrors the real exam's fixed answer
  // window, and stops the recording when the window closes.
  const stopRecorder = recorder.stop;
  useEffect(() => {
    if (remaining === null) return;
    if (remaining <= 0) {
      stopRecorder();
      setRemaining(null);
      return;
    }
    const timer = window.setTimeout(() => setRemaining((value) => (value === null ? null : value - 1)), 1000);
    return () => window.clearTimeout(timer);
  }, [remaining, stopRecorder]);

  // A new question starts clean: no leftover clip, no revealed answer, and the
  // heard parts play themselves once so the learner never reads them first.
  const audioText = slot?.item.audio_text ?? null;
  const resetRecorder = recorder.reset;
  useEffect(() => {
    if (!slot) return;
    resetRecorder();
    setRevealed(false);
    setRemaining(null);
    if (audioText && settings.autoplay_audio) play(audioText, { voice: settings.audio_voice });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slot?.item.question_id]);

  const startExam = useCallback(async () => {
    setBusy(true);
    try {
      const next = await api.hskk.createSession(examLevel);
      setPaper(next);
      setIndex(0);
      setResult(null);
    } catch (error) {
      toast.error("Không tạo được đề thi thử", error instanceof Error ? error.message : undefined);
    } finally {
      setBusy(false);
    }
  }, [examLevel, toast]);

  const finish = useCallback(
    async (sessionId: number) => {
      recorder.reset();
      try {
        setResult(await api.hskk.complete(sessionId));
        stats.reload();
      } catch (error) {
        toast.error("Không nộp được bài", error instanceof Error ? error.message : undefined);
      }
    },
    [recorder, stats, toast]
  );

  async function rate(value: HskkSelfRating) {
    if (!paper || !slot || busy) return;
    setBusy(true);
    recorder.stop();
    setRemaining(null);
    try {
      await api.hskk.answer(
        paper.session_id,
        slot.part.part,
        slot.item.question_index,
        slot.item.question_id,
        value,
        recorder.seconds
      );
      if (index + 1 >= slots.length) await finish(paper.session_id);
      else setIndex(index + 1);
    } catch (error) {
      toast.error("Không lưu được câu trả lời", error instanceof Error ? error.message : undefined);
    } finally {
      setBusy(false);
    }
  }

  function toggleRecording() {
    if (!slot) return;
    if (recorder.recording) {
      recorder.stop();
      setRemaining(null);
      return;
    }
    void recorder.start();
    setRemaining(slot.part.answer_seconds);
    // Once you have spoken there is no reason to hide the prompt any more.
    setRevealed(true);
  }

  // Keyboard shortcuts, kept off while a field has focus (there are none on this
  // page today, but the guard keeps it true if one is added).
  const ratingRef = useRef(rate);
  ratingRef.current = rate;
  useEffect(() => {
    if (!paper || result) return;
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA"].includes(target.tagName)) return;
      if (event.key === "1") void ratingRef.current("good");
      if (event.key === "2") void ratingRef.current("ok");
      if (event.key === "3") void ratingRef.current("bad");
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [paper, result]);

  if (levels.error) return <ErrorState message={levels.error} onRetry={levels.reload} />;
  if (levels.loading && !levels.data) return <PageSkeleton tiles={4} rows={2} />;

  // ---------------------------------------------------------------- result --
  if (result) {
    return (
      <div className="animate-float-in mx-auto max-w-2xl">
        <Card className="flex flex-col items-center gap-5 px-6 py-10 text-center">
          <ProgressRing value={result.percent} accent={result.passed ? "jade" : "gold"} size={150}>
            <span className="font-display tnum text-3xl font-bold text-ink">{result.score}</span>
            <span className="text-xs text-ink-faint">/ {result.max_score} điểm</span>
          </ProgressRing>
          <div>
            <p className="font-display text-2xl font-bold text-ink">
              {result.passed ? "Đạt" : "Chưa đạt"}
            </p>
            <p className="mt-1 text-sm text-ink-soft">{result.band}</p>
            <p className="mt-1 text-xs text-ink-faint">
              Điểm đỗ: {result.pass_score} · Đã trả lời {formatNumber(result.answered_items)}/
              {formatNumber(result.total_items)} câu
            </p>
          </div>

          <div className="w-full space-y-2 border-t border-border-soft pt-5 text-left">
            {result.parts.map((part) => (
              <div key={part.part} className="flex items-center gap-3">
                <span className="w-24 shrink-0 text-xs text-ink-faint">Phần {part.part}</span>
                <span className="flex-1 truncate text-sm text-ink">{part.title}</span>
                <ProgressBar value={part.max_score ? (part.score / part.max_score) * 100 : 0} accent="accent" />
                <span className="tnum w-20 shrink-0 text-right text-sm font-semibold text-ink-soft">
                  {part.score}/{part.max_score}
                </span>
              </div>
            ))}
          </div>

          <p className="max-w-md text-xs text-ink-faint">
            Điểm dựa trên phần bạn tự đánh giá, vì bài nói không thể chấm tự động. Nghe lại bản ghi
            của chính mình là cách nhanh nhất để thấy chỗ cần sửa.
          </p>

          <div className="flex flex-wrap justify-center gap-3">
            <Button onClick={startExam} disabled={busy}>
              <IconRefresh className="h-4 w-4" /> Thi lại đề mới
            </Button>
            <Button variant="secondary" onClick={() => { setPaper(null); setResult(null); }}>
              Về trang thi thử
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  // ------------------------------------------------------------------ intro --
  if (!paper || !slot) {
    return (
      <div className="animate-float-in">
        <PageHeader
          eyebrow="Kỹ năng nói"
          title="Thi thử HSKK"
          description="Đề mô phỏng đúng cấu trúc kỳ thi khẩu ngữ HSKK: đủ số phần, số câu, thang điểm và thời gian trả lời. Mỗi lần thi là một đề khác, ghép từ ngân hàng câu hỏi."
        />

        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatTile
            label="Điểm cao nhất"
            value={formatPercent(stats.data?.best_percent, 0)}
            hint="Trên thang 100"
            accent="jade"
            icon={<IconTrophy className="h-4 w-4" />}
          />
          <StatTile
            label="Điểm lần gần nhất"
            value={formatPercent(stats.data?.last_percent, 0)}
            accent="accent"
            icon={<IconTarget className="h-4 w-4" />}
          />
          <StatTile
            label="Điểm trung bình"
            value={formatPercent(stats.data?.average_percent, 0)}
            accent="sky"
          />
          <StatTile label="Lượt thi đã nộp" value={formatNumber(stats.data?.sessions)} accent="violet" />
        </div>

        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          {levels.data?.items.map((entry) => (
            <button
              key={entry.code}
              onClick={() => setExamLevel(entry.code)}
              aria-pressed={examLevel === entry.code}
              className={clsx(
                "rounded-xl border px-5 py-4 text-left transition-colors duration-200",
                examLevel === entry.code
                  ? "border-accent bg-accent-soft"
                  : "border-border bg-surface hover:border-border-strong"
              )}
            >
              <div className="flex items-center gap-2">
                <p className={clsx("font-display text-base font-bold", examLevel === entry.code ? "text-accent" : "text-ink")}>
                  {entry.label}
                </p>
                <Badge tone="gold">{entry.hsk_range}</Badge>
              </div>
              <p className="mt-1 text-xs text-ink-soft">{entry.blurb}</p>
            </button>
          ))}
        </div>

        {format && <FormatTable format={format} />}

        <Card className="mt-6 p-6">
          <h2 className="font-display text-lg font-bold text-ink">Trước khi bắt đầu</h2>
          <ul className="mt-3 space-y-1.5 text-sm text-ink-soft">
            <li>· Bài nói được ghi âm ngay trong trình duyệt để bạn nghe lại, không gửi đi đâu cả.</li>
            <li>· Mỗi câu có đồng hồ đếm ngược đúng bằng thời gian trả lời của đề thật.</li>
            <li>· Sau mỗi câu bạn tự chấm, vì không có cách nào chấm phát âm tự động.</li>
            {!recorder.supported && (
              <li className="text-gold">
                · Trình duyệt này không ghi âm được (cần HTTPS hoặc localhost) — bài thi vẫn chạy
                bình thường, chỉ không nghe lại được.
              </li>
            )}
          </ul>
          <Button size="lg" className="mt-6 w-full sm:w-auto" onClick={startExam} disabled={busy}>
            <IconClipboard className="h-4 w-4" /> Bắt đầu thi thử
          </Button>
        </Card>
      </div>
    );
  }

  // ------------------------------------------------------------------- exam --
  const heard = isHeard(slot.part);
  const showPrompt = revealed || !heard;
  const partIndex = slot.item.question_index + 1;

  return (
    <div className="animate-float-in mx-auto max-w-2xl">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Badge tone="accent">
          Phần {slot.part.part} · {slot.part.title}
        </Badge>
        <span className="tnum text-xs font-semibold text-ink-soft">
          Câu {partIndex}/{slot.part.items.length}
        </span>
        <span className="ml-auto tnum text-xs text-ink-faint">
          {slot.position}/{slots.length} toàn bài · {slot.part.points_per_item} điểm/câu
        </span>
      </div>
      <ProgressBar value={((slot.position - 1) / slots.length) * 100} accent="accent" />

      <p className="mt-3 text-xs text-ink-faint">{slot.part.instruction_vi}</p>

      <AnimatePresence mode="wait">
        <motion.div
          key={slot.item.question_id}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -12 }}
          transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
        >
          <Card className="mt-4 flex flex-col items-center gap-4 p-8">
            {heard && (
              <>
                <button
                  onClick={() => audioText && play(audioText, { voice: settings.audio_voice })}
                  className="flex h-20 w-20 items-center justify-center rounded-full bg-accent text-accent-ink shadow-lift transition-transform duration-200 active:scale-95"
                  aria-label="Nghe lại đề"
                >
                  {playingText === audioText ? <IconPause className="h-8 w-8" /> : <IconPlay className="h-8 w-8" />}
                </button>
                <p className="text-sm text-ink-faint">
                  {slot.part.kind === "repeat" ? "Nghe rồi nhắc lại nguyên văn" : "Nghe rồi trả lời"}
                </p>
              </>
            )}

            {showPrompt ? (
              <div className="text-center">
                <p className="hanzi text-2xl font-bold leading-relaxed text-ink">{slot.item.hanzi}</p>
                <p className="mt-2 text-sm font-medium text-gold">{slot.item.pinyin}</p>
                <p className="mt-2 text-sm text-ink-soft">{slot.item.vi}</p>
              </div>
            ) : (
              <Button variant="secondary" onClick={() => setRevealed(true)}>
                <IconEye className="h-4 w-4" /> Xem lời đề
              </Button>
            )}

            {slot.item.hints.length > 0 && showPrompt && (
              <div className="w-full rounded-xl border border-border-soft bg-surface-2 p-4">
                <p className="text-xs font-semibold text-ink-soft">Gợi ý bố cục</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {slot.item.hints.map((hint) => (
                    <span key={hint} className="hanzi rounded-lg border border-border px-2.5 py-1 text-sm text-ink-soft">
                      {hint}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {slot.part.min_sentences && (
              <p className="text-xs text-ink-faint">Cần nói ít nhất {slot.part.min_sentences} câu.</p>
            )}
          </Card>
        </motion.div>
      </AnimatePresence>

      <Card className="mt-4 flex flex-col items-center gap-3 p-6">
        <button
          onClick={toggleRecording}
          disabled={!recorder.supported}
          className={clsx(
            "flex h-16 w-16 items-center justify-center rounded-full transition-transform duration-200 active:scale-95",
            recorder.recording ? "bg-danger text-white animate-pulse" : "bg-surface-2 text-ink border border-border",
            !recorder.supported && "opacity-50"
          )}
          aria-label={recorder.recording ? "Dừng ghi âm" : "Bắt đầu ghi âm"}
        >
          {recorder.recording ? <IconStop className="h-6 w-6" /> : <IconMic className="h-6 w-6" />}
        </button>
        <div className="flex items-center gap-3 text-sm">
          <span className="tnum font-semibold text-ink">{clock(recorder.seconds)}</span>
          <span className="text-ink-faint">
            {remaining !== null
              ? `còn ${clock(remaining)}`
              : `tối đa ${clock(slot.part.answer_seconds)}`}
          </span>
        </div>
        {recorder.error && <p className="text-xs text-danger">{recorder.error}</p>}
        {recorder.clipUrl && (
          <audio controls src={recorder.clipUrl} className="w-full max-w-sm" aria-label="Nghe lại bài nói của bạn" />
        )}
      </Card>

      <div className="mt-4 grid grid-cols-3 gap-3">
        {RATINGS.map((entry) => (
          <button
            key={entry.value}
            onClick={() => void rate(entry.value)}
            disabled={busy}
            className={clsx(
              "rounded-xl border px-3 py-3.5 text-center transition-colors duration-200 disabled:opacity-60",
              entry.tone === "jade" && "border-jade/50 bg-jade-soft text-jade hover:border-jade",
              entry.tone === "gold" && "border-border bg-surface text-ink hover:border-border-strong",
              entry.tone === "danger" && "border-danger/50 bg-danger-soft text-danger hover:border-danger"
            )}
          >
            <span className="flex items-center justify-center gap-1.5 text-sm font-semibold">
              {entry.tone === "jade" && <IconCheck className="h-4 w-4" />}
              {entry.tone === "danger" && <IconX className="h-4 w-4" />}
              {entry.label}
            </span>
            <span className="mt-0.5 block text-[11px] font-normal text-ink-faint">{entry.hint}</span>
          </button>
        ))}
      </div>

      <div className="mt-4 flex items-center justify-between gap-3">
        <span className="text-xs text-ink-faint">
          <Kbd>1</Kbd> trôi chảy · <Kbd>2</Kbd> tạm được · <Kbd>3</Kbd> còn vấp
        </span>
        <button
          onClick={() => void rate("skipped")}
          disabled={busy}
          className="text-xs font-semibold text-ink-soft transition-colors hover:text-ink"
        >
          Bỏ qua câu này
        </button>
      </div>
    </div>
  );
}

/** The official paper layout, so the learner knows what they are walking into. */
function FormatTable({ format }: { format: HskkLevelFormat }) {
  return (
    <Card className="mt-6 overflow-hidden">
      <div className="flex flex-wrap items-center gap-3 border-b border-border-soft px-6 py-4">
        <h2 className="font-display text-lg font-bold text-ink">Cấu trúc đề {format.label}</h2>
        <Badge tone="neutral">{format.total_items} câu</Badge>
        <Badge tone="neutral">{format.total_points} điểm</Badge>
        <span className="ml-auto text-xs text-ink-faint">
          Chuẩn bị {Math.round(format.prep_seconds / 60)} phút · đỗ từ {format.pass_score} điểm
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[34rem] text-left text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-wide text-ink-faint">
              <th className="px-6 py-2.5 font-semibold">Phần</th>
              <th className="px-3 py-2.5 font-semibold">Dạng đề</th>
              <th className="px-3 py-2.5 font-semibold">Số câu</th>
              <th className="px-3 py-2.5 font-semibold">Thời gian/câu</th>
              <th className="px-6 py-2.5 text-right font-semibold">Điểm</th>
            </tr>
          </thead>
          <tbody>
            {format.parts.map((part) => (
              <tr key={part.part} className="border-t border-border-soft">
                <td className="px-6 py-3 font-semibold text-ink">{part.part}</td>
                <td className="px-3 py-3">
                  <p className="font-medium text-ink">{part.title}</p>
                  <p className="mt-0.5 text-xs text-ink-faint">{part.instruction_vi}</p>
                </td>
                <td className="tnum px-3 py-3 text-ink-soft">{part.count}</td>
                <td className="tnum px-3 py-3 text-ink-soft">{clock(part.answer_seconds)}</td>
                <td className="tnum px-6 py-3 text-right text-ink-soft">{part.total_points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
