import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../lib/api";
import { useApi } from "../lib/useApi";
import { useSettings } from "../lib/settings";
import { useToast } from "../lib/toast";
import { usePlayAudio } from "../lib/useAudio";
import { useRecorder } from "../lib/useRecorder";
import { useSpeechLog } from "../lib/useSpeechLog";
import { blobToWavBase64 } from "../lib/wav";
import { ReadingRunner } from "../components/ReadingRunner";
import { formatNumber, formatPercent } from "../lib/format";
import type {
  HskkExamLevel,
  HskkGrade,
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
  IconSpark,
  IconStop,
  IconTarget,
  IconTrophy,
  IconX,
} from "../components/icons";

/** One flattened speaking question plus the part it belongs to. */
interface Slot {
  part: HskkPart;
  item: HskkItem;
  /** 1-based position across the speaking half, for the progress bar. */
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

/** Parts 1 and 2 must be *heard* first; part 3 is read off the paper. */
function isHeard(part: HskkPart): boolean {
  return part.kind === "repeat" || part.kind === "answer";
}

type Stage = "intro" | "written" | "speaking" | "result";

export default function Hskk() {
  const { settings } = useSettings();
  const toast = useToast();
  const { play, playingText } = usePlayAudio();
  const recorder = useRecorder();
  const speech = useSpeechLog();

  const [examLevel, setExamLevel] = useState<HskkExamLevel>("beginner");
  const [stage, setStage] = useState<Stage>("intro");
  const [paper, setPaper] = useState<HskkPaper | null>(null);

  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [grade, setGrade] = useState<HskkGrade | null>(null);
  const [grading, setGrading] = useState(false);
  const [result, setResult] = useState<HskkResult | null>(null);
  const [busy, setBusy] = useState(false);
  /**
   * The server forgot this exam — its database was reset while the paper was
   * open (Render's free tier has no persistent disk, so every redeploy wipes
   * it). Nothing the learner does can save the paper, so the runner stops and
   * offers a fresh one instead of firing an identical toast on every answer.
   */
  const [lostSession, setLostSession] = useState(false);

  const isLostSession = (error: unknown) =>
    error instanceof Error && error.message.includes("Không tìm thấy bài thi");

  const levels = useApi(() => api.hskk.levels(), []);
  const stats = useApi(() => api.hskk.stats(), []);

  const slots = useMemo(() => (paper ? flatten(paper) : []), [paper]);
  const slot = slots[index];
  const format = levels.data?.items.find((entry) => entry.code === examLevel);

  // Countdown mirroring the exam's fixed answer window; it stops the recording
  // when the window closes.
  const stopRecorder = recorder.stop;
  const stopSpeech = speech.stop;
  useEffect(() => {
    if (remaining === null) return;
    if (remaining <= 0) {
      stopRecorder();
      stopSpeech();
      setRemaining(null);
      return;
    }
    const timer = window.setTimeout(() => setRemaining((value) => (value === null ? null : value - 1)), 1000);
    return () => window.clearTimeout(timer);
  }, [remaining, stopRecorder, stopSpeech]);

  // A new speaking question starts clean, and the heard parts play themselves
  // once so the learner never reads the prompt first.
  const audioText = slot?.item.audio_text ?? null;
  const resetRecorder = recorder.reset;
  const resetSpeech = speech.reset;
  useEffect(() => {
    if (stage !== "speaking" || !slot) return;
    resetRecorder();
    resetSpeech();
    setRevealed(false);
    setRemaining(null);
    setGrade(null);
    if (audioText && settings.autoplay_audio) play(audioText, { voice: settings.audio_voice });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slot?.item.question_id, stage]);

  const startExam = useCallback(async () => {
    setBusy(true);
    try {
      const next = await api.hskk.createSession(examLevel);
      setPaper(next);
      setStage("written");
      setLostSession(false);
      setIndex(0);
      setGrade(null);
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
        setStage("result");
        stats.reload();
      } catch (error) {
        toast.error("Không nộp được bài", error instanceof Error ? error.message : undefined);
      }
    },
    [recorder, stats, toast]
  );

  // --------------------------------------------------------------- speaking --
  async function requestGrade() {
    if (!paper || !slot || grading) return;
    const transcript = (speech.text || "").trim();
    if (!transcript && !recorder.clipBlob) return;
    setGrading(true);
    try {
      // The transcript is what gets graded; the clip goes along only when it is
      // small enough to be worth the upload, so pronunciation can also be judged.
      let audio: string | null = null;
      if (recorder.clipBlob && recorder.seconds <= 150) {
        try {
          audio = await blobToWavBase64(recorder.clipBlob);
        } catch {
          audio = null; // Grading from the text alone is still useful.
        }
      }
      const graded = await api.hskk.grade(
        paper.session_id,
        slot.part.part,
        slot.item.question_index,
        slot.item.question_id,
        transcript,
        audio,
        recorder.seconds
      );
      setGrade(graded);
      setRevealed(true);
    } catch (error) {
      toast.error(
        "Không chấm được bằng AI",
        error instanceof Error ? error.message : "Bạn vẫn có thể tự chấm câu này."
      );
    } finally {
      setGrading(false);
    }
  }

  const advance = useCallback(async () => {
    if (!paper) return;
    if (index + 1 >= slots.length) await finish(paper.session_id);
    else setIndex(index + 1);
  }, [finish, index, paper, slots.length]);

  async function rate(value: HskkSelfRating) {
    if (!paper || !slot || busy) return;
    setBusy(true);
    recorder.stop();
    speech.stop();
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
      await advance();
    } catch (error) {
      if (isLostSession(error)) setLostSession(true);
      else toast.error("Không lưu được câu trả lời", error instanceof Error ? error.message : undefined);
    } finally {
      setBusy(false);
    }
  }

