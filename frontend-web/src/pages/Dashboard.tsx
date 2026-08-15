import { Suspense, lazy } from "react";
import { Link } from "react-router-dom";
import clsx from "clsx";
import { HIDDEN_ROUTES } from "../components/navigation";
import { BaoTuongHoa } from "../components/Ornament";
import { api } from "../lib/api";
import { useApi } from "../lib/useApi";
import { formatNumber, formatPercent } from "../lib/format";
import {
  Badge,
  Button,
  Card,
  CountUp,
  ErrorState,
  Heatmap,
  PageHeader,
  PageSkeleton,
  ProgressBar,
  ProgressRing,
  Reveal,
  SectionTitle,
  Skeleton,
  StatTile,
} from "../components/ui";
import {
  IconArrowRight,
  IconBolt,
  IconBook,
  IconCheckSquare,
  IconFlame,
  IconHeadphones,
  IconKeyboard,
  IconLayers,
  IconMessage,
  IconMic,
  IconPencil,
  IconRefresh,
  IconShuffle,
  IconTarget,
} from "../components/icons";

// Same hidden-route list the menus use, so a tile can never offer a page the
// sidebar is deliberately not showing.
const FEATURES = [
  { to: "/review", label: "Ôn tập thông minh", desc: "Đúng từ, đúng lúc", icon: IconRefresh, accent: "accent" as const },
  { to: "/vocabulary", label: "Từ vựng", desc: "Tra cứu & lọc theo cấp độ", icon: IconBook, accent: "sky" as const },
  { to: "/flashcards", label: "Flashcard", desc: "Ôn nhanh, tự đánh giá", icon: IconLayers, accent: "gold" as const },
  { to: "/matching", label: "Nối từ", desc: "Ghép Hán tự với nghĩa/pinyin", icon: IconShuffle, accent: "jade" as const },
  { to: "/sentences", label: "Luyện câu", desc: "Sắp xếp cụm từ đúng thứ tự", icon: IconMessage, accent: "sky" as const },
  { to: "/listening", label: "Luyện nghe", desc: "Nghe phát âm, chọn đáp án", icon: IconHeadphones, accent: "violet" as const },
  { to: "/quiz", label: "Kiểm tra", desc: "Trắc nghiệm tổng hợp", icon: IconCheckSquare, accent: "accent" as const },
  { to: "/typing", label: "Luyện gõ", desc: "Gõ lại pinyin hoặc chữ Hán", icon: IconKeyboard, accent: "sky" as const },
  { to: "/hskk", label: "Thi thử HSK", desc: "Trắc nghiệm và phần thi nói", icon: IconMic, accent: "accent" as const },
  { to: "/writing", label: "Luyện viết", desc: "Tập viết chữ Hán đúng nét", icon: IconPencil, accent: "gold" as const },
].filter((feature) => !HIDDEN_ROUTES.has(feature.to));

const WRITING_VISIBLE = !HIDDEN_ROUTES.has("/writing");

type FeatureAccent = (typeof FEATURES)[number]["accent"];

// Tailwind needs whole class names in the source to keep them in the build, so
// these are lookup tables rather than interpolated strings.
const FEATURE_CHIP: Record<FeatureAccent, string> = {
  accent: "bg-accent-soft text-accent",
  gold: "bg-gold-soft text-gold",
  jade: "bg-jade-soft text-jade",
  sky: "bg-sky-soft text-sky",
  violet: "bg-violet-soft text-violet",
};

const FEATURE_TEXT: Record<FeatureAccent, string> = {
  accent: "text-accent",
  gold: "text-gold",
  jade: "text-jade",
  sky: "text-sky",
  violet: "text-violet",
};

const FEATURE_GLOW: Record<FeatureAccent, string> = {
  accent: "bg-accent/25",
  gold: "bg-gold/25",
  jade: "bg-jade/25",
  sky: "bg-sky/25",
  violet: "bg-violet/25",
};



const LEVEL_LABEL: Record<string, string> = {
  "1": "HSK 1", "2": "HSK 2", "3": "HSK 3", "4": "HSK 4",
  "5": "HSK 5", "6": "HSK 6", "7-9": "HSK 7-9",
};

const ForecastChart = lazy(() =>
  import("../components/DashboardCharts").then((module) => ({ default: module.ForecastChart }))
);
const ActivityChart = lazy(() =>
  import("../components/DashboardCharts").then((module) => ({ default: module.ActivityChart }))
);

