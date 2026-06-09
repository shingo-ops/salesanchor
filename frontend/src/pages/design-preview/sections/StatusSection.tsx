/**
 * §13 ステータス対応表 — 決定レイヤー 1 SSoT
 *
 * 全 11 ドメイン × 全ステータスを getStatusPresentation() 経由で一覧表示する。
 * この見た目が実画面の正解（設計§3 のバケット規則に基づく）。
 *
 * 参照: docs/adr/ADR-120-status-presentation-ssot.md
 */
import { STATUS_PRESENTATION_MAP, type StatusDomain } from "../../../utils/statusPresentation";
import { SectionHeader } from "./_shared";

const DOMAIN_LABELS: Record<StatusDomain, string> = {
  lead:          "リード (LeadStatus)",
  quote:         "見積 (QuoteStatus)",
  invoice:       "請求書 (InvoiceStatus)",
  deal:          "商談 (DealStatus)",
  order:         "受注 (OrderStatus)",
  purchaseOrder: "発注 (PurchaseOrderStatus)",
  parseStatus:   "Discord 解析 (ParseStatus)",
  staff:         "スタッフ (StaffStatus)",
  bot:           "ボット (BotStatus)",
  prospectRank:  "商談ランク (ProspectRank)",
  erpJobStatus:  "ERP同期ジョブ (ErpJobStatus)",
};

const BUCKET_ORDER = ["success", "danger", "warning", "info", "neutral"] as const;
type Bucket = typeof BUCKET_ORDER[number];

const BUCKET_LABELS: Record<Bucket, string> = {
  success: "success — 緑",
  danger:  "danger — 赤",
  warning: "warning — 黄",
  info:    "info — 青",
  neutral: "neutral — 灰",
};

export function StatusSection() {
  const domains = Object.keys(STATUS_PRESENTATION_MAP) as StatusDomain[];

  return (
    <>
      {/* §13a: ドメイン別一覧 */}
      <section className="dp-section">
        <SectionHeader
          title="13a. ステータス対応表 — ドメイン別（決定レイヤー 1 SSoT）"
          desc="全10ドメイン × 全ステータスを getStatusPresentation() 経由で表示。hover で bucket 名を確認できる。ADR-120 参照。"
        />

        {domains.map((domain) => (
          <div key={domain} style={{ marginTop: "var(--space-6)" }}>
            <p style={{
              fontSize: "var(--font-sm)",
              fontWeight: 600,
              marginBottom: "var(--space-2)",
              color: "var(--text-secondary)",
            }}>
              {DOMAIN_LABELS[domain]}
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
              {Object.entries(STATUS_PRESENTATION_MAP[domain]).map(([status, presentation]) => (
                <span
                  key={status}
                  className={`badge badge-${presentation.badgeVariant}`}
                  title={`bucket: ${presentation.bucket}`}
                >
                  {status}
                </span>
              ))}
            </div>
          </div>
        ))}
      </section>

      {/* §13b: バケット別サマリ */}
      <section className="dp-section">
        <SectionHeader
          title="13b. バケット別サマリ（5バケット規則）"
          desc="success / danger / warning / info / neutral — 全ドメインをバケット軸でまとめた一覧。同一バケットが同じ色になっていることを確認する。"
        />

        {BUCKET_ORDER.map((bucket) => {
          const entries = domains.flatMap((domain) =>
            Object.entries(STATUS_PRESENTATION_MAP[domain])
              .filter(([, p]) => p.bucket === bucket)
              .map(([status, p]) => ({ domain, status, badgeVariant: p.badgeVariant })),
          );
          return (
            <div key={bucket} style={{ marginTop: "var(--space-4)" }}>
              <p style={{
                fontSize: "var(--font-sm)",
                fontWeight: 600,
                marginBottom: "var(--space-2)",
                color: "var(--text-secondary)",
              }}>
                {BUCKET_LABELS[bucket]} ({entries.length} 件)
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
                {entries.map(({ domain, status, badgeVariant }) => (
                  <span
                    key={`${domain}.${status}`}
                    className={`badge badge-${badgeVariant}`}
                    title={`${domain}.${status}`}
                  >
                    {domain}.{status}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </section>

      {/* §13c: 使い方スニペット */}
      <section className="dp-section">
        <SectionHeader
          title="13c. 使い方スニペット（ステップ2 移行時の参考）"
          desc="getStatusPresentation() を使った実装パターン。ページ側で badge-${status} を直書きしない。"
        />
        <pre style={{
          background: "var(--bg-subtle)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-md)",
          padding: "var(--space-4)",
          fontSize: "var(--font-xs)",
          overflowX: "auto",
          margin: 0,
        }}>
{`import { getStatusPresentation } from "../../utils/statusPresentation";

// ページコンポーネント内
const p = getStatusPresentation("lead", lead.status);
<span className={\`badge badge-\${p.badgeVariant}\`}>
  {t(p.labelKey ?? lead.status)}
</span>

// 未知ステータスは neutral に安全フォールバック（console.warn のみ）
const p = getStatusPresentation("invoice", unknownStatus);
// → { bucket: "neutral", badgeVariant: "neutral" }`}
        </pre>
      </section>
    </>
  );
}
