import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import clsx from "clsx";
import { api } from "../lib/api";
import { useApi } from "../lib/useApi";
import { useLevel } from "../lib/levelContext";
import { useSettings } from "../lib/settings";
import { useToast } from "../lib/toast";
import { formatInterval, formatNumber, formatPercent, shortMeaning } from "../lib/format";
import { useShortcuts } from "../lib/useShortcuts";
import type { HskLevel, ReviewRating, VocabularyItem } from "../lib/types";
import {
  AudioButton,
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  FavoriteButton,
  Kbd,
  PageHeader,
  PageSkeleton,
  ProgressBar,
  ProgressRing,
  StatTile,
} from "../components/ui";
import { IconBolt, IconCheck, IconEye, IconRefresh, IconTarget } from "../components/icons";

const RATINGS: Array<{
  value: ReviewRating;
  label: string;
  hint: string;
  key: string;
  className: string;
}> = [
  { value: "again", label: "Quên rồi", hint: "Học lại ngay", key: "1", className: "bg-danger text-white hover:brightness-110" },
  { value: "hard", label: "Khó", hint: "Ôn sớm hơn", key: "2", className: "bg-gold text-black hover:brightness-110" },
  { value: "good", label: "Nhớ", hint: "Đúng lịch", key: "3", className: "bg-jade text-black hover:brightness-110" },
  { value: "easy", label: "Quá dễ", hint: "Giãn cách xa", key: "4", className: "bg-sky text-black hover:brightness-110" },
];

interface SessionTally {
  reviewed: number;
  correct: number;
}

