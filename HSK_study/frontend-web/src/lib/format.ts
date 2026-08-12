const NUMBER_FORMAT = new Intl.NumberFormat("vi-VN");

export function formatNumber(value: number | null | undefined): string {
  return NUMBER_FORMAT.format(value ?? 0);
}

export function formatPercent(value: number | null | undefined, digits = 0): string {
  return `${(value ?? 0).toFixed(digits)}%`;
}

/** Render an SRS interval in the largest unit that stays readable. */
export function formatInterval(days: number): string {
  if (days <= 0) return "ngay bây giờ";
  if (days < 1 / 24) return `${Math.max(1, Math.round(days * 24 * 60))} phút`;
  if (days < 1) return `${Math.round(days * 24)} giờ`;
  if (days < 30) return `${Math.round(days)} ngày`;
  if (days < 365) return `${Math.round(days / 30)} tháng`;
  return `${(days / 365).toFixed(1)} năm`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export function formatRelative(value: string | null | undefined): string {
  if (!value) return "chưa ôn";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "chưa ôn";
  const diffMs = Date.now() - parsed.getTime();
  const diffDays = Math.floor(diffMs / 86_400_000);
  if (diffDays <= 0) return "hôm nay";
  if (diffDays === 1) return "hôm qua";
  if (diffDays < 30) return `${diffDays} ngày trước`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} tháng trước`;
  return `${Math.floor(diffDays / 365)} năm trước`;
}
