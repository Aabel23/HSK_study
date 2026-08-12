import { useRef, useState } from "react";
import { api } from "../lib/api";
import { useApi } from "../lib/useApi";
import { useSettings } from "../lib/settings";
import { useToast } from "../lib/toast";
import { formatNumber } from "../lib/format";
import type { AppSettings } from "../lib/types";
import {
  Badge,
  Button,
  Card,
  Kbd,
  Modal,
  PageHeader,
  Segmented,
  SliderField,
  Switch,
} from "../components/ui";
import { IconDownload, IconKeyboard, IconTrash, IconUpload } from "../components/icons";

const LEVEL_OPTIONS = [
  { value: "all", label: "Tất cả" },
  { value: "1", label: "HSK 1" },
  { value: "2", label: "HSK 2" },
  { value: "3", label: "HSK 3" },
  { value: "4", label: "HSK 4" },
  { value: "5", label: "HSK 5" },
  { value: "6", label: "HSK 6" },
  { value: "7-9", label: "HSK 7-9" },
];

const SHORTCUTS = [
  { keys: ["Ctrl", "K"], description: "Mở bảng lệnh tìm kiếm nhanh" },
  { keys: ["/"], description: "Mở bảng lệnh (khi không gõ trong ô nhập)" },
  { keys: ["Space"], description: "Hiện đáp án khi đang ôn tập" },
  { keys: ["1"], description: "Đánh giá: Quên rồi" },
  { keys: ["2"], description: "Đánh giá: Khó" },
  { keys: ["3"], description: "Đánh giá: Nhớ" },
  { keys: ["4"], description: "Đánh giá: Quá dễ" },
  { keys: ["Esc"], description: "Đóng hộp thoại đang mở" },
];

