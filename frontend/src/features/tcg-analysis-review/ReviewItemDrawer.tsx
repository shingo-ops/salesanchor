/**
 * 本番タブの行から開く、1件の訂正 Drawer（設計 §13-5 の 3）。
 * 既存の ItemComparison（読み取り専用）・ConditionReviewPanel・ProductMasterDrawer をそのまま使い、
 * v102 の件だけ理由ごとの「このままで良い」を出す（POST /tcg/items/{id}/review-ack）。
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { Drawer } from "../../components/Drawer";
import { Stack } from "../../components/Stack";
import { api, ApiError } from "../../lib/api";
import { ConditionReviewPanel } from "./ConditionReviewPanel";
import { ItemComparison, type AnalysisReviewItem } from "./ItemComparison";
import { ProductMasterDrawer } from "./ProductMasterDrawer";
import { reviewReasonLabel, reviewSourceLabel } from "./reviewReasonLabel";

export type ReviewDrawerItem = AnalysisReviewItem & { is_v102?: boolean };

interface Props {
  item: ReviewDrawerItem;
  onClose: () => void;
  /** 一覧の読み直し */
  onRefresh: () => Promise<void>;
}

type Notice = { variant: "info" | "warning"; title: string } | null;

// 原文ペインを持たない画面なので、行へのジャンプは何もしない
const noJump = () => undefined;

export function ReviewItemDrawer({ item, onClose, onRefresh }: Props) {
  const { t } = useTranslation();
  const [isProductDrawerOpen, setIsProductDrawerOpen] = useState(false);
  const [ackedCodes, setAckedCodes] = useState<string[]>([]);
  const [pendingCode, setPendingCode] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(null);
  const details = item.review_reason_details ?? [];

  const acknowledge = async (code: string) => {
    setPendingCode(code);
    setNotice(null);
    try {
      await api.post(`/tcg/items/${item.extraction_item_id}/review-ack`, {
        source_message_id: item.source_message_id,
        codes: [code],
      });
      setAckedCodes((current) => [...current, code]);
      setNotice({ variant: "info", title: t("reviewItem.acked") });
      await onRefresh();
    } catch (error: unknown) {
      const message = error instanceof ApiError && error.message ? error.message : t("reviewItem.ackFailed");
      setNotice({ variant: "warning", title: message });
    } finally {
      setPendingCode(null);
    }
  };

  return (
    <>
      <Drawer open onClose={onClose} title={t("reviewItem.drawerTitle")}>
        <Stack gap="3">
          {notice && <Callout variant={notice.variant} title={notice.title} />}
          <ItemComparison item={item} readOnly={true} onJumpToSourceLine={noJump} />
          <ConditionReviewPanel item={item} onRefresh={onRefresh} />
          <div>
            <Button variant="secondary" onClick={() => setIsProductDrawerOpen(true)}>
              {t("superAdmin.supplierQuality.correctPhase3")}
            </Button>
          </div>
          <section>
            <h3>{t("reviewItem.reasonsHeading")}</h3>
            {details.length === 0 && <p>{t("reviewItem.noReasons")}</p>}
            {details.length > 0 && (
              <p>{t("reviewItem.sourceLine", { source: reviewSourceLabel(t, details) ?? "—" })}</p>
            )}
            <ul>
              {details.map((detail) => (
                <li key={detail.code}>
                  <span>{reviewReasonLabel(t, detail.code)}</span>{" "}
                  {item.is_v102 === true && !ackedCodes.includes(detail.code) && (
                    <Button
                      variant="secondary"
                      size="sm"
                      loading={pendingCode === detail.code}
                      disabled={pendingCode !== null}
                      onClick={() => void acknowledge(detail.code)}
                    >
                      {t("reviewItem.ack")}
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          </section>
        </Stack>
      </Drawer>
      {isProductDrawerOpen && (
        <ProductMasterDrawer
          item={item}
          onClose={() => setIsProductDrawerOpen(false)}
          onSaved={() => {
            setIsProductDrawerOpen(false);
            void onRefresh();
          }}
        />
      )}
    </>
  );
}
