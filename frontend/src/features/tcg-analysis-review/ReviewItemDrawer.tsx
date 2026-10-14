/**
 * 本番タブの行から開く、1件の訂正 Drawer（設計 §13-5 の 3、review-fix-column）。
 * 上から: 赤字の理由 → 原文 | 比較表（「修正」列、行を押すと選べる）→ 「直す」欄。
 * 比較表は表示だけで、値を変えられるのは「直す」欄（ReviewFixWizard）だけ。
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { Drawer } from "../../components/Drawer";
import { Stack } from "../../components/Stack";
import { TwoColumn } from "../../components/TwoColumn";
import { GAP_SUSPECT_CODE, GapSuspectNote, gapSuspectOf, type GapSuspectData } from "./GapSuspectNote";
import { ItemComparison, type AnalysisReviewItem } from "./ItemComparison";
import { choicesForScope, ReviewFixWizard, type FixScope } from "./ReviewFixWizard";
import { fixRowsOf } from "./reviewFixRows";
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
  /** 一覧から外れた件を最後の内容のまま表示しているとき true */
  removedFromList?: boolean;
}

// 原文ペインはその商品の行へ自動で送るため、行ジャンプは何もしない
const noJump = () => undefined;

export function ReviewItemDrawer({ item, onClose, onRefresh, removedFromList = false }: Props) {
  const { t } = useTranslation();
  const details = item.review_reason_details ?? [];
  const gapSuspect = gapSuspectOf(item);
  const [scope, setScope] = useState<FixScope | null>(null);
  const [selectedRowKey, setSelectedRowKey] = useState<string | null>(null);
  const [ackedCodes, setAckedCodes] = useState<string[]>([]);
  const [ackedNotice, setAckedNotice] = useState(false);

  const fixRows = fixRowsOf(item, t);
  const fixableRowKeys = Object.keys(fixRows);
  const canKeep = choicesForScope(item, "keep", ackedCodes).length > 0;

  const selectRow = (rowKey: string) => {
    const rowScope = fixRows[rowKey]?.scope;
    if (!rowScope) return;
    setAckedNotice(false);
    setSelectedRowKey(rowKey);
    setScope(rowScope);
  };

  const chooseKeep = () => {
    setAckedNotice(false);
    setSelectedRowKey(null);
    setScope("keep");
  };

  // 理由を確認済みにできた。使い切ったら「このままで良い」を閉じて通知だけ残す
  const handleAcked = (codes: string[]) => {
    const next = [...ackedCodes, ...codes];
    setAckedCodes(next);
    if (choicesForScope(item, "keep", next).length === 0) {
      setScope(null);
      setAckedNotice(true);
    }
  };

  return (
    <Drawer open onClose={onClose} title={t("reviewItem.drawerTitle")} size="wide">
      <Stack gap="4">
        {removedFromList && <Callout variant="info" title={t("reviewItem.removedFromList")} />}
        <section className="review-item-reasons-block">
          <Stack gap="2">
            {details.length === 0 && <p>{t("reviewItem.noReasons")}</p>}
            <ul className="review-item-reasons">
              {details.map((detail) => (
                <li key={detail.code}>
                  <span className="review-item-reasons__text">{reviewReasonLabel(t, detail.code)}</span>
                  {detail.code === "excluded" && (
                    <p>
                      {item.system.status
                        ? t("reviewItem.excludedHelp", { status: item.system.status })
                        : t("reviewItem.excludedHelpNoStatus")}
                    </p>
                  )}
                  {detail.code === GAP_SUSPECT_CODE && gapSuspect && (
                    <GapSuspectNote gapLines={gapSuspect.gap_lines} candidates={gapSuspect.candidates} />
                  )}
                </li>
              ))}
            </ul>
            {details.length > 0 && <p>{t("reviewItem.sourceLine", { source: reviewSourceLabel(t, details) ?? "—" })}</p>}
            {canKeep && (
              <div>
                <Button variant="secondary" size="sm" onClick={chooseKeep}>
                  {t("reviewItem.wizard.choice.keep")}
                </Button>
              </div>
            )}
            {ackedNotice && <Callout variant="info" title={t("reviewItem.acked")} />}
          </Stack>
        </section>
        <TwoColumn ratio="1:2" gap="3" align="stretch" className="review-item-top">
          <section className="review-item-source">
            <div className="review-item-pane-head">
              <h3>{t("reviewItem.sourceHeading")}</h3>
            </div>
            <ShadowSourcePane rawText={item.raw_text} blockRange={parseSourceLineRange(item.gemini.span)} />
          </section>
          <ItemComparison
            item={item}
            readOnly={true}
            onJumpToSourceLine={noJump}
            heading={t("reviewItem.compareHeading")}
            fixColumn={{ selectedRowKey, onRowSelect: selectRow, fixableRowKeys }}
          />
        </TwoColumn>
        {scope !== null && (
          <section className="review-item-fix">
            <ReviewFixWizard
              key={`${item.extraction_item_id}:${scope}`}
              item={item}
              scope={scope}
              ackedCodes={ackedCodes}
              onAcked={handleAcked}
              onRefresh={onRefresh}
            />
          </section>
        )}
      </Stack>
    </Drawer>
  );
}
