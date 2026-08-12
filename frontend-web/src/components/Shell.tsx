import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import clsx from "clsx";
import { api } from "../lib/api";
import { useTheme } from "../lib/theme";
import { useApi } from "../lib/useApi";
import { formatNumber } from "../lib/format";
import { LevelPicker } from "./LevelPicker";
import { CommandPalette } from "./CommandPalette";
import { Kbd } from "./ui";
import { MOBILE_NAV, SECTION_LABELS, VISIBLE_NAV_ITEMS, type NavItem } from "./navigation";
import { IconBolt, IconFlame, IconMenu, IconMoon, IconSearch, IconSun, IconX } from "./icons";

const SECTION_ORDER: NavItem["section"][] = ["chính", "luyện tập", "tiến độ"];

export function Shell({ children }: { children: ReactNode }) {
  const { theme, toggle } = useTheme();
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  // The streak header reloads on navigation so a finished session is reflected
  // straight away without a manual refresh.
  const streak = useApi(() => api.streak(30), [location.pathname]);
  const reviewStats = useApi(() => api.review.stats(), [location.pathname]);

  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  // Global shortcuts. Typing in a field must never be hijacked, so the handler
  // bails out whenever an editable element has focus.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable;

      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((open) => !open);
        return;
      }
      if (event.key === "/" && !typing && !event.ctrlKey && !event.metaKey) {
        event.preventDefault();
        setPaletteOpen(true);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const dueCount = reviewStats.data?.due_now ?? 0;

  return (
    <div className="min-h-screen bg-base">
      <a href="#main-content" className="skip-link">
        Bỏ qua điều hướng
      </a>

      <div className="mx-auto flex min-h-screen max-w-[1600px]">
        <aside
          id="app-sidebar"
          aria-label="Điều hướng chính"
          className={clsx(
            "fixed inset-y-0 left-0 z-40 flex w-72 shrink-0 flex-col overflow-y-auto border-r border-border bg-surface p-5 transition-transform duration-200 lg:static lg:translate-x-0",
            drawerOpen ? "translate-x-0" : "-translate-x-full"
          )}
        >
          <div className="flex items-center justify-between">
            <a href="#/" className="flex items-center gap-3">
              <span className="font-display flex h-11 w-11 items-center justify-center rounded-2xl bg-accent text-xl font-bold text-accent-ink">
                学
              </span>
              <span>
                <span className="font-display block text-lg font-bold leading-tight text-ink">HSK Master</span>
                <span className="block text-xs text-ink-soft">HSK 1–9 · Tiếng Việt</span>
              </span>
            </a>
            <button
              className="rounded-lg p-1.5 text-ink-soft transition-colors hover:bg-surface-2 hover:text-ink lg:hidden"
              onClick={() => setDrawerOpen(false)}
              aria-label="Đóng menu"
            >
              <IconX />
            </button>
          </div>

          <button
            onClick={() => setPaletteOpen(true)}
            className="mt-5 flex w-full items-center gap-2.5 rounded-xl border border-border bg-surface-2 px-3 py-2.5 text-left text-sm text-ink-faint transition-colors duration-200 hover:border-border-strong hover:text-ink-soft"
          >
            <IconSearch className="h-4 w-4 shrink-0" />
            <span className="flex-1 truncate">Tìm kiếm nhanh</span>
            <Kbd>Ctrl K</Kbd>
          </button>

          <div className="mt-5">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">Cấp độ đang học</p>
            <LevelPicker />
          </div>

          <nav className="mt-5 flex flex-1 flex-col gap-5">
            {SECTION_ORDER.map((section) => (
              <div key={section}>
                <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-faint">
                  {SECTION_LABELS[section]}
                </p>
                <div className="flex flex-col gap-0.5">
                  {VISIBLE_NAV_ITEMS.filter((item) => item.section === section).map(
                    ({ to, label, icon: Icon, end }) => (
                      <NavLink
                        key={to}
                        to={to}
                        end={end}
                        className={({ isActive }) =>
                          clsx(
                            "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors duration-200",
                            isActive
                              ? "bg-accent-soft text-accent"
                              : "text-ink-soft hover:bg-surface-2 hover:text-ink"
                          )
                        }
                      >
                        <Icon className="h-[18px] w-[18px] shrink-0" />
                        <span className="flex-1 truncate">{label}</span>
                        {to === "/review" && dueCount > 0 && (
                          <span className="tnum rounded-full bg-accent px-1.5 py-0.5 text-[10px] font-bold text-accent-ink">
                            {dueCount > 99 ? "99+" : dueCount}
                          </span>
                        )}
                      </NavLink>
                    )
                  )}
                </div>
              </div>
            ))}
          </nav>

          <div className="mt-5 rounded-2xl border border-border-soft bg-surface-2 p-4">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-gold">Mục tiêu hôm nay</p>
              <span className="tnum text-xs font-semibold text-ink-soft">
                {streak.data ? `${streak.data.today_reviews}/${streak.data.daily_goal}` : "—"}
              </span>
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-3">
              <div
                className="h-full rounded-full bg-gold transition-[width] duration-500"
                style={{ width: `${streak.data?.goal_percentage ?? 0}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-ink-soft">
              {streak.data?.goal_met
                ? "Đã hoàn thành mục tiêu hôm nay."
                : "Nghe · Đọc · Viết · Kiểm tra, học đều mỗi ngày."}
            </p>
          </div>
        </aside>

        {drawerOpen && (
          <button
            className="fixed inset-0 z-30 bg-black/50 lg:hidden"
            onClick={() => setDrawerOpen(false)}
            aria-label="Đóng menu"
          />
        )}

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="no-print sticky top-0 z-20 flex items-center gap-3 border-b border-border bg-base/85 px-4 py-3 backdrop-blur sm:px-8">
            <button
              className="rounded-lg p-2 text-ink-soft transition-colors hover:bg-surface-2 hover:text-ink lg:hidden"
              onClick={() => setDrawerOpen(true)}
              aria-label="Mở menu"
              aria-controls="app-sidebar"
              aria-expanded={drawerOpen}
            >
              <IconMenu />
            </button>

            <button
              onClick={() => setPaletteOpen(true)}
              className="rounded-lg p-2 text-ink-soft transition-colors hover:bg-surface-2 hover:text-ink lg:hidden"
              aria-label="Tìm kiếm nhanh"
            >
              <IconSearch className="h-[18px] w-[18px]" />
            </button>

            <p className="hidden text-sm text-ink-faint lg:block">
              Dữ liệu học được lưu trên máy của bạn
            </p>

            <div className="ml-auto flex items-center gap-2">
              <HeaderStat
                icon={<IconFlame className="h-3.5 w-3.5" />}
                value={streak.data ? `${streak.data.current_streak}` : "—"}
                label="ngày liên tiếp"
                tone="text-accent"
              />
              <HeaderStat
                icon={<IconBolt className="h-3.5 w-3.5" />}
                value={streak.data ? formatNumber(streak.data.total_xp) : "—"}
                label={streak.data ? `cấp ${streak.data.level}` : "kinh nghiệm"}
                tone="text-gold"
              />
              <button
                onClick={toggle}
                className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface text-ink-soft transition-colors duration-200 hover:text-accent"
                aria-label={theme === "dark" ? "Chuyển giao diện sáng" : "Chuyển giao diện tối"}
              >
                {theme === "dark" ? <IconSun className="h-4 w-4" /> : <IconMoon className="h-4 w-4" />}
              </button>
            </div>
          </header>

          <main id="main-content" className="flex-1 px-4 pb-24 pt-8 sm:px-8 lg:pb-8">
            {children}
          </main>
        </div>
      </div>

      <MobileTabBar dueCount={dueCount} />
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}

function HeaderStat({
  icon,
  value,
  label,
  tone,
}: {
  icon: ReactNode;
  value: string;
  label: string;
  tone: string;
}) {
  return (
    <span
      title={label}
      className="hidden items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1.5 sm:inline-flex"
    >
      <span className={tone}>{icon}</span>
      <span className="tnum text-xs font-bold text-ink">{value}</span>
      <span className="text-[10px] text-ink-faint">{label}</span>
    </span>
  );
}

/** Thumb-reachable navigation for small screens. */
function MobileTabBar({ dueCount }: { dueCount: number }) {
  const items = MOBILE_NAV.map((path) =>
    VISIBLE_NAV_ITEMS.find((item) => item.to === path)
  ).filter((item): item is NavItem => Boolean(item));
  return (
    <nav
      aria-label="Điều hướng nhanh"
      className="no-print fixed inset-x-0 bottom-0 z-30 flex border-t border-border bg-surface/95 backdrop-blur lg:hidden"
    >
      {items.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            clsx(
              "relative flex flex-1 flex-col items-center gap-1 py-2.5 text-[10px] font-medium transition-colors duration-200",
              isActive ? "text-accent" : "text-ink-faint"
            )
          }
        >
          <span className="relative">
            <Icon className="h-5 w-5" />
            {to === "/review" && dueCount > 0 && (
              <span className="absolute -right-1.5 -top-1 h-2 w-2 rounded-full bg-accent" />
            )}
          </span>
          <span className="truncate">{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
