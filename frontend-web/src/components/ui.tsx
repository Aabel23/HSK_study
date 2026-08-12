import { useEffect, type ReactNode } from "react";
import clsx from "clsx";
import { motion } from "framer-motion";
import { usePlayAudio } from "../lib/useAudio";
import {
  IconAlert,
  IconBookmark,
  IconBookmarkFilled,
  IconPause,
  IconRefresh,
  IconVolume,
  IconX,
} from "./icons";

export function Card({
  children,
  className,
  as: Component = "div",
  ...rest
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section";
} & Record<string, unknown>) {
  return (
    <Component
      className={clsx(
        "rounded-2xl border border-border bg-surface shadow-soft",
        className
      )}
      {...rest}
    >
      {children}
    </Component>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">{eyebrow}</p>
        <h1 className="font-display mt-1 text-3xl font-bold text-ink sm:text-4xl">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-sm text-ink-soft sm:text-base">{description}</p>}
      </div>
      {action}
    </div>
  );
}

type Accent = "accent" | "gold" | "jade" | "sky" | "violet";

const TEXT_ACCENT: Record<Accent, string> = {
  accent: "text-accent",
  gold: "text-gold",
  jade: "text-jade",
  sky: "text-sky",
  violet: "text-violet",
};

const BG_ACCENT: Record<Accent, string> = {
  accent: "bg-accent",
  gold: "bg-gold",
  jade: "bg-jade",
  sky: "bg-sky",
  violet: "bg-violet",
};

const BADGE_TONE: Record<Accent | "danger", string> = {
  accent: "bg-accent-soft text-accent border-transparent",
  gold: "bg-gold-soft text-gold border-transparent",
  jade: "bg-jade-soft text-jade border-transparent",
  sky: "bg-sky-soft text-sky border-transparent",
  violet: "bg-violet-soft text-violet border-transparent",
  danger: "bg-danger-soft text-danger border-transparent",
};

export function StatTile({
  label,
  value,
  hint,
  accent = "accent",
  icon,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  accent?: Accent;
  icon?: ReactNode;
}) {
  return (
    <Card className="p-5 transition-colors duration-200 hover:border-border-strong">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-faint">{label}</p>
        {icon && <span className={clsx("shrink-0", TEXT_ACCENT[accent])}>{icon}</span>}
      </div>
      <p className={clsx("font-display tnum mt-2 text-3xl font-bold", TEXT_ACCENT[accent])}>{value}</p>
      {hint && <p className="mt-1 text-xs text-ink-soft">{hint}</p>}
    </Card>
  );
}

export function ProgressBar({ value, accent = "accent" }: { value: number; accent?: Accent }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div
      className="h-2 w-full overflow-hidden rounded-full bg-surface-2"
      role="progressbar"
      aria-valuenow={Math.round(clamped)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <motion.div
        className={clsx("h-full rounded-full", BG_ACCENT[accent])}
        initial={{ width: 0 }}
        animate={{ width: `${clamped}%` }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      />
    </div>
  );
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | Accent | "danger" }) {
  const toneClass = tone === "neutral" ? "bg-surface-2 text-ink-soft border-border" : BADGE_TONE[tone];
  return (
    <span className={clsx("inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold", toneClass)}>
      {children}
    </span>
  );
}

export function Button({
  children,
  onClick,
  variant = "primary",
  size = "md",
  className,
  disabled,
  type = "button",
  ...rest
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  className?: string;
  disabled?: boolean;
  type?: "button" | "submit";
} & Record<string, unknown>) {
  const variantClass = {
    primary: "bg-accent text-accent-ink hover:bg-accent-hover shadow-soft",
    secondary: "bg-surface-2 text-ink border border-border hover:border-border-strong",
    ghost: "text-ink-soft hover:text-ink hover:bg-surface-2",
    danger: "bg-danger text-white hover:brightness-110",
  }[variant];
  const sizeClass = { sm: "px-3 py-1.5 text-xs", md: "px-4 py-2.5 text-sm", lg: "px-6 py-3 text-base" }[size];
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-all duration-200 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50",
        variantClass,
        sizeClass,
        className
      )}
      {...rest}
    >
      {children}
    </button>
  );
}

