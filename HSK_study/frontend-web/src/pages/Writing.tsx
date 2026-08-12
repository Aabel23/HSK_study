import { useEffect, useRef, useState } from "react";
import HanziWriter from "hanzi-writer";
import { api } from "../lib/api";
import { useLevel } from "../lib/levelContext";
import type { WritingCharacter } from "../lib/types";
import { AudioButton, Badge, Button, Card, PageHeader } from "../components/ui";
import { IconRefresh } from "../components/icons";

export default function Writing() {
  const { level } = useLevel();
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [characters, setCharacters] = useState<WritingCharacter[]>([]);
  const [index, setIndex] = useState(0);
  const [stats, setStats] = useState({ correct: 0, incorrect: 0 });
  const [finished, setFinished] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [mistakes, setMistakes] = useState(0);
  const targetRef = useRef<HTMLDivElement | null>(null);
  const writerRef = useRef<ReturnType<typeof HanziWriter.create> | null>(null);

  const current = characters[index];

  async function start() {
    const session = await api.writing.createSession(level === "all" ? null : level, 8);
    setSessionId(session.session_id);
    setCharacters(session.characters);
    setIndex(0);
    setStats({ correct: 0, incorrect: 0 });
    setFinished(false);
  }

  useEffect(() => {
    if (!current || !targetRef.current) return;
    targetRef.current.innerHTML = "";
    setCompleted(false);
    setMistakes(0);
    const writer = HanziWriter.create(targetRef.current, current.character, {
      width: 260,
      height: 260,
      padding: 12,
      strokeAnimationSpeed: 1.2,
      delayBetweenStrokes: 100,
      showOutline: true,
      strokeColor: "#e2483b",
      radicalColor: "#e3b23c",
      drawingColor: "#57a6ff",
    });
    writerRef.current = writer;
    writer.quiz({
      onMistake: () => setMistakes((m) => m + 1),
      onCorrectStroke: () => {},
      onComplete: async ({ totalMistakes }: { totalMistakes: number }) => {
        setCompleted(true);
        if (sessionId) {
          const isCorrect = totalMistakes <= 2;
          await api.writing.attempt(sessionId, current.character, totalMistakes, isCorrect);
          setStats((s) => (isCorrect ? { ...s, correct: s.correct + 1 } : { ...s, incorrect: s.incorrect + 1 }));
        }
      },
    });
    return () => {
      writerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.character, sessionId]);

  async function next() {
    if (!sessionId) return;
    if (index + 1 >= characters.length) {
      await api.writing.complete(sessionId, characters.length, stats.correct, stats.incorrect);
      setFinished(true);
      return;
    }
    setIndex(index + 1);
  }

  function replay() {
    writerRef.current?.animateCharacter();
  }

  function hint() {
    writerRef.current?.showOutline();
  }

  if (!sessionId) {
    return (
      <div className="animate-float-in">
        <PageHeader eyebrow="Kỹ năng viết" title="Luyện viết chữ Hán" description="Viết theo đúng thứ tự nét, hệ thống sẽ chấm điểm trực tiếp." />
        <Button size="lg" onClick={start}>
          Bắt đầu luyện viết
        </Button>
      </div>
    );
  }

  if (finished) {
    return (
      <div className="animate-float-in flex flex-col items-center py-12 text-center">
        <p className="font-display text-4xl font-bold text-ink">Hoàn thành!</p>
        <p className="mt-2 text-ink-soft">
          {stats.correct}/{characters.length} chữ viết tốt
        </p>
        <Button className="mt-6" onClick={() => setSessionId(null)}>
          <IconRefresh className="h-4 w-4" /> Luyện thêm
        </Button>
      </div>
    );
  }

  return (
    <div className="animate-float-in mx-auto max-w-xl">
      <div className="mb-4 flex items-center justify-between text-sm text-ink-soft">
        <span>
          Chữ {index + 1}/{characters.length}
        </span>
        <Badge tone="neutral">{mistakes} lần sai</Badge>
      </div>

      <Card className="flex flex-col items-center gap-4 p-6">
        <div ref={targetRef} className="rounded-xl border border-border-soft bg-surface-2" />
        <div className="flex items-center gap-3">
          <span className="text-sm text-gold">{current.pinyin}</span>
          <AudioButton text={current.character} size="sm" />
        </div>
        <p className="text-center text-sm text-ink-soft">
          <span className="hanzi font-semibold text-ink">{current.word}</span> · {current.meaning}
        </p>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={replay}>
            Xem lại nét
          </Button>
          <Button variant="ghost" size="sm" onClick={hint}>
            Gợi ý
          </Button>
        </div>
      </Card>

      {completed && (
        <Button className="mt-6 w-full" size="lg" onClick={next}>
          Chữ tiếp theo
        </Button>
      )}
    </div>
  );
}