export default function Settings() {
  const { settings, update, reset } = useSettings();
  const toast = useToast();
  const health = useApi(() => api.health(), []);
  const fileInput = useRef<HTMLInputElement>(null);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const set = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    void update({ [key]: value } as Partial<AppSettings>);
  };

  const exportBackup = async () => {
    setBusy(true);
    try {
      const payload = await api.backup.export();
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `chinese-study-backup-${new Date().toISOString().slice(0, 10)}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      toast.success("Đã xuất bản sao lưu", "Tệp JSON đã được tải xuống máy của bạn.");
    } catch (error) {
      toast.error("Xuất sao lưu thất bại", error instanceof Error ? error.message : undefined);
    } finally {
      setBusy(false);
    }
  };

  const importBackup = async (file: File) => {
    setBusy(true);
    try {
      const payload = JSON.parse(await file.text());
      const result = await api.backup.import(payload);
      const restored = result.imported.learning_progress ?? 0;
      toast.success(
        "Khôi phục thành công",
        `Đã hợp nhất ${formatNumber(restored)} từ vựng và toàn bộ tiến độ liên quan.`
      );
    } catch (error) {
      toast.error(
        "Khôi phục thất bại",
        error instanceof Error ? error.message : "Tệp không hợp lệ."
      );
    } finally {
      setBusy(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  return (
    <div className="animate-float-in max-w-4xl">
      <PageHeader
        eyebrow="Tuỳ chỉnh"
        title="Cài đặt"
        description="Điều chỉnh mục tiêu, hiển thị và sao lưu dữ liệu. Mọi thay đổi được lưu ngay trên máy bạn."
      />

      <div className="grid gap-6">
        <Card className="p-6">
          <h2 className="font-display text-lg font-bold text-ink">Mục tiêu học tập</h2>
          <p className="mt-1 text-sm text-ink-soft">
            Mục tiêu vừa sức giúp giữ chuỗi ngày học lâu hơn một mục tiêu quá tham vọng.
          </p>
          <div className="mt-4 divide-y divide-border-soft">
            <SliderField
              label="Số lượt ôn mỗi ngày"
              value={settings.daily_goal}
              min={5}
              max={200}
              step={5}
              suffix="lượt"
              onChange={(value) => set("daily_goal", value)}
            />
            <SliderField
              label="Từ mới mỗi ngày"
              value={settings.new_words_per_day}
              min={0}
              max={50}
              step={1}
              suffix="từ"
              onChange={(value) => set("new_words_per_day", value)}
            />
            <SliderField
              label="Số thẻ mỗi phiên"
              value={settings.session_size}
              min={5}
              max={100}
              step={5}
              suffix="thẻ"
              onChange={(value) => set("session_size", value)}
            />
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="font-display text-lg font-bold text-ink">Hiển thị</h2>
          <div className="mt-4 divide-y divide-border-soft">
            <div className="flex flex-wrap items-center justify-between gap-3 py-3">
              <span className="text-sm font-medium text-ink">Giao diện</span>
              <Segmented
                label="Giao diện"
                value={settings.theme}
                onChange={(value) => set("theme", value)}
                options={[
                  { value: "dark", label: "Tối" },
                  { value: "light", label: "Sáng" },
                ]}
              />
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 py-3">
              <span className="text-sm font-medium text-ink">Cấp độ mặc định</span>
              <Segmented
                label="Cấp độ mặc định"
                value={settings.preferred_level}
                onChange={(value) => set("preferred_level", value)}
                options={LEVEL_OPTIONS}
              />
            </div>
            <Switch
              label="Hiện pinyin"
              description="Ẩn đi để tự kiểm tra khả năng đọc Hán tự."
              checked={settings.show_pinyin}
              onChange={(value) => set("show_pinyin", value)}
            />
            <Switch
              label="Hiện chữ phồn thể"
              description="Hiển thị dạng phồn thể bên cạnh giản thể khi có."
              checked={settings.show_traditional}
              onChange={(value) => set("show_traditional", value)}
            />
            <Switch
              label="Giảm hiệu ứng chuyển động"
              description="Tắt animation nếu bạn thấy chóng mặt hoặc muốn tiết kiệm pin."
              checked={settings.reduced_motion}
              onChange={(value) => set("reduced_motion", value)}
            />
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="font-display text-lg font-bold text-ink">Âm thanh</h2>
          <div className="mt-4 divide-y divide-border-soft">
            <div className="flex flex-wrap items-center justify-between gap-3 py-3">
              <span className="text-sm font-medium text-ink">Giọng đọc</span>
              <Segmented
                label="Giọng đọc"
                value={settings.audio_voice}
                onChange={(value) => set("audio_voice", value)}
                options={[
                  { value: "female", label: "Nữ" },
                  { value: "male", label: "Nam" },
                ]}
              />
            </div>
            <Switch
              label="Tự động phát âm"
              description="Phát âm ngay khi một thẻ mới xuất hiện."
              checked={settings.autoplay_audio}
              onChange={(value) => set("autoplay_audio", value)}
            />
            <Switch
              label="Hiệu ứng âm thanh"
              description="Âm báo ngắn khi trả lời đúng hoặc sai."
              checked={settings.sound_effects}
              onChange={(value) => set("sound_effects", value)}
            />
          </div>
          <p className="mt-3 rounded-xl bg-surface-2 px-3 py-2 text-xs text-ink-soft">
            Lần đầu phát âm một từ cần Internet; sau đó âm thanh được lưu lại để dùng ngoại tuyến.
          </p>
        </Card>

        <Card className="p-6">
          <h2 className="font-display text-lg font-bold text-ink">Dữ liệu của bạn</h2>
          <p className="mt-1 text-sm text-ink-soft">
            Bản sao lưu chứa tiến độ, lịch ôn, ghi chú và thành tích. Khi khôi phục, dữ liệu được
            hợp nhất — không có gì bị xoá.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Button onClick={exportBackup} disabled={busy}>
              <IconDownload className="h-4 w-4" /> Xuất bản sao lưu
            </Button>
            <Button variant="secondary" onClick={() => fileInput.current?.click()} disabled={busy}>
              <IconUpload className="h-4 w-4" /> Khôi phục từ tệp
            </Button>
            <input
              ref={fileInput}
              type="file"
              accept="application/json,.json"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void importBackup(file);
              }}
            />
            <Button variant="ghost" onClick={() => setShortcutsOpen(true)}>
              <IconKeyboard className="h-4 w-4" /> Phím tắt
            </Button>
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="font-display text-lg font-bold text-ink">Nâng cao</h2>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-ink">Đặt lại tuỳ chọn</p>
              <p className="mt-0.5 text-xs text-ink-soft">
                Chỉ khôi phục cài đặt về mặc định. Tiến độ học tập không bị ảnh hưởng.
              </p>
            </div>
            <Button variant="danger" onClick={() => setResetOpen(true)}>
              <IconTrash className="h-4 w-4" /> Đặt lại
            </Button>
          </div>
          <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-border-soft pt-4 text-xs text-ink-faint">
            <Badge tone="neutral">Phiên bản {health.data?.version ?? "—"}</Badge>
            <Badge tone={health.data ? "jade" : "danger"}>
              {health.data ? "Máy chủ nội bộ đang chạy" : "Không kết nối được máy chủ"}
            </Badge>
          </div>
        </Card>
      </div>

      <Modal open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} title="Phím tắt">
        <div className="divide-y divide-border-soft">
          {SHORTCUTS.map((shortcut) => (
            <div key={shortcut.description} className="flex items-center justify-between gap-4 py-2.5">
              <span className="text-sm text-ink-soft">{shortcut.description}</span>
              <span className="flex shrink-0 gap-1">
                {shortcut.keys.map((key) => (
                  <Kbd key={key}>{key}</Kbd>
                ))}
              </span>
            </div>
          ))}
        </div>
      </Modal>

      <Modal
        open={resetOpen}
        onClose={() => setResetOpen(false)}
        title="Đặt lại cài đặt?"
        footer={
          <>
            <Button variant="ghost" onClick={() => setResetOpen(false)}>
              Huỷ
            </Button>
            <Button
              variant="danger"
              onClick={async () => {
                await reset();
                setResetOpen(false);
                toast.success("Đã đặt lại cài đặt");
              }}
            >
              Đặt lại
            </Button>
          </>
        }
      >
        <p className="text-sm text-ink-soft">
          Toàn bộ tuỳ chọn sẽ trở về giá trị mặc định. Tiến độ học, lịch ôn tập và thành tích của
          bạn được giữ nguyên.
        </p>
      </Modal>
    </div>
  );
}
