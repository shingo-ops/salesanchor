import { useCallback, useEffect, useRef, useState } from "react";
import {
  getImportItems,
  getImportProgress,
  type ImportItemFilter,
  type ImportItems,
  type ImportProgress,
} from "./importWorkflowApi";

export function useImportWorkflow(
  importJobId: string | null,
  filter: ImportItemFilter,
  offset: number,
  limit = 25,
) {
  const [progress, setProgress] = useState<ImportProgress | null>(null);
  const [items, setItems] = useState<ImportItems | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const key = importJobId ? `${importJobId}:${filter}:${offset}:${limit}` : null;
  const [dataKey, setDataKey] = useState<string | null>(null);
  const loadRef = useRef<(() => void) | null>(null);
  const refresh = useCallback(() => loadRef.current?.(), []);
  useEffect(() => {
    if (!importJobId) { setProgress(null); setItems(null); setError(null); setLoading(false); loadRef.current=null; return; }
    let mounted = true;
    let inflight = false;
    let reloadPending = false;
    let visibilityGeneration = 0;
    const load = async () => {
      if (!mounted || inflight || document.visibilityState === "hidden") return;
      inflight = true;
      const startedGeneration = visibilityGeneration;
      setLoading(true);
      try {
        const [progressResult, itemsResult] = await Promise.allSettled([
          getImportProgress(importJobId),
          getImportItems(importJobId, limit, offset, filter),
        ]);
        if (mounted && document.visibilityState === "visible" && startedGeneration === visibilityGeneration && progressResult.status === "fulfilled" && itemsResult.status === "fulfilled") {
          setProgress(progressResult.value); setItems(itemsResult.value); setDataKey(key);
          setError(null); setErrorKey(null);
        } else if (mounted && document.visibilityState === "visible" && startedGeneration === visibilityGeneration && (progressResult.status === "rejected" || itemsResult.status === "rejected")) {
          const cause = progressResult.status === "rejected" ? progressResult.reason : (itemsResult as PromiseRejectedResult).reason;
          setError(cause instanceof Error ? cause.message : String(cause)); setErrorKey(key);
        }
      } finally {
        if (mounted) setLoading(false);
        inflight = false;
        if (mounted && reloadPending && document.visibilityState === "visible") { reloadPending = false; void load(); }
      }
    };
    loadRef.current = () => { void load(); };
    const visible = () => {
      if (document.visibilityState === "hidden") { visibilityGeneration += 1; return; }
      if (inflight) { reloadPending = true; return; }
      if (document.visibilityState === "visible") void load();
    };
    void load();
    const interval = window.setInterval(() => void load(), 5000);
    document.addEventListener("visibilitychange", visible);
    return () => {
      mounted = false;
      loadRef.current = null;
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", visible);
    };
  }, [importJobId, filter, offset, limit, key]);
  const current = dataKey === key;
  return {
    progress: current ? progress : null,
    items: current ? items : null,
    error: errorKey === key ? error : null,
    loading,
    refresh,
    lastAsOf: current ? progress?.as_of ?? items?.as_of ?? null : null,
  };
}
