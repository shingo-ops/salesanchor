/**
 * AvatarUpload — 担当者アイコン登録金型（ADR-159）
 *
 * 円形プレビュー・画像選択・削除・エラー表示（行動ボタン付き）を 1 つにまとめた金型。
 * 未登録時は Discord 標準アイコンと同じく「アイコンなし」の汎用表示にする。
 * 文言は呼び出し側が t() で解決して labels に渡す（金型自身は文字列を持たない）。
 *
 * - 画像の形式・サイズ検証はサーバー側が正本。ここでは accept で選択肢を絞るだけ。
 * - エラー時は errorActionLabel の Button（画像を選び直す等）を表示し、押すと選択ダイアログを開く。
 */

import { useRef } from "react";
import type { ChangeEvent } from "react";
import { Button } from "./Button";
import { ACCOUNT_ICONS } from "../constants/icons";
import { ICON } from "../constants/iconSizes";
import "./AvatarUpload.css";

export interface AvatarUploadLabels {
  /** 未登録時の選択ボタン（例: 画像を選ぶ） */
  choose: string;
  /** 登録済み時の変更ボタン（例: 画像を変更） */
  change: string;
  /** 削除ボタン（例: 削除） */
  remove: string;
  /** アップロード中の表示（例: 保存中...） */
  uploading: string;
  /** 補足説明（例: 2MB以下のJPG・PNG・WebP） */
  hint: string;
  /** プレビュー画像の代替テキスト */
  imageAlt: string;
  /** エラー時の行動ボタン（例: 画像を選び直す） */
  errorAction: string;
}

export interface AvatarUploadProps {
  /** 登録済み画像の URL。未登録は null / undefined */
  imageUrl?: string | null;
  onSelect: (file: File) => void;
  onDelete: () => void;
  uploading?: boolean;
  /** 表示するエラーメッセージ（非エンジニア向けの短文）。空なら非表示 */
  errorMessage?: string;
  /** エラー行動ボタンの動作。省略時は画像選択ダイアログを開く（保存失敗の再試行など別動作にしたいときに指定） */
  onErrorAction?: () => void;
  labels: AvatarUploadLabels;
}

const ACCEPT = "image/jpeg,image/png,image/webp";

export function AvatarUpload({
  imageUrl,
  onSelect,
  onDelete,
  uploading = false,
  errorMessage,
  onErrorAction,
  labels,
}: AvatarUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const hasImage = Boolean(imageUrl);
  const Placeholder = ACCOUNT_ICONS.profile;

  const openPicker = () => inputRef.current?.click();

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    // 同じファイルを選び直しても change が発火するよう値を空に戻す
    e.target.value = "";
    if (file) onSelect(file);
  };

  return (
    <div className="comp-avatar-upload">
      <div className="comp-avatar-upload__row">
        <div
          className={
            hasImage
              ? "comp-avatar-upload__preview"
              : "comp-avatar-upload__preview comp-avatar-upload__preview--empty"
          }
          data-testid="avatar-preview"
        >
          {hasImage ? (
            <img className="comp-avatar-upload__img" src={imageUrl ?? undefined} alt={labels.imageAlt} />
          ) : (
            <Placeholder size={ICON.xl} aria-hidden="true" />
          )}
        </div>

        <div className="comp-avatar-upload__actions">
          <div className="comp-avatar-upload__buttons">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={openPicker}
              loading={uploading}
              loadingText={labels.uploading}
              disabled={uploading}
            >
              {hasImage ? labels.change : labels.choose}
            </Button>
            {hasImage && (
              <Button type="button" variant="ghost" size="sm" onClick={onDelete} disabled={uploading}>
                {labels.remove}
              </Button>
            )}
          </div>
          <span className="comp-avatar-upload__hint">{labels.hint}</span>
        </div>

        {/* 非表示のネイティブ file input（text/search ではないため UI ガバナンスの禁止対象外） */}
        <input
          ref={inputRef}
          className="comp-avatar-upload__input"
          type="file"
          accept={ACCEPT}
          onChange={handleChange}
          tabIndex={-1}
          aria-hidden="true"
          data-testid="avatar-file-input"
        />
      </div>

      {errorMessage && (
        <div className="comp-avatar-upload__error" role="alert">
          <span>{errorMessage}</span>
          <Button type="button" variant="outline" size="sm" onClick={onErrorAction ?? openPicker} disabled={uploading}>
            {labels.errorAction}
          </Button>
        </div>
      )}
    </div>
  );
}
