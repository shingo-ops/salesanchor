/**
 * useFitTableZoom — 表を枠の幅に合わせて縮める hook（DataTable fitToWidth）
 *
 * 倍率は ref の setProperty で `--comp-table-fit-zoom` に渡す（style 属性は使わない）。
 * enabled が偽・ref が null・matchMedia が無い環境では何もしない。
 */
import { useEffect, type RefObject } from "react";
import { BREAKPOINTS } from "../constants/breakpoints";
import { initialZoom, refineZoom } from "../lib/tableFitZoom";

const ZOOM_VAR = "--comp-table-fit-zoom";

export function useFitTableZoom(
  enabled: boolean,
  frameRef: RefObject<HTMLElement | null>,
  cardRef: RefObject<HTMLElement | null>,
  scrollRef: RefObject<HTMLElement | null>,
  /** 変わると計算し直す値（行データなど） */
  dep: unknown,
): void {
  useEffect(() => {
    if (!enabled) return undefined;
    if (typeof window.matchMedia !== "function") return undefined;
    const frame = frameRef.current;
    const card = cardRef.current;
    const scroll = scrollRef.current;
    if (!frame || !card || !scroll) return undefined;

    const mql = window.matchMedia(`(min-width: ${BREAKPOINTS.TABLET_MIN}px)`);
    let raf = 0;

    const compute = () => {
      raf = 0;
      if (!mql.matches) {
        card.style.removeProperty(ZOOM_VAR);
        return;
      }
      card.style.removeProperty(ZOOM_VAR);
      const cs = window.getComputedStyle(scroll);
      const border = (parseFloat(cs.borderLeftWidth) || 0) + (parseFloat(cs.borderRightWidth) || 0);
      const natural = scroll.scrollWidth + border;
      const z = initialZoom(frame.clientWidth, natural);
      if (z >= 1) return;
      card.style.setProperty(ZOOM_VAR, String(z));
      const refined = refineZoom(z, (zz) => {
        card.style.setProperty(ZOOM_VAR, String(zz));
        return scroll.scrollWidth > scroll.clientWidth;
      });
      card.style.setProperty(ZOOM_VAR, String(refined));
    };

    const schedule = () => {
      if (raf) return;
      raf = window.requestAnimationFrame(compute);
    };

    schedule();
    let ro: ResizeObserver | null = null;
    if (typeof ResizeObserver === "function") {
      ro = new ResizeObserver(schedule);
      ro.observe(frame);
    } else {
      window.addEventListener("resize", schedule);
    }
    mql.addEventListener("change", schedule);

    return () => {
      if (raf) window.cancelAnimationFrame(raf);
      ro?.disconnect();
      window.removeEventListener("resize", schedule);
      mql.removeEventListener("change", schedule);
      card.style.removeProperty(ZOOM_VAR);
    };
  }, [enabled, frameRef, cardRef, scrollRef, dep]);
}
