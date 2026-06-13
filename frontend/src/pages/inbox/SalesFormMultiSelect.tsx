/**
 * SalesFormMultiSelect — ADR-108 Phase B-1
 *
 * カルテ company タブの販売形態フィールドを複数選択対応に置き換えるコンポーネント。
 *
 * 機能:
 *   - チェックボックス付きドロップダウン（クリックでトグル表示）
 *   - 選択済み項目をチップ形式で表示
 *   - 「その他」選択時に自由記述欄を表示
 *   - onBlur イベントで既存の handleCardFieldBlur を呼び出す
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { NAV_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import type { SalesFormOption, SalesFormSelectionState } from "./inbox.types";

interface Props {
  options: SalesFormOption[];
  value: SalesFormSelectionState[];
  onChange: (selections: SalesFormSelectionState[]) => void;
  onBlur: () => void;
}

export function SalesFormMultiSelect({ options, value, onChange, onBlur }: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // ドロップダウン外クリックで閉じる
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        if (open) {
          setOpen(false);
          onBlur();
        }
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open, onBlur]);

  const isSelected = useCallback(
    (optionId: number) => value.some((s) => s.option_id === optionId),
    [value],
  );

  const otherOption = options.find((o) => o.value === "other");
  const otherSelection = value.find((s) => s.option_id === otherOption?.id);

  const toggleOption = useCallback(
    (option: SalesFormOption) => {
      const alreadySelected = isSelected(option.id);
      let next: SalesFormSelectionState[];
      if (alreadySelected) {
        next = value.filter((s) => s.option_id !== option.id);
      } else {
        next = [
          ...value,
          {
            option_id: option.id,
            option_value: option.value,
            option_label: option.label,
            other_text: null,
          },
        ];
      }
      onChange(next);
    },
    [value, isSelected, onChange],
  );

  const handleOtherTextChange = useCallback(
    (text: string) => {
      if (!otherOption) return;
      const next = value.map((s) =>
        s.option_id === otherOption.id ? { ...s, other_text: text || null } : s,
      );
      onChange(next);
    },
    [value, otherOption, onChange],
  );

  const selectedLabels = value
    .map((s) => {
      if (s.option_value === "other" && s.other_text) {
        return s.other_text;
      }
      return s.option_label;
    })
    .join("、");

  return (
    <div
      className="sales-form-multi-select"
      ref={containerRef}
      data-testid="sales-form-multi-select"
    >
      {/* トリガーボタン（選択済み表示 + ドロップダウン開閉） */}
      <button
        type="button"
        className="right-panel-field sales-form-trigger"
        onClick={() => {
          if (open) onBlur();
          setOpen((prev) => !prev);
        }}
        aria-haspopup="listbox"
        aria-expanded={open}
        data-testid="sales-form-trigger"
      >
        {selectedLabels || t("leads.salesFormPlaceholder")}
        <NAV_ICONS.chevronDown size={ICON.sm} aria-hidden="true" className="sales-form-caret" />
      </button>

      {/* ドロップダウンパネル */}
      {open && (
        <div
          className="sales-form-dropdown"
          role="listbox"
          aria-multiselectable="true"
          data-testid="sales-form-dropdown"
        >
          {options.map((option) => {
            const checked = isSelected(option.id);
            return (
              <label
                key={option.id}
                className={`sales-form-option${checked ? " sales-form-option--checked" : ""}`}
                data-testid={`sales-form-option-${option.value}`}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleOption(option)}
                  aria-label={option.label}
                />
                <span className="sales-form-option-label">{option.label}</span>
              </label>
            );
          })}
        </div>
      )}

      {/* 「その他」自由記述欄 */}
      {otherOption && isSelected(otherOption.id) && (
        <input
          type="text"
          className="right-panel-field sales-form-other-input"
          placeholder={t("leads.salesFormOtherPlaceholder")}
          value={otherSelection?.other_text ?? ""}
          onChange={(e) => handleOtherTextChange(e.target.value)}
          onBlur={onBlur}
          data-testid="sales-form-other-input"
        />
      )}
    </div>
  );
}
