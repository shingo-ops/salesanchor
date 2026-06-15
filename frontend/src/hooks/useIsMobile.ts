/**
 * useIsMobile — JS ブレークポイント判定 hook
 *
 * PR-R2-A で新規追加。PR-R2-C で App.tsx が利用する。
 * window.matchMedia (max-width: MOBILE_MAX) で判定。
 * SSR 将来対応時は再設計が必要（現時点は CSR のみ）。
 *
 * 参照: docs/handoff/mobile-shell-pr-r2a/design.md
 * ADR: ADR-137 §採用アーキテクチャ
 */

import { useState, useEffect } from "react";
import { BREAKPOINTS } from "../constants/breakpoints";

export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(
    () => window.matchMedia(`(max-width: ${BREAKPOINTS.MOBILE_MAX}px)`).matches,
  );

  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${BREAKPOINTS.MOBILE_MAX}px)`);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  return isMobile;
}
