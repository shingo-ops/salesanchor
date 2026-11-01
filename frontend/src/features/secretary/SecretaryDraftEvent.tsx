/**
 * 予定の下書き（ADR-1056 段2）。送る欄は全部見せて、全部直せる。
 * 「作る」は今の予定の画面と同じ口 POST /calendar/events を、本人のログインで呼ぶ。
 * 日付と時刻の組み立ては今の予定の画面と同じ関数（combineDateTime など）を使う。
 */

import { useState } from "react";
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
import type { EventDraftData } from "./secretaryApi";

interface Props {
  draft: EventDraftData;
  onCreated: () => void;
  onCancel: () => void;
}

export function SecretaryDraftEvent({ draft, onCreated, onCancel }: Props) {
  const { t } = useTranslation();
  const [title, setTitle] = useState(draft.title);
  const [allDay, setAllDay] = useState(draft.is_all_day);
  // 下書きの start・end（+09:00 付き）は、今の画面と同じくブラウザの時間帯で欄に入れる
  const [startDate, setStartDate] = useState(() => formatDateInput(new Date(draft.start)));
  const [startTime, setStartTime] = useState(() => formatTimeInput(new Date(draft.start)));
  const [endDate, setEndDate] = useState(() => formatDateInput(new Date(draft.end)));
  const [endTime, setEndTime] = useState(() => formatTimeInput(new Date(draft.end)));
  const [location, setLocation] = useState(draft.location ?? "");
  const [description, setDescription] = useState(draft.description ?? "");
  const [calendarType, setCalendarType] = useState<"personal" | "shared">(draft.calendar_type);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const canCreate = title.trim() !== "" && startDate !== "" && endDate !== "" && !saving;

  const submit = async () => {
    if (!canCreate) return;
    setSaving(true);
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
      });
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
      setSaving(false);
    }
  };

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
}