  async function toggleRecording() {
    if (!slot) return;
    if (recorder.recording) {
      recorder.stop();
      speech.stop();
      setRemaining(null);
      return;
    }
    // The countdown only runs if the microphone actually opened; otherwise the
    // clock would tick down against a recording that never started.
    if (!(await recorder.start())) return;
    // Transcribing in parallel with recording: the clip is for listening back,
    // the log is what gets sent for grading.
    if (speech.supported) speech.start();
    setGrade(null);
    setRemaining(slot.part.answer_seconds);
    // Once you have spoken there is no reason to hide the prompt any more.
    setRevealed(true);
  }

  const ratingRef = useRef(rate);
  ratingRef.current = rate;
  useEffect(() => {
    if (stage !== "speaking") return;
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA"].includes(target.tagName)) return;
      if (event.key === "1") void ratingRef.current("good");
      if (event.key === "2") void ratingRef.current("ok");
      if (event.key === "3") void ratingRef.current("bad");
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [stage]);

  if (levels.error) return <ErrorState message={levels.error} onRetry={levels.reload} />;
  if (levels.loading && !levels.data) return <PageSkeleton tiles={4} rows={2} />;

  if (lostSession) {
    return (
      <Card className="animate-float-in mx-auto mt-6 flex max-w-md flex-col items-center gap-4 px-6 py-12 text-center">
        <p className="font-display text-xl font-bold text-ink">Bài thi này không còn trên máy chủ</p>
        <p className="text-sm text-ink-soft">
          Máy chủ đã khởi động lại giữa chừng nên phiên thi bị mất. Không cứu được bài đang làm, hãy
          bắt đầu một đề mới.
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <Button onClick={startExam} disabled={busy}>
            <IconRefresh className="h-4 w-4" /> Bắt đầu đề mới
          </Button>
          <Button variant="secondary" onClick={() => { setLostSession(false); setPaper(null); setStage("intro"); }}>
            Về trang thi thử
          </Button>
        </div>
      </Card>
    );
  }

  // ---------------------------------------------------------------- result --
  if (stage === "result" && result) {
    return (
      <div className="animate-float-in mx-auto max-w-2xl">
        <Card className="flex flex-col items-center gap-5 px-6 py-10 text-center">
          <ProgressRing value={result.overall_percent} accent={result.passed ? "jade" : "gold"} size={150}>
            <span className="font-display tnum text-3xl font-bold text-ink">{result.overall_percent}</span>
            <span className="text-xs text-ink-faint">/ 100 điểm</span>
          </ProgressRing>
          <div>
            <p className="font-display text-2xl font-bold text-ink">{result.passed ? "Đạt" : "Chưa đạt"}</p>
            <p className="mt-1 text-sm text-ink-soft">{result.band}</p>
            <p className="mt-1 text-xs text-ink-faint">
              Điểm đỗ: {result.pass_score} · Đã làm {formatNumber(result.answered_items)}/
              {formatNumber(result.total_items)} câu
            </p>
          </div>

          <div className="grid w-full grid-cols-2 gap-4 border-t border-border-soft pt-5">
            <StatTile
              label="Từ vựng & câu"
              value={formatPercent(result.written_percent, 0)}
              hint={`${result.written_score}/${result.written_max} điểm`}
              accent="sky"
            />
            <StatTile
              label="Phần nói"
              value={formatPercent(result.percent, 0)}
              hint={`${result.score}/${result.max_score} điểm`}
              accent="accent"
            />
          </div>

          <div className="w-full space-y-2 text-left">
            {result.parts.map((part) => (
              <div key={part.part} className="flex items-center gap-3">
                <span className="flex-1 truncate text-sm text-ink">{part.title}</span>
                <ProgressBar value={part.max_score ? (part.score / part.max_score) * 100 : 0} accent="accent" />
                <span className="tnum w-20 shrink-0 text-right text-sm font-semibold text-ink-soft">
                  {part.score}/{part.max_score}
                </span>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap justify-center gap-3">
            <Button onClick={startExam} disabled={busy}>
              <IconRefresh className="h-4 w-4" /> Thi lại đề mới
            </Button>
            <Button variant="secondary" onClick={() => setStage("intro")}>
              Về trang thi thử
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  // ------------------------------------------------------------------ intro --
  if (stage === "intro" || !paper) {
    return (
      <div className="animate-float-in">
        <PageHeader
          eyebrow="Thi thử"
          title="Thi thử HSK"
          description="Một đề duy nhất chạy từ trắc nghiệm từ vựng đến phần thi nói theo đúng cấu trúc HSKK. Mỗi lần thi là một đề khác, ghép từ ngân hàng câu hỏi."
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
          <StatTile label="Điểm trung bình" value={formatPercent(stats.data?.average_percent, 0)} accent="sky" />
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
            <li>· Làm phần trắc nghiệm trước, sau đó chuyển sang phần nói.</li>
            <li>· Mỗi câu nói có đồng hồ đếm ngược đúng bằng thời gian của đề thật.</li>
            {format?.ai_grading ? (
              <li className="text-jade">
                · Phần nói được AI chấm: bản ghi âm được gửi lên Gemini để nhận điểm, bản gỡ băng và
                nhận xét chi tiết.
              </li>
            ) : (
              <li className="text-gold">
                · Chưa cấu hình khoá Gemini nên phần nói sẽ do bạn tự chấm. Đặt biến môi trường
                <code className="mx-1 rounded bg-surface-2 px-1.5 py-0.5 text-xs">GEMINI_API_KEY</code>
                để bật chấm điểm bằng AI.
              </li>
            )}
            {!recorder.supported && (
              <li className="text-gold">· Trình duyệt này không ghi âm được — bài thi vẫn chạy, chỉ không nghe lại hay chấm AI được.</li>
            )}
          </ul>
          <Button size="lg" className="mt-6 w-full sm:w-auto" onClick={startExam} disabled={busy}>
            <IconClipboard className="h-4 w-4" /> Bắt đầu thi thử
          </Button>
        </Card>
      </div>
    );
  }

  // ---------------------------------------------------------------- reading --
  if (stage === "written") {
    return (
      <ReadingRunner
        sessionId={paper.session_id}
        section={paper.reading}
        onFinish={() => setStage("speaking")}
        onSessionLost={() => setLostSession(true)}
      />
    );
  }

  // --------------------------------------------------------------- speaking --
  if (!slot) return <PageSkeleton tiles={0} rows={2} />;

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
          {slot.position}/{slots.length} phần nói · {slot.part.points_per_item} điểm/câu
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
          onClick={() => void toggleRecording()}
          disabled={!recorder.supported}
          className={clsx(
            "flex h-16 w-16 items-center justify-center rounded-full transition-transform duration-200 active:scale-95",
            recorder.recording ? "animate-pulse bg-danger text-white" : "border border-border bg-surface-2 text-ink",
            !recorder.supported && "opacity-50"
          )}
          aria-label={recorder.recording ? "Dừng ghi âm" : "Bắt đầu ghi âm"}
        >
          {recorder.recording ? <IconStop className="h-6 w-6" /> : <IconMic className="h-6 w-6" />}
        </button>
        <div className="flex items-center gap-3 text-sm">
          <span className="tnum font-semibold text-ink">{clock(recorder.seconds)}</span>
          <span className="text-ink-faint">
            {remaining !== null ? `còn ${clock(remaining)}` : `tối đa ${clock(slot.part.answer_seconds)}`}
          </span>
        </div>
        {recorder.error && <p className="text-center text-xs text-danger">{recorder.error}</p>}

        {/* Live speech-to-text log: what the grader will actually read. */}
        {(speech.listening || speech.text || speech.interim) && (
          <div className="w-full rounded-xl border border-border-soft bg-surface-2 p-4">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-ink-soft">Log lời nói</span>
              {speech.listening && (
                <span className="flex items-center gap-1.5 text-[11px] text-danger">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-danger" /> đang nghe
                </span>
              )}
              {speech.text && (
                <span className="tnum ml-auto text-[11px] text-ink-faint">{speech.text.length} chữ</span>
              )}
            </div>
            <p className="hanzi mt-2 text-lg leading-relaxed text-ink">
              {speech.text}
              {speech.interim && <span className="text-ink-faint">{speech.interim}</span>}
              {!speech.text && !speech.interim && (
                <span className="text-sm text-ink-faint">Hãy nói to và rõ, chữ sẽ hiện ở đây...</span>
              )}
            </p>
          </div>
        )}
        {speech.error && <p className="text-center text-xs text-gold">{speech.error}</p>}
        {!speech.supported && recorder.recording && (
          <p className="text-center text-xs text-gold">
            Trình duyệt này không chuyển lời nói thành chữ được (cần Chrome hoặc Edge) — AI sẽ chấm
            trực tiếp từ đoạn ghi âm.
          </p>
        )}

        {recorder.clipUrl && (
          <audio controls src={recorder.clipUrl} className="w-full max-w-sm" aria-label="Nghe lại bài nói của bạn" />
        )}
        {paper.ai_grading && (recorder.clipBlob || speech.text) && !recorder.recording && !grade && (
          <Button onClick={() => void requestGrade()} disabled={grading}>
            <IconSpark className="h-4 w-4" /> {grading ? "AI đang chấm..." : "Chấm bằng AI"}
          </Button>
        )}
      </Card>

      {grade && <GradeCard grade={grade} />}

      <div className="mt-4 grid grid-cols-3 gap-3">
        {RATINGS.map((entry) => (
          <button
            key={entry.value}
            onClick={() => void rate(entry.value)}
            disabled={busy || grading}
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
          {grade ? "AI đã chấm câu này." : <>
            <Kbd>1</Kbd> trôi chảy · <Kbd>2</Kbd> tạm được · <Kbd>3</Kbd> còn vấp
          </>}
        </span>
        {grade ? (
          <Button onClick={() => void advance()} disabled={busy}>
            {index + 1 >= slots.length ? "Nộp bài" : "Câu tiếp theo"}
          </Button>
        ) : (
          <button
            onClick={() => void rate("skipped")}
            disabled={busy}
            className="text-xs font-semibold text-ink-soft transition-colors hover:text-ink"
          >
            Bỏ qua câu này
          </button>
        )}
      </div>
    </div>
  );
}

/** Gemini's verdict for one spoken answer. */
function GradeCard({ grade }: { grade: HskkGrade }) {
  const tone = grade.percent >= 80 ? "jade" : grade.percent >= 50 ? "gold" : "danger";
  return (
    <Card
      className={clsx(
        "mt-4 p-5",
        tone === "jade" && "border-jade/40",
        tone === "gold" && "border-gold/40",
        tone === "danger" && "border-danger/40"
      )}
      role="status"
    >
      <div className="flex flex-wrap items-center gap-3">
        <Badge tone="violet">AI chấm</Badge>
        <span
          className={clsx(
            "tnum font-display text-2xl font-bold",
            tone === "jade" && "text-jade",
            tone === "gold" && "text-gold",
            tone === "danger" && "text-danger"
          )}
        >
          {Math.round(grade.percent)}%
        </span>
        <span className="tnum text-xs text-ink-faint">
          {grade.score}/{grade.max_score} điểm
        </span>
      </div>

      {grade.verdict && <p className="mt-2 text-sm text-ink">{grade.verdict}</p>}

      <div className="mt-4 grid grid-cols-3 gap-3">
        {[
          { label: "Phát âm", value: grade.pronunciation_percent },
          { label: "Nội dung", value: grade.content_percent },
          { label: "Trôi chảy", value: grade.fluency_percent },
        ].map((entry) => (
          <div key={entry.label}>
            <div className="flex items-center justify-between text-[11px] text-ink-faint">
              <span>{entry.label}</span>
              <span className="tnum">{Math.round(entry.value)}%</span>
            </div>
            <div className="mt-1">
              <ProgressBar value={entry.value} accent="violet" />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 space-y-2 border-t border-border-soft pt-4 text-sm">
        <div>
          <p className="text-xs font-semibold text-ink-soft">Bạn đã nói</p>
          <p className="hanzi mt-0.5 text-base text-ink">{grade.transcript || "— không nghe được tiếng nói nào —"}</p>
        </div>
        <div>
          <p className="text-xs font-semibold text-ink-soft">Đề bài</p>
          <p className="hanzi mt-0.5 text-base text-ink-soft">{grade.expected}</p>
        </div>
      </div>

      {grade.strengths.length > 0 && (
        <ul className="mt-3 space-y-1 text-xs text-jade">
          {grade.strengths.map((entry) => (
            <li key={entry}>+ {entry}</li>
          ))}
        </ul>
      )}
      {grade.fixes.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs text-ink-soft">
          {grade.fixes.map((entry) => (
            <li key={entry}>· {entry}</li>
          ))}
        </ul>
      )}
    </Card>
  );
}

/** The official paper layout, so the learner knows what they are walking into. */
function FormatTable({ format }: { format: HskkLevelFormat }) {
  return (
    <Card className="mt-6 overflow-hidden">
      <div className="flex flex-wrap items-center gap-3 border-b border-border-soft px-6 py-4">
        <h2 className="font-display text-lg font-bold text-ink">Cấu trúc đề {format.label}</h2>
        <Badge tone="neutral">{format.total_items} câu</Badge>
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
            {format.reading.parts.map((part, position) => (
              <tr key={part.part_number} className="border-t border-border-soft">
                <td className="px-6 py-3 font-semibold text-ink">阅读 {part.part_number}</td>
                <td className="px-3 py-3">
                  <p className="font-medium text-ink">{part.instruction_zh}</p>
                  <p className="mt-0.5 text-xs text-ink-faint">{part.instruction_vi}</p>
                </td>
                <td className="tnum px-3 py-3 text-ink-soft">{part.count}</td>
                <td className="px-3 py-3 text-ink-faint">
                  {position === 0 ? `${format.reading.time_minutes} phút` : "—"}
                </td>
                <td className="tnum px-6 py-3 text-right text-ink-soft">
                  {position === 0 ? format.reading.total_points : "—"}
                </td>
              </tr>
            ))}
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
      {format.skipped_parts.map((entry) => (
        <p key={entry.part} className="border-t border-border-soft px-6 py-3 text-xs text-gold">
          Phần {entry.part} ({entry.title}): {entry.reason}
        </p>
      ))}
      <p className="border-t border-border-soft px-6 py-3 text-xs text-ink-faint">
        Trắc nghiệm và phần nói được chấm riêng, mỗi bên thang 100; điểm cuối là trung bình hai bên.
      </p>
    </Card>
  );
}
