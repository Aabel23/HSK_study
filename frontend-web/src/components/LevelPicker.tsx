import { useEffect, useState } from "react";
import clsx from "clsx";
import { api } from "../lib/api";
import { useLevel, LEVEL_LABELS } from "../lib/levelContext";
import type { HskLevel } from "../lib/types";

const ORDER: Array<HskLevel | "all"> = ["all", "1", "2", "3", "4", "5", "6", "7-9"];

export function LevelPicker({ compact = false }: { compact?: boolean }) {
  const { level, setLevel } = useLevel();
  const [counts, setCounts] = useState<Record<string, number>>({});

  useEffect(() => {
    api.vocabulary.levels().then((res) => {
      const map: Record<string, number> = {};
      let total = 0;
      for (const item of res.items) {
        map[item.level] = item.total;
        total += item.total;
      }
      map.all = total;
      setCounts(map);
    });
  }, []);

  return (
    // A two-column grid rather than a wrapping row. The labels are all about the
    // same width, so wrapping produced ragged rows that changed shape whenever a
    // count went from three digits to four; a grid keeps the block steady.
    <div className={clsx("grid grid-cols-2 gap-1.5", compact && "gap-1")}>
      {ORDER.map((value) => {
        const active = level === value;
        return (
          <button
            key={value}
            onClick={() => setLevel(value)}
            aria-pressed={active}
            className={clsx(
              "flex items-baseline justify-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition-all duration-200",
              active
                ? "border-accent bg-accent text-accent-ink shadow-soft"
                : "border-border bg-surface text-ink-soft hover:border-accent/50 hover:text-ink"
            )}
          >
            <span>{LEVEL_LABELS[value]}</span>
            {counts[value] ? (
              // Set in the gold, and lighter than the label: the count is
              // context, not the thing being chosen.
              <span
                className={clsx(
                  "tnum text-[10px] font-medium",
                  active ? "text-accent-ink/75" : "text-gold/80"
                )}
              >
                {counts[value].toLocaleString("vi-VN")}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
