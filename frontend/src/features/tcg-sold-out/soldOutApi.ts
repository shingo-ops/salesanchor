import { api } from "../../lib/api";

import type { components, operations } from "../../api/generated/schema";

export type SourceScope = NonNullable<NonNullable<
  operations["list_sold_out_results_api_v1_tcg_sold_out_results_get"]["parameters"]["query"]
>["source_scope"]>;
export type SoldOutItem = components["schemas"]["SoldOutResultItem"];
export type SoldOutResponse = components["schemas"]["SoldOutResultsResponse"];
export function fetchSoldOut(q: string, sourceScope: SourceScope, offset: number) {
  const params = new URLSearchParams({ q: q.trim(), source_scope: sourceScope, offset: String(offset), limit: "50" });
  return api.get<SoldOutResponse>(`/tcg/sold-out-results?${params}`);
}
