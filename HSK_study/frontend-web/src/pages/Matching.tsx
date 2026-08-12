import { useState } from "react";
import clsx from "clsx";
import { api } from "../lib/api";
import type { MatchingItem } from "../lib/types";
import { Button, Card, PageHeader } from "../components/ui";
import { IconRefresh } from "../components/icons";

type Mode = "meaning" | "pinyin";

export default function Matching() {
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [mode, setMode] = useState<Mode>("meaning");
  const [left, setLeft] = useState<MatchingItem[]>([]);
  const [right, setRight] = useState<MatchingItem[]>([]);
  const [selectedLeft, setSelectedLeft] = useState<number | null>(null);
  const [selectedRight, setSelectedRight] = useState<number | null>(null);
  const [matched, setMatched] = useState<Set<number>>(new Set());
  const [wrongFlash, setWrongFlash] = useState<{ left: number | null; right: number | null }>({ left: null, right: null });
  const [attempts, setAttempts] = useState({ correct: 0, incorrect: 0 });
  const [finished, setFinished] = useState(false);

  async function start(selectedMode: Mode) {
    const session = await api.matching.createSession(selectedMode, 6);
    setSessionId(session.session_id);
    setMode(selectedMode);
    setLeft(session.left_items);
    setRight(session.right_items);
    setMatched(new Set());
    setSelectedLeft(null);
    setSelectedRight(null);
    setAttempts({ correct: 0, incorrect: 0 });
    setFinished(false);
  }

  async function tryMatch(leftId: number, rightId: number) {
    if (!sessionId) return;
    const isCorrect = leftId === rightId;
    await api.matching.attempt(sessionId, leftId, mode, isCorrect);
    if (isCorrect) {
      const next = new Set(matched).add(leftId);
      setMatched(next);
      setAttempts((a) => ({ ...a, correct: a.correct + 1 }));
      setSelectedLeft(null);
      setSelectedRight(null);
      if (next.size === left.length) {
        await api.matching.complete(sessionId, left.length, attempts.correct + 1, attempts.incorrect);
        setFinished(true);
      }
    } else {
      setWrongFlash({ left: leftId, right: rightId });
      setAttempts((a) => ({ ...a, incorrect: a.incorrect + 1 }));
      setTimeout(() => {
        setWrongFlash({ left: null, right: null });
        setSelectedLeft(null);
        setSelectedRight(null);
      }, 500);
    }
  }

  function pickLeft(id: number) {
    if (matched.has(id)) return;
    setSelectedLeft(id);
    if (selectedRight !== null) tryMatch(id, selectedRight);
  }
  function pickRight(id: number) {
    if (matched.has(id)) return;
    setSelectedRight(id);
    if (selectedLeft !== null) tryMatch(selectedLeft, id);
  }

  if (!sessionId) {
    return (
      <div className="animate-float-in">
        <PageHeader eyebrow="Trò chơi" title="Nối từ" description="Ghép Hán tự với nghĩa hoặc pinyin tương ứng." />
        <div className="flex gap-3">
          <Button onClick={() => start("meaning")}>Hán tự ↔ Nghĩa</Button>
          <Button variant="secondary" onClick={() => start("pinyin")}>
            Hán tự ↔ Pinyin
          </Button>
        </div>
      </div>
    );
  }

  if (finished) {
    return (
      <div className="animate-float-in flex flex-col items-center py-12 text-center">
        <p className="font-display text-4xl font-bold text-ink">Hoàn thành!</p>
        <p className="mt-2 text-ink-soft">
          {attempts.correct} đúng / {attempts.incorrect} sai
        </p>
        <Button className="mt-6" onClick={() => setSessionId(null)}>
          <IconRefresh className="h-4 w-4" /> Vòng mới
        </Button>
      </div>
    );
  }

  return (
    <div className="animate-float-in">
      <PageHeader eyebrow="Trò chơi" title={`Nối từ · ${mode === "meaning" ? "Nghĩa" : "Pinyin"}`} />
      <div className="grid grid-cols-2 gap-4 sm:gap-8">
        <div className="flex flex-col gap-3">
          {left.map((item) => (
            <Tile
              key={item.vocabulary_id}
              item={item}
              hanzi
              matched={matched.has(item.vocabulary_id)}
              selected={selectedLeft === item.vocabulary_id}
              wrong={wrongFlash.left === item.vocabulary_id}
              onClick={() => pickLeft(item.vocabulary_id)}
            />
          ))}
        </div>
        <div className="flex flex-col gap-3">
          {right.map((item) => (
            <Tile
              key={item.vocabulary_id}
              item={item}
              matched={matched.has(item.vocabulary_id)}
              selected={selectedRight === item.vocabulary_id}
              wrong={wrongFlash.right === item.vocabulary_id}
              onClick={() => pickRight(item.vocabulary_id)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function Tile({
  item,
  hanzi,
  matched,
  selected,
  wrong,
  onClick,
}: {
  item: MatchingItem;
  hanzi?: boolean;
  matched: boolean;
  selected: boolean;
  wrong: boolean;
  onClick: () => void;
}) {
  return (
    <Card
      onClick={onClick}
      className={clsx(
        "cursor-pointer px-4 py-3.5 text-center transition-all",
        hanzi && "hanzi text-lg font-semibold",
        matched && "border-jade/50 bg-jade-soft text-jade opacity-70",
        selected && !matched && "border-accent bg-accent-soft text-accent",
        wrong && "border-danger bg-danger-soft text-danger"
      )}
    >
      {item.text}
    </Card>
  );
}