export default function Review() {
  const { level } = useLevel();
  const { settings } = useSettings();
  const toast = useToast();

  const [queue, setQueue] = useState<VocabularyItem[]>([]);
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [tally, setTally] = useState<SessionTally>({ reviewed: 0, correct: 0 });
  const [submitting, setSubmitting] = useState(false);

  const levelParam = level === "all" ? undefined : (level as HskLevel);
  const stats = useApi(() => api.review.stats(), []);

  const loadQueue = useCallback(() => {
    return api.review.queue({
      limit: settings.session_size,
      hsk_level: levelParam,
      include_new: true,
      new_limit: settings.new_words_per_day,
    });
  }, [levelParam, settings.session_size, settings.new_words_per_day]);

  const queueRequest = useApi(loadQueue, [levelParam, settings.session_size, settings.new_words_per_day]);

  useEffect(() => {
    if (queueRequest.data) {
      setQueue(queueRequest.data.items);
      setIndex(0);
      setRevealed(false);
      setTally({ reviewed: 0, correct: 0 });
    }
  }, [queueRequest.data]);

  const current = queue[index];
  const finished = queue.length > 0 && index >= queue.length;

  const submit = useCallback(
    async (rating: ReviewRating) => {
      if (!current || submitting) return;
      setSubmitting(true);
      try {
        const result = await api.review.submit(current.id, rating);
        setTally((previous) => ({
          reviewed: previous.reviewed + 1,
          correct: previous.correct + (rating === "again" ? 0 : 1),
        }));
        if (rating === "again") {
          // A forgotten word goes back to the end of this session so it is seen
          // again before the user leaves the page.
          setQueue((previous) => [...previous, current]);
        }
        setIndex((previous) => previous + 1);
        setRevealed(false);
        if (result.status === "mastered") {
          toast.success(`Đã thuộc ${current.hanzi}`, `Lần ôn tiếp theo sau ${formatInterval(result.interval_days)}.`);
        }
      } catch (error) {
        toast.error(
          "Không lưu được kết quả",
          error instanceof Error ? error.message : "Vui lòng thử lại."
        );
      } finally {
        setSubmitting(false);
      }
    },
    [current, submitting, toast]
  );

  const toggleFavorite = useCallback(async () => {
    if (!current) return;
    const next = !current.is_favorite;
    setQueue((previous) =>
      previous.map((item) => (item.id === current.id ? { ...item, is_favorite: next } : item))
    );
    try {
      await api.review.setFavorite(current.id, next);
    } catch {
      setQueue((previous) =>
        previous.map((item) => (item.id === current.id ? { ...item, is_favorite: !next } : item))
      );
      toast.error("Không lưu được đánh dấu");
    }
  }, [current, toast]);

  // Space reveals, 1-4 rate. Only bound while a card is on screen.
  useShortcuts({
    enabled: Boolean(current),
    onAdvance: () => setRevealed(true),
    onPick: (choice) => {
      if (!revealed) return;
      const rating = RATINGS[choice - 1];
      if (rating) void submit(rating.value);
    },
  });

  const sessionAccuracy = tally.reviewed ? (tally.correct / tally.reviewed) * 100 : 0;
  const progressPercent = queue.length ? (Math.min(index, queue.length) / queue.length) * 100 : 0;

  const header = useMemo(
    () => (
      <PageHeader
        eyebrow="Lặp lại ngắt quãng"
        title="Ôn tập thông minh"
        description="Thuật toán SM-2 chọn đúng từ bạn sắp quên, để mỗi phút ôn tập đều có giá trị."
        action={
          <Button variant="secondary" onClick={() => queueRequest.reload()} disabled={queueRequest.loading}>
            <IconRefresh className="h-4 w-4" /> Tải lại hàng đợi
          </Button>
        }
      />
    ),
    [queueRequest]
  );

  if (queueRequest.loading && queue.length === 0) return <PageSkeleton tiles={4} rows={1} />;
  if (queueRequest.error) return <ErrorState message={queueRequest.error} onRetry={queueRequest.reload} />;

  return (
    <div className="animate-float-in">
      {header}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile
          label="Đến hạn hôm nay"
          value={formatNumber(stats.data?.due_now)}
          accent="accent"
          icon={<IconTarget className="h-4 w-4" />}
        />
        <StatTile
          label="Đang trong lịch"
          value={formatNumber(stats.data?.in_rotation)}
          hint={`${formatNumber(stats.data?.total_vocabulary)} từ tổng cộng`}
          accent="sky"
        />
        <StatTile
          label="Tỉ lệ nhớ"
          value={formatPercent(stats.data?.retention_percentage, 1)}
          hint={`${formatNumber(stats.data?.total_reviews)} lượt ôn`}
          accent="jade"
        />
        <StatTile
          label="Độ dễ trung bình"
          value={stats.data ? stats.data.average_ease.toFixed(2) : "—"}
          hint="Càng cao càng nhớ lâu"
          accent="violet"
          icon={<IconBolt className="h-4 w-4" />}
        />
      </div>

      {queue.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            title="Không còn từ nào đến hạn"
            description="Bạn đã ôn hết phần của hôm nay. Quay lại sau, hoặc học từ mới ở trang Từ vựng."
            action={
              <Link to="/vocabulary">
                <Button>Khám phá từ vựng</Button>
              </Link>
            }
          />
        </div>
      ) : finished ? (
        <SessionSummary
          tally={tally}
          accuracy={sessionAccuracy}
          onRestart={() => {
            queueRequest.reload();
            stats.reload();
          }}
        />
      ) : (
        <>
          <div className="mt-8 flex items-center gap-4">
            <ProgressBar value={progressPercent} accent="jade" />
            <span className="tnum shrink-0 text-xs font-semibold text-ink-soft">
              {Math.min(index + 1, queue.length)} / {queue.length}
            </span>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={`${current?.id}-${index}`}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -14 }}
              transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            >
              <ReviewCard
                item={current}
                revealed={revealed}
                showPinyin={settings.show_pinyin}
                showTraditional={settings.show_traditional}
                onReveal={() => setRevealed(true)}
                onToggleFavorite={toggleFavorite}
              />
            </motion.div>
          </AnimatePresence>

          <div className="mt-5">
            {revealed ? (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {RATINGS.map((rating) => (
                  <button
                    key={rating.value}
                    onClick={() => submit(rating.value)}
                    disabled={submitting}
                    className={clsx(
                      "flex flex-col items-center gap-0.5 rounded-xl px-4 py-3.5 font-semibold transition-all duration-200 active:scale-[0.98] disabled:opacity-60",
                      rating.className
                    )}
                  >
                    <span className="text-sm">{rating.label}</span>
                    <span className="text-[10px] font-medium opacity-80">{rating.hint}</span>
                    <span className="mt-1 rounded border border-black/20 bg-black/10 px-1.5 text-[10px] font-bold">
                      {rating.key}
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <Button size="lg" className="w-full" onClick={() => setRevealed(true)}>
                <IconEye className="h-4 w-4" /> Hiện đáp án
                <Kbd>Space</Kbd>
              </Button>
            )}
          </div>

          <p className="mt-4 text-center text-xs text-ink-faint">
            Phím tắt: <Kbd>Space</Kbd> hiện đáp án · <Kbd>1</Kbd>–<Kbd>4</Kbd> đánh giá
          </p>
        </>
      )}
    </div>
  );
}

