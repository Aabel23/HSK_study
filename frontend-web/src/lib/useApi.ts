import { useCallback, useEffect, useRef, useState } from "react";

interface AsyncState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

/**
 * Fetch-on-mount helper with loading/error state and a manual `reload`.
 *
 * A generation counter guards against out-of-order responses: only the newest
 * request is allowed to write state, so a slow first call cannot overwrite a
 * fast second one.
 */
export function useApi<T>(
  loader: () => Promise<T>,
  deps: unknown[] = []
): AsyncState<T> & { reload: () => void; setData: (value: T) => void } {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    error: null,
    loading: true,
  });
  const generation = useRef(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const run = useCallback(() => {
    const current = ++generation.current;
    setState((previous) => ({ ...previous, loading: true, error: null }));
    loaderRef.current()
      .then((data) => {
        if (generation.current === current) setState({ data, error: null, loading: false });
      })
      .catch((error: unknown) => {
        if (generation.current !== current) return;
        const message =
          error instanceof Error ? error.message : "Không thể tải dữ liệu. Vui lòng thử lại.";
        setState((previous) => ({ data: previous.data, error: message, loading: false }));
      });
  }, []);

  useEffect(() => {
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  const setData = useCallback((value: T) => {
    setState((previous) => ({ ...previous, data: value }));
  }, []);

  return { ...state, reload: run, setData };
}
