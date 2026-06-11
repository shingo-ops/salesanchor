/**
 * SA-02 Stage 3: 手動会話ログ記録セクション
 *
 * 表示条件: 現在の会話プラットフォームが connection_type='manual' のとき（入口排他）。
 * 自動連携チャネル（messenger/instagram/discord）ではレンダリングしない。
 *
 * ADR-096 §3-3: 手動記録 API + スレッド欄常設のチャット風入力 UI
 */
import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import api from "../../lib/api";

interface ChannelMaster {
  platform: string;
  display_name: string;
  connection_type: "auto" | "manual";
  is_active: boolean;
}

interface Props {
  leadId: number;
  currentPlatform: string | null;
}

export function ManualRecordSection({ leadId, currentPlatform }: Props) {
  const { t } = useTranslation();
  const [manualChannels, setManualChannels] = useState<ChannelMaster[]>([]);
  const [isManualContext, setIsManualContext] = useState(false);

  const [channelType, setChannelType] = useState("");
  const [contentText, setContentText] = useState("");
  const [occurredAt, setOccurredAt] = useState(
    () => new Date().toISOString().slice(0, 16)
  );
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [dupWarning, setDupWarning] = useState<string | null>(null);
  const [savedCount, setSavedCount] = useState(0);

  // チャネルマスタを取得して手動チャネル判定
  useEffect(() => {
    api
      .get<ChannelMaster[]>("/api/v1/channel-masters")
      .then((res) => {
        const all: ChannelMaster[] = Array.isArray(res) ? res : (res as { data?: ChannelMaster[] }).data ?? [];
        const manuals = all.filter((c) => c.connection_type === "manual");
        setManualChannels(manuals);

        // 現在のプラットフォームが manual かチェック
        const isManual =
          currentPlatform != null &&
          manuals.some((c) => c.platform === currentPlatform);
        setIsManualContext(isManual);

        // デフォルトチャネルをセット
        if (isManual && currentPlatform) {
          setChannelType(currentPlatform);
        } else if (manuals.length > 0) {
          setChannelType(manuals[0].platform);
        }
      })
      .catch(() => {
        // チャネルマスタ取得失敗時はセクション非表示（エラー通知不要）
      });
  }, [currentPlatform]);

  const handleSave = useCallback(async (allowDuplicate = false) => {
    if (!contentText.trim() || !channelType) return;
    setSaving(true);
    setSaveError(null);
    setDupWarning(null);
    try {
      await api.post(`/api/v1/leads/${leadId}/conv-logs`, {
        channel_type: channelType,
        direction: "inbound",
        content_text: contentText.trim(),
        occurred_at: new Date(occurredAt).toISOString(),
        allow_duplicate: allowDuplicate,
      });
      setContentText("");
      setOccurredAt(new Date().toISOString().slice(0, 16));
      setSavedCount((c) => c + 1);
    } catch (err: unknown) {
      const httpStatus = (err as { response?: { status?: number } }).response?.status;
      if (httpStatus === 409) {
        setDupWarning(t("inbox.manualRecord.dupWarning"));
      } else {
        setSaveError(t("inbox.manualRecord.saveError"));
      }
    } finally {
      setSaving(false);
    }
  }, [contentText, channelType, occurredAt, leadId, t]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSave(false);
      }
    },
    [handleSave]
  );

  // 手動チャネルコンテキストでない場合は非表示
  if (!isManualContext) return null;

  return (
    <div className="manual-record-section">
      <div className="manual-record-header">
        <span className="manual-record-title">
          {t("inbox.manualRecord.sectionTitle")}
        </span>
        {savedCount > 0 && (
          <span className="manual-record-saved-badge">
            {t("inbox.manualRecord.savedBadge")} ×{savedCount}
          </span>
        )}
      </div>

      {/* チャネル選択 */}
      <div className="manual-record-row">
        <label className="manual-record-label" htmlFor="manual-channel-select">
          {t("inbox.manualRecord.channelLabel")}
        </label>
        <select
          id="manual-channel-select"
          className="manual-record-select"
          value={channelType}
          onChange={(e) => setChannelType(e.target.value)}
          disabled={saving}
          aria-label={t("inbox.manualRecord.channelLabel")}
        >
          {manualChannels.map((ch) => (
            <option key={ch.platform} value={ch.platform}>
              {ch.display_name}
            </option>
          ))}
        </select>
      </div>

      {/* 日時 */}
      <div className="manual-record-row">
        <label className="manual-record-label" htmlFor="manual-occurred-at">
          {t("inbox.manualRecord.occurredAtLabel")}
        </label>
        <input
          id="manual-occurred-at"
          type="datetime-local"
          className="manual-record-datetime"
          value={occurredAt}
          onChange={(e) => setOccurredAt(e.target.value)}
          disabled={saving}
          aria-label={t("inbox.manualRecord.occurredAtLabel")}
        />
      </div>

      {/* 内容入力 */}
      <textarea
        className="manual-record-textarea"
        value={contentText}
        onChange={(e) => setContentText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={t("inbox.manualRecord.contentPlaceholder")}
        rows={3}
        disabled={saving}
        aria-label={t("inbox.manualRecord.contentPlaceholder")}
      />

      {saveError && (
        <div className="manual-record-error" role="alert">
          {saveError}
        </div>
      )}

      {dupWarning && (
        <div className="manual-record-dup-warning" role="alert">
          {dupWarning}
          <button
            type="button"
            className="manual-record-dup-force-btn"
            onClick={() => handleSave(true)}
            disabled={saving}
          >
            {t("inbox.manualRecord.saveAnyway")}
          </button>
        </div>
      )}

      <button
        type="button"
        className="manual-record-save-btn"
        onClick={() => handleSave(false)}
        disabled={saving || !contentText.trim()}
        aria-label={t("inbox.manualRecord.save")}
      >
        {saving
          ? t("inbox.manualRecord.saving")
          : t("inbox.manualRecord.save")}
      </button>
    </div>
  );
}
