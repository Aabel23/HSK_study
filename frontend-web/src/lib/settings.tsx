import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "./api";
import type { AppSettings } from "./types";

const STORAGE_KEY = "hsk-settings";

export const DEFAULT_SETTINGS: AppSettings = {
  daily_goal: 20,
  new_words_per_day: 10,
  session_size: 20,
  theme: "dark",
  audio_voice: "female",
  autoplay_audio: true,
  show_pinyin: true,
  show_traditional: false,
  reduced_motion: false,
  sound_effects: true,
  preferred_level: "all",
};

interface SettingsApi {
  settings: AppSettings;
  update: (patch: Partial<AppSettings>) => Promise<void>;
  reset: () => Promise<void>;
  ready: boolean;
}

const SettingsContext = createContext<SettingsApi>({
  settings: DEFAULT_SETTINGS,
  update: async () => {},
  reset: async () => {},
  ready: false,
});

/** Read the last known settings synchronously so the first paint is not themed wrong. */
function readCache(): AppSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    return { ...DEFAULT_SETTINGS, ...(JSON.parse(raw) as Partial<AppSettings>) };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function applyToDocument(settings: AppSettings) {
  const root = document.documentElement;
  root.setAttribute("data-theme", settings.theme);
  root.setAttribute("data-reduced-motion", String(settings.reduced_motion));
  root.style.colorScheme = settings.theme;
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<AppSettings>(readCache);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    applyToDocument(settings);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch {
      // A full or restricted storage quota must not break the app.
    }
  }, [settings]);

  // The database is the source of truth across devices/reinstalls; the cache
  // only exists to avoid a themed flash before this resolves.
  useEffect(() => {
    let cancelled = false;
    api.settings
      .get()
      .then(({ settings: serverSettings }) => {
        if (!cancelled) setSettings((current) => ({ ...current, ...serverSettings }));
      })
      .catch(() => {
        /* offline or first run: keep the cached values */
      })
      .finally(() => {
        if (!cancelled) setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const update = useCallback(async (patch: Partial<AppSettings>) => {
    // Applied optimistically so toggles feel instant; the server is the
    // authority, so its response wins if it normalises a value.
    setSettings((current) => ({ ...current, ...patch }));
    try {
      const { settings: saved } = await api.settings.update(patch);
      setSettings((current) => ({ ...current, ...saved }));
    } catch {
      /* keep the optimistic value; it is re-synced on next load */
    }
  }, []);

  const reset = useCallback(async () => {
    const { settings: saved } = await api.settings.reset();
    setSettings(saved);
  }, []);

  const value = useMemo<SettingsApi>(
    () => ({ settings, update, reset, ready }),
    [settings, update, reset, ready]
  );

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings() {
  return useContext(SettingsContext);
}
