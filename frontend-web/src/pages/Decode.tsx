/**
 * Giải mã Hán-Việt — the screen that teaches reading past the syllabus.
 *
 * Every other practice page here asks the learner to recall a word they were
 * taught. This one hands them a word they were *not* taught and asks them to
 * work it out, which a Vietnamese learner can do and most other learners
 * cannot: each character has a fixed âm Hán-Việt, so 图书馆 spells out "đồ thư
 * quán" and 发展 spells out "phát triển" — words they have always known.
 *
 * Three tabs, in the order a learner needs them:
 *   Tra chữ    — look a character up: reading, radicals, mnemonic, word family.
 *   Luyện giải mã — the drill, on words deliberately drawn from the unstudied pile.
 *   Chữ chủ lực — characters ranked by how much vocabulary each one unlocks.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { api } from "../lib/api";
import { useLevel } from "../lib/levelContext";
import { useToast } from "../lib/toast";
import { useApi } from "../lib/useApi";
import { formatNumber, formatPercent, shortMeaning } from "../lib/format";
import { useShortcuts } from "../lib/useShortcuts";
import type {
  CharacterItem,
  DecodeMode,
  DecodeQuestion,
  HskLevel,
} from "../lib/types";
import {
  AudioButton,
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Kbd,
  LoadingState,
  PageHeader,
  PracticeBar,
  ProgressBar,
  Segmented,
  SessionComplete,
  SessionSizePicker,
  StatTile,
  SectionTitle,
} from "../components/ui";
import {
  IconArrowRight,
  IconCheck,
  IconRefresh,
  IconSearch,
  IconSpark,
  IconX,
} from "../components/icons";

type Tab = "lookup" | "drill" | "leverage";

const TABS: Array<{ value: Tab; label: string }> = [
  { value: "lookup", label: "Tra chữ" },
  { value: "drill", label: "Luyện giải mã" },
  { value: "leverage", label: "Chữ chủ lực" },
];

const MODES: Array<{ value: DecodeMode; label: string; blurb: string }> = [
  {
    value: "han_viet_to_meaning",
    label: "Âm Hán-Việt → nghĩa",
    blurb: "Từ chưa học, đoán nghĩa qua âm Hán-Việt",
  },
  {
    value: "meaning_to_han_viet",
    label: "Nghĩa → âm Hán-Việt",
    blurb: "Nhớ lại cách đọc Hán-Việt của cả từ",
  },
  {
    value: "character_reading",
    label: "Từng chữ",
    blurb: "Nền tảng: âm Hán-Việt của mỗi chữ",
  },
];

/** Readings from the weaker source get a caveat rather than silent confidence. */
const UNCERTAIN_SOURCES = new Set(["wiktionary-forms", "variant"]);

export default function Decode() {
  const [tab, setTab] = useState<Tab>("lookup");

  return (
    <div className="animate-float-in">
      <PageHeader
        eyebrow="Vượt ngoài HSK"
        title="Giải mã Hán-Việt"
        description="Hơn một nửa từ vựng tiếng Việt là gốc Hán. Mỗi chữ Hán có một âm Hán-Việt cố định, nên 图书馆 đọc là “đồ thư quán” và 发展 là “phát triển”. Nắm được lớp chữ này, bạn đọc hiểu được cả những từ chưa bao giờ học."
      />
      <div className="mb-6">
        <Segmented value={tab} onChange={setTab} options={TABS} label="Chế độ" />
      </div>
      {tab === "lookup" && <LookupTab />}
      {tab === "drill" && <DrillTab />}
      {tab === "leverage" && <LeverageTab />}
    </div>
  );
}

/* ------------------------------------------------------------------ lookup */

