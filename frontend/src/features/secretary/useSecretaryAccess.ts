/**
 * 秘書の窓を出す条件の 1 か所（窓と設定の「秘書の声」の欄が同じ条件で出る）。
 * 条件は backend の口と同じ 4 つ（feature・super admin・customers.view・invoices.create）。
 */

import { useFeatures } from "../../hooks/useFeatures";
import { usePermissions } from "../../hooks/usePermissions";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";

export function useSecretaryAccess(): { ready: boolean; allowed: boolean } {
  const features = useFeatures();
  const superAdmin = useSuperAdmin();
  const permissions = usePermissions();

  const ready = !features.loading && !superAdmin.loading && !permissions.loading;
  const allowed =
    ready &&
    features.isEnabled("secretary_chat") &&
    superAdmin.isSuperAdmin &&
    permissions.hasPermission("customers.view") &&
    permissions.hasPermission("invoices.create");
  return { ready, allowed };
}
