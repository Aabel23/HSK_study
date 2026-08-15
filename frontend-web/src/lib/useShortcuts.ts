import { useEffect, useRef } from "react";

/**
 * One keyboard contract for every practice screen.
 *
 * Three pages had grown their own copy of the same keydown listener, each with
 * its own copy of the "don't hijack a text field" guard, and each having picked
 * slightly different keys. The result was that Space advanced a flashcard but
 * did nothing on a quiz, and a learner had to relearn the keyboard on every
 * screen.
 *
 * The contract, which every practice screen should follow:
 *
 * | Key        | Means                                                    |
 * | ---------- | -------------------------------------------------------- |
 * | `Space`    | The one obvious next step: reveal, check, continue        |
 * | `Enter`    | Same as Space, for people who reach for it instead        |
 * | `1`–`9`    | Pick the nth choice — a rating, or an answer button       |
 * | `Escape`   | Leave: close, or end the session early                    |
 *
 * Anything that would be a second meaning for one of these keys belongs on a
 * different key, because the value here is that Space always does the same
 * kind of thing.
 */
export interface Shortcuts {
  /** Space and Enter. The screen's primary action. */
  onAdvance?: () => void;
  /** A number key, 1-indexed as printed on the keyboard. */
  onPick?: (choice: number) => void;
  /** Escape. */
  onExit?: () => void;
  /** Set false while a session is not running, to unbind everything. */
  enabled?: boolean;
}

/** True when the keystroke belongs to whatever the learner is typing into. */
function isTyping(target: EventTarget | null): boolean {
  const element = target as HTMLElement | null;
  return (
    element?.tagName === "INPUT" ||
    element?.tagName === "TEXTAREA" ||
    Boolean(element?.isContentEditable)
  );
}

export function useShortcuts({ onAdvance, onPick, onExit, enabled = true }: Shortcuts): void {
  // Held in a ref so a handler that closes over fresh state does not have to
  // re-bind the listener on every render — re-binding mid-keypress is how a
  // shortcut ends up firing twice.
  const handlers = useRef<Shortcuts>({});
  handlers.current = { onAdvance, onPick, onExit };

  useEffect(() => {
    if (!enabled) return;
    const onKey = (event: KeyboardEvent) => {
      if (isTyping(event.target)) return;
      // A modifier means the learner is talking to the browser, not the page.
      if (event.ctrlKey || event.metaKey || event.altKey) return;

      const { onAdvance: advance, onPick: pick, onExit: exit } = handlers.current;

      if (event.key === " " || event.key === "Enter") {
        if (!advance) return;
        // Space scrolls the page by default, which would move the card the
        // learner is looking at out from under them.
        event.preventDefault();
        advance();
        return;
      }
      if (event.key === "Escape") {
        if (!exit) return;
        event.preventDefault();
        exit();
        return;
      }
      if (pick && /^[1-9]$/.test(event.key)) {
        event.preventDefault();
        pick(Number(event.key));
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [enabled]);
}
