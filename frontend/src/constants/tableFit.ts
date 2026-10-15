/**
 * 表を幅に合わせて縮める計算の定数（DataTable fitToWidth）
 * GAS 在庫一覧（H:1506-1569）と同じ値。
 */

/** 縮小の微調整を繰り返す最大回数 */
export const MAX_ZOOM_ADJUST_STEPS = 200;

/** 微調整1回あたりに下げる倍率 */
export const ZOOM_ADJUST_DECREMENT = 0.001;

/** 倍率の丸め精度（小数第3位） */
export const ZOOM_PRECISION = 1000;
