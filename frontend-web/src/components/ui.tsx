import { useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import clsx from "clsx";
import { motion } from "framer-motion";
import { usePlayAudio } from "../lib/useAudio";
import { BaoTuongHoa, CardOrnament } from "./Ornament";
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
  ornament,
  lift = false,
  inlay = false,
  ...rest
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section";
  /**
   * Gives the card its texture: 七宝, the interlocking-circle ground.
   *
   * A flag rather than a choice of motif, and that is the whole point. An
   * earlier version let each card pick — hexagons here, circles there, a corner
   * mark elsewhere — and a grid of cards wearing three different patterns reads
   * as clutter no matter how faint each one is. Making it structural means
   * nobody can reintroduce the mix by passing a different string.
   *
   * Use it on the few cards that lead a page — today's goal, the headline
   * figures — and leave the rest plain. Texture on every card is texture on
   * nothing: it stops marking anything out and just makes the page busy.
   */
  ornament?: boolean;
  /** Raises the card towards the pointer on hover. */
  lift?: boolean;
  /** Gold hairline just inside the border, lit on hover. */
  inlay?: boolean;
} & Record<string, unknown>) {
  const decorated = Boolean(ornament) || lift || inlay;
  return (
    <Component
      className={clsx(
        "rounded-2xl border border-border bg-surface shadow-soft",
        // `isolate` is what lets the ornament sit at a negative z-index: it
        // creates a stacking context, so the watermark paints above the card's
        // own background but below its content. Wrapping the children in a
        // positioned div would do the same job and break every Card whose
        // className makes it a flex or grid container.
        decorated && "group relative isolate overflow-hidden",
        inlay && "inlay",
        lift &&
          "transition-[transform,box-shadow,border-color] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-1 hover:border-border-strong hover:shadow-lift",
        className
      )}
      {...rest}
    >
      {ornament && <CardOrnament />}
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
    <div className="animate-rise relative mb-6">
      <div className="relative flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-accent">
            <span className="inline-block h-px w-6 bg-accent/60" />
            {eyebrow}
          </p>
          <h1 className="font-display text-foil mt-2 text-3xl font-bold sm:text-4xl">{title}</h1>
          {description && (
            <p className="mt-2 max-w-2xl text-sm text-ink-soft sm:text-base">{description}</p>
          )}
        </div>
        {/* A page with a button uses its right-hand side; a page without one was
            leaving the whole half empty, which is what made these headers read
            as under-filled. The medallion fills it — and only ever when there is
            no action, so it can never crowd a control. */}
        {action ?? (
          <BaoTuongHoa
            className="pointer-events-none -mb-6 -mt-10 hidden h-40 w-40 shrink-0 text-gold opacity-[0.22] lg:block"
          />
        )}
      </div>
      {/* A hairline, nothing more. A band of lotus petals lived here briefly and
          was wrong: repeated across the full width of every page it stopped
          reading as a divider and became a chain competing with the title.
          A divider's job is to separate two things quietly. */}
      <div className="rule-foil mt-5" />
    </div>
  );
}

/**
 * A number that counts up to its value when it first appears.
 *
 * Only worth it on figures the learner earned — a streak, an XP total, a score.
 * Counting up an unrelated total is noise, so this is opt-in rather than baked
 * into every number in the app.
 *
 * Falls straight to the final value when motion is reduced: an animation that
 * cannot run must still leave the correct number on screen.
 */
export function CountUp({
  value,
  duration = 900,
  decimals = 0,
  suffix,
}: {
  value: number;
  duration?: number;
  decimals?: number;
  suffix?: string;
}) {
  const [shown, setShown] = useState(value);
  const from = useRef(value);

  useEffect(() => {
    const reduced =
      document.documentElement.dataset.reducedMotion === "true" ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced || !Number.isFinite(value)) {
      setShown(value);
      from.current = value;
      return;
    }

    const start = performance.now();
    const origin = from.current;
    let frame = 0;
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / duration);
      // Same easing curve as the layout motion, so numbers and cards settle
      // together instead of finishing at visibly different moments.
      const eased = 1 - Math.pow(1 - progress, 3);
      setShown(origin + (value - origin) * eased);
      if (progress < 1) frame = requestAnimationFrame(tick);
      else from.current = value;
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value, duration]);

  return (
    <span className="tnum">
      {shown.toLocaleString("vi-VN", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}
      {suffix}
    </span>
  );
}

