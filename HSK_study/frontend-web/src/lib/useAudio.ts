import { useCallback, useRef, useState } from "react";
import { audioUrl } from "./api";

let sharedAudio: HTMLAudioElement | null = null;

function getSharedAudio(): HTMLAudioElement {
  if (!sharedAudio) sharedAudio = new Audio();
  return sharedAudio;
}

export type PlaybackRate = 0.5 | 0.75 | 1 | 1.25;

export const PLAYBACK_RATES: PlaybackRate[] = [0.5, 0.75, 1, 1.25];

interface PlayOptions {
  voice?: "female" | "male";
  rate?: PlaybackRate;
}

/**
 * Shared audio player.
 *
 * A single <audio> element is reused so starting a new clip always stops the
 * previous one, and a generation counter makes sure a slow request cannot
 * clear the state of a newer one. `playCount` is exposed because dictation
 * grades how many replays a learner needed.
 */
export function usePlayAudio() {
  const [playingText, setPlayingText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [playCount, setPlayCount] = useState(0);
  const requestId = useRef(0);

  const play = useCallback((text: string, options: PlayOptions = {}) => {
    if (!text.trim()) return;
    const { voice = "female", rate = 1 } = options;
    const id = ++requestId.current;
    const audio = getSharedAudio();
    setError(null);
    setPlayingText(text);
    setPlayCount((count) => count + 1);
    audio.src = audioUrl(text, voice);
    // Slower playback is the single most useful listening aid; the rate has to
    // be set after src because loading resets it in some browsers.
    audio.playbackRate = rate;
    audio.onended = () => {
      if (requestId.current === id) setPlayingText(null);
    };
    audio.onerror = () => {
      if (requestId.current === id) {
        setPlayingText(null);
        setError("Không thể phát âm thanh. Cần Internet cho lần phát đầu tiên.");
      }
    };
    audio.play().catch(() => {
      if (requestId.current === id) {
        setPlayingText(null);
        setError("Không thể phát âm thanh.");
      }
    });
  }, []);

  const stop = useCallback(() => {
    const audio = getSharedAudio();
    audio.pause();
    setPlayingText(null);
  }, []);

  const resetCount = useCallback(() => setPlayCount(0), []);

  return { play, stop, playingText, error, playCount, resetCount };
}
