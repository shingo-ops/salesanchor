/**
 * 現在のユーザーの有効権限をAPIから取得し、キャッシュするフック。
 * UIのメニュー・ボタン表示制御に使用する。
 *
 * 変更履歴:
 *   2026-04-16: 初版作成（Phase 1）
 *   2026-11-03: is_tenant_admin を返す（予定の画面の Google カレンダー連携ボタン用）。
 *   2026-11-06: is_tenant_owner を返す（会社のオーナーのログイン許可の画面と鈴・ADR-1063）。
 *   2026-11-01: 写しの置き場（useApiQuery）に載せた（ADR-1054）。戻った時は前の権限を先に出し、裏で取り直す。
 */

import { useCallback, useMemo } from "react";
import { useApiQuery } from "../lib/query/apiQuery";

interface PermissionsResponse {
  permissions: string[];
  is_tenant_admin?: boolean;
  is_tenant_owner?: boolean;
}

export function usePermissions() {
  const { data, isPending, error: queryError, refetch } = useApiQuery<PermissionsResponse>("/me/permissions");

  const permissions = useMemo(() => new Set(data?.permissions ?? []), [data]);
  const isTenantAdmin = data?.is_tenant_admin === true;
  const isTenantOwner = data?.is_tenant_owner === true;
  const loading = isPending;

  let error: string | null = null;
  if (queryError) {
    // eslint-disable-next-line local/no-japanese-literal -- TODO: i18n対応（ADR-027 既知負債）
    error = queryError instanceof Error ? queryError.message : "権限情報の取得に失敗しました";
  }

  const load = useCallback(async () => {
    await refetch();
  }, [refetch]);

  const hasPermission = useCallback(
    (key: string) => permissions.has(key),
    [permissions],
  );

  const hasAny = useCallback(
    (...keys: string[]) => keys.some((k) => permissions.has(k)),
    [permissions],
  );

  return useMemo(
    () => ({ permissions, isTenantAdmin, isTenantOwner, loading, error, hasPermission, hasAny, reload: load }),
    [permissions, isTenantAdmin, isTenantOwner, loading, error, hasPermission, hasAny, load],
  );
}
