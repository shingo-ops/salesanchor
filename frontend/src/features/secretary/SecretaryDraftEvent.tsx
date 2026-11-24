/**
 * 予定の下書き（ADR-1056 段2）。送る欄は全部見せて、全部直せる。
 * 「作る」は今の予定の画面と同じ口 POST /calendar/events を、本人のログインで呼ぶ。
 * 日付と時刻の組み立ては今の予定の画面と同じ関数（combineDateTime など）を使う。
 */

import { forwardRef, useImperativeHandle, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { Button } from "../../components/Button";
import { Select } from "../../components/Select";
import { TextField } from "../../components/TextField";
import { Textarea } from "../../components/Textarea";
import { Checkbox } from "../../components/Checkbox";
import {
  combineDateTime,
  formatDateInput,
  formatTimeInput,
} from "../../pages/schedule/schedule-utils";
import { toKarteTime, type EventDraftData, type EventKarte } from "./secretaryApi";

interface Props {
  draft: EventDraftData;
  onCreated: () => void;
  onCancel: () => void;
  /** 声の「はい」で作るのに失敗したとき（今の失敗の表示のあとで呼ぶ） */
  onVoiceFailed?: () => void;
  /** 「作る」で保存を始めた直後に呼ぶ（親が、作成の往復の間に直した下書きで置き換えないための印） */
  onSaving?: () => void;
  /** 画面で選び直した公開の範囲を引き継ぐときの最初の値 */
  initialCalendarType?: "personal" | "shared";
}

/** 親が声の「はい」で「作る」を呼ぶための口（ボタンと同じ submit を呼ぶ） */
export interface SecretaryDraftEventHandle {
  /** 作れる状態なら作り始めて true。作れない（欄が足りない・保存中）なら何もせず false */
  submitByVoice(): boolean;
  /** 便W: 今の欄の値（直す頼みに付けるカルテ）と、画面で選んだ公開の範囲 */
  currentValues(): { karte: EventKarte; calendarType: "personal" | "shared" };
}

export const SecretaryDraftEvent = forwardRef<SecretaryDraftEventHandle, Props>(function SecretaryDraftEvent(
  { draft, onCreated, onCancel, onVoiceFailed, onSaving, initialCalendarType },
  ref,
) {
  const { t } = useTranslation();
  const [title, setTitle] = useState(draft.title ?? "");
  const [allDay, setAllDay] = useState(draft.is_all_day);
  // 下書きの start・end（+09:00 付き）は、今の画面と同じくブラウザの時間帯で欄に入れる。
  // ADR-1078: 空（null）なら欄も空にする（new Date(null) は 1970 年になるため呼ばない）
  const [startDate, setStartDate] = useState(() => (draft.start ? formatDateInput(new Date(draft.start)) : ""));
  const [startTime, setStartTime] = useState(() => (draft.start ? formatTimeInput(new Date(draft.start)) : ""));
  const [endDate, setEndDate] = useState(() => (draft.end ? formatDateInput(new Date(draft.end)) : ""));
  const [endTime, setEndTime] = useState(() => (draft.end ? formatTimeInput(new Date(draft.end)) : ""));
  const [location, setLocation] = useState(draft.location ?? "");
  const [description, setDescription] = useState(draft.description ?? "");
  const [calendarType, setCalendarType] = useState<"personal" | "shared">(initialCalendarType ?? draft.calendar_type);
  // ADR-1078: Meet は付けてよい人（meet_available）にだけ出す。最初の値は「はい」と答えたときだけ印あり
  const [addMeet, setAddMeet] = useState(draft.add_meet === true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const canCreate =
    title.trim() !== "" &&
    startDate !== "" &&
    endDate !== "" &&
    (allDay || (startTime !== "" && endTime !== "")) &&
    !saving;

  const submit = async () => {
    if (!canCreate) return;
    setSaving(true);
    onSaving?.();
    setError("");
    try {
      await api.post("/calendar/events", {
        title,
        start_datetime: combineDateTime(startDate, allDay ? "00:00" : startTime).toISOString(),
        end_datetime: combineDateTime(endDate, allDay ? "23:59" : endTime).toISOString(),
        is_all_day: allDay,
        calendar_type: calendarType,
        description: description || undefined,
        location: location || undefined,
        // 予定の画面と同じく、印があるときだけ add_meet を送る
        ...(draft.meet_available && addMeet ? { add_meet: true } : {}),
      });
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
      setSaving(false);
      onVoiceFailed?.();
    }
  };

  const submitRef = useRef(submit);
  submitRef.current = submit;
  const canRef = useRef(canCreate);
  canRef.current = canCreate && !saving;
  const valuesRef = useRef<() => { karte: EventKarte; calendarType: "personal" | "shared" }>(() => {
    throw new Error("not ready");
  });
  valuesRef.current = () => {
    const text = (value: string) => value.trim().slice(0, 1000) || null;
    const start = startDate === "" || (!allDay && startTime === "") ? null : toKarteTime(startDate, allDay ? "00:00" : startTime);
    const end = endDate === "" || (!allDay && endTime === "") ? null : toKarteTime(endDate, allDay ? "23:59" : endTime);
    return {
      karte: {
        title: text(title),
        start,
        end,
        is_all_day: allDay,
        location: text(location),
        description: text(description),
        is_meeting: draft.is_meeting,
        add_meet: draft.meet_available ? addMeet : draft.add_meet,
        asked: null,
        asked_count: 0,
        edit: true,
      },
      calendarType,
    };
  };
  useImperativeHandle(
    ref,
    () => ({
      submitByVoice: () => {
        if (!canRef.current) return false;
        void submitRef.current();
        return true;
      },
      currentValues: () => valuesRef.current(),
    }),
    [],
  );

  return (
    <div className="secretary-draft">
      <p className="secretary-draft__title">{t("secretary.event.title")}</p>
      <div className="secretary-draft__section">
        <TextField
          fullWidth
          label={t("secretary.event.name")}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <Checkbox
          label={t("secretary.event.allDay")}
          checked={allDay}
          onChange={(e) => setAllDay(e.target.checked)}
        />
        {draft.meet_available && (
          <Checkbox label={t("schedule.addMeet")} checked={addMeet} onChange={(e) => setAddMeet(e.target.checked)} />
        )}
        <div className="secretary-draft__row">
          <TextField
            fullWidth
            label={t("secretary.event.startDate")}
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
          {!allDay && (
            <TextField
              fullWidth
              label={t("secretary.event.startTime")}
              type="time"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
            />
          )}
        </div>
        <div className="secretary-draft__row">
          <TextField
            fullWidth
            label={t("secretary.event.endDate")}
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
          {!allDay && (
            <TextField
              fullWidth
              label={t("secretary.event.endTime")}
              type="time"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
            />
          )}
        </div>
        <TextField
          fullWidth
          label={t("secretary.event.location")}
          value={location}
          onChange={(e) => setLocation(e.target.value)}
        />
        <Textarea
          fullWidth
          label={t("secretary.event.description")}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <Select
          fullWidth
          label={t("secretary.event.visibility")}
          value={calendarType}
          onChange={(e) => setCalendarType(e.target.value === "shared" ? "shared" : "personal")}
          options={[
            { value: "personal", label: t("secretary.event.personal") },
            { value: "shared", label: t("secretary.event.shared") },
          ]}
        />
        {calendarType === "shared" && <p className="secretary-draft__hint">{t("secretary.event.sharedNote")}</p>}
      </div>
      {error && (
        <p className="secretary-draft__error" role="alert">
          {error}
        </p>
      )}
      <div className="secretary-draft__actions">
        <Button variant="secondary" size="sm" onClick={onCancel} disabled={saving}>
          {t("secretary.cancel")}
        </Button>
        <Button size="sm" onClick={submit} disabled={!canCreate} loading={saving}>
          {t("secretary.create")}
        </Button>
      </div>
    </div>
  );
});
