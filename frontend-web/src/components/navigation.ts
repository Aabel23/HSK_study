import type { ComponentType } from "react";
import {
  IconBook,
  IconChart,
  IconCheckSquare,
  IconHeadphones,
  IconHeart,
  IconHome,
  IconKeyboard,
  IconLayers,
  IconMessage,
  IconMic,
  IconPencil,
  IconRefresh,
  IconSettings,
  IconShuffle,
  IconTrophy,
} from "./icons";

export interface NavItem {
  to: string;
  label: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
  end?: boolean;
  /** Grouping used by the sidebar; the command palette ignores it. */
  section: "chính" | "luyện tập" | "tiến độ";
  /**
   * Temporarily kept out of every menu.
   *
   * The page, its route and its API stay in place — this only stops the entry
   * being offered, so switching the flag back is the whole of the undo. Set on
   * pages that are not ready to be shown yet rather than deleting them.
   */
  hidden?: boolean;
}

/**
 * Single source of truth for navigation, shared by the sidebar, the mobile bar
 * and the command palette so a new page only has to be registered once.
 */
export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Tổng quan", description: "Bảng điều khiển học tập", icon: IconHome, end: true, section: "chính" },
  { to: "/review", label: "Ôn tập thông minh", description: "Lặp lại ngắt quãng theo lịch", icon: IconRefresh, section: "chính" },
  { to: "/vocabulary", label: "Từ vựng", description: "Tra cứu và lọc theo cấp độ", icon: IconBook, section: "chính" },
  { to: "/flashcards", label: "Flashcard", description: "Ôn nhanh, tự đánh giá", icon: IconLayers, section: "luyện tập" },
  { to: "/matching", label: "Nối từ", description: "Ghép Hán tự với nghĩa hoặc pinyin", icon: IconShuffle, section: "luyện tập" },
  { to: "/sentences", label: "Luyện câu", description: "Sắp xếp cụm từ đúng thứ tự", icon: IconMessage, section: "luyện tập" },
  { to: "/listening", label: "Luyện nghe", description: "Nghe phát âm và chọn đáp án", icon: IconHeadphones, section: "luyện tập" },
  { to: "/typing", label: "Luyện gõ", description: "Gõ lại pinyin hoặc chữ Hán", icon: IconKeyboard, section: "luyện tập" },
  { to: "/quiz", label: "Kiểm tra", description: "Trắc nghiệm tổng hợp", icon: IconCheckSquare, section: "luyện tập" },
  { to: "/hskk", label: "Thi thử HSKK", description: "Đề nói mô phỏng kỳ thi khẩu ngữ", icon: IconMic, section: "luyện tập" },
  { to: "/writing", label: "Luyện viết", description: "Tập viết chữ Hán đúng nét", icon: IconPencil, section: "luyện tập", hidden: true },
  { to: "/progress", label: "Tiến độ", description: "Thống kê và lịch sử học", icon: IconChart, section: "tiến độ" },
  { to: "/achievements", label: "Thành tích", description: "Huy hiệu và cột mốc", icon: IconTrophy, section: "tiến độ", hidden: true },
  { to: "/settings", label: "Cài đặt", description: "Tuỳ chọn, sao lưu và khôi phục", icon: IconSettings, section: "tiến độ" },
  { to: "/donate", label: "Donate cho anh Ba", description: "Ủng hộ tác giả qua QR ngân hàng", icon: IconHeart, section: "tiến độ" },
];

/**
 * Everything the user is actually offered. Menus and shortcuts read this, never
 * `NAV_ITEMS`, so a hidden page cannot leak back in through one of them.
 */
export const VISIBLE_NAV_ITEMS: NavItem[] = NAV_ITEMS.filter((item) => !item.hidden);

/** Routes currently hidden, for surfaces outside the menus (dashboard tiles). */
export const HIDDEN_ROUTES: ReadonlySet<string> = new Set(
  NAV_ITEMS.filter((item) => item.hidden).map((item) => item.to)
);

/** Condensed set shown in the mobile bottom bar. */
export const MOBILE_NAV = ["/", "/review", "/vocabulary", "/quiz", "/progress"];

export const SECTION_LABELS: Record<NavItem["section"], string> = {
  "chính": "Học tập",
  "luyện tập": "Luyện tập",
  "tiến độ": "Theo dõi",
};
