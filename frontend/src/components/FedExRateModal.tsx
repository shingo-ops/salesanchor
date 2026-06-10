/**
 * FedEx ライブ見積もり比較モーダル（ADR-124 D6）
 *
 * FedEx Rates and Transit Times API から取得したリアルタイム送料を表示し、
 * テナントが希望のサービスタイプを選択できる。
 *
 * ADR-124 D5（暗黙フォールバック禁止）:
 * - ライブ取得に成功した場合のみ「ライブ」バッジを表示
 * - live_error が返ってきた場合は明示的なエラーメッセージを表示
 * - FedEx 未連携の場合は連携設定ページへの導線を提供
 *
 * ADR-027: 全文字列は t("key") 経由
 *
 * 変更履歴:
 *   2026-06-09: 初版（ADR-124 Phase C）
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Modal } from "./Modal";
import { Button } from "./Button";
import { api } from "../lib/api";

// ---------------------------------------------------------------------------
// 型定義
// ---------------------------------------------------------------------------

interface FedExRateResult {
  carrier: string;
  zone: string;
  fee: number;
  currency: string;
  source: "static" | "fedex_live";
  service_type: string | null;
  service_name: string | null;
  transit_days: number | null;
  delivery_timestamp: string | null;
}

interface ShippingCalcResponse {
  results: FedExRateResult[];
  cheapest: FedExRateResult | null;
  live_error: string | null;
  rate_precision: "exact" | "approximate" | null;
}

interface Props {
  /** モーダルの開閉 */
  open: boolean;
  onClose: () => void;
  /** 宛先国コード（受注情報から渡す）*/
  destinationCountryCode: string;
  /** 重量（kg）*/
  weightKg: number;
  /** 選択した料金を受け取るコールバック */
  onSelectRate: (fee: number, currency: string, serviceType: string | null) => void;
}

// ---------------------------------------------------------------------------
// SourceBadge: ライブ / 静的 バッジ
// ---------------------------------------------------------------------------

function SourceBadge({ source }: { source: "static" | "fedex_live" }) {
  const { t } = useTranslation();
  if (source === "fedex_live") {
    return (
      <span
        style={{
          display: "inline-block",
          padding: "2px 6px",
          borderRadius: "4px",
          fontSize: "11px",
          fontWeight: 600,
          backgroundColor: "var(--color-blue-100)",
          color: "var(--color-blue-700)",
        }}
      >
        {t("fedexRateModal.sourceLive")}
      </span>
    );
  }
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 6px",
        borderRadius: "4px",
        fontSize: "11px",
        fontWeight: 600,
        backgroundColor: "var(--color-gray-100)",
        color: "var(--color-gray-600)",
      }}
    >
      {t("fedexRateModal.sourceStatic")}
    </span>
  );
}

// ---------------------------------------------------------------------------
// FedExRateModal 本体
// ---------------------------------------------------------------------------

