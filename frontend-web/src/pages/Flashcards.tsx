import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../lib/api";
import { useLevel } from "../lib/levelContext";
import type { VocabularyItem } from "../lib/types";
import { AudioButton, Badge, Button, Card, PageHeader } from "../components/ui";
import { IconCheck, IconRefresh, IconX } from "../components/icons";

type Result = "forgot" | "hard" | "remembered";

export default function Flashcards() {
  const { level } = useLevel();
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [items, setItems] = useState<VocabularyItem[]>([]);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [count, setCount] = useState(10);
  const [results, setResults] = useState<Result[]>([]);
  const [finished, setFinished] = useState(false);

  async function start() {
    const session = await api.flashcard.createSession(count, false);
    setSessionId(session.session_id);
    setItems(session.items);
    setIndex(0);
    setFlipped(false);
    setResults([]);
    setFinished(false);
  }

  async function rate(result: Result) {
    if (!sessionId) return;
    const item = items[index];
    await api.flashcard.review(sessionId, item.id, result);
    const nextResults = [...results, result];
    setResults(nextResults);
    if (index + 1 >= items.length) {
      const correct = nextResults.filter((r) => r === "remembered").length;
      await api.flashcard.complete(sessionId, items.length, correct, items.length - correct);
      setFinished(true);
    } else {
      setIndex(index + 1);
      setFlipped(false);
    }
  }

  if (!sessionId) {
    return (
      <div className="animate-float-in">
        <PageHeader eyebrow="Ôn tập" title="Flashcard" description="Lật thẻ, tự đánh giá mức độ nhớ của bạn cho từng từ." />
        <Card className="max-w-md p-6">
          <label className="text-sm font-semibold text-ink">Số lượng thẻ: {count}</label>
          <input
            type="range"
            min={5}
            max={30}
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            className="mt-3 w-full accent-[var(--c-accent)]"
          />
          <Button className="mt-5 w-full" size="lg" onClick={start}>
            Bắt đầu phiên học ({level === "all" ? "mọi cấp độ" : `HSK ${level}`})
          </Button>
        </Card>
      </div>
    );
  }

  if (finished) {
    const correct = results.filter((r) => r === "remembered").length;
    return (
      <div className="animate-float-in flex flex-col items-center py-12 text-center">
        <p className="font-display text-4xl font-bold text-ink">Hoàn thành!</p>
        <p className="mt-2 text-ink-soft">
          Bạn nhớ đúng {correct}/{items.length} thẻ ({Math.round((correct / items.length) * 100)}%)
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
      <div className="mb-4 flex items-center justify-between text-sm text-ink-soft">
        <span>
          Thẻ {index + 1}/{items.length}
        </span>
        <Badge tone="neutral">HSK {item.hsk_level}</Badge>
      </div>

      <div className="h-2 w-full overflow-hidden rounded-full bg-surface-2">
        <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${(index / items.length) * 100}%` }} />
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
            <span className="text-lg text-gold">{item.pinyin}</span>
            <AudioButton text={item.hanzi} />
            <p className="absolute bottom-4 text-xs text-ink-faint">Nhấn để xem nghĩa</p>
          </Card>
          <Card
            className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-8"
            style={{ backfaceVisibility: "hidden", transform: "rotateY(180deg)" }}
          >
            <span className="hanzi text-3xl font-bold text-ink">{item.hanzi}</span>
            <span className="text-lg font-semibold text-accent">{item.meaning}</span>
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
            <Button variant="danger" onClick={() => rate("forgot")}>
              <IconX className="h-4 w-4" /> Quên
            </Button>
            <Button variant="secondary" onClick={() => rate("hard")}>
              Khó
            </Button>
            <Button onClick={() => rate("remembered")}>
              <IconCheck className="h-4 w-4" /> Đã nhớ
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
