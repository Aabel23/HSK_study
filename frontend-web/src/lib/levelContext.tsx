import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { HskLevel } from "./types";

type LevelValue = HskLevel | "all";

const LevelContext = createContext<{ level: LevelValue; setLevel: (level: LevelValue) => void }>({
  level: "all",
  setLevel: () => {},
});

export function LevelProvider({ children }: { children: ReactNode }) {
  const [level, setLevel] = useState<LevelValue>(() => {
    const stored = localStorage.getItem("hsk-level");
    return (stored as LevelValue) || "all";
  });

  useEffect(() => {
    localStorage.setItem("hsk-level", level);
  }, [level]);

  return <LevelContext.Provider value={{ level, setLevel }}>{children}</LevelContext.Provider>;
}

export function useLevel() {
  return useContext(LevelContext);
}

export const LEVEL_LABELS: Record<LevelValue, string> = {
  all: "Tất cả",
  "1": "HSK 1",
  "2": "HSK 2",
  "3": "HSK 3",
  "4": "HSK 4",
  "5": "HSK 5",
  "6": "HSK 6",
  "7-9": "HSK 7-9",
};
