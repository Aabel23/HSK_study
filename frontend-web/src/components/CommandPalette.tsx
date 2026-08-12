import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import clsx from "clsx";
import { api } from "../lib/api";
import { useLevel, LEVEL_LABELS } from "../lib/levelContext";
import { useSettings } from "../lib/settings";
import type { VocabularyItem } from "../lib/types";
import { Kbd } from "./ui";
import { IconArrowRight, IconSearch, IconVolume } from "./icons";
import { VISIBLE_NAV_ITEMS } from "./navigation";

interface Command {
  id: string;
  label: string;
  hint?: string;
  group: string;
  run: () => void;
}

const SEARCH_DEBOUNCE_MS = 180;

/**
 * Ctrl/Cmd+K launcher: jumps between pages, switches HSK level and theme, and
 * searches the whole dictionary without leaving the current screen.
 */
export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate();
  const { setLevel } = useLevel();
  const { settings, update } = useSettings();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<VocabularyItem[]>([]);
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      setQuery("");
      setResults([]);
      setActive(0);
      // Defer so the input exists before focus is moved to it.
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  // Dictionary lookup is debounced so typing does not fire a request per keystroke.
  useEffect(() => {
    const term = query.trim();
    if (term.length < 1) {
      setResults([]);
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      api.vocabulary
        .list({ search: term, limit: 6 })
        .then((response) => {
          if (!cancelled) setResults(response.items);
        })
        .catch(() => {
          if (!cancelled) setResults([]);
        });
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query]);

  const go = useCallback(
    (to: string) => {
      navigate(to);
      onClose();
    },
    [navigate, onClose]
  );

  const commands = useMemo<Command[]>(() => {
    const navigation: Command[] = VISIBLE_NAV_ITEMS.map((item) => ({
      id: `nav:${item.to}`,
      label: item.label,
      hint: item.description,
      group: "Điều hướng",
      run: () => go(item.to),
    }));

    const levels: Command[] = (["all", "1", "2", "3", "4", "5", "6", "7-9"] as const).map((value) => ({
      id: `level:${value}`,
      label: `Chuyển sang ${LEVEL_LABELS[value]}`,
      group: "Cấp độ",
      run: () => {
        setLevel(value);
        onClose();
      },
    }));

    const actions: Command[] = [
      {
        id: "action:theme",
        label: settings.theme === "dark" ? "Chuyển giao diện sáng" : "Chuyển giao diện tối",
        group: "Hành động",
        run: () => {
          update({ theme: settings.theme === "dark" ? "light" : "dark" });
          onClose();
        },
      },
      {
        id: "action:motion",
        label: settings.reduced_motion ? "Bật hiệu ứng chuyển động" : "Giảm hiệu ứng chuyển động",
        group: "Hành động",
        run: () => {
          update({ reduced_motion: !settings.reduced_motion });
          onClose();
        },
      },
    ];

    return [...navigation, ...levels, ...actions];
  }, [go, onClose, setLevel, settings.theme, settings.reduced_motion, update]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return commands.slice(0, 9);
    return commands.filter((command) => command.label.toLowerCase().includes(term)).slice(0, 8);
  }, [commands, query]);

  const total = filtered.length + results.length;

  useEffect(() => {
    setActive((current) => (current >= total ? 0 : current));
  }, [total]);

  const runAt = useCallback(
    (index: number) => {
      if (index < filtered.length) {
        filtered[index]?.run();
        return;
      }
      const word = results[index - filtered.length];
      if (word) go(`/vocabulary?focus=${word.id}`);
    },
    [filtered, results, go]
  );

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        setActive((current) => (total ? (current + 1) % total : 0));
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        setActive((current) => (total ? (current - 1 + total) % total : 0));
      } else if (event.key === "Enter") {
        event.preventDefault();
        runAt(active);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose, total, active, runAt]);

  useEffect(() => {
    listRef.current
      ?.querySelector<HTMLElement>(`[data-index="${active}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [active]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[90] flex items-start justify-center p-4 pt-[12vh]">
      <button className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} aria-label="Đóng bảng lệnh" tabIndex={-1} />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Bảng lệnh"
        className="animate-pop-in relative z-10 w-full max-w-xl overflow-hidden rounded-2xl border border-border bg-surface shadow-pop"
      >
        <div className="flex items-center gap-3 border-b border-border-soft px-4 py-3.5">
          <IconSearch className="h-4 w-4 shrink-0 text-ink-faint" />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Tìm trang, từ vựng hoặc lệnh..."
            aria-label="Tìm kiếm"
            className="min-w-0 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-ink-faint"
          />
          <Kbd>Esc</Kbd>
        </div>

        <div ref={listRef} className="max-h-[52vh] overflow-y-auto p-2" role="listbox" aria-label="Kết quả">
          {total === 0 && (
            <p className="px-3 py-8 text-center text-sm text-ink-faint">Không có kết quả phù hợp.</p>
          )}

          {filtered.map((command, index) => (
            <Row
              key={command.id}
              index={index}
              active={index === active}
              onHover={setActive}
              onSelect={() => runAt(index)}
            >
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-ink">{command.label}</span>
                {command.hint && <span className="block truncate text-xs text-ink-faint">{command.hint}</span>}
              </span>
              <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-ink-faint">
                {command.group}
              </span>
            </Row>
          ))}

          {results.length > 0 && (
            <p className="px-3 pt-3 pb-1 text-[10px] font-semibold uppercase tracking-wide text-ink-faint">
              Từ vựng
            </p>
          )}
          {results.map((word, offset) => {
            const index = filtered.length + offset;
            return (
              <Row
                key={word.id}
                index={index}
                active={index === active}
                onHover={setActive}
                onSelect={() => runAt(index)}
              >
                <span className="hanzi shrink-0 text-lg font-semibold text-ink">{word.hanzi}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm text-ink-soft">{word.meaning}</span>
                  <span className="block truncate text-xs text-ink-faint">{word.pinyin}</span>
                </span>
                <IconVolume className="h-3.5 w-3.5 shrink-0 text-ink-faint" />
              </Row>
            );
          })}
        </div>

        <div className="flex items-center justify-between gap-2 border-t border-border-soft px-4 py-2.5 text-[11px] text-ink-faint">
          <span className="flex items-center gap-1.5">
            <Kbd>↑</Kbd>
            <Kbd>↓</Kbd> di chuyển
          </span>
          <span className="flex items-center gap-1.5">
            <Kbd>Enter</Kbd> chọn
            <IconArrowRight className="h-3 w-3" />
          </span>
        </div>
      </div>
    </div>
  );
}

function Row({
  index,
  active,
  onHover,
  onSelect,
  children,
}: {
  index: number;
  active: boolean;
  onHover: (index: number) => void;
  onSelect: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      data-index={index}
      role="option"
      aria-selected={active}
      onMouseEnter={() => onHover(index)}
      onClick={onSelect}
      className={clsx(
        "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors duration-150",
        active ? "bg-accent-soft" : "hover:bg-surface-2"
      )}
    >
      {children}
    </button>
  );
}
