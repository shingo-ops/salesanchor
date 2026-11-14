/**
 * 予定のカルテの途中の吹き出し（ADR-1078）。埋まった欄と、次に聞く 1 つの質問を出す。
 * 質問の文は翻訳キー secretary.ask.*（AI に書かせない）。日時の書き方は予定の画面と同じ関数を使う。
 */

import { useTranslation } from "react-i18next";
import { formatDateInput, formatDraftDateLine, formatTimeInput } from "../../pages/schedule/schedule-utils";
import type { EventDraftData } from "./secretaryApi";

interface Props {
  draft: EventDraftData;
}

export function SecretaryKarteAsk({ draft }: Props) {
  const { t, i18n } = useTranslation();

  // 1 つの日時を「11月2日(月) 午前10:00」の形で書く。読めなければ空（その行は出さない）
  const dateLine = (iso: string | null): string => {
    if (iso === null) return "";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "";
    return formatDraftDateLine(
      { startDate: formatDateInput(date), startTime: formatTimeInput(date), endDate: "", endTime: "", allDay: draft.is_all_day },
      t,
      i18n.language,
    );
  };

  const rows = [
    { key: "name", label: t("secretary.event.name"), value: draft.title ?? "" },
    { key: "start", label: t("secretary.event.startDate"), value: dateLine(draft.start) },
    { key: "end", label: t("secretary.event.endDate"), value: dateLine(draft.end) },
  ].filter((row) => row.value !== "");

  return (
    <div className="secretary-karte">
      {rows.length > 0 && (
        <>
          <p className="secretary-karte__heading">{t("secretary.karte.filled")}</p>
          <dl className="secretary-karte__list">
            {rows.map((row) => (
              <div key={row.key} className="secretary-karte__row">
                <dt className="secretary-karte__label">{row.label}</dt>
                <dd className="secretary-karte__value">{row.value}</dd>
              </div>
            ))}
          </dl>
        </>
      )}
      {draft.ask && <p className="secretary-karte__question">{t(`secretary.ask.${draft.ask}`)}</p>}
    </div>
  );
}
