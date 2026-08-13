import { useCallback, useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { useLevel } from "../lib/levelContext";
import { api } from "../lib/api";
import { useToast } from "../lib/toast";
import { formatDate, formatNumber, formatInterval } from "../lib/format";
import type { ProgressStatus, VocabularyItem } from "../lib/types";
import {
  AudioButton,
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  FavoriteButton,
  LoadingState,
  Modal,
  PageHeader,
  Segmented,
} from "../components/ui";
import { IconBookmarkFilled, IconSearch } from "../components/icons";

const STATUS_LABEL: Record<ProgressStatus, string> = {
  new: "Chưa học",
  learning: "Đang học",
  review: "Cần ôn",
  mastered: "Đã thuộc",
};
const STATUS_TONE: Record<ProgressStatus, "neutral" | "sky" | "gold" | "jade"> = {
  new: "neutral",
  learning: "gold",
  review: "sky",
  mastered: "jade",
};

type StatusFilter = ProgressStatus | "all";

const STATUS_FILTERS: Array<{ value: StatusFilter; label: string }> = [
  { value: "all", label: "Tất cả" },
  { value: "new", label: "Chưa học" },
  { value: "learning", label: "Đang học" },
  { value: "review", label: "Cần ôn" },
  { value: "mastered", label: "Đã thuộc" },
];

/** Mirrors the `sort` pattern the vocabulary endpoint accepts. */
const SORTS: Array<{ value: string; label: string }> = [
  { value: "id", label: "Mặc định" },
  { value: "hanzi", label: "Nét chữ" },
  { value: "pinyin", label: "Pinyin A→Z" },
  { value: "level", label: "Cấp độ HSK" },
  { value: "frequency", label: "Phổ biến nhất" },
  { value: "recent", label: "Vừa ôn gần đây" },
  { value: "due", label: "Sắp đến hạn ôn" },
];

const PAGE_SIZE = 24;

export default function Vocabulary() {
  const { level } = useLevel();
  const toast = useToast();

  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [topic, setTopic] = useState("");
  const [sort, setSort] = useState("id");
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  const [page, setPage] = useState(0);

  const [data, setData] = useState<{ items: VocabularyItem[]; total: number } | null>(null);
  const [topics, setTopics] = useState<string[]>([]);
  const [selected, setSelected] = useState<VocabularyItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Any change to the filters invalidates the current page number.
  useEffect(() => setPage(0), [debounced, level, status, topic, sort, favoritesOnly]);

  useEffect(() => {
    api.vocabulary
      .topics()
      .then((response) => setTopics(response.items))
      .catch(() => setTopics([]));
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    api.vocabulary
      .list({
        search: debounced || undefined,
        hsk_level: level === "all" ? undefined : level,
        status: status === "all" ? undefined : status,
        topic: topic || undefined,
        sort,
        favorites_only: favoritesOnly || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      })
      .then(setData)
      // Without this the page used to sit on a spinner forever when a request
      // failed, and the rejection went unhandled.
      .catch((reason) =>
        setError(reason instanceof Error ? reason.message : "Không tải được danh sách từ vựng.")
      )
      .finally(() => setLoading(false));
  }, [debounced, favoritesOnly, level, page, sort, status, topic]);

  useEffect(load, [load]);

  /** Patch one entry in place so toggling a bookmark does not refetch the page. */
  const patchItem = useCallback((id: number, patch: Partial<VocabularyItem>) => {
    setData((previous) =>
      previous
        ? { ...previous, items: previous.items.map((item) => (item.id === id ? { ...item, ...patch } : item)) }
        : previous
    );
    setSelected((previous) => (previous && previous.id === id ? { ...previous, ...patch } : previous));
  }, []);

  const toggleFavorite = useCallback(
    async (item: VocabularyItem) => {
      const next = !item.is_favorite;
      patchItem(item.id, { is_favorite: next });
      try {
        await api.review.setFavorite(item.id, next);
      } catch {
        patchItem(item.id, { is_favorite: item.is_favorite });
        toast.error("Không lưu được đánh dấu");
      }
    },
    [patchItem, toast]
  );

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const activeFilters = useMemo(
    () => [status !== "all", Boolean(topic), favoritesOnly, sort !== "id"].filter(Boolean).length,
    [favoritesOnly, sort, status, topic]
  );

  return (
    <div className="animate-float-in">
      <PageHeader
        eyebrow="Từ điển"
        title="Từ vựng HSK"
        description="Tra cứu toàn bộ từ vựng HSK 1-9: pinyin, nghĩa tiếng Việt, phồn thể, từ loại, lượng từ, câu ví dụ có phát âm và ghi chú riêng của bạn."
      />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative w-full max-w-md">
          <IconSearch className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-faint" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Tìm theo Hán tự, pinyin hoặc nghĩa..."
            aria-label="Tìm từ vựng"
            className="w-full rounded-xl border border-border bg-surface py-2.5 pl-10 pr-4 text-sm text-ink outline-none placeholder:text-ink-faint focus:border-accent"
          />
        </div>
        {data && (
          <span className="tnum text-sm text-ink-soft">
            {formatNumber(data.total)} từ
            {activeFilters > 0 && <span className="text-ink-faint"> · {activeFilters} bộ lọc</span>}
          </span>
        )}
      </div>

      <Card className="mb-6 flex flex-wrap items-center gap-x-4 gap-y-3 p-4">
        <Segmented
          label="Lọc theo trạng thái học"
          value={status}
          onChange={setStatus}
          options={STATUS_FILTERS}
        />

        <label className="flex items-center gap-2 text-xs text-ink-soft">
          Chủ đề
          <select
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            className="rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs font-semibold text-ink outline-none focus:border-accent"
          >
            <option value="">Tất cả</option>
            {topics.map((entry) => (
              <option key={entry} value={entry}>
                {entry}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-2 text-xs text-ink-soft">
          Sắp xếp
          <select
            value={sort}
            onChange={(event) => setSort(event.target.value)}
            className="rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs font-semibold text-ink outline-none focus:border-accent"
          >
            {SORTS.map((entry) => (
              <option key={entry.value} value={entry.value}>
                {entry.label}
              </option>
            ))}
          </select>
        </label>

        <button
          onClick={() => setFavoritesOnly((value) => !value)}
          aria-pressed={favoritesOnly}
          className={clsx(
            "inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors duration-200",
            favoritesOnly
              ? "border-gold/50 bg-gold-soft text-gold"
              : "border-border bg-surface text-ink-soft hover:text-ink"
          )}
        >
          <IconBookmarkFilled className="h-3.5 w-3.5" /> Đã đánh dấu
        </button>

        {activeFilters > 0 && (
          <button
            onClick={() => {
              setStatus("all");
              setTopic("");
              setSort("id");
              setFavoritesOnly(false);
            }}
            className="ml-auto text-xs font-semibold text-ink-faint transition-colors hover:text-ink"
          >
            Xoá bộ lọc
          </button>
        )}
      </Card>

      {error ? (
        <ErrorState message={error} onRetry={load} />
      ) : loading && !data ? (
        <LoadingState />
      ) : data && data.items.length === 0 ? (
        <EmptyState
          title="Không tìm thấy từ nào"
          description="Thử từ khoá khác, đổi cấp độ hoặc xoá bớt bộ lọc."
        />
      ) : (
        <div className={clsx("grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3", loading && "opacity-60")}>
          {data?.items.map((item) => (
            <Card
              key={item.id}
              className="cursor-pointer p-4 transition-colors hover:border-accent/40"
              onClick={() => setSelected(item)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-baseline gap-2">
                    <span className="hanzi text-2xl font-bold text-ink">{item.hanzi}</span>
                    <span className="text-sm text-gold">{item.pinyin}</span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-sm text-ink-soft">{item.meaning}</p>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <AudioButton text={item.hanzi} size="sm" />
                  <FavoriteButton
                    active={Boolean(item.is_favorite)}
                    onToggle={() => void toggleFavorite(item)}
                  />
                </div>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-1.5">
                <Badge tone="neutral">HSK {item.hsk_level}</Badge>
                <Badge tone={STATUS_TONE[item.status]}>{STATUS_LABEL[item.status]}</Badge>
                {item.pos_vi && <Badge tone="neutral">{item.pos_vi}</Badge>}
              </div>
            </Card>
          ))}
        </div>
      )}

      {data && totalPages > 1 && (
        <div className="mt-8 flex items-center justify-center gap-2">
          <button
            disabled={page === 0}
            onClick={() => setPage((value) => Math.max(0, value - 1))}
            className="rounded-lg border border-border px-3 py-1.5 text-sm text-ink-soft disabled:opacity-40"
          >
            Trước
          </button>
          <span className="tnum text-sm text-ink-soft">
            {page + 1} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages - 1}
            onClick={() => setPage((value) => Math.min(totalPages - 1, value + 1))}
            className="rounded-lg border border-border px-3 py-1.5 text-sm text-ink-soft disabled:opacity-40"
          >
            Sau
          </button>
        </div>
      )}

      <EntryDialog
        item={selected}
        onClose={() => setSelected(null)}
        onPatch={patchItem}
        onToggleFavorite={toggleFavorite}
      />
    </div>
  );
}

/** The full dictionary entry: everything the database holds about one word. */
function EntryDialog({
  item,
  onClose,
  onPatch,
  onToggleFavorite,
}: {
  item: VocabularyItem | null;
  onClose: () => void;
  onPatch: (id: number, patch: Partial<VocabularyItem>) => void;
  onToggleFavorite: (item: VocabularyItem) => void;
}) {
  const toast = useToast();
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => setNote(item?.note ?? ""), [item?.id, item?.note]);

  if (!item) return null;

  async function setStatus(next: ProgressStatus) {
    if (!item) return;
    const previous = item.status;
    onPatch(item.id, { status: next });
    try {
      await api.progress.setStatus(item.id, next);
    } catch {
      onPatch(item.id, { status: previous });
      toast.error("Không đổi được trạng thái");
    }
  }

  async function saveNote() {
    if (!item) return;
    setSaving(true);
    try {
      const trimmed = note.trim();
      await api.review.setNote(item.id, trimmed || null);
      onPatch(item.id, { note: trimmed || null });
      toast.success("Đã lưu ghi chú");
    } catch {
      toast.error("Không lưu được ghi chú");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Chi tiết từ">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-baseline gap-3">
            <span className="hanzi text-4xl font-bold text-ink">{item.hanzi}</span>
            {item.traditional && item.traditional !== item.hanzi && (
              <span className="hanzi text-2xl text-ink-faint" title="Phồn thể">
                {item.traditional}
              </span>
            )}
          </div>
          <p className="mt-1.5 text-base font-medium text-gold">{item.pinyin}</p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <AudioButton text={item.hanzi} />
          <FavoriteButton active={Boolean(item.is_favorite)} onToggle={() => onToggleFavorite(item)} />
        </div>
      </div>

      <p className="mt-3 text-sm leading-relaxed text-ink">{item.meaning}</p>

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <Badge tone="neutral">HSK {item.hsk_level}</Badge>
        {item.pos_vi && <Badge tone="neutral">{item.pos_vi}</Badge>}
        {item.topic && <Badge tone="neutral">{item.topic}</Badge>}
        {item.classifiers && <Badge tone="gold">Lượng từ {item.classifiers}</Badge>}
      </div>

      {item.meaning_en && item.meaning_en !== item.meaning && (
        <p className="mt-3 text-xs text-ink-faint">
          <span className="font-semibold">Nghĩa tiếng Anh (tham chiếu):</span> {item.meaning_en}
        </p>
      )}

      {item.example && (
        <div className="mt-4 flex items-start justify-between gap-2 rounded-xl bg-surface-2 p-3">
          <div className="min-w-0">
            <p className="hanzi text-base text-ink">{item.example}</p>
            {item.example_pinyin && <p className="mt-0.5 text-xs text-gold">{item.example_pinyin}</p>}
            {item.example_meaning && <p className="mt-0.5 text-xs text-ink-soft">{item.example_meaning}</p>}
          </div>
          <AudioButton text={item.example} size="sm" />
        </div>
      )}

      <div className="mt-5 border-t border-border-soft pt-4">
        <p className="text-xs font-semibold text-ink-soft">Trạng thái học</p>
        <div className="mt-2">
          <Segmented
            label="Trạng thái học"
            value={item.status}
            onChange={(next) => void setStatus(next)}
            options={(Object.keys(STATUS_LABEL) as ProgressStatus[]).map((value) => ({
              value,
              label: STATUS_LABEL[value],
            }))}
          />
        </div>
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs sm:grid-cols-4">
          <Stat label="Đã ôn" value={`${formatNumber(item.review_count)} lần`} />
          <Stat label="Đúng / sai" value={`${formatNumber(item.correct_count)} / ${formatNumber(item.incorrect_count)}`} />
          <Stat label="Khoảng lặp" value={item.interval_days ? formatInterval(item.interval_days) : "—"} />
          <Stat label="Hạn ôn" value={item.due_at ? formatDate(item.due_at) : "—"} />
        </dl>
      </div>

      <div className="mt-5 border-t border-border-soft pt-4">
        <label htmlFor="vocab-note" className="text-xs font-semibold text-ink-soft">
          Ghi chú của bạn
        </label>
        <textarea
          id="vocab-note"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          rows={3}
          maxLength={2000}
          placeholder="Mẹo nhớ, câu tự đặt, chỗ hay nhầm..."
          className="mt-2 w-full resize-y rounded-xl border border-border bg-surface-2 px-3 py-2.5 text-sm text-ink outline-none placeholder:text-ink-faint focus:border-accent"
        />
        <div className="mt-2 flex justify-end">
          <Button
            size="sm"
            variant="secondary"
            onClick={saveNote}
            disabled={saving || note.trim() === (item.note ?? "").trim()}
          >
            Lưu ghi chú
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-ink-faint">{label}</dt>
      <dd className="tnum mt-0.5 font-semibold text-ink">{value}</dd>
    </div>
  );
}
