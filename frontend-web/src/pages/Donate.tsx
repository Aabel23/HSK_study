import { useCallback, useEffect, useRef, useState } from "react";
import QRCode from "qrcode";
import clsx from "clsx";
import { api } from "../lib/api";
import { useApi } from "../lib/useApi";
import { useToast } from "../lib/toast";
import { formatNumber, formatRelative } from "../lib/format";
import type { Donation, DonationStatus } from "../lib/types";
import {
  Badge,
  Button,
  Card,
  ErrorState,
  Modal,
  PageHeader,
  PageSkeleton,
  StatTile,
} from "../components/ui";
import { IconCheck, IconHeartFilled, IconQr } from "../components/icons";

const POLL_INTERVAL_MS = 3000;

const STATUS_LABEL: Record<DonationStatus, string> = {
  pending: "Đang chờ",
  paid: "Đã nhận",
  cancelled: "Đã huỷ",
  expired: "Hết hạn",
};

const STATUS_TONE: Record<DonationStatus, "gold" | "jade" | "neutral"> = {
  pending: "gold",
  paid: "jade",
  cancelled: "neutral",
  expired: "neutral",
};

function formatDong(value: number): string {
  return `${formatNumber(value)} ₫`;
}

export default function Donate() {
  const toast = useToast();
  const config = useApi(() => api.donate.config(), []);
  const summary = useApi(() => api.donate.summary(), []);
  const recent = useApi(() => api.donate.recent(8), []);

  const [amount, setAmount] = useState(50_000);
  const [donorName, setDonorName] = useState("");
  const [message, setMessage] = useState("");
  const [donation, setDonation] = useState<Donation | null>(null);
  const [busy, setBusy] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const settings = config.data;
  const isPaid = donation?.status === "paid";

  // The QR is drawn from the raw VietQR payload with a bundled encoder rather
  // than a CDN script or a remote image service: the app has to keep working
  // with no internet, and the payload should not travel to a third party.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !donation?.qr_code || isPaid) return;
    QRCode.toCanvas(canvas, donation.qr_code, {
      width: 240,
      margin: 1,
      color: { dark: "#0f172a", light: "#ffffff" },
    }).catch(() => {
      toast.error("Không vẽ được mã QR", "Bạn có thể mở trang thanh toán thay thế.");
    });
  }, [donation?.qr_code, isPaid, toast]);

  const refreshAll = useCallback(() => {
    summary.reload();
    recent.reload();
  }, [summary, recent]);

  // PayOS cannot call a webhook back to 127.0.0.1, so the browser polls until
  // the transfer settles. Polling stops as soon as the status is final.
  useEffect(() => {
    if (!donation || donation.status !== "pending") return;
    const orderCode = donation.order_code;
    const timer = setInterval(async () => {
      try {
        const updated = await api.donate.status(orderCode);
        if (updated.status !== "pending") {
          setDonation(updated);
          refreshAll();
        }
      } catch {
        // A failed poll is not worth surfacing; the next tick tries again.
      }
    }, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [donation, refreshAll]);

  async function start() {
    if (!settings) return;
    setBusy(true);
    try {
      setDonation(await api.donate.create(amount, message, donorName));
    } catch (error) {
      toast.error("Không tạo được mã QR", error instanceof Error ? error.message : undefined);
    } finally {
      setBusy(false);
    }
  }

  async function close() {
    const current = donation;
    setDonation(null);
    if (current?.status === "pending") {
      // Release the link so it stops sitting in the donor's banking app.
      try {
        await api.donate.cancel(current.order_code);
      } catch {
        // It may already have been paid or expired; the list will show the truth.
      }
      refreshAll();
    }
  }

  if (config.error) return <ErrorState message={config.error} onRetry={config.reload} />;
  if (config.loading && !settings) return <PageSkeleton tiles={3} rows={1} />;

  const clampedAmount = settings
    ? Math.min(settings.max_amount, Math.max(settings.min_amount, amount))
    : amount;

  return (
    <div className="animate-float-in">
      <PageHeader
        eyebrow="Ủng hộ"
        title={`Donate cho ${settings?.recipient ?? "anh Ba"}`}
        description="Ứng dụng miễn phí và chạy hoàn toàn trên máy bạn. Nếu thấy hữu ích, bạn có thể mời tác giả một ly cà phê."
      />

      {!settings?.enabled ? (
        <Card className="max-w-2xl p-6">
          <p className="font-display text-lg font-bold text-ink">Chưa cấu hình cổng thanh toán</p>
          <p className="mt-2 text-sm text-ink-soft">
            Tính năng ủng hộ cần khoá PayOS. Tạo kênh thanh toán tại{" "}
            <a
              href="https://my.payos.vn"
              target="_blank"
              rel="noreferrer"
              className="font-medium text-accent underline"
            >
              my.payos.vn
            </a>
            , rồi đặt ba biến môi trường sau (hoặc ghi vào file <code>.env</code> ở thư mục gốc):
          </p>
          <pre className="mt-4 overflow-x-auto rounded-xl border border-border bg-surface-2 p-4 font-mono text-xs text-ink-soft">
{`PAYOS_CLIENT_ID=...
PAYOS_API_KEY=...
PAYOS_CHECKSUM_KEY=...`}
          </pre>
          <p className="mt-3 text-xs text-ink-faint">
            Khoá chỉ nằm trong môi trường chạy, không được commit và không đóng gói vào bản .exe.
          </p>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
            <StatTile
              label="Đã nhận"
              value={formatDong(summary.data?.paid_total ?? 0)}
              accent="jade"
              icon={<IconHeartFilled className="h-4 w-4" />}
            />
            <StatTile
              label="Lượt ủng hộ"
              value={formatNumber(summary.data?.paid_count)}
              accent="gold"
            />
            <StatTile
              label="Gần nhất"
              value={summary.data?.last_paid_at ? formatRelative(summary.data.last_paid_at) : "—"}
              accent="accent"
            />
          </div>

          <div className="mt-8 grid gap-6 lg:grid-cols-3">
            <Card className="p-6 lg:col-span-2">
              <h2 className="font-display text-lg font-bold text-ink">Chọn số tiền</h2>

              <div className="mt-4 flex flex-wrap gap-2">
                {settings.suggested_amounts.map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    aria-pressed={clampedAmount === preset}
                    onClick={() => setAmount(preset)}
                    className={clsx(
                      "tnum rounded-full border px-3.5 py-1.5 text-sm font-semibold transition-colors duration-200",
                      clampedAmount === preset
                        ? "border-accent bg-accent-soft text-accent"
                        : "border-border text-ink-soft hover:border-border-strong hover:text-ink"
                    )}
                  >
                    {formatDong(preset)}
                  </button>
                ))}
              </div>

              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <label className="block">
                  <span className="text-sm font-medium text-ink">Số tiền khác (₫)</span>
                  <input
                    type="number"
                    inputMode="numeric"
                    min={settings.min_amount}
                    max={settings.max_amount}
                    step={1000}
                    value={amount}
                    onChange={(event) => setAmount(Number(event.target.value) || 0)}
                    className="tnum mt-1.5 w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm font-semibold text-ink outline-none focus:border-accent"
                  />
                  <span className="mt-1 block text-xs text-ink-faint">
                    Từ {formatDong(settings.min_amount)} đến {formatDong(settings.max_amount)}
                  </span>
                </label>

                <label className="block">
                  <span className="text-sm font-medium text-ink">Tên của bạn (tuỳ chọn)</span>
                  <input
                    type="text"
                    maxLength={80}
                    value={donorName}
                    onChange={(event) => setDonorName(event.target.value)}
                    placeholder="Để trống nếu muốn ẩn danh"
                    className="mt-1.5 w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm text-ink outline-none placeholder:text-ink-faint focus:border-accent"
                  />
                </label>
              </div>

              <label className="mt-4 block">
                <span className="text-sm font-medium text-ink">Lời nhắn (tuỳ chọn)</span>
                <input
                  type="text"
                  maxLength={200}
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder="Cảm ơn anh Ba đã làm app!"
                  className="mt-1.5 w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm text-ink outline-none placeholder:text-ink-faint focus:border-accent"
                />
              </label>

              <Button
                className="mt-5 w-full"
                size="lg"
                disabled={busy || clampedAmount < settings.min_amount}
                onClick={start}
              >
                <IconQr className="h-4 w-4" />
                {busy ? "Đang tạo mã..." : `Tạo mã QR ${formatDong(clampedAmount)}`}
              </Button>
            </Card>

            <Card className="p-6">
              <h2 className="font-display text-lg font-bold text-ink">Cách ủng hộ</h2>
              <ol className="mt-3 space-y-2.5 text-sm text-ink-soft">
                <li>1. Chọn số tiền rồi nhấn tạo mã QR.</li>
                <li>2. Mở app ngân hàng bất kỳ và quét mã VietQR hiện ra.</li>
                <li>3. Xác nhận chuyển khoản trên app ngân hàng.</li>
                <li>4. Cửa sổ tự báo thành công sau vài giây.</li>
              </ol>
              <p className="mt-4 rounded-xl bg-surface-2 p-3 text-xs leading-relaxed text-ink-faint">
                Giao dịch do PayOS xử lý. Ứng dụng không nhìn thấy và không lưu bất kỳ thông tin
                ngân hàng nào của bạn — chỉ lưu số tiền và trạng thái đơn ngay trên máy này.
              </p>
            </Card>
          </div>

          {recent.data && recent.data.items.length > 0 && (
            <Card className="mt-6 p-6">
              <h2 className="font-display text-lg font-bold text-ink">Lượt ủng hộ gần đây</h2>
              <ul className="mt-3 divide-y divide-border-soft">
                {recent.data.items.map((item) => (
                  <li key={item.order_code} className="flex items-center justify-between gap-3 py-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-ink">
                        {item.donor_name || "Ẩn danh"}
                        {item.message && (
                          <span className="font-normal text-ink-soft"> — {item.message}</span>
                        )}
                      </p>
                      <p className="text-xs text-ink-faint">
                        #{item.order_code} · {formatRelative(item.created_at)}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <span className="tnum text-sm font-semibold text-ink">
                        {formatDong(item.amount)}
                      </span>
                      <Badge tone={STATUS_TONE[item.status]}>{STATUS_LABEL[item.status]}</Badge>
                    </div>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </>
      )}

      <Modal
        open={Boolean(donation)}
        onClose={close}
        title={isPaid ? "Đã nhận được, cảm ơn bạn!" : "Quét mã để ủng hộ"}
        footer={
          <Button variant="secondary" onClick={close}>
            {isPaid ? "Đóng" : "Huỷ"}
          </Button>
        }
      >
        {isPaid ? (
          <div className="flex flex-col items-center gap-3 py-6 text-center">
            <span className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-jade-soft text-jade">
              <IconCheck className="h-8 w-8" />
            </span>
            <p className="font-display text-xl font-bold text-jade">
              {formatDong(donation?.amount ?? 0)}
            </p>
            <p className="text-sm text-ink-soft">
              Cảm ơn bạn đã ủng hộ {settings?.recipient ?? "anh Ba"}. Chúc bạn học tốt!
            </p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 text-center">
            <p className="font-display tnum text-2xl font-bold text-accent">
              {formatDong(donation?.amount ?? 0)}
            </p>
            <div className="rounded-2xl border border-border bg-white p-3">
              <canvas ref={canvasRef} className="block h-auto w-[240px] max-w-full" />
            </div>
            <p className="flex items-center gap-2 text-sm text-ink-soft">
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-gold" />
              Đang chờ chuyển khoản...
            </p>
            <p className="text-xs text-ink-faint">
              Mở app ngân hàng (MB, ACB, Vietcombank, Techcombank…) rồi quét mã trên.
            </p>
            {donation?.checkout_url && (
              <a
                href={donation.checkout_url}
                target="_blank"
                rel="noreferrer"
                className="text-xs font-medium text-accent underline"
              >
                Hoặc mở trang thanh toán PayOS
              </a>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
