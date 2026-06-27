/**
 * テナント単位フィーチャーフラグを参照するフック。
 * /me/permissions レスポンスの enabled_features を使用する。
 * usePermissions と同じデータソース（/me/permissions）を利用するため
 * 追加の API コールは発生しない。
 *
 * 変更履歴:
 *   2026-06-27: 初版作成（テナント単位フィーチャーフラグ MVP）
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";

interface PermissionsWithFeaturesResponse {
  permissions: string[];
  enabled_features?: string[];
}

export function useFeatures() {
  const [features, setFeatures] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .get<PermissionsWithFeaturesResponse>("/me/permissions")
      .then((data) => {
        setFeatures(new Set(data.enabled_features ?? []));
      })
      .catch(() => {
        // フィーチャーフラグ取得失敗時は空セット（全機能無効=安全側に倒す）
        setFeatures(new Set());
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const isEnabled = useCallback(
    (featureKey: string) => features.has(featureKey),
    [features],
  );

  return useMemo(
    () => ({ features, loading, isEnabled }),
    [features, loading, isEnabled],
  );
}
