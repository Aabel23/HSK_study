import { useCallback, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../lib/api";
import { useLevel } from "../lib/levelContext";
import { useSettings } from "../lib/settings";
import { useToast } from "../lib/toast";
import { useApi } from "../lib/useApi";
import { formatNumber, shortMeaning } from "../lib/format";
import { useShortcuts } from "../lib/useShortcuts";
import type { HskLevel, VocabularyItem } from "../lib/types";
import {
  AudioButton,
  Badge,
  Button,
  Card,
  InlineSwitch,
  Kbd,
  PracticeBar,
  PageHeader,
  SessionSizePicker,
  Switch,
} from "../components/ui";
import { IconCheck, IconRefresh, IconX } from "../components/icons";

type Result = "forgot" | "hard" | "remembered";

export default function Flashcards() {
  const { level } = useLevel();
  const { settings, update } = useSettings();
  const toast = useToast();

  const [sessionId, setSessionId] = useState<number | null>(null);
  const [items, setItems] = useState<VocabularyItem[]>([]);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [count, setCount] = useState(settings.session_size);
  const [includeMastered, setIncludeMastered] = useState(false);
  const [results, setResults] = useState<Result[]>([]);
  const [finished, setFinished] = useState(false);
  const [busy, setBusy] = useState(false);

  const levels = useApi(() => api.vocabulary.levels(), []);

  // Offering more cards than the chosen level holds would silently produce a
  // shorter session, so the picker is capped by the real pool.
  const available =
    level === "all"
      ? (levels.data?.items ?? []).reduce((sum, entry) => sum + entry.total, 0)
      : (levels.data?.items ?? []).find((entry) => entry.level === level)?.total ?? 0;
  const maxCount = Math.min(200, available || 200);

  async function start() {
    setBusy(true);
    try {
      const session = await api.flashcard.createSession(
        Math.min(count, maxCount),
        includeMastered,
        level === "all" ? null : (level as HskLevel)
      );
      setSessionId(session.session_id);
      setItems(session.items);
      setIndex(0);
      setFlipped(false);
      setResults([]);
      setFinished(false);
    } catch (error) {
      toast.error(
        "Không tạo được phiên Flashcard",
        error instanceof Error ? error.message : undefined
      );
    } finally {
      setBusy(false);
    }
  }

  /** Close the session on the server and show the summary. */
  const wrapUp = useCallback(
    async (finalResults: Result[]) => {
      if (!sessionId) return;
      const correct = finalResults.filter((entry) => entry === "remembered").length;
      try {
        await api.flashcard.complete(
          sessionId,
          finalResults.length,
          correct,
          finalResults.length - correct
        );
      } catch {
        // The cards were already graded one by one; a failed summary call must
        // not cost the learner the session they just finished.
      }
      setFinished(true);
    },
    [sessionId]
  );

  const rate = useCallback(
    async (result: Result) => {
      if (!sessionId || busy || finished) return;
      const item = items[index];
      if (!item) return;
      setBusy(true);
      try {
        await api.flashcard.review(sessionId, item.id, result);
        const nextResults = [...results, result];
        setResults(nextResults);
        if (index + 1 >= items.length) {
          await wrapUp(nextResults);
        } else {
          setIndex(index + 1);
          setFlipped(false);
        }
      } catch (error) {
        toast.error("Không lưu được kết quả", error instanceof Error ? error.message : undefined);
      } finally {
        setBusy(false);
      }
    },
    [busy, finished, index, items, results, sessionId, toast, wrapUp]
  );

  // Rating a long run of cards with the mouse gets tiring fast. Space flips,
  // 1/2/3 grade — the same contract every other practice screen follows.
  useShortcuts({
    enabled: Boolean(sessionId) && !finished,
    onAdvance: () => setFlipped((value) => !value),
    onPick: (choice) => {
      if (!flipped) return;
      const result = (["forgot", "hard", "remembered"] as const)[choice - 1];
      if (result) void rate(result);
    },
  });

  if (!sessionId) {
    return (
      <div className="animate-float-in">
        <PageHeader
          eyebrow="Ôn tập"
          title="Flashcard"
          description="Lật thẻ, tự đánh giá mức độ nhớ của bạn cho từng từ."
        />
        <Card className="max-w-md p-6">
          <SessionSizePicker
            value={Math.min(count, maxCount)}
            onChange={setCount}
            max={maxCount}
            unit="thẻ"
          />
          <div className="mt-2 border-t border-border-soft">
            <Switch
              checked={includeMastered}
              onChange={setIncludeMastered}
              label="Gồm cả từ đã thuộc"
              description="Tắt để chỉ ôn những từ bạn chưa nắm chắc."
            />
          </div>
          <Button className="mt-4 w-full" size="lg" disabled={busy} onClick={start}>
            {busy
              ? "Đang chuẩn bị..."
              : `Bắt đầu ${Math.min(count, maxCount)} thẻ (${
                  level === "all" ? "mọi cấp độ" : `HSK ${level}`
                })`}
          </Button>
          {available > 0 && (
            <p className="mt-3 text-center text-xs text-ink-faint">
              {formatNumber(available)} từ khả dụng ở cấp độ đang chọn.
            </p>
          )}
        </Card>
      </div>
    );
  }

  if (finished) {
    const correct = results.filter((entry) => entry === "remembered").length;
    const total = Math.max(1, results.length);
    return (
      <div className="animate-float-in flex flex-col items-center py-12 text-center">
        <p className="font-display text-4xl font-bold text-ink">Hoàn thành!</p>
        <p className="mt-2 text-ink-soft">
          Bạn nhớ đúng {correct}/{results.length} thẻ ({Math.round((correct / total) * 100)}%)
        </p>
        <Button className="mt-6" onClick={() => setSessionId(null)}>
          <IconRefresh className="h-4 w-4" /> Học phiên mới
        </Button>
      </div>
    );
  }

  const item = items[index];

  return (
    <div className="animate-float-in mx-auto max-w-xl">
      <PracticeBar
        unit="Thẻ"
        position={index + 1}
        total={items.length}
        badge={<Badge tone="neutral">HSK {item.hsk_level}</Badge>}
      >
        <InlineSwitch
          checked={settings.show_pinyin}
          onChange={(next) => void update({ show_pinyin: next })}
          label="Pinyin"
          title="Bật/tắt phiên âm pinyin trên thẻ"
        />
      </PracticeBar>

      <div className="h-2 w-full overflow-hidden rounded-full bg-surface-2">
        <div
          className="h-full rounded-full bg-accent transition-all"
          style={{ width: `${(index / items.length) * 100}%` }}
        />
      </div>

      <div className="perspective-1000 mt-8" style={{ perspective: 1200 }}>
        <motion.div
          className="relative h-72 cursor-pointer"
          onClick={() => setFlipped((f) => !f)}
          style={{ transformStyle: "preserve-3d" }}
          animate={{ rotateY: flipped ? 180 : 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <Card
            className="absolute inset-0 flex flex-col items-center justify-center gap-4 p-8"
            style={{ backfaceVisibility: "hidden" }}
          >
            <span className="hanzi text-6xl font-bold text-ink">{item.hanzi}</span>
            {settings.show_pinyin && <span className="text-lg text-gold">{item.pinyin}</span>}
            <AudioButton text={item.hanzi} />
            <p className="absolute bottom-4 text-xs text-ink-faint">Nhấn để xem nghĩa</p>
          </Card>
          <Card
            className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-8"
            style={{ backfaceVisibility: "hidden", transform: "rotateY(180deg)" }}
          >
            <span className="hanzi text-3xl font-bold text-ink">{item.hanzi}</span>
            <span className="text-sm text-gold">{item.pinyin}</span>
            <span className="text-lg font-semibold text-accent">{shortMeaning(item.meaning, { senses: 3, chars: 100 })}</span>
            {item.example && (
              <div className="mt-2 text-center text-sm text-ink-soft">
                <p className="hanzi">{item.example}</p>
                <p className="text-gold">{item.example_pinyin}</p>
                <p>{item.example_meaning}</p>
              </div>
            )}
          </Card>
        </motion.div>
      </div>

      <AnimatePresence>
        {flipped && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-6 grid grid-cols-3 gap-3"
          >
            <Button variant="danger" disabled={busy} onClick={() => void rate("forgot")}>
              <IconX className="h-4 w-4" /> Quên
            </Button>
            <Button variant="secondary" disabled={busy} onClick={() => void rate("hard")}>
              Khó
            </Button>
            <Button disabled={busy} onClick={() => void rate("remembered")}>
              <IconCheck className="h-4 w-4" /> Đã nhớ
            </Button>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 text-xs text-ink-faint">
        <span className="flex flex-wrap items-center gap-1.5">
          <Kbd>Space</Kbd> lật thẻ · <Kbd>1</Kbd> quên · <Kbd>2</Kbd> khó · <Kbd>3</Kbd> đã nhớ
        </span>
        <Button variant="ghost" size="sm" onClick={() => void wrapUp(results)}>
          Kết thúc sớm
        </Button>
      </div>
    </div>
  );
}