function ReviewCard({
  item,
  revealed,
  showPinyin,
  showTraditional,
  onReveal,
  onToggleFavorite,
}: {
  item: VocabularyItem | undefined;
  revealed: boolean;
  showPinyin: boolean;
  showTraditional: boolean;
  onReveal: () => void;
  onToggleFavorite: () => void;
}) {
  if (!item) return null;
  const isNew = !item.due_at;

  return (
    <Card className="mt-5 overflow-hidden">
      <div className="flex items-center justify-between border-b border-border-soft px-5 py-3">
        <div className="flex items-center gap-2">
          <Badge tone={isNew ? "sky" : "accent"}>{isNew ? "Từ mới" : "Đến hạn ôn"}</Badge>
          <Badge tone="neutral">HSK {item.hsk_level}</Badge>
          {item.lapses > 0 && <Badge tone="danger">{item.lapses} lần quên</Badge>}
        </div>
        <div className="flex items-center gap-2">
          <AudioButton text={item.hanzi} size="sm" />
          <FavoriteButton active={Boolean(item.is_favorite)} onToggle={onToggleFavorite} />
        </div>
      </div>

      <button
        onClick={onReveal}
        className="flex w-full flex-col items-center justify-center gap-3 px-6 py-14 text-center"
        aria-label={revealed ? undefined : "Hiện đáp án"}
      >
        <p className="hanzi text-6xl font-bold leading-none text-ink sm:text-7xl">{item.hanzi}</p>
        {showTraditional && item.traditional && item.traditional !== item.hanzi && (
          <p className="hanzi text-lg text-ink-faint">{item.traditional}</p>
        )}
        {showPinyin && <p className="text-lg font-medium text-accent">{item.pinyin}</p>}

        {revealed ? (
          <div className="mt-2 w-full max-w-lg border-t border-border-soft pt-4">
            <p className="text-xl font-semibold text-ink">
              {shortMeaning(item.meaning, { senses: 3, chars: 110 })}
            </p>
            {/* Labelled, and quieter than the Vietnamese. The project rule is
                that a learner reads Vietnamese; English is a reference they can
                consult, never a second definition competing for attention. */}
            {item.meaning_en && (
              <p className="mt-2 text-xs text-ink-faint">
                <span className="font-semibold">Tiếng Anh: </span>
                {shortMeaning(item.meaning_en, { senses: 2, chars: 90 })}
              </p>
            )}
            {item.pos_vi && (
              <p className="mt-2 text-xs uppercase tracking-wide text-ink-faint">{item.pos_vi}</p>
            )}
            {item.example && (
              <div className="mt-4 rounded-xl bg-surface-2 p-4 text-left">
                <p className="hanzi text-base text-ink">{item.example}</p>
                {item.example_pinyin && <p className="mt-1 text-xs text-accent">{item.example_pinyin}</p>}
                {item.example_meaning && (
                  <p className="mt-1 text-xs text-ink-soft">{item.example_meaning}</p>
                )}
              </div>
            )}
            {item.note && (
              <p className="mt-3 rounded-xl border border-gold/30 bg-gold-soft px-3 py-2 text-left text-xs text-gold">
                {item.note}
              </p>
            )}
          </div>
        ) : (
          <p className="mt-2 text-sm text-ink-faint">Nhấn để xem nghĩa</p>
        )}
      </button>
    </Card>
  );
}

function SessionSummary({
  tally,
  accuracy,
  onRestart,
}: {
  tally: SessionTally;
  accuracy: number;
  onRestart: () => void;
}) {
  return (
    <Card className="mt-8 flex flex-col items-center gap-5 px-6 py-12 text-center">
      <ProgressRing value={accuracy} accent="jade" size={140}>
        <span className="font-display tnum text-3xl font-bold text-jade">{Math.round(accuracy)}%</span>
        <span className="text-xs text-ink-faint">chính xác</span>
      </ProgressRing>
      <div>
        <p className="font-display text-2xl font-bold text-ink">Hoàn thành phiên ôn tập</p>
        <p className="mt-1 text-sm text-ink-soft">
          Bạn đã ôn {formatNumber(tally.reviewed)} lượt, nhớ đúng {formatNumber(tally.correct)} từ.
        </p>
      </div>
      <div className="flex flex-wrap justify-center gap-3">
        <Button onClick={onRestart}>
          <IconRefresh className="h-4 w-4" /> Ôn tiếp
        </Button>
        <Link to="/progress">
          <Button variant="secondary">
            <IconCheck className="h-4 w-4" /> Xem tiến độ
          </Button>
        </Link>
      </div>
    </Card>
  );
}
