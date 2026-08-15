import { useCallback, useState } from "react";
import clsx from "clsx";
import { api } from "../lib/api";
import { useLevel } from "../lib/levelContext";
import { useSettings } from "../lib/settings";
import { useToast } from "../lib/toast";
import { useApi } from "../lib/useApi";
import { formatNumber } from "../lib/format";
import type { HskLevel, SentenceItem, SentenceToken } from "../lib/types";
import {
  AudioButton,
  Button,
  Card,
  EmptyState,
  InlineSwitch,
  PageHeader,
  PracticeBar,
  SessionSizePicker,
  SessionComplete,
} from "../components/ui";
import { IconRefresh } from "../components/icons";

export default function Sentences() {
  const { level } = useLevel();
  const { settings } = useSettings();
  const toast = useToast();

  const [sessionId, setSessionId] = useState<number | null>(null);
  const [items, setItems] = useState<SentenceItem[]>([]);
  const [index, setIndex] = useState(0);
  const [pool, setPool] = useState<SentenceToken[]>([]);
  const [chosen, setChosen] = useState<SentenceToken[]>([]);
  const [result, setResult] = useState<{ isCorrect: boolean; answer: SentenceItem } | null>(null);
  const [showPinyin, setShowPinyin] = useState(settings.show_pinyin);
  const [showMeaning, setShowMeaning] = useState(true);
  const [count, setCount] = useState(10);
  const [stats, setStats] = useState({ correct: 0, incorrect: 0 });
  const [finished, setFinished] = useState(false);
  const [busy, setBusy] = useState(false);

  const levels = useApi(() => api.sentences.levels(), []);

  // The sentence corpus is far smaller than the vocabulary list, so the picker
  // has to be capped by what the chosen level actually contains -- otherwise
  // asking for 100 would quietly hand back whatever few sentences exist.
  const available =
    level === "all"
      ? (levels.data?.items ?? []).reduce((sum, entry) => sum + entry.total, 0)
      : (levels.data?.items ?? []).find((entry) => entry.level === level)?.total ?? 0;
  const maxCount = Math.min(200, available || 200);

  async function start() {
    setBusy(true);
    try {
      const session = await api.sentences.createSession(
        Math.min(count, maxCount),
        undefined,
        level === "all" ? null : (level as HskLevel)
      );
      setSessionId(session.session_id);
      setItems(session.items);
      setIndex(0);
      setPool(session.items[0].tokens);
      setChosen([]);
      setResult(null);
      setStats({ correct: 0, incorrect: 0 });
      setFinished(false);
    } catch (error) {
      toast.error(
        "Không tạo được phiên luyện câu",
        error instanceof Error ? error.message : undefined
      );
    } finally {
      setBusy(false);
    }
  }

  function pick(token: SentenceToken) {
    if (result) return;
    setPool((p) => p.filter((t) => t.token_id !== token.token_id));
    setChosen((c) => [...c, token]);
  }

  function unpick(token: SentenceToken) {
    if (result) return;
    setChosen((c) => c.filter((t) => t.token_id !== token.token_id));
    setPool((p) => [...p, token]);
  }

  async function submit() {
    if (!sessionId || busy) return;
    setBusy(true);
    try {
      const current = items[index];
      const positions = chosen.map((t) => t.position);
      const res = await api.sentences.attempt(sessionId, current.id, positions);
      setResult({ isCorrect: res.is_correct, answer: current });
      setStats((s) =>
        res.is_correct ? { ...s, correct: s.correct + 1 } : { ...s, incorrect: s.incorrect + 1 }
      );
    } catch (error) {
      toast.error("Không chấm được câu", error instanceof Error ? error.message : undefined);
    } finally {
      setBusy(false);
    }
  }

  const wrapUp = useCallback(
    async (done: number) => {
      if (!sessionId) return;
      try {
        await api.sentences.complete(sessionId, done, stats.correct, stats.incorrect);
      } catch {
        // Each attempt was already recorded; a failed summary call must not
        // cost the learner the session they just finished.
      }
      setFinished(true);
    },
    [sessionId, stats.correct, stats.incorrect]
  );

  async function next() {
    if (!sessionId) return;
    if (index + 1 >= items.length) {
      await wrapUp(items.length);
      return;
    }
    const nextIndex = index + 1;
    setIndex(nextIndex);
    setPool(items[nextIndex].tokens);
    setChosen([]);
    setResult(null);
  }

  if (!sessionId) {
    return (
      <div className="animate-float-in">
        <PageHeader
          eyebrow="Ngữ pháp"
          title="Luyện câu"
          description="Sắp xếp các cụm từ để tạo thành câu đúng."
        />
        {levels.data && available === 0 ? (
          <EmptyState
            title={`Chưa có câu luyện tập cho HSK ${level}`}
            description="Kho câu chưa phủ hết cấp độ này. Hãy chuyển sang cấp độ khác hoặc chọn “Tất cả” ở thanh bên để luyện tiếp."
          />
        ) : (
          <Card className="max-w-md p-6">
            <SessionSizePicker
              value={Math.min(count, maxCount)}
              onChange={setCount}
              max={maxCount}
              unit="câu"
              presets={[5, 10, 20, 50, 100]}
            />
            <Button className="mt-5 w-full" size="lg" disabled={busy} onClick={start}>
              {busy
                ? "Đang chuẩn bị..."
                : `Bắt đầu ${Math.min(count, maxCount)} câu (${
                    level === "all" ? "mọi cấp độ" : `HSK ${level}`
                  })`}
            </Button>
            {available > 0 && (
              <p className="mt-3 text-center text-xs text-ink-faint">
                {formatNumber(available)} câu khả dụng ở cấp độ đang chọn.
              </p>
            )}
          </Card>
        )}
      </div>
    );
  }

  if (finished) {
    return (
      <SessionComplete
        correct={stats.correct}
        total={stats.correct + stats.incorrect}
        unit="câu"
        detail={`${stats.correct} đúng · ${stats.incorrect} sai`}
        primary={
          <Button size="lg" onClick={() => setSessionId(null)}>
            <IconRefresh className="h-4 w-4" /> Luyện thêm
          </Button>
        }
      />
    );
  }

  const current = items[index];

  return (
    <div className="animate-float-in mx-auto max-w-2xl">
      <PracticeBar position={index + 1} total={items.length}>
        <InlineSwitch
          checked={showPinyin}
          onChange={setShowPinyin}
          label="Pinyin"
          title="Bật/tắt phiên âm pinyin"
        />
        <InlineSwitch
          checked={showMeaning}
          onChange={setShowMeaning}
          label="Nghĩa"
          title="Bật/tắt bản dịch tiếng Việt"
        />
      </PracticeBar>

      {/* The Vietnamese sentence is the prompt: without it there is nothing to
          tell the learner which sentence the shuffled chunks should form. */}
      {showMeaning && (
        <p className="mb-3 text-base font-medium text-ink">{current.meaning}</p>
      )}

      <Card className="min-h-24 p-4">
        <div className="flex flex-wrap gap-2">
          {chosen.map((token) => (
            <button
              key={token.token_id}
              onClick={() => unpick(token)}
              className="rounded-lg border border-accent bg-accent-soft px-3 py-2 text-center text-accent"
            >
              <span className="hanzi block text-lg font-semibold">{token.text}</span>
              {showPinyin && <span className="block text-[11px] opacity-80">{token.pinyin}</span>}
            </button>
          ))}
          {chosen.length === 0 && (
            <p className="text-sm text-ink-faint">Chọn các cụm từ bên dưới theo đúng thứ tự...</p>
          )}
        </div>
      </Card>

      <div className="mt-4 flex flex-wrap gap-2">
        {pool.map((token) => (
          <button
            key={token.token_id}
            onClick={() => pick(token)}
            className="rounded-lg border border-border bg-surface px-3 py-2 text-center text-ink transition-colors hover:border-accent/50"
          >
            <span className="hanzi block text-lg font-semibold">{token.text}</span>
            {showPinyin && <span className="block text-[11px] text-ink-faint">{token.pinyin}</span>}
          </button>
        ))}
      </div>

      {!result ? (
        <Button className="mt-6 w-full" size="lg" disabled={pool.length > 0 || busy} onClick={submit}>
          Kiểm tra
        </Button>
      ) : (
        <Card
          className={clsx(
            "mt-6 p-5",
            result.isCorrect ? "border-jade/50 bg-jade-soft" : "border-danger/50 bg-danger-soft"
          )}
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className={clsx("font-semibold", result.isCorrect ? "text-jade" : "text-danger")}>
                {result.isCorrect ? "Chính xác!" : "Chưa đúng, đáp án đúng là:"}
              </p>
              <p className="hanzi mt-2 text-xl font-bold text-ink">{result.answer.hanzi}</p>
              {showPinyin && <p className="text-gold">{result.answer.pinyin}</p>}
              {showMeaning && <p className="text-ink-soft">{result.answer.meaning}</p>}
            </div>
            <AudioButton text={result.answer.hanzi} />
          </div>
          <Button className="mt-4" onClick={next}>
            {index + 1 >= items.length ? "Xem kết quả" : "Câu tiếp theo"}
          </Button>
        </Card>
      )}

      <div className="mt-6 flex items-center justify-between gap-3 text-xs text-ink-faint">
        <span className="tnum">
          {stats.correct} đúng · {stats.incorrect} sai
        </span>
        <Button variant="ghost" size="sm" onClick={() => void wrapUp(index + (result ? 1 : 0))}>
          Kết thúc sớm
        </Button>
      </div>
    </div>
  );
}
