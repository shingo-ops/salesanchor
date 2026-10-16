/**
 * 本番タブの行から開く、1件の訂正 Drawer（設計 §13-5 の 3、review-fix-column）。
 * 上から: 赤字の理由 → 原文 | 比較表（「修正」列、行を押すと選べる）→ 「直す」欄。
 * 比較表の行を押すと、その行に合わせた「直す」欄（ReviewFixWizard）が出る。値を変えられるのは「直す」欄だけ。
 */
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import ConfirmModal from "../../components/ConfirmModal";
import { Drawer } from "../../components/Drawer";
import { Stack } from "../../components/Stack";
import { TwoColumn } from "../../components/TwoColumn";
import { ApiError } from "../../lib/api";
import { GAP_SUSPECT_CODE, GapSuspectNote, gapSuspectOf, type GapSuspectData } from "./GapSuspectNote";
import { ItemComparison, type AnalysisReviewItem } from "./ItemComparison";
import { ackableReasonCodes, ReviewFixWizard, type FixScope } from "./ReviewFixWizard";
import { postReviewAck, postReviewAckRevoke } from "./reviewActions";
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
  /** 「確認済み」タブから開いたとき true（確認済みである旨と取り消しボタンを出す） */
  ackedView?: boolean;
  /** 見るだけ（在庫表から開くとき）。「確認済み」・取消・行を押して直す操作を出さない */
  viewOnly?: boolean;
  /** 本文の先頭に置く部品（在庫表のまとめた行の切り替えタブなど） */
  headerSlot?: ReactNode;
}

// 原文ペインはその商品の行へ自動で送るため、行ジャンプは何もしない
const noJump = () => undefined;

