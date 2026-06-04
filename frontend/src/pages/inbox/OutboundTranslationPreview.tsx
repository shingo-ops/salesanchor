/**
 * ADR-110: 送信下訳プレビューモーダル。
 *
 * フロー:
 *   1. 日本語下書き → 「英訳プレビュー」ボタンで API 呼び出し
 *   2. 下訳 + 低確信度ハイライト + 編集フィールドを表示
 *   3. 「確認して送信」で confirm → 親コンポーネントが実際の送信を行う
 *
 * 「確認して送信」以外に送信経路は存在しない（ADR-110 受け入れ条件 3）。
 */

import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import type { OutboundPreviewResponse } from "../../lib/messages";
import { confirmOutboundDraft, requestOutboundPreview } from "../../lib/messages";

interface Props {
  leadId: number | null;
  draftText: string;
  onConfirmedSend: (finalText: string) => void;
  onClose: () => void;
  disabled: boolean;
}

export function OutboundTranslationPreview({
  leadId,
  draftText,
  onConfirmedSend,
  onClose,
  disabled,
}: Props) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<OutboundPreviewResponse | null>(null);
  const [editedText, setEditedText] = useState("");
  const [confirming, setConfirming] = useState(false);

  const handlePreview = useCallback(async () => {
    if (!draftText.trim()) return;
    setLoading(true);
    setError(null);
    setPreview(null);
    try {
      const result = await requestOutboundPreview(draftText, leadId);
      setPreview(result);
      setEditedText(result.draft_text);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("translation.outbound.previewError");
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [draftText, leadId, t]);

  const handleConfirmSend = useCallback(async () => {
    if (!preview || !editedText.trim()) return;
    setConfirming(true);
    setError(null);
    try {
      await confirmOutboundDraft(preview.draft_id, editedText.trim());
      onConfirmedSend(editedText.trim());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t("translation.outbound.confirmError");
      setError(msg);
      setConfirming(false);
    }
  }, [preview, editedText, onConfirmedSend, t]);

  return (
    <div className="outbound-translation-overlay" role="dialog" aria-modal="true">
      <div className="outbound-translation-modal">
        <div className="outbound-translation-header">
          <span className="outbound-translation-title">{t("translation.outbound.title")}</span>
          <button
            type="button"
            className="outbound-translation-close"
            onClick={onClose}
            aria-label={t("common.close")}
          >
            ×
          </button>
        </div>

        {/* 原文（日本語下書き） */}
        <div className="outbound-translation-section">
          <div className="outbound-translation-label">{t("translation.outbound.originalLabel")}</div>
          <div className="outbound-translation-original">{draftText}</div>
        </div>

        {/* プレビューボタン */}
        {!preview && (
          <button
            type="button"
            className="outbound-translation-preview-btn"
            onClick={handlePreview}
            disabled={loading || disabled || !draftText.trim()}
          >
            {loading ? t("translation.outbound.generating") : t("translation.outbound.generateBtn")}
          </button>
        )}

        {/* エラー */}
        {error && (
          <div className="outbound-translation-error" role="alert">
            {error}
          </div>
        )}

        {/* 下訳プレビュー */}
        {preview && (
          <>
            <div className="outbound-translation-section">
              <div className="outbound-translation-label">
                {t("translation.outbound.draftLabel")}
                {preview.is_low_confidence && (
                  <span className="outbound-translation-low-conf-badge">
                    {t("translation.outbound.lowConfidence")}
                  </span>
                )}
              </div>

              {/* 低確信度フラグ一覧 */}
              {preview.flagged_terms.length > 0 && (
                <div className="outbound-translation-flags">
                  <div className="outbound-translation-flags-title">
                    {t("translation.outbound.flaggedTermsTitle")}
                  </div>
                  {preview.flagged_terms.map((ft, i) => (
                    <div key={i} className="outbound-translation-flag-item">
                      <span className="outbound-translation-flag-term">「{ft.term}」</span>
                      {ft.reason && (
                        <span className="outbound-translation-flag-reason">— {ft.reason}</span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* 編集可能テキストエリア */}
              <textarea
                className="outbound-translation-edit"
                value={editedText}
                onChange={(e) => setEditedText(e.target.value)}
                rows={4}
                disabled={confirming}
                aria-label={t("translation.outbound.editAriaLabel")}
              />
              <div className="outbound-translation-meta">
                {t("translation.outbound.modelLabel")}: {preview.model}
                {" · "}
                {t("translation.outbound.confidenceLabel")}: {Math.round(preview.confidence * 100)}%
              </div>
            </div>

            {/* アクションボタン */}
            <div className="outbound-translation-actions">
              <button
                type="button"
                className="outbound-translation-regenerate-btn"
                onClick={handlePreview}
                disabled={loading || confirming}
              >
                {loading ? t("translation.outbound.generating") : t("translation.outbound.regenerate")}
              </button>
              <button
                type="button"
                className="outbound-translation-send-btn"
                onClick={handleConfirmSend}
                disabled={confirming || !editedText.trim()}
              >
                {confirming
                  ? t("translation.outbound.confirming")
                  : t("translation.outbound.confirmSend")}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
