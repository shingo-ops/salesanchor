/**
 * テナント単位フィーチャーフラグによる表示制御コンポーネント。
 * 指定された feature が有効なテナントでのみ children を描画する。
 *
 * 使用例:
 *   <FeatureGate feature="inventory_v2">
 *     <NewInventoryPanel />
 *   </FeatureGate>
 *
 * 変更履歴:
 *   2026-06-27: 初版作成（テナント単位フィーチャーフラグ MVP）
 */

import type { ReactNode } from "react";
import { useFeatures } from "../hooks/useFeatures";

interface FeatureGateProps {
  feature: string;
  children: ReactNode;
}

export function FeatureGate({ feature, children }: FeatureGateProps) {
  const { isEnabled, loading } = useFeatures();

  if (loading || !isEnabled(feature)) {
    return null;
  }

  return <>{children}</>;
}
