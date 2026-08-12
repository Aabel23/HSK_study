import type { ComponentType } from "react";
import {
  IconBook,
  IconChart,
  IconCheckSquare,
  IconHeadphones,
  IconHome,
  IconLayers,
  IconMessage,
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
  { to: "/quiz", label: "Kiểm tra", description: "Trắc nghiệm tổng hợp", icon: IconCheckSquare, section: "luyện tập" },
  { to: "/writing", label: "Luyện viết", description: "Tập viết chữ Hán đúng nét", icon: IconPencil, section: "luyện tập" },
  { to: "/progress", label: "Tiến độ", description: "Thống kê và lịch sử học", icon: IconChart, section: "tiến độ" },
  { to: "/achievements", label: "Thành tích", description: "Huy hiệu và cột mốc", icon: IconTrophy, section: "tiến độ" },
  { to: "/settings", label: "Cài đặt", description: "Tuỳ chọn, sao lưu và khôi phục", icon: IconSettings, section: "tiến độ" },
];

/** Condensed set shown in the mobile bottom bar. */
export const MOBILE_NAV = ["/", "/review", "/vocabulary", "/quiz", "/progress"];

export const SECTION_LABELS: Record<NavItem["section"], string> = {
  "chính": "Học tập",
  "luyện tập": "Luyện tập",
  "tiến độ": "Theo dõi",
};
