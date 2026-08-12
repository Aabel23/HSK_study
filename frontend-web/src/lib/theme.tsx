/**
 * Theme access.
 *
 * Preferences moved into {@link SettingsProvider} so they persist in the
 * database alongside progress. This module stays as the theme-shaped view onto
 * that store, keeping the original `ThemeProvider` / `useTheme` API intact for
 * the pages that already import it.
 */
import { SettingsProvider, useSettings } from "./settings";

export const ThemeProvider = SettingsProvider;

export function useTheme() {
  const { settings, update } = useSettings();
  return {
    theme: settings.theme,
    toggle: () => update({ theme: settings.theme === "dark" ? "light" : "dark" }),
  };
}