export function AudioButton({
  text,
  size = "md",
  className,
}: {
  text: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const { play, playingText } = usePlayAudio();
  const isPlaying = playingText === text;
  const dims = { sm: "h-8 w-8", md: "h-10 w-10", lg: "h-12 w-12" }[size];
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        play(text);
      }}
      aria-label={`Phát âm ${text}`}
      className={clsx(
        "inline-flex shrink-0 items-center justify-center rounded-full border border-border bg-surface-2 text-accent transition-colors duration-200 hover:bg-accent-soft",
        isPlaying && "bg-accent-soft",
        dims,
        className
      )}
    >
      {isPlaying ? <IconPause className="h-4 w-4" /> : <IconVolume className="h-4 w-4" />}
    </button>
  );
}

export function LoadingState({ label = "Đang tải..." }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24 text-ink-soft" aria-busy="true">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-border border-t-accent" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <Card className="flex flex-col items-center justify-center gap-2 px-6 py-16 text-center">
      <p className="font-display text-lg font-semibold text-ink">{title}</p>
      {description && <p className="max-w-sm text-sm text-ink-soft">{description}</p>}
      {action && <div className="mt-3">{action}</div>}
    </Card>
  );
}

/* --------------------------------------------------------------------------
   Primitives added for the review flow, dashboard and settings pages.
-------------------------------------------------------------------------- */

/** Grey placeholder block. Preferred over a spinner: it keeps layout stable. */
export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("skeleton", className)} aria-hidden="true" />;
}

/** Loading placeholder shaped like the page it stands in for. */
export function PageSkeleton({ tiles = 5, rows = 2 }: { tiles?: number; rows?: number }) {
  return (
    <div className="animate-float-in" aria-busy="true" aria-label="Đang tải nội dung">
      <Skeleton className="h-3.5 w-28" />
      <Skeleton className="mt-3 h-9 w-72 max-w-full" />
      <Skeleton className="mt-3 h-4 w-full max-w-xl" />
      <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {Array.from({ length: tiles }).map((_, index) => (
          <Skeleton key={index} className="h-[104px] rounded-2xl" />
        ))}
      </div>
      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        {Array.from({ length: rows }).map((_, index) => (
          <Skeleton key={index} className={clsx("h-64 rounded-2xl", index === 0 && "lg:col-span-2")} />
        ))}
      </div>
    </div>
  );
}

/** Inline failure state with a retry affordance, paired with `useApi`. */
export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Card className="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
      <span className="inline-flex h-11 w-11 items-center justify-center rounded-full bg-danger-soft text-danger">
        <IconAlert className="h-5 w-5" />
      </span>
      <p className="font-display text-lg font-semibold text-ink">Không tải được dữ liệu</p>
      <p className="max-w-sm text-sm text-ink-soft">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          <IconRefresh className="h-4 w-4" /> Thử lại
        </Button>
      )}
    </Card>
  );
}

/** Circular progress ring; `size` and `stroke` are in pixels. */
export function ProgressRing({
  value,
  size = 120,
  stroke = 10,
  accent = "accent",
  children,
}: {
  value: number;
  size?: number;
  stroke?: number;
  accent?: Accent;
  children?: ReactNode;
}) {
  const clamped = Math.max(0, Math.min(100, value));
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const dash = (clamped / 100) * circumference;
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90" role="img" aria-label={`${Math.round(clamped)}%`}>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--color-surface-2)" strokeWidth={stroke} />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`var(--color-${accent})`}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - dash }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">{children}</div>
    </div>
  );
}

/** Accessible on/off control backed by a real checkbox input. */
export function Switch({
  checked,
  onChange,
  label,
  description,
  disabled,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
  description?: string;
  disabled?: boolean;
}) {
  return (
    <label className="flex items-start justify-between gap-4 py-3">
      <span className="min-w-0">
        <span className="block text-sm font-medium text-ink">{label}</span>
        {description && <span className="mt-0.5 block text-xs text-ink-soft">{description}</span>}
      </span>
      <span className="relative mt-0.5 shrink-0">
        <input
          type="checkbox"
          role="switch"
          checked={checked}
          disabled={disabled}
          onChange={(event) => onChange(event.target.checked)}
          className="peer sr-only"
        />
        <span
          aria-hidden="true"
          className={clsx(
            "block h-6 w-11 rounded-full transition-colors duration-200 peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent",
            checked ? "bg-accent" : "bg-surface-3",
            disabled && "opacity-50"
          )}
        />
        <span
          aria-hidden="true"
          className={clsx(
            "pointer-events-none absolute top-1 left-1 h-4 w-4 rounded-full bg-white shadow transition-transform duration-200",
            checked && "translate-x-5"
          )}
        />
      </span>
    </label>
  );
}

