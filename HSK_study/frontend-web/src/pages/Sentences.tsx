import { useState } from "react";
import clsx from "clsx";
import { api } from "../lib/api";
import type { SentenceItem, SentenceToken } from "../lib/types";
import { AudioButton, Button, Card, PageHeader } from "../components/ui";
import { IconRefresh } from "../components/icons";

export default function Sentences() {
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [items, setItems] = useState<SentenceItem[]>([]);
  const [index, setIndex] = useState(0);
  const [pool, setPool] = useState<SentenceToken[]>([]);
  const [chosen, setChosen] = useState<SentenceToken[]>([]);
  const [result, setResult] = useState<{ isCorrect: boolean; answer: SentenceItem } | null>(null);
  const [showPinyin, setShowPinyin] = useState(true);
  const [showMeaning, setShowMeaning] = useState(true);
  const [stats, setStats] = useState({ correct: 0, incorrect: 0 });
  const [finished, setFinished] = useState(false);

  async function start() {
    const session = await api.sentences.createSession(8);
    setSessionId(session.session_id);
    setItems(session.items);
    setIndex(0);
    setPool(session.items[0].tokens);
    setChosen([]);
    setResult(null);
    setStats({ correct: 0, incorrect: 0 });
    setFinished(false);
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
    if (!sessionId) return;
    const current = items[index];
    const positions = chosen.map((t) => t.position);
    const res = await api.sentences.attempt(sessionId, current.id, positions);
    setResult({ isCorrect: res.is_correct, answer: current });
    setStats((s) => (res.is_correct ? { ...s, correct: s.correct + 1 } : { ...s, incorrect: s.incorrect + 1 }));
  }

  async function next() {
    if (!sessionId) return;
    if (index + 1 >= items.length) {
      await api.sentences.complete(sessionId, items.length, stats.correct, stats.incorrect);
      setFinished(true);
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
        <PageHeader eyebrow="Ngữ pháp" title="Luyện câu" description="Sắp xếp các cụm từ để tạo thành câu đúng." />
        <Button size="lg" onClick={start}>
          Bắt đầu luyện tập
        </Button>
      </div>
    );
  }

  if (finished) {
    return (
      <div className="animate-float-in flex flex-col items-center py-12 text-center">
        <p className="font-display text-4xl font-bold text-ink">Hoàn thành!</p>
        <p className="mt-2 text-ink-soft">
          {stats.correct} đúng / {stats.incorrect} sai
        </p>
        <Button className="mt-6" onClick={() => setSessionId(null)}>
          <IconRefresh className="h-4 w-4" /> Luyện thêm
        </Button>
      </div>
    );
  }

  return (
    <div className="animate-float-in mx-auto max-w-2xl">
      <div className="mb-4 flex items-center justify-between">
        <span className="text-sm text-ink-soft">
          Câu {index + 1}/{items.length}
        </span>
        <div className="flex gap-2 text-xs">
          <ToggleChip active={showPinyin} onClick={() => setShowPinyin((v) => !v)} label="Pinyin" />
          <ToggleChip active={showMeaning} onClick={() => setShowMeaning((v) => !v)} label="Nghĩa" />
        </div>
      </div>

      <Card className="min-h-24 p-4">
        <div className="flex flex-wrap gap-2">
          {chosen.map((token) => (
            <button
              key={token.token_id}
              onClick={() => unpick(token)}
              className="hanzi rounded-lg border border-accent bg-accent-soft px-3 py-2 text-lg font-semibold text-accent"
            >
              {token.text}
            </button>
          ))}
          {chosen.length === 0 && <p className="text-sm text-ink-faint">Chọn các cụm từ bên dưới theo đúng thứ tự...</p>}
        </div>
      </Card>

      <div className="mt-4 flex flex-wrap gap-2">
        {pool.map((token) => (
          <button
            key={token.token_id}
            onClick={() => pick(token)}
            className="hanzi rounded-lg border border-border bg-surface px-3 py-2 text-lg font-semibold text-ink transition-colors hover:border-accent/50"
          >
            {token.text}
          </button>
        ))}
      </div>

      {!result ? (
        <Button className="mt-6 w-full" size="lg" disabled={pool.length > 0} onClick={submit}>
          Kiểm tra
        </Button>
      ) : (
        <Card className={clsx("mt-6 p-5", result.isCorrect ? "border-jade/50 bg-jade-soft" : "border-danger/50 bg-danger-soft")}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className={clsx("font-semibold", result.isCorrect ? "text-jade" : "text-danger")}>
                {result.isCorrect ? "Chính xác!" : "Sai rồi, thử lại câu tiếp theo nhé."}
              </p>
              <p className="hanzi mt-2 text-xl font-bold text-ink">{result.answer.hanzi}</p>
              {showPinyin && <p className="text-gold">{result.answer.pinyin}</p>}
              {showMeaning && <p className="text-ink-soft">{result.answer.meaning}</p>}
            </div>
            <AudioButton text={result.answer.hanzi} />
          </div>
          <Button className="mt-4" onClick={next}>
            Câu tiếp theo
          </Button>
        </Card>
      )}
    </div>
  );
}

function ToggleChip({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "rounded-full border px-2.5 py-1 font-medium transition-colors",
        active ? "border-accent bg-accent-soft text-accent" : "border-border text-ink-faint"
      )}
    >
      {label}
    </button>
  );
}
