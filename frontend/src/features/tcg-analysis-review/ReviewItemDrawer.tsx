/**
 * 本番タブの行から開く、1件の訂正 Drawer（設計 §13-5 の 3）。
 * 既存の ItemComparison（読み取り専用）と、理由の一覧（読むだけ）、
 * 「何を直しますか？」の質問（ReviewFixWizard）で構成する。
 */
import { useTranslation } from "react-i18next";
import { Drawer } from "../../components/Drawer";
import { Stack } from "../../components/Stack";
import { TwoColumn } from "../../components/TwoColumn";
import { GAP_SUSPECT_CODE, GapSuspectNote, gapSuspectOf, type GapSuspectData } from "./GapSuspectNote";
import { ItemComparison, type AnalysisReviewItem } from "./ItemComparison";
import { ReviewFixWizard } from "./ReviewFixWizard";
import { reviewReasonLabel, reviewSourceLabel } from "./reviewReasonLabel";
import { ShadowSourcePane } from "./ShadowSourcePane";
import { parseSourceLineRange } from "./sourceRawNavigation";
import "./review-item-drawer.css";

export type ReviewDrawerItem = AnalysisReviewItem & { is_v102?: boolean; gap_suspect?: GapSuspectData | null };

interface Props {
  item: ReviewDrawerItem;
  onClose: () => void;
  /** 一覧の読み直し */
  onRefresh: () => Promise<void>;
}

// 原文ペインはその商品の行へ自動で送るため、行ジャンプは何もしない
const noJump = () => undefined;

export function ReviewItemDrawer({ item, onClose, onRefresh }: Props) {
  const { t } = useTranslation();
  const details = item.review_reason_details ?? [];
  const gapSuspect = gapSuspectOf(item);

  return (
    <Drawer open onClose={onClose} title={t("reviewItem.drawerTitle")} size="wide">
      <Stack gap="4">
        <TwoColumn ratio="1:2" gap="3" align="stretch" className="review-item-top">
          <section className="review-item-source">
            <div className="review-item-pane-head">
              <h3>{t("reviewItem.sourceHeading")}</h3>
            </div>
            <ShadowSourcePane rawText={item.raw_text} blockRange={parseSourceLineRange(item.gemini.span)} />
          </section>
          <ItemComparison item={item} readOnly={true} onJumpToSourceLine={noJump} heading={t("reviewItem.compareHeading")} />
        </TwoColumn>
        <section className="review-item-fix">
          <h3>{t("reviewItem.fixHeading")}</h3>
          <Stack gap="3">
            <section>
              <h3>{t("reviewItem.reasonsHeading")}</h3>
              {details.length === 0 && <p>{t("reviewItem.noReasons")}</p>}
              {details.length > 0 && (
                <p>{t("reviewItem.sourceLine", { source: reviewSourceLabel(t, details) ?? "—" })}</p>
              )}
              <ul>
                {details.map((detail) => (
                  <li key={detail.code}>
                    <span>{reviewReasonLabel(t, detail.code)}</span>
                    {detail.code === GAP_SUSPECT_CODE && gapSuspect && (
                      <GapSuspectNote gapLines={gapSuspect.gap_lines} candidates={gapSuspect.candidates} />
                    )}
                  </li>
                ))}
              </ul>
            </section>
            <ReviewFixWizard key={item.extraction_item_id} item={item} onRefresh={onRefresh} />
          </Stack>
        </section>
      </Stack>
    </Drawer>
  );
}