/**
 * Deals its children in one after another as they enter.
 *
 * The stagger is carried by a CSS custom property rather than by JavaScript
 * timers, so it costs nothing at runtime and stops by itself under the
 * reduced-motion rules in `index.css`.
 */
export function Reveal({
  children,
  index = 0,
  className,
  as: Component = "div",
}: {
  children: ReactNode;
  index?: number;
  className?: string;
  as?: "div" | "li" | "section";
}) {
  return (
    <Component
      className={clsx("animate-rise", className)}
      style={{ "--i": index } as React.CSSProperties}
    >
      {children}
    </Component>
  );
}

/**
 * Heading for a block within a page, with a rule that runs out to the margin.
 *
 * Pages had been writing this as a bare `<h2>` with their own classes, which
 * drifted: three different sizes and two different margins across the app.
 */
export function SectionTitle({
  children,
  action,
  className,
}: {
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx("mb-4 flex items-center gap-4", className)}>
      <h2 className="font-display shrink-0 text-lg font-bold text-ink">{children}</h2>
      <span aria-hidden="true" className="rule-foil hidden flex-1 sm:block" />
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

const GLOW_ACCENT: Record<Accent, string> = {
  accent: "bg-accent/20",
  gold: "bg-gold/20",
  jade: "bg-jade/20",
  sky: "bg-sky/20",
  violet: "bg-violet/20",
};

export function StatTile({
  label,
  value,
  hint,
  accent = "accent",
  icon,
  index = 0,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  accent?: Accent;
  icon?: ReactNode;
  /** Position in a row of tiles, so a row deals itself out left to right. */
  index?: number;
}) {
  return (
    <Reveal index={index}>
      <Card ornament lift inlay className="h-full p-5">
        {/* A pool of the tile's own colour, so a row of tiles reads as five
            different things at a glance rather than five identical boxes. */}
        <div
          aria-hidden="true"
          className={clsx(
            "pointer-events-none absolute -left-8 -top-10 -z-10 h-28 w-28 rounded-full blur-2xl transition-opacity duration-500 group-hover:opacity-100",
            GLOW_ACCENT[accent],
            "opacity-60"
          )}
        />
        <div className="flex items-start justify-between gap-2">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-faint">{label}</p>
          {icon && (
            <span
              className={clsx(
                "shrink-0 transition-transform duration-300 group-hover:-rotate-6 group-hover:scale-110",
                TEXT_ACCENT[accent]
              )}
            >
              {icon}
            </span>
          )}
        </div>
        <p className={clsx("font-display tnum mt-2 text-3xl font-bold", TEXT_ACCENT[accent])}>
          {value}
        </p>
        {hint && <p className="mt-1 text-xs text-ink-soft">{hint}</p>}
      </Card>
    </Reveal>
  );
}

export function ProgressBar({ value, accent = "accent" }: { value: number; accent?: Accent }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div
      className="relative h-2 w-full overflow-hidden rounded-full bg-surface-2"
      role="progressbar"
      aria-valuenow={Math.round(clamped)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <motion.div
        className={clsx("relative h-full rounded-full", BG_ACCENT[accent])}
        initial={{ width: 0 }}
        animate={{ width: `${clamped}%` }}
        // Deliberately not the springy curve: a bar that overshoots reads as
        // "you are further along than you are", then takes it back.
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      >
        {/* A brighter cap at the leading edge, so the bar has a head to it. */}
        <span
          aria-hidden="true"
          className="absolute inset-y-0 right-0 w-6 rounded-full bg-gradient-to-l from-white/45 to-transparent"
        />
      </motion.div>
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
    primary:
      "bg-gradient-to-br from-accent-hover to-accent text-accent-ink shadow-soft hover:shadow-lift hover:brightness-[1.06]",
    secondary:
      "bg-surface-2 text-ink border border-border hover:border-gold/45 hover:bg-surface-3",
    ghost: "text-ink-soft hover:text-ink hover:bg-surface-2",
    danger: "bg-gradient-to-br from-danger to-danger text-white hover:brightness-110",
  }[variant];
  const sizeClass = { sm: "px-3 py-1.5 text-xs", md: "px-4 py-2.5 text-sm", lg: "px-6 py-3 text-base" }[size];
  // The light sweep would read as a glitch on a button that is only ever a bit
  // of text, so it is kept to the two filled variants.
  const sweeps = variant === "primary" || variant === "danger";
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        "relative inline-flex items-center justify-center gap-2 overflow-hidden rounded-xl font-semibold transition-all duration-200 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none",
        variantClass,
        sizeClass,
        className
      )}
      {...rest}
    >
      {sweeps && !disabled && <span className="sweep" aria-hidden="true" />}
      <span className="relative inline-flex items-center gap-2">{children}</span>
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

