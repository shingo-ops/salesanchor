/**
 * tableFitZoom — 表の縮小倍率を求める純関数（GAS 在庫一覧 H:1506-1569 と同じ計算）
 */
import {
  MAX_ZOOM_ADJUST_STEPS,
  ZOOM_ADJUST_DECREMENT,
  ZOOM_PRECISION,
} from "../constants/tableFit";

/** 枠の幅と表の自然な幅から、最初の倍率（最大 1）を求める */
export function initialZoom(frameWidth: number, naturalWidth: number): number {
  if (!(naturalWidth > 0)) return 1;
  return Math.floor(Math.min(1, frameWidth / naturalWidth) * ZOOM_PRECISION) / ZOOM_PRECISION;
}

/** はみ出している間、倍率を ZOOM_ADJUST_DECREMENT ずつ下げる（最大 MAX_ZOOM_ADJUST_STEPS 回） */
export function refineZoom(z: number, overflows: (z: number) => boolean): number {
  let zoom = z;
  let steps = 0;
  while (steps < MAX_ZOOM_ADJUST_STEPS && zoom > ZOOM_ADJUST_DECREMENT && overflows(zoom)) {
    zoom = Math.round((zoom - ZOOM_ADJUST_DECREMENT) * ZOOM_PRECISION) / ZOOM_PRECISION;
    steps += 1;
  }
  return zoom;
}
