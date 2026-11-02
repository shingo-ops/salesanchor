/**
 * useHideMobileTabbar — スマホで画面ごとに下のメニュー（.mobile-tabbar）を隠す
 *
 * 目的: 受信箱で会話を開いている間だけ、下のメニューを隠す（WhatsApp と同じ動き）。
 * 出どころ: docs/handoff/inbox-deal-ui/thread-a/card-a2.md §13・ADR-140 追記（PO 2026-11-02）。
 *
 * 仕組み: MobileShell が MobileTabbarContext に「隠す状態を変える関数」を渡す。
 * 子の画面はこのフックで頼む。画面が外れる（unmount）と false に戻す。
 * Provider が無い所（DesktopShell）では何もしない。
 */

import { createContext, useContext, useEffect } from "react";

export const MobileTabbarContext = createContext<((hidden: boolean) => void) | null>(null);

export function useHideMobileTabbar(hidden: boolean): void {
  const set = useContext(MobileTabbarContext);
  useEffect(() => {
    if (!set) return;
    set(hidden);
    return () => set(false);
  }, [set, hidden]);
}
