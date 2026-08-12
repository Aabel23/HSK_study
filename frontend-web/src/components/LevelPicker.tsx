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
    <div className={clsx("flex flex-wrap gap-1.5", compact && "gap-1")}>
      {ORDER.map((value) => {
        const active = level === value;
        return (
          <button
            key={value}
            onClick={() => setLevel(value)}
            className={clsx(
              "rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors",
              active
                ? "border-accent bg-accent text-accent-ink"
                : "border-border bg-surface text-ink-soft hover:border-accent/50 hover:text-ink"
            )}
          >
            {LEVEL_LABELS[value]}
            {counts[value] ? <span className="ml-1 opacity-70">{counts[value]}</span> : null}
          </button>
        );
      })}
    </div>
  );
}