/** Compact on/off switch for a single option inside an exercise toolbar.
 *
 * `Switch` above is a full settings row with its own label column; this one is
 * meant to sit in a corner of a running session, where the only thing there is
 * room for is the word and the toggle.
 */
export function InlineSwitch({
  checked,
  onChange,
  label,
  title,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
  title?: string;
}) {
  return (
    <label
      title={title}
      className="inline-flex cursor-pointer select-none items-center gap-2 rounded-full border border-border bg-surface px-2.5 py-1"
    >
      <span className={clsx("text-xs font-semibold", checked ? "text-accent" : "text-ink-faint")}>
        {label}
      </span>
      <span className="relative inline-block">
        <input
          type="checkbox"
          role="switch"
          checked={checked}
          onChange={(event) => onChange(event.target.checked)}
          className="peer sr-only"
        />
        <span
          aria-hidden="true"
          className={clsx(
            "block h-4 w-7 rounded-full transition-colors duration-200 peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent",
            checked ? "bg-accent" : "bg-surface-3"
          )}
        />
        <span
          aria-hidden="true"
          className={clsx(
            "pointer-events-none absolute left-0.5 top-0.5 h-3 w-3 rounded-full bg-white shadow transition-transform duration-200",
            checked && "translate-x-3"
          )}
        />
      </span>
    </label>
  );
}

/** Choose how many items a practice session holds.
 *
 * Presets cover the common cases in one tap, and the number field is there for
 * the exact figure someone has in mind ("I want to do 100 in a row"). Both are
 * clamped to `max`, because promising more items than the filtered pool holds
 * would only produce a session that ends early without explanation.
 */
export function SessionSizePicker({
  value,
  onChange,
  max,
  unit,
  presets = [10, 20, 50, 100],
  label = "Số lượng mỗi phiên",
}: {
  value: number;
  onChange: (next: number) => void;
  max: number;
  unit: string;
  presets?: number[];
  label?: string;
}) {
  const ceiling = Math.max(1, max);
  const clamp = (next: number) => Math.min(ceiling, Math.max(1, Math.round(next || 1)));
  const options = [...new Set(presets.filter((preset) => preset < ceiling)), ceiling];

  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor="session-size" className="text-sm font-semibold text-ink">
          {label}
        </label>
        <span className="text-xs text-ink-faint">tối đa {ceiling.toLocaleString("vi-VN")}</span>
      </div>

      <div role="group" aria-label={label} className="mt-3 flex flex-wrap gap-2">
        {options.map((option) => (
          <button
            key={option}
            type="button"
            aria-pressed={value === option}
            onClick={() => onChange(option)}
            className={clsx(
              "tnum rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors duration-200",
              value === option
                ? "border-accent bg-accent-soft text-accent"
                : "border-border text-ink-soft hover:border-border-strong hover:text-ink"
            )}
          >
            {option === ceiling && !presets.includes(option) ? `Tất cả (${option})` : option}
          </button>
        ))}
      </div>

      <div className="mt-3 flex items-center gap-2">
        <input
          id="session-size"
          type="number"
          inputMode="numeric"
          min={1}
          max={ceiling}
          value={value}
          onChange={(event) => onChange(clamp(Number(event.target.value)))}
          className="tnum w-24 rounded-xl border border-border bg-surface px-3 py-2 text-sm font-semibold text-ink outline-none focus:border-accent"
        />
        <span className="text-sm text-ink-soft">{unit}</span>
      </div>
    </div>
  );
}

