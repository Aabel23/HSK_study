import { Suspense, lazy } from "react";
import { HashRouter, Route, Routes } from "react-router-dom";
import { Shell } from "./components/Shell";
import { SettingsProvider } from "./lib/settings";
import { LevelProvider } from "./lib/levelContext";
import { ToastProvider } from "./lib/toast";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { PageSkeleton } from "./components/ui";
import Dashboard from "./pages/Dashboard";

// Routes are split so the first paint only pays for the dashboard. The heavy
// dependencies (charts, the stroke-order canvas) load with the page that needs
// them instead of blocking startup.
const Review = lazy(() => import("./pages/Review"));
const Vocabulary = lazy(() => import("./pages/Vocabulary"));
const Flashcards = lazy(() => import("./pages/Flashcards"));
const Matching = lazy(() => import("./pages/Matching"));
const Sentences = lazy(() => import("./pages/Sentences"));
const Listening = lazy(() => import("./pages/Listening"));
const Quiz = lazy(() => import("./pages/Quiz"));
const Typing = lazy(() => import("./pages/Typing"));
const Hskk = lazy(() => import("./pages/Hskk"));
const Writing = lazy(() => import("./pages/Writing"));
const Progress = lazy(() => import("./pages/Progress"));
const Achievements = lazy(() => import("./pages/Achievements"));
const Settings = lazy(() => import("./pages/Settings"));
const Donate = lazy(() => import("./pages/Donate"));
const NotFound = lazy(() => import("./pages/NotFound"));

export default function App() {
  return (
    <SettingsProvider>
      <ToastProvider>
        <LevelProvider>
          <HashRouter>
            <Shell>
              <ErrorBoundary>
                <Suspense fallback={<PageSkeleton />}>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/review" element={<Review />} />
                    <Route path="/vocabulary" element={<Vocabulary />} />
                    <Route path="/flashcards" element={<Flashcards />} />
                    <Route path="/matching" element={<Matching />} />
                    <Route path="/sentences" element={<Sentences />} />
                    <Route path="/listening" element={<Listening />} />
                    <Route path="/quiz" element={<Quiz />} />
                    <Route path="/typing" element={<Typing />} />
                    <Route path="/hskk" element={<Hskk />} />
                    <Route path="/writing" element={<Writing />} />
                    <Route path="/progress" element={<Progress />} />
                    <Route path="/achievements" element={<Achievements />} />
                    <Route path="/settings" element={<Settings />} />
                    <Route path="/donate" element={<Donate />} />
                    <Route path="*" element={<NotFound />} />
                  </Routes>
                </Suspense>
              </ErrorBoundary>
            </Shell>
          </HashRouter>
        </LevelProvider>
      </ToastProvider>
    </SettingsProvider>
  );
}
