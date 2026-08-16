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
 * The contract, which every practice screen follows:
 *
 * | Key        | Means                                                    |
 * | ---------- | -------------------------------------------------------- |
 * | `Space`    | **Confirm** — reveal, check, submit what is on screen     |
 * | `Enter`    | **Next** — move on to the following item                  |
 * | `1`–`9`    | Pick the nth choice — a rating, or an answer button       |
 * | `Escape`   | Leave: close, or end the session early                    |
 *
 * Space and Enter used to be synonyms for "the one obvious next step", which
 * fell apart on any screen with two steps: on Luyện câu the same key had to
 * mean both "check my arrangement" and "give me the next sentence", so it
 * meant whichever the page happened to wire it to. Splitting them gives the
 * learner one rhythm that holds everywhere — Space to commit, Enter to go on.
 *
 * Where a screen only has one of the two steps, the other key falls through to
 * it rather than doing nothing: a learner who reaches for Enter on a flashcard
 * still flips it. So the split is strict where it matters and forgiving where
 * it does not.
 *
 * Anything that would be a second meaning for one of these keys belongs on a
 * different key, because the value here is that Space always does the same
 * kind of thing.
 */
export interface Shortcuts {
  /** Space. Commit what is on screen: reveal, check, submit. */
  onConfirm?: () => void;
  /** Enter. Move to the next item. */
  onNext?: () => void;
  /**
   * Both keys, for a screen whose only step is "carry on".
   *
   * Prefer `onConfirm`/`onNext`. This exists for screens that genuinely have
   * one action, so they do not have to pass the same function twice.
   */
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

export function useShortcuts({
  onConfirm,
  onNext,
  onAdvance,
  onPick,
  onExit,
  enabled = true,
}: Shortcuts): void {
  // Held in a ref so a handler that closes over fresh state does not have to
  // re-bind the listener on every render — re-binding mid-keypress is how a
  // shortcut ends up firing twice.
  const handlers = useRef<Shortcuts>({});
  handlers.current = { onConfirm, onNext, onAdvance, onPick, onExit };

  useEffect(() => {
    if (!enabled) return;
    const onKey = (event: KeyboardEvent) => {
      if (isTyping(event.target)) return;
      // A modifier means the learner is talking to the browser, not the page.
      if (event.ctrlKey || event.metaKey || event.altKey) return;

      const current = handlers.current;
      // Space prefers confirm, Enter prefers next, and each falls back to the
      // other so neither key is ever dead on a one-step screen.
      const confirm = current.onConfirm ?? current.onAdvance ?? current.onNext;
      const next = current.onNext ?? current.onAdvance ?? current.onConfirm;

      if (event.key === " ") {
        if (!confirm) return;
        // Space scrolls the page by default, which would move the card the
        // learner is looking at out from under them.
        event.preventDefault();
        confirm();
        return;
      }
      if (event.key === "Enter") {
        if (!next) return;
        event.preventDefault();
        next();
        return;
      }
      if (event.key === "Escape") {
        if (!current.onExit) return;
        event.preventDefault();
        current.onExit();
        return;
      }
      if (current.onPick && /^[1-9]$/.test(event.key)) {
        event.preventDefault();
        current.onPick(Number(event.key));
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [enabled]);
}
