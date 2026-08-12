import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button, Card } from "./ui";
import { IconAlert, IconRefresh } from "./icons";

interface State {
  error: Error | null;
}

/**
 * Catches render-time crashes so one broken page cannot blank the whole app.
 * React has no hook equivalent, so this stays a class component.
 */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Giao diện gặp lỗi:", error, info.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    return (
      <Card className="mx-auto mt-10 flex max-w-lg flex-col items-center gap-3 px-6 py-14 text-center">
        <span className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-danger-soft text-danger">
          <IconAlert className="h-6 w-6" />
        </span>
        <h1 className="font-display text-xl font-bold text-ink">Trang này gặp sự cố</h1>
        <p className="max-w-sm text-sm text-ink-soft">
          Tiến độ học của bạn vẫn an toàn. Hãy tải lại trang để tiếp tục.
        </p>
        <p className="max-w-sm break-words rounded-lg bg-surface-2 px-3 py-2 font-mono text-[11px] text-ink-faint">
          {error.message}
        </p>
        <Button onClick={() => window.location.reload()}>
          <IconRefresh className="h-4 w-4" /> Tải lại ứng dụng
        </Button>
      </Card>
    );
  }
}