function LookupTab() {
  const [query, setQuery] = useState("学");
  const [debounced, setDebounced] = useState("学");
  const [detail, setDetail] = useState<CharacterItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query.trim()), 300);
    return () => clearTimeout(timer);
  }, [query]);

  // Typing a whole word is the natural thing to do, and looking up only the
  // first character of it is the natural thing to want.
  const target = useMemo(() => {
    const chars = Array.from(debounced).filter((char) => /[一-鿿]/.test(char));
    return chars[0] ?? "";
  }, [debounced]);

  // Most people cannot type Chinese. Asking a screen about âm Hán-Việt to be
  // opened with a Chinese character first is backwards: the whole promise is
  // that the learner already knows "học", so typing that — or the pinyin
  // "xue", with or without its tone mark — has to find 学.
  const [matches, setMatches] = useState<CharacterItem[]>([]);
  const romanised = !target && /[a-zà-ỹ]/i.test(debounced);

  useEffect(() => {
    if (!romanised) {
      setMatches([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    api.characters
      .list({ search: debounced, limit: 24 })
      .then((data) => {
        if (!cancelled) {
          setMatches(data.items);
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelled) setMatches([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [debounced, romanised]);

  useEffect(() => {
    if (!target) {
      setDetail(null);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    api.characters
      .get(target)
      .then((data) => {
        if (!cancelled) {
          setDetail(data);
          setError(null);
        }
      })
      .catch((cause: unknown) => {
        if (!cancelled) {
          setDetail(null);
          setError(cause instanceof Error ? cause.message : "Không tra được chữ này.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [target]);

  // Every character of the typed word, so a learner who pastes 图书馆 can step
  // through 图, 书 and 馆 without retyping.
  const siblings = useMemo(
    () => Array.from(new Set(Array.from(debounced).filter((c) => /[一-鿿]/.test(c)))),
    [debounced]
  );

  return (
    <div className="space-y-6">
      <Card className="p-4">
        <label className="relative block">
          <span className="sr-only">Tra chữ Hán</span>
          <IconSearch className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-faint" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Gõ chữ Hán, pinyin hoặc âm Hán-Việt: 学, xue, hoc..."
            className="hanzi w-full rounded-xl border border-border bg-surface-2 py-2.5 pl-10 pr-3 text-base text-ink outline-none focus:border-accent"
          />
        </label>
        {siblings.length > 1 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {siblings.map((char) => (
              <button
                key={char}
                onClick={() => setQuery(char)}
                className={clsx(
                  "hanzi rounded-lg border px-3 py-1 text-lg transition-colors",
                  char === target
                    ? "border-accent bg-accent-soft text-accent"
                    : "border-border text-ink-soft hover:text-ink"
                )}
              >
                {char}
              </button>
            ))}
          </div>
        )}
      </Card>

      {loading && <LoadingState label="Đang tra chữ" />}
      {!loading && error && <ErrorState message={error} />}

      {!loading && !error && romanised && matches.length > 0 && (
        <section>
          <SectionTitle>Chữ khớp với “{debounced}”</SectionTitle>
          <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-4">
            {matches.map((match) => (
              <Card
                key={match.hanzi}
                className="cursor-pointer p-3 transition-colors hover:border-border-strong"
                onClick={() => setQuery(match.hanzi)}
                lift
              >
                <div className="flex items-start gap-3">
                  <span className="hanzi text-3xl font-bold leading-none text-ink">
                    {match.hanzi}
                  </span>
                  <div className="min-w-0">
                    <p className="font-display text-sm font-bold text-gold">{match.han_viet}</p>
                    <p className="text-xs text-accent">{match.pinyin}</p>
                    <p className="line-clamp-1 text-xs text-ink-soft">{match.meaning_vi}</p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </section>
      )}

      {!loading && !error && romanised && matches.length === 0 && (
        <EmptyState
          title={`Không có chữ nào khớp “${debounced}”`}
          description="Thử một âm Hán-Việt khác, hoặc gõ thẳng chữ Hán."
        />
      )}

      {!loading && !error && !target && !romanised && (
        <EmptyState
          title="Nhập chữ Hán, pinyin hoặc âm Hán-Việt"
          description="Gõ “hoc” hay “xue” đều ra 学. Dán cả từ thì ứng dụng tách từng chữ ra cho bạn chọn."
        />
      )}
      {!loading && !error && detail && <CharacterDetail item={detail} onPick={setQuery} />}
    </div>
  );
}

function CharacterDetail({
  item,
  onPick,
}: {
  item: CharacterItem;
  onPick: (hanzi: string) => void;
}) {
  const toast = useToast();
  const [status, setStatus] = useState(item.status);

  useEffect(() => setStatus(item.status), [item.hanzi, item.status]);

  async function mark(next: "new" | "learning" | "mastered") {
    setStatus(next);
    try {
      await api.characters.setStatus(item.hanzi, next);
    } catch (error) {
      setStatus(item.status);
      toast.error(
        "Không lưu được trạng thái",
        error instanceof Error ? error.message : undefined
      );
    }
  }

  const byLevel = useMemo(() => {
    const groups = new Map<string, typeof item.words>();
    for (const word of item.words ?? []) {
      const bucket = groups.get(word.hsk_level) ?? [];
      bucket.push(word);
      groups.set(word.hsk_level, bucket);
    }
    return [...groups.entries()];
  }, [item.words]);

  return (
    <div className="space-y-6">
      <Card ornament inlay className="p-6">
        <div className="flex flex-wrap items-start gap-6">
          <div className="text-center">
            <p className="hanzi text-7xl font-bold leading-none text-ink">{item.hanzi}</p>
            {item.traditional && item.traditional !== item.hanzi && (
              <p className="hanzi mt-2 text-sm text-ink-faint">Phồn thể: {item.traditional}</p>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-display text-2xl font-bold text-gold">
                {item.han_viet || "—"}
              </p>
              <span className="text-lg text-accent">{item.pinyin}</span>
              <AudioButton text={item.hanzi} />
              {item.hsk_level && <Badge tone="neutral">HSK {item.hsk_level}</Badge>}
            </div>
            {item.meaning_vi && <p className="mt-2 text-ink">{item.meaning_vi}</p>}
            {UNCERTAIN_SOURCES.has(item.han_viet_source) && (
              <p className="mt-2 text-xs text-ink-faint">
                Âm Hán-Việt suy ra từ dạng phồn thể hoặc từ điển cộng đồng — nên đối chiếu lại
                với từ điển giấy nếu bạn dùng cho việc quan trọng.
              </p>
            )}
            <div className="mt-3 flex flex-wrap gap-4 text-xs text-ink-soft">
              {item.stroke_count != null && <span>{item.stroke_count} nét</span>}
              <span>{formatNumber(item.word_count)} từ trong kho dùng chữ này</span>
            </div>
          </div>
        </div>

        {item.mnemonic_vi && (
          <div className="mt-5 rounded-xl border border-border-soft bg-surface-2 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
              Mẹo nhớ mặt chữ
            </p>
            <p className="mt-1 text-sm leading-relaxed text-ink">{item.mnemonic_vi}</p>
            {item.stroke_hint_vi && (
              <p className="mt-2 text-sm leading-relaxed text-ink-soft">{item.stroke_hint_vi}</p>
            )}
          </div>
        )}

        <div className="mt-5 flex flex-wrap items-center gap-2">
          <span className="text-xs text-ink-faint">Bạn đã nắm chữ này chưa?</span>
          <Segmented
            value={status}
            onChange={(next) => void mark(next)}
            options={[
              { value: "new", label: "Chưa" },
              { value: "learning", label: "Đang học" },
              { value: "mastered", label: "Đã nắm" },
            ]}
            label="Trạng thái chữ"
          />
        </div>
      </Card>

      {(item.radical_details ?? []).length > 0 && (
        <section>
          {/* Only 659 characters have a hand-written decomposition. The rest
              get the radical they are filed under, which is one component
              rather than a breakdown — so the heading says which of the two
              this is instead of passing one off as the other. */}
          <SectionTitle>
            {item.radical_source === "kangxi" ? "Bộ thủ" : "Chiết tự"}
          </SectionTitle>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {(item.radical_details ?? []).map((radical) => (
              <Card key={radical.hanzi} className="p-4">
                <div className="flex items-baseline gap-3">
                  <span className="hanzi text-3xl font-semibold text-ink">{radical.hanzi}</span>
                  <span className="text-sm font-semibold text-accent">{radical.name_vi}</span>
                </div>
                {radical.meaning_vi && (
                  <p className="mt-1 text-sm text-ink-soft">{radical.meaning_vi}</p>
                )}
                {radical.mnemonic_vi && (
                  <p className="mt-1 text-xs text-ink-faint">{radical.mnemonic_vi}</p>
                )}
              </Card>
            ))}
          </div>
        </section>
      )}

      {byLevel.length > 0 && (
        <section>
          <SectionTitle
            action={
              <span className="shrink-0 text-xs text-ink-faint">
                {formatNumber(item.word_count)} từ trong kho
              </span>
            }
          >
            Họ từ
          </SectionTitle>
          <div className="space-y-4">
            {byLevel.map(([level, words]) => (
              <div key={level}>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">
                  HSK {level}
                </p>
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {(words ?? []).map((word) => (
                    <Card
                      key={word.id}
                      className="cursor-pointer p-3 transition-colors hover:border-border-strong"
                      onClick={() => onPick(word.hanzi)}
                      title={word.meaning}
                    >
                      <div className="flex items-baseline justify-between gap-2">
                        <span className="hanzi text-lg font-semibold text-ink">{word.hanzi}</span>
                        {word.status === "mastered" && <Badge tone="jade">đã thuộc</Badge>}
                      </div>
                      <p className="mt-0.5 text-xs text-accent">{word.pinyin}</p>
                      {word.han_viet && (
                        <p className="text-xs font-medium text-gold">{word.han_viet}</p>
                      )}
                      <p className="mt-1 line-clamp-2 text-xs text-ink-soft">
                        {shortMeaning(word.meaning, { senses: 2, chars: 60 })}
                      </p>
                    </Card>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------- drill */

function DrillTab() {
  const { level } = useLevel();
  const toast = useToast();

  const [mode, setMode] = useState<DecodeMode>("han_viet_to_meaning");
  const [count, setCount] = useState(10);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [question, setQuestion] = useState<DecodeQuestion | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [index, setIndex] = useState(0);
  const [score, setScore] = useState({ correct: 0, incorrect: 0 });
  const [finished, setFinished] = useState(false);
  const [busy, setBusy] = useState(false);

  const stats = useApi(() => api.characters.drillStats(), []);
  const overview = useApi(() => api.characters.stats(), []);

  const answer =
    question && (mode === "han_viet_to_meaning"
      ? shortMeaning(question.meaning, { senses: 1, chars: 42 })
      : question.han_viet);

  const load = useCallback(async (id: number) => {
    setBusy(true);
    try {
      setQuestion(await api.characters.next(id));
      setPicked(null);
    } catch (error) {
      toast.error("Không tạo được câu hỏi", error instanceof Error ? error.message : undefined);
    } finally {
      setBusy(false);
    }
  }, [toast]);

  async function start() {
    setBusy(true);
    try {
      const session = await api.characters.createSession(
        mode,
        count,
        level === "all" ? null : (level as HskLevel)
      );
      setSessionId(session.session_id);
      setIndex(0);
      setScore({ correct: 0, incorrect: 0 });
      setFinished(false);
      await load(session.session_id);
    } catch (error) {
      toast.error("Không bắt đầu được phiên", error instanceof Error ? error.message : undefined);
      setBusy(false);
    }
  }

  const choose = useCallback(
    async (option: string) => {
      if (!sessionId || !question || picked || busy) return;
      setPicked(option);
      const isCorrect = option === answer;
      setScore((current) => ({
        correct: current.correct + (isCorrect ? 1 : 0),
        incorrect: current.incorrect + (isCorrect ? 0 : 1),
      }));
      try {
        await api.characters.attempt(sessionId, question.word, isCorrect, question.vocabulary_id);
      } catch {
        // The answer is already on screen; a failed log must not undo it.
      }
    },
    [answer, busy, picked, question, sessionId]
  );

  const advance = useCallback(async () => {
    if (!sessionId || !picked) return;
    if (index + 1 >= count) {
      try {
        await api.characters.complete(sessionId, count, score.correct, score.incorrect);
      } catch {
        // Same reasoning: the session happened whether or not the summary saved.
      }
      setFinished(true);
      stats.reload();
      overview.reload();
      return;
    }
    setIndex(index + 1);
    await load(sessionId);
  }, [count, index, load, overview, picked, score, sessionId, stats]);

  useShortcuts({
    enabled: Boolean(sessionId) && !finished,
    onNext: () => {
      if (picked) void advance();
    },
    onPick: (choice) => {
      if (picked || !question) return;
      const option = question.options[choice - 1];
      if (option) void choose(option);
    },
  });

  if (finished) {
    return (
      <SessionComplete
        correct={score.correct}
        total={count}
        unit="từ"
        detail={`Bạn giải mã đúng ${score.correct} trên ${count} từ chưa từng học.`}
        primary={
          <Button size="lg" onClick={() => setSessionId(null)}>
            <IconRefresh className="h-4 w-4" /> Phiên mới
          </Button>
        }
      />
    );
  }

  if (!sessionId) {
    const decodable = overview.data
      ? Math.round((overview.data.words_decodable / Math.max(1, overview.data.words_total)) * 100)
      : null;
    return (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label="Chữ đã nắm"
            value={formatNumber(overview.data?.mastered)}
            hint={`trên ${formatNumber(overview.data?.total)} chữ trong kho`}
            accent="jade"
            index={0}
          />
          <StatTile
            label="Từ đã mở khoá"
            value={formatNumber(overview.data?.words_unlocked)}
            hint="từ chứa chữ bạn đã nắm"
            accent="gold"
            icon={<IconSpark className="h-4 w-4" />}
            index={1}
          />
          <StatTile
            label="Chữ đến hạn ôn"
            value={formatNumber(overview.data?.due_now)}
            hint={
              decodable == null
                ? "sẽ có sau vài lượt luyện"
                : `${decodable}% từ trong kho giải mã được`
            }
            accent="sky"
            index={2}
          />
          <StatTile
            label="Độ chính xác"
            value={formatPercent(stats.data?.accuracy)}
            hint={`${formatNumber((stats.data?.correct ?? 0) + (stats.data?.incorrect ?? 0))} lượt`}
            accent="accent"
            index={3}
          />
        </div>

        <Card className="max-w-xl p-6">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-ink-faint">
            Chọn kiểu luyện
          </p>
          <div className="space-y-2">
            {MODES.map((option) => (
              <button
                key={option.value}
                onClick={() => setMode(option.value)}
                className={clsx(
                  "w-full rounded-xl border px-4 py-3 text-left transition-colors",
                  option.value === mode
                    ? "border-accent bg-accent-soft"
                    : "border-border hover:border-border-strong"
                )}
              >
                <p
                  className={clsx(
                    "text-sm font-semibold",
                    option.value === mode ? "text-accent" : "text-ink"
                  )}
                >
                  {option.label}
                </p>
                <p className="text-xs text-ink-soft">{option.blurb}</p>
              </button>
            ))}
          </div>
          <div className="mt-4">
            <SessionSizePicker value={count} onChange={setCount} max={30} unit="câu" />
          </div>
          <Button className="mt-4 w-full" size="lg" disabled={busy} onClick={start}>
            {busy
              ? "Đang chuẩn bị..."
              : `Bắt đầu ${count} câu (${level === "all" ? "mọi cấp độ" : `HSK ${level}`})`}
          </Button>
          <p className="mt-3 text-center text-xs text-ink-faint">
            {mode === "character_reading"
              ? "Chữ nào bạn vừa quên sẽ quay lại trước — lịch ôn riêng cho từng chữ."
              : "Đề ưu tiên những từ bạn chưa mở bao giờ — vì chỉ khi đó bạn mới thật sự phải giải mã."}
          </p>
        </Card>
      </div>
    );
  }

  if (!question) return <LoadingState label="Đang tạo câu hỏi" />;

  const revealed = picked !== null;

  return (
    <div className="mx-auto max-w-2xl">
      <PracticeBar
        position={index + 1}
        total={count}
        badge={<Badge tone="neutral">HSK {question.hsk_level}</Badge>}
      >
        <span className="text-xs text-ink-soft">
          {score.correct} đúng · {score.incorrect} sai
        </span>
      </PracticeBar>

      <ProgressBar value={(index / count) * 100} />

      <Card ornament className="mt-6 p-6 text-center">
        {mode === "meaning_to_han_viet" ? (
          <p className="text-xl font-semibold text-ink">{question.prompt.meaning}</p>
        ) : (
          <>
            <p className="hanzi text-5xl font-bold leading-tight text-ink">{question.word}</p>
            <p className="mt-2 text-sm text-accent">{question.pinyin}</p>
          </>
        )}

        {/* The clue. Not a hint to be unlocked — the whole exercise is reading
            this row and turning it into a Vietnamese word. */}
        {mode !== "meaning_to_han_viet" && question.breakdown.length > 0 && (
          <div className="mt-5 flex flex-wrap items-stretch justify-center gap-2">
            {question.breakdown.map((part, position) => (
              <div
                key={`${part.hanzi}-${position}`}
                className="min-w-[5.5rem] rounded-xl border border-border-soft bg-surface-2 px-3 py-2"
              >
                <p className="hanzi text-2xl font-semibold text-ink">{part.hanzi}</p>
                <p className="font-display text-sm font-bold text-gold">{part.han_viet || "?"}</p>
                {revealed && part.meaning_vi && (
                  <p className="mt-0.5 text-[11px] leading-tight text-ink-soft">
                    {part.meaning_vi}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}

        {mode === "meaning_to_han_viet" && (
          <p className="hanzi mt-4 text-4xl font-bold text-ink">{question.word}</p>
        )}
      </Card>

      <p className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-ink-faint">
        <span>
          <Kbd>1</Kbd>–<Kbd>4</Kbd> chọn đáp án
        </span>
        <span>
          <Kbd>Enter</Kbd> câu tiếp theo
        </span>
      </p>

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {question.options.map((option, position) => {
          const isAnswer = option === answer;
          const isPicked = option === picked;
          return (
            <button
              key={option}
              onClick={() => void choose(option)}
              disabled={revealed}
              className={clsx(
                "flex items-center gap-2 rounded-xl border px-4 py-3 text-left text-sm transition-colors",
                !revealed && "border-border hover:border-accent hover:bg-accent-soft",
                revealed && isAnswer && "border-jade bg-jade-soft text-jade",
                revealed && isPicked && !isAnswer && "border-danger bg-danger-soft text-danger",
                revealed && !isAnswer && !isPicked && "border-border opacity-60"
              )}
            >
              <span className="shrink-0 text-xs text-ink-faint">{position + 1}</span>
              <span className="min-w-0 flex-1">{option}</span>
              {revealed && isAnswer && <IconCheck className="h-4 w-4 shrink-0" />}
              {revealed && isPicked && !isAnswer && <IconX className="h-4 w-4 shrink-0" />}
            </button>
          );
        })}
      </div>

      {revealed && (
        <Card className="mt-4 p-4">
          <p className="text-sm text-ink">
            <span className="hanzi font-semibold">{question.word}</span>{" "}
            <span className="text-accent">{question.pinyin}</span>{" "}
            <span className="font-display font-bold text-gold">{question.han_viet}</span>
          </p>
          <p className="mt-1 text-sm text-ink-soft">{question.meaning}</p>
          <Button className="mt-4 w-full" onClick={() => void advance()}>
            {index + 1 >= count ? "Xem kết quả" : "Câu tiếp theo"}{" "}
            <IconArrowRight className="h-4 w-4" />
          </Button>
        </Card>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- leverage */

function LeverageTab() {
  const { level } = useLevel();
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 36;

  const list = useApi(
    () =>
      api.characters.list({
        hskLevel: level === "all" ? null : (level as HskLevel),
        sort: "reach",
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
    [level, page]
  );

  useEffect(() => setPage(0), [level]);

  if (list.loading && !list.data) return <LoadingState label="Đang xếp hạng chữ" />;
  if (list.error) return <ErrorState message={list.error} onRetry={list.reload} />;
  if (!list.data || list.data.items.length === 0) {
    return (
      <EmptyState
        title="Chưa có chữ nào ở cấp độ này"
        description="Hãy đổi cấp độ ở thanh bên để xem bảng xếp hạng."
      />
    );
  }

  const maxReach = Math.max(...list.data.items.map((item) => item.word_count), 1);
  const pages = Math.ceil(list.data.total / PAGE_SIZE);

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-soft">
        Xếp theo số từ mà mỗi chữ mở khoá. Học theo thứ tự này, mỗi chữ nắm được sẽ kéo theo
        hàng chục từ — kể cả những từ nằm ngoài giáo trình HSK.
      </p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {list.data.items.map((item) => (
          <Card key={item.hanzi} className="p-4" lift>
            <div className="flex items-start gap-3">
              <span className="hanzi text-4xl font-bold leading-none text-ink">{item.hanzi}</span>
              <div className="min-w-0 flex-1">
                <p className="font-display text-base font-bold text-gold">{item.han_viet || "—"}</p>
                <p className="text-xs text-accent">{item.pinyin}</p>
                <p className="mt-0.5 line-clamp-2 text-xs text-ink-soft">{item.meaning_vi}</p>
              </div>
              {item.status === "mastered" && <Badge tone="jade">đã nắm</Badge>}
            </div>
            <div className="mt-3">
              <div className="flex items-baseline justify-between text-xs">
                <span className="text-ink-faint">mở khoá</span>
                <span className="font-semibold text-ink">{formatNumber(item.word_count)} từ</span>
              </div>
              <div className="mt-1">
                <ProgressBar value={(item.word_count / maxReach) * 100} accent="gold" />
              </div>
            </div>
          </Card>
        ))}
      </div>
      {pages > 1 && (
        <div className="flex items-center justify-center gap-3 pt-2">
          <Button
            variant="secondary"
            disabled={page === 0}
            onClick={() => setPage((value) => Math.max(0, value - 1))}
          >
            Trước
          </Button>
          <span className="text-xs text-ink-soft">
            Trang {page + 1} / {pages}
          </span>
          <Button
            variant="secondary"
            disabled={page + 1 >= pages}
            onClick={() => setPage((value) => value + 1)}
          >
            Sau
          </Button>
        </div>
      )}
    </div>
  );
}
