import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import clsx from "clsx";
import { motion } from "framer-motion";
import { api } from "../lib/api";
import { useTheme } from "../lib/theme";
import { useApi } from "../lib/useApi";
import { formatNumber } from "../lib/format";
import { LevelPicker } from "./LevelPicker";
import { CommandPalette } from "./CommandPalette";
import { AmbientOrnament, ThatBaoField } from "./Ornament";
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
    <div className="relative min-h-screen bg-base">
      <a href="#main-content" className="skip-link">
        Bỏ qua điều hướng
      </a>

      <AmbientOrnament />

      <div className="relative z-10 mx-auto flex min-h-screen max-w-[1600px]">
        <aside
          id="app-sidebar"
          aria-label="Điều hướng chính"
          className={clsx(
            // The scroll container. Its padding moved onto the inner wrapper so
            // the pattern below can reach the panel's edges.
            "fixed inset-y-0 left-0 z-40 flex w-72 shrink-0 flex-col overflow-y-auto overscroll-contain border-r border-border bg-surface/95 backdrop-blur-xl transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] lg:sticky lg:top-0 lg:h-dvh lg:translate-x-0 lg:self-start",
            drawerOpen ? "translate-x-0" : "-translate-x-full"
          )}
        >
          {/* This wrapper exists for one reason: it is as tall as the menu, not
              as tall as the window.

              An absolutely positioned `inset-0` child of a *scrolling* element
              resolves against that element's visible box, so `h-full` was one
              screenful — and scrolling the menu ran off the bottom of the
              pattern into bare panel. `min-h-full` makes this wrapper at least
              the panel's height and then lets it grow with the nav, so the
              pattern is measured against the content it is meant to sit behind.

              `isolate` plus `-z-10` keeps it under the menu while still above
              the panel's own background, which the <aside> paints. */}
          <div className="relative isolate flex min-h-full flex-col p-5">
            {/* Round, not the lattice that was here before. 步步锦 is a grid of
                rectangles and the menu is a column of rectangular pills; two
                rectangle grids that do not share a rhythm read as a
                misalignment, because the eye keeps trying to line them up.
                Circles have no rhythm to clash with. It is the same 七宝 the
                cards carry, which also keeps the panel and the cards reading as
                one material. */}
            <ThatBaoField
              className="pointer-events-none absolute inset-0 -z-10 h-full w-full text-gold"
              opacity={0.1}
            />

            <div className="relative flex items-center justify-between">
              <a href="#/" className="group flex items-center gap-3">
                <span className="relative">
                  {/* Halo behind the mark, brightening as the pointer nears it. */}
                  <span
                    aria-hidden="true"
                    className="absolute inset-0 rounded-2xl bg-accent/40 blur-lg transition-opacity duration-500 group-hover:opacity-100 opacity-50"
                  />
                  <span className="font-display relative flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-accent-hover to-accent text-xl font-bold text-accent-ink shadow-soft ring-1 ring-gold/30 transition-transform duration-500 group-hover:scale-105 group-hover:ring-gold/60">
                    学
                  </span>
                </span>
                <span>
                  {/* Solid gold rather than the foil gradient: at 18px this is
                      body-sized text needing 4.5:1, which a gradient with a light
                      highlight cannot hold. The `gold` token is contrast-checked
                      in both themes. */}
                  <span className="font-display block text-lg font-bold leading-tight text-gold">
                    HSK Master
                  </span>
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
              className="group relative mt-5 flex w-full items-center gap-2.5 overflow-hidden rounded-xl border border-border bg-surface-2 px-3 py-2.5 text-left text-sm text-ink-faint transition-all duration-300 hover:border-gold/40 hover:text-ink-soft"
            >
              <IconSearch className="h-4 w-4 shrink-0 transition-transform duration-300 group-hover:scale-110" />
              <span className="flex-1 truncate">Tìm kiếm nhanh</span>
              <Kbd>Ctrl K</Kbd>
            </button>

            <div className="relative mt-5">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">Cấp độ đang học</p>
              <LevelPicker />
            </div>

            <nav className="relative mt-5 flex flex-col gap-5 pb-6">
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
                              "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors duration-200",
                              isActive ? "text-accent" : "text-ink-soft hover:bg-surface-2 hover:text-ink"
                            )
                          }
                        >
                          {({ isActive }) => (
                            <>
                              {isActive && (
                                // One shared element across every link, so the
                                // highlight slides from the old page to the new
                                // one instead of blinking out and back in.
                                <motion.span
                                  layoutId="nav-active"
                                  aria-hidden="true"
                                  className="absolute inset-0 rounded-xl border border-accent/25 bg-accent-soft"
                                  transition={{ type: "spring", stiffness: 420, damping: 34 }}
                                />
                              )}
                              {isActive && (
                                <span
                                  aria-hidden="true"
                                  className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-accent"
                                />
                              )}
                              <Icon
                                className={clsx(
                                  "relative h-[18px] w-[18px] shrink-0 transition-transform duration-300",
                                  isActive ? "scale-110" : "group-hover:scale-110"
                                )}
                              />
                              <span className="relative flex-1 truncate">{label}</span>
                              {to === "/review" && dueCount > 0 && (
                                <span className="tnum relative rounded-full bg-accent px-1.5 py-0.5 text-[10px] font-bold text-accent-ink shadow-soft">
                                  {dueCount > 99 ? "99+" : dueCount}
                                </span>
                              )}
                            </>
                          )}
                        </NavLink>
                      )
                    )}
                  </div>
                </div>
              ))}
            </nav>
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
          <header className="glass no-print sticky top-0 z-20 flex items-center gap-3 border-b border-border px-4 py-3 sm:px-8">
            {/* Gold hairline under the header, fading at both ends. */}
            <span aria-hidden="true" className="rule-foil absolute inset-x-0 -bottom-px" />
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
                className="group relative flex h-9 w-9 items-center justify-center overflow-hidden rounded-full border border-border bg-surface text-ink-soft transition-colors duration-300 hover:border-gold/50 hover:text-gold"
                aria-label={theme === "dark" ? "Chuyển giao diện sáng" : "Chuyển giao diện tối"}
              >
                <span className="transition-transform duration-500 group-hover:rotate-[140deg]">
                  {theme === "dark" ? <IconSun className="h-4 w-4" /> : <IconMoon className="h-4 w-4" />}
                </span>
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
      className="group hidden items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1.5 transition-all duration-300 hover:-translate-y-0.5 hover:border-gold/40 hover:shadow-soft sm:inline-flex"
    >
      <span className={clsx(tone, "transition-transform duration-300 group-hover:scale-125")}>
        {icon}
      </span>
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
      className="glass no-print fixed inset-x-0 bottom-0 z-30 flex border-t border-border lg:hidden"
    >
      <span aria-hidden="true" className="rule-foil absolute inset-x-0 top-0" />
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
          {({ isActive }) => (
            <>
              {isActive && (
                <motion.span
                  layoutId="mobile-nav-active"
                  aria-hidden="true"
                  className="absolute inset-x-3 top-0 h-[2px] rounded-full bg-accent"
                  transition={{ type: "spring", stiffness: 420, damping: 34 }}
                />
              )}
              <span className="relative">
                <Icon
                  className={clsx(
                    "h-5 w-5 transition-transform duration-300",
                    isActive && "-translate-y-0.5 scale-110"
                  )}
                />
                {to === "/review" && dueCount > 0 && (
                  <span className="absolute -right-1.5 -top-1 h-2 w-2 rounded-full bg-accent" />
                )}
              </span>
              <span className="truncate">{label}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
