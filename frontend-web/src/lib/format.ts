const NUMBER_FORMAT = new Intl.NumberFormat("vi-VN");

/* --------------------------------------------------------------------------
   Cutting a dictionary entry down to a card

   The vocabulary table holds full CVDICT entries, and that is the right thing
   for it to hold — 就 genuinely has fourteen senses, and the dictionary screen
   should show all of them. But a flashcard has room for one line, and a
   multiple-choice button for about four words. Dropping the whole entry into
   those places is what made a card unreadable and made a listening option like
   "điểm yếu; lỗi; khuyết điểm; bất lợi; lượng từ: 个" impossible to choose
   between.

   So the shortening happens here, at the point of display, rather than in the
   database. The data stays complete; the card takes what fits.
-------------------------------------------------------------------------- */

/** Sense fragments that are reference notes rather than meanings. */
const NOT_A_MEANING = /^(lượng từ|CL)\s*[:：]/i;

/**
 * The leading senses of a gloss, for somewhere with one line to spare.
 *
 * Senses come semicolon-separated, roughly in order of usefulness, so taking
 * the first few keeps the sense a learner most likely wants. Classifier notes
 * are dropped outright: they are dictionary apparatus, never an answer.
 */
export function shortMeaning(
  meaning: string | null | undefined,
  { senses = 2, chars = 64 }: { senses?: number; chars?: number } = {}
): string {
  const parts = (meaning ?? "")
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean)
    .filter((part) => !NOT_A_MEANING.test(part));
  if (parts.length === 0) return (meaning ?? "").trim();

  const kept: string[] = [];
  for (const part of parts.slice(0, senses)) {
    // Always keep the first sense even when it alone is over budget; a button
    // with nothing on it is worse than a button with a long label.
    if (kept.length > 0 && kept.join("; ").length + part.length + 2 > chars) break;
    kept.push(part);
  }

  let text = kept.join("; ");
  let clipped = kept.length < parts.length;
  if (text.length > chars) {
    // Cut on a word boundary so the label does not end mid-syllable.
    const cut = text.slice(0, chars);
    const space = cut.lastIndexOf(" ");
    text = (space > chars * 0.6 ? cut.slice(0, space) : cut).trimEnd();
    clipped = true;
  }
  return clipped ? `${text}…` : text;
}

/** The tightest usable form, for a multiple-choice button. */
export function optionLabel(meaning: string | null | undefined): string {
  return shortMeaning(meaning, { senses: 1, chars: 38 });
}

/**
 * Shorten a set of options, but never to the point where two of them match.
 *
 * Trimming each option to its first sense is what makes them readable, and it
 * is also what could make two different words collide — "thực hiện; tạo ra…"
 * and "thực hiện; đưa ra…" both cut down to "thực hiện…", leaving a question
 * with two identical buttons and no right answer. So the labels are widened
 * together until they are distinct, and if even the full glosses are identical
 * the question is no worse off than before.
 */
export function distinctOptionLabels(meanings: Array<string | null | undefined>): string[] {
  const budgets = [
    { senses: 1, chars: 38 },
    { senses: 2, chars: 64 },
    { senses: 3, chars: 96 },
  ];
  for (const budget of budgets) {
    const labels = meanings.map((meaning) => shortMeaning(meaning, budget));
    if (new Set(labels).size === labels.length) return labels;
  }
  return meanings.map((meaning) => (meaning ?? "").trim());
}

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
