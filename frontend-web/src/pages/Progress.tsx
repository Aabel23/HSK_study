import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { ProgressSummary, WritingProgressSummary } from "../lib/types";
import { Badge, Card, LoadingState, PageHeader, ProgressBar, StatTile } from "../components/ui";

const SESSION_LABEL: Record<string, string> = {
  flashcard: "Thẻ ghi nhớ",
  matching: "Nối từ",
  sentence: "Luyện câu",
  quiz: "Kiểm tra",
  listening: "Luyện nghe",
  writing: "Luyện viết",
};

export default function Progress() {
  const [data, setData] = useState<ProgressSummary | null>(null);
  const [writing, setWriting] = useState<WritingProgressSummary | null>(null);

  useEffect(() => {
    api.progress.summary().then(setData);
    api.writing.progress().then(setWriting);
  }, []);

  if (!data) return <LoadingState />;

  return (
    <div className="animate-float-in">
      <PageHeader eyebrow="Theo dõi" title="Tiến độ học tập" description="Tổng quan mức độ hoàn thành và lịch sử luyện tập gần đây." />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatTile label="Hoàn thành" value={`${data.completion_percentage}%`} accent="jade" />
        <StatTile label="Đã thuộc" value={data.mastered_count.toLocaleString("vi-VN")} accent="accent" />
        <StatTile label="Cần ôn" value={data.review_count.toLocaleString("vi-VN")} accent="sky" />
        <StatTile label="Chữ luyện viết" value={writing?.practiced_count ?? 0} hint={`${writing?.mastered_count ?? 0} thành thạo`} accent="violet" />
      </div>

      <Card className="mt-6 p-6">
        <ProgressBar value={data.completion_percentage} accent="jade" />
        <p className="mt-2 text-xs text-ink-soft">
          {data.mastered_count.toLocaleString("vi-VN")} / {data.total_vocabulary.toLocaleString("vi-VN")} từ đã thuộc
        </p>
      </Card>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <h2 className="font-display text-lg font-bold text-ink">Từ cần ôn lại</h2>
          <div className="mt-4 flex flex-col gap-2">
            {data.review_items.length === 0 && <p className="text-sm text-ink-faint">Không có từ nào cần ôn.</p>}
            {data.review_items.map((item) => (
              <div key={item.id} className="flex items-center justify-between border-b border-border-soft pb-2 text-sm last:border-0">
                <div>
                  <span className="hanzi font-semibold text-ink">{item.hanzi}</span>
                  <span className="ml-2 text-ink-soft">{item.meaning}</span>
                </div>
                <Badge tone="sky">{item.pinyin}</Badge>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="font-display text-lg font-bold text-ink">Lịch sử phiên gần đây</h2>
          <div className="mt-4 flex flex-col gap-2">
            {data.recent_sessions.length === 0 && <p className="text-sm text-ink-faint">Chưa có phiên học nào.</p>}
            {data.recent_sessions.map((session) => (
              <div key={`${session.session_type}-${session.id}`} className="flex items-center justify-between border-b border-border-soft pb-2 text-sm last:border-0">
                <span className="text-ink">{SESSION_LABEL[session.session_type] ?? session.session_type}</span>
                <span className="text-ink-soft">
                  {session.correct_items}/{session.total_items} đúng
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
