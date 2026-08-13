import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Microphone recorder for the HSKK mock exam.
 *
 * Hearing your own answer back is the whole point of practising a spoken test,
 * so the clip stays in the browser as an object URL and is never uploaded — the
 * server only ever receives the self-rating. Recording is optional: on a device
 * or context without microphone access (`getUserMedia` needs HTTPS or
 * localhost) the exam still runs, the learner just speaks without playback.
 */
export function useRecorder() {
  const [supported] = useState(
    () => typeof navigator !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia) && typeof MediaRecorder !== "undefined"
  );
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [clipUrl, setClipUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const timerRef = useRef<number | null>(null);
  const clipUrlRef = useRef<string | null>(null);

  const revokeClip = useCallback(() => {
    if (clipUrlRef.current) URL.revokeObjectURL(clipUrlRef.current);
    clipUrlRef.current = null;
    setClipUrl(null);
  }, []);

  const stopTimer = useCallback(() => {
    if (timerRef.current !== null) window.clearInterval(timerRef.current);
    timerRef.current = null;
  }, []);

  const stop = useCallback(() => {
    stopTimer();
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
    setRecording(false);
  }, [stopTimer]);

  const start = useCallback(async () => {
    if (!supported) {
      setError("Trình duyệt này không cho phép ghi âm.");
      return;
    }
    revokeClip();
    setError(null);
    setSeconds(0);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        // Releasing the tracks is what turns the browser's recording indicator
        // off; leaving them open reads as the app still listening.
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        const url = URL.createObjectURL(blob);
        clipUrlRef.current = url;
        setClipUrl(url);
      };
      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
      timerRef.current = window.setInterval(() => setSeconds((value) => value + 1), 1000);
    } catch {
      setError("Không truy cập được micro. Hãy cho phép quyền ghi âm rồi thử lại.");
    }
  }, [revokeClip, supported]);

  /** Clear the previous answer before moving to the next question. */
  const reset = useCallback(() => {
    stop();
    revokeClip();
    setSeconds(0);
    setError(null);
  }, [revokeClip, stop]);

  useEffect(() => {
    return () => {
      stopTimer();
      const recorder = recorderRef.current;
      if (recorder && recorder.state !== "inactive") recorder.stop();
      if (clipUrlRef.current) URL.revokeObjectURL(clipUrlRef.current);
    };
  }, [stopTimer]);

  return { supported, recording, seconds, clipUrl, error, start, stop, reset };
}