export default function Dashboard() {
  const dashboard = useApi(() => api.dashboard(), []);
  const streak = useApi(() => api.streak(182), []);
  const review = useApi(() => api.review.stats(), []);

  if (dashboard.loading && !dashboard.data) return <PageSkeleton />;
  if (dashboard.error) return <ErrorState message={dashboard.error} onRetry={dashboard.reload} />;
  const data = dashboard.data;
  if (!data) return null;

  const masteredPct = data.total_vocabulary
    ? (data.mastered_vocabulary / data.total_vocabulary) * 100
    : 0;

  const forecast = (review.data?.forecast ?? []).slice(0, 10).map((point) => ({
    label: point.offset === 0 ? "Hôm nay" : `+${point.offset}`,
    count: point.count,
  }));

  const activity = (streak.data?.history ?? []).slice(-14).map((entry) => ({
    label: entry.activity_date.slice(5),
    reviews: entry.reviews_done,
  }));

  return (
    <div className="animate-float-in">
      <PageHeader
        eyebrow="HSK Master"
        title="Chào mừng trở lại"
        description="Theo dõi tiến độ từ vựng, luyện nghe, luyện viết và kiểm tra trên toàn bộ 9 cấp độ HSK."
        action={
          <Link to="/review">
            <Button size="lg">
              <IconRefresh className="h-4 w-4" />
              {review.data && review.data.due_now > 0
                ? `Ôn ${formatNumber(review.data.due_now)} từ đến hạn`
                : "Bắt đầu ôn tập"}
            </Button>
          </Link>
        }
      />

      {/* Today's goal is the single most actionable thing on this page, so it
          leads the layout ahead of the lifetime totals. */}
      <div className="grid gap-6 lg:grid-cols-3">
        <Card ornament lift inlay className="flex items-center gap-6 p-6">
          {/* The ring and the two badges leave the card's lower right empty, and
              on a card this tall the void was the first thing you noticed. Same
              line-art medallion the rest of the app uses — drawn whole, tucked
              under the content, and cropped by nothing. */}
          <BaoTuongHoa className="pointer-events-none absolute bottom-0 right-0 -z-10 h-36 w-36 text-gold opacity-[0.2]" />
          <ProgressRing value={streak.data?.goal_percentage ?? 0} accent="gold" size={116} stroke={9}>
            <span className="font-display tnum text-2xl font-bold text-gold">
              <CountUp value={streak.data?.today_reviews ?? 0} />
            </span>
            <span className="text-[10px] text-ink-faint">/ {formatNumber(streak.data?.daily_goal)}</span>
          </ProgressRing>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">Mục tiêu hôm nay</p>
            <p className="font-display mt-1 text-xl font-bold text-ink">
              {streak.data?.goal_met ? "Đã hoàn thành" : "Tiếp tục nào"}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Badge tone="accent">
                <IconFlame className="h-3 w-3" /> {formatNumber(streak.data?.current_streak)} ngày
              </Badge>
              <Badge tone="gold">
                <IconBolt className="h-3 w-3" /> {formatNumber(streak.data?.today_xp)} XP
              </Badge>
            </div>
          </div>
        </Card>

        <Card lift inlay className="p-6 lg:col-span-2">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">Lịch ôn 10 ngày tới</p>
              <p className="font-display mt-1 text-xl font-bold text-ink">
                {formatNumber(review.data?.due_now)} từ đang chờ
              </p>
            </div>
            <Badge tone="jade">Tỉ lệ nhớ {formatPercent(review.data?.retention_percentage, 1)}</Badge>
          </div>
          <div className="mt-4 h-32">
            <Suspense fallback={<Skeleton className="h-full w-full rounded-xl" />}>
              <ForecastChart data={forecast} />
            </Suspense>
          </div>
        </Card>
      </div>

      <div
        className={clsx(
          "mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3",
          WRITING_VISIBLE ? "lg:grid-cols-5" : "lg:grid-cols-4"
        )}
      >
        <StatTile index={0} label="Tổng từ vựng" value={<CountUp value={data.total_vocabulary} />} accent="accent" icon={<IconBook className="h-4 w-4" />} />
        <StatTile index={1} label="Đã thuộc" value={<CountUp value={data.mastered_vocabulary} />} hint={formatPercent(masteredPct, 1) + " tổng số"} accent="jade" />
        <StatTile index={2} label="Đang học" value={<CountUp value={data.learning_vocabulary} />} accent="gold" />
        <StatTile index={3} label="Cần ôn" value={<CountUp value={data.review_vocabulary} />} accent="sky" icon={<IconTarget className="h-4 w-4" />} />
        {/* A writing statistic is only meaningful while the writing page is offered. */}
        {WRITING_VISIBLE && (
          <StatTile index={4} label="Chữ đã luyện viết" value={<CountUp value={data.writing_practiced} />} hint={`${formatNumber(data.writing_mastered)} thành thạo`} accent="violet" />
        )}
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <Card lift inlay className="p-6 lg:col-span-2">
          <h2 className="font-display text-lg font-bold text-ink">Tiến độ theo cấp độ</h2>
          <div className="mt-5 flex flex-col gap-4">
            {data.hsk_levels.map((level) => {
              const pct = level.total ? (level.mastered / level.total) * 100 : 0;
              return (
                <div key={level.level}>
                  <div className="mb-1.5 flex items-center justify-between text-sm">
                    <span className="font-semibold text-ink">{LEVEL_LABEL[level.level]}</span>
                    <span className="tnum text-ink-soft">
                      {formatNumber(level.mastered)}/{formatNumber(level.total)} đã thuộc
                    </span>
                  </div>
                  <ProgressBar value={pct} accent="jade" />
                </div>
              );
            })}
          </div>
        </Card>

        <Card lift inlay className="p-6">
          <h2 className="font-display text-lg font-bold text-ink">Độ chính xác</h2>
          <div className="mt-4 flex flex-col gap-3 text-sm">
            <ResultRow label="Nối từ" correct={data.matching_correct} incorrect={data.matching_incorrect} accuracy={data.matching_accuracy} />
            <ResultRow label="Luyện câu" correct={data.sentence_correct} incorrect={data.sentence_incorrect} accuracy={data.sentence_accuracy} />
            <ResultRow label="Luyện nghe" correct={data.listening_correct} incorrect={data.listening_incorrect} accuracy={data.listening_accuracy} />
            {/* Fed by the mock exam's written half, which runs on the quiz engine. */}
            <ResultRow label="Trắc nghiệm" correct={data.quiz_correct} incorrect={data.quiz_incorrect} accuracy={data.quiz_accuracy} />
          </div>
        </Card>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <Card lift inlay className="p-6">
          <h2 className="font-display text-lg font-bold text-ink">Hoạt động 14 ngày</h2>
          <div className="mt-4 h-40">
            <Suspense fallback={<Skeleton className="h-full w-full rounded-xl" />}>
              <ActivityChart data={activity} />
            </Suspense>
          </div>
        </Card>

        <Card lift inlay className="p-6">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-bold text-ink">Chuỗi ngày học</h2>
            <Badge tone="accent">
              <IconFlame className="h-3 w-3" /> Kỷ lục {formatNumber(streak.data?.longest_streak)}
            </Badge>
          </div>
          <div className="mt-5">
            {streak.data ? (
              <Heatmap days={streak.data.heatmap} weeks={26} />
            ) : (
              <p className="text-sm text-ink-faint">Chưa có dữ liệu hoạt động.</p>
            )}
          </div>
          <p className="mt-3 text-xs text-ink-faint">
            Mỗi ô là một ngày; ô càng đậm nghĩa là bạn ôn càng nhiều.
          </p>
        </Card>
      </div>

      <div className="mt-10">
        <SectionTitle>Bắt đầu luyện tập</SectionTitle>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {FEATURES.map((feature, index) => (
          <Reveal key={feature.to} index={index}>
            <Link to={feature.to} className="block h-full">
              <Card
                lift
                inlay
                className="flex h-full flex-col justify-between p-5"
              >
                {/* The tile's own colour, pooled behind the icon. It is what
                    makes ten tiles read as ten things instead of a grid. */}
                <span
                  aria-hidden="true"
                  className={clsx(
                    "pointer-events-none absolute -left-6 -top-8 -z-10 h-24 w-24 rounded-full opacity-50 blur-2xl transition-opacity duration-500 group-hover:opacity-90",
                    FEATURE_GLOW[feature.accent]
                  )}
                />
                <div>
                  <div
                    className={clsx(
                      "mb-3 inline-flex h-11 w-11 items-center justify-center rounded-xl transition-transform duration-500 group-hover:-rotate-6 group-hover:scale-110",
                      FEATURE_CHIP[feature.accent]
                    )}
                  >
                    <feature.icon className="h-5 w-5" />
                  </div>
                  <p className="font-display font-bold text-ink">{feature.label}</p>
                  <p className="mt-1 text-xs text-ink-soft">{feature.desc}</p>
                </div>
                <div
                  className={clsx(
                    "mt-4 flex items-center gap-1 text-xs font-semibold transition-all duration-300",
                    "translate-y-1 opacity-0 group-hover:translate-y-0 group-hover:opacity-100",
                    FEATURE_TEXT[feature.accent]
                  )}
                >
                  Bắt đầu
                  <IconArrowRight className="h-3.5 w-3.5 transition-transform duration-300 group-hover:translate-x-1" />
                </div>
              </Card>
            </Link>
          </Reveal>
        ))}
      </div>

      {data.recent_vocabulary.length > 0 && (
        <div className="mt-10">
          <SectionTitle>Từ vựng vừa học</SectionTitle>
          <div className="flex flex-wrap gap-2">
            {data.recent_vocabulary.map((item, index) => (
              <Reveal key={item.id} index={index} className="inline-flex">
                <Badge tone="neutral">
                  <span className="hanzi font-semibold text-ink">{item.hanzi}</span>
                  <span className="text-ink-faint">·</span>
                  {item.meaning}
                </Badge>
              </Reveal>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ResultRow({
  label,
  correct,
  incorrect,
  accuracy,
}: {
  label: string;
  correct: number;
  incorrect: number;
  accuracy: number;
}) {
  const total = correct + incorrect;
  return (
    <div className="border-b border-border-soft pb-2.5 last:border-0 last:pb-0">
      <div className="flex items-center justify-between">
        <span className="text-ink-soft">{label}</span>
        <span className="tnum font-semibold text-ink">{total === 0 ? "—" : formatPercent(accuracy)}</span>
      </div>
      {total > 0 && (
        <div className="mt-1.5">
          <ProgressBar value={accuracy} accent={accuracy >= 80 ? "jade" : accuracy >= 50 ? "gold" : "accent"} />
        </div>
      )}
    </div>
  );
}
