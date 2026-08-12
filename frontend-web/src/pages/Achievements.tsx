import { useMemo } from "react";
import { motion } from "framer-motion";
import clsx from "clsx";
import { api } from "../lib/api";
import { useApi } from "../lib/useApi";
import { formatNumber, formatDate } from "../lib/format";
import type { AchievementItem } from "../lib/types";
import {
  Badge,
  Card,
  ErrorState,
  PageHeader,
  PageSkeleton,
  ProgressBar,
  ProgressRing,
  StatTile,
} from "../components/ui";
import {
  IconBolt,
  IconBookmark,
  IconCheck,
  IconFlame,
  IconHeadphones,
  IconLayers,
  IconPencil,
  IconSpark,
  IconStar,
  IconTarget,
  IconTrophy,
} from "../components/icons";

const TIER_STYLE: Record<AchievementItem["tier"], { ring: string; chip: string; label: string }> = {
  bronze: { ring: "border-gold/25", chip: "bg-gold-soft text-gold", label: "Đồng" },
  silver: { ring: "border-sky/25", chip: "bg-sky-soft text-sky", label: "Bạc" },
  gold: { ring: "border-gold/50", chip: "bg-gold-soft text-gold", label: "Vàng" },
  diamond: { ring: "border-violet/50", chip: "bg-violet-soft text-violet", label: "Kim cương" },
};

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  spark: IconSpark,
  layers: IconLayers,
  flame: IconFlame,
  check: IconCheck,
  pencil: IconPencil,
  headphones: IconHeadphones,
  target: IconTarget,
  star: IconStar,
  bookmark: IconBookmark,
};

export default function Achievements() {
  const achievements = useApi(() => api.achievements(), []);
  const streak = useApi(() => api.streak(30), []);

  const { unlocked, locked, completion } = useMemo(() => {
    const items = achievements.data?.items ?? [];
    return {
      unlocked: items.filter((item) => item.unlocked),
      locked: items.filter((item) => !item.unlocked),
      completion: items.length
        ? (items.filter((item) => item.unlocked).length / items.length) * 100
        : 0,
    };
  }, [achievements.data]);

  if (achievements.loading && !achievements.data) return <PageSkeleton tiles={4} rows={2} />;
  if (achievements.error) return <ErrorState message={achievements.error} onRetry={achievements.reload} />;

  return (
    <div className="animate-float-in">
      <PageHeader
        eyebrow="Động lực"
        title="Thành tích"
        description="Mỗi cột mốc là một bằng chứng cho thói quen học đều đặn của bạn."
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="flex flex-col items-center justify-center gap-3 p-6 lg:col-span-1">
          <ProgressRing value={completion} accent="gold" size={148}>
            <span className="font-display tnum text-3xl font-bold text-gold">
              {achievements.data?.unlocked_count ?? 0}
            </span>
            <span className="text-xs text-ink-faint">/ {achievements.data?.total_count ?? 0} huy hiệu</span>
          </ProgressRing>
          <p className="text-center text-sm text-ink-soft">
            Đã mở khoá {Math.round(completion)}% tổng số thành tích.
          </p>
        </Card>

        <div className="grid grid-cols-2 gap-4 lg:col-span-2">
          <StatTile
            label="Chuỗi hiện tại"
            value={formatNumber(streak.data?.current_streak)}
            hint={`Kỷ lục ${formatNumber(streak.data?.longest_streak)} ngày`}
            accent="accent"
            icon={<IconFlame className="h-4 w-4" />}
          />
          <StatTile
            label="Cấp độ"
            value={formatNumber(streak.data?.level)}
            hint={`${formatNumber(streak.data?.xp_into_level)}/${formatNumber(streak.data?.xp_per_level)} XP`}
            accent="gold"
            icon={<IconBolt className="h-4 w-4" />}
          />
          <StatTile
            label="Tổng kinh nghiệm"
            value={formatNumber(streak.data?.total_xp)}
            accent="violet"
          />
          <StatTile
            label="Ngày đã học"
            value={formatNumber(streak.data?.active_days)}
            accent="jade"
          />
        </div>
      </div>

      {unlocked.length > 0 && (
        <section className="mt-10">
          <h2 className="font-display mb-4 flex items-center gap-2 text-lg font-bold text-ink">
            <IconTrophy className="h-5 w-5 text-gold" /> Đã mở khoá
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {unlocked.map((item, position) => (
              <AchievementCard key={item.code} item={item} position={position} />
            ))}
          </div>
        </section>
      )}

      <section className="mt-10">
        <h2 className="font-display mb-4 text-lg font-bold text-ink">Đang chinh phục</h2>
        {locked.length === 0 ? (
          <Card className="px-6 py-10 text-center">
            <p className="font-display text-lg font-semibold text-ink">Bạn đã mở khoá tất cả thành tích.</p>
            <p className="mt-1 text-sm text-ink-soft">Thật đáng nể — hãy tiếp tục giữ chuỗi ngày học.</p>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {locked.map((item, position) => (
              <AchievementCard key={item.code} item={item} position={position} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function AchievementCard({ item, position }: { item: AchievementItem; position: number }) {
  const Icon = ICONS[item.icon] ?? IconTrophy;
  const tier = TIER_STYLE[item.tier];
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(position * 0.03, 0.3) }}
    >
      <Card className={clsx("flex h-full flex-col p-5", item.unlocked ? tier.ring : "opacity-75")}>
        <div className="flex items-start justify-between gap-3">
          <span
            className={clsx(
              "inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl",
              item.unlocked ? tier.chip : "bg-surface-2 text-ink-faint"
            )}
          >
            <Icon className="h-5 w-5" />
          </span>
          <Badge tone={item.unlocked ? "gold" : "neutral"}>{tier.label}</Badge>
        </div>

        <p className="font-display mt-3 font-bold text-ink">{item.title}</p>
        <p className="mt-1 flex-1 text-xs leading-relaxed text-ink-soft">{item.description}</p>

        <div className="mt-4">
          <ProgressBar value={item.percentage} accent={item.unlocked ? "gold" : "sky"} />
          <div className="mt-1.5 flex items-center justify-between text-[11px]">
            <span className="tnum text-ink-faint">
              {formatNumber(item.progress)} / {formatNumber(item.target)}
            </span>
            {item.unlocked && item.unlocked_at && (
              <span className="text-gold">{formatDate(item.unlocked_at)}</span>
            )}
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
