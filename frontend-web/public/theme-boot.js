/*
 * Applies the stored theme before first paint so the app never flashes the
 * wrong background while the React bundle loads.
 *
 * Kept as a separate file rather than an inline <script> so the app can ship a
 * strict `script-src 'self'` Content-Security-Policy with no 'unsafe-inline'.
 * Loaded synchronously from <head>, so it runs before the body renders.
 */
(function () {
  try {
    var stored = JSON.parse(localStorage.getItem("hsk-settings") || "{}");
    var theme = stored.theme === "light" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.style.colorScheme = theme;
    if (stored.reduced_motion) {
      document.documentElement.setAttribute("data-reduced-motion", "true");
    }
  } catch (error) {
    document.documentElement.setAttribute("data-theme", "dark");
  }
})();