/**
 * The screen a learner sees when they finish a session.
 *
 * Every drill had written its own: a bold line, a fraction, and a button on a
 * bare background. That is the least ceremonious moment in the app attached to
 * the most earned one, and it made finishing feel like nothing had happened.
 *
 * So this is where 海水江崖 — standing water over cliffs, the hem of a court
 * robe, the most formal motif in the set — finally gets used. It appears on
 * this screen and nowhere else, which is exactly why it still means something
 * when it does.
 */
export function SessionComplete({
  title = "Hoàn thành!",
  correct,
  total,
  unit,
  detail,
  primary,
  secondary,
}: {
  title?: string;
  correct: number;
  total: number;
  /** "thẻ", "câu", "từ" — what was counted. */
  unit: string;
  /** An extra line under the score, when the drill has more to report. */
  detail?: ReactNode;
  primary: ReactNode;
  secondary?: ReactNode;
}) {
  const percentage = total > 0 ? Math.round((correct / total) * 100) : 0;
  // The band of colour is the honest signal here; the words stay warm either
  // way, because a session that went badly is still a session that happened.
  const tone: Accent = percentage >= 80 ? "jade" : percentage >= 50 ? "gold" : "accent";

  return (
    <div className="animate-float-in mx-auto max-w-lg">
      <Card className="relative isolate overflow-hidden px-6 pb-10 pt-10 text-center">
        <div
          aria-hidden="true"
          className={clsx(
            "pointer-events-none absolute -top-24 left-1/2 h-64 w-64 -translate-x-1/2 rounded-full blur-[80px]",
            GLOW_ACCENT[tone]
          )}
        />
        {/* Sized to own the bottom-right quarter of the card, and flush into the
            corner rather than floating near it — at 10rem it read as a small
            sticker dropped on the card instead of as part of it.
            Still placed whole: a 宝相花 is radially symmetric, so a cropped one
            reads as damage. Filling the corner and being cut by it are two
            different things. */}
        <BaoTuongHoa className="pointer-events-none absolute bottom-0 right-0 -z-10 h-1/2 w-1/2 text-gold opacity-[0.16]" />

        <div className="animate-bloom-in relative inline-flex">
          <ProgressRing value={percentage} accent={tone} size={148} stroke={10}>
            <span className={clsx("font-display text-4xl font-bold", TEXT_ACCENT[tone])}>
              <CountUp value={percentage} suffix="%" />
            </span>
            <span className="text-[11px] text-ink-faint">
              {correct}/{total} {unit}
            </span>
          </ProgressRing>
        </div>

        <h2 className="font-display text-foil relative mt-5 text-3xl font-bold">{title}</h2>
        {detail && <div className="relative mt-2 text-sm text-ink-soft">{detail}</div>}

        <div className="relative mt-6 flex flex-wrap items-center justify-center gap-3">
          {primary}
          {secondary}
        </div>
      </Card>
    </div>
  );
}

