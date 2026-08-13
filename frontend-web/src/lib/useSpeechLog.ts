import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Live speech-to-text log of a spoken answer, in Chinese.
 *
 * Runs alongside the recorder: the clip is what the learner listens back to,
 * this is the text that gets graded. Sending the transcript rather than several
 * megabytes of audio makes grading fast and cheap, and it lets the learner see
 * immediately whether they were understood at all.
 *
 * Built on the Web Speech API, which only Chromium-based browsers implement, so
 * everything here degrades to `supported: false` and the exam falls back to the
 * audio clip alone.
 */

/** Minimal shape of the vendor-prefixed API; the DOM lib does not declare it. */
interface SpeechRecognitionLike extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
}

interface SpeechRecognitionEventLike {
  resultIndex: number;
  results: ArrayLike<{ 0: { transcript: string }; isFinal: boolean; length: number }>;
}

type RecognitionConstructor = new () => SpeechRecognitionLike;

function getRecognitionConstructor(): RecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  const candidate = window as unknown as {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  };
  return candidate.SpeechRecognition ?? candidate.webkitSpeechRecognition ?? null;
}

export function useSpeechLog(lang = "zh-CN") {
  const [supported] = useState(() => Boolean(getRecognitionConstructor()));
  const [finalText, setFinalText] = useState("");
  const [interimText, setInterimText] = useState("");
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  // The callbacks fire outside React's render cycle, so the accumulated text is
  // also kept in a ref — `stop()` must be able to read it synchronously.
  const finalRef = useRef("");
  const wantedRef = useRef(false);

  const start = useCallback(() => {
    const Recognition = getRecognitionConstructor();
    if (!Recognition) {
      setError("Trình duyệt này không nhận dạng được giọng nói. Hãy dùng Chrome hoặc Edge.");
      return;
    }
    recognitionRef.current?.abort();
    finalRef.current = "";
    setFinalText("");
    setInterimText("");
    setError(null);
    wantedRef.current = true;

    const recognition = new Recognition();
    recognition.lang = lang;
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
      let interim = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (result.isFinal) finalRef.current += result[0].transcript;
        else interim += result[0].transcript;
      }
      setFinalText(finalRef.current);
      setInterimText(interim);
    };
    recognition.onerror = (event) => {
      if (event.error === "no-speech") return; // A pause is not a failure.
      if (event.error === "aborted") return;
      setError(
        event.error === "not-allowed"
          ? "Micro bị chặn nên không ghi được lời nói thành chữ."
          : "Không nhận dạng được giọng nói. Bài thi vẫn tiếp tục bình thường."
      );
    };
    recognition.onend = () => {
      // Chrome stops on its own after a silence; restart while the learner is
      // still answering so a pause mid-sentence does not truncate the log.
      if (wantedRef.current) {
        try {
          recognition.start();
          return;
        } catch {
          // Already restarting; fall through to reporting that it stopped.
        }
      }
      setListening(false);
    };

    try {
      recognition.start();
      recognitionRef.current = recognition;
      setListening(true);
    } catch {
      setError("Không khởi động được phần nhận dạng giọng nói.");
    }
  }, [lang]);

  /** Stop listening and return everything heard so far. */
  const stop = useCallback((): string => {
    wantedRef.current = false;
    recognitionRef.current?.stop();
    setListening(false);
    setInterimText("");
    return finalRef.current.trim();
  }, []);

  const reset = useCallback(() => {
    wantedRef.current = false;
    recognitionRef.current?.abort();
    recognitionRef.current = null;
    finalRef.current = "";
    setFinalText("");
    setInterimText("");
    setListening(false);
    setError(null);
  }, []);

  useEffect(() => {
    return () => {
      wantedRef.current = false;
      recognitionRef.current?.abort();
    };
  }, []);

  return {
    supported,
    listening,
    /** Text confirmed by the recogniser. */
    text: finalText,
    /** Words still being revised; shown greyed out so the log looks live. */
    interim: interimText,
    error,
    start,
    stop,
    reset,
  };
}