/** Single-choice control rendered as a radio group. */
export function Segmented<T extends string>({
  value,
  onChange,
  options,
  label,
}: {
  value: T;
  onChange: (next: T) => void;
  options: Array<{ value: T; label: string }>;
  label?: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex flex-wrap gap-1 rounded-xl bg-surface-2 p-1">
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            role="radio"
            aria-checked={active}
            onClick={() => onChange(option.value)}
            className={clsx(
              "rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors duration-200",
              active ? "bg-accent text-accent-ink shadow-soft" : "text-ink-soft hover:text-ink"
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

/** Labelled range slider used by the goal settings. */
export function SliderField({
  label,
  value,
  min,
  max,
  step = 1,
  suffix,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  suffix?: string;
  onChange: (next: number) => void;
}) {
  return (
    <div className="py-3">
      <div className="flex items-baseline justify-between">
        <label className="text-sm font-medium text-ink">{label}</label>
        <span className="tnum font-display text-lg font-bold text-accent">
          {value}
          {suffix && <span className="ml-1 text-xs font-medium text-ink-soft">{suffix}</span>}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        aria-label={label}
        className="mt-2 h-1.5 w-full appearance-none rounded-full bg-surface-3 accent-[var(--color-accent)]"
      />
    </div>
  );
}

/** Keyboard hint chip. */
export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="rounded border border-border bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-ink-soft">
      {children}
    </kbd>
  );
}

/** Contribution-grid view of daily study activity. */
export function Heatmap({
  days,
  weeks = 26,
}: {
  days: Array<{ date: string; count: number }>;
  weeks?: number;
}) {
  const recent = days.slice(-weeks * 7);
  const max = Math.max(1, ...recent.map((day) => day.count));
  const shades = ["bg-surface-2", "bg-jade/25", "bg-jade/45", "bg-jade/70", "bg-jade"];
  const level = (count: number) => {
    if (count === 0) return 0;
    const ratio = count / max;
    if (ratio > 0.66) return 4;
    if (ratio > 0.4) return 3;
    if (ratio > 0.15) return 2;
    return 1;
  };
  return (
    <div className="overflow-x-auto">
      <div className="grid grid-flow-col grid-rows-7 gap-[3px]" style={{ minWidth: weeks * 15 }}>
        {recent.map((day) => (
          <div
            key={day.date}
            title={`${day.date}: ${day.count} lượt ôn`}
            className={clsx("h-3 w-3 rounded-[3px]", shades[level(day.count)])}
          />
        ))}
      </div>
    </div>
  );
}

/** Dialog closed by Escape or a backdrop click. */
export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4">
      <button
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-label="Đóng hộp thoại"
        tabIndex={-1}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="animate-pop-in relative z-10 w-full max-w-lg rounded-2xl border border-border bg-surface shadow-pop"
      >
        <div className="flex items-center justify-between border-b border-border-soft px-5 py-4">
          <h2 className="font-display text-base font-bold text-ink">{title}</h2>
          <button
            onClick={onClose}
            aria-label="Đóng"
            className="rounded-lg p-1.5 text-ink-faint transition-colors hover:bg-surface-2 hover:text-ink"
          >
            <IconX className="h-4 w-4" />
          </button>
        </div>
        <div className="max-h-[60vh] overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t border-border-soft px-5 py-3.5">{footer}</div>}
      </div>
    </div>
  );
}

/** Bookmark toggle shared by the vocabulary list and the review card. */
export function FavoriteButton({
  active,
  onToggle,
  className,
}: {
  active: boolean;
  onToggle: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        onToggle();
      }}
      aria-pressed={active}
      aria-label={active ? "Bỏ đánh dấu từ này" : "Đánh dấu từ này"}
      className={clsx(
        "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border transition-colors duration-200",
        active ? "border-gold/50 bg-gold-soft text-gold" : "border-border bg-surface-2 text-ink-faint hover:text-gold",
        className
      )}
    >
      {active ? <IconBookmarkFilled className="h-4 w-4" /> : <IconBookmark className="h-4 w-4" />}
    </button>
  );
}