/**
 * The bar that sits above every running exercise.
 *
 * Counter on the left, toggles on the right, same place on every screen. It
 * exists because the Pinyin switch had drifted: on one page it sat beside an
 * HSK badge, on another it was paired with a second toggle, and on a third it
 * was somewhere else entirely — so a learner who turned pinyin off had to go
 * looking for the switch again on the next exercise. A control that means the
 * same thing everywhere should be in the same place everywhere.
 */
export function PracticeBar({
  position,
  total,
  unit = "Câu",
  badge,
  children,
}: {
  position: number;
  total: number;
  /** "Câu", "Thẻ", "Từ" — whatever this drill counts. */
  unit?: string;
  badge?: ReactNode;
  /** The toggles, right-aligned. */
  children?: ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
      <span className="tnum text-sm text-ink-soft">
        {unit} {position}/{total}
      </span>
      <div className="flex flex-wrap items-center gap-2">
        {badge}
        {children}
      </div>
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
    // Lock the page behind the dialog without letting the layout jump sideways
    // when the scrollbar disappears.
    const previousOverflow = document.body.style.overflow;
    const previousPadding = document.body.style.paddingRight;
    const scrollbar = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.overflow = "hidden";
    if (scrollbar > 0) document.body.style.paddingRight = `${scrollbar}px`;
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
      document.body.style.paddingRight = previousPadding;
    };
  }, [open, onClose]);

  if (!open) return null;
  return createPortal(
    // Two nested elements on purpose. Centring the dialog with `items-center`
    // directly on the scrolling element is the classic flexbox trap: once the
    // dialog is taller than the viewport its top overflows *above* the scroll
    // range and can never be reached. Scrolling on the outer element and
    // centring inside a `min-h-full` wrapper centres short dialogs and scrolls
    // tall ones from the top.
    <div className="fixed inset-0 z-[70] overflow-y-auto overscroll-contain">
      <button
        className="fixed inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-label="Đóng hộp thoại"
        tabIndex={-1}
      />
      {/* `index.html` opts into `viewport-fit=cover`, so on a notched phone the
          bottom of the viewport sits under the home indicator and the footer
          button goes with it. The safe-area inset is the floor for the bottom
          padding; on every other device `max()` just picks the 1rem. */}
      <div
        className="flex min-h-full items-center justify-center p-4"
        style={{
          paddingBottom: "max(1rem, env(safe-area-inset-bottom))",
          paddingTop: "max(1rem, env(safe-area-inset-top))",
        }}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-label={title}
          className="animate-pop-in relative z-10 flex w-full max-w-lg flex-col rounded-2xl border border-border bg-surface shadow-pop"
        >
          <div className="flex shrink-0 items-center justify-between border-b border-border-soft px-5 py-4">
            <h2 className="font-display text-base font-bold text-ink">{title}</h2>
            <button
              onClick={onClose}
              aria-label="Đóng"
              className="rounded-lg p-1.5 text-ink-faint transition-colors hover:bg-surface-2 hover:text-ink"
            >
              <IconX className="h-4 w-4" />
            </button>
          </div>
          <div className="px-5 py-4">{children}</div>
          {footer && (
            <div className="flex shrink-0 justify-end gap-2 border-t border-border-soft px-5 py-3.5">
              {footer}
            </div>
          )}
        </div>
      </div>
    </div>,
    // Rendered into <body>, and this is not a stylistic choice.
    //
    // `position: fixed` resolves against the viewport only while no ancestor
    // has a transform — and every page in this app is wrapped in
    // `.animate-float-in`, whose `animation-fill-mode: both` leaves
    // `transform: translateY(0)` on the element permanently. Any transform
    // other than `none` makes that element the containing block for fixed
    // descendants, so the dialog was being positioned against the *page*
    // rather than the screen. On a laptop the page is about viewport-sized and
    // it looked correct; on a phone the page is several screens tall, so the
    // dialog was centred somewhere far below the fold with no way to scroll to
    // it. A portal puts the dialog outside every one of those wrappers.
    document.body
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
