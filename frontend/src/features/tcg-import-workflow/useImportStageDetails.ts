import { useCallback, useEffect, useRef, useState } from "react";
import { getImportExtractionJobs, getImportMessages, type Coverage, type ExtractionJob, type ImportMessage } from "./importWorkflowApi";

export type ImportStageDetailMode = "messages" | "errors" | null;
interface State {
  key: string | null;
  rows: (ImportMessage | ExtractionJob)[] | null;
  total: number | null;
  coverage: Coverage | null;
  reason: string | null;
  asOf: string | null;
  error: string | null;
  loading: boolean;
}
const empty = (key: string | null): State => ({ key, rows: null, total: null, coverage: null, reason: null, asOf: null, error: null, loading: false });

export function useImportStageDetails(importJobId: string | null, mode: ImportStageDetailMode, offset: number, limit: number) {
  const key = importJobId && mode ? `${importJobId}:${mode}:${offset}:${limit}` : null;
  const generation = useRef(0);
  const [reload, setReload] = useState(0);
  const [state, setState] = useState<State>(empty(null));
  const refresh = useCallback(() => setReload(value => value + 1), []);
  useEffect(() => {
    let active = true;
    const load = () => {
      const current = ++generation.current;
      if (!key || !importJobId || !mode) { setState(empty(key)); return; }
      if (document.visibilityState === "hidden") return;
      setState(previous => ({ ...(previous.key === key ? previous : empty(key)), loading: true, error: null }));
      const request = mode === "messages"
        ? getImportMessages(importJobId, limit, offset).then(v => ({ rows: v.messages, total: v.total, coverage: v.coverage, asOf: v.as_of, reason: v.reason }))
        : getImportExtractionJobs(importJobId, limit, offset, "error").then(v => ({ rows: v.jobs, total: v.total, coverage: v.coverage, asOf: v.as_of, reason: v.reason }));
      void request.then(value => {
        if (active && current === generation.current) setState({ key, ...value, loading: false, error: null });
      }).catch(reason => {
        if (active && current === generation.current) setState(previous => ({ ...(previous.key === key ? previous : empty(key)), loading: false, error: reason instanceof Error ? reason.message : String(reason) }));
      });
    };
    const visibility = () => { if (document.visibilityState === "hidden") generation.current += 1; else load(); };
    load();
    document.addEventListener("visibilitychange", visibility);
    return () => { active = false; generation.current += 1; document.removeEventListener("visibilitychange", visibility); };
  }, [key, importJobId, mode, offset, limit, reload]);
  const current = state.key === key;
  const visible = current ? state : empty(key);
  return { ...visible, loading: key !== null && (!current || visible.loading), stale: current && state.asOf !== null && state.error !== null, refresh };
}