export function ReviewItemDrawer({ item, onClose, onRefresh, removedFromList = false, ackedView = false, viewOnly = false, headerSlot }: Props) {
  const { t } = useTranslation();
  const details = item.review_reason_details ?? [];
  const gapSuspect = gapSuspectOf(item);
  const [scope, setScope] = useState<FixScope | null>(null);
  const [selectedRowKey, setSelectedRowKey] = useState<string | null>(null);
  const [ackedCodes, setAckedCodes] = useState<string[]>([]);
  const [ackedNotice, setAckedNotice] = useState(false);
  const [ackError, setAckError] = useState<string | null>(null);
  const [ackPending, setAckPending] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [revokedNotice, setRevokedNotice] = useState(false);
  // 取り消しが成功した後は true（お知らせは行の選択で消えるが、取り消し済みは変わらないので別に持つ）
  const [revoked, setRevoked] = useState(false);
  const [revokeError, setRevokeError] = useState(false);
  const [revokeAsk, setRevokeAsk] = useState(false);
  const [revokePending, setRevokePending] = useState(false);

  const fixRows = fixRowsOf(item, t);
  const fixableRowKeys = Object.keys(fixRows);
  const keepCodes = ackableReasonCodes(item, ackedCodes);
  const canKeep = !viewOnly && keepCodes.length > 0;

  const selectRow = (rowKey: string) => {
    if (viewOnly) return;
    const rowScope = fixRows[rowKey]?.scope;
    if (!rowScope) return;
    setAckedNotice(false);
    setAckError(null);
    setRevokedNotice(false);
    setRevokeError(false);
    setSelectedRowKey(rowKey);
    setScope(rowScope);
  };

  const askKeep = () => {
    setAckedNotice(false);
    setAckError(null);
    setRevokedNotice(false);
    setRevokeError(false);
    setConfirmOpen(true);
  };

  // 「このまま」を押した。残っている理由をまとめて1回で確認済みにする
  const confirmKeep = async () => {
    setConfirmOpen(false);
    setAckPending(true);
    try {
      await postReviewAck(item, keepCodes);
    } catch (error: unknown) {
      setAckError(error instanceof ApiError && error.message ? error.message : t("reviewItem.ackFailed"));
      setAckPending(false);
      return;
    }
    setAckedCodes([...ackedCodes, ...keepCodes]);
    setAckedNotice(true);
    setRevoked(false);
    setRevokedNotice(false);
    setRevokeError(false);
    setAckPending(false);
    try {
      await onRefresh();
    } catch {
      // 読み直しの失敗は保存結果と無関係。次の操作・再表示で最新になる
    }
  };

  // 確認済みを取り消す。成功したら解析のやり直しが始まっている（一覧は読み直す）
  const confirmRevoke = async () => {
    setRevokeAsk(false);
    setRevokePending(true);
    setRevokeError(false);
    try {
      await postReviewAckRevoke(item);
    } catch {
      setRevokeError(true);
      setRevokePending(false);
      return;
    }
    setAckedNotice(false);
    setAckedCodes([]);
    setRevokedNotice(true);
    setRevoked(true);
    setRevokePending(false);
    try {
      await onRefresh();
    } catch {
      // 読み直しの失敗は保存結果と無関係。次の操作・再表示で最新になる
    }
  };

  const revokeButton = (
    <div>
      <Button
        variant="secondary"
        size="sm"
        loading={revokePending}
        disabled={revokePending}
        onClick={() => setRevokeAsk(true)}
      >
        {ackedNotice ? t("reviewItem.revokeUndo") : t("reviewItem.revoke")}
      </Button>
    </div>
  );

  return (
    <Drawer open onClose={confirmOpen || revokeAsk ? () => undefined : onClose} title={t("reviewItem.drawerTitle")} size="wide">
      <Stack gap="4">
        {headerSlot}
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
                <Button variant="secondary" size="sm" loading={ackPending} disabled={ackPending || revokePending} onClick={askKeep}>
                  {t("reviewItem.ack")}
                </Button>
              </div>
            )}
            {ackError && <Callout variant="warning" title={ackError} />}
            {revokeError && <Callout variant="warning" title={t("reviewItem.revokeFailed")} />}
            {ackedNotice && <Callout variant="info" title={t("reviewItem.acked")}>{revokeButton}</Callout>}
            {!viewOnly && ackedView && !ackedNotice && !revoked && (
              <Callout variant="info" title={t("reviewItem.ackedState")}>{revokeButton}</Callout>
            )}
            {revokedNotice && <Callout variant="info" title={t("reviewItem.revoked")} />}
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
            fixColumn={viewOnly ? undefined : { selectedRowKey, onRowSelect: selectRow, fixableRowKeys }}
          />
        </TwoColumn>
        {scope !== null && (
          <section className="review-item-fix">
            <ReviewFixWizard
              key={`${item.extraction_item_id}:${scope}:${selectedRowKey ?? ""}`}
              item={item}
              scope={scope}
              rowKey={selectedRowKey ?? ""}
              onRefresh={onRefresh}
            />
          </section>
        )}
      </Stack>
      <ConfirmModal
        open={confirmOpen}
        title={t("reviewItem.ackConfirm.title")}
        message={
          <>
            <p>{t("reviewItem.ackConfirm.message")}</p>
            <ul className="review-item-reasons">
              {keepCodes.map((code) => (
                <li key={code}>{reviewReasonLabel(t, code)}</li>
              ))}
            </ul>
          </>
        }
        confirmLabel={t("reviewItem.ackConfirm.confirm")}
        cancelLabel={t("common.close")}
        onConfirm={() => void confirmKeep()}
        onCancel={() => setConfirmOpen(false)}
      />
      <ConfirmModal
        open={revokeAsk}
        title={t("reviewItem.revokeConfirm.title")}
        message={<p>{t("reviewItem.revokeConfirm.message")}</p>}
        confirmLabel={t("reviewItem.revokeConfirm.confirm")}
        cancelLabel={t("common.close")}
        onConfirm={() => void confirmRevoke()}
        onCancel={() => setRevokeAsk(false)}
      />
    </Drawer>
  );
}