export function FedExRateModal({
  open,
  onClose,
  destinationCountryCode,
  weightKg,
  onSelectRate,
}: Props) {
  const { t } = useTranslation();
  const [originCountryCode, setOriginCountryCode] = useState("JP");
  const [destinationPostalCode, setDestinationPostalCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ShippingCalcResponse | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const handleGetQuote = async () => {
    setLoading(true);
    setFetchError(null);
    setResponse(null);

    try {
      const data = await api.post<ShippingCalcResponse>("/shipping/calculate", {
        country_code: destinationCountryCode,
        weight_kg: weightKg,
        carrier: "fedex",
        origin_country_code: originCountryCode || "JP",
        ...(destinationPostalCode ? { destination_postal_code: destinationPostalCode } : {}),
      });
      setResponse(data);
    } catch (e) {
      setFetchError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setResponse(null);
    setFetchError(null);
    onClose();
  };

  // エラーメッセージの整形（ADR-124 D5）
  // 未連携 / アカウント番号未設定 / API エラーの3種を区別して表示
  const isNotConnected = response?.live_error?.includes("未連携") ?? false;
  const liveErrorMessage = response?.live_error
    ? isNotConnected
      ? t("fedexRateModal.errorNotConnected")
      : response.live_error.includes("アカウント番号")
        ? t("fedexRateModal.errorAccountNumber")
        : `${t("fedexRateModal.errorApiFailure")}: ${response.live_error}`
    : null;

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title={t("fedexRateModal.title")}
      size="lg"
    >
      {/* 発送元国コード入力 */}
      <div style={{ marginBottom: "12px" }}>
        <label
          htmlFor="fedex-origin"
          style={{ display: "block", marginBottom: "4px", fontWeight: 500 }}
        >
          {t("fedexRateModal.originLabel")}
        </label>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <input
            id="fedex-origin"
            type="text"
            value={originCountryCode}
            maxLength={3}
            placeholder={t("fedexRateModal.originPlaceholder")}
            onChange={(e) => setOriginCountryCode(e.target.value.toUpperCase())}
            style={{ width: "80px", padding: "6px 8px", border: "1px solid var(--color-border)", borderRadius: "4px" }}
          />
          <Button
            variant="primary"
            loading={loading}
            onClick={handleGetQuote}
            disabled={loading || !originCountryCode || !destinationCountryCode}
          >
            {loading ? t("fedexRateModal.loading") : t("fedexRateModal.getQuote")}
          </Button>
        </div>
      </div>

      {/* 宛先郵便番号（任意）— rate_precision 制御用 */}
      <div style={{ marginBottom: "16px" }}>
        <label
          htmlFor="fedex-dest-postal"
          style={{ display: "block", marginBottom: "4px", fontWeight: 500, fontSize: "13px" }}
        >
          {t("fedexRateModal.postalCodeLabel")}
        </label>
        <input
          id="fedex-dest-postal"
          type="text"
          value={destinationPostalCode}
          maxLength={20}
          placeholder={t("fedexRateModal.postalCodePlaceholder")}
          onChange={(e) => setDestinationPostalCode(e.target.value)}
          style={{ width: "160px", padding: "6px 8px", border: "1px solid var(--color-border)", borderRadius: "4px", fontSize: "13px" }}
        />
      </div>

      {/* API エラー（fetch 自体の失敗） */}
      {fetchError && (
        <div
          role="alert"
          style={{
            padding: "12px",
            borderRadius: "6px",
            backgroundColor: "var(--color-red-50)",
            color: "var(--color-red-700)",
            marginBottom: "12px",
          }}
        >
          {fetchError}
        </div>
      )}

      {/* 未連携状態（ADR-124 D5 + PO C1判断: FedEx 未連携時は設定ページへ誘導） */}
      {isNotConnected && (
        <div
          role="alert"
          style={{
            padding: "16px",
            borderRadius: "6px",
            backgroundColor: "var(--color-amber-50)",
            color: "var(--color-amber-800)",
            marginBottom: "12px",
          }}
        >
          <p style={{ marginBottom: "8px" }}>{t("fedexRateModal.errorNotConnected")}</p>
          <a
            href="/integrations/fedex"
            style={{ color: "var(--color-blue-700)", textDecoration: "underline", fontSize: "14px" }}
          >
            {t("fedexRateModal.goToIntegrationSettings")}
          </a>
        </div>
      )}

      {/* live_error（未連携以外: アカウント番号未設定 / API エラー） */}
      {liveErrorMessage && !isNotConnected && (
        <div
          role="alert"
          style={{
            padding: "12px",
            borderRadius: "6px",
            backgroundColor: "var(--color-amber-50)",
            color: "var(--color-amber-800)",
            marginBottom: "12px",
          }}
        >
          {liveErrorMessage}
        </div>
      )}

      {/* 見積もり結果テーブル */}
      {response && !liveErrorMessage && (
        <>
          {/* 概算バッジ（郵便番号未指定時）— ADR-124 仕様追補 2026-06-10 */}
          {response.rate_precision === "approximate" && (
            <div
              role="note"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 10px",
                borderRadius: "6px",
                backgroundColor: "var(--color-amber-50)",
                color: "var(--color-amber-800)",
                fontSize: "12px",
                marginBottom: "10px",
              }}
            >
              <span style={{ fontWeight: 600 }}>{t("fedexRateModal.badgeApproximate")}</span>
            </div>
          )}
          {response.results.length === 0 ? (
            <p style={{ color: "var(--color-text-secondary)" }}>{t("fedexRateModal.noResults")}</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid var(--color-border)" }}>
                  <th style={{ textAlign: "left", padding: "8px 4px" }}>{t("fedexRateModal.colSource")}</th>
                  <th style={{ textAlign: "left", padding: "8px 4px" }}>{t("fedexRateModal.colService")}</th>
                  <th style={{ textAlign: "right", padding: "8px 4px" }}>{t("fedexRateModal.colTransitDays")}</th>
                  <th style={{ textAlign: "right", padding: "8px 4px" }}>{t("fedexRateModal.colFee")}</th>
                  <th style={{ textAlign: "center", padding: "8px 4px" }}>{t("fedexRateModal.colCurrency")}</th>
                  <th style={{ textAlign: "center", padding: "8px 4px" }} />
                </tr>
              </thead>
              <tbody>
                {response.results.map((r, i) => (
                  <tr
                    key={i}
                    style={{ borderBottom: "1px solid var(--color-border-subtle)" }}
                  >
                    <td style={{ padding: "8px 4px" }}>
                      <SourceBadge source={r.source} />
                    </td>
                    <td style={{ padding: "8px 4px" }}>
                      {r.service_name ?? r.service_type ?? r.zone}
                    </td>
                    <td style={{ textAlign: "right", padding: "8px 4px" }}>
                      {r.transit_days != null
                        ? `${r.transit_days}${t("fedexRateModal.days")}`
                        : "—"}
                    </td>
                    <td style={{ textAlign: "right", padding: "8px 4px", fontWeight: 600 }}>
                      {Number(r.fee).toLocaleString()}
                    </td>
                    <td style={{ textAlign: "center", padding: "8px 4px" }}>
                      {r.currency}
                    </td>
                    <td style={{ textAlign: "center", padding: "8px 4px" }}>
                      <Button
                        variant="outline"
                        onClick={() => {
                          onSelectRate(r.fee, r.currency, r.service_type);
                          handleClose();
                        }}
                      >
                        {t("fedexRateModal.selectRate")}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      {/* フッター */}
      <div style={{ marginTop: "16px", textAlign: "right" }}>
        <Button variant="secondary" onClick={handleClose}>
          {t("fedexRateModal.cancel")}
        </Button>
      </div>
    </Modal>
  );
}
