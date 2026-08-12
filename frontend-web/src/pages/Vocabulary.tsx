import { useEffect, useState } from "react";
import { useLevel } from "../lib/levelContext";
import { api } from "../lib/api";
import type { VocabularyItem } from "../lib/types";
import { AudioButton, Badge, Card, EmptyState, LoadingState, PageHeader } from "../components/ui";

const STATUS_LABEL: Record<string, string> = { new: "Chưa học", learning: "Đang học", review: "Cần ôn", mastered: "Đã thuộc" };
const STATUS_TONE: Record<string, "neutral" | "sky" | "gold" | "jade"> = { new: "neutral", learning: "gold", review: "sky", mastered: "jade" };

const PAGE_SIZE = 24;

export default function Vocabulary() {
  const { level } = useLevel();
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [page, setPage] = useState(0);
  const [data, setData] = useState<{ items: VocabularyItem[]; total: number } | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => setPage(0), [debounced, level]);

  useEffect(() => {
    setLoading(true);
    api.vocabulary
      .list({
        search: debounced || undefined,
        hsk_level: level === "all" ? undefined : level,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      })
      .then(setData)
      .finally(() => setLoading(false));
  }, [debounced, level, page]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="animate-float-in">
      <PageHeader
        eyebrow="Từ điển"
        title="Từ vựng HSK"
        description="Tra cứu toàn bộ từ vựng HSK 1-9 với pinyin, nghĩa tiếng Việt và phát âm chuẩn."
      />

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Tìm theo Hán tự, pinyin hoặc nghĩa..."
          className="w-full max-w-md rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-ink outline-none placeholder:text-ink-faint focus:border-accent"
        />
        {data && <span className="text-sm text-ink-soft">{data.total.toLocaleString("vi-VN")} từ</span>}
      </div>

      {loading && !data ? (
        <LoadingState />
      ) : data && data.items.length === 0 ? (
        <EmptyState title="Không tìm thấy từ nào" description="Thử từ khoá khác hoặc đổi cấp độ." />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data?.items.map((item) => {
            const isOpen = expanded === item.id;
            return (
              <Card
                key={item.id}
                className="cursor-pointer p-4 transition-colors hover:border-accent/40"
                onClick={() => setExpanded(isOpen ? null : item.id)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-baseline gap-2">
                      <span className="hanzi text-2xl font-bold text-ink">{item.hanzi}</span>
                      <span className="text-sm text-gold">{item.pinyin}</span>
                    </div>
                    <p className="mt-1 text-sm text-ink-soft">{item.meaning}</p>
                  </div>
                  <AudioButton text={item.hanzi} size="sm" />
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-1.5">
                  <Badge tone="neutral">HSK {item.hsk_level}</Badge>
                  <Badge tone={STATUS_TONE[item.status]}>{STATUS_LABEL[item.status]}</Badge>
                  {item.topic && <Badge tone="neutral">{item.topic}</Badge>}
                </div>
                {isOpen && (
                  <div className="mt-3 space-y-2 border-t border-border-soft pt-3 text-sm">
                    {item.meaning_en && item.meaning_en !== item.meaning && (
                      <p className="text-ink-faint">
                        <span className="font-medium">Nghĩa tiếng Anh:</span> {item.meaning_en}
                      </p>
                    )}
                    {item.example && (
                      <div className="flex items-start justify-between gap-2 rounded-lg bg-surface-2 p-3">
                        <div>
                          <p className="hanzi text-ink">{item.example}</p>
                          {item.example_pinyin && <p className="text-xs text-gold">{item.example_pinyin}</p>}
                          {item.example_meaning && <p className="text-xs text-ink-soft">{item.example_meaning}</p>}
                        </div>
                        <AudioButton text={item.example} size="sm" />
                      </div>
                    )}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}

      {data && totalPages > 1 && (
        <div className="mt-8 flex items-center justify-center gap-2">
          <button
            disabled={page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            className="rounded-lg border border-border px-3 py-1.5 text-sm text-ink-soft disabled:opacity-40"
          >
            Trước
          </button>
          <span className="text-sm text-ink-soft">
            {page + 1} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            className="rounded-lg border border-border px-3 py-1.5 text-sm text-ink-soft disabled:opacity-40"
          >
            Sau
          </button>
        </div>
      )}
    </div>
  );
}
